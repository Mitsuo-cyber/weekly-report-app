import pdfplumber
import pandas as pd
import glob
import os
import re

def parse_num(val, zone_name="Unknown"):
    val_str = str(val).strip()
    # Handle negative indicators
    if '△' in val_str or '▲' in val_str:
        val_str = '-' + val_str.replace('△', '').replace('▲', '')
    
    # Handle explicit zero indicators if any (though usually just 0)
    if val_str == '-':
        return 0

    try:
        return int(float(val_str))
    except (ValueError, TypeError):
        if val_str and val_str not in ['', 'nan', 'None']:
             print(f"[WARNING] Could not parse number: '{val}' (Zone: {zone_name})")
        return 0

def parse_float(val, zone_name="Unknown"):
    val_str = str(val).strip()
    if '△' in val_str or '▲' in val_str:
        val_str = '-' + val_str.replace('△', '').replace('▲', '')
    
    if val_str == '-':
        return 0.0

    try:
        return float(val_str)
    except (ValueError, TypeError):
        if val_str and val_str not in ['', 'nan', 'None']:
             print(f"[WARNING] Could not parse float: '{val}' (Zone: {zone_name})")
        return 0.0

def extract_from_pdf(pdf_file_obj, filename=None):
    """
    Extracts data from a PDF file object (or path).
    Modified to be robust against header shifts (ignores SHO00200 dependency).
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
            if not pdf.pages:
                print(f"No pages in {filename}")
                return None
                 
            page = pdf.pages[0]
            
            # --- STRATEGY 1: Robust Table Extraction (Text-based) ---
            # Using "text" strategy is better for reports where lines might be missing or shifted
            table = page.extract_table(table_settings={
                "vertical_strategy": "text", 
                "horizontal_strategy": "text",
                "intersection_y_tolerance": 10
            })
            
            # Fallback to default if text strategy returns nothing
            if not table:
                print(f"Text strategy failed for {filename}. Trying default...")
                table = page.extract_table()

            # Process the table
            if table:
                print(f"Table extracted from {filename}. Searching for Header '純売上高'...")
                header_row_idx = -1
                col_map = {}
                
                # 1. Find the Header Row (Anchor)
                for i, row in enumerate(table):
                    # Filter None values for safe checking
                    row_text = [str(x).replace('\n', '') if x is not None else '' for x in row]
                    row_str = "".join(row_text)
                    
                    if '純売上高' in row_text or '純売上高' in row_str:
                        header_row_idx = i
                        print(f"Header found at row {i} in {filename}")
                        
                        # Dynamic Column Mapping
                        try:
                            # Try to find index of key columns
                            for idx, col in enumerate(row_text):
                                if '純売上高' in col:
                                    col_map['Sales'] = idx
                                if '客数' in col:
                                    col_map['Count'] = idx
                            
                            # Fallbacks if exact match failed but row was found
                            if 'Sales' not in col_map: col_map['Sales'] = 2
                            if 'Count' not in col_map: col_map['Count'] = 4
                            
                            # YoY columns usually follow the metrics
                            col_map['Sales_YoY'] = col_map['Sales'] + 1
                            col_map['Count_YoY'] = col_map['Count'] + 1
                            
                        except Exception as e:
                            print(f"Mapping error: {e}")
                            # Default fallback
                            col_map = {'Sales': 2, 'Sales_YoY': 3, 'Count': 4, 'Count_YoY': 5}
                        break
                
                if header_row_idx == -1:
                    print(f"WARNING: Header '純売上高' not found in Table of {filename}. Skipping table method.")
                else:
                    # 2. Extract Data Rows (Loop starting AFTER header)
                    for i, row in enumerate(table):
                        if i <= header_row_idx: continue
                        
                        row = [str(x).replace(',', '').replace('None', '') if x is not None else '' for x in row]
                        
                        # Basic validation: Row must have enough columns and a valid Zone name
                        if len(row) < 3: continue
                        
                        zone_name = row[0]
                        
                        # Skip garbage rows
                        if not zone_name or zone_name in ['ブロック／業種', 'nan', 'None', ''] or '純売上高' in zone_name: continue
                        if 'SHO00200' in str(row): continue 
                        if '店別選択' in str(row): continue

                        try:
                            # Safely get values using the map
                            sales_idx = col_map.get('Sales', 2)
                            count_idx = col_map.get('Count', 4)
                            
                            # Boundary check
                            if sales_idx >= len(row) or count_idx >= len(row): continue

                            sales = parse_num(row[sales_idx], zone_name)
                            # If sales is 0, it might be a garbage row, but we keep it if zone is valid
                            
                            sales_yoy = 0.0
                            if col_map.get('Sales_YoY') < len(row):
                                sales_yoy = parse_float(row[col_map['Sales_YoY']], zone_name)
                                
                            count = parse_num(row[count_idx], zone_name)
                            
                            count_yoy = 0.0
                            if col_map.get('Count_YoY') < len(row):
                                count_yoy = parse_float(row[col_map['Count_YoY']], zone_name)
                            
                            if zone_name and zone_name != "Unknown":
                                data.append({
                                    'Date': date_str, 'Zone': zone_name,
                                    'Sales': sales, 'Sales_YoY': sales_yoy,
                                    'Count': count, 'Count_YoY': count_yoy
                                })
                        except Exception as e:
                            # print(f"Row parse error: {e}") 
                            continue
                            
            # --- TEXT FALLBACK (Only if table method yielded no data) ---
            if not data:
                print(f"Table extraction yielded no data for {filename}. Trying RAW TEXT fallback...")
                text = page.extract_text()
                if text:
                    lines = text.split('\n')
                    header_found_in_text = False
                    
                    for line in lines:
                        # Find header first to start "listening"
                        if '純売上高' in line and '客数' in line:
                            header_found_in_text = True
                            continue
                        
                        # Only parse if we have seen the header OR if the line looks like data (heuristic)
                        if header_found_in_text:
                            parts = line.split()
                            # Heuristic: Valid data line usually has: ZoneName Number Number ...
                            if len(parts) >= 5:
                                try:
                                    # Attempt to parse from the end of the line (usually safer)
                                    # Expected: [Zone] ... [Sales] [SalesYoY] [Count] [CountYoY]
                                    c_yoy = parse_float(parts[-1])
                                    cnt = parse_num(parts[-2])
                                    s_yoy = parse_float(parts[-3])
                                    sls = parse_num(parts[-4])
                                    
                                    # Zone is whatever is left at the start
                                    zn = parts[0] 
                                    
                                    if sls > 0 or cnt > 0: # Only add if it looks like real data
                                        data.append({
                                            'Date': date_str, 'Zone': zn,
                                            'Sales': sls, 'Sales_YoY': s_yoy,
                                            'Count': cnt, 'Count_YoY': c_yoy
                                        })
                                except:
                                    pass

            return pd.DataFrame(data)

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
