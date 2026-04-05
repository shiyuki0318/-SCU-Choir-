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

st.title("🎵 東吳校友合唱團 ~ SCU Choir ~ | 2026 排練看板(暫定版)")
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
        
        # 智慧標籤 (大小團)
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

        # 🌟【新增功能】：日期圖示系統 (老師🤵 / 演出🎤)
        def add_status_icons(row):
            note = str(row['備註'])
            content = str(row['進度內容'])
            date_str = str(row['日期'])
            
            # 1. 客席老師
            if "老師" in note and "🤵" not in date_str:
                date_str = f"{date_str} 🤵"
            
            # 2. 演出 (新增這段)
            if ("演出" in note or "演出" in content) and "🎤" not in date_str:
                date_str = f"{date_str} 🎤"
                
            return date_str

        df['日期'] = df.apply(add_status_icons, axis=1)
        
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
    
    # 高亮邏輯
    def highlight_rows(row):
        note = str(row['備註'])
        content = str(row['進度內容'])
        
        alert_keywords = ["務必出席", "重要", "順排", "總彩排"]
        
        # 1. 紅色警戒
        is_alert = any(kw in note for kw in alert_keywords) or any(kw in content for kw in alert_keywords)
        if is_alert:
            return ['background-color: #FFCCCC; color: #8B0000; font-weight: bold'] * len(row)
        
        # 2. 黃色提醒 (演出)
        if "演出" in note or "演出" in content:
            return ['background-color: #FFF9C4; color: #555500; font-weight: bold'] * len(row)
        
        # 3. 小團 (大地色)
        if row['type'] in ['small', 'mixed']:
            return ['font-weight: bold; color: #8B4513; background-color: #FFF8DC'] * len(row)
        
        # 4. 斑馬紋
        is_even_row = row.name % 2 == 0
        base_bg = "#FFFFFF" if is_even_row else "#E6F0FF"
        return [f'color: #4B3621; background-color: {base_bg}'] * len(row)

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
    # 🌟 三欄式儀表板
    # ==========================================
    today = datetime.now().date()
    today_str = datetime.now().strftime("%m/%d")
    
    reminder_source_df = df.copy()
    if not show_small:
         reminder_source_df = reminder_source_df[reminder_source_df['type'].isin(['large', 'mixed'])]

    # 1. 演出資料
    future_performances = df[
        (df['datetime'].dt.date >= today) & 
        (df['is_performance'] == True)
    ].sort_values(by='datetime', na_position='last')

    # 2. 下次排練資料
    upcoming_events_real = reminder_source_df[reminder_source_df['datetime'].dt.date >= today].sort_values(by='datetime', na_position='last')

    col1, col2, col3 = st.columns([1, 1.2, 0.8])

    # --- 左欄：排練提醒 ---
    with col1:
        with st.container(border=True):
            if not upcoming_events_real.empty:
                next_event = upcoming_events_real.iloc[0]
                next_date = next_event['日期']
                next_time = next_event['時間']
                next_location = next_event['場地']
                
                is_today = next_event['datetime'].date() == today
                icon = "🔔" if is_today else "✨"
                title = "今天排練！" if is_today else "下次排練"
                
                st.markdown(f"#### {icon} {title}")
                st.markdown(f"**日期：** {next_date}")
                st.markdown(f"**時間：** {next_time}")
                st.markdown(f"**地點：** {next_location}")
                
                if is_today:
                    st.success("請準時出席，不見不散！")
                else:
                    days_left = (next_event['datetime'].date() - today).days
                    st.caption(f"距離下次排練還有 {days_left} 天")
            else:
                st.markdown("#### ✨ 下次排練")
                st.info("目前無排練行程")

    # --- 中欄：排練進度 (強力修復版) ---
    with col2:
        with st.container(border=True):
            st.markdown(f"#### 📖 本周進度")
            
            if not upcoming_events_real.empty:
                raw_content = next_event['進度內容']
                
                def format_progress_list(content_str):
                    if not content_str or str(content_str) == "nan":
                        return "暫無詳細內容"
                    
                    raw_text = str(content_str).replace('|', '\n').strip()
                    
                    # 🌟【超級強力正則表達式】：強制切割所有時間段
                    # 尋找類似 "19:30-20:40" 或 "20:45~21:40" 這樣的模式
                    # (?<!^) 表示不要在字串開頭就加換行
                    # \d{1,2}[:：]\d{2} 匹配時間 (支援全形/半形冒號)
                    # \s*[-~–—]\s* 匹配連接號 (支援連字號、波浪號、En Dash、Em Dash、空格)
                    time_pattern = r'(?<!^)(\d{1,2}[:：]\d{2}\s*[-~–—]\s*\d{1,2}[:：]\d{2})'
                    
                    # 在這些時間模式前面強制加上換行符號 \n
                    raw_text = re.sub(time_pattern, r'\n\1', raw_text)
                    
                    lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
                    output_lines = []
                    
                    for line in lines:
                        split_idx = -1
                        for i, char in enumerate(line):
                            if char == '：': 
                                split_idx = i
                                break
                            if char == ':': 
                                prev_is_digit = (i > 0 and line[i-1].isdigit())
                                next_is_digit = (i < len(line) - 1 and line[i+1].isdigit())
                                if not (prev_is_digit and next_is_digit):
                                    split_idx = i
                                    break
                        
                        if split_idx != -1:
                            header = line[:split_idx].strip()
                            songs_str = line[split_idx+1:].strip()
                            output_lines.append(f"**🔸 {header}**")
                            songs = re.split(r'[、,]', songs_str)
                            for song in songs:
                                song = song.strip()
                                if song:
                                    output_lines.append(f"- {song}")
                        else:
                            items = re.split(r'[、,]', line)
                            for item in items:
                                item = item.strip()
                                if item:
                                    output_lines.append(f"- {item}")
                    return "\n".join(output_lines)

                formatted_content = format_progress_list(raw_content)
                st.markdown(formatted_content)
            else:
                st.info("休息是為了走更長遠的路")

    # --- 右欄：演出倒數 ---
    with col3:
        with st.container(border=True): 
            st.markdown(f"#### ⏳ 演出倒數")
            if not future_performances.empty:
                perf = future_performances.iloc[0]
                countdown = (perf['datetime'].date() - today).days
                p_name = perf['進度內容'] if perf['進度內容'] else "年度公演"
                
                st.metric(
                    label=f"距離 {p_name}", 
                    value=f"{countdown} 天"
                )
                st.caption(f"📅 {perf['日期']}")
                st.caption(f"📍 {perf['場地']}")
            else:
                st.info("目前無待辦演出")

    st.markdown("---") 

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

    st.caption("🎨 圖例說明： 🔴 **紅色 = 務必出席** | 🟡 **黃色 = 演出** | 🟠 **褐字 = 包含小團**")

else:
    st.warning("⚠️ 目前讀取不到有效資料，請檢查 Google Sheet 連結和內容。")

st.markdown("---")
st.caption("SCU Choir 2025 | Design with 💚 by 志行")
