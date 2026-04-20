from app.database import fetch_daily_summary, get_summary_dict

print("--- Fetching data from DB ---")
df = fetch_daily_summary()

print("\n--- Raw DataFrame ---")
print(df)

print("\n--- Summary Dictionary ---")
summary = get_summary_dict(df)
for key, value in summary.items():
    print(f"  {key}: {value}")