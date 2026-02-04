import streamlit as st
import pandas as pd
import io
import time
import json
import os
from src.extractor import extract_from_pdf
from src.aggregator import calculate_weekly_summary

st.set_page_config(page_title="売上PDF集計アプリ", layout="wide")

st.title("🗂️ 売上報告PDF 自動集計ツール")

# --- Manual Data Persistence ---
MANUAL_DATA_FILE = "manual_data.json"

def load_manual_data():
    if os.path.exists(MANUAL_DATA_FILE):
        try:
            with open(MANUAL_DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_manual_data(data):
    with open(MANUAL_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if 'manual_data' not in st.session_state:
    st.session_state['manual_data'] = load_manual_data()
# -------------------------------

# --- Authentication ---
AUTH_PASSWORD = st.secrets["AUTH_PASSWORD"]  # 簡易的なパスワード（後で変更可能）
password = st.sidebar.text_input("認証コードを入力してください", type="password")

if password != AUTH_PASSWORD:
    st.warning("👈 左側のメニューに認証コードを入力してください。")
    st.image("https://placehold.co/600x400?text=Please+Login", caption="Login Required")
    st.stop()  # Stop execution if password is wrong
# ----------------------


st.markdown("""
日次の売上PDFファイルをアップロードしてください（複数可）。
自動的に数値を読み取り、ブロック業種ごとの週次サマリーを作成します。
""")

@st.cache_data(ttl="2h")
def process_file_content(file_bytes, filename):
    """
    Cache the expensive OCR/extraction process.
    Pass file content as bytes to ensure proper hashing.
    """
    # Wrap bytes back into a file-like object for pdfplumber
    file_obj = io.BytesIO(file_bytes)
    return extract_from_pdf(file_obj, filename=filename)


uploaded_files = st.file_uploader("PDFファイルをここにドラッグ＆ドロップ", type="pdf", accept_multiple_files=True)

if uploaded_files:
    st.info(f"{len(uploaded_files)} 個のファイルを処理中...")
    
    extracted_data = [] # Raw extraction from PDFs
    
    progress_bar = st.progress(0)
    
    for i, file in enumerate(uploaded_files):
        # Streamlit file object works with pdfplumber
        # Pass bytes to cached function
        df = process_file_content(file.getvalue(), file.name)
        if df is not None and not df.empty:
            extracted_data.append(df)
        progress_bar.progress((i + 1) / len(uploaded_files))
        
    if extracted_data:
        raw_concatenated = pd.concat(extracted_data, ignore_index=True)
        
        # --- Error Handling & Validation ---
        # 1. Unreadable File Markers
        error_df_ocr = raw_concatenated[raw_concatenated['Zone'].str.contains('ERR:', na=False)].copy()
        
        # 2. Suspicious Data (Sales = 0) - likely misread or empty but valid PDF
        # We assume Sales=0 is impossible for a business day, as per user.
        warnings_df = raw_concatenated[
            (~raw_concatenated['Zone'].str.contains('ERR:', na=False)) & 
            (raw_concatenated['Sales'] == 0) &
            (raw_concatenated['Zone'].str.contains('軽井沢ＰＳＰ 計|総合計', na=False)) # Only check Total rows for strictness
        ].copy()
        
        # Combine errors
        unique_errors = []
        if not error_df_ocr.empty:
            for _, row in error_df_ocr.iterrows():
                fname = row['Zone'].split(':')[-1]
                unique_errors.append(f"📄 **{fname}** (読み取り失敗: {row['Date']})")
        
        if not warnings_df.empty:
             for _, row in warnings_df.iterrows():
                unique_errors.append(f"⚠️ **日付: {row['Date']}** (売上0円 - 誤検知の可能性あり)")

        # Filter out invalid rows from main data
        valid_df = raw_concatenated[
            (~raw_concatenated['Zone'].str.contains('ERR:', na=False)) & 
            (raw_concatenated['Sales'] > 0)
        ]
        
        # Explicit Error Display
        if unique_errors:
            st.error("⚠️ 以下のデータの読み取りに失敗、または内容に不備があります。手動でデータを修正してください。")
            for err in unique_errors:
                st.write(f"- {err}")
        
        # --- Manual Data Entry Form ---
        with st.expander("✍️ 手動データ入力 (読取失敗・修正用)", expanded=bool(unique_errors)):
            st.caption("読み取れなかった、または数値が正しくない日の「総合計」を入力してください。")
            
            with st.form("manual_entry_form"):
                col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
                m_date = col_m1.text_input("日付 (例: 20260201)", value="")
                m_sales = col_m2.number_input("純売上高", min_value=0, step=1000)
                m_sales_yoy = col_m3.number_input("売上前年比(%)", step=0.1)
                m_count = col_m4.number_input("客数", min_value=0, step=10)
                m_count_yoy = col_m5.number_input("客数前年比(%)", step=0.1)
                
                submitted = st.form_submit_button("データ保存/上書き")
                
                if submitted and m_date:
                    # Save into session state
                    new_entry = {
                        'Date': m_date,
                        'Zone': '【軽井沢ＰＳＰ 計】', # Manual entry is always treated as Total
                        'Sales': int(m_sales),
                        'Sales_YoY': float(m_sales_yoy),
                        'Count': int(m_count),
                        'Count_YoY': float(m_count_yoy)
                    }
                    st.session_state['manual_data'][m_date] = new_entry
                    save_manual_data(st.session_state['manual_data'])
                    st.success(f"{m_date} のデータを保存しました。")
                    st.rerun()

        # --- Merge Manual Data ---
        if st.session_state['manual_data']:
            manual_list = list(st.session_state['manual_data'].values())
            manual_df = pd.DataFrame(manual_list)
            
            # Strategy: If Manual Data exists for a Date, drop the Extracted Data for that Date (to prevent dupes/conflicts)
            manual_dates = set(manual_df['Date'].astype(str).str.strip())
            
            # Ensure Date is string matchable
            valid_df['Date'] = valid_df['Date'].astype(str).str.strip()
            
            # Filter out extracted rows that conflict with manual dates
            filtered_valid_df = valid_df[~valid_df['Date'].isin(manual_dates)]
            
            combined_df = pd.concat([filtered_valid_df, manual_df], ignore_index=True)
        else:
            combined_df = valid_df

        # --- Calculate Summary ---
        summary_df = calculate_weekly_summary(combined_df)
        
        st.success("集計完了！")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("📊 週次サマリー（業種別）")
            # Formatting for display
            display_df = summary_df.copy()
            
            # Handle potential empty data gracefully
            if not display_df.empty:
                try:
                    display_df['Sales'] = display_df['Sales'].apply(lambda x: f"{int(x):,}")
                    display_df['Count'] = display_df['Count'].apply(lambda x: f"{int(x):,}")
                except: pass
                
                display_df['Sales_YoY'] = display_df['Sales_YoY'].astype(str) + "%"
                display_df['Count_YoY'] = display_df['Count_YoY'].astype(str) + "%"
            
            # Rename columns
            display_df.columns = ['ブロック/業種', '純売上高', '売上前年比', '客数', '客数前年比']
            
            st.dataframe(display_df, use_container_width=True)
            
        with col2:
            st.subheader("📥 ダウンロード")
            
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                summary_df.to_excel(writer, sheet_name='週次サマリー', index=False)
                combined_df.to_excel(writer, sheet_name='日別詳細', index=False)
                
            st.download_button(
                label="Excelファイルをダウンロード",
                data=buffer.getvalue(),
                file_name=f"売上集計_{time.strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_btn"
            )
            
        with st.expander("📅 日別詳細データ（サマリー）", expanded=True):
            st.write("各日の総合計一覧です。")
            if not combined_df.empty:
                # Filter for Total Zone, sort, and Drop Duplicates to be safe
                daily_view = combined_df[combined_df['Zone'].str.contains('軽井沢ＰＳＰ 計|総合計', na=False)].copy()
                
                # Robust Deduplication
                # Ensure Date is strictly string and clean
                daily_view['Date'] = daily_view['Date'].astype(str).str.strip()
                daily_view = daily_view.sort_values('Date')
                
                # Deduplicate by Date, keeping the last (last is usually better if sorted or manual appends)
                daily_view = daily_view.drop_duplicates(subset=['Date'], keep='last')
                
                # Consistent Formatting
                try:
                    daily_view['Sales'] = daily_view['Sales'].apply(lambda x: f"{int(x):,}")
                    daily_view['Count'] = daily_view['Count'].apply(lambda x: f"{int(x):,}")
                    
                    # Ensure YoY has 1 decimal + % (same as Weekly Summary)
                    # Note: Manual input might be float, extracted might be float. 
                    daily_view['Sales_YoY'] = daily_view['Sales_YoY'].astype(float).round(1).astype(str) + "%"
                    daily_view['Count_YoY'] = daily_view['Count_YoY'].astype(float).round(1).astype(str) + "%"
                except Exception as e:
                    pass

                daily_view = daily_view[['Date', 'Sales', 'Sales_YoY', 'Count', 'Count_YoY']]
                daily_view.columns = ['日付', '純売上高', '売上前年比', '客数', '客数前年比']
                
                st.dataframe(daily_view, use_container_width=True)
            else:
                st.info("データがありません。")
            
    else:
        st.error("データの抽出に失敗しました。PDFの形式を確認してください。")
