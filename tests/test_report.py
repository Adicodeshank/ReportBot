"""
tests/test_report.py
--------------------
Unit tests for the PDF generation layer (app/report.py).

KEY CONCEPT - WHAT WE TEST HERE:
  We do NOT test what the PDF looks like visually.
  We test that:
    1. A file is actually created on disk
    2. The file is a valid PDF (starts with %PDF header)
    3. The file is not empty (has real content)
    4. It handles zero-data gracefully (holiday scenario)
    5. The returned path string is correct

  We use the REAL generate_report() with real FAKE data.
  No mocking needed here because PDF generation is pure
  computation - no network, no DB. It just takes a dict
  and writes a file. Fast and isolated by nature.

RUN:
  pytest tests/test_report.py -v
"""

import os
import pytest
from datetime import date
from unittest.mock import patch

from app.report import generate_report


# == Shared test data ==========================================================

FAKE_SUMMARY = {
    "report_date":      date(2026, 4, 20),
    "new_users":        3,
    "total_orders":     4,
    "total_revenue":    175.50,
    "avg_order_value":  103.88,
    "max_order_value":  200.00,
    "completed_orders": 2,
    "pending_orders":   1,
    "cancelled_orders": 1,
}

ZERO_SUMMARY = {
    "report_date":      date(2026, 4, 20),
    "new_users":        0,
    "total_orders":     0,
    "total_revenue":    0.0,
    "avg_order_value":  0.0,
    "max_order_value":  0.0,
    "completed_orders": 0,
    "pending_orders":   0,
    "cancelled_orders": 0,
}


# == Tests for generate_report() ===============================================

class TestGenerateReport:

    def test_returns_string_path(self, tmp_path):
        """
        WHAT:  generate_report() must return a string (the PDF file path).
        WHY:   send_report() in emailer.py receives this return value
               and passes it to open(). If it is None or wrong type,
               the email step crashes immediately.

        tmp_path is a pytest built-in fixture that gives us a clean
        temporary directory for each test. We redirect the PDF there
        so tests never write to the real filesystem permanently.
        """
        fake_pdf_path = str(tmp_path / "test_report.pdf")

        with patch("app.report.config") as mock_config:
            mock_config.pdf_path    = fake_pdf_path
            mock_config.report_date = date(2026, 4, 20)
            result = generate_report(FAKE_SUMMARY)

        assert isinstance(result, str), "generate_report() must return a string path"

    def test_file_is_created(self, tmp_path):
        """
        WHAT:  A PDF file must actually exist on disk after the call.
        WHY:   The most basic contract. If no file is created,
               the email attachment step raises FileNotFoundError.
        """
        fake_pdf_path = str(tmp_path / "test_report.pdf")

        with patch("app.report.config") as mock_config:
            mock_config.pdf_path    = fake_pdf_path
            mock_config.report_date = date(2026, 4, 20)
            generate_report(FAKE_SUMMARY)

        assert os.path.exists(fake_pdf_path), \
            "PDF file was not created on disk"

    def test_file_is_not_empty(self, tmp_path):
        """
        WHAT:  The PDF file must have real content (size > 0 bytes).
        WHY:   An empty file would be created if fpdf2 crashes mid-render
               but still calls output(). The email would attach a
               0-byte PDF that cannot be opened. Embarrassing.
        """
        fake_pdf_path = str(tmp_path / "test_report.pdf")

        with patch("app.report.config") as mock_config:
            mock_config.pdf_path    = fake_pdf_path
            mock_config.report_date = date(2026, 4, 20)
            generate_report(FAKE_SUMMARY)

        file_size = os.path.getsize(fake_pdf_path)
        assert file_size > 1000, \
            f"PDF is suspiciously small ({file_size} bytes) - likely corrupt"

    def test_file_is_valid_pdf(self, tmp_path):
        """
        WHAT:  The file must start with the PDF magic header '%PDF'.
        WHY:   Every valid PDF file starts with the bytes '%PDF-'.
               If the file exists but is not a real PDF, email clients
               will refuse to open it or show a blank document.

        This is called a 'magic bytes' check - a fast way to verify
        file format without parsing the entire file.
        """
        fake_pdf_path = str(tmp_path / "test_report.pdf")

        with patch("app.report.config") as mock_config:
            mock_config.pdf_path    = fake_pdf_path
            mock_config.report_date = date(2026, 4, 20)
            generate_report(FAKE_SUMMARY)

        with open(fake_pdf_path, "rb") as f:
            header = f.read(4)

        assert header == b"%PDF", \
            f"File does not start with PDF header. Got: {header}"

    def test_handles_zero_data(self, tmp_path):
        """
        WHAT:  generate_report() must not crash when all values are zero.
        WHY:   Holiday / outage scenario. A zero-data report is still
               a valid report. The bot must send it without crashing.
               The bar chart section has a guard for total_orders == 0
               but this test makes sure it actually works.
        """
        fake_pdf_path = str(tmp_path / "zero_report.pdf")

        with patch("app.report.config") as mock_config:
            mock_config.pdf_path    = fake_pdf_path
            mock_config.report_date = date(2026, 4, 20)

            try:
                generate_report(ZERO_SUMMARY)
                created = os.path.exists(fake_pdf_path)
            except Exception as e:
                pytest.fail(f"generate_report() crashed on zero data: {e}")

        assert created, "PDF was not created for zero-data summary"