import os
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime

def get_sp500_tickers():
    """从维基百科获取最新标普500成分股列表"""
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    tables = pd.read_html(res.text)
    df = tables[0]
    
    # 统一字段命名
    df = df[['Symbol', 'Security', 'GICS Sector']].copy()
    df.columns = ['代码', '公司名称', '行业板块']
    df['代码'] = df['代码'].str.replace('.', '-', regex=False)
    return df

def fetch_single_ticker(ticker):
    """安全拉取单只股票量化因子与最新收盘价"""
    try:
        t = yf.Ticker(ticker)
        # 取最近 5 天历史数据，确保永远取到最新结算收盘日
        hist = t.history(period="5d")
        if hist.empty:
            return None
        
        last_close = float(hist['Close'].dropna().iloc[-1])
        
        # 计算 50 日均线偏离度（若历史够长）
        hist_long = t.history(period="3mo")
        dev_50ma = None
        if len(hist_long) >= 50:
            ma50 = hist_long['Close'].rolling(50).mean().iloc[-1]
            dev_50ma = round(((last_close - ma50) / ma50) * 100, 2)

        info = t.info or {}
        
        market_cap = info.get('marketCap')
        cap_b = round(market_cap / 1e9, 2) if market_cap else None
        pe = info.get('trailingPE')
        pe = round(pe, 2) if pe else None
        peg = info.get('pegRatio')
        peg = round(peg, 2) if peg else None
        roe = info.get('returnOnEquity')
        roe = round(roe * 100, 2) if roe else None
        rev_growth = info.get('revenueGrowth')
        rev_growth = round(rev_growth * 100, 2) if rev_growth else None
        div_yield = info.get('dividendYield')
        div_yield = round(div_yield * 100, 2) if div_yield else 0.0

        return {
            "现价 ($)": round(last_close, 2),
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

def main():
    print(f"[{datetime.now()}] 开始同步标普500成分股最新行情与因子...")
    base_df = get_sp500_tickers()
    
    results = []
    for idx, row in base_df.iterrows():
        ticker = row['代码']
        data = fetch_single_ticker(ticker)
        if data:
            combined = {**row.to_dict(), **data}
            results.append(combined)
            print(f"[{idx+1}/{len(base_df)}] {ticker} 同步完成: ${data['现价 ($)']}")
        else:
            print(f"[{idx+1}/{len(base_df)}] {ticker} 抓取跳过")
            
    final_df = pd.DataFrame(results)
    final_df.to_csv("sp500_data.csv", index=False, encoding="utf-8-sig")
    print(f"[{datetime.now()}] 同步成功！共保存 {len(final_df)} 只标的至 sp500_data.csv")

if __name__ == "__main__":
    main()
