
import pdfplumber
import pandas as pd
import glob
import os
import re
import sys

# Import the functions from src/extractor.py
# Assuming src is in the python path or same directory or I can just copy paste the logic to be safe and modify it for debugging
# Let's import to check the actual behavior of the existing code first.
sys.path.append(os.path.join(os.getcwd(), 'src'))
try:
    from extractor import extract_from_pdf, parse_num
except ImportError:
    # If import fails, I'll copy paste the function here to ensure I'm testing the logic
    pass

def debug_process():
    pdf_files = [
        "【ゾーン別】売上実績20260126.pdf",
        "【ゾーン別】売上実績20260127.pdf",
        "【ゾーン別】売上実績20260128.pdf",
        "【ゾーン別】売上実績20260129.pdf",
        "【ゾーン別】売上実績20260130.pdf",
        "【ゾーン別】売上実績20260131.pdf",
        "【ゾーン別】売上実績20260201.pdf"
    ]
    
    current_dir = os.getcwd()
    all_data = []

    for filename in pdf_files:
        filepath = os.path.join(current_dir, filename)
        if not os.path.exists(filepath):
            print(f"File not found: {filename}")
            continue
            
        print(f"--- Debugging {filename} ---")
        try:
             # direct call to extract_from_pdf from imported module
             df = extract_from_pdf(filepath)
             if df is not None and not df.empty:
                 # Check for '総合計' (Grand Total) in Zone
                 total_row = df[df['Zone'].str.contains('総合計', na=False)]
                 if not total_row.empty:
                     print(f"Found Total Row for {filename}:")
                     print(total_row[['Zone', 'Sales', 'Count']].to_string(index=False))
                     all_data.append(df)
                 else:
                     print(f"WARNING: No '総合計' row found in extraction for {filename}")
                     print("First 5 rows extracted:")
                     print(df.head().to_string())
             else:
                 print(f"FAILED: No data extracted from {filename}")
                 # Debug deeper if failed
                 with pdfplumber.open(filepath) as pdf:
                     if len(pdf.pages) > 0:
                         p0 = pdf.pages[0]
                         text = p0.extract_text()
                         print("Page 0 Text Snippet:")
                         print(text[:500])
                         table = p0.extract_table()
                         if table:
                             print("Table found but extraction logic might have filtered it out.")
                             print("First 3 rows of raw table:")
                             for row in table[:3]:
                                 print(row)
                         else:
                             print("No table structure detected on Page 0.")
        except Exception as e:
            print(f"Exception processing {filename}: {e}")

    if all_data:
        combined = pd.concat(all_data, ignore_index=True)
        # Filter for Grand Total rows only to sum check
        totals = combined[combined['Zone'].str.contains('総合計', na=False)]
        
        print("\n--- Summary of Daily Totals ---")
        print(totals[['Date', 'Zone', 'Sales', 'Count']].sort_values('Date'))
        
        total_sales = totals['Sales'].sum()
        total_count = totals['Count'].sum()
        
        print(f"\nAGGREGATED TOTAL SALES: {total_sales:,}")
        print(f"AGGREGATED TOTAL COUNT: {total_count:,}")
        
    else:
        print("No Valid Data Aggregated.")

if __name__ == "__main__":
    debug_process()
