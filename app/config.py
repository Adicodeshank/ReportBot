"""
config.py
---------

WHY THIS EXISTS:
  Instead of scattering os.environ calls across every file,
  we load everything here once. If a variable is missing, the app
  crashes immediately with a clear error - not silently mid-run.

USAGE:
  from app.config import config
  print(config.db_url)
""" 

import os
import tempfile
from dataclasses import dataclass
from datetime import date, timedelta
from urllib.parse import quote_plus
from dotenv import load_dotenv

# Load variables from .env file into os.environ.
# In Docker, env vars are injected directly - load_dotenv() does nothing there.
load_dotenv()


def _require(key: str) -> str:
    """
    Fetch a required environment variable.
    Raises a clear error immediately if it is missing.
    """
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(
            f"Missing required environment variable: '{key}'\n"
            f"Please add it to your .env file. See .env.example for reference."
        )
    return value


def _build_db_url() -> str:
    """
    Build the PostgreSQL connection URL from individual parts.

    WHY NOT A SINGLE DATABASE_URL STRING?
      Passwords often contain special characters like @, #, $.
      These break URL parsing. quote_plus() percent-encodes them
      safely - e.g. @ becomes %40.

    Required .env variables:
      DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
    """
    host     = _require("DB_HOST")
    port     = _require("DB_PORT")
    name     = _require("DB_NAME")
    user     = _require("DB_USER")
    password = quote_plus(_require("DB_PASSWORD"))
    return f"postgresql://{user}:{password}@{host}:{port}/{name}"


def _pdf_path(report_date: date) -> str:
    """
    Build a cross-platform temp path for the PDF.

    WHY tempfile.gettempdir()?
      /tmp/ works on Linux/Mac but does NOT exist on Windows.
      tempfile.gettempdir() returns the right folder on every OS:
        Windows -> C:\\Users\\<user>\\AppData\\Local\\Temp
        Linux   -> /tmp
        Mac     -> /var/folders/...
    """
    tmp = tempfile.gettempdir()
    return os.path.join(tmp, f"report_{report_date}.pdf")


@dataclass(frozen=True)#frozen = true means read only
class Config:
    """
    Immutable config object.
    frozen=True means nothing can accidentally overwrite a value at runtime.
    """
    db_url:         str
    gmail_user:     str
    gmail_password: str
    recipient:      str
    report_date:    date
    pdf_path:       str


def load_config() -> Config:
    """Build and return the Config object from environment variables."""
    report_date = date.today() - timedelta(days=1)

    return Config(
        db_url         = _build_db_url(),
        gmail_user     = _require("GMAIL_USER"),
        gmail_password = _require("GMAIL_APP_PASSWORD"),
        recipient      = _require("REPORT_RECIPIENT"),
        report_date    = report_date,
        pdf_path       = _pdf_path(report_date),
    )


# Module-level singleton - import this everywhere
config = load_config()