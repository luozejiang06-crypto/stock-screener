import io
import requests
import pandas as pd
import yfinance as yf

print(">>> 1. 正在获取维基百科最新标普500全量成分股名单...")

url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
# 添加浏览器 User-Agent，避免 403 拦截
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

response = requests.get(url, headers=headers)
response.raise_for_status()

# 解析 HTML 表格
tables = pd.read_html(io.StringIO(response.text))
sp500_table = tables[0]

# 提取股票代码与公司名称、行业
tickers = sp500_table["Symbol"].str.replace(".", "-", regex=False).tolist()
sector_map = dict(zip(tickers, sp500_table["GICS Sector"]))
name_map = dict(zip(tickers, sp500_table["Security"]))

print(f">>> 成功获取 {len(tickers)} 只标普500股票清单！")
print(">>> 2. 正在批量拉取核心行情与财务指标（需数分钟，请耐心等待）...")

records = []
total = len(tickers)

for idx, ticker in enumerate(tickers, 1):
    try:
        t = yf.Ticker(ticker)
        info = t.info
        current_price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose", 0.0)
        fifty_ma = info.get("fiftyDayAverage", None)
        ma50_pct = round(((current_price - fifty_ma) / fifty_ma) * 100, 2) if fifty_ma and current_price else None

        records.append({
            "代码": ticker,
            "公司名称": name_map.get(ticker, info.get("shortName", ticker)),
            "行业板块": sector_map.get(ticker, info.get("sector", "其他")),
            "现价 ($)": current_price,
            "市值 (十亿$)": round(info.get("marketCap", 0) / 1e9, 2) if info.get("marketCap") else None,
            "滚动PE": round(info.get("trailingPE"), 2) if info.get("trailingPE") else None,
            "预测PE": round(info.get("forwardPE"), 2) if info.get("forwardPE") else None,
            "PEG": round(info.get("pegRatio"), 2) if info.get("pegRatio") else None,
            "ROE (%)": round(info.get("returnOnEquity", 0) * 100, 2) if info.get("returnOnEquity") else None,
            "营收增速 (%)": round(info.get("revenueGrowth", 0) * 100, 2) if info.get("revenueGrowth") else None,
            "毛利率 (%)": round(info.get("grossMargins", 0) * 100, 2) if info.get("grossMargins") else None,
            "资产负债率 (%)": round(info.get("debtToEquity", 0), 2) if info.get("debtToEquity") else None,
            "股息率 (%)": round(info.get("dividendYield", 0) * 100, 2) if info.get("dividendYield") else 0.0,
            "偏离50日线 (%)": ma50_pct
        })
    except Exception:
        continue

    if idx % 25 == 0 or idx == total:
        print(f"进度: {idx}/{total} (已完成 {round(idx/total*100, 1)}%)")

df = pd.DataFrame(records)
df.to_csv("sp500_data.csv", index=False, encoding="utf-8-sig")
print(">>> 全量数据采集完毕！已成功保存至本地 sp500_data.csv！")