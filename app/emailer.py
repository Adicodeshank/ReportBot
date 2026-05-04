"""
emailer.py
----------
Sends the generated PDF report via Gmail SMTP.

RESPONSIBILITIES:
  - Build a professional email (subject, body, attachment)
  - Connect to Gmail SMTP securely via TLS
  - Attach the PDF and deliver it to the recipient

THIS FILE KNOWS NOTHING ABOUT:
  - The database (no imports from database.py)
  - PDF generation (receives only a file path string)

USAGE:
  from app.emailer import send_report
  send_report("/tmp/report_2026-04-19.pdf")

HOW GMAIL SMTP WORKS:
  1. Connect to smtp.gmail.com on port 587
  2. Upgrade connection to TLS via STARTTLS (encrypted tunnel)
  3. Login with Gmail address + App Password
  4. Send the MIME email object
  5. Connection closes automatically (context manager)
"""

import os
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase #Multipurpose Internet Mail Extension 
from email.mime.text import MIMEText
from email import encoders
from pathlib import Path

from app.config import config

log = logging.getLogger(__name__)

# Gmail SMTP settings - these never change for Gmail
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587              # 587 = TLS 
# Transport layer security 

def _build_subject() -> str:
    """
    Build the email subject line.
    Formatted so it sorts cleanly in an inbox by date.
    Example: "Daily Report | 19 April 2026"
    """
    return f"Daily Report | {config.report_date.strftime('%d %B %Y')}" # d for day of month b for month in english y for year 
#  %A is sor weekday like monday

def _build_body() -> str:
    """
    Build the plain-text email body.
    Kept intentionally short - the data is in the PDF attachment.
    """
    return f"""Hello,

Please find attached the automated daily business report for {config.report_date.strftime('%d %B %Y')}.

Report highlights are inside the PDF:
  - New user signups
  - Total orders and revenue
  - Order status breakdown (completed / pending / cancelled)

This report was generated and sent automatically at 8:00 AM.
No action is required on this email.

Regards,
Report Bot
"""


def _attach_pdf(msg: MIMEMultipart, pdf_path: str) -> None:
    """
    Attach the PDF file to the email message object.

    HOW MIME ATTACHMENTS WORK:
      Email cannot carry binary files directly - everything must be text.
      MIMEBase + encode_base64 converts the binary PDF into base64 text
      that email servers can safely transmit. The receiving email client
      decodes it back to a PDF automatically.

    Args:
        msg:      The email message object to attach the PDF to
        pdf_path: Absolute path to the PDF file on disk
    """
    path = Path(pdf_path)

    if not path.exists():
        raise FileNotFoundError(
            f"PDF not found at: {pdf_path}\n"
            f"Make sure generate_report() ran successfully before send_report()."
        )

# with blocks do not create their own scope.
    with open(path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())#part becomes the local variable for _attach_pdf function 

    # Encode binary content as base64 so it survives email transmission
    encoders.encode_base64(part)#turns your PDF into a text string so it doesn't get corrupted during the journey.

    #==========================================
    # ==========================
    """
        Content-Disposition is a specific MIME header that tells the receiving email client (like Gmail, Outlook, or Apple Mail) exactly how to present the attached file to the user.

        attachment means => attach this pdf but pdf should not be in body 
    """
    part.add_header(
        "Content-Disposition",
        f'attachment; filename="report_{config.report_date}.pdf"',
    )

    msg.attach(part)
    log.info(f"PDF attached: {path.name} ({path.stat().st_size / 1024:.1f} KB)")


def _build_message(pdf_path: str) -> MIMEMultipart:
    """
    Assemble the full MIME email object:
      - Headers (From, To, Subject)
      - Plain text body
      - PDF attachment

    WHY MIMEMultipart?
      A plain MIMEText can only carry text.
      MIMEMultipart is a container that holds multiple parts -
      text body + binary attachments - in one email object.
    """
    msg = MIMEMultipart()
    msg["From"]    = config.gmail_user
    msg["To"]      = config.recipient
    msg["Subject"] = _build_subject()

    # Attach the body text first, then the PDF
    msg.attach(MIMEText(_build_body(), "plain"))
    _attach_pdf(msg, pdf_path)

    return msg


def send_report(pdf_path: str) -> None:
    """
    Send the daily report email with the PDF attached.

    WHY smtplib AND NOT A THIRD-PARTY LIBRARY?
      smtplib is Python's built-in SMTP library - zero extra dependencies.
      For simple transactional email like this, it is more than enough.
      Libraries like sendgrid or mailgun add cost and complexity
      that is not needed here.

    Args:
        pdf_path: Absolute path to the generated PDF file

    Raises:
        FileNotFoundError: if the PDF does not exist
        smtplib.SMTPAuthenticationError: if Gmail credentials are wrong
        smtplib.SMTPException: for any other SMTP-level failure
    """
    log.info(f"Preparing email to {config.recipient}...")

    msg = _build_message(pdf_path)

    # smtplib.SMTP as a context manager - closes connection automatically
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:

            # Step 1: Introduce ourselves to the server
            server.ehlo()

            # Step 2: Upgrade to encrypted TLS tunnel
            # After this point everything is encrypted - login is safe
            server.starttls()
            server.ehlo()   # re-introduce after TLS upgrade

            # Step 3: Login with Gmail App Password
            server.login(config.gmail_user, config.gmail_password)
            log.info("Gmail SMTP login successful.")

            # Step 4: Send the email
            server.sendmail(
                from_addr = config.gmail_user,
                to_addrs  = config.recipient,
                msg       = msg.as_string(),
            )

        log.info(f"Email sent successfully to {config.recipient}.")

    except smtplib.SMTPAuthenticationError:
        log.error(
            "Gmail authentication failed.\n"
            "Make sure GMAIL_APP_PASSWORD in your .env is a Gmail App Password\n"
            "(16-character code from myaccount.google.com/apppasswords),\n"
            "NOT your regular Gmail login password."
        )
        raise

    except smtplib.SMTPException as e:
        log.error(f"SMTP error while sending email: {e}")
        raise