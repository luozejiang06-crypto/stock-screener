import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

st.set_page_config(page_title="S&P 500 QUANTITATIVE TERMINAL", layout="wide", initial_sidebar_state="expanded")

# 高可用金融 Logo 接口
def get_stock_logo_url(ticker):
    if pd.isna(ticker) or ticker is None:
        return "https://ui-avatars.com/api/?name=NA&background=181c26&color=38bdf8&rounded=true"
    clean_t = str(ticker).replace("-", "").replace(".", "").upper()
    return f"https://financialmodelingprep.com/image-stock/{clean_t}.png"

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

    div[data-testid="stMetric"] {
        background: rgba(16, 20, 30, 0.65) !important;
        border: 1px solid rgba(56, 189, 248, 0.2) !important;
        border-radius: 8px;
        padding: 12px 18px;
        backdrop-filter: blur(12px);
    }
    div[data-testid="stMetricValue"] {
        color: #38bdf8 !important;
        text-shadow: 0 0 12px rgba(56, 189, 248, 0.35);
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

st.markdown('<div class="cyber-title">⚡ S&P 500 QUANTITATIVE TERMINAL</div>', unsafe_allow_html=True)
st.markdown('<div class="cyber-caption">标普500全量智能量化终端 // 标的高清图标全覆盖与多因子穿透</div>', unsafe_allow_html=True)

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

# 列表展示处理
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

# 穿透走势与个股分析
st.markdown("<hr style='border: 1px solid rgba(255, 255, 255, 0.08); margin-top: 35px; margin-bottom: 25px;'>", unsafe_allow_html=True)
st.markdown("<h4 style='color: #f1f5f9; letter-spacing: 0.5px;'>🔍 标的穿透分析与专业 K 线走势</h4>", unsafe_allow_html=True)

available_tickers = filtered["代码"].tolist() if len(filtered) > 0 else df_raw["代码"].tolist()

col_select, col_period = st.columns([2, 1])
with col_select:
    selected_ticker = st.selectbox("选择股票代码：", options=available_tickers, index=0)
with col_period:
    selected_period = st.selectbox("走势周期：", options=["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)

@st.cache_data(ttl=1800)
def fetch_kline_data(ticker, period):
    t = yf.Ticker(ticker)
    buffer_hist = t.history(period="max" if period == "5y" else "2y")
    return buffer_hist

if selected_ticker:
    full_hist = fetch_kline_data(selected_ticker, selected_period)
    stock_info_row = df_raw[df_raw["代码"] == selected_ticker].iloc[0]
    logo_url = get_stock_logo_url(selected_ticker)
    company_name = str(stock_info_row["公司名称"])
    
    st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 20px; background: rgba(16, 20, 30, 0.7); padding: 14px 22px; border-radius: 10px; border: 1px solid rgba(56, 189, 248, 0.2); box-shadow: 0 4px 15px rgba(0,0,0,0.3);">
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

    ic1, ic2, ic3, ic4, ic5 = st.columns(5)
    ic1.metric("市值 (十亿$)", f"${stock_info_row['市值 (十亿$)' ]:.1f}B")
    ic2.metric("最新股价", f"${stock_info_row['现价 ($)']:.2f}")
    ic3.metric("滚动 PE", f"{stock_info_row['滚动PE']}" if pd.notnull(stock_info_row['滚动PE']) else "--")
    ic4.metric("ROE (净资产收益率)", f"{stock_info_row['ROE (%)']}%" if pd.notnull(stock_info_row['ROE (%)']) else "--")
    div_show = stock_info_row['股息率 (%)']
    ic5.metric("股息率", f"{div_show:.2f}%" if pd.notnull(div_show) else "--")

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
            height=600,
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
    else:
        st.warning("暂未获取到该标的的历史走势数据。")
