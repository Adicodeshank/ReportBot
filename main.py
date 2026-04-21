"""
main.py
-------
The single entry point for the Report Bot.

This file is what cron calls every morning at 8:00 AM.
It does NOT contain any business logic of its own.
Its only job is to call the three layers in the correct order
and handle any failures gracefully.

PIPELINE:
  1. fetch_daily_summary()  ->  pulls data from PostgreSQL
  2. get_summary_dict()     ->  flattens DataFrame to plain dict
  3. generate_report()      ->  builds the PDF from the dict
  4. send_report()          ->  emails the PDF to the manager

WHY A SEPARATE main.py?
  Each module (database, report, emailer) does one thing.
  main.py is the only file that knows all three exist.
  This means you can test each module independently,
  and swap any one of them without touching the others.

  Example: want Excel instead of PDF tomorrow?
  Replace generate_report() with generate_excel() here.
  Nothing else changes.

USAGE:
  python main.py
  (or via cron: 0 8 * * * python /app/main.py)
"""

import logging
import sys
from datetime import datetime

from app.config   import config
from app.database import fetch_daily_summary, get_summary_dict
from app.report   import generate_report
from app.emailer  import send_report


# == Logging setup =============================================================
# We configure logging here (in the entry point) not inside individual modules.
# Modules only call log.info() / log.error() - they never configure handlers.
# This is the correct Python pattern: configure once at the top, use everywhere.

logging.basicConfig(
    level    = logging.INFO,
    format   = "%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt  = "%Y-%m-%d %H:%M:%S",
    handlers = [
        logging.StreamHandler(sys.stdout),
    ]
)

log = logging.getLogger(__name__)


# == Pipeline steps ============================================================

def step_fetch() -> dict:
    """
    Step 1: Fetch from DB and convert to summary dict.

    Returns:
        dict with all KPI values for yesterday.
    """
    log.info("STEP 1/3 - Fetching data from database...")
    df      = fetch_daily_summary()
    summary = get_summary_dict(df)

    log.info(
        f"Data fetched -> "
        f"Users: {summary['new_users']}  |  "
        f"Orders: {summary['total_orders']}  |  "
        f"Revenue: INR {summary['total_revenue']:,.2f}"
    )
    return summary


def step_generate(summary: dict) -> str:
    """
    Step 2: Generate the PDF report from the summary dict.

    Args:
        summary: dict from step_fetch()

    Returns:
        str: path to the saved PDF file
    """
    log.info("STEP 2/3 - Generating PDF report...")
    pdf_path = generate_report(summary)
    log.info(f"PDF ready -> {pdf_path}")
    return pdf_path


def step_email(pdf_path: str) -> None:
    """
    Step 3: Email the PDF to the manager.

    Args:
        pdf_path: path returned by step_generate()
    """
    log.info(f"STEP 3/3 - Sending email to {config.recipient}...")
    send_report(pdf_path)
    log.info("Email delivered successfully.")


# == Main entry point ==========================================================

def main() -> None:
    """
    Run the full pipeline with proper error handling.

    Exit codes (important for cron and Docker monitoring):
      0 -> success
      1 -> failure
    """
    start_time = datetime.now()

    log.info("=" * 60)
    log.info(f"  Report Bot starting for {config.report_date}")
    log.info("=" * 60)

    try:
        summary  = step_fetch()
        pdf_path = step_generate(summary)
        step_email(pdf_path)

        duration = (datetime.now() - start_time).seconds
        log.info("=" * 60)
        log.info(f"  Report Bot DONE in {duration}s")
        log.info("=" * 60)

        sys.exit(0)

    except Exception as e:
        log.error("=" * 60)
        log.error(f"  Report Bot FAILED: {type(e).__name__}: {e}")
        log.error("  Check the logs above for details.")
        log.error("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()