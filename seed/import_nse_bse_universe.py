"""Expand stock universe by downloading official NSE/BSE equity lists.

Downloads the NSE equity list (EQUITY_L.csv) and optionally the BSE scrip
master, cross-references by ISIN, and upserts new stocks into the database.
"""

import io
import logging

import httpx
import pandas as pd

from stockpulse.extensions import get_db
from stockpulse.models.stock import Stock

logger = logging.getLogger(__name__)

NSE_EQUITY_URL = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"

# NSE blocks bare requests; mimic a browser
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*",
}


def download_nse_equity_list() -> pd.DataFrame:
    """Download and parse the NSE equity list CSV.

    Returns a DataFrame with columns: SYMBOL, NAME OF COMPANY, SERIES, ISIN NUMBER, etc.
    Filtered to EQ series only (regular equity, excluding BE/BZ/SM etc.).
    """
    with httpx.Client(headers=_HEADERS, follow_redirects=True, timeout=30) as client:
        # NSE requires a session cookie; hit the homepage first
        client.get("https://www.nseindia.com/")
        resp = client.get(NSE_EQUITY_URL)
        resp.raise_for_status()

    df = pd.read_csv(io.StringIO(resp.text))

    # Normalize column names (strip whitespace)
    df.columns = [c.strip() for c in df.columns]

    # Handle slight column name variations
    actual_cols = set(df.columns)
    isin_col = None
    for candidate in ("ISIN NUMBER", " ISIN NUMBER", "ISIN"):
        if candidate in actual_cols:
            isin_col = candidate
            break

    if isin_col and isin_col != "ISIN NUMBER":
        df = df.rename(columns={isin_col: "ISIN NUMBER"})

    # Filter to EQ series if the column exists
    if " SERIES" in df.columns:
        df = df[df[" SERIES"].str.strip() == "EQ"]
    elif "SERIES" in df.columns:
        df = df[df["SERIES"].str.strip() == "EQ"]

    logger.info("NSE equity list: %d EQ-series stocks downloaded", len(df))
    return df


def import_expanded_universe(dry_run: bool = False) -> dict:
    """Download the NSE equity list and upsert new stocks into the database.

    Args:
        dry_run: If True, only report counts without inserting.

    Returns:
        Dict with counts: {downloaded, created, skipped, reactivated}
    """
    nse_df = download_nse_equity_list()
    stats = {"downloaded": len(nse_df), "created": 0, "skipped": 0, "reactivated": 0}

    if dry_run:
        session = get_db()
        try:
            existing_nse = {
                s.nse_symbol
                for s in session.query(Stock.nse_symbol).filter(Stock.nse_symbol.isnot(None)).all()
            }
            new_count = sum(
                1 for _, row in nse_df.iterrows()
                if str(row["SYMBOL"]).strip() not in existing_nse
            )
            stats["would_create"] = new_count
            stats["would_skip"] = stats["downloaded"] - new_count
        finally:
            session.close()

        logger.info("Dry run: %d new stocks would be added", stats.get("would_create", 0))
        return stats

    session = get_db()
    new_stock_ids = []

    try:
        for idx, row in nse_df.iterrows():
            nse_symbol = str(row["SYMBOL"]).strip()
            company_name = str(row["NAME OF COMPANY"]).strip()
            isin = str(row.get("ISIN NUMBER", "")).strip() or None

            if not nse_symbol or not company_name:
                stats["skipped"] += 1
                continue

            # Check by NSE symbol first
            existing = (
                session.query(Stock)
                .filter(Stock.nse_symbol == nse_symbol)
                .first()
            )

            if existing:
                if not existing.is_active:
                    existing.is_active = True
                    stats["reactivated"] += 1
                else:
                    stats["skipped"] += 1
                continue

            # Also check by ISIN to avoid duplicates
            if isin:
                existing_isin = (
                    session.query(Stock)
                    .filter(Stock.isin == isin)
                    .first()
                )
                if existing_isin:
                    # Update NSE symbol if missing
                    if not existing_isin.nse_symbol:
                        existing_isin.nse_symbol = nse_symbol
                    stats["skipped"] += 1
                    continue

            stock = Stock(
                symbol=nse_symbol,  # Use NSE symbol as primary symbol
                nse_symbol=nse_symbol,
                company_name=company_name,
                isin=isin,
                is_active=True,
            )
            session.add(stock)
            stats["created"] += 1

            # Commit in batches
            if stats["created"] % 200 == 0:
                session.flush()
                logger.info("Progress: %d created", stats["created"])

        session.commit()

        # Collect IDs of newly created stocks for backfill
        if stats["created"] > 0:
            new_stocks = (
                session.query(Stock.id)
                .filter(Stock.is_active.is_(True))
                .order_by(Stock.id.desc())
                .limit(stats["created"])
                .all()
            )
            new_stock_ids = [s.id for s in new_stocks]

        logger.info(
            "Universe expansion complete: %d downloaded, %d created, %d skipped, %d reactivated",
            stats["downloaded"], stats["created"], stats["skipped"], stats["reactivated"],
        )

    except Exception:
        session.rollback()
        logger.exception("Universe expansion failed")
        raise
    finally:
        session.close()

    stats["new_stock_ids"] = new_stock_ids
    return stats


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Expand StockPulse universe from NSE/BSE")
    parser.add_argument("--dry-run", action="store_true", help="Show counts without inserting")
    parser.add_argument("--backfill", action="store_true", help="Trigger backfill for new stocks")
    args = parser.parse_args()

    from stockpulse.app import create_app
    create_app()

    result = import_expanded_universe(dry_run=args.dry_run)
    print(f"Result: {result}")

    if args.backfill and not args.dry_run and result.get("new_stock_ids"):
        from stockpulse.ingestion.tasks import backfill_batch
        stock_ids = result["new_stock_ids"]
        # Split into chunks of ~500 for parallel workers
        chunk_size = 500
        for i in range(0, len(stock_ids), chunk_size):
            chunk = stock_ids[i : i + chunk_size]
            backfill_batch.delay(chunk)
            print(f"Queued backfill for {len(chunk)} stocks (batch {i // chunk_size + 1})")
