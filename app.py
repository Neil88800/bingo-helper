import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib3
import re

# 忽略 SSL 安全警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="賓果三星神算", page_icon="🎰", layout="centered")

# --- 核心抓取邏輯：針對 Kuaishou1688 ---

@st.cache_data(ttl=60)  # 設定 60 秒快取
def get_bingo_data():
    """
    來源: 快手網 (bingo.kuaishou1688.com)
    """
    url = "https://bingo.kuaishou1688.com/"
    
    # 偽裝成真實的 Chrome 瀏覽器 (這對快手網很重要)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.google.com/"
    }
    
    try:
        # verify=False 忽略 SSL 驗證
        response = requests.get(url, headers=headers, verify=False, timeout=15)
        response.encoding = 'utf-8' # 快手網通常是 utf-8
        
        if response.status_code != 200:
            st.error(f"連線失敗，狀態碼: {response.status_code}")
            return pd.DataFrame()

        soup = BeautifulSoup(response.text, 'html.parser')
        data_list = []
        
        # 快手網的結構通常比較現代，可能用 table 或是 div list
        # 策略：抓取所有可能的「行容器」
        # 1. 先找 table row
        rows = soup.find_all('tr')
        
        # 如果找不到 tr，嘗試找 div class 含有 row 或 list 的元素 (備用方案)
        if not rows or len(rows) < 5:
             rows = soup.find_all('div', class_=re.compile(r'row|list|item'))

        for row in rows:
            # 取得該行所有文字
            text = row.get_text(" ", strip=True)
            
            # 使用正則表達式抓取 1-80 的數字
            # 快手網通常會顯示：期數(9碼) 時間 獎號(20個) 超級獎號
            all_nums = re.findall(r'\b(0?[1-9]|[1-7][0-9]|80)\b', text)
            
            # 轉換為數字
            nums_int = [int(n) for n in all_nums]
            
            # 過濾邏輯：
            # 1. 賓果獎號範圍是 1-80
            # 2. 一期會有 20 個一般號碼
            valid_bingo_nums = [n for n in nums_int if 1 <= n <= 80]
            
            # 如果這行包含 20 個以上的有效號碼，極有可能是獎號列
            if len(valid_bingo_nums) >= 20:
                # 截取「最後」20 個號碼 (排除前面的期數或前面的雜訊)
                # 假設最後一個數字可能是超級獎號或猜大小，我們保守取倒數 20 個
                # 快手網排列通常是：期數 ... 號碼1~20 ...
                
                # 這裡我們嘗試抓取最像獎號的一段
                # 如果有超級獎號，通常是第 21 個
                current_draw = valid_bingo_nums[-20:]
                
                # 再次確認這組號碼是否有重複 (賓果開獎不重複)
                if len(set(current_draw)) == 20:
                    data_list.append(current_draw)

        if not data_list:
            st.error("解析失敗：找不到符合格式的數據")
            # debug: 顯示一點點原始碼幫助除錯
            # st.text(soup.prettify()[:500])
            return pd.DataFrame()

        return pd.DataFrame(data_list)

    except Exception as e:
        st.error(f"系統錯誤: {e}")
        return pd.DataFrame()

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

st.title("🎰 賓果三星神算")
st.caption("資料來源：快手網 (Kuaishou)")

# 側邊欄
st.sidebar.header("設定")
analyze_period = st.sidebar.slider("分析期數", 10, 50, 20)
if st.sidebar.button("🔄 強制刷新"):
    st.cache_data.clear()
    st.rerun()

# 執行抓取
with st.spinner('正在連線至快手網...'):
    df_history = get_bingo_data()

if not df_history.empty:
    st.success(f"✅ 連線成功！分析近 {len(df_history)} 期數據")
    
    hot_df, cold_df, recent_df = analyze_numbers(df_history, analyze_period)
    
    # 顯示最新一期
    latest_draw = recent_df.iloc[0].tolist()
    st.markdown("### 📢 最新獎號")
    
    # 美化排版：分兩排顯示
    c1 = st.columns(10)
    c2 = st.columns(10)
    for i, num in enumerate(latest_draw):
        if i < 10:
            c1[i].markdown(f"**{num:02d}**")
        else:
            c2[i-10].markdown(f"**{num:02d}**")

    st.markdown("---")
    
    # 推薦區塊
    st.header("🎯 三星推薦")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.error("🔥 追熱門")
        if hot_df is not None:
            top_3 = hot_df.head(3)['number'].tolist()
            st.metric("號碼", f"{top_3[0]:02d}, {top_3[1]:02d}, {top_3[2]:02d}")
            st.caption("近期出現最多次")
            
    with col2:
        st.info("❄️ 抓冷門")
        if cold_df is not None:
            bottom_3 = cold_df.head(3)['number'].tolist()
            st.metric("號碼", f"{bottom_3[0]:02d}, {bottom_3[1]:02d}, {bottom_3[2]:02d}")
            st.caption("近期出現最少次")

    with col3:
        st.warning("⚖️ 混合")
        if hot_df is not None and len(hot_df) >= 2 and cold_df is not None:
            mix_nums = hot_df.head(2)['number'].tolist() + cold_df.head(1)['number'].tolist()
            st.metric("號碼", f"{mix_nums[0]:02d}, {mix_nums[1]:02d}, {mix_nums[2]:02d}")
            st.caption("2熱 + 1冷")

    st.markdown("---")
    with st.expander("📊 查看詳細歷史數據"):
        st.dataframe(df_history)

else:
    st.error("⚠️ 無法取得數據")
    st.write("可能原因：")
    st.write("1. 網站正在進行 Cloudflare 人機驗證")
    st.write("2. 雲端 IP 被暫時阻擋")
    st.info("請稍後按側邊欄「強制刷新」再試")
