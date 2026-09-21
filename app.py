import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from deep_translator import MyMemoryTranslator, GoogleTranslator

st.set_page_config(page_title="S&P 500 QUANTITATIVE TERMINAL", layout="wide", initial_sidebar_state="expanded")

# 初始化用户自选股池 (Session State)
if "watchlist" not in st.session_state:
    st.session_state.watchlist = []

# 高可用金融 Logo 接口
def get_stock_logo_url(ticker):
    if pd.isna(ticker) or ticker is None:
        return "https://ui-avatars.com/api/?name=NA&background=181c26&color=38bdf8&rounded=true"
    clean_t = str(ticker).replace("-", "").replace(".", "").upper()
    return f"https://financialmodelingprep.com/image-stock/{clean_t}.png"

# 通用双通道翻译函数
@st.cache_data(ttl=604800)
def translate_text_zh(text):
    if not text or not text.strip():
        return ""
    trimmed = text[:350]
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
    return translated if translated else text

# 动态获取公司业务简介
@st.cache_data(ttl=604800)
def get_company_summary_zh(ticker):
    try:
        t = yf.Ticker(ticker)
        raw_summary = t.info.get("longBusinessSummary", "")
        if not raw_summary:
            return "暂无该公司业务详细介绍。"
        
        translated = translate_text_zh(raw_summary)
        if translated and translated != raw_summary[:350]:
            return f"【中文业务速览】\n{translated}\n\n---\n【官方英文完整介绍】\n{raw_summary}"
        else:
            return f"【官方主营业务简介 (原文)】\n\n{raw_summary}"
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

    .signal-box {
        background: rgba(16, 20, 30, 0.65);
        border-radius: 8px;
        padding: 12px 16px;
        border: 1px solid rgba(56, 189, 248, 0.2);
        margin-bottom: 12px;
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

    .stDownloadButton button, .stButton button {
        background: rgba(16, 20, 30, 0.8) !important;
        color: #38bdf8 !important;
        border: 1px solid rgba(56, 189, 248, 0.4) !important;
        border-radius: 6px !important;
        transition: 0.2s all;
    }
    .stDownloadButton button:hover, .stButton button:hover {
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

def clean_dividend(val):
    if pd.isna(val) or val is None or val <= 0:
        return 0.0
    if val >= 10.0:
        return round(val / 100.0, 2)
    return round(float(val), 2)

@st.cache_data
def load_and_clean_data():
    df = pd.read_csv(CSV_PATH)
    if "股息率 (%)" in df.columns:
        df["股息率 (%)"] = df["股息率 (%)"].apply(clean_dividend)
    return df

df_raw = load_and_clean_data()

# 侧边栏：因子控制矩阵
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

# 数据筛选
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

# 选项卡主布局：市场矩阵 vs 自选关注池
tab_screener, tab_watchlist = st.tabs(["⚡ 全量量化矩阵与单票穿透", "⭐ 我的专属自选股池"])

with tab_screener:
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

    # 标的深度穿透
    st.markdown("<hr style='border: 1px solid rgba(255, 255, 255, 0.08); margin-top: 35px; margin-bottom: 25px;'>", unsafe_allow_html=True)
    st.markdown("<h4 style='color: #f1f5f9; letter-spacing: 0.5px;'>🔍 标的穿透分析与技术走势</h4>", unsafe_allow_html=True)

    available_tickers = filtered["代码"].tolist() if len(filtered) > 0 else df_raw["代码"].tolist()

    col_select, col_period, col_fav = st.columns([2, 1, 1])
    with col_select:
        selected_ticker = st.selectbox("选择股票代码：", options=available_tickers, index=0)
    with col_period:
        selected_period = st.selectbox("走势周期：", options=["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)
    with col_fav:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        is_fav = selected_ticker in st.session_state.watchlist
        if st.button("⭐ 移出自选" if is_fav else "➕ 加入自选", use_container_width=True):
            if is_fav:
                st.session_state.watchlist.remove(selected_ticker)
            else:
                st.session_state.watchlist.append(selected_ticker)
            st.rerun()

    @st.cache_data(ttl=1800)
    def fetch_stock_deep_data(ticker, period):
        t = yf.Ticker(ticker)
        hist = t.history(period="max" if period == "5y" else "2y")
        info = t.info
        news = t.news if hasattr(t, "news") else []
        return hist, info, news

    if selected_ticker:
        full_hist, stock_info, stock_news = fetch_stock_deep_data(selected_ticker, selected_period)
        stock_info_row = df_raw[df_raw["代码"] == selected_ticker].iloc[0]
        logo_url = get_stock_logo_url(selected_ticker)
        company_name = str(stock_info_row["公司名称"])
        
        # TradingView 风格铭牌
        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 16px; background: rgba(16, 20, 30, 0.7); padding: 14px 22px; border-radius: 10px; border: 1px solid rgba(56, 189, 248, 0.2); box-shadow: 0 4px 15px rgba(0,0,0,0.3);">
            <img src="{logo_url}" onerror="this.onerror=null;this.src='https://ui-avatars.com/api/?name={selected_ticker}&background=181c26&color=38bdf8&rounded=true';" 
                 style="width: 48px; height: 48px; border-radius: 50%; object-fit: contain; background: #ffffff; padding: 5px; border: 1px solid rgba(255,255,255,0.15); box-shadow: 0 0 12px rgba(56, 189, 248, 0.25);">
            <div>
                <div style="font-size: 1.5rem; font-weight: 700; color: #f1f5f9; letter-spacing: 0.5px; margin-bottom: 2px;">
                    {selected_ticker} <span style="font-size: 1.1rem; color: #94a3b8; font-weight: 400; margin-left: 10px;">{company_name}</span>
                </div>
                <div style="font-size: 0.8rem; color: #38bdf8; text-transform: uppercase; letter-spacing: 1px;">
                    {stock_info_row['行业板块']} // 标普500 成分股 (S&P 500)
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        beta_val = stock_info.get("beta", None)
        beta_str = f"{beta_val:.2f}" if beta_val is not None else "--"

        latest_rsi = None
        if not full_hist.empty and len(full_hist) >= 15:
            rsi_series = calculate_rsi(full_hist["Close"])
            latest_rsi = rsi_series.iloc[-1]
            rsi_str = f"{latest_rsi:.1f}"
        else:
            rsi_str = "--"

        # 核心指标看板
        col_k1, col_k2, col_k3, col_k4, col_k5 = st.columns(5)
        col_k1.metric("最新股价", f"${stock_info_row['现价 ($)']:.2f}")
        col_k2.metric("总市值", f"${stock_info_row['市值 (十亿$)' ]:.1f}B")
        col_k3.metric("滚动 PE", f"{stock_info_row['滚动PE']}" if pd.notnull(stock_info_row['滚动PE']) else "--")
        col_k4.metric("ROE (净资产收益率)", f"{stock_info_row['ROE (%)']}%" if pd.notnull(stock_info_row['ROE (%)']) else "--")
        col_k5.metric("股息率", f"{stock_info_row['股息率 (%)']:.2f}%" if pd.notnull(stock_info_row['股息率 (%)']) else "--")

        c_sub1, c_sub2, c_sub3 = st.columns([1, 1, 2])
        c_sub1.metric("Beta (市场弹性)", beta_str)
        c_sub2.metric("RSI-14 (相对强弱)", rsi_str)
        week_high = stock_info.get("fiftyTwoWeekHigh", None)
        week_low = stock_info.get("fiftyTwoWeekLow", None)
        range_str = f"${week_low:.2f} ~ ${week_high:.2f}" if (week_high and week_low) else "--"
        c_sub3.metric("52 周价格运行区间", range_str)

        # 智能诊断卡片 + 五维量化雷达图
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        col_diag, col_radar = st.columns([1, 1])

        with col_diag:
            st.markdown("<h5 style='color: #7dd3fc;'>🤖 智能量化技术诊断</h5>", unsafe_allow_html=True)
            
            # 诊断逻辑
            signals = []
            if latest_rsi is not None:
                if latest_rsi >= 70:
                    signals.append(("⚠️ 相对强弱 (RSI) 严重超买", f"当前 RSI 达到 {rsi_str}，处于技术过热区间，注意高位回调风险。", "#f87171"))
                elif latest_rsi <= 30:
                    signals.append(("🟢 相对强弱 (RSI) 深度超卖", f"当前 RSI 降至 {rsi_str}，处于空头耗尽区，关注技术性反弹机会。", "#4ade80"))
                else:
                    signals.append(("⚪ 相对强弱 (RSI) 处于常态中枢", f"当前 RSI 为 {rsi_str}，多空双方博弈均衡。", "#94a3b8"))

            bias = stock_info_row.get("偏离50日线 (%)", None)
            if pd.notnull(bias):
                if bias > 5:
                    signals.append(("🚀 中期多头排列走强", f"现价站上 50 日均线 {bias:+.2f}%，呈强势进攻态势。", "#38bdf8"))
                elif bias < -5:
                    signals.append(("📉 均线承压空头格局", f"现价跌破 50 日均线 {bias:+.2f}%，短中期承压调整。", "#fb923c"))

            if beta_val is not None:
                if beta_val > 1.3:
                    signals.append(("⚡ 高贝塔进攻标的", f"Beta 为 {beta_val:.2f}，对大盘波动极具放大效应，适合顺势博取超额收益。", "#c084fc"))
                elif beta_val < 0.8:
                    signals.append(("🛡️ 低贝塔防御底仓", f"Beta 仅为 {beta_val:.2f}，抗市场颠簸能力强，防御属性凸显。", "#34d399"))

            for title, desc, color in signals:
                st.markdown(f"""
                <div class="signal-box" style="border-left: 4px solid {color};">
                    <div style="font-weight: 600; color: {color}; font-size: 0.9rem;">{title}</div>
                    <div style="color: #cbd5e1; font-size: 0.82rem; margin-top: 3px;">{desc}</div>
                </div>
                """, unsafe_allow_html=True)

        with col_radar:
            st.markdown("<h5 style='color: #7dd3fc;'>🕸️ 五维量化因子雷达</h5>", unsafe_allow_html=True)
            # 计算 0-100 标准化得分
            pe = float(stock_info_row.get("滚动PE", 30)) if pd.notnull(stock_info_row.get("滚动PE")) else 30
            score_val = max(10, min(100, int(100 - (pe - 10) * 1.5)))
            
            roe = float(stock_info_row.get("ROE (%)", 15)) if pd.notnull(stock_info_row.get("ROE (%)")) else 15
            score_prof = max(10, min(100, int(roe * 2.5)))
            
            growth = float(stock_info_row.get("营收增速 (%)", 10)) if pd.notnull(stock_info_row.get("营收增速 (%)")) else 10
            score_gro = max(10, min(100, int(growth * 3.5)))
            
            div = float(stock_info_row.get("股息率 (%)", 1.0)) if pd.notnull(stock_info_row.get("股息率 (%)")) else 1.0
            score_div = max(10, min(100, int(div * 25)))
            
            score_mom = max(10, min(100, int(50 + (bias if pd.notnull(bias) else 0) * 2)))

            radar_fig = go.Figure()
            radar_fig.add_trace(go.Scatterpolar(
                r=[score_val, score_prof, score_gro, score_div, score_mom],
                theta=['估值优势', '盈利质量', '成长潜力', '红利回报', '技术动量'],
                fill='toself',
                fillcolor='rgba(56, 189, 248, 0.25)',
                line=dict(color='#38bdf8', width=2),
                name=selected_ticker
            ))
            radar_fig.update_layout(
                polar=dict(
                    radialaxis=dict(visible=True, range=[0, 100], showticklabels=False, linecolor="rgba(255,255,255,0.1)"),
                    angularaxis=dict(color="#cbd5e1", linecolor="rgba(255,255,255,0.1)")
                ),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=260,
                margin=dict(l=35, r=35, t=10, b=20),
                showlegend=False
            )
            st.plotly_chart(radar_fig, use_container_width=True)

        # 业务概况折叠面板
        with st.expander(f"📖 查看 {selected_ticker} ({company_name}) 业务概况与主营介绍", expanded=False):
            summary_zh = get_company_summary_zh(selected_ticker)
            st.markdown(f'<div class="company-desc-card">{summary_zh}</div>', unsafe_allow_html=True)

        # 走势 K 线与成交量联动图
        if not full_hist.empty:
            full_hist["MA20"] = full_hist["Close"].rolling(window=20).mean()
            full_hist["MA50"] = full_hist["Close"].rolling(window=50).mean()

            period_days = {"1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "2y": 730, "5y": 1825}
            days = period_days.get(selected_period, 365)
            stock_hist = full_hist.tail(days).copy()

            fig = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.03,
                row_heights=[0.75, 0.25]
            )

            fig.add_trace(
                go.Candlestick(
                    x=stock_hist.index,
                    open=stock_hist["Open"],
                    high=stock_hist["High"],
                    low=stock_hist["Low"],
                    close=stock_hist["Close"],
                    name="K线 (OHLC)",
                    increasing_line_color="#00e676",
                    decreasing_line_color="#ff5252"
                ),
                row=1, col=1
            )

            fig.add_trace(go.Scatter(x=stock_hist.index, y=stock_hist["MA20"], line=dict(color="#fadb14", width=1.6), name="MA20 (月线)"), row=1, col=1)
            fig.add_trace(go.Scatter(x=stock_hist.index, y=stock_hist["MA50"], line=dict(color="#38bdf8", width=1.6), name="MA50 (季线)"), row=1, col=1)

            colors = ["rgba(0, 230, 118, 0.55)" if c >= o else "rgba(255, 82, 82, 0.55)" for c, o in zip(stock_hist["Close"], stock_hist["Open"])]
            fig.add_trace(
                go.Bar(x=stock_hist.index, y=stock_hist["Volume"], marker_color=colors, name="成交量", showlegend=False),
                row=2, col=1
            )

            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(11, 14, 23, 0.75)",
                height=560,
                margin=dict(l=10, r=20, t=25, b=10),
                xaxis_rangeslider_visible=False,
                hovermode="x unified",
                font=dict(color="#94a3b8", family="monospace"),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                    bgcolor="rgba(0,0,0,0)"
                )
            )

            fig.update_xaxes(
                rangebreaks=[dict(bounds=["sat", "mon"])],
                showgrid=True,
                gridwidth=1,
                gridcolor="rgba(255, 255, 255, 0.04)"
            )
            fig.update_yaxes(
                showgrid=True,
                gridwidth=1,
                gridcolor="rgba(255, 255, 255, 0.04)",
                side="right"
            )

            st.plotly_chart(fig, use_container_width=True)

        # 标的最新英文快讯 + 双语自动翻译
        st.markdown("<h5 style='color: #7dd3fc; margin-top: 25px;'>📰 实时外媒资讯与智能速译</h5>", unsafe_allow_html=True)
        if stock_news and len(stock_news) > 0:
            for item in stock_news[:4]:
                title_en = item.get("title", "")
                link = item.get("link", "#")
                publisher = item.get("publisher", "Financial News")
                if title_en:
                    title_zh = translate_text_zh(title_en)
                    st.markdown(f"""
                    <div style="background: rgba(16, 20, 30, 0.5); border-left: 3px solid #38bdf8; padding: 8px 14px; margin-bottom: 8px; border-radius: 4px;">
                        <a href="{link}" target="_blank" style="text-decoration: none; color: #f1f5f9; font-weight: 500; font-size: 0.9rem;">{title_zh}</a>
                        <div style="color: #64748b; font-size: 0.75rem; margin-top: 2px;">
                            原文: {title_en} // 来源: <span style="color: #38bdf8;">{publisher}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("暂未检索到该标的的近期公开快讯。")

# 自选股池独立选项卡
with tab_watchlist:
    st.markdown("<h4 style='color: #f1f5f9; letter-spacing: 0.5px;'>⭐ 个人量化自选池</h4>", unsafe_allow_html=True)
    if not st.session_state.watchlist:
        st.info("自选池暂为空白。你可以在“全量量化矩阵”标签页中点击【➕ 加入自选】收藏心仪标的！")
    else:
        watch_df = df_raw[df_raw["代码"].isin(st.session_state.watchlist)].copy().reset_index(drop=True)
        watch_df["标的"] = watch_df["代码"].apply(get_stock_logo_url)
        
        watch_cols = ["标的", "代码", "公司名称", "行业板块", "现价 ($)", "市值 (十亿$)", "滚动PE", "ROE (%)", "股息率 (%)", "偏离50日线 (%)"]
        final_watch_cols = [c for c in watch_cols if c in watch_df.columns]
        
        st.dataframe(
            watch_df[final_watch_cols].style.format({
                "现价 ($)": "${:.2f}",
                "市值 (十亿$)": "${:.1f}B",
                "滚动PE": "{:.1f}",
                "ROE (%)": "{:.1f}%",
                "股息率 (%)": "{:.2f}%",
                "偏离50日线 (%)": "{:+.2f}%"
            }),
            column_config={"标的": st.column_config.ImageColumn(label="Logo", width="small")},
            use_container_width=True,
            hide_index=True
        )

        # 自选池多股百分比收益率对比图
        st.markdown("<h5 style='color: #7dd3fc; margin-top: 20px;'>📈 自选标的归一化走势对比 (近半年收益率 %)</h5>", unsafe_allow_html=True)
        compare_fig = go.Figure()
        for t_code in st.session_state.watchlist:
            try:
                hist_c = yf.Ticker(t_code).history(period="6mo")
                if not hist_c.empty:
                    base_price = hist_c["Close"].iloc[0]
                    norm_returns = (hist_c["Close"] / base_price - 1.0) * 100.0
                    compare_fig.add_trace(go.Scatter(x=hist_c.index, y=norm_returns, mode="lines", name=t_code))
            except Exception:
                pass

        compare_fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(11, 14, 23, 0.75)",
            height=400,
            margin=dict(l=10, r=20, t=20, b=10),
            hovermode="x unified",
            font=dict(color="#94a3b8", family="monospace"),
            yaxis=dict(ticksuffix="%", showgrid=True, gridcolor="rgba(255,255,255,0.04)", side="right"),
            xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.04)")
        )
        st.plotly_chart(compare_fig, use_container_width=True)

# 页面底部全局作者水印
st.markdown("<br><hr style='border: 1px solid rgba(255,255,255,0.06);'>", unsafe_allow_html=True)
st.markdown("<div style='text-align: center; color: #475569; font-size: 0.8rem; letter-spacing: 1px;'>DESIGNED & ENGINEERED BY <span style='color: #38bdf8; font-weight: 600;'>LZJPPY</span> // QUANT TERMINAL</div><br>", unsafe_allow_html=True)
