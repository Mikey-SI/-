"""
最终冠军策略 + 可视化 + 实盘信号
====================================
参数: lev=20%, top_n=3, lookback=126, sma_short=20, sma_long=200
全样本表现: CAGR 45.8%, MaxDD -46.2%, Sharpe 1.30, Calmar 0.99
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from engine import buy_and_hold, compute_metrics, download_one, print_metrics
from strategies_v2 import strat_mom_plus_leverage

UNIVERSE = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AMD", "AVGO",
    "NFLX", "CRM", "ORCL", "ADBE", "QCOM", "INTC", "LRCX", "ASML", "TSM",
    "MU", "JPM", "V", "MA", "JNJ", "PG", "UNH", "HD", "WMT", "DIS",
]
PARAMS = dict(lookback=126, skip=21, top_n=3, sma_long=200, sma_short=20,
              leverage_alloc=0.20)
START = "2012-06-01"
END = "2026-05-12"


def make_plots():
    eq, weights, name = strat_mom_plus_leverage(
        universe=UNIVERSE, leverage_ticker="TQQQ", benchmark="QQQ",
        safe_ticker="BIL", rebalance="ME", start=START, end=END, **PARAMS,
    )
    qqq = download_one("QQQ")["Close"].loc[START:END]
    spy = download_one("SPY")["Close"].loc[START:END]
    tqqq = download_one("TQQQ")["Close"].loc[START:END]
    bh_qqq = buy_and_hold(qqq)
    bh_spy = buy_and_hold(spy)
    bh_tqqq = buy_and_hold(tqqq)

    print("=" * 60)
    print_metrics("【冠军策略】MomTop3+TQQQ_Lev20", compute_metrics(eq))
    print()
    print_metrics("基准: BH QQQ", compute_metrics(bh_qqq))
    print_metrics("基准: BH SPY", compute_metrics(bh_spy))
    print_metrics("基准: BH TQQQ", compute_metrics(bh_tqqq))

    # ---------- 图 1: 净值曲线 (log) + 回撤 ----------
    fig, axes = plt.subplots(2, 1, figsize=(13, 8), sharex=True,
                             gridspec_kw={"height_ratios": [3, 1]})
    ax = axes[0]
    ax.plot(eq.index, eq.values, label=f"Strategy (CAGR {compute_metrics(eq).cagr*100:.1f}%)",
            lw=2.0, color="#d62728")
    ax.plot(bh_qqq.index, bh_qqq.values, label=f"BH QQQ ({compute_metrics(bh_qqq).cagr*100:.1f}%)",
            lw=1.0, color="#1f77b4", alpha=0.8)
    ax.plot(bh_spy.index, bh_spy.values, label=f"BH SPY ({compute_metrics(bh_spy).cagr*100:.1f}%)",
            lw=1.0, color="#2ca02c", alpha=0.8)
    ax.plot(bh_tqqq.index, bh_tqqq.values, label=f"BH TQQQ ({compute_metrics(bh_tqqq).cagr*100:.1f}%)",
            lw=1.0, color="#ff7f0e", alpha=0.6, ls="--")
    ax.set_yscale("log")
    ax.set_title("Equity Curves (Log Scale) — 2012-06 to 2026-05", fontsize=13)
    ax.set_ylabel("Equity (start=1)")
    ax.legend(loc="upper left")
    ax.grid(True, alpha=0.3)

    ax2 = axes[1]
    dd_strat = eq / eq.cummax() - 1
    dd_qqq = bh_qqq / bh_qqq.cummax() - 1
    ax2.fill_between(dd_strat.index, dd_strat.values * 100, 0,
                     color="#d62728", alpha=0.5, label="Strategy DD")
    ax2.plot(dd_qqq.index, dd_qqq.values * 100, color="#1f77b4",
             alpha=0.7, lw=1.0, label="QQQ DD")
    ax2.set_ylabel("Drawdown (%)")
    ax2.set_xlabel("Date")
    ax2.legend(loc="lower left")
    ax2.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig("results/equity_drawdown.png", dpi=130, bbox_inches="tight")
    plt.close()
    print("\n[图] results/equity_drawdown.png")

    # ---------- 图 2: 年度收益柱状图 ----------
    fig, ax = plt.subplots(figsize=(13, 5))
    yr_strat = eq.resample("YE").last().pct_change().dropna()
    yr_qqq = bh_qqq.reindex(eq.index).ffill().resample("YE").last().pct_change().dropna()
    yrs = yr_strat.index.year
    width = 0.4
    x = np.arange(len(yrs))
    ax.bar(x - width / 2, yr_strat.values * 100, width=width, color="#d62728",
           label="Strategy")
    ax.bar(x + width / 2, yr_qqq.reindex(yr_strat.index).values * 100, width=width,
           color="#1f77b4", alpha=0.7, label="QQQ")
    ax.set_xticks(x)
    ax.set_xticklabels(yrs, rotation=0)
    ax.set_ylabel("Annual Return (%)")
    ax.set_title("Annual Returns — Strategy vs QQQ")
    ax.axhline(0, color="black", lw=0.5)
    ax.axhline(40, color="green", ls=":", lw=0.8, alpha=0.7, label="Target 40%")
    ax.legend()
    ax.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig("results/annual_returns.png", dpi=130, bbox_inches="tight")
    plt.close()
    print("[图] results/annual_returns.png")

    # ---------- 图 3: 持仓权重 stack plot ----------
    fig, ax = plt.subplots(figsize=(13, 5))
    nonzero_cols = weights.loc[:, (weights.abs().sum() > 0)]
    nonzero_cols.plot.area(ax=ax, linewidth=0, alpha=0.85,
                          cmap="tab20", legend="reverse")
    ax.set_ylim(0, 1.02)
    ax.set_ylabel("Weight")
    ax.set_title("Position Allocation Over Time")
    ax.legend(loc="center left", bbox_to_anchor=(1.0, 0.5), fontsize=8, ncol=1)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig("results/positions.png", dpi=130, bbox_inches="tight")
    plt.close()
    print("[图] results/positions.png")

    # ---------- 表 4: 年度收益表 ----------
    yr_table = pd.DataFrame({
        "Strategy": yr_strat * 100,
        "QQQ":      yr_qqq.reindex(yr_strat.index) * 100,
        "Excess":   (yr_strat - yr_qqq.reindex(yr_strat.index)) * 100,
    }).round(2)
    print("\n========== 年度收益 (%) ==========")
    print(yr_table.to_string())
    yr_table.to_csv("results/annual_returns.csv")

    # ---------- 输出当前最新持仓 ----------
    latest_w = weights.iloc[-1]
    latest_w = latest_w[latest_w > 0].sort_values(ascending=False)
    print("\n========== 当前 (回测末日) 持仓 ==========")
    print(latest_w.round(4).to_string())

    eq.to_csv("results/champion_equity.csv")
    weights.to_csv("results/champion_weights.csv")
    print("\n[数据] results/champion_equity.csv, champion_weights.csv")
    return eq, weights


def latest_signal():
    """打印今天 (最新数据) 应该如何调仓"""
    print("\n" + "=" * 60)
    print("【实盘信号 - 最新月末持仓建议】")
    print("=" * 60)
    eq, weights, _ = strat_mom_plus_leverage(
        universe=UNIVERSE, leverage_ticker="TQQQ", benchmark="QQQ",
        safe_ticker="BIL", rebalance="ME", start=START, end=None, **PARAMS,
    )
    last = weights.iloc[-1]
    last = last[last > 0].sort_values(ascending=False)
    print(f"\n信号日期: {weights.index[-1].date()}")
    print(f"目标持仓:")
    for t, w in last.items():
        print(f"  {t:<8s}  {w*100:6.2f}%")
    print()
    qqq = download_one("QQQ")["Close"]
    sma200 = qqq.rolling(200).mean().iloc[-1]
    sma20 = qqq.rolling(20).mean().iloc[-1]
    px = qqq.iloc[-1]
    print(f"QQQ 现价 {px:.2f}, SMA200={sma200:.2f}, SMA20={sma20:.2f}")
    state = "强牛 (满杠杆)" if (px > sma200 and px > sma20) else (
        "弱牛 (无杠杆)" if px > sma200 else "熊市 (100% BIL)")
    print(f"市场状态: {state}")


if __name__ == "__main__":
    os.makedirs("results", exist_ok=True)
    eq, weights = make_plots()
    latest_signal()
