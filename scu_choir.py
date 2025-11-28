import streamlit as st
import pandas as pd
from datetime import datetime

# --- 1. 網頁基礎設定 ---
st.set_page_config(
    page_title="SCU Choir 排練進度表", 
    page_icon="🎵", 
    layout="wide"
)

st.title("🎵 東吳校友合唱團 - SCU Choir - 2025 排練看板")
st.markdown("### 讓排練更有效率，資訊不漏接！")
st.markdown("---")

# --- 2. 讀取資料 (使用您的 Google Sheet 網址) ---
# 這是您剛剛提供的公開 CSV 連結
sheet_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQuBpbRyxlP9-sjmm9tAGtQvtmeoUECLpThRbpdQlPyex1W-EyWvgZ2UvAovr1gqR8mAJCPpmI2c1x9/pub?gid=0&single=true&output=csv"

@st.cache_data(ttl=60) # 每 60 秒會自動檢查一次有沒有新資料
def load_data(url):
    try:
        # 讀取 CSV
        df = pd.read_csv(url)
        
        # 資料清洗：把全空的行刪掉
        df = df.dropna(how="all")
        
        # 填補月份 (處理合併儲存格的邏輯)
        # 確保 '月份' 欄位存在才執行填補
        if '月份' in df.columns:
            df['月份'] = df['月份'].ffill()
        
        # 將 NaN (空值) 填補為空字串，避免網頁顯示 "None"
        df = df.fillna("")
            
        return df
    except Exception as e:
        st.error(f"❌ 讀取資料失敗，請確認網路連線。錯誤訊息: {e}")
        return None

# 執行讀取
df = load_data(sheet_url)

if df is not None:
    # --- 3. 側邊欄：強大的篩選器 ---
    st.sidebar.header("🔍 篩選功能")

    # [功能 A] 篩選月份
    if "月份" in df.columns:
        all_months = df["月份"].unique().tolist()
        # 預設全選，讓大家一進來看到所有行程
        selected_month = st.sidebar.multiselect("選擇月份", all_months, default=all_months)
    else:
        selected_month = []

    # [功能 B] 關鍵字搜尋
    st.sidebar.markdown("---")
    search_keyword = st.sidebar.text_input("🔎 搜尋關鍵字", placeholder="輸入: 慈音老師, 小團, 新光...")

    # --- 4. 資料篩選邏輯 ---
    filtered_df = df.copy()

    # 執行月份篩選
    if selected_month and "月份" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["月份"].isin(selected_month)]

    # 執行關鍵字搜尋 (搜尋所有欄位)
    if search_keyword:
        mask = filtered_df.apply(lambda x: x.astype(str).str.contains(search_keyword, case=False).any(), axis=1)
        filtered_df = filtered_df[mask]

    # --- 5. 主畫面顯示 ---
    
    # [亮點功能] 自動偵測「今天」有沒有排練
    today_str = datetime.now().strftime("%m/%d") # 抓取今天日期 (格式如 11/27)
    # today_str = "11/28" # 測試用：您可以把這行打開，假裝今天是 11/28 看看效果
    
    if '日期' in df.columns:
        # 模糊比對：只要日期欄位裡包含今天的日期字串
        today_rehearsal = df[df['日期'].astype(str).str.contains(today_str, na=False)]
        
        if not today_rehearsal.empty:
            st.success(f"🔔 **提醒：今天 ({today_str}) 有排練！請準時出席。**")
            # 特別顯示今天的行程
            st.dataframe(today_rehearsal, use_container_width=True, hide_index=True)
        else:
            # 如果今天沒排練，顯示這句貼心的話
            st.info(f"🍵 今天 ({today_str}) 沒有排練，讓喉嚨休息一下吧！ ~音樂組 關心您~ ❤️")

    st.subheader(f"📅 排練日程表 ({len(filtered_df)} 筆資料)")
    
    # [美化表格] 設定欄位顯示方式
    st.dataframe(
        filtered_df,
        use_container_width=True, # 填滿視窗
        hide_index=True,          # 隱藏醜醜的 0,1,2 索引
        column_config={
            "月份": st.column_config.TextColumn("月份", width="small"),
            "日期": st.column_config.TextColumn("日期", width="medium"),
            "時段": st.column_config.TextColumn("時段", width="small"),
            "時間": st.column_config.TextColumn("時間", width="medium"),
            "進度內容": st.column_config.TextColumn(
                "進度內容", 
                width="large", 
                help="💡 包含分團與詳細曲目"
            ),
            "場地": st.column_config.TextColumn("場地", width="medium"),
            "備註": st.column_config.TextColumn(
                "備註", 
                width="medium",
                help="⚠️ 重要出席提醒"
            ),
        }
    )

    st.markdown("---")
    st.caption("資料來源：SCU Choir Google 雲端排練表 | 資料更新：即時同步")
