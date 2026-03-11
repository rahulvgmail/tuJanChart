"""Run the full spreadsheet migration pipeline.

Usage:
    uv run python seed/run_migration.py [--skip-backfill] [--force]
"""

import argparse
import logging
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Run StockPulse data migration")
    parser.add_argument("--skip-backfill", action="store_true", help="Skip yfinance backfill")
    parser.add_argument("--force", action="store_true", help="Force re-import (clears existing data)")
    args = parser.parse_args()

    # Initialize Flask app (sets up DB, etc.)
    from stockpulse.app import create_app
    app = create_app()

    with app.app_context():
        start = time.time()

        # Step 1: Import stock universe
        print("\n=== Step 1: Importing stock universe ===")
        from seed.import_universe import import_universe
        universe_stats = import_universe(force=args.force)
        print(f"  Universe: {universe_stats}")

        # Step 2: Import result dates
        print("\n=== Step 2: Importing result dates ===")
        from seed.import_result_dates import import_result_dates, import_board_meetings
        rd_stats = import_result_dates()
        print(f"  Result dates: {rd_stats}")
        bm_stats = import_board_meetings()
        print(f"  Board meetings: {bm_stats}")

        # Step 3: Import ASM and circuit bands
        print("\n=== Step 3: Importing ASM & circuit bands ===")
        from seed.import_corporate_data import import_asm_entries, import_circuit_bands
        asm_stats = import_asm_entries()
        print(f"  ASM entries: {asm_stats}")
        cb_stats = import_circuit_bands()
        print(f"  Circuit bands: {cb_stats}")

        # Step 4: Seed screeners
        print("\n=== Step 4: Seeding screener definitions ===")
        from seed.import_screeners import seed_screeners
        screener_count = seed_screeners(force=args.force)
        print(f"  Screeners seeded: {screener_count}")

        # Step 5: Backfill historical prices (optional, long-running)
        if not args.skip_backfill:
            print("\n=== Step 5: Backfilling historical prices ===")
            print("  This will take ~30 minutes for 1660 stocks...")
            _run_backfill()
        else:
            print("\n=== Step 5: Skipping price backfill (--skip-backfill) ===")

        elapsed = time.time() - start
        print(f"\n=== Migration complete in {elapsed:.1f}s ===")


def _run_backfill():
    """Backfill 1 year of daily prices for all active stocks."""
    from stockpulse.extensions import get_db
    from stockpulse.ingestion.adapters.yfinance_adapter import YFinanceAdapter
    from stockpulse.ingestion.tasks import _generate_weekly_prices, _upsert_daily_prices
    from stockpulse.models.stock import Stock
    from datetime import date, timedelta

    session = get_db()
    adapter = YFinanceAdapter()

    try:
        stocks = (
            session.query(Stock.id, Stock.nse_symbol)
            .filter(Stock.is_active == True, Stock.nse_symbol.isnot(None))
            .all()
        )

        end = date.today()
        start = end - timedelta(days=365)

        total = len(stocks)
        done = 0
        errors = 0

        # Process in batches of 50 (yfinance batch size)
        symbols_batch = []
        id_map = {}

        for stock_id, nse_symbol in stocks:
            symbols_batch.append(nse_symbol)
            id_map[nse_symbol] = stock_id

            if len(symbols_batch) >= 50:
                _process_batch(session, adapter, symbols_batch, id_map, start, end)
                done += len(symbols_batch)
                print(f"  Progress: {done}/{total} stocks backfilled")
                symbols_batch = []
                id_map = {}

        # Process remaining
        if symbols_batch:
            _process_batch(session, adapter, symbols_batch, id_map, start, end)
            done += len(symbols_batch)

        session.commit()
        print(f"  Backfill complete: {done} stocks, {errors} errors")

    except Exception:
        session.rollback()
        logger.exception("Backfill failed")
        raise
    finally:
        session.close()


def _process_batch(session, adapter, symbols, id_map, start, end):
    """Process a batch of symbols for backfill."""
    from stockpulse.ingestion.tasks import _generate_weekly_prices, _upsert_daily_prices

    try:
        data = adapter.fetch_daily_ohlcv(symbols, start, end)
        for sym, df in data.items():
            stock_id = id_map.get(sym)
            if stock_id and not df.empty:
                _upsert_daily_prices(session, stock_id, df)
                _generate_weekly_prices(session, stock_id, start, end)
        session.commit()
    except Exception as e:
        logger.warning("Batch backfill error: %s", e)
        session.rollback()


if __name__ == "__main__":
    main()
