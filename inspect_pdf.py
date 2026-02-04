import pdfplumber
import pandas as pd

pdf_path = "【ゾーン別】売上実績20260126.pdf"

print(f"Analyzing {pdf_path}...")

with pdfplumber.open(pdf_path) as pdf:
    for i, page in enumerate(pdf.pages):
        print(f"--- Page {i+1} ---")
        
        # Extract text to see general layout
        text = page.extract_text()
        print("Text Preview (First 200 chars):")
        print(text[:200])
        print("-" * 20)

        # Extract tables
        tables = page.extract_tables()
        print(f"Found {len(tables)} tables.")
        
        for j, table in enumerate(tables):
            print(f"Table {j+1}:")
            df = pd.DataFrame(table)
            print(df.head()) # Show first few rows to understand headers
            print(f"Shape: {df.shape}")
            
            # Save to checking CSV (optional, but good for debugging if needed later)
            # df.to_csv(f"debug_page{i+1}_table{j+1}.csv", index=False, header=False)
