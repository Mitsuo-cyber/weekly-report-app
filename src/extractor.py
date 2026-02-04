import pdfplumber
import os

try:
    import pytesseract
    # Set Tesseract path for Windows
    if os.name == 'nt':
        tess_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        if os.path.exists(tess_path):
            pytesseract.pytesseract.tesseract_cmd = tess_path
    # On Linux (Streamlit Cloud), tesseract is usually in PATH, so no need to set cmd.
except ImportError:
    pytesseract = None
    print("WARNING: pytesseract import failed.")

if pytesseract:
    print("DEBUG: pytesseract module loaded.")
else:
    print("DEBUG: pytesseract module NOT loaded.")




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
        # Try splitting by ANY whitespace (e.g., '0.0 0' -> '0.0', '0.0\xa00' -> '0.0')
        parts = val_str.split()
        if len(parts) > 1:
            try:
                first_part = parts[0]
                return int(float(first_part))
            except: pass

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
        # Try splitting by ANY whitespace
        parts = val_str.split()
        if len(parts) > 1:
            try:
                first_part = parts[0]
                return float(first_part)
            except: pass

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
                        
                        # Skip garbage & duplicates
                        if not zone_name or zone_name in ['ブロック／業種', 'nan', 'None', ''] or '純売上高' in zone_name: continue
                        if 'SHO00200' in str(row): continue 
                        if '店別選択' in str(row): continue
                        
                        # Fix for Duplicate "Total" Rows:
                        # "准合計" (Jun-Gokei) often appears right before "軽井沢PSP計" with same numbers.
                        # Exclude it.
                        if '准合計' in zone_name: continue

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
                            # Use custom tessdata path if in project root (mainly for local Windows dev)
                            local_tessdata = os.path.join(os.getcwd(), 'tessdata')
                            if os.path.exists(local_tessdata) and os.name == 'nt':
                                os.environ['TESSDATA_PREFIX'] = local_tessdata
                            
                            # On Linux/Cloud, we rely on apt-installed tessdata
                            
                            # Rotation strategy: 180 first (common issue), then 0, then 90, 270
                            # Also often PDFs are landscape but processed as portrait.
                             
                            valid_ocr_text = None
                            
                            for angle in [0, 180, 90, 270]:
                                print(f"DEBUG: Trying OCR with rotation {angle}...")
                                if angle == 0:
                                    rotated_img = img
                                else:
                                    rotated_img = img.rotate(angle, expand=True) # expand=True to keep full image
                                    
                                temp_text = pytesseract.image_to_string(rotated_img, lang='jpn')
                                # print(f"DEBUG: Rotation {angle} text preview: {repr(temp_text[:200])}")
                                
                                # Check if it looks valid using clean text (ignoring spaces)
                                clean_temp = temp_text.replace(" ", "").replace("\n", "")
                                
                                if '純売上高' in clean_temp or '売上' in clean_temp or 'Sales' in clean_temp or 'ブロック' in clean_temp or '業種' in clean_temp:
                                    # print(f"DEBUG: Found valid headers at angle {angle}")
                                    valid_ocr_text = temp_text
                                    break
                            
                            if valid_ocr_text:
                                ocr_text = valid_ocr_text
                                print("OCR (Tesseract) success.")
                                print(f"DEBUG_OCR_TEXT: {repr(ocr_text[:500])}")
                            else:
                                print(f"DEBUG: No valid headers found in any rotation. Using last result.")
                                ocr_text = temp_text # Fallback to last attempt

                        except Exception as e:
                            print(f"Tesseract failed: {e}")
                    
                    # EasyOCR Removed to save memory on Cloud


                    # Parse OCR Output (Same logic as Strategy 2)
                    if ocr_text:
                        lines = ocr_text.split('\n')
                        header_found_in_text = False
                        
                        for line in lines:
                            # Cleanup common OCR garbage/spaces
                            line = line.strip()
                            if not line: continue
                            
                            # Robust header check
                            clean_line = line.replace(" ", "")
                            if '純売上高' in clean_line or '売上' in clean_line or 'ブロック' in clean_line: 
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
                                    
                                    # Helper to check if string is a number
                                    def is_valid_num(s):
                                        try:
                                            float(s)
                                            return True
                                        except:
                                            return False

                                    is_num = False
                                    final_val = clean_p
                                    
                                    # Case 1: Standard number
                                    if is_valid_num(clean_p):
                                        # Heuristic: If 1 dot and > 2 decimal places, assume it's a separator and strip it.
                                        # (Exceptions: small numbers? But likely safe for this report)
                                        if clean_p.count('.') == 1 and len(clean_p.split('.')[1]) > 2:
                                             temp = clean_p.replace('.', '')
                                             if is_valid_num(temp):
                                                 final_val = temp
                                        
                                        is_num = True
                                    
                                    # Case 2: OCR noise with dots as thousands separators (e.g. 3.720.970)
                                    # Only enters if NOT valid num (e.g. 2 dots)
                                    elif clean_p.count('.') > 1:
                                        # Try removing all dots (assume integer like 3.720.970)
                                        temp = clean_p.replace('.', '')
                                        if is_valid_num(temp):
                                            final_val = temp
                                            is_num = True
                                        else:
                                            # Try keeping only last dot (e.g. 2.240.39)
                                            # Split by dot, join all but last, then add dot back
                                            dot_parts = clean_p.split('.')
                                            temp2 = "".join(dot_parts[:-1]) + '.' + dot_parts[-1]
                                            if is_valid_num(temp2):
                                                final_val = temp2
                                                is_num = True

                                    # Case 3: Negative with triangle
                                    if not is_num and ('△' in p or '▲' in p):
                                        clean_p_neg = p.replace('△', '').replace('▲', '').replace(',', '').replace('%', '')
                                        # Apply same dot logic to negative
                                        if clean_p_neg.count('.') > 1:
                                             temp = clean_p_neg.replace('.', '')
                                             if is_valid_num(temp):
                                                 final_val = '-' + temp # Treat as negative
                                                 is_num = True
                                        elif clean_p_neg.count('.') == 1:
                                            parts_dot = clean_p_neg.split('.')
                                            if len(parts_dot[1]) > 2:
                                                temp = clean_p_neg.replace('.', '')
                                                if is_valid_num(temp):
                                                    final_val = '-' + temp
                                                    is_num = True
                                        
                                        if not is_num and is_valid_num(clean_p_neg):
                                            final_val = '-' + clean_p_neg
                                            is_num = True
                                    
                                    if is_num:
                                        valid_nums.insert(0, final_val)
                                    else:
                                        # Not a number.
                                        # If we already have our 2 target numbers, this is likely Zone text.
                                        if len(valid_nums) >= 2:
                                            zone_parts.insert(0, p)
                                
                                if len(valid_nums) >= 2:
                                    try:
                                        sls = 0
                                        s_yoy = 0.0
                                        cnt = 0
                                        c_yoy = 0.0
                                        
                                        if len(valid_nums) >= 4:
                                            c_yoy = parse_float(valid_nums[-1])
                                            cnt = parse_num(valid_nums[-2])
                                            s_yoy = parse_float(valid_nums[-3])
                                            sls = parse_num(valid_nums[-4])
                                        elif len(valid_nums) >= 2:
                                            # Assuming 2 numbers are Sales and YoY
                                            v1 = parse_float(valid_nums[0])
                                            v2 = parse_float(valid_nums[1])
                                            
                                            # Disambiguate Sales vs YoY using Magnitude
                                            # Sales is usually the larger absolute value (millions vs percentage)
                                            # Unless Sales is 0. 
                                            
                                            if abs(v1) > abs(v2):
                                                sls = int(v1)
                                                s_yoy = v2
                                            else:
                                                sls = int(v2)
                                                s_yoy = v1
                                                
                                            # Edge case: If both are small? Unlikely for "Sales" in this context.
                                            # But if v1 is 97.80 and v2 is 1.908.111 (parsed as 1908111), logic holds.

                                        # Zone Name reconstruction
                                        zn = parts[0]
                                        if zone_parts:
                                            zn = "".join(zone_parts)
                                        
                                        # Clean zone name
                                        zn = zn.replace(" ", "")
                                        # Remove common OCR trash from zone name start
                                        trash_chars = ['|', '!', ':', ';', '.']
                                        for tc in trash_chars:
                                            zn = zn.replace(tc, '')

                                        # Skip duplicated subtotal in OCR too
                                        if '准合計' in zn: continue

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
                # Return a specific error marker so app.py can detect it
                data.append({
                    'Date': date_str, 
                    'Zone': f'ERROR_UNREADABLE:{filename}',
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
            'Zone': f'ERROR_UNREADABLE:{filename}',
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
