import pdfplumber
import pandas as pd
import glob
import os
import re

def extract_from_pdf(pdf_file_obj, filename=None):
    """
    Extracts data from a PDF file object (or path).
    """
    if filename is None:
        filename = "Unknown"
        if isinstance(pdf_file_obj, str):
            filename = os.path.basename(pdf_file_obj)

    print(f"Processing {filename}...")
    
    # Extract date from filename (e.g., 20260126)
    date_match = re.search(r'202\d{5}', filename)
    if date_match:
        date_str = date_match.group(0)
    else:
        date_str = "Unknown"

    data = []
    
    try:
        with pdfplumber.open(pdf_file_obj) as pdf:
            # Assume data is on the first page
            if not pdf.pages:
                 print(f"No pages in {filename}")
                 return None
                 
            page = pdf.pages[0]
            table = page.extract_table()

            if not table:
                print(f"No table found in {filename}")
                return None

            for row in table:
                # Clean row values (handle None)
                row = [str(x).replace(',', '').replace('None', '') if x is not None else '' for x in row]
                
                # Skip empty rows or rows with no useful data
                if len(row) < 6:
                    continue
                    
                zone_name = row[0]
                
                # Skip Header Rows
                if zone_name in ['ブロック／業種', '', 'nan']:
                    continue
                
                # Skip "Karuizawa PSP Type" as requested (duplicates of Grand Total)
                if '軽井沢ＰＳＰ' in zone_name:
                    continue

                # Skip "Store Selection: Karuizawa PSP" headers appearing in data
                if '軽井沢' in zone_name and '店別選択' in str(row):
                    continue

                # Standardize numbers
                def parse_num(val):
                    try:
                        return int(float(val))
                    except:
                        return 0
                
                def parse_float(val):
                    try:
                        return float(val)
                    except:
                        return 0.0

                # Map Columns
                # 0: Zone, 1: Tsubo(Drop), 2: Sales, 3: Sales YoY, 4: Count, 5: Count YoY
                try:
                    sales = parse_num(row[2])
                    sales_yoy = parse_float(row[3])
                    count = parse_num(row[4])
                    count_yoy = parse_float(row[5])
                except IndexError:
                    continue

                entry = {
                    'Date': date_str,
                    'Zone': zone_name,
                    'Sales': sales,
                    'Sales_YoY': sales_yoy,
                    'Count': count,
                    'Count_YoY': count_yoy
                }
                data.append(entry)

        df = pd.DataFrame(data)
        return df
    except Exception as e:
        print(f"Error processing {filename}: {e}")
        return pd.DataFrame()

def process_all_pdfs(input_dir):
    pdf_files = glob.glob(os.path.join(input_dir, "*.pdf"))
    all_data = []
    
    for pdf_file in pdf_files:
        df = extract_from_pdf(pdf_file)
        if df is not None and not df.empty:
            all_data.append(df)
            
    if all_data:
        final_df = pd.concat(all_data, ignore_index=True)
        return final_df
    else:
        return pd.DataFrame()
