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
st.markdown("### 讓排練更有效率，資訊不漏接！")
st.markdown("---")

# --- 2. 讀取資料 ---
sheet_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQuBpbRyxlP9-sjmm9tAGtQvtmeoUECLpThRbpdQlPyex1W-EyWvgZ2UvAovr1gqR8mAJCPpmI2c1x9/pub?gid=0&single=true&output=csv"

@st.cache_data(ttl=60)
def load_data(url):
    try:
        # 【暴力解法】 header=None 代表「我不信賴檔案裡的標題，全部讀進來當資料」
        df = pd.read_csv(url, header=None)
        
        # 直接指定欄位名稱 (根據您的表格順序)
        # 假設您的表格依序是：月份, 日期, 時段, 時間, 進度, 場地, 備註
        # 如果您的 CSV 有多餘的空白欄，這裡只取前 7 欄
        df = df.iloc[:, :7] 
        df.columns = ['月份', '日期', '時段', '時間', '進度內容', '場地', '備註']
        
        # 【資料清洗】
        # 1. 把 "月份" 這一欄填滿 (處理合併儲存格)
        df['月份'] = df['月份'].ffill()
        
        # 2. 過濾掉 "垃圾行"
        # 如果 "日期" 那一欄寫著 "日期" (原本的標題行)，或是 "2025..." (大標題)，或是空的，都刪掉
        # 我們只保留 "日期" 欄位裡有包含數字或 "/" 的行
        df = df[df['日期'].astype(str).str.contains(r'\d', na=False)]
        
        # 3. 填補剩下的空值
        df = df.fillna("")
        
        return df
    except Exception as e:
        st.error(f"❌ 資料讀取發生錯誤：{e}")
        return pd.DataFrame()

# 執行讀取
df = load_data(sheet_url)

# --- 3. 顯示介面 ---
if not df.empty:
    # 側邊欄
    st.sidebar.header("🔍 篩選功能")
    all_months = df["月份"].unique().tolist()
    selected_month = st.sidebar.multiselect("選擇月份", all_months, default=all_months)
    search_keyword = st.sidebar.text_input("🔎 搜尋關鍵字")

    # 篩選
    filtered_df = df.copy()
    if selected_month:
        filtered_df = filtered_df[filtered_df["月份"].isin(selected_month)]
    if search_keyword:
        mask = filtered_df.apply(lambda x: x.astype(str).str.contains(search_keyword, case=False).any(), axis=1)
        filtered_df = filtered_df[mask]

    # 今日提醒
    today_str = datetime.now().strftime("%m/%d")
    # today_str = "12/13" # 測試用，您可以把這行打開看看 12/13 的效果
    
    today_rehearsal = df[df['日期'].astype(str).str.contains(today_str, na=False)]
    if not today_rehearsal.empty:
        st.success(f"🔔 **提醒：今天 ({today_str}) 有排練！**")
        st.dataframe(today_rehearsal, use_container_width=True, hide_index=True)

    # 主表格
    st.subheader(f"📅 排練日程表 ({len(filtered_df)} 筆)")
    st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "進度內容": st.column_config.TextColumn("進度內容", width="large"),
            "備註": st.column_config.TextColumn("備註", help="⚠️"),
        }
    )
    
else:
    st.warning("⚠️ 讀取不到有效資料，請檢查 Google Sheet 連結。")

st.markdown("---")
st.caption("SCU Choir Rehearsal Schedule")