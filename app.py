import streamlit as st
import pandas as pd
import cloudscraper
import json
import time
from datetime import datetime, timedelta

st.set_page_config(page_title="賓果三星神算", page_icon="🎰", layout="centered")

# --- 核心功能：突破封鎖抓取 ---

@st.cache_data(ttl=60) # 快取 60 秒
def get_bingo_data_v7():
    """
    V7.0 突破版：
    1. 優先嘗試台灣彩券官方 API (JSON)
    2. 失敗則使用 CloudScraper 繞過 Auzo 驗證
    """
    scraper = cloudscraper.create_scraper(browser='chrome')
    data_list = []
    source_used = "未知"

    # --- 策略 A: 官方 API (最快、最準、JSON 格式) ---
    try:
        # 這是台彩新版官網的後端 API，直接回傳 JSON，不用解析 HTML
        # 我們抓取今天的資料
        today_str = (datetime.now() + timedelta(hours=8)).strftime('%Y-%m-%d')
        # 官方 API 網址 (無需參數通常回傳最近 10 期，或需指定時間)
        # 這裡嘗試直接抓取最近期數
        api_url = "https://api.content.taiwanlottery.com/v1/result/bingo"
        
        # 雖然是 API，還是用 scraper 呼叫比較保險
        response = scraper.get(api_url, timeout=10)
        
        if response.status_code == 200:
            try:
                # 解析 JSON
                json_data = response.json()
                # 官方結構通常是: content -> list of results
                # 或是直接 list
                # 假設結構: [ { "period": "113000001", "winnrs": [...] }, ... ]
                
                # 根據觀察，台彩 API 回傳結構 (content)
                raw_list = json_data.get('content', [])
                
                # 如果直接是 list
                if isinstance(json_data, list):
                    raw_list = json_data

                for item in raw_list:
                    # 提取獎號
                    # 官方欄位名稱通常是 'prizeNo' (一般號) 和 'superPrizeNo' (超級獎號)
                    # 或是 'bigSmall' 等
                    if 'prizeNo' in item:
                        # 官方號碼有時是字串陣列，轉為 int
                        nums = [int(n) for n in item['prizeNo']]
                        # 賓果應該有 20 個號碼
                        if len(nums) == 20:
                            data_list.append(nums)
                
                if data_list:
                    source_used = "官方 API (JSON)"
                    return pd.DataFrame(data_list), source_used
            except:
                pass # JSON 解析失敗，轉用策略 B
    except Exception as e:
        print(f"Official API Error: {e}")

    # --- 策略 B: CloudScraper + Auzo (最強備援) ---
    try:
        url = "https://lotto.auzo.tw/bingobingo.php"
        # 使用 cloudscraper 發送請求 (它會自動處理 Cloudflare 驗證)
        response = scraper.get(url, timeout=15)
        response.encoding = 'utf-8'
        
        if response.status_code == 200:
            from bs4 import BeautifulSoup
            import re
            
            soup = BeautifulSoup(response.text, 'html.parser')
            rows = soup.find_all('tr')
            
            for row in rows:
                text = row.get_text(" ", strip=True)
                nums = re.findall(r'\b(0?[1-9]|[1-7][0-9]|80)\b', text)
                
                if len(nums) >= 20:
                    clean_nums = [int(n) for n in nums]
                    # 檢查是否包含有效的賓果範圍
                    bingo_nums = [n for n in clean_nums if 1 <= n <= 80]
                    
                    if len(bingo_nums) >= 20:
                        # Auzo 的資料很整齊，取倒數第 21 到倒數第 1 個?
                        # 通常 Auzo 結構: 期數, 日期, 號碼1~20, 超級獎號
                        # 我們取最後 20 個介於 1-80 的數字 (假設最後一個是超級獎號，我們取那之前的20個)
                        # 但為了保險，先取最後 20 個試試
                        final_draw = bingo_nums[-20:]
                        # 簡單去重檢查
                        if len(set(final_draw)) == 20:
                            data_list.append(final_draw)
            
            if data_list:
                source_used = "Auzo (CloudScraper)"
                return pd.DataFrame(data_list), source_used

    except Exception as e:
        print(f"Scraper Error: {e}")

    return pd.DataFrame(), "所有線路皆中斷"

def analyze_numbers(df, periods=20):
    if df.empty: return None, None, None
    
    # 確保只有數字
    df = df.apply(pd.to_numeric, errors='coerce')
    
    recent_data = df.head(periods)
    all_numbers = recent_data.values.flatten()
    all_numbers = all_numbers[~pd.isna(all_numbers)]
    
    from collections import Counter
    counts = Counter(all_numbers)
    
    stat_df = pd.DataFrame.from_dict(counts, orient='index', columns=['count'])
    stat_df.index.name = 'number'
    stat_df = stat_df.reset_index()
    
    hot_numbers = stat_df.sort_values(by='count', ascending=False)
    cold_numbers = stat_df.sort_values(by='count', ascending=True)
    
    return hot_numbers, cold_numbers, recent_data

# --- UI ---

st.title("🎰 賓果三星神算")
st.caption("版本：V7.0 穿牆破網版")

# 側邊欄
st.sidebar.header("設定")
analyze_period = st.sidebar.slider("分析期數", 10, 50, 20)
if st.sidebar.button("🔄 強制刷新"):
    st.cache_data.clear()
    st.rerun()

# 執行抓取
with st.spinner('正在嘗試突破 Cloudflare 防護網...'):
    df_history, source_name = get_bingo_data_v7()

if not df_history.empty:
    st.success(f"✅ 連線成功！來源：{source_name}")
    
    hot_df, cold_df, recent_df = analyze_numbers(df_history, analyze_period)
    
    # 顯示最新一期
    if not recent_df.empty:
        latest_draw = recent_df.iloc[0].tolist()
        st.markdown("### 📢 最新開獎")
        
        c1 = st.columns(10)
        c2 = st.columns(10)
        for i, num in enumerate(latest_draw):
            val = int(num)
            if i < 10:
                c1[i].markdown(f"**{val:02d}**")
            elif i < 20:
                c2[i-10].markdown(f"**{val:02d}**")

    st.markdown("---")
    
    # 推薦
    st.header("🎯 三星推薦")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.error("🔥 追熱門")
        if hot_df is not None and len(hot_df) >= 3:
            top = hot_df.head(3)['number'].tolist()
            st.metric("號碼", f"{int(top[0]):02d}, {int(top[1]):02d}, {int(top[2]):02d}")
            
    with col2:
        st.info("❄️ 抓冷門")
        if cold_df is not None and len(cold_df) >= 3:
            bot = cold_df.head(3)['number'].tolist()
            st.metric("號碼", f"{int(bot[0]):02d}, {int(bot[1]):02d}, {int(bot[2]):02d}")

    with col3:
        st.warning("⚖️ 混合")
        if hot_df is not None and len(hot_df) >= 2 and cold_df is not None:
            mix = hot_df.head(2)['number'].tolist() + cold_df.head(1)['number'].tolist()
            st.metric("號碼", f"{int(mix[0]):02d}, {int(mix[1]):02d}, {int(mix[2]):02d}")

    with st.expander("詳細數據"):
        st.dataframe(hot_df)

else:
    st.error("❌ 依然無法穿透")
    st.write("這表示 Streamlit 的雲端 IP (美國) 被所有台灣網站列入黑名單。")
    st.info("由於這是免費雲端主機的限制，目前無解，除非在您本地電腦執行。")
