import os
import io
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

def get_sp500_table():
    """获取成分股基准池"""
    url_primary = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
    try:
        df = pd.read_csv(url_primary)
        df = df[['Symbol', 'Name', 'Sector']].copy()
        df.columns = ['代码', '公司名称', '行业板块']
        df['代码'] = df['代码'].str.replace('.', '-', regex=False)
        return df
    except Exception:
        url_backup = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url_backup, headers=headers, timeout=15)
        tables = pd.read_html(io.StringIO(res.text))
        df = tables[0][['Symbol', 'Security', 'GICS Sector']].copy()
        df.columns = ['代码', '公司名称', '行业板块']
        df['代码'] = df['代码'].str.replace('.', '-', regex=False)
        return df

def fetch_details(row, hist_data):
    ticker = row['代码']
    try:
        last_close, dev_50ma = None, None
        if ticker in hist_data and not hist_data[ticker].empty:
            t_hist = hist_data[ticker].dropna(how='all')
            if 'Close' in t_hist.columns and not t_hist['Close'].dropna().empty:
                last_close = float(t_hist['Close'].dropna().iloc[-1])
                if len(t_hist) >= 50:
                    ma50 = t_hist['Close'].rolling(50).mean().iloc[-1]
                    dev_50ma = round(((last_close - ma50) / ma50) * 100, 2)

        t_obj = yf.Ticker(ticker)
        fast = getattr(t_obj, 'fast_info', None)
        info = t_obj.info if hasattr(t_obj, 'info') else {}

        market_cap = getattr(fast, 'market_cap', None) or info.get('marketCap')
        cap_b = round(market_cap / 1e9, 2) if market_cap else None
        
        if last_close is None:
            last_close = getattr(fast, 'last_price', None)

        pe = info.get('trailingPE')
        pe = round(pe, 2) if pe else None
        peg = info.get('pegRatio')
        peg = round(peg, 2) if peg else None
        roe = info.get('returnOnEquity')
        roe = round(roe * 100, 2) if roe else None
        rev_growth = info.get('revenueGrowth')
        rev_growth = round(rev_growth * 100, 2) if rev_growth else None

        # 【根治核心逻辑】：使用 年现金分红 / 现价 计算真实股息率
        div_rate = info.get('dividendRate')
        if div_rate and last_close and last_close > 0:
            div_yield = round((float(div_rate) / float(last_close)) * 100, 2)
        else:
            raw_div = info.get('dividendYield')
            if raw_div is not None and raw_div > 0:
                # 只有纯小数（小于0.12）才乘 100
                div_yield = round(raw_div * 100, 2) if raw_div < 0.12 else round(raw_div, 2)
                # 针对美股标普500成分股进行异常保护：超过12%做回归
                if div_yield > 12.0:
                    div_yield = round(div_yield / 100.0, 2)
            else:
                div_yield = 0.0

        return {
            "代码": ticker,
            "公司名称": row['公司名称'],
            "行业板块": row['行业板块'],
            "现价 ($)": round(last_close, 2) if last_close else None,
            "市值 (十亿$)": cap_b,
            "滚动PE": pe,
            "PEG": peg,
            "ROE (%)": roe,
            "营收增速 (%)": rev_growth,
            "股息率 (%)": div_yield,
            "偏离50日线 (%)": dev_50ma
        }
    except Exception:
        return None

def sync_data():
    print(f"[{datetime.now()}] 1. 获取基准列表...")
    base_df = get_sp500_table()
    tickers = base_df['代码'].tolist()

    print(f"[{datetime.now()}] 2. 并发下载日线行情...")
    hist_data = yf.download(
        tickers,
        period="3mo",
        interval="1d",
        group_by='ticker',
        threads=True,
        timeout=15,
        progress=False
    )

    print(f"[{datetime.now()}] 3. 并发解析全量因子与真实股息率...")
    results = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(fetch_details, row, hist_data) for _, row in base_df.iterrows
