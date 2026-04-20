"""
test_phase2.py
--------------
Run this to test Phase 2 (PDF generation) end to end.

What it does:
  1. Fetches real data from your PostgreSQL database
  2. Passes the summary dict into generate_report()
  3. Saves the PDF and prints the file path

Run it:
  python test_phase2.py

Then open the PDF path it prints to see your report.
"""

import os
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

from app.database import fetch_daily_summary, get_summary_dict
from app.report import generate_report

print("=" * 50)
print("  PHASE 2 TEST — PDF Generation")
print("=" * 50)

# Step 1: get data from DB
print("\n[1/2] Fetching data from database...")
df      = fetch_daily_summary()
summary = get_summary_dict(df)

print("      Summary dict:")
for k, v in summary.items():
    print(f"        {k}: {v}")

# Step 2: generate PDF
print("\n[2/2] Generating PDF...")
# print(summary)
pdf_path = generate_report(summary)

print(f"\n✓ Done! PDF saved to:\n  {pdf_path}")
print("\nOpen that file to see your report.")
print("=" * 50)