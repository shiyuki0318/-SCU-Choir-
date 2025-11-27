import streamlit as st
import pandas as pd
from datetime import datetime

# --- 1. 網頁基礎設定 ---
st.set_page_config(
    page_title="SCU Choir 排練進度", 
    page_icon="🎵", 
    layout="wide"
)

# 自訂 CSS 樣式 - 溫暖大地色系
st.markdown("""
<style>
    /* 主要背景 - 溫暖米色 */
    .stApp {
        background: linear-gradient(135deg, #F5E6D3 0%, #E8D5C4 100%);
    }
    
    /* 標題區域 */
    h1 {
        color: #6B4423 !important;
        font-weight: 700 !important;
        text-shadow: 2px 2px 4px rgba(107, 68, 35, 0.1);
    }
    
    h3 {
        color: #8B6F47 !important;
    }
    
    /* 側邊欄樣式 */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #D4B896 0%, #C9A87C 100%);
    }
    
    [data-testid="stSidebar"] h2 {
        color: #6B4423 !important;
    }
    
    /* 表格樣式 */
    [data-testid="stDataFrame"] {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 4px 12px rgba(107, 68, 35, 0.15);
    }
    
    /* 成功提示框 */
    .stSuccess {
        background-color: #E8D5C4;
        border-left: 4px solid #A67C52;
        color: #6B4423;
    }
    
    /* 警告提示框 */
    .stWarning {
        background-color: #F5E6D3;
        border-left: 4px solid #D4A574;
    }
    
    /* 按鈕樣式 */
    .stButton>button {
        background-color: #A67C52;
        color: white;
        border-radius: 8px;
        border: none;
        font-weight: 600;
    }
    
    .stButton>button:hover {
        background-color: #8B6F47;
        box-shadow: 0 4px 8px rgba(107, 68, 35, 0.2);
    }
    
    /* Checkbox 樣式 */
    [data-testid="stCheckbox"] label {
        color: #6B4423 !important;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

st.title("🎵 SCU Choir 東吳校友合唱團 | 2025 排練看板")
st.markdown("### 🍂 溫暖排練，效率滿點")
st.markdown("---")

# --- 2. 讀取資料 ---
sheet_id = "1tR6BGppgC_VEKUqJ_pBs3T26Lg54VdGQOYHHzzKLImE"
gid = "0"
sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"

@st.cache_data(ttl=60)
def load_data(url):
    try:
        df = pd.read_csv(url, header=None)
        df = df.iloc[:, :7] 
        df.columns = ['月份', '日期', '時段', '時間', '進度內容', '場地', '備註']
        
        # 數據清洗
        df['月份'] = df['月份'].ffill()
        df = df[df['日期'].astype(str).str.contains(r'\d', na=False)]
        df = df.fillna("")

        # 智慧標籤系統
        def tag_row(row):
            content = str(row['進度內容']) + str(row['備註'])
            content_lower = content.lower()
            
            # 判斷是否為「僅樂手」
            if "僅樂手" in content or "band only" in content_lower or "樂手" in content and "團員" not in content:
                return "musician"
            
            # 判斷小團/室內團
            is_small = "小團" in content or "室內團" in content or "chamber" in content_lower
            
            # 判斷大團
            is_large = "大團" in content or "全體" in content or "全部人員" in content or "所有曲目" in content or "tutti" in content_lower
            
            if is_small and is_large:
                return "mixed"
            elif is_small:
                return "small"
            else:
                return "large"

        df['type'] = df.apply(tag_row, axis=1)
        
        return df
        
    except Exception as e:
        st.error(f"❌ 資料讀取發生錯誤：{e}")
        st.info("💡 請確認 Google Sheet 已設定為「知道連結的任何人」可檢視")
        return pd.DataFrame()

df = load_data(sheet_url)

# --- 3. 顯示介面 ---
if not df.empty and "月份" in df.columns:
    
    # 側邊欄篩選
    st.sidebar.header("🔍 排練篩選器")
    st.sidebar.markdown("---")
    
    # 身份選擇
    st.sidebar.markdown("### 👥 您的身份")
    show_small = st.sidebar.checkbox("✓ 我有參加「室內團 / 小團」", value=False, help="勾選後會顯示小團的排練行程")
    
    st.sidebar.markdown("---")
    
    # 月份篩選
    st.sidebar.markdown("### 📅 月份篩選")
    all_months = df["月份"].unique().tolist()
    selected_month = st.sidebar.multiselect("選擇月份", all_months, default=all_months)
    
    st.sidebar.markdown("---")
    
    # 關鍵字搜尋
    st.sidebar.markdown("### 🔎 關鍵字搜尋")
    search_keyword = st.sidebar.text_input("輸入關鍵字", placeholder="例：Mozart、12/25")

    # 篩選邏輯
    filtered_df = df.copy()
    
    # 1. 先過濾掉「僅樂手」的行程（所有人都不需要看到）
    filtered_df = filtered_df[filtered_df['type'] != 'musician']
    
    # 2. 根據身份篩選
    if not show_small:
        # 只顯示大團和混合行程
        filtered_df = filtered_df[filtered_df['type'].isin(['large', 'mixed'])]
    
    # 3. 月份篩選
    if selected_month:
        filtered_df = filtered_df[filtered_df["月份"].isin(selected_month)]
    
    # 4. 關鍵字搜尋
    if search_keyword:
        mask = filtered_df.apply(lambda x: x.astype(str).str.contains(search_keyword, case=False).any(), axis=1)
        filtered_df = filtered_df[mask]

    # 今日提醒
    today_str = datetime.now().strftime("%m/%d")
    today_rehearsal = filtered_df[filtered_df['日期'].astype(str).str.contains(today_str, na=False)]
    
    if not today_rehearsal.empty:
        st.success(f"🔔 **提醒：今天 ({today_str}) 有排練！**")
        today_display = today_rehearsal[['月份', '日期', '時段', '時間', '進度內容', '場地', '備註']].copy()
        st.dataframe(today_display, use_container_width=True, hide_index=True)
        st.markdown("---")

    # 主表格顯示
    st.subheader(f"📅 排練日程表 ({len(filtered_df)} 筆)")
    
    # 準備顯示的資料
    display_df = filtered_df[['月份', '日期', '時段', '時間', '進度內容', '場地', '備註', 'type']].copy()
    
    # 自訂樣式函數 - 加強視覺區分
    def style_dataframe(df):
        def apply_styles(row):
            # 月份交替顏色
            month_colors = {
                month: '#FFFFFF' if i % 2 == 0 else '#FFF8E7'
                for i, month in enumerate(df['月份'].unique())
            }
            bg_color = month_colors.get(row['月份'], '#FFFFFF')
            
            # 小團/混合行程：加粗 + 深褐色 + 淺黃色背景
            if row['type'] in ['small', 'mixed']:
                return [
                    f'background-color: #FFF4D4; font-weight: 900; color: #6B4423; border-left: 5px solid #D4A574;',  # 月份
                    f'background-color: #FFF4D4; font-weight: 900; color: #6B4423;',  # 日期
                    f'background-color: #FFF4D4; font-weight: 900; color: #6B4423;',  # 時段
                    f'background-color: #FFF4D4; font-weight: 900; color: #6B4423;',  # 時間
                    f'background-color: #FFF4D4; font-weight: 900; color: #6B4423;',  # 進度內容
                    f'background-color: #FFF4D4; font-weight: 900; color: #6B4423;',  # 場地
                    f'background-color: #FFF4D4; font-weight: 900; color: #6B4423;',  # 備註
                    ''  # type (隱藏)
                ]
            # 大團行程：正常字體 + 月份交替色
            else:
                return [
                    f'background-color: {bg_color}; color: #5D4E37; border-left: 3px solid transparent;',
                    f'background-color: {bg_color}; color: #5D4E37;',
                    f'background-color: {bg_color}; color: #5D4E37;',
                    f'background-color: {bg_color}; color: #5D4E37;',
                    f'background-color: {bg_color}; color: #5D4E37;',
                    f'background-color: {bg_color}; color: #5D4E37;',
                    f'background-color: {bg_color}; color: #5D4E37;',
                    ''
                ]
        
        return df.style.apply(apply_styles, axis=1)
    
    styled_df = style_dataframe(display_df)
    
    # 顯示表格（不顯示 type 欄位）
    columns_to_display = ['月份', '日期', '時段', '時間', '進度內容', '場地', '備註']
    
    st.dataframe(
        styled_df[columns_to_display], 
        use_container_width=True,
        hide_index=True,
        column_config={
            "月份": st.column_config.TextColumn("月份", width="small"),
            "日期": st.column_config.TextColumn("日期", width="small"),
            "時段": st.column_config.TextColumn("時段", width="small"),
            "時間": st.column_config.TextColumn("時間", width="medium"),
            "進度內容": st.column_config.TextColumn("進度內容", width="large"),
            "場地": st.column_config.TextColumn("場地", width="medium"),
            "備註": st.column_config.TextColumn("備註", width="medium", help="⚠️ 注意事項"),
        },
        height=600
    )

    # 圖例說明
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("🎨 **顏色說明**")
        st.markdown("- ⬜ 白色 / 🟨 淺黃色：月份交替顯示，方便閱讀")
        st.markdown("- 🟡 **粗體深褐色 + 黃色底**：包含小團/室內團排練")
    with col2:
        st.markdown("👥 **篩選功能**")
        st.markdown("- 未勾選「小團」：只看大團行程")
        st.markdown("- 勾選「小團」：顯示所有相關行程")
        st.markdown("- 「僅樂手」行程已自動隱藏")
    
else:
    st.warning("⚠️ 讀取不到有效資料，請檢查 Google Sheet 連結和權限設定。")
    
    with st.expander("📚 權限設定指引"):
        st.markdown("""
        ### 如何設定 Google Sheet 權限？
        
        1. 開啟您的 Google Sheet
        2. 點擊右上角「共用」按鈕
        3. 點擊「一般存取權」下的「限制」
        4. 選擇「**知道連結的任何人**」
        5. 權限設為「**檢視者**」
        6. 點擊「完成」
        7. 重新整理此頁面
        
        🔗 您的 Google Sheet：  
        https://docs.google.com/spreadsheets/d/1tR6BGppgC_VEKUqJ_pBs3T26Lg54VdGQOYHHzzKLImE/edit
        """)

st.markdown("---")
st.caption("🎵 SCU Choir 2025 | Design with 🤎")
