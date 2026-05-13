"""第二轮：增强策略 + 第一轮最优参数微调。目标更接近 CAGR>=40% & MaxDD<=50%。"""
import pandas as pd

from engine import buy_and_hold, compute_metrics, download_one
from strategies import strat_sma_leveraged, strat_momentum_stocks, strat_dual_momentum
from strategies_v2 import (
    strat_adaptive_rp,
    strat_dual_sma_vol_brake,
    strat_mom_plus_leverage,
)

START = "2010-03-01"
START_MOM = "2012-06-01"
END = "2026-05-12"

UNIVERSE_MOM = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AMD", "AVGO",
    "NFLX", "CRM", "ORCL", "ADBE", "QCOM", "INTC", "LRCX", "ASML", "TSM",
    "MU", "JPM", "V", "MA", "JNJ", "PG", "UNH", "HD", "WMT", "DIS",
]


def run():
    results = {}

    qqq = download_one("QQQ")["Close"].loc[START:END]
    results["BH_QQQ"] = buy_and_hold(qqq)
    tqqq = download_one("TQQQ")["Close"].loc[START:END]
    results["BH_TQQQ"] = buy_and_hold(tqqq)

    # ===== 策略 6 网格: 杠杆比例 + Top-N + lookback =====
    print("\n[策略6] 动量Top-N + TQQQ杠杆叠加")
    for lev in [0.20, 0.30, 0.40, 0.50]:
        for topn in [3, 5, 7]:
            for lb in [126, 189]:
                eq, _, n = strat_mom_plus_leverage(
                    universe=UNIVERSE_MOM, leverage_ticker="TQQQ",
                    benchmark="QQQ", safe_ticker="BIL",
                    lookback=lb, skip=21, top_n=topn,
                    sma_long=200, sma_short=50,
                    leverage_alloc=lev,
                    start=START_MOM, end=END,
                )
                results[f"S6_lev{int(lev*100)}_top{topn}_lb{lb}"] = eq

    # ===== 策略 7 网格: 双均线 + 波动率刹车 =====
    print("[策略7] 双SMA + 波动刹车")
    for vthr in [0.40, 0.50, 0.60, 9.99]:  # 9.99 = 关闭刹车
        for sma_short in [20, 50, 100]:
            eq, _, n = strat_dual_sma_vol_brake(
                signal_ticker="QQQ", bull_ticker="TQQQ", bear_ticker="BIL",
                sma_long=200, sma_short=sma_short,
                vol_window=20, vol_threshold=vthr,
                half_weight_when_weak=True,
                start=START, end=END,
            )
            results[f"S7_SMA200/{sma_short}_vol{int(vthr*100)}"] = eq

    # ===== 策略 8: 自适应风险平价 =====
    print("[策略8] 动态风险平价 (UPRO/TMF/GLD)")
    eq, _, n = strat_adaptive_rp(
        pool=("UPRO", "TMF", "GLD"),
        safe_ticker="BIL", lookback_mom=126, lookback_vol=60,
        momentum_filter=True, start=START, end=END,
    )
    results["S8_AdapRP_UPRO_TMF_GLD"] = eq

    eq, _, n = strat_adaptive_rp(
        pool=("UPRO", "TQQQ", "TMF", "GLD"),
        safe_ticker="BIL", lookback_mom=126, lookback_vol=60,
        momentum_filter=True, start=START, end=END,
    )
    results["S8_AdapRP_UPRO_TQQQ_TMF_GLD"] = eq

    # ===== 复用最佳基准 =====
    eq, _, n = strat_momentum_stocks(
        universe=UNIVERSE_MOM, benchmark="QQQ", safe_ticker="BIL",
        lookback=126, skip=21, top_n=5, sma_window=200, rebalance="ME",
        start=START_MOM, end=END,
    )
    results[n + "_base"] = eq

    rows = []
    for name, eq in results.items():
        m = compute_metrics(eq)
        rows.append({"name": name, **m.to_dict()})
    df = pd.DataFrame(rows).set_index("name").sort_values("CAGR", ascending=False)
    pd.options.display.float_format = "{:.4f}".format
    print("\n============ 第二轮全部结果 (按 CAGR 降序, 共 {} 个) ============".format(len(df)))
    print(df.head(30).to_string())

    print("\n============ 目标达成 (CAGR>=40%, |MaxDD|<=50%) ============")
    qualified = df[(df["CAGR"] >= 0.40) & (df["MaxDD"] >= -0.50)]
    if len(qualified):
        print(qualified.to_string())
    else:
        print("无")
        soft = df[(df["CAGR"] >= 0.35) & (df["MaxDD"] >= -0.50)]
        print(f"\n软指标 CAGR>=35% & DD<=50%: {len(soft)} 个")
        print(soft.to_string())

    df.to_csv("results/phase2_summary.csv")
    print("\n已保存到 results/phase2_summary.csv")


if __name__ == "__main__":
    run()
