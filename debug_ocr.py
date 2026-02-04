
import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'src'))
from extractor import extract_from_pdf
import pandas as pd

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

target_file = "【ゾーン別】売上実績20260127.pdf"

if os.path.exists(target_file):
    print(f"Testing extraction on {target_file}...")
    df = extract_from_pdf(target_file)
    
    if df is not None and not df.empty:
        print("\n--- Extraction Result ---")
        print(df)
        print("\n--- End of Result ---")
    else:
        print("\n[!] No data extracted.")
else:
    print(f"File {target_file} not found.")
