import pandas as pd
from src.extractor import process_all_pdfs
from src.aggregator import calculate_weekly_summary

print("Starting Verification Pipeline...")

# 1. Extract
print("Extracting data from PDFs...")
daily_df = process_all_pdfs(".")
print(f"Extracted {len(daily_df)} rows.")

# 2. Aggregate
print("Calculating Weekly Summary...")
summary_df = calculate_weekly_summary(daily_df)

# 3. Display
print("\n--- Weekly Summary ---")
print(summary_df.to_string())

# 4. Check for 'Total'
print("\n--- Manual Check ---")
total_row = summary_df[summary_df['Zone'] == '【総合計】']
if not total_row.empty:
    print("Grand Total found:")
    print(total_row.to_string())
else:
    print("WARNING: Grand Total ('【総合計】') not found in summary.")

print("\nPipeline Verification Complete.")
