import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

st.set_page_config(page_title="标普500全量量化筛选器", layout="wide")

st.title("📊 标普500 全成分股量化筛选器")
st.caption("完整收录 S&P 500 全部上市公司 | 支持多因子筛选与个股 K 线穿透分析")

CSV_PATH = "sp500_data.csv"

if not os.path.exists(CSV_PATH):
    st.warning("⚠️ 尚未检测到本地数据库，请先运行 sync_sp500.py 数据同步脚本！")
    st.stop()

# 严密股息率归一化函数（美股标普股息率通常在 0% ~ 10% 之间）
def clean_dividend(val):
    if pd.isna(val) or val is None or val <= 0:
        return 0.0
    # 针对 188.0、246.0、360.0 这种百倍异常值除以 100 恢复为 1.88%、2.46%、3.6%
    if val >= 10.0:
        return round(val / 100.0, 2)
    return round(float(val), 2)

@st.cache_data
def load_and_clean_data():
    df = pd.read_csv(CSV_PATH)
    # 全局清洗修复股息率
    if "股息率 (%)" in df.columns:
        df["股息率 (%)"] = df["股息率 (%)"].apply(clean_dividend)
    return df

df_raw = load_and_clean_data()

# ----------------- 侧边栏：多维筛选控件 -----------------
st.sidebar.header("🛠️ 筛选控制台")

# 1. 行业板块
all_sectors = sorted([str(s) for s in df_raw["行业板块"].dropna().unique()])
selected_sectors = st.sidebar.multiselect("行业板块", options=all_sectors, default=all_sectors)

# 2. 规模与估值
st.sidebar.markdown("---")
st.sidebar.subheader("📌 规模与估值")
max_cap = int(df_raw["市值 (十亿$)"].max(skipna=True) or 3000)
selected_cap = st.sidebar.slider("最低市值 (十亿$)", min_value=0, max_value=max_cap, value=10, step=10)
max_pe = st.sidebar.slider("最高滚动市盈率 (PE)", min_value=5.0, max_value=120.0, value=60.0, step=2.0)

filter_peg = st.sidebar.checkbox("启用 PEG 过滤 (< 1.5 估值洼地)")
max_peg_val = st.sidebar.slider("最高 PEG 阈值", 0.5, 3.0, 1.5, 0.1) if filter_peg else None

# 3. 盈利质量与成长
st.sidebar.markdown("---")
st.sidebar.subheader("📈 质量与成长")
min_roe = st.sidebar.slider("最低 ROE (%)", -20.0, 60.0, 10.0, step=2.0)
min_growth = st.sidebar.slider("最低营收增长率 (%)", -20.0, 60.0, 0.0, step=2.0)
min_dividend = st.sidebar.slider("最低股息率 (%)", 0.0, 8.0, 0.0, step=0.2)

# 4. 动量趋势
st.sidebar.markdown("---")
st.sidebar.subheader("📊 技术动量")
above_50ma = st.sidebar.checkbox("仅筛选股价在 50 日均线之上")

# ----------------- 筛选逻辑执行 -----------------
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

# ----------------- 顶部数据指标卡 -----------------
c1, c2, c3 = st.columns(3)
c1.metric("标普500 基础池", f"{len(df_raw)} 只")
c2.metric("当前符合条件", f"{len(filtered)} 只")
c3.metric("入围占比", f"{round(len(filtered) / len(df_raw) * 100, 1) if len(df_raw) > 0 else 0}%")

# ----------------- 筛选结果表格展示 -----------------
st.markdown("### 📋 标的筛选结果")
st.dataframe(
    filtered.style.format({
        "现价 ($)": "${:.2f}",
        "市值 (十亿$)": "${:.1f}B",
        "滚动PE": "{:.1f}",
        "预测PE": "{:.1f}",
        "PEG": "{:.2f}",
        "ROE (%)": "{:.1f}%",
        "营收增速 (%)": "{:.1f}%",
        "毛利率 (%)": "{:.1f}%",
        "资产负债率 (%)": "{:.1f}",
        "股息率 (%)": "{:.2f}%",
        "偏离50日线 (%)": "{:+.2f}%"
    }),
    use_container_width=True,
    height=380
)

# 导出按钮
st.download_button(
    label="📥 导出筛选结果为 CSV",
    data=filtered.to_csv(index=False).encode('utf-8-sig'),
    file_name="标普500筛选结果.csv",
    mime="text/csv"
)

# ----------------- 个股深度穿透与交互式 K 线 -----------------
st.markdown("---")
st.subheader("🔍 个股深度穿透与交互式 K 线")

available_tickers = filtered["代码"].tolist() if len(filtered) > 0 else df_raw["代码"].tolist()

col_select, col_period = st.columns([2, 1])
with col_select:
    selected_ticker = st.selectbox("选择要分析穿透的股票代码：", options=available_tickers, index=0)
with col_period:
    selected_period = st.selectbox("选择历史走势时间范围：", options=["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)

@st.cache_data(ttl=1800)
def fetch_kline_data(ticker, period):
    t = yf.Ticker(ticker)
    return t.history(period=period)

if selected_ticker:
    stock_hist = fetch_kline_data(selected_ticker, selected_period)
    stock_info_row = df_raw[df_raw["代码"] == selected_ticker].iloc[0]
    
    ic1, ic2, ic3, ic4, ic5 = st.columns(5)
    ic1.metric("公司名称", str(stock_info_row["公司名称"]))
    ic2.metric("当前股价", f"${stock_info_row['现价 ($)']:.2f}")
    ic3.metric("滚动 PE", f"{stock_info_row['滚动PE']}" if pd.notnull(stock_info_row['滚动PE']) else "--")
    ic4.metric("ROE", f"{stock_info_row['ROE (%)']}%" if pd.notnull(stock_info_row['ROE (%)']) else "--")
    
    div_show = stock_info_row['股息率 (%)']
    ic5.metric("股息率", f"{div_show:.2f}%" if pd.notnull(div_show) else "--")

    if not stock_hist.empty:
        stock_hist["MA20"] = stock_hist["Close"].rolling(window=20).mean()
        stock_hist["MA50"] = stock_hist["Close"].rolling(window=50).mean()

        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
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
                increasing_line_color="#26a69a",
                decreasing_line_color="#ef5350"
            ),
            row=1, col=1
        )

        fig.add_trace(go.Scatter(x=stock_hist.index, y=stock_hist["MA20"], line=dict(color="#f39c12", width=1.5), name="MA20 (月线)"), row=1, col=1)
        fig.add_trace(go.Scatter(x=stock_hist.index, y=stock_hist["MA50"], line=dict(color="#3498db", width=1.5), name="MA50 (季线)"), row=1, col=1)

        colors = ["#26a69a" if c >= o else "#ef5350" for c, o in zip(stock_hist["Close"], stock_hist["Open"])]
        fig.add_trace(
            go.Bar(x=stock_hist.index, y=stock_hist["Volume"], marker_color=colors, name="成交量 (Volume)"),
            row=2, col=1
        )

        fig.update_layout(
            height=600,
            margin=dict(l=20, r=20, t=30, b=20),
            xaxis_rangeslider_visible=False,
            hovermode="x unified"
        )
        fig.update_yaxes(title_text="价格 ($)", row=1, col=1)
        fig.update_yaxes(title_text="成交量", row=2, col=1)

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("暂未获取到该标的的历史走势数据。")