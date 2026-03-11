"""Webhook delivery dispatcher with retry logic."""

import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy.orm import Session

from stockpulse.models.event import Event, Webhook, WebhookDelivery

logger = logging.getLogger(__name__)

# Retry delays in seconds (exponential backoff)
RETRY_DELAYS = [30, 120, 900]  # 30s, 2min, 15min
MAX_RETRIES = 3


def dispatch_events(session: Session, event_ids: list[int]) -> int:
    """Match events to webhooks and create delivery records.

    Returns number of deliveries created.
    """
    if not event_ids:
        return 0

    events = session.query(Event).filter(Event.id.in_(event_ids)).all()
    webhooks = session.query(Webhook).filter(Webhook.is_active == True).all()

    deliveries = 0
    for event in events:
        for webhook in webhooks:
            if event.event_type in webhook.event_types:
                delivery = WebhookDelivery(
                    webhook_id=webhook.id,
                    event_id=event.id,
                    status="pending",
                    attempt=0,
                )
                session.add(delivery)
                deliveries += 1

    if deliveries:
        session.commit()
        logger.info("Created %d webhook deliveries for %d events", deliveries, len(events))

    return deliveries


def deliver(session: Session, delivery_id: int) -> bool:
    """Attempt to deliver a single webhook payload.

    Returns True if delivery succeeded.
    """
    delivery = session.query(WebhookDelivery).filter(WebhookDelivery.id == delivery_id).first()
    if not delivery:
        return False

    webhook = session.query(Webhook).filter(Webhook.id == delivery.webhook_id).first()
    event = session.query(Event).filter(Event.id == delivery.event_id).first()

    if not webhook or not event:
        delivery.status = "failed"
        session.commit()
        return False

    # Build payload
    payload = {
        "event_id": event.id,
        "event_type": event.event_type,
        "stock_id": event.stock_id,
        "payload": event.payload,
        "created_at": event.created_at.isoformat(),
    }

    body = json.dumps(payload)

    # Sign payload if secret is set
    headers = {"Content-Type": "application/json"}
    if webhook.secret:
        signature = hmac.new(
            webhook.secret.encode("utf-8"),
            body.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        headers["X-StockPulse-Signature"] = signature

    delivery.attempt += 1

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(webhook.url, content=body, headers=headers)

        delivery.response_code = resp.status_code
        delivery.response_body = resp.text[:1000]  # Truncate

        if 200 <= resp.status_code < 300:
            delivery.status = "delivered"
            delivery.delivered_at = datetime.now(timezone.utc)
            session.commit()
            return True
        else:
            logger.warning(
                "Webhook delivery %d got %d from %s",
                delivery_id, resp.status_code, webhook.url,
            )

    except Exception as e:
        delivery.response_body = str(e)[:1000]
        logger.warning("Webhook delivery %d failed: %s", delivery_id, e)

    # Schedule retry or mark as failed
    if delivery.attempt >= MAX_RETRIES:
        delivery.status = "failed"
    else:
        delivery.status = "retrying"
        delay = RETRY_DELAYS[min(delivery.attempt - 1, len(RETRY_DELAYS) - 1)]
        delivery.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=delay)

    session.commit()
    return False


def process_pending_retries(session: Session) -> int:
    """Process any webhook deliveries that are due for retry.

    Returns number of retries attempted.
    """
    now = datetime.now(timezone.utc)
    pending = (
        session.query(WebhookDelivery)
        .filter(
            WebhookDelivery.status == "retrying",
            WebhookDelivery.next_retry_at <= now,
        )
        .all()
    )

    retried = 0
    for delivery in pending:
        deliver(session, delivery.id)
        retried += 1

    return retried
