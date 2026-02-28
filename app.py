import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime
import time

# 設定頁面
st.set_page_config(page_title="賓果三星神算", page_icon="🎰", layout="centered")

# --- 核心功能：官方 API 直連 ---

@st.cache_data(ttl=30)  # 縮短快取時間為 30 秒，確保即時性
def get_bingo_data_v8():
    """
    V8.0 官方 API 直連版 (No-Dependency)
    直接請求台灣彩券官方 App 使用的後端 API
    """
    # 這是台彩官方 App 和新版官網使用的 API 端點
    api_url = "https://api.content.taiwanlottery.com/v1/result/bingo"
    
    # 只需要最基本的偽裝，不用 cloudscraper
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        "Accept": "application/json",
        "Origin": "https://www.taiwanlottery.com.tw",
        "Referer": "https://www.taiwanlottery.com.tw/"
    }
    
    try:
        # 加上 timeout 避免卡死
        response = requests.get(api_url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            st.error(f"API 連線異常: {response.status_code}")
            return pd.DataFrame(), "連線失敗"

        # 解析 JSON
        data = response.json()
        
        # 官方 API 結構通常放在 'content' 裡面
        raw_list = data.get('content', [])
        
        parsed_data = []
        
        for item in raw_list:
            # 官方欄位名稱確認：
            # prizeNo: 一般號碼 (陣列)
            # superPrizeNo: 超級獎號 (整數)
            # period: 期別 (字串)
            
            if 'prizeNo' in item and 'superPrizeNo' in item:
                # 取得一般號碼
                nums = item['prizeNo']
                
                # 確保格式正確 (有時候 API 會給字串陣列)
                nums = [int(n) for n in nums]
                
                # 賓果應該有 20 個號碼
                if len(nums) == 20:
                    # 這裡是重點：官方 API 的號碼通常是「由小到大」排序好的
                    # 但賓果開獎順序其實沒差，我們只要這 20 個號碼
                    parsed_data.append(nums)
        
        if parsed_data:
            return pd.DataFrame(parsed_data), "台灣彩券官方 API"
            
        return pd.DataFrame(), "無數據回傳"

    except Exception as e:
        print(f"API Error: {e}")
        return pd.DataFrame(), f"系統錯誤: {e}"

def analyze_numbers(df, periods=20):
    if df.empty: return None, None, None
    
    # 取最近 N 期
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
st.caption("🚀 核心：官方 API 直連 (V8.0)")

# 側邊欄
st.sidebar.header("設定")
analyze_period = st.sidebar.slider("分析期數", 10, 50, 20)
if st.sidebar.button("🔄 強制刷新"):
    st.cache_data.clear()
    st.rerun()

# 執行抓取
with st.spinner('正在同步官方數據...'):
    df_history, source_name = get_bingo_data_v8()

if not df_history.empty:
    st.success(f"✅ 連線成功！來源：{source_name}")
    
    hot_df, cold_df, recent_df = analyze_numbers(df_history, analyze_period)
    
    # 顯示最新一期
    if not recent_df.empty:
        latest_draw = recent_df.iloc[0].tolist()
        st.markdown("### 📢 最新開獎")
        
        # 官方 API 給的號碼通常是排序過的，這裡保持原樣顯示
        c1 = st.columns(10)
        c2 = st.columns(10)
        for i, num in enumerate(latest_draw):
            if i < 10:
                c1[i].markdown(f"**{num:02d}**")
            elif i < 20:
                c2[i-10].markdown(f"**{num:02d}**")

    st.markdown("---")
    
    # 推薦區塊
    st.header("🎯 三星推薦")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.error("🔥 追熱門")
        if hot_df is not None and len(hot_df) >= 3:
            top = hot_df.head(3)['number'].tolist()
            st.metric("號碼", f"{top[0]:02d}, {top[1]:02d}, {top[2]:02d}")
            st.caption("近期最熱")
            
    with col2:
        st.info("❄️ 抓冷門")
        if cold_df is not None and len(cold_df) >= 3:
            bot = cold_df.head(3)['number'].tolist()
            st.metric("號碼", f"{bot[0]:02d}, {bot[1]:02d}, {bot[2]:02d}")
            st.caption("近期最冷")

    with col3:
        st.warning("⚖️ 混合")
        if hot_df is not None and len(hot_df) >= 2 and cold_df is not None:
            mix = hot_df.head(2)['number'].tolist() + cold_df.head(1)['number'].tolist()
            st.metric("號碼", f"{mix[0]:02d}, {mix[1]:02d}, {mix[2]:02d}")
            st.caption("2熱 + 1冷")

    with st.expander("📊 查看詳細統計"):
        st.dataframe(hot_df)

else:
    st.error("❌ 無法取得數據")
    st.write("請確認您的網路連線，或稍後再試。")
