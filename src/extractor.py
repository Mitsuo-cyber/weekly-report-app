import pdfplumber
import os

try:
    import pytesseract
    # Set Tesseract path for Windows
    if os.name == 'nt':
        tess_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        if os.path.exists(tess_path):
            pytesseract.pytesseract.tesseract_cmd = tess_path
except ImportError:
    pytesseract = None

try:
    import easyocr
except ImportError:
    easyocr = None

import numpy as np
import warnings

# Suppress easyocr warnings
warnings.filterwarnings("ignore", category=UserWarning)
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
    Tries default extraction first (best for valid tables), then falls back to text strategy.
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
            
            # --- STRATEGY 1: Default (Lines) - BEST for standard tables ---
            # Most files work best with this.
            table = page.extract_table()
            
            # --- STRATEGY 2: Text-based - Fallback for broken lines ---
            if not table:
                print(f"Default extraction failed for {filename}. Trying text strategy...")
                table = page.extract_table(table_settings={
                    "vertical_strategy": "text", 
                    "horizontal_strategy": "text",
                    "intersection_y_tolerance": 10
                })

            # Process the table (common logic)
            if table:
                print(f"Table extracted from {filename}. Searching for Header '純売上高'...")
                header_row_idx = -1
                col_map = {}
                
                # 1. Find the Header Row (Anchor)
                for i, row in enumerate(table):
                    row_text = [str(x).replace('\n', '') if x is not None else '' for x in row]
                    row_str = "".join(row_text)
                    
                    # Search for key header
                    if '純売上高' in row_text or '純売上高' in row_str:
                        header_row_idx = i
                        print(f"Header found at row {i} in {filename}")
                        
                        # Dynamic Column Mapping
                        try:
                            for idx, col in enumerate(row_text):
                                if '純売上高' in col and 'Sales' not in col_map:
                                    col_map['Sales'] = idx
                                if '客数' in col and 'Count' not in col_map:
                                    col_map['Count'] = idx
                            
                            # Fallbacks
                            if 'Sales' not in col_map: col_map['Sales'] = 2
                            if 'Count' not in col_map: col_map['Count'] = 4
                            col_map['Sales_YoY'] = col_map['Sales'] + 1
                            col_map['Count_YoY'] = col_map['Count'] + 1
                            
                        except Exception:
                            col_map = {'Sales': 2, 'Sales_YoY': 3, 'Count': 4, 'Count_YoY': 5}
                        break
                
                if header_row_idx == -1:
                    print(f"WARNING: Header '純売上高' not found in Table of {filename}. skipping.")
                else:
                    # 2. Extract Data Rows
                    for i, row in enumerate(table):
                        if i <= header_row_idx: continue
                        
                        row = [str(x).replace(',', '').replace('None', '') if x is not None else '' for x in row]
                        
                        # Basic validation
                        if len(row) < 3: continue
                        zone_name = row[0]
                        
                        # Skip garbage
                        if not zone_name or zone_name in ['ブロック／業種', 'nan', 'None', ''] or '純売上高' in zone_name: continue
                        if 'SHO00200' in str(row): continue 
                        if '店別選択' in str(row): continue

                        try:
                            sales_idx = col_map.get('Sales', 2)
                            count_idx = col_map.get('Count', 4)
                            
                            if sales_idx >= len(row) or count_idx >= len(row): continue

                            sales = parse_num(row[sales_idx], zone_name)


                            count = parse_num(row[count_idx], zone_name)
                            
                            sales_yoy = 0.0
                            if col_map.get('Sales_YoY') < len(row):
                                sales_yoy = parse_float(row[col_map['Sales_YoY']], zone_name)
                                
                            count_yoy = 0.0
                            if col_map.get('Count_YoY') < len(row):
                                count_yoy = parse_float(row[col_map['Count_YoY']], zone_name)
                            
                            if zone_name and zone_name != "Unknown":
                                data.append({
                                    'Date': date_str, 'Zone': zone_name,
                                    'Sales': sales, 'Sales_YoY': sales_yoy,
                                    'Count': count, 'Count_YoY': count_yoy
                                })
                        except Exception: continue
                            
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

            # --- STRATEGY 3: OCR Fallback (Image/Scan) ---
            if not data:
                print(f"Text extraction failed for {filename}. Trying OCR strategy...")
                try:
                    # Convert page to image
                    # resolution=300 is standard for OCR
                    img = page.to_image(resolution=300).original
                    
                    ocr_text = ""
                    
                    # Method A: Tesseract (Preferred if available)
                    if pytesseract:
                        try:
                            # Tesseract needs 'jpn' data. If not found, it might error or default to eng.
                            # We assume user might have it or we try.
                            # Use custom tessdata path if in project root
                            local_tessdata = os.path.join(os.getcwd(), 'tessdata')
                            if os.path.exists(local_tessdata):
                                os.environ['TESSDATA_PREFIX'] = local_tessdata
                            
                            ocr_text = pytesseract.image_to_string(img, lang='jpn')
                            print("OCR (Tesseract) success.")


                        except Exception as e:
                            print(f"Tesseract failed: {e}")
                    
                    # Method B: EasyOCR (Fallback if Tesseract fails/missing)
                    if not ocr_text and easyocr:
                        try:
                            print("Attempting EasyOCR (this may take a moment)...")
                            reader = easyocr.Reader(['ja', 'en'], gpu=False, verbose=False)
                            result = reader.readtext(np.array(img), detail=0)
                            ocr_text = "\n".join(result)
                            print("OCR (EasyOCR) success.")
                        except Exception as e:
                            print(f"EasyOCR failed: {e}")


                    # Parse OCR Output (Same logic as Strategy 2)
                    if ocr_text:
                        lines = ocr_text.split('\n')
                        header_found_in_text = False
                        
                        for line in lines:
                            # Cleanup common OCR garbage/spaces
                            line = line.strip()
                            if not line: continue
                            
                            if '純売上高' in line or '売上' in line: # Looser check for OCR
                                header_found_in_text = True
                                continue
                            
                            if header_found_in_text:
                                parts = line.split()
                                # OCR often splits numbers into parts (e.g. 1, 234 -> 1 234)
                                # This is a simplified parser assuming good OCR. 
                                # If OCR is messy, we might need regex.
                                
                                # Heuristic: scan for numbers at the end
                                valid_nums = []
                                zone_parts = []
                                
                                for p in reversed(parts):
                                    # remove commas and %
                                    clean_p = p.replace(',', '').replace('%', '')
                                    try:
                                        # is it a number?
                                        float(clean_p) 
                                        valid_nums.insert(0, clean_p)
                                    except:
                                        # matches negative like "A100" or triangle char?
                                        if '△' in p or '▲' in p:
                                            valid_nums.insert(0, p)
                                        else:
                                            # Not a number affecting, stop if we found enough numbers
                                            if len(valid_nums) >= 4:
                                                zone_parts.insert(0, p)
                                                # Break not strictly correct if zone has spaces, 
                                                # but we are iterating backwards.
                                                # Actually, better to just collect anything not num as zone
                                            else:
                                                 # if we haven't found 4 nums yet, and this isn't a num,
                                                 # it might be part of a broken number or noise.
                                                 pass
                                
                                if len(valid_nums) >= 4:
                                     # Last 4 are likely our target
                                     # [Sales] [SalesYoY] [Count] [CountYoY]
                                    try:
                                        c_yoy = parse_float(valid_nums[-1])
                                        cnt = parse_num(valid_nums[-2])
                                        s_yoy = parse_float(valid_nums[-3])
                                        sls = parse_num(valid_nums[-4])
                                        
                                        # Zone is everything else?
                                        # Re-read line to find zone text?
                                        # Simple heuristic: first token
                                        zn = parts[0]
                                        
                                        if sls > 0 or cnt > 0:
                                             data.append({
                                                'Date': date_str, 'Zone': zn,
                                                'Sales': sls, 'Sales_YoY': s_yoy,
                                                'Count': cnt, 'Count_YoY': c_yoy
                                            })
                                    except: pass

                except Exception as e:
                    print(f"OCR Strategy failed completely: {e}")


            # --- FINAL FALLBACK: Prevent App Error ---
            if not data:
                print(f"WARNING: Completely failed to extract data from {filename} (likely Image/Vector PDF). Returning placeholder.")
                # Return a single row with Date and 0 values so the app doesn't show "Format Error"
                data.append({
                    'Date': date_str, 
                    'Zone': '【読取不可】(画像PDFの可能性あり)',
                    'Sales': 0, 
                    'Sales_YoY': 0.0,
                    'Count': 0, 
                    'Count_YoY': 0.0
                })

            return pd.DataFrame(data)

    except Exception as e:
        print(f"Error processing {filename}: {e}")
        # Return placeholder on exception too
        return pd.DataFrame([{
            'Date': date_str if 'date_str' in locals() else "Unknown",
            'Zone': '【エラー】処理失敗',
            'Sales': 0, 'Sales_YoY': 0.0, 'Count': 0, 'Count_YoY': 0.0
        }])

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
