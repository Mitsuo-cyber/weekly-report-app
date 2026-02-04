import streamlit as st
import pandas as pd
import io
import time
from src.extractor import extract_from_pdf
from src.aggregator import calculate_weekly_summary

st.set_page_config(page_title="売上PDF集計アプリ", layout="wide")

st.title("🗂️ 売上報告PDF 自動集計ツール")

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

uploaded_files = st.file_uploader("PDFファイルをここにドラッグ＆ドロップ", type="pdf", accept_multiple_files=True)

if uploaded_files:
    st.info(f"{len(uploaded_files)} 個のファイルを処理中...")
    
    all_data = []
    
    progress_bar = st.progress(0)
    
    for i, file in enumerate(uploaded_files):
        # Streamlit file object works with pdfplumber
        df = extract_from_pdf(file, filename=file.name)
        if df is not None and not df.empty:
            all_data.append(df)
        progress_bar.progress((i + 1) / len(uploaded_files))
        
    if all_data:
        daily_concatenated = pd.concat(all_data, ignore_index=True)
        
        # Calculate Summary
        summary_df = calculate_weekly_summary(daily_concatenated)
        
        st.success("集計完了！")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("📊 週次サマリー（業種別）")
            # Formatting for display
            display_df = summary_df.copy()
            display_df['Sales'] = display_df['Sales'].apply(lambda x: f"{int(x):,}")
            display_df['Count'] = display_df['Count'].apply(lambda x: f"{int(x):,}")
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
                daily_concatenated.to_excel(writer, sheet_name='日別詳細', index=False)
                
            st.download_button(
                label="Excelファイルをダウンロード",
                data=buffer.getvalue(),
                file_name=f"売上集計_{time.strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
        with st.expander("詳細データを確認する"):
            st.dataframe(daily_concatenated)
            
    else:
        st.error("データの抽出に失敗しました。PDFの形式を確認してください。")
