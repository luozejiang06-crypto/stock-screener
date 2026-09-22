import os
import requests
import io
import pandas as pd
import yfinance as yf
from datetime import datetime

def get_sp500_table():
    """多源备用方案：杜绝维基百科 403 阻断"""
    # 优先通道：开源金融标的纯数据 CSV 源
    url_primary = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
    try:
        df = pd.read_csv(url_primary)
        df = df[['Symbol', 'Name', 'Sector']].copy()
        df.columns = ['代码', '公司名称', '行业板块']
        df['代码'] = df['代码'].str.replace('.', '-', regex=False)
        return df
    except Exception as e:
        print(f"主数据源拉取失败: {e}，启用备用通道...")
    
    # 备用通道：带浏览器真实 Headers 的维基百科
    url_backup = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    res = requests.get(url_backup, headers=headers, timeout=15)
    tables = pd.read_html(io.StringIO(res.text))
    df = tables[0][['Symbol', 'Security', 'GICS Sector']].copy()
    df.columns = ['代码', '公司名称', '行业板块']
    df['代码'] = df['代码'].str.replace('.', '-', regex=False)
    return df

def sync_data():
    print(f"[{datetime.now()}] 1. 获取标普500成分股基准池...")
    base_df = get_sp500_table()
    tickers = base_df['代码'].tolist()
    print(f"成功获取 {len(tickers)} 只标的！")

    # 2. 批量拉取近 5 个交易日行情，确保获取最新结算收盘价与均线
    print(f"[{datetime.now()}] 2. 批量获取全量日线收盘价数据...")
    hist_data = yf.download(tickers, period="3mo", interval="1d", group_by='ticker', threads=True, timeout=30)

    results = []
    print(f"[{datetime.now()}] 3. 解析量化指标...")
    for idx, row in base_df.iterrows():
        ticker = row['代码']
        try:
            # 提取历史价格
            if ticker in hist_data and not hist_data[ticker].empty:
                t_hist = hist_data[ticker].dropna(how='all')
                last_close = float(t_hist['Close'].dropna().iloc[-1])
                
                # 计算 50 日均线偏离度
                dev_50ma = None
                if len(t_hist) >= 50:
                    ma50 = t_hist['Close'].rolling(50).mean().iloc[-1]
                    dev_50ma = round(((last_close - ma50) / ma50) * 100, 2)
            else:
                last_close = None
                dev_50ma = None

            # 提取财务估值
            t_obj = yf.Ticker(ticker)
            fast_info = getattr(t_obj, 'fast_info', None)
            info = t_obj.info if hasattr(t_obj, 'info') else {}

            # 市值计算
            market_cap = getattr(fast_info, 'market_cap', None) or info.get('marketCap')
            cap_b = round(market_cap / 1e9, 2) if market_cap else None

            # 估值与成长因子
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

            results.append({
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
            })
        except Exception as err:
            continue

    final_df = pd.DataFrame(results)
    final_df.to_csv("sp500_data.csv", index=False, encoding="utf-8-sig")
    print(f"[{datetime.now()}] 全部数据更新完成！共输出 {len(final_df)} 行数据至 sp500_data.csv")

if __name__ == "__main__":
    sync_data()
