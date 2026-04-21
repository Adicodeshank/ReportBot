"""
test_phase3.py
--------------
Tests the full pipeline end to end:
  DB -> summary dict -> PDF -> Email

Run it:
  python test_phase3.py

What to expect:
  - PDF gets generated in your temp folder
  - Email arrives in the recipient inbox within ~30 seconds
  - Check spam folder if it does not appear in inbox

Prerequisites:
  - .env has real GMAIL_USER and GMAIL_APP_PASSWORD
  - Gmail App Password generated at myaccount.google.com/apppasswords
"""

import logging

logging.basicConfig(
    level  = logging.INFO,
    format = "%(levelname)s  %(message)s"
)

from app.database import fetch_daily_summary, get_summary_dict
from app.report   import generate_report
from app.emailer  import send_report

print("=" * 55)
print("  PHASE 3 TEST -- Full Pipeline")
print("  DB -> PDF -> Email")
print("=" * 55)

# Step 1: Fetch from DB
print("\n[1/3] Fetching data from database...")
df      = fetch_daily_summary()
summary = get_summary_dict(df)
print(f"      Orders found: {summary['total_orders']}")
print(f"      Revenue:      INR {summary['total_revenue']:,.2f}")

# Step 2: Generate PDF
print("\n[2/3] Generating PDF...")
pdf_path = generate_report(summary)
print(f"      Saved to: {pdf_path}")

# Step 3: Send email
print("\n[3/3] Sending email...")
send_report(pdf_path)

print("\n" + "=" * 55)
print("  Done! Check your inbox now.")
print("  (Check spam if it does not appear in 1 minute)")
print("=" * 55)