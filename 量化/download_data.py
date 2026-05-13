"""一次性下载美股核心 ETF/个股数据并缓存到 data/。"""
from engine import download_one

CORE_ETFS = [
    # 大盘/纳指/小盘指数 ETF
    "SPY", "QQQ", "IWM", "DIA",
    # 杠杆 ETF (2010+ 才有完整数据)
    "TQQQ", "SQQQ", "UPRO", "SPXU", "SOXL", "SOXS", "TMF", "TMV", "UDOW", "SPXL",
    # 反向/避险
    "TLT", "IEF", "GLD", "SHY", "BIL",
    # 行业
    "XLK", "XLF", "XLE", "XLY", "XLV", "XLP", "XLI", "XLU", "XLB", "XLRE", "XLC",
    # 因子/动量
    "MTUM", "QUAL", "VLUE", "USMV", "SPLV",
    # 加密相关
    "MSTR", "COIN",
    # 龙头股 (动量回测候选)
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AMD", "AVGO", "NFLX",
    "CRM", "ORCL", "ADBE", "PYPL", "QCOM", "INTC", "LRCX", "ASML", "TSM", "MU",
    # 大盘其他
    "BRK-B", "JPM", "V", "MA", "JNJ", "PG", "UNH", "HD", "WMT", "DIS",
]


def main():
    failed = []
    for t in CORE_ETFS:
        try:
            df = download_one(t, start="2000-01-01")
            print(f"OK  {t:<8s} rows={len(df):>5d}  {df.index[0].date()} -> {df.index[-1].date()}")
        except Exception as e:
            failed.append(t)
            print(f"FAIL {t:<8s} : {e}")
    print(f"\n完成. 成功: {len(CORE_ETFS) - len(failed)}, 失败: {len(failed)} {failed}")


if __name__ == "__main__":
    main()
