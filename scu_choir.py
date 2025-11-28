import streamlit as st
import pandas as pd
from datetime import datetime
import re

# --- 1. 網頁基礎設定 ---
st.set_page_config(
    page_title="SCU Choir 排練進度", 
    page_icon="🎵", 
    layout="wide"
)

st.title("🎵 東吳校友合唱團 ~ SCU Choir ~ | 2025 排練看板")
st.markdown("### 🍂 溫暖排練，效率滿點")
st.markdown("---")

# --- 2. 讀取資料 (最終防彈版) ---
sheet_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQuBpbRyxlP9-sjmm9tAGtQvtmeoUECLpThRbpdQlPyex1W-EyWvgZ2UvAovr1gqR8mAJCPpmI2c1x9/pub?gid=0&single=true&output=csv" 

@st.cache_data(ttl=60)
def load_data(url):
    try:
        # 使用最強解析器
        df = pd.read_csv(url, header=None, on_bad_lines='skip', engine='python') 
        df = df.iloc[:, :7] 
        df.columns = ['月份', '日期', '時段', '時間', '進度內容', '場地', '備註']
        
        # --- 數據清洗與標籤 ---
        df['月份'] = df['月份'].ffill()
        df = df[df['日期'].astype(str).str.contains(r'\d', na=False)]
        df = df.fillna("")

        # 🌟 日期解析 (確保能正確判斷下次排練)
        def parse_datetime(row):
            try:
                date_part = str(row['日期']).split('(')[0].strip()
                month, day = map(int, date_part.split('/'))
                year = 2025 if month >= 11 else 2026 
                return datetime(year, month, day)
            except:
                return pd.NaT

        df['datetime'] = df.apply(parse_datetime, axis=1)
        
        # 智慧標籤系統
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
        df = df[df['type'] != 'musician']
        
        return df
    except Exception as e:
        st.error(f"資料讀取錯誤：無法解析 Google Sheet 檔案。")
        return pd.DataFrame() 

df = load_data(sheet_url)

# --- 3. 顯示介面與功能 ---
if not df.empty and "月份" in df.columns:
    
    # 樣式定義 (白藍交替 + 小團高亮)
    def highlight_rows(row):
        is_even_row = row.name % 2 == 0
        base_bg = "#FFFFFF" if is_even_row else "#E6F0FF"
        if row['type'] in ['small', 'mixed']:
            style = f'font-weight: bold; color: #8B4513; background-color: #FFF8DC' 
        else:
            style = f'color: #4B3621; background-color: {base_bg}'
        return [style] * len(row)

    st.sidebar.header("🔍 排練篩選")
    
    # 身份選擇
    st.sidebar.markdown("**您的身份是？**")
    show_small = st.sidebar.checkbox("🙋‍♂️ 我有參加「室內團 / 小團」", value=False)
    st.sidebar.markdown("---")

    all_months = df["月份"].unique().tolist()
    selected_month = st.sidebar.multiselect("選擇月份", all_months, default=all_months)
    search_keyword = st.sidebar.text_input("🔎 關鍵字搜尋")

    # --- 過濾邏輯 ---
    filtered_df = df.copy()

    if not show_small:
        filtered_df = filtered_df[filtered_df['type'].isin(['large', 'mixed'])]
    if selected_month:
        filtered_df = filtered_df[filtered_df["月份"].isin(selected_month)]
    if search_keyword:
        mask = filtered_df.apply(lambda x: x.astype(str).str.contains(search_keyword, case=False).any(), axis=1)
        filtered_df = filtered_df[mask]

    # --- 聰明提醒：下次排練置頂 (格式修正) ---
    today = datetime.now().date()
    today_str = datetime.now().strftime("%m/%d")
    is_rehearsal_today = False
    
    upcoming_rehearsals = filtered_df[filtered_df['datetime'].dt.date >= today].sort_values(by='datetime', na_position='last')

    if not upcoming_rehearsals.empty and pd.notna(upcoming_rehearsals.iloc[0]['datetime']):
        next_rehearsal = upcoming_rehearsals.iloc[0]
        next_date = next_rehearsal['日期']
        next_time = next_rehearsal['時間']
        next_location = next_rehearsal['場地']
        
        # 🌟 修正後的提醒格式 (使用 markdown 換行)
        if next_rehearsal['datetime'].date() == today:
             is_rehearsal_today = True
             st.success(
                 f"🔔 **提醒：今天 ({next_date}) 要排練喔！請準時出席!!我們不見不散~** \n\n"
                 f"**排練時間:** {next_time}   **地點:** {next_location}"
             )
        else:
             st.info(
                 f"✨ **下次排練提醒：** {next_date} \n\n"
                 f"**排練時間:** {next_time} 在 **{next_location}**！"
             )

    # 顯示「今天沒有」的貼心訊息
    if not is_rehearsal_today:
        if not upcoming_rehearsals.empty:
            st.info(f"🍵 今天 ({today_str}) 沒有排練，讓喉嚨休息一下吧！ ~音樂組 關心您~ ❤️")
        else:
            st.info("🥳 恭喜！本學期排練行程已全部結束，請靜候新一波公告！")

    # 應用樣式與顯示
    display_df = filtered_df.reset_index(drop=True)
    styled_df = display_df.style.apply(highlight_rows, axis=1)

    # 🌟 新增注意事項
    st.info("⚠️ **注意事項：** 每週排練進度有可能視排練狀況斟酌調整，以進度表最新內容為準。")

    # 顯示表格 (使用 column_config 隱藏不需要的欄位)
    st.subheader(f"📅 排練日程表 ({len(display_df)} 筆)")
    
    st.dataframe(
        styled_df, # 傳遞樣式物件
        use_container_width=True,
        hide_index=True,
        column_config={
            "進度內容": st.column_config.TextColumn(label="進度內容", width="large"),
            "備註": st.column_config.TextColumn(label="備註", help="⚠️"),
            "月份": st.column_config.TextColumn(label="月份", width="small"),
            "場地": st.column_config.TextColumn(label="場地", width="medium"), 
            "datetime": None, 
            "type": None,     
        },
        height=500
    )

    st.caption("🎨 圖例說明： 🟤 一般字體 = 大團行程 | 🟠 **粗體褐字 = 包含小團/室內團行程**")

else:
    st.warning("⚠️ 目前讀取不到有效資料，請檢查 Google Sheet 連結和內容。")

st.markdown("---")
st.caption("SCU Choir 2025 | Design with 🤎")
