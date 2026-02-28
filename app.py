import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib3

# 關閉 SSL 警告 (針對某些憑證較舊的網站)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="賓果三星神算", page_icon="🎰", layout="centered")

# --- 核心功能函數 ---

@st.cache_data(ttl=60)
def get_bingo_data():
    """
    V3 強力抓取版：使用 BeautifulSoup 手動解析 + 忽略 SSL
    """
    url = "https://www.lotto-8.com/listbingo.asp" 
    
    # 偽裝成一般的瀏覽器
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    }
    
    try:
        # verify=False 忽略 SSL 驗證，timeout=15 避免卡死
        response = requests.get(url, headers=headers, verify=False, timeout=15)
        
        # 強制設定編碼 (解決亂碼關鍵)
        response.encoding = 'big5'
        
        if response.status_code != 200:
            st.error(f"連線失敗，狀態碼: {response.status_code}")
            return pd.DataFrame()

        # 使用 BeautifulSoup 解析 HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 尋找所有表格
        tables = soup.find_all('table')
        target_table = None
        
        # 策略：尋找包含最多數字的那個表格
        max_rows = 0
        for table in tables:
            rows = table.find_all('tr')
            if len(rows) > max_rows:
                max_rows = len(rows)
                target_table = table
        
        if not target_table:
            st.error("找不到數據表格")
            return pd.DataFrame()

        # 開始解析表格內容
        data_list = []
        rows = target_table.find_all('tr')
        
        for row in rows:
            cols = row.find_all(['td', 'th'])
            # 將該列所有文字串接
            row_text = " ".join([ele.text.strip() for ele in cols])
            
            # 使用正則表達式抓取數字 (1-80)
            import re
            # 抓取獨立的數字
            numbers = re.findall(r'\b(0?[1-9]|[1-7][0-9]|80)\b', row_text)
            
            # 賓果每期有 20 個號碼，通常如果抓到超過 15 個數字就算是有獎號的列
            if len(numbers) >= 20:
                # 取最後 20 個 (因為前面可能是期數或日期)
                draw_numbers = [int(n) for n in numbers[-20:]]
                data_list.append(draw_numbers)
        
        if not data_list:
            st.error("解析後無數據，可能是網站改版")
            return pd.DataFrame()

        return pd.DataFrame(data_list)

    except Exception as e:
        st.error(f"系統錯誤: {str(e)}")
        return pd.DataFrame()

def analyze_numbers(df, periods=20):
    if df.empty:
        return None, None, None
    
    recent_data = df.head(periods)
    all_numbers = recent_data.values.flatten()
    from collections import Counter
    counts = Counter(all_numbers)
    
    stat_df = pd.DataFrame.from_dict(counts, orient='index', columns=['count'])
    stat_df.index.name = 'number'
    stat_df = stat_df.reset_index()
    
    hot_numbers = stat_df.sort_values(by='count', ascending=False)
    cold_numbers = stat_df.sort_values(by='count', ascending=True)
    
    return hot_numbers, cold_numbers, recent_data

# --- UI 介面 ---

st.title("🎰 賓果賓果：三星神算")
st.caption("版本：V3.0 強力連線版")

# 側邊欄
st.sidebar.header("設定")
analyze_period = st.sidebar.slider("分析期數", 10, 50, 20)
if st.sidebar.button("🔄 強制刷新"):
    st.cache_data.clear()
    st.rerun()

# 執行抓取
with st.spinner('正在連線至台灣資料庫...'):
    df_history = get_bingo_data()

if not df_history.empty:
    st.success(f"✅ 數據更新成功！(分析近 {len(df_history)} 期)")
    
    hot_df, cold_df, recent_df = analyze_numbers(df_history, analyze_period)
    
    # 顯示最新一期
    latest_draw = recent_df.iloc[0].tolist()
    st.markdown("### 📢 最新開獎")
    
    # 美化顯示
    s_cols = st.columns(10)
    for i in range(10):
        s_cols[i].markdown(f"**{latest_draw[i]:02d}**")
    s_cols2 = st.columns(10)
    for i in range(10):
        s_cols2[i].markdown(f"**{latest_draw[i+10]:02d}**")

    st.markdown("---")
    
    # 推薦區塊
    st.header("🎯 三星推薦")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.error("🔥 追熱門")
        if hot_df is not None:
            top_3 = hot_df.head(3)['number'].tolist()
            if len(top_3) >= 3:
                st.metric("號碼", f"{top_3[0]:02d}, {top_3[1]:02d}, {top_3[2]:02d}")
                st.caption("近期出現最多次")
            
    with col2:
        st.info("❄️ 抓冷門")
        if cold_df is not None:
            bottom_3 = cold_df.head(3)['number'].tolist()
            if len(bottom_3) >= 3:
                st.metric("號碼", f"{bottom_3[0]:02d}, {bottom_3[1]:02d}, {bottom_3[2]:02d}")
                st.caption("近期出現最少次")

    with col3:
        st.warning("⚖️ 混合")
        if hot_df is not None and len(hot_df) >= 2 and cold_df is not None:
            mix_nums = hot_df.head(2)['number'].tolist() + cold_df.head(1)['number'].tolist()
            st.metric("號碼", f"{mix_nums[0]:02d}, {mix_nums[1]:02d}, {mix_nums[2]:02d}")
            st.caption("2 熱 + 1 冷")

    st.markdown("---")
    with st.expander("📊 查看詳細統計"):
        st.dataframe(hot_df)

else:
    st.warning("⚠️ 仍然無法抓取數據。")
    st.write("請檢查上方出現的紅色錯誤訊息。")
