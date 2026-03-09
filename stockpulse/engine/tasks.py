"""Celery tasks for indicator computation."""

import logging
import time
from datetime import date

from stockpulse.extensions import celery_app, get_db
from stockpulse.engine.indicators import compute_all_indicators
from stockpulse.models.stock import Stock

logger = logging.getLogger(__name__)


@celery_app.task(name="engine.recompute_universe", bind=True)
def recompute_universe(self, as_of_str: str | None = None):
    """Recompute all indicators for all active stocks.

    Target: 1660 stocks in <3 minutes.
    Called after EOD data pull or manually.
    """
    as_of = date.fromisoformat(as_of_str) if as_of_str else date.today()
    session = get_db()
    start_time = time.time()

    try:
        stock_ids = [
            sid
            for (sid,) in session.query(Stock.id)
            .filter(Stock.is_active == True)
            .all()
        ]

        if not stock_ids:
            logger.warning("No active stocks to recompute")
            return {"status": "no_stocks"}

        computed = 0
        errors = 0

        for stock_id in stock_ids:
            try:
                indicator = compute_all_indicators(session, stock_id, as_of)
                if indicator:
                    computed += 1
            except Exception:
                logger.exception("Error computing indicators for stock %d", stock_id)
                errors += 1

            # Commit in batches of 100
            if (computed + errors) % 100 == 0:
                session.commit()
                logger.info("Progress: %d/%d stocks", computed + errors, len(stock_ids))

        session.commit()
        elapsed = time.time() - start_time

        logger.info(
            "Recompute complete: %d computed, %d errors, %.1fs elapsed",
            computed,
            errors,
            elapsed,
        )

        return {
            "status": "ok",
            "date": as_of.isoformat(),
            "computed": computed,
            "errors": errors,
            "elapsed_seconds": round(elapsed, 1),
        }

    except Exception:
        session.rollback()
        logger.exception("Recompute universe failed")
        return {"status": "error"}
    finally:
        session.close()


@celery_app.task(name="engine.compute_single_stock", bind=True)
def compute_single_stock(self, stock_id: int, as_of_str: str | None = None):
    """Compute indicators for a single stock.

    Used after backfill or for on-demand recomputation.
    """
    as_of = date.fromisoformat(as_of_str) if as_of_str else date.today()
    session = get_db()

    try:
        indicator = compute_all_indicators(session, stock_id, as_of)
        session.commit()

        if indicator:
            return {
                "status": "ok",
                "stock_id": stock_id,
                "date": as_of.isoformat(),
                "price": float(indicator.current_price) if indicator.current_price else None,
            }
        return {"status": "no_data", "stock_id": stock_id}

    except Exception:
        session.rollback()
        logger.exception("Compute failed for stock %d", stock_id)
        return {"status": "error", "stock_id": stock_id}
    finally:
        session.close()
