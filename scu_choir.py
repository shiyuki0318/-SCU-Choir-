import streamlit as st
import pandas as pd
from datetime import datetime

# --- 1. 網頁基礎設定 ---
st.set_page_config(
    page_title="SCU Choir 排練進度", 
    page_icon="🎵", 
    layout="wide"
)

st.title("🎵 SCU Choir 東吳校友合唱團 | 2025 排練看板")
st.markdown("### 🍂 溫暖排練，效率滿點")
st.markdown("---")

# --- 2. 讀取資料 ---
sheet_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQuBpbRyxlP9-sjmm9tAGtAGQvtmeoUECLpThRbpdQlPyex1W-EyWvgZ2UvAovr1gqR8mAJCPpmI2c1x9/pub?gid=0&single=true&output=csv" # 您的網址

@st.cache_data(ttl=60)
def load_data(url):
    try:
        # 【最終修復】: engine='python' 讓 Pandas 使用更強大的解析器，
        # 配合 on_bad_lines='skip' 專門處理不規範的 Google Sheet 輸出。
        df = pd.read_csv(url, header=None, on_bad_lines='skip', engine='python') 
        
        # 確保我們只取前 7 欄
        df = df.iloc[:, :7] 
        df.columns = ['月份', '日期', '時段', '時間', '進度內容', '場地', '備註']
        
        # --- 數據清洗與標籤 ---
        df['月份'] = df['月份'].ffill()
        df = df[df['日期'].astype(str).str.contains(r'\d', na=False)]
        df = df.fillna("")

        # 智慧標籤系統：判斷每一列屬於哪種排練
        def tag_row(row):
            content = str(row['進度內容']) + str(row['備註'])
            
            if "僅樂手" in content or "band and soli" in content:
                return "musician"
            
            is_small = "小團" in content or "室內團" in content
            is_large = "大團" in content or "全部人員" in content or "所有曲目" in content
            
            if is_small and is_large:
                return "mixed"
            elif is_small:
                return "small"
            else:
                return "large"

        df['type'] = df.apply(tag_row, axis=1)
        
        # 過濾掉「僅樂手」的行程
        df = df[df['type'] != 'musician']
        
        return df
    except Exception as e:
        # 如果還是失敗，可能是網址或檔案完全錯誤
        st.error(f"資料讀取錯誤：無法解析 Google Sheet 檔案。請確認網址和檔案內容。錯誤: {e}")
        return pd.DataFrame()

df = load_data(sheet_url)

# --- 3. 顯示介面 --- (後續邏輯不變)
if not df.empty and "月份" in df.columns:
    
    # 樣式定義 (在 'type' 欄位存在的情況下執行)
    def highlight_rows(row):
        if row['type'] in ['small', 'mixed']:
            return ['font-weight: bold; color: #8B4513; background-color: #FFF8DC'] * len(row)
        return ['color: #4B3621'] * len(row)

    st.sidebar.header("🔍 排練篩選")
    st.sidebar.markdown("**您的身份是？**")
    show_small = st.sidebar.checkbox("🙋‍♂️ 我有參加「室內團 / 小團」", value=False)
    st.sidebar.markdown("---")

    all_months = df["月份"].unique().tolist()
    selected_month = st.sidebar.multiselect("選擇月份", all_months, default=all_months)
    search_keyword = st.sidebar.text_input("🔎 關鍵字搜尋")

    # 過濾邏輯
    filtered_df = df.copy()
    if not show_small:
        filtered_df = filtered_df[filtered_df['type'].isin(['large', 'mixed'])]
    if selected_month:
        filtered_df = filtered_df[filtered_df["月份"].isin(selected_month)]
    if search_keyword:
        mask = filtered_df.apply(lambda x: x.astype(str).str.contains(search_keyword, case=False).any(), axis=1)
        filtered_df = filtered_df[mask]

    # 應用樣式與顯示
    styled_df = filtered_df.style.apply(highlight_rows, axis=1)
    columns_to_display = [col for col in filtered_df.columns if col not in ['type']]
    
    st.subheader(f"📅 排練日程表 ({len(filtered_df)} 筆)")
    
    st.dataframe(
        styled_df[columns_to_display], 
        use_container_width=True,
        hide_index=True,
        column_config={
            "進度內容": st.column_config.TextColumn("進度內容", width="large"),
            "備註": st.column_config.TextColumn("備註", help="⚠️"),
            "月份": st.column_config.TextColumn("月份", width="small"),
        },
        height=500
    )

    st.caption("🎨 圖例說明： 🟤 一般字體 = 大團行程 | 🟠 **粗體褐字 = 包含小團/室內團行程**")

else:
    st.warning("⚠️ 目前讀取不到有效資料，請檢查 Google Sheet 連結和內容。")

st.markdown("---")
st.caption("SCU Choir 2025 | Design with 🤎")
