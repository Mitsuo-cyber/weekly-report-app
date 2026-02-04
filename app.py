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
        
        # --- Error Handling ---
        # Identify unreadable files
        error_df = raw_concatenated[raw_concatenated['Zone'].str.contains('ERROR_UNREADABLE', na=False)]
        valid_df = raw_concatenated[~raw_concatenated['Zone'].str.contains('ERROR_UNREADABLE', na=False)]
        
        if not error_df.empty:
            st.error("⚠️ 以下のファイルの読み取りに失敗しました。手動でデータを入力してください。")
            for _, row in error_df.iterrows():
                fname = row['Zone'].split(':')[-1]
                st.write(f"- 📄 **{fname}** (日付: {row['Date']})")
        
        # --- Manual Data Entry Form ---
        with st.expander("✍️ 手動データ入力 (読取失敗時用)", expanded=not error_df.empty):
            st.caption("読み取れなかった日の「総合計」を入力してください。詳細の入力は不要です。")
            
            with st.form("manual_entry_form"):
                col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
                m_date = col_m1.text_input("日付 (例: 20260201)", value="")
                m_sales = col_m2.number_input("純売上高", min_value=0, step=1000)
                m_sales_yoy = col_m3.number_input("売上前年比(%)", step=0.1)
                m_count = col_m4.number_input("客数", min_value=0, step=10)
                m_count_yoy = col_m5.number_input("客数前年比(%)", step=0.1)
                
                submitted = st.form_submit_button("データを保存")
                
                if submitted and m_date:
                    # Save to session and file
                    new_entry = {
                        'Date': m_date,
                        'Zone': '【軽井沢ＰＳＰ 計】', # Treat as Total Zone
                        'Sales': int(m_sales),
                        'Sales_YoY': float(m_sales_yoy),
                        'Count': int(m_count),
                        'Count_YoY': float(m_count_yoy)
                    }
                    st.session_state['manual_data'][m_date] = new_entry
                    save_manual_data(st.session_state['manual_data'])
                    st.success(f"{m_date} のデータを保存しました。集計に反映されます。")
                    st.rerun()

        # --- Merge Manual Data ---
        # Convert manual dict to DataFrame
        if st.session_state['manual_data']:
            manual_list = list(st.session_state['manual_data'].values())
            manual_df = pd.DataFrame(manual_list)
            # Combine valid extracted data with manual data
            combined_df = pd.concat([valid_df, manual_df], ignore_index=True)
            # Deduplicate? If extraction succeeded later, prefer extraction? 
            # For now, simple concat. User manages manual data.
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
            try:
                display_df['Sales'] = display_df['Sales'].apply(lambda x: f"{int(x):,}")
                display_df['Count'] = display_df['Count'].apply(lambda x: f"{int(x):,}")
            except: pass # fallback if non-numeric
            
            display_df['Sales_YoY'] = display_df['Sales_YoY'].astype(str) + "%"
            display_df['Count_YoY'] = display_df['Count_YoY'].astype(str) + "%"
            
            # Rename columns for display
            display_df.columns = ['ブロック/業種', '純売上高', '売上前年比', '客数', '客数前年比']
            
            st.dataframe(display_df, use_container_width=True)
            
        with col2:
            st.subheader("📥 ダウンロード")
            
            # Create Excel in memory
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
            # Filter for Total Zone only to show daily breakdown cleanly
            daily_summary_view = combined_df[combined_df['Zone'].str.contains('軽井沢ＰＳＰ 計|総合計', na=False)].sort_values('Date')
            
            # Format numbers
            daily_view_fmt = daily_summary_view.copy()
            try:
                daily_view_fmt['Sales'] = daily_view_fmt['Sales'].apply(lambda x: f"{int(x):,}")
                daily_view_fmt['Count'] = daily_view_fmt['Count'].apply(lambda x: f"{int(x):,}")
            except: pass
            
            daily_view_fmt = daily_view_fmt[['Date', 'Sales', 'Sales_YoY', 'Count', 'Count_YoY']]
            daily_view_fmt.columns = ['日付', '純売上高', '売上前年比(%)', '客数', '客数前年比(%)']
            
            st.dataframe(daily_view_fmt, use_container_width=True)
            
    else:
        st.error("データの抽出に失敗しました。PDFの形式を確認してください。")
