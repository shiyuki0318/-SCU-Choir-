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

# --- 2. 讀取資料 ---
sheet_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQuBpbRyxlP9-sjmm9tAGtQvtmeoUECLpThRbpdQlPyex1W-EyWvgZ2UvAovr1gqR8mAJCPpmI2c1x9/pub?gid=0&single=true&output=csv" 

@st.cache_data(ttl=60)
def load_data(url):
    try:
        # 使用最強解析器
        df = pd.read_csv(url, header=None, on_bad_lines='skip', engine='python') 
        df = df.iloc[:, :7] 
        df.columns = ['月份', '日期', '時段', '時間', '進度內容', '場地', '備註']
        
        # --- 數據清洗 ---
        df['月份'] = df['月份'].ffill()
        df = df[df['日期'].astype(str).str.contains(r'\d', na=False)]
        df = df.fillna("")

        # 日期解析
        def parse_datetime(row):
            try:
                date_part = str(row['日期']).split('(')[0].strip()
                month, day = map(int, date_part.split('/'))
                year = 2025 if month >= 11 else 2026 
                return datetime(year, month, day)
            except:
                return pd.NaT

        df['datetime'] = df.apply(parse_datetime, axis=1)
        
        # 智慧標籤
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

# --- 標記演出 ---
df['is_performance'] = df['備註'].astype(str).str.contains('演出', case=False, na=False) | \
                      df['進度內容'].astype(str).str.contains('演出', case=False, na=False)

# --- 3. 顯示介面 ---
if not df.empty and "月份" in df.columns:
    
    # 樣式定義
    def highlight_rows(row):
        is_even_row = row.name % 2 == 0
        base_bg = "#FFFFFF" if is_even_row else "#E6F0FF"
        if row['type'] in ['small', 'mixed']:
            style = f'font-weight: bold; color: #8B4513; background-color: #FFF8DC' 
        else:
            style = f'color: #4B3621; background-color: {base_bg}'
        return [style] * len(row)

    # --- 側邊欄 ---
    st.sidebar.header("🔍 排練篩選")
    st.sidebar.markdown("**您的身份是？**")
    show_small = st.sidebar.checkbox("🙋‍♂️ 我有參加「室內團 / 小團」", value=False)
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("**特別篩選**")
    show_performance_only = st.sidebar.checkbox("🎬 僅顯示「演出」時間", value=False)
    st.sidebar.markdown("---")

    all_months = df["月份"].unique().tolist()
    selected_month = st.sidebar.multiselect("選擇月份", all_months, default=all_months)
    search_keyword = st.sidebar.text_input("🔎 搜尋關鍵字")

    # ==========================================
    # 🌟 Part 1 & 2: 獨立提醒計算
    # ==========================================
    today = datetime.now().date()
    today_str = datetime.now().strftime("%m/%d")
    
    reminder_source_df = df.copy()
    if not show_small:
         reminder_source_df = reminder_source_df[reminder_source_df['type'].isin(['large', 'mixed'])]

    # 1. 演出倒數
    future_performances = df[
        (df['datetime'].dt.date >= today) & 
        (df['is_performance'] == True)
    ].sort_values(by='datetime', na_position='last')

    if not future_performances.empty:
        perf = future_performances.iloc[0]
        p_date_obj = perf['datetime'].date()
        countdown = (p_date_obj - today).days
        p_name = perf['進度內容'] if perf['進度內容'] else "重要演出"
        p_date = perf['日期']
        p_time = perf['時間']
        p_loc = perf['場地']

        st.warning(
            f"### ⏳ **距離演出倒數： {countdown} 天**\n"
            f"**{p_name}**\n\n"
            f"📅 **日期:** {p_date} ｜ ⏰ **時間:** {p_time} ｜ 📍 **地點:** {p_loc}"
        )

    # 2. 下次排練/事件提醒
    upcoming_events_real = reminder_source_df[reminder_source_df['datetime'].dt.date >= today].sort_values(by='datetime', na_position='last')

    if not upcoming_events_real.empty:
        next_event = upcoming_events_real.iloc[0]
        next_date = next_event['日期']
        next_time = next_event['時間']
        next_location = next_event['場地']
        raw_content = next_event['進度內容'] 

        # 🌟【關鍵優化】：使用標準 Markdown 清單讓對齊更完美
        def format_progress_list(content_str):
            if not content_str or str(content_str) == "nan":
                return "暫無詳細內容"
            
            # 支援換行符號 \n 或 |
            raw_text = str(content_str).replace('|', '\n').strip()
            lines = raw_text.split('\n')
            
            output_lines = []
            
            for line in lines:
                line = line.strip()
                if not line: continue
                
                # 偵測冒號 (全形或半形)
                if '：' in line or ':' in line:
                    line = line.replace(':', '：')
                    parts = line.split('：', 1)
                    header = parts[0].strip()
                    songs_str = parts[1].strip()
                    
                    # 標題行 (時段/團別)
                    output_lines.append(f"**🔸 {header}**")
                    
                    # 曲目清單 (使用 Markdown 的 '-' 符號自動縮排)
                    songs = re.split(r'[、,]', songs_str)
                    for song in songs:
                        song = song.strip()
                        if song:
                            output_lines.append(f"- {song}")
                    output_lines.append("") # 空行分隔
                else:
                    # 沒有冒號，純文字清單
                    items = re.split(r'[、,]', line)
                    for item in items:
                        item = item.strip()
                        if item:
                            output_lines.append(f"- {item}")
            
            return "\n".join(output_lines)

        formatted_content = format_progress_list(raw_content)
        
        reminder_box_type = st.success if next_event['datetime'].date() == today else st.info
        reminder_title = f"🔔 **提醒：今天 ({next_date}) 要排練喔！**" if next_event['datetime'].date() == today else f"✨ **下次排練提醒：**"
        
        # 組合顯示 (把時間地點稍微加大)
        msg_content = (
            f"### 【本周進度:】\n"
            f"**{next_date}**\n\n"
            f"{formatted_content}\n"
            f"---\n"
            f"#### ⏰ {next_time} ｜ 📍 {next_location}"
        )
        
        reminder_box_type(reminder_title) 
        st.markdown(msg_content)          
        
    else:
        st.info(f"🍵 今天 ({today_str}) 沒有排練，讓喉嚨休息一下吧！ ~音樂組 關心您~ ❤️")


    # ==========================================
    # 🌟 Part 3: 表格呈現
    # ==========================================
    filtered_df = df.copy()

    if not show_small:
        filtered_df = filtered_df[filtered_df['type'].isin(['large', 'mixed'])]
    if selected_month:
        filtered_df = filtered_df[filtered_df["月份"].isin(selected_month)]
    if search_keyword:
        mask = filtered_df.apply(lambda x: x.astype(str).str.contains(search_keyword, case=False).any(), axis=1)
        filtered_df = filtered_df[mask]
    if show_performance_only:
        filtered_df = filtered_df[filtered_df['is_performance'] == True]

    def simulate_merge_month(series):
        is_first = ~series.duplicated()
        return series.where(is_first, '')

    filtered_df['月份'] = simulate_merge_month(filtered_df['月份'])
    display_df = filtered_df.reset_index(drop=True)
    styled_df = display_df.style.apply(highlight_rows, axis=1)

    st.markdown("### ⚠️ **注意事項：**")
    st.caption("每週排練進度有可能視排練狀況斟酌調整，以進度表最新內容為準。")

    st.subheader(f"📅 排練日程表 ({len(display_df)} 筆)")
    
    st.dataframe(
        styled_df, 
        use_container_width=True,
        hide_index=True,
        column_config={
            "進度內容": st.column_config.TextColumn(label="進度內容", width="large"),
            "備註": st.column_config.TextColumn(label="備註", help="⚠️"),
            "月份": st.column_config.TextColumn(label="月份", width="small"),
            "場地": st.column_config.TextColumn(label="場地", width="medium"), 
            "datetime": None, 
            "type": None,
            "is_performance": None
        },
        height=500
    )

    st.caption("🎨 圖例說明： 🟤 一般字體 = 大團行程 | 🟠 **粗體褐字 = 包含小團/室內團行程**")

else:
    st.warning("⚠️ 目前讀取不到有效資料，請檢查 Google Sheet 連結和內容。")

st.markdown("---")
st.caption("SCU Choir 2025 | Design with 💚 by 志行")
