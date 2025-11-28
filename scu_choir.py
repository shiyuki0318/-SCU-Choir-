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

# 🌟 採用使用者客製化標題
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
                # 這裡假設年份是 2025 或 2026 (根據實際排練表進行調整)
                year = 2025 if month >= 11 else 2026 
                return datetime(year, month, day)
            except:
                return pd.NaT

        df['datetime'] = df.apply(parse_datetime, axis=1)
        
        # 智慧標籤系統 (用於小團/大團高亮)
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

# --- 🌟 新增：標籤演出事件 (用於篩選與提醒) ---
df['is_performance'] = df['備註'].astype(str).str.contains('演出', case=False, na=False) | \
                      df['進度內容'].astype(str).str.contains('演出', case=False, na=False)

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

    # --- 側邊欄篩選 ---
    st.sidebar.header("🔍 排練篩選")
    
    st.sidebar.markdown("**您的身份是？**")
    show_small = st.sidebar.checkbox("🙋‍♂️ 我有參加「室內團 / 小團」", value=False)
    
    # 🌟 新增：演出時間篩選按鈕
    st.sidebar.markdown("---")
    st.sidebar.markdown("**特別篩選**")
    show_performance_only = st.sidebar.checkbox("🎬 僅顯示「演出」時間", value=False)
    st.sidebar.markdown("---")

    all_months = df["月份"].unique().tolist()
    selected_month = st.sidebar.multiselect("選擇月份", all_months, default=all_months)
    search_keyword = st.sidebar.text_input("🔎 搜尋關鍵字")

    # --- 過濾邏輯 ---
    filtered_df = df.copy()

    if not show_small:
        filtered_df = filtered_df[filtered_df['type'].isin(['large', 'mixed'])]
    if selected_month:
        filtered_df = filtered_df[filtered_df["月份"].isin(selected_month)]
    if search_keyword:
        mask = filtered_df.apply(lambda x: x.astype(str).str.contains(search_keyword, case=False).any(), axis=1)
        filtered_df = filtered_df[mask]
        
    # 🌟 新增：演出時間過濾邏輯
    if show_performance_only:
        filtered_df = filtered_df[filtered_df['is_performance'] == True]

    # --- 聰明提醒：下次排練置頂 (修改邏輯為演出優先) ---
    today = datetime.now().date()
    today_str = datetime.now().strftime("%m/%d")
    reminder_shown = False
    
    # 1. 從完整的 df 找出最近的【演出】 (確保演出倒數不受排練篩選影響)
    all_upcoming_performances = df[
        (df['datetime'].dt.date >= today) & 
        (df['is_performance'] == True)
    ].sort_values(by='datetime', na_position='last')

    nearest_performance = None
    if not all_upcoming_performances.empty and pd.notna(all_upcoming_performances.iloc[0]['datetime']):
        nearest_performance = all_upcoming_performances.iloc[0]
        
    # A. 優先顯示演出倒數 (不受側邊欄篩選影響)
    if nearest_performance is not None:
        performance_date_dt = nearest_performance['datetime'].date()
        countdown_days = (performance_date_dt - today).days
        
        if countdown_days >= 0:
            p_date = nearest_performance['日期']
            p_time = nearest_performance['時間']
            p_location = nearest_performance['場地']
            p_content = nearest_performance['進度內容']
            
            # 🌟 顯示演出倒數計時
            st.success(
                f"🎉 **【重要演出倒數】**： **{p_content}** \n\n"
                f"**演出日期:** {p_date} \n"
                f"**距離演出倒數:** {countdown_days} 天"
                f"\n\n**演出時間:** {p_time} **地點:** {p_location}"
            )
            reminder_shown = True

    # 2. 找出過濾後的【最近事件】
    upcoming_events_filtered = filtered_df[filtered_df['datetime'].dt.date >= today].sort_values(by='datetime', na_position='last')
    nearest_event_filtered = upcoming_events_filtered.iloc[0] if not upcoming_events_filtered.empty and pd.notna(upcoming_events_filtered.iloc[0]['datetime']) else None

    # B. 顯示下次排練提醒 (只在沒有演出倒數時顯示，且下一個事件不是演出)
    if not reminder_shown and nearest_event_filtered is not None:
        
        event_is_performance = nearest_event_filtered['is_performance']
        
        # 只有當下一個事件是排練時才顯示常規提醒 (因為演出的提醒已由 Case A 處理)
        if not event_is_performance:
            
            next_event = nearest_event_filtered
            next_date = next_event['日期']
            next_time = next_event['時間']
            next_location = next_event['場地']
            
            if next_event['datetime'].date() == today:
                 # 🌟 今天排練格式
                 st.success(
                     f"🔔 **提醒：今天 ({next_date}) 要排練喔！請準時出席!!我們不見不散~** \n\n"
                     f"**排練時間:** {next_time}    **地點:** {next_location}"
                 )
            else:
                 # 🌟 下次排練格式
                 st.info(
                     f"✨ **下次排練提醒：** {next_date} \n\n"
                     f"**排練時間:** {next_time} 在 **{next_location}**！"
                 )
            reminder_shown = True

    # C. 處理今天沒有排練/演出的情況
    if not reminder_shown:
        
        # 檢查今天是否有任何事件 (即使被篩選器隱藏)
        today_has_event = not df[df['datetime'].dt.date == today].empty
        
        if today_has_event:
            # 今天有活動但被篩選器濾掉 (e.g. 篩選小團但今天是只有大團)，不顯示 "今天沒有"
            pass 
        elif not upcoming_events_filtered.empty:
            # 今天沒有活動，但未來有活動
            st.info(f"🍵 今天 ({today_str}) 沒有排練，讓喉嚨休息一下吧！ ~音樂組 關心您~ ❤️")
        else:
            # 季度結束
            st.info("👉 請靜候新一波公告！ 👈")
            
    # --- 表格顯示 ---
    
    # 🌟【月份合併邏輯】
    def simulate_merge_month(series):
        is_first = ~series.duplicated()
        return series.where(is_first, '')

    filtered_df['月份'] = simulate_merge_month(filtered_df['月份'])
    display_df = filtered_df.reset_index(drop=True) # 重設索引，確保斑馬紋正確
    styled_df = display_df.style.apply(highlight_rows, axis=1)

    # 🌟 新增注意事項 (使用者要求)
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

# 🌟 採用使用者客製化頁尾
st.markdown("---")
st.caption("SCU Choir 2025 | Design with 💚 by 志行")
