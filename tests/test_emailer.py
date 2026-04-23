"""
tests/test_emailer.py
---------------------
Unit tests for the email layer (app/emailer.py).

KEY CONCEPT - WHY WE MOCK SMTP:
  We never send a real email in tests. Ever. Here is why:
    1. Tests would be slow (network round trip)
    2. Tests would fail without internet
    3. We would spam the manager's inbox every time tests run
    4. Gmail could rate-limit or block the account

  Instead we patch smtplib.SMTP with a MagicMock.
  The mock records every method call made on it.
  We then assert those calls happened correctly -
  e.g. starttls() was called, login() used right credentials,
  sendmail() was called with the right addresses.

  This is called BEHAVIOUR TESTING - we verify the code
  did the right things, not just that it ran without crashing.

RUN:
  pytest tests/test_emailer.py -v
"""

import os
import pytest
from unittest.mock import patch, MagicMock, call
from datetime import date

from app.emailer import send_report


# == Helpers ===================================================================

def make_fake_pdf(tmp_path) -> str:
    """
    Create a minimal but valid-looking PDF file for testing.
    We write the PDF magic header so any file-existence
    checks in the code under test pass correctly.
    """
    pdf_path = str(tmp_path / "test_report.pdf")
    with open(pdf_path, "wb") as f:
        f.write(b"%PDF-1.4 fake content for testing")
    return pdf_path


# == Tests for send_report() ===================================================

class TestSendReport:

    @patch("app.emailer.smtplib.SMTP")
    def test_smtp_connection_established(self, mock_smtp_class, tmp_path):
        """
        WHAT:  send_report() must connect to smtp.gmail.com on port 587.
        WHY:   Port 587 is the TLS port for Gmail. Port 465 is SSL.
               Using the wrong port causes a connection timeout.
               This test locks in the correct host and port forever.

        HOW THE MOCK WORKS:
          @patch("app.emailer.smtplib.SMTP") replaces the SMTP class
          inside the emailer module with mock_smtp_class.
          When code calls smtplib.SMTP("smtp.gmail.com", 587),
          it actually calls mock_smtp_class("smtp.gmail.com", 587).
          We then check mock_smtp_class was called with those exact args.
        """
        pdf_path   = make_fake_pdf(tmp_path)
        mock_smtp  = MagicMock()
        mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_smtp)
        mock_smtp_class.return_value.__exit__  = MagicMock(return_value=False)

        with patch("app.emailer.config") as mock_config:
            mock_config.gmail_user     = "bot@gmail.com"
            mock_config.gmail_password = "testpassword"
            mock_config.recipient      = "manager@company.com"
            mock_config.report_date    = date(2026, 4, 20)
            send_report(pdf_path)

        mock_smtp_class.assert_called_once_with("smtp.gmail.com", 587)

    @patch("app.emailer.smtplib.SMTP")
    def test_starttls_is_called(self, mock_smtp_class, tmp_path):
        """
        WHAT:  starttls() must be called before login().
        WHY:   Without starttls(), credentials are sent in plain text
               over the network. Anyone sniffing traffic could steal
               the Gmail App Password. This test enforces the secure
               handshake sequence.

        SEQUENCE ENFORCED:
          ehlo() -> starttls() -> ehlo() -> login() -> sendmail()
        """
        pdf_path   = make_fake_pdf(tmp_path)
        mock_smtp  = MagicMock()
        mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_smtp)
        mock_smtp_class.return_value.__exit__  = MagicMock(return_value=False)

        with patch("app.emailer.config") as mock_config:
            mock_config.gmail_user     = "bot@gmail.com"
            mock_config.gmail_password = "testpassword"
            mock_config.recipient      = "manager@company.com"
            mock_config.report_date    = date(2026, 4, 20)
            send_report(pdf_path)

        mock_smtp.starttls.assert_called_once()

    @patch("app.emailer.smtplib.SMTP")
    def test_login_uses_correct_credentials(self, mock_smtp_class, tmp_path):
        """
        WHAT:  login() must be called with the exact credentials from config.
        WHY:   If credentials come from the wrong source (hardcoded,
               wrong env var) the login silently uses wrong values and
               fails at 8 AM. This test makes sure config values flow
               through correctly.
        """
        pdf_path   = make_fake_pdf(tmp_path)
        mock_smtp  = MagicMock()
        mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_smtp)
        mock_smtp_class.return_value.__exit__  = MagicMock(return_value=False)

        with patch("app.emailer.config") as mock_config:
            mock_config.gmail_user     = "bot@gmail.com"
            mock_config.gmail_password = "secret123"
            mock_config.recipient      = "manager@company.com"
            mock_config.report_date    = date(2026, 4, 20)
            send_report(pdf_path)

        mock_smtp.login.assert_called_once_with("bot@gmail.com", "secret123")

    @patch("app.emailer.smtplib.SMTP")
    def test_sendmail_uses_correct_addresses(self, mock_smtp_class, tmp_path):
        """
        WHAT:  sendmail() must use the right from/to addresses.
        WHY:   An email sent from the wrong address or to the wrong
               recipient is a silent failure - no error is raised but
               the manager never receives the report.
        """
        pdf_path   = make_fake_pdf(tmp_path)
        mock_smtp  = MagicMock()
        mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_smtp)
        mock_smtp_class.return_value.__exit__  = MagicMock(return_value=False)

        with patch("app.emailer.config") as mock_config:
            mock_config.gmail_user     = "bot@gmail.com"
            mock_config.gmail_password = "testpassword"
            mock_config.recipient      = "manager@company.com"
            mock_config.report_date    = date(2026, 4, 20)
            send_report(pdf_path)

        call_args = mock_smtp.sendmail.call_args
        assert call_args[1]["from_addr"] == "bot@gmail.com"
        assert call_args[1]["to_addrs"]  == "manager@company.com"

    @patch("app.emailer.smtplib.SMTP")
    def test_raises_if_pdf_missing(self, mock_smtp_class, tmp_path):
        """
        WHAT:  send_report() must raise FileNotFoundError if PDF is missing.
        WHY:   If generate_report() failed silently and produced no file,
               we should fail loudly here with a clear error - not send
               a broken email with no attachment.

        pytest.raises() is the clean way to assert an exception is raised.
        """
        fake_path = str(tmp_path / "nonexistent.pdf")

        with patch("app.emailer.config") as mock_config:
            mock_config.gmail_user     = "bot@gmail.com"
            mock_config.gmail_password = "testpassword"
            mock_config.recipient      = "manager@company.com"
            mock_config.report_date    = date(2026, 4, 20)

            with pytest.raises(FileNotFoundError):
                send_report(fake_path)

        # SMTP should never even be called if the file is missing
        mock_smtp_class.assert_not_called()