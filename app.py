import streamlit as st
import pandas as pd
import requests
import lxml

# 1. 必須是第一個執行的指令
st.set_page_config(page_title="賓果三星神算", page_icon="🎰", layout="centered")

# --- 核心功能函數 ---

@st.cache_data(ttl=60)
def get_bingo_data():
    """
    抓取賓果賓果近期獎號 (防卡死版)
    """
    # 備用來源列表 (若主來源掛掉，可擴充)
    url = "https://www.lotto-8.com/listbingo.asp" 
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    
    try:
        # 設定 timeout=10 秒，避免無限等待造成黑畫面
        response = requests.get(url, headers=headers, timeout=10)
        
        # Lotto-8 通常是 Big5 編碼，若亂碼可嘗試 'cp950' 或 'utf-8'
        # 先嘗試自動偵測，若失敗則手動指定
        response.encoding = 'big5' 
        
        if response.status_code != 200:
            return pd.DataFrame()
            
        # 使用 Pandas 讀取 HTML 表格
        # match參數確保抓到包含「期別」或「開獎號碼」的表格
        dfs = pd.read_html(response.text, flavor='bs4')
        
        target_df = None
        for df in dfs:
            # 賓果表格特徵：寬度大於5欄，列數大於10
            if df.shape[1] > 10 and df.shape[0] > 5:
                target_df = df
                break
        
        if target_df is None:
            return pd.DataFrame()

        # 資料清理
        clean_data = []
        for index, row in target_df.iterrows():
            row_str = " ".join(row.astype(str).tolist())
            import re
            # 抓取 1-80 的數字 (排除日期格式)
            numbers = re.findall(r'\b(0?[1-9]|[1-7][0-9]|80)\b', row_str)
            
            # 賓果有 20 個號碼 + 1 個超級獎號，通常一列會有 20+ 個數字
            if len(numbers) >= 20:
                # 取最後 20 個號碼
                draw_numbers = [int(n) for n in numbers[-20:]]
                clean_data.append(draw_numbers)
        
        return pd.DataFrame(clean_data)

    except Exception as e:
        # 在 log 中印出錯誤，但不阻擋程式執行
        print(f"Error fetching data: {e}")
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

# 側邊欄
st.sidebar.header("設定")
analyze_period = st.sidebar.slider("分析期數", 10, 50, 20)
if st.sidebar.button("🔄 強制刷新"):
    st.cache_data.clear()
    st.rerun()

# 狀態指示
status_text = st.empty()
status_text.text("正在連線更新數據...")

# 執行抓取
df_history = get_bingo_data()

# 清除狀態文字
status_text.empty()

if not df_history.empty:
    st.success(f"✅ 數據更新成功 (最新 {len(df_history)} 期)")
    
    hot_df, cold_df, recent_df = analyze_numbers(df_history, analyze_period)
    
    # 顯示最新一期
    latest_draw = recent_df.iloc[0].tolist()
    st.markdown("### 📢 最新開獎")
    cols = st.columns(5)
    for i, num in enumerate(latest_draw[:5]): # 只秀前5個示意，避免版面太亂
        cols[i].metric(label=f"球號 {i+1}", value=f"{num:02d}")
    st.caption("...等共 20 個號碼")

    st.markdown("---")
    
    # 推薦區塊
    st.header("🎯 三星推薦")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.error("🔥 追熱門")
        if hot_df is not None:
            top_3 = hot_df.head(3)['number'].tolist()
            # 檢查是否有足夠號碼
            if len(top_3) >= 3:
                st.markdown(f"**{top_3[0]:02d}, {top_3[1]:02d}, {top_3[2]:02d}**")
            
    with col2:
        st.info("❄️ 抓冷門")
        if cold_df is not None:
            bottom_3 = cold_df.head(3)['number'].tolist()
            if len(bottom_3) >= 3:
                st.markdown(f"**{bottom_3[0]:02d}, {bottom_3[1]:02d}, {bottom_3[2]:02d}**")

    with col3:
        st.warning("⚖️ 混合")
        if hot_df is not None and len(hot_df) >= 2 and cold_df is not None:
            mix_nums = hot_df.head(2)['number'].tolist() + cold_df.head(1)['number'].tolist()
            st.markdown(f"**{mix_nums[0]:02d}, {mix_nums[1]:02d}, {mix_nums[2]:02d}**")

    st.markdown("---")
    with st.expander("📊 查看詳細統計"):
        st.dataframe(hot_df)

else:
    st.warning("⚠️ 目前無法抓取數據。")
    st.info("可能原因：\n1. 網站正在維護\n2. 雲端 IP 被暫時阻擋\n3. 請過幾分鐘後按左側「強制刷新」再試。")
    
    # 顯示一個假資料示意，確認 UI 沒壞
    st.markdown("---")
    st.caption("系統測試模式：若您看到此行字，代表 App 正常，僅是資料源暫時無法連線。")
