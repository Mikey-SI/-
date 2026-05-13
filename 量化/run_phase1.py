"""
第一轮回测：对比 5 类经典策略，看谁最接近"年化40%+，回撤<50%"的目标。
所有策略都从 2010-03-01 开始 (TQQQ/SOXL 上市后)。
"""
import pandas as pd

from engine import buy_and_hold, compute_metrics, download_one, print_metrics
from strategies import (
    strat_dual_momentum,
    strat_hedgefundie,
    strat_momentum_stocks,
    strat_sma_leveraged,
    strat_vol_target_trend,
)

START = "2010-03-01"
END = "2026-05-12"


def run():
    results = {}

    # 基准
    qqq = download_one("QQQ")["Close"]
    qqq = qqq.loc[START:END]
    spy = download_one("SPY")["Close"].loc[START:END]
    tqqq = download_one("TQQQ")["Close"].loc[START:END]
    results["BH_QQQ"] = buy_and_hold(qqq)
    results["BH_SPY"] = buy_and_hold(spy)
    results["BH_TQQQ"] = buy_and_hold(tqqq)

    # 策略 1: SMA200 + TQQQ
    eq, w, n = strat_sma_leveraged("QQQ", "TQQQ", "BIL", 200, START, END)
    results[n] = eq

    # 策略 1b: SMA200 + UPRO
    eq, w, n = strat_sma_leveraged("SPY", "UPRO", "BIL", 200, START, END)
    results[n] = eq

    # 策略 1c: SMA200 + SOXL (半导体3x)
    eq, w, n = strat_sma_leveraged("SOXX", "SOXL", "BIL", 200, START, END)
    # SOXX 没有缓存, fallback to QQQ
    eq, w, n = strat_sma_leveraged("QQQ", "SOXL", "BIL", 200, START, END)
    results["SMA200_QQQ→SOXL/BIL"] = eq

    # 策略 2: 双动量 (杠杆ETF池)
    eq, w, n = strat_dual_momentum(
        pool=["TQQQ", "UPRO", "SOXL", "TMF"],
        safe_ticker="BIL", lookback=126, top_n=1, start=START, end=END,
    )
    results[n + "_lev"] = eq

    # 策略 2b: 双动量 (普通行业ETF)
    eq, w, n = strat_dual_momentum(
        pool=["XLK", "XLY", "XLF", "XLE", "XLV", "XLI", "XLU", "XLB"],
        safe_ticker="BIL", lookback=126, top_n=2, start=START, end=END,
    )
    results[n + "_sect"] = eq

    # 策略 3: 波动率目标 + 趋势
    eq, w, n = strat_vol_target_trend(
        risk_ticker="TQQQ", safe_ticker="BIL", signal_ticker="QQQ",
        sma_window=200, target_vol=0.40, vol_window=20, max_leverage=1.0,
        start=START, end=END,
    )
    results[n] = eq

    # 策略 4: Hedgefundie 55/45
    eq, w, n = strat_hedgefundie(start=START, end=END)
    results[n] = eq

    # 策略 5: 纳指动量 Top-5
    universe = [
        "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AMD", "AVGO",
        "NFLX", "CRM", "ORCL", "ADBE", "QCOM", "INTC", "LRCX", "ASML", "TSM",
        "MU", "JPM", "V", "MA", "JNJ", "PG", "UNH", "HD", "WMT",
    ]
    eq, w, n = strat_momentum_stocks(
        universe=universe, benchmark="QQQ", safe_ticker="BIL",
        lookback=126, skip=21, top_n=5, sma_window=200, rebalance="ME",
        start="2012-06-01", end=END,
    )
    results[n] = eq

    # 汇总
    rows = []
    for name, eq in results.items():
        m = compute_metrics(eq)
        rows.append({"name": name, **m.to_dict()})
    df = pd.DataFrame(rows).set_index("name")
    df = df.sort_values("CAGR", ascending=False)
    pd.options.display.float_format = "{:.4f}".format
    print("\n======================== 第一轮对比 ========================")
    print(df.to_string())
    print("\n目标: CAGR ≥ 40%, |MaxDD| ≤ 50%")
    qualified = df[(df["CAGR"] >= 0.40) & (df["MaxDD"] >= -0.50)]
    print(f"\n通过策略数: {len(qualified)}")
    if len(qualified):
        print(qualified.to_string())

    df.to_csv("results/phase1_summary.csv")
    print("\n已保存到 results/phase1_summary.csv")


if __name__ == "__main__":
    run()
