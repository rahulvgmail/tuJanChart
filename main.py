import click

from stockpulse.app import create_app

app = create_app()


def create_app_wrapper():
    """Entry point for gunicorn / flask run."""
    return app


@app.cli.command("seed-admin")
@click.argument("email")
@click.argument("password")
@click.option("--name", default=None, help="Admin user name")
def seed_admin(email, password, name):
    """Create the initial admin user.

    Usage: flask seed-admin admin@example.com MySecurePassword
    """
    from stockpulse.extensions import get_db
    from stockpulse.models.user import User

    session = get_db()
    try:
        existing = session.query(User).filter(User.email == email).first()
        if existing:
            click.echo(f"User {email} already exists.")
            return

        user = User(email=email, name=name, role="admin")
        user.set_password(password)
        session.add(user)
        session.commit()
        click.echo(f"Admin user {email} created successfully.")
    finally:
        session.close()


@app.cli.command("seed-screeners")
@click.option("--force", is_flag=True, help="Re-create even if they exist")
def seed_screeners_cmd(force):
    """Load built-in screener definitions into the database."""
    from seed.import_screeners import seed_screeners

    count = seed_screeners(force=force)
    click.echo(f"Seeded {count} screeners.")


@app.cli.command("import-universe")
@click.option("--force", is_flag=True, help="Clear and re-import all stocks")
def import_universe_cmd(force):
    """Import stock universe from spreadsheet."""
    from seed.import_universe import import_universe

    result = import_universe(force=force)
    click.echo(f"Universe import: {result}")


@app.cli.command("import-result-dates")
def import_result_dates_cmd():
    """Import result dates and board meetings from spreadsheet."""
    from seed.import_result_dates import import_board_meetings, import_result_dates

    rd = import_result_dates()
    click.echo(f"Result dates: {rd}")
    bm = import_board_meetings()
    click.echo(f"Board meetings: {bm}")


@app.cli.command("import-corporate-data")
def import_corporate_data_cmd():
    """Import ASM entries and circuit bands from spreadsheet."""
    from seed.import_corporate_data import import_asm_entries, import_circuit_bands

    asm = import_asm_entries()
    click.echo(f"ASM entries: {asm}")
    cb = import_circuit_bands()
    click.echo(f"Circuit bands: {cb}")


@app.cli.command("run-migration")
@click.option("--skip-backfill", is_flag=True, help="Skip yfinance price backfill")
@click.option("--force", is_flag=True, help="Force re-import")
def run_migration_cmd(skip_backfill, force):
    """Run the full spreadsheet migration pipeline."""
    import time

    start = time.time()

    from seed.import_corporate_data import import_asm_entries, import_circuit_bands
    from seed.import_result_dates import import_board_meetings, import_result_dates
    from seed.import_screeners import seed_screeners
    from seed.import_universe import import_universe

    click.echo("Step 1: Importing stock universe...")
    click.echo(f"  {import_universe(force=force)}")

    click.echo("Step 2: Importing result dates...")
    click.echo(f"  {import_result_dates()}")
    click.echo(f"  {import_board_meetings()}")

    click.echo("Step 3: Importing ASM & circuit bands...")
    click.echo(f"  {import_asm_entries()}")
    click.echo(f"  {import_circuit_bands()}")

    click.echo("Step 4: Seeding screeners...")
    click.echo(f"  {seed_screeners(force=force)} screeners")

    if not skip_backfill:
        click.echo("Step 5: Backfilling prices (this will take a while)...")
        from seed.run_migration import _run_backfill
        _run_backfill()
    else:
        click.echo("Step 5: Skipped price backfill")

    click.echo(f"Migration complete in {time.time() - start:.1f}s")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
