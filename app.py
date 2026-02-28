import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib3
import re

# 忽略 SSL 安全警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="賓果三星神算", page_icon="🎰", layout="centered")

# --- 爬蟲核心功能 ---

def fetch_auzo():
    """
    來源 1: 奧索樂透網 (Auzo)
    特點：傳統表格結構，極易抓取
    """
    url = "https://lotto.auzo.tw/bingobingo.php"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, verify=False, timeout=10)
        response.encoding = 'utf-8' # 奧索通常是 utf-8
        
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        data_list = []
        
        # 奧索的獎號通常在表格的 td 裡面，且有特定的樣式
        # 這裡使用通用策略：抓取所有表格列
        rows = soup.find_all('tr')
        
        for row in rows:
            text = row.get_text(" ", strip=True) # 用空格分隔
            # 抓取所有 1-80 的數字
            nums = re.findall(r'\b(0?[1-9]|[1-7][0-9]|80)\b', text)
            
            # 過濾掉非獎號的雜訊 (賓果一期有20個獎號+1個超級獎號，通常大於20個數字)
            # 奧索的表格結構：期別, 開獎時間, 號碼1-20, 超級獎號...
            if len(nums) >= 20:
                # 轉換為整數
                clean_nums = [int(n) for n in nums]
                
                # 檢查這組數字是否包含有效的賓果範圍
                # 取這列中「最後」出現的 20 個介於 1-80 的數字 (通常前面的數字可能是期數)
                # 假設最後一個是超級獎號，我們取倒數第 21 到 倒數第 2 個
                # 或者簡單點：找出這列中連續出現的 1-80 數字群
                
                # 這裡採取最穩定的「取最多的一組」策略
                # 假設獎號位於中間或後段
                bingo_nums = [n for n in clean_nums if 1 <= n <= 80]
                
                # 如果這列有足夠的賓果號碼
                if len(bingo_nums) >= 20:
                    # 奧索的排版通常獎號是連在一起的，取最後 20 個 (或 21 個包含超級獎號)
                    # 為了保險，我們取倒數第 20 個開始
                    final_draw = bingo_nums[-20:]
                    data_list.append(final_draw)
        
        if not data_list:
            return None
            
        return pd.DataFrame(data_list)

    except Exception as e:
        print(f"Auzo Error: {e}")
        return None

def fetch_winwin():
    """
    來源 2: WinWin (穩贏)
    """
    url = "https://winwin.tw/Bingo"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, verify=False, timeout=10)
        if response.status_code != 200:
            return None
        
        # WinWin 可能是動態網頁，如果 requests 抓不到資料，soup 會是空的
        soup = BeautifulSoup(response.text, 'html.parser')
        data_list = []
        
        # 針對 WinWin 的結構嘗試抓取
        # 尋找包含獎號的容器
        rows = soup.find_all(['div', 'tr']) # 可能是 div 排版也可能是 table
        
        for row in rows:
            text = row.get_text(" ", strip=True)
            nums = re.findall(r'\b(0?[1-9]|[1-7][0-9]|80)\b', text)
            
            if len(nums) >= 20:
                clean_nums = [int(n) for n in nums if 1 <= int(n) <= 80]
                if len(clean_nums) >= 20:
                    # WinWin 排版：期數 號碼...
                    data_list.append(clean_nums[-20:])
        
        # 去重 (因為 div 結構可能會重複抓到)
        if data_list:
            # 將 list 轉 tuple 才能 hash 去重
            data_list = [list(x) for x in set(tuple(x) for x in data_list)]
            # 排序回原本順序 (簡單依據第一個號碼或總和判斷) - 這裡略過排序，直接回傳
            
        return pd.DataFrame(data_list) if data_list else None

    except Exception as e:
        print(f"WinWin Error: {e}")
        return None

@st.cache_data(ttl=60) # 60秒快取
def get_bingo_data():
    """
    雙來源調度器
    """
    # 優先嘗試 Auzo (結構最簡單，成功率最高)
    df = fetch_auzo()
    if df is not None and not df.empty:
        return df, "Auzo 奧索樂透網"
    
    # 備用嘗試 WinWin
    df = fetch_winwin()
    if df is not None and not df.empty:
        return df, "WinWin 穩贏網"
    
    return pd.DataFrame(), "所有來源皆無法連線"

def analyze_numbers(df, periods=20):
    if df.empty: return None, None, None
    
    # 確保資料是數值型
    df = df.apply(pd.to_numeric, errors='coerce')
    
    recent_data = df.head(periods)
    all_numbers = recent_data.values.flatten()
    # 移除 NaN
    all_numbers = all_numbers[~pd.isna(all_numbers)]
    
    from collections import Counter
    counts = Counter(all_numbers)
    
    stat_df = pd.DataFrame.from_dict(counts, orient='index', columns=['count'])
    stat_df.index.name = 'number'
    stat_df = stat_df.reset_index()
    
    hot_numbers = stat_df.sort_values(by='count', ascending=False)
    cold_numbers = stat_df.sort_values(by='count', ascending=True)
    
    return hot_numbers, cold_numbers, recent_data

# --- UI 介面 ---

st.title("🎰 賓果三星神算")

# 側邊欄
st.sidebar.header("設定")
analyze_period = st.sidebar.slider("分析期數", 10, 50, 20)
if st.sidebar.button("🔄 刷新數據"):
    st.cache_data.clear()
    st.rerun()

# 執行抓取
with st.spinner('正在連線至 Auzo / WinWin...'):
    df_history, source_name = get_bingo_data()

if not df_history.empty:
    st.success(f"✅ 成功連線：{source_name}")
    
    hot_df, cold_df, recent_df = analyze_numbers(df_history, analyze_period)
    
    # 顯示最新一期
    if not recent_df.empty:
        latest_draw = recent_df.iloc[0].tolist()
        st.markdown("### 📢 最新獎號")
        
        # 顯示排版
        cols1 = st.columns(10)
        cols2 = st.columns(10)
        
        for i, num in enumerate(latest_draw):
            if i < 10:
                cols1[i].markdown(f"**{int(num):02d}**")
            elif i < 20:
                cols2[i-10].markdown(f"**{int(num):02d}**")

    st.markdown("---")
    
    # 推薦區塊
    st.header("🎯 三星推薦")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.error("🔥 追熱門")
        if hot_df is not None and len(hot_df) >= 3:
            top_3 = hot_df.head(3)['number'].tolist()
            st.metric("號碼", f"{int(top_3[0]):02d}, {int(top_3[1]):02d}, {int(top_3[2]):02d}")
            st.caption("近期最熱")
            
    with col2:
        st.info("❄️ 抓冷門")
        if cold_df is not None and len(cold_df) >= 3:
            bottom_3 = cold_df.head(3)['number'].tolist()
            st.metric("號碼", f"{int(bottom_3[0]):02d}, {int(bottom_3[1]):02d}, {int(bottom_3[2]):02d}")
            st.caption("近期最冷")

    with col3:
        st.warning("⚖️ 混合")
        if hot_df is not None and len(hot_df) >= 2 and cold_df is not None:
            mix_nums = hot_df.head(2)['number'].tolist() + cold_df.head(1)['number'].tolist()
            st.metric("號碼", f"{int(mix_nums[0]):02d}, {int(mix_nums[1]):02d}, {int(mix_nums[2]):02d}")
            st.caption("2熱 + 1冷")

    st.markdown("---")
    with st.expander("📊 查看詳細數據源"):
        st.dataframe(df_history.head(10))

else:
    st.error("❌ 兩個來源皆無法抓取數據")
    st.write("可能原因：")
    st.write("1. 雲端主機 IP 被 Auzo 與 WinWin 封鎖")
    st.write("2. 網站結構暫時變更")
    st.info("請稍後按側邊欄「刷新數據」重試")
