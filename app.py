import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib3
import time

# 關閉 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="賓果三星神算", page_icon="🎰", layout="centered")

# --- 核心功能：多重來源抓取系統 ---

def fetch_from_9800():
    """來源 1: 9800.com.tw"""
    url = "https://www.9800.com.tw/lotto80/"
    try:
        response = requests.get(url, timeout=10, verify=False)
        response.encoding = 'utf-8' # 或 big5，視情況自動調整
        if response.status_code != 200: return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        # 尋找包含獎號的表格
        # 9800 通常將獎號放在特定的 class 或結構中
        # 這裡使用通用的「抓取大量數字」策略
        
        data_list = []
        # 抓取所有表格列
        rows = soup.find_all('tr')
        
        for row in rows:
            text = row.get_text()
            import re
            # 抓取 1-80 的數字
            nums = re.findall(r'\b(0?[1-9]|[1-7][0-9]|80)\b', text)
            
            # 賓果每期 20 個號碼 + 1 超級獎號 + 期數等，通常大於 20 個數字
            if len(nums) >= 20:
                # 嘗試過濾：通常期數是很大的數字(如113054123)，獎號是1-80
                # 取最後 20 個 1-80 的數字作為獎號
                draw_nums = [int(n) for n in nums if 1 <= int(n) <= 80]
                
                # 確保至少有 20 個號碼 (賓果開 20 個)
                if len(draw_nums) >= 20:
                    # 取最後 20 個 (假設前面的可能是日期月份等小數字)
                    # 或是取前 20 個? 需觀察網站。
                    # 通常網站排序是：期數, 號碼1...號碼20, 超級獎號...
                    # 9800 的排列通常很整齊
                    
                    # 這裡採取保守策略：取該列最後 20 個介於 1-80 的數字
                    final_nums = draw_nums[-20:]
                    data_list.append(final_nums)
                    
        return pd.DataFrame(data_list)
    except Exception as e:
        print(f"9800 Error: {e}")
        return None

def fetch_from_lotto8():
    """來源 2: Lotto-8 (嘗試不同網址)"""
    # 嘗試 HTTP 而非 HTTPS，有時能避開憑證問題
    url = "http://www.lotto-8.com/listbingo.asp" 
    try:
        response = requests.get(url, timeout=10, verify=False)
        response.encoding = 'big5'
        if response.status_code != 200: return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        data_list = []
        rows = soup.find_all('tr')
        for row in rows:
            text = row.get_text()
            import re
            nums = re.findall(r'\b(0?[1-9]|[1-7][0-9]|80)\b', text)
            if len(nums) >= 20:
                draw_nums = [int(n) for n in nums[-20:]]
                data_list.append(draw_nums)
        return pd.DataFrame(data_list)
    except Exception as e:
        print(f"Lotto-8 Error: {e}")
        return None

def fetch_from_official():
    """來源 3: 台灣彩券官網 (僅抓取首頁最新幾期)"""
    url = "https://www.taiwanlottery.com.tw/Lotto/BINGOBINGO/drawing.aspx"
    try:
        # 官網擋爬蟲較嚴，需完整 Headers
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        if response.status_code != 200: return None
        
        # 官網結構較複雜，通常有特定 ID
        dfs = pd.read_html(response.text)
        
        # 尋找最大的表格
        target_df = None
        for df in dfs:
            if df.shape[1] > 10 and df.shape[0] >= 1:
                target_df = df
                break
        
        if target_df is None: return None

        data_list = []
        for index, row in target_df.iterrows():
            row_str = " ".join(row.astype(str).tolist())
            import re
            nums = re.findall(r'\b(0?[1-9]|[1-7][0-9]|80)\b', row_str)
            if len(nums) >= 20:
                data_list.append([int(n) for n in nums[-20:]])
                
        return pd.DataFrame(data_list)
    except Exception as e:
        print(f"Official Error: {e}")
        return None

@st.cache_data(ttl=60)
def get_bingo_data_multi_source():
    """
    智慧調度器：依序嘗試所有來源
    """
    # 1. 嘗試 9800
    df = fetch_from_9800()
    if df is not None and not df.empty:
        return df, "來源: 9800.com.tw (穩定)"
    
    # 2. 嘗試 Lotto-8
    df = fetch_from_lotto8()
    if df is not None and not df.empty:
        return df, "來源: Lotto-8 (備用)"
        
    # 3. 嘗試 官網
    df = fetch_from_official()
    if df is not None and not df.empty:
        return df, "來源: 台灣彩券官網 (權威)"
    
    return pd.DataFrame(), "所有來源皆無法連線"

def analyze_numbers(df, periods=20):
    if df.empty: return None, None, None
    
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
st.caption("版本：V4.0 終極多源版")

# 側邊欄
st.sidebar.header("設定")
analyze_period = st.sidebar.slider("分析期數", 10, 50, 20)
if st.sidebar.button("🔄 強制刷新"):
    st.cache_data.clear()
    st.rerun()

# 執行抓取
with st.spinner('正在搜尋最佳線路...'):
    df_history, source_name = get_bingo_data_multi_source()

if not df_history.empty:
    st.success(f"✅ 連線成功！ | {source_name}")
    
    hot_df, cold_df, recent_df = analyze_numbers(df_history, analyze_period)
    
    # 顯示最新一期
    latest_draw = recent_df.iloc[0].tolist()
    st.markdown("### 📢 最新開獎")
    
    # 美化顯示
    s_cols = st.columns(10)
    for i in range(10):
        if i < len(latest_draw):
            s_cols[i].markdown(f"**{latest_draw[i]:02d}**")
    s_cols2 = st.columns(10)
    for i in range(10):
        if i+10 < len(latest_draw):
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
    st.error("❌ 所有來源皆無法連線")
    st.write("這通常是雲端主機 IP 遭到台灣網站全面封鎖。")
    st.info("建議解決方案：\n1. 請過 10 分鐘後再試 (可能是暫時性阻擋)\n2. 檢查您的網路環境是否正常")
