"""
database.py
-----------
Handles everything related to the database:
  1. Creates a connection engine (once, reused)
  2. Reads the SQL query from sql/daily_summary.sql
  3. Executes it with :start_date / :end_date parameters
  4. Returns a clean Pandas DataFrame + a flat summary dict

SCHEMA THIS FILE EXPECTS:
  users  (id, email, signup_date)
  orders (id, user_id, amount, status)
"""

import logging
from datetime import timedelta
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.config import config

log = logging.getLogger(__name__)

# ── SQL file path ─────────────────────────────────────────────────────────────
# Resolved relative to this file so it works from any working directory.
SQL_PATH = Path(__file__).parent.parent / "sql" / "daily_summary.sql"

# ── Engine singleton ──────────────────────────────────────────────────────────
# Created once at import time. pool_pre_ping=True auto-recovers stale connections.
import os
# secure socket layer
_ssl_mode = os.getenv('DB_SSLMODE', 'prefer')   # require for Neon, prefer for local
_engine = create_engine(
    config.db_url,
    pool_pre_ping=True,
    connect_args={'sslmode': _ssl_mode}
)


def _load_query() -> str:
    """Read and return the SQL file contents."""
    if not SQL_PATH.exists():
        raise FileNotFoundError(f"SQL file not found: {SQL_PATH}")
    return SQL_PATH.read_text()


def fetch_daily_summary() -> pd.DataFrame:
    """
    Run daily_summary.sql for yesterday and return results as a DataFrame.

    Returns a DataFrame with these columns:
        report_date, new_users, total_orders, total_revenue,
        avg_order_value, max_order_value,
        completed_orders, pending_orders, cancelled_orders

    Returns an EMPTY DataFrame (not an error) if there is no data —
    the PDF layer handles the empty case gracefully.
    """
    log.info(f"Fetching daily summary for {config.report_date}...")

    params = {
        "start_date": str(config.report_date),
        "end_date":   str(config.report_date + timedelta(days=1)),
    }

    try:
        with _engine.connect() as conn:
            df = pd.read_sql(text(_load_query()), conn, params=params)
    except SQLAlchemyError as e:
        log.error(f"Database error: {e}")
        raise

    if df.empty or df["total_orders"].iloc[0] == 0:
        log.warning(f"No orders found for {config.report_date}.")
    else:
        log.info(
            f"Found {df['total_orders'].iloc[0]} orders | "
            f"Revenue: ₹{df['total_revenue'].iloc[0]}"
        )

    return df


def get_summary_dict(df: pd.DataFrame) -> dict:
    """
    Flatten the first (and only) DataFrame row into a plain dictionary.
    Returns safe zero-defaults if the DataFrame is empty.

    This dict is what report.py and emailer.py consume —
    they never touch the DataFrame directly.
    """
    if df.empty or df["total_orders"].iloc[0] == 0:
        return {
            "report_date":      config.report_date,
            "new_users":        0,
            "total_orders":     0,
            "total_revenue":    0.0,
            "avg_order_value":  0.0,
            "max_order_value":  0.0,
            "completed_orders": 0,
            "pending_orders":   0,
            "cancelled_orders": 0,
        }

    row = df.iloc[0]
    return {
        "report_date":      row["report_date"],
        "new_users":        int(row["new_users"]),
        "total_orders":     int(row["total_orders"]),
        "total_revenue":    float(row["total_revenue"]),
        "avg_order_value":  float(row["avg_order_value"]),
        "max_order_value":  float(row["max_order_value"]),
        "completed_orders": int(row["completed_orders"]),
        "pending_orders":   int(row["pending_orders"]),
        "cancelled_orders": int(row["cancelled_orders"]),
    }