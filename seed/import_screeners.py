"""Seed the database with built-in screener definitions."""

import logging

from stockpulse.extensions import get_db
from stockpulse.models.screener import Screener, ScreenerCondition
from seed.builtin_screeners import BUILTIN_SCREENERS

logger = logging.getLogger(__name__)


def seed_screeners(force: bool = False) -> int:
    """Load all built-in screeners into the database.

    Args:
        force: If True, delete existing built-in screeners and re-seed.

    Returns:
        Number of screeners created.
    """
    session = get_db()

    try:
        if force:
            # Delete existing built-in screeners
            session.query(ScreenerCondition).filter(
                ScreenerCondition.screener_id.in_(
                    session.query(Screener.id).filter(Screener.is_builtin == True)
                )
            ).delete(synchronize_session=False)
            session.query(Screener).filter(Screener.is_builtin == True).delete()
            session.commit()
            logger.info("Deleted existing built-in screeners")

        created = 0
        for defn in BUILTIN_SCREENERS:
            # Skip if slug already exists
            existing = (
                session.query(Screener)
                .filter(Screener.slug == defn["slug"])
                .first()
            )
            if existing:
                logger.debug("Screener %s already exists, skipping", defn["slug"])
                continue

            screener = Screener(
                name=defn["name"],
                slug=defn["slug"],
                category=defn.get("category"),
                is_builtin=True,
                is_active=True,
            )
            session.add(screener)
            session.flush()  # Get the ID

            for i, cond in enumerate(defn["conditions"]):
                session.add(
                    ScreenerCondition(
                        screener_id=screener.id,
                        field=cond["field"],
                        operator=cond["operator"],
                        value=cond.get("value"),
                        ordinal=i,
                    )
                )

            created += 1

        session.commit()
        logger.info("Seeded %d built-in screeners", created)
        return created

    except Exception:
        session.rollback()
        logger.exception("Failed to seed screeners")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from stockpulse.app import create_app

    create_app()
    count = seed_screeners(force=True)
    print(f"Seeded {count} screeners")
