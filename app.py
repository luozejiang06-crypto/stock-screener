import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from deep_translator import MyMemoryTranslator, GoogleTranslator

st.set_page_config(page_title="S&P 500 QUANTITATIVE TERMINAL", layout="wide", initial_sidebar_state="expanded")

# 高可用金融 Logo 接口
def get_stock_logo_url(ticker):
    if pd.isna(ticker) or ticker is None:
        return "https://ui-avatars.com/api/?name=NA&background=181c26&color=38bdf8&rounded=true"
    clean_t = str(ticker).replace("-", "").replace(".", "").upper()
    return f"https://financialmodelingprep.com/image-stock/{clean_t}.png"

# 动态获取公司业务简介：优先免翻直连通道翻译，带原文对照
@st.cache_data(ttl=604800)
def get_company_summary_zh(ticker):
    try:
        t = yf.Ticker(ticker)
        raw_summary = t.info.get("longBusinessSummary", "")
        if not raw_summary:
            return "暂无该公司业务详细介绍。"
        
        trimmed = raw_summary[:350] + "..." if len(raw_summary) > 350 else raw_summary
        translated = ""
        
        try:
            translated = MyMemoryTranslator(source='en-US', target='zh-CN').translate(trimmed)
        except Exception:
            pass
            
        if not translated:
            try:
                translated = GoogleTranslator(source='auto', target='zh-CN').translate(trimmed)
            except Exception:
                pass

        if translated and translated != trimmed:
            return f"【中文业务速览】\n{translated}\n\n---\n【官方英文完整介绍】\n{raw_summary}"
        else:
            return f"【官方主营业务简介 (英文原文)】\n\n{raw_summary}"
    except Exception:
        return "暂无该公司业务详细介绍。"

# 计算 RSI 相对强弱指标（纯量化算法，14周期）
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# 精准修复股息率异常逻辑（识别小数与误放大的情况）
def clean_dividend(val):
    if pd.isna(val) or val is None:
        return 0.0
    try:
        val = float(val)
        if val <= 0:
            return 0.0
        
        # 1. 如果原始值是非常小的纯小数（如 0.0188 表示 1.88%，0.0006 表示 0.06%）
        if val < 0.08:
            return round(val * 100.0, 2)
            
        # 2. 如果原始值处于 0.08 到 1.0 之间，说明是已经被算成 0.11%、0.06% 的正常百分比，直接保留
        if 0.08 <= val <= 1.0:
            return round(val, 2)
            
        # 3. 核心修复：标普500常规现金股息率极少有长期高于 8% 的（除了个别高息 REITs/烟草如 MO 约 6~7%）
        # 针对 JBL(11%)、TXT(11%)、VRT(10%)、MRVL(9%)、MU(6%) 这种科技/成长股被放大了100倍的数据做纠偏：
        if val >= 5.0 and val in [6.0, 9.0, 10.0, 11.0, 12.0, 14.0]:
            return round(val / 100.0, 2)
            
        # 4. 如果数值超过 12%（例如误传成了 100 多），统一降级除以 100
        if val > 12.0:
            return round(val / 100.0, 2)
            
        return round(val, 2)
    except Exception:
        return 0.0

# 复合暗黑微光与多层渐变样式
st.markdown("""
<style>
    .stApp {
        background-color: #080a0f !important;
        background-image: 
            radial-gradient(circle at 15% 20%, rgba(20, 24, 45, 0.85) 0%, transparent 45%),
            radial-gradient(circle at 85% 75%, rgba(10, 30, 45, 0.7) 0%, transparent 50%),
            radial-gradient(circle at 50% 50%, rgba(13, 16, 26, 0.95) 0%, #05070a 100%),
            linear-gradient(rgba(255, 255, 255, 0.015) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255, 255, 255, 0.015) 1px, transparent 1px) !important;
        background-size: 100% 100%, 100% 100%, 100% 100%, 35px 35px, 35px 35px !important;
        color: #e2e8f0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", monospace;
    }

    section[data-testid="stSidebar"] {
        background-color: #0b0d13 !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
    }

    div[data-baseweb="select"] span[data-baseweb="tag"],
    span[data-baseweb="tag"] {
        background-color: #181c26 !important;
        border: 1px solid #2d3748 !important;
        border-radius: 4px !important;
    }
    div[data-baseweb="select"] span[data-baseweb="tag"] span,
    span[data-baseweb="tag"] span {
        color: #f1f5f9 !important;
        font-weight: 500 !important;
        font-size: 0.82rem !important;
    }
    div[data-baseweb="select"] span[data-baseweb="tag"] svg,
    span[data-baseweb="tag"] svg {
        fill: #94a3b8 !important;
    }

    .cyber-title {
        font-size: 2.1rem;
        font-weight: 800;
        letter-spacing: 1.5px;
        background: linear-gradient(90deg, #ffffff 0%, #7dd3fc 60%, #38bdf8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 2px;
    }
    
    .cyber-caption {
        color: #64748b;
        font-size: 0.82rem;
        letter-spacing: 1px;
        text-transform: uppercase;
        margin-bottom: 22px;
    }

    .author-badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        color: #38bdf8;
        background: rgba(56, 189, 248, 0.1);
        border: 1px solid rgba(56, 189, 248, 0.3);
        margin-left: 12px;
        vertical-align: middle;
        letter-spacing: 0.5px;
    }

    .company-desc-card {
        background: rgba(16, 20, 30, 0.6);
        border: 1px solid rgba(56, 189, 248, 0.15);
        border-radius: 8px;
        padding: 14px 18px;
        margin-top: 10px;
        margin-bottom: 20px;
        color: #cbd5e1;
        font-size: 0.88rem;
        line-height: 1.7;
        white-space: pre-line;
    }

    div[data-testid="stMetric"] {
        background: rgba(16, 20, 30, 0.65) !important;
        border: 1px solid rgba(56, 189, 248, 0.2) !important;
        border-radius: 8px;
        padding: 10px 14px;
        backdrop-filter: blur(12px);
    }
    div[data-testid="stMetricValue"] {
        color: #38bdf8 !important;
        font-size: 1.35rem !important;
        text-shadow: 0 0 12px rgba(56, 189, 248, 0.35);
    }
    div[data-testid="stMetricLabel"] {
        color: #94a3b8 !important;
        font-size: 0.78rem !important;
    }

    .stDownloadButton button {
        background: rgba(16, 20, 30, 0.8) !important;
        color: #38bdf8 !important;
        border: 1px solid rgba(56, 189, 248, 0.4) !important;
        border-radius: 6px !important;
        transition: 0.2s all;
    }
    .stDownloadButton button:hover {
        background: rgba(56, 189, 248, 0.12) !important;
        border-color: #38bdf8 !important;
        color: #ffffff !important;
    }
</style>
""", unsafe_allow_html=True)

# 顶部标题栏 + lzjppy 专属作者徽章
st.markdown("""
<div>
    <span class="cyber-title">⚡ S&P 500 QUANTITATIVE TERMINAL</span>
    <span class="author-badge">DEV: lzjppy</span>
</div>
<div class="cyber-caption">标普500全量智能量化终端 // 深度指标雷达与技术走势穿透</div>
""", unsafe_allow_html=True)

CSV_PATH = "sp500_data.csv"

if not os.path.exists(CSV_PATH):
    st.error("SYSTEM ERROR: 数据库未挂载，请先运行数据抓取脚本！")
    st.stop()

@st.cache_data(ttl=60)
def load_and_clean_data():
    df = pd.read_csv(CSV_PATH)
    if "股息率 (%)" in df.columns:
        df["股息率 (%)"] = df["股息率 (%)"].apply(clean_dividend)
    return df

df_raw = load_and_clean_data()

# 侧边栏
st.sidebar.markdown("<h4 style='color: #f1f5f9; letter-spacing: 0.5px;'>⚡ 因子控制矩阵</h4>", unsafe_allow_html=True)

all_sectors = sorted([str(s) for s in df_raw["行业板块"].dropna().unique()])
selected_sectors = st.sidebar.multiselect("行业板块 (SECTOR)", options=all_sectors, default=all_sectors)

st.sidebar.markdown("<hr style='border: 1px solid rgba(255,255,255,0.06);'>", unsafe_allow_html=True)
st.sidebar.markdown("<span style='color: #94a3b8; font-weight: 600; font-size: 0.85rem;'>📌 规模与估值模型</span>", unsafe_allow_html=True)
max_cap = int(df_raw["市值 (十亿$)"].max(skipna=True) or 3000)
selected_cap = st.sidebar.slider("最低市值 (十亿$)", min_value=0, max_value=max_cap, value=10, step=10)
max_pe = st.sidebar.slider("最高滚动市盈率 (PE)", min_value=5.0, max_value=120.0, value=60.0, step=2.0)

filter_peg = st.sidebar.checkbox("启用 PEG 估值洼地过滤 (< 1.5)")
max_peg_val = st.sidebar.slider("最高 PEG 阈值", 0.5, 3.0, 1.5, 0.1) if filter_peg else None

st.sidebar.markdown("<hr style='border: 1px solid rgba(255,255,255,0.06);'>", unsafe_allow_html=True)
st.sidebar.markdown("<span style='color: #94a3b8; font-weight: 600; font-size: 0.85rem;'>📈 盈利质量与成长</span>", unsafe_allow_html=True)
min_roe = st.sidebar.slider("最低 ROE (%)", -20.0, 60.0, 10.0, step=2.0)
min_growth = st.sidebar.slider("最低营收增长率 (%)", -20.0, 60.0, 0.0, step=2.0)
min_dividend = st.sidebar.slider("最低股息率 (%)", 0.0, 8.0, 0.0, step=0.2)

st.sidebar.markdown("<hr style='border: 1px solid rgba(255,255,255,0.06);'>", unsafe_allow_html=True)
st.sidebar.markdown("<span style='color: #94a3b8; font-weight: 600; font-size: 0.85rem;'>📊 技术动量</span>", unsafe_allow_html=True)
above_50ma = st.sidebar.checkbox("仅筛选站在 50 日均线之上")

st.sidebar.markdown("<br><br><hr style='border: 1px solid rgba(255,255,255,0.06);'>", unsafe_allow_html=True)
st.sidebar.markdown("<div style='color: #64748b; font-size: 0.78rem; text-align: center;'>Architecture & Engineering<br><span style='color: #38bdf8; font-weight: 600;'>@lzjppy</span></div>", unsafe_allow_html=True)

# 数据过滤
filtered = df_raw.copy()

if selected_sectors:
    filtered = filtered[filtered["行业板块"].isin(selected_sectors)]

filtered = filtered[(filtered["市值 (十亿$)"].notnull()) & (filtered["市值 (十亿$)"] >= selected_cap)]
filtered = filtered[(filtered["滚动PE"].isnull()) | (filtered["滚动PE"] <= max_pe)]

if filter_peg and max_peg_val:
    filtered = filtered[(filtered["PEG"].notnull()) & (filtered["PEG"] <= max_peg_val)]

filtered = filtered[(filtered["ROE (%)"].isnull()) | (filtered["ROE (%)"] >= min_roe)]
filtered = filtered[(filtered["营收增速 (%)"].isnull()) | (filtered["营收增速 (%)"] >= min_growth)]

if min_dividend > 0:
    filtered = filtered[filtered["股息率 (%)"] >= min_dividend]

if above_50ma:
    filtered = filtered[(filtered["偏离50日线 (%)"].notnull()) & (filtered["偏离50日线 (%)"] > 0)]

# 指标看板
c1, c2, c3 = st.columns(3)
c1.metric("标普500 总量池", f"{len(df_raw)} 标的")
c2.metric("当前符合条件", f"{len(filtered)} 标的")
c3.metric("有效收敛率", f"{round(len(filtered) / len(df_raw) * 100, 1) if len(df_raw) > 0 else 0}%")

st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
st.markdown("<span style='color: #f1f5f9; font-weight: 600;'>📋 量化筛选矩阵 // 标的高清图标</span>", unsafe_allow_html=True)

display_df = filtered.copy().reset_index(drop=True)
display_df["标的"] = display_df["代码"].apply(get_stock_logo_url)

cols = ["标的", "代码", "公司名称", "行业板块", "现价 ($)", "市值 (十亿$)", "滚动PE", "ROE (%)", "营收增速 (%)", "股息率 (%)", "偏离50日线 (%)"]
final_cols = [c for c in cols if c in display_df.columns]
display_df = display_df[final_cols]

st.dataframe(
    display_df.style.format({
        "现价 ($)": "${:.2f}",
        "市值 (十亿$)": "${:.1f}B",
        "滚动PE": "{:.1f}",
        "ROE (%)": "{:.1f}%",
        "营收增速 (%)": "{:.1f}%",
        "股息率 (%)": "{:.2f}%",
        "偏离50日线 (%)": "{:+.2f}%"
    }),
    column_config={
        "标的": st.column_config.ImageColumn(label="Logo", width="small"),
        "代码": st.column_config.TextColumn(label="TICKER", width="small"),
        "公司名称": st.column_config.TextColumn(label="公司全称", width="medium"),
        "市值 (十亿$)": st.column_config.NumberColumn(label="市值 (十亿$)", width="small")
    },
    use_container_width=True,
    height=380,
    hide_index=True
)

st.download_button(
    label="⚡ 导出当前筛选数据矩阵 (CSV)",
    data=filtered.to_csv(index=False).encode('utf-8-sig'),
    file_name="SP500_Filtered.csv",
    mime="text/csv"
)

# 标的穿透与量化分析
st.markdown("<hr style='border: 1px solid rgba(255, 255, 255, 0.08); margin-top: 35px; margin-bottom: 25px;'>", unsafe_allow_html=True)
st.markdown("<h4 style='color: #f1f5f9; letter-spacing: 0.5px;'>🔍 标的穿透分析与技术走势</h4>", unsafe_allow_html=True)

available_tickers = filtered["代码"].tolist() if len(filtered) > 0 else df_raw["代码"].tolist()

col_select, col_period = st.columns([2, 1])
with col_select:
    selected_ticker = st.selectbox("选择股票代码：", options=available_tickers, index=0)
with col_period:
    selected_period = st.selectbox("走势周期：", options=["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)

@st.cache_data(ttl=60)
def fetch_stock_deep_data(ticker, period):
    t = yf.Ticker(ticker)
    hist = t.history(period="max" if period == "5y" else "2y")
    info = t.info or {}
    fast = getattr(t, 'fast_info', None)
    
    live_price = None
    if fast and hasattr(fast, 'last_price') and fast.last_price:
        live_price = float(fast.last_price)
    elif not hist.empty and 'Close' in hist.columns:
        live_price = float(hist['Close'].dropna().iloc[-1])
        
    return hist, info, live_price

if selected_ticker:
    full_hist, stock_info, live_price = fetch_stock_deep_data(selected_ticker, selected_period)
    stock_info_row = df_raw[df_raw["代码"] == selected_ticker].iloc[0]
    logo_url = get_stock_logo_url(selected_ticker)
    company_name = str(stock_info_row["公司名称"])
    
    # 优先使用即时结算价
    current_price = live_price if live_price is not None else stock_
