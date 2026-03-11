"""Celery tasks for event detection and webhook delivery."""

import logging
from datetime import date

from stockpulse.extensions import celery_app, get_db
from stockpulse.engine.events import detect_events_for_universe
from stockpulse.models.stock import Stock
from stockpulse.webhooks.dispatcher import deliver, dispatch_events, process_pending_retries

logger = logging.getLogger(__name__)


@celery_app.task(name="webhooks.process_events", bind=True)
def process_events(self, as_of_str: str | None = None):
    """Detect events for all stocks and dispatch to webhooks.

    Called after indicator recomputation.
    """
    as_of = date.fromisoformat(as_of_str) if as_of_str else date.today()
    session = get_db()

    try:
        stock_ids = [
            sid for (sid,) in session.query(Stock.id).filter(Stock.is_active == True).all()
        ]

        if not stock_ids:
            return {"status": "no_stocks"}

        # Detect events
        total_events = detect_events_for_universe(session, stock_ids, as_of)

        # Get newly created event IDs
        from stockpulse.models.event import Event
        from sqlalchemy import desc

        new_events = (
            session.query(Event.id)
            .order_by(desc(Event.created_at))
            .limit(total_events)
            .all()
        )
        event_ids = [e.id for e in new_events]

        # Dispatch to webhooks
        deliveries = dispatch_events(session, event_ids)

        # Attempt immediate delivery
        from stockpulse.models.event import WebhookDelivery

        pending = (
            session.query(WebhookDelivery)
            .filter(WebhookDelivery.status == "pending")
            .all()
        )
        for d in pending:
            deliver(session, d.id)

        logger.info(
            "Event processing complete: %d events, %d deliveries",
            total_events, deliveries,
        )

        return {
            "status": "ok",
            "events": total_events,
            "deliveries": deliveries,
        }

    except Exception:
        session.rollback()
        logger.exception("Event processing failed")
        return {"status": "error"}
    finally:
        session.close()


@celery_app.task(name="webhooks.retry_deliveries", bind=True)
def retry_deliveries(self):
    """Process webhook deliveries that are due for retry."""
    session = get_db()

    try:
        retried = process_pending_retries(session)
        if retried:
            logger.info("Retried %d webhook deliveries", retried)
        return {"status": "ok", "retried": retried}
    except Exception:
        session.rollback()
        logger.exception("Retry processing failed")
        return {"status": "error"}
    finally:
        session.close()
