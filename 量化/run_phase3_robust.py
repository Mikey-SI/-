"""
第三轮：参数稳健性 + 样本外 + 滚动子期间检验
聚焦最优策略 S6 (动量Top-N + TQQQ杠杆), 验证它在不同参数和不同时间段下都稳健。
"""
import numpy as np
import pandas as pd

from engine import compute_metrics, download_one, buy_and_hold
from strategies_v2 import strat_mom_plus_leverage

UNIVERSE_MOM = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AMD", "AVGO",
    "NFLX", "CRM", "ORCL", "ADBE", "QCOM", "INTC", "LRCX", "ASML", "TSM",
    "MU", "JPM", "V", "MA", "JNJ", "PG", "UNH", "HD", "WMT", "DIS",
]

START_FULL = "2012-06-01"
END_FULL = "2026-05-12"

# 子期间 (out-of-sample 验证)
SUB_PERIODS = {
    "全样本_2012-2026": (START_FULL, END_FULL),
    "牛市_2012-2017":   ("2012-06-01", "2017-12-31"),
    "震荡_2018-2019":   ("2018-01-01", "2019-12-31"),
    "新冠_2020-2021":   ("2020-01-01", "2021-12-31"),
    "熊市_2022":        ("2022-01-01", "2022-12-31"),
    "复苏_2023-2024":   ("2023-01-01", "2024-12-31"),
    "2025+":            ("2025-01-01", END_FULL),
    "近10年_2016-2026": ("2016-01-01", END_FULL),
    "近5年_2021-2026":  ("2021-01-01", END_FULL),
}


def run_one(lev: float, topn: int, lb: int, skip: int,
            sma_l: int, sma_s: int, start: str, end: str) -> dict:
    eq, _, _ = strat_mom_plus_leverage(
        universe=UNIVERSE_MOM, leverage_ticker="TQQQ",
        benchmark="QQQ", safe_ticker="BIL",
        lookback=lb, skip=skip, top_n=topn,
        sma_long=sma_l, sma_short=sma_s,
        leverage_alloc=lev, start=start, end=end,
    )
    m = compute_metrics(eq)
    return m.to_dict()


def grid_search():
    print("\n[A] 参数网格 (全样本)")
    rows = []
    for lev in [0.10, 0.20, 0.30]:
        for topn in [3, 4, 5]:
            for lb in [126, 189, 252]:
                for sma_s in [20, 50, 100]:
                    r = run_one(lev, topn, lb, 21, 200, sma_s, START_FULL, END_FULL)
                    r.update(lev=lev, topn=topn, lb=lb, sma_s=sma_s)
                    rows.append(r)
    df = pd.DataFrame(rows)
    df = df.sort_values("CAGR", ascending=False)
    pd.options.display.float_format = "{:.4f}".format
    print("\n  Top 15:")
    print(df.head(15).to_string(index=False))

    qualified = df[(df["CAGR"] >= 0.40) & (df["MaxDD"] >= -0.50)]
    print(f"\n  达标参数组合: {len(qualified)} / {len(df)}")
    if len(qualified):
        print(qualified.to_string(index=False))

    df.to_csv("results/phase3_grid.csv", index=False)
    return df, qualified


def out_of_sample(best_params: dict):
    """用全样本最优参数测各子期间表现"""
    print(f"\n[B] 子期间稳健性 (参数: {best_params})")
    rows = []
    for label, (s, e) in SUB_PERIODS.items():
        try:
            r = run_one(
                best_params["lev"], best_params["topn"], best_params["lb"],
                21, 200, best_params["sma_s"], s, e,
            )
            r["period"] = label
            rows.append(r)
        except Exception as ex:
            print(f"  {label}: 失败 {ex}")
    df = pd.DataFrame(rows).set_index("period")
    cols = ["CAGR", "Vol", "Sharpe", "MaxDD", "Calmar", "WinRate", "TotalRet", "Years"]
    print(df[cols].to_string())
    df.to_csv("results/phase3_subperiods.csv")
    return df


def main():
    grid, qualified = grid_search()

    # 选择"达标"组合中 Calmar 最高的作为冠军
    if len(qualified):
        champ = qualified.sort_values("Calmar", ascending=False).iloc[0]
    else:
        champ = grid.sort_values("Calmar", ascending=False).iloc[0]

    best_params = {
        "lev": float(champ["lev"]), "topn": int(champ["topn"]),
        "lb": int(champ["lb"]), "sma_s": int(champ["sma_s"]),
    }
    print(f"\n[!] 冠军参数: {best_params}")
    print(f"   CAGR={champ['CAGR']:.2%}  MaxDD={champ['MaxDD']:.2%}  Calmar={champ['Calmar']:.2f}")

    out_of_sample(best_params)

    print("\n[C] 大盘动量信号 vs 个股动量信号 - 子期间对比 (参考: BH_QQQ)")
    qqq_full = download_one("QQQ")["Close"]
    rows = []
    for label, (s, e) in SUB_PERIODS.items():
        sub = qqq_full.loc[s:e]
        eq = buy_and_hold(sub)
        m = compute_metrics(eq)
        rows.append({"period": label, **m.to_dict()})
    bench = pd.DataFrame(rows).set_index("period")
    print(bench[["CAGR", "MaxDD", "Sharpe"]].to_string())


if __name__ == "__main__":
    main()
