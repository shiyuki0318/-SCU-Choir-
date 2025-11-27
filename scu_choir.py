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

# --- 2. 讀取與標記資料 (核心邏輯) ---
sheet_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQuBpbRyxlP9-sjmm9tAGtQvtmeoUECLpThRbpdQlPyex1W-EyWvgZ2UvAovr1gqR8mAJCPpmI2c1x9/pub?gid=0&single=true&output=csv"

@st.cache_data(ttl=60)
def load_data(url):
    try:
        # 讀取資料 (強制 header=None 以防標題跑掉)
        df = pd.read_csv(url, header=None)
        df = df.iloc[:, :7] 
        df.columns = ['月份', '日期', '時段', '時間', '進度內容', '場地', '備註']
        
        # 資料清洗
        df['月份'] = df['月份'].ffill()
        df = df[df['日期'].astype(str).str.contains(r'\d', na=False)]
        df = df.fillna("")

        # 🌟 智慧標籤系統：判斷每一列屬於哪種排練
        def tag_row(row):
            content = str(row['進度內容']) + str(row['備註'])
            
            # 1. 判斷是否為「僅樂手」(不用給團員看)
            if "僅樂手" in content or "band and soli" in content:
                return "musician"
            
            # 2. 判斷是否包含「小團/室內團」
            # 注意：有些排練是「大團+小團」同一天，這種我們算成 "mixed"
            is_small = "小團" in content or "室內團" in content
            is_large = "大團" in content or "全部人員" in content or "所有曲目" in content
            
            if is_small and is_large:
                return "mixed" # 大小團都有
            elif is_small:
                return "small" # 只有小團
            else:
                return "large" # 預設為大團

        df['type'] = df.apply(tag_row, axis=1)
        
        # 直接過濾掉「僅樂手」的行程，團員不需要看到
        df = df[df['type'] != 'musician']
        
        return df
    except Exception as e:
        st.error(f"資料讀取錯誤: {e}")
        return pd.DataFrame()

df = load_data(sheet_url)

# --- 3. 側邊欄與篩選器 ---
if not df.empty:
    st.sidebar.header("🔍 排練篩選")
    
    # [功能 A] 身份選擇 (控制大小團顯示)
    st.sidebar.markdown("**您的身份是？**")
    show_small = st.sidebar.checkbox("🙋‍♂️ 我有參加「室內團 / 小團」", value=False)
    
    if show_small:
        st.sidebar.success("已顯示小團專屬行程")
    else:
        st.sidebar.info("目前僅顯示大團/全體行程")

    st.sidebar.markdown("---")

    # [功能 B] 月份篩選
    all_months = df["月份"].unique().tolist()
    selected_month = st.sidebar.multiselect("選擇月份", all_months, default=all_months)

    # [功能 C] 搜尋
    search_keyword = st.sidebar.text_input("🔎 關鍵字搜尋")

    # --- 4. 資料過濾邏輯 ---
    filtered_df = df.copy()

    # 1. 根據身份過濾
    if not show_small:
        # 如果不是小團成員，隱藏「純小團」的行程
        # (保留 "large" 和 "mixed"，因為 mixed 裡也有大團的事)
        filtered_df = filtered_df[filtered_df['type'].isin(['large', 'mixed'])]
    
    # 2. 月份過濾
    if selected_month:
        filtered_df = filtered_df[filtered_df["月份"].isin(selected_month)]

    # 3. 關鍵字過濾
    if search_keyword:
        mask = filtered_df.apply(lambda x: x.astype(str).str.contains(search_keyword, case=False).any(), axis=1)
        filtered_df = filtered_df[mask]

    # --- 5. 表格樣式優化 (Pandas Styler) ---
    # 定義樣式函數
    def highlight_rows(row):
        styles = [''] * len(row)
        
        # 針對「小團」或「混合」行程，給予特殊樣式
        if row['type'] in ['small', 'mixed']:
            # 粗體 + 深咖啡色字 + 淺橘色背景
            return ['font-weight: bold; color: #8B4513; background-color: #FFF8DC'] * len(row)
        
        # 針對「大團」行程，保持大地色系的清爽
        return ['color: #4B3621'] * len(row)

    # 隱藏不需要顯示的 type 欄位
    display_df = filtered_df.drop(columns=['type'])

    # 應用樣式
    styled_df = display_df.style.apply(highlight_rows, axis=1)

    # --- 6. 顯示畫面 ---
    
    # 今日提醒
    today_str = datetime.now().strftime("%m/%d")
    today_rehearsal = filtered_df[filtered_df['日期'].astype(str).str.contains(today_str, na=False)]
    
    if not today_rehearsal.empty:
        st.success(f"🔔 **今天 ({today_str}) 有排練！請確認下方行程。**")
    
    st.subheader(f"📅 排練日程表")
    
    # 使用 st.dataframe 顯示帶有樣式的表格
    st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "進度內容": st.column_config.TextColumn("進度內容", width="large"),
            "備註": st.column_config.TextColumn("備註", help="⚠️"),
            "月份": st.column_config.TextColumn("月份", width="small"),
        },
        height=500 # 固定高度讓捲動更順暢
    )

    # 顏色說明圖例
    st.caption("🎨 圖例說明： 🟤 一般字體 = 大團行程 | 🟠 **粗體褐字 = 包含小團/室內團行程**")

else:
    st.warning("讀取資料中，請稍候...")

st.markdown("---")
st.caption("SCU Choir 2025 | Design with 🤎")
