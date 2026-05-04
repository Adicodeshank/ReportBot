"""
config.py
---------
"""

import os
import tempfile
from dataclasses import dataclass
from datetime import date, timedelta
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(
            f"Missing required environment variable: '{key}'\n"
            f"Please add it to your .env file. See .env.example for reference."
        )
    return value


def _build_db_url() -> str:
    """
    Build the PostgreSQL connection URL.

    PRIORITY:
      1. If DATABASE_URL env var exists -> use it directly (Neon provides this)
      2. Otherwise -> build from individual DB_* parts (local development)

    WHY TWO APPROACHES?
      Neon gives a full connection string with sslmode already included.
      Local PostgreSQL is easier to configure with separate parts.
      This function handles both cases automatically.
    """
    # Option 1: Full URL provided directly (GitHub Actions + Neon)
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    # Option 2: Build from parts (local development)
    host     = _require("DB_HOST")
    port     = _require("DB_PORT")
    name     = _require("DB_NAME")
    user     = _require("DB_USER")
    password = quote_plus(_require("DB_PASSWORD"))
    sslmode  = os.getenv("DB_SSLMODE", "prefer")
    return f"postgresql://{user}:{password}@{host}:{port}/{name}?sslmode={sslmode}"


def _pdf_path(report_date: date) -> str:
    tmp = tempfile.gettempdir()
    return os.path.join(tmp, f"report_{report_date}.pdf")


@dataclass(frozen=True)
class Config:
    db_url:         str
    gmail_user:     str
    gmail_password: str
    recipient:      str
    report_date:    date
    pdf_path:       str


def load_config() -> Config:
    report_date = date.today() - timedelta(days=1)
    return Config(
        db_url         = _build_db_url(),
        gmail_user     = _require("GMAIL_USER"),
        gmail_password = _require("GMAIL_APP_PASSWORD"),
        recipient      = _require("REPORT_RECIPIENT"),
        report_date    = report_date,
        pdf_path       = _pdf_path(report_date),
    )


config = load_config()