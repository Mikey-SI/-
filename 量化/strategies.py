"""
量化策略实现集合（统一接口）
每个策略返回 (equity_curve, weights_df) 二元组。
weights_df: 各资产每日权重
equity_curve: 净值
"""
from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np
import pandas as pd

from engine import backtest_weights, download_one


# ----------------------------- 工具 ----------------------------- #

def _aligned_close(tickers: List[str], start: Optional[str] = None,
                   end: Optional[str] = None) -> pd.DataFrame:
    """读取多个标的收盘价并按交集索引对齐。"""
    series = {}
    for t in tickers:
        df = download_one(t)
        if start is not None:
            df = df.loc[df.index >= pd.to_datetime(start)]
        if end is not None:
            df = df.loc[df.index <= pd.to_datetime(end)]
        series[t] = df["Close"]
    px = pd.concat(series, axis=1).dropna(how="any")
    return px


# ===================== 策略 1: SMA 趋势 + 杠杆 ETF ===================== #

def strat_sma_leveraged(
    signal_ticker: str = "QQQ",
    bull_ticker: str = "TQQQ",
    bear_ticker: str = "BIL",
    sma_window: int = 200,
    start: Optional[str] = "2010-03-01",
    end: Optional[str] = None,
    fee_bps: float = 1.0,
) -> Tuple[pd.Series, pd.DataFrame, str]:
    """
    若 signal_ticker 收盘价 > sma_window 日均线 → 100% bull_ticker
    否则 → 100% bear_ticker (现金/短期国债)
    每日检测信号，T+1 收盘调仓 (用 shift(1) 实现)。
    """
    # 信号用 signal 的全部历史 (避免 SMA 起始 NaN)
    sig_full = download_one(signal_ticker)["Close"]
    sma = sig_full.rolling(sma_window).mean()
    signal = (sig_full > sma).astype(float)

    px = _aligned_close([bull_ticker, bear_ticker], start=start, end=end)
    signal = signal.reindex(px.index).ffill().fillna(0.0)

    weights = pd.DataFrame(0.0, index=px.index, columns=px.columns)
    weights[bull_ticker] = signal
    weights[bear_ticker] = 1.0 - signal

    equity = backtest_weights(px, weights, fee_bps=fee_bps)
    name = f"SMA{sma_window}_{signal_ticker}→{bull_ticker}/{bear_ticker}"
    return equity, weights, name


# ===================== 策略 2: 双动量轮动 ===================== #

def strat_dual_momentum(
    pool: List[str],
    safe_ticker: str = "BIL",
    lookback: int = 126,   # ~6个月
    top_n: int = 1,
    rebalance: str = "ME",  # 月度调仓 (pandas 3.0+)
    start: Optional[str] = "2010-03-01",
    end: Optional[str] = None,
    fee_bps: float = 2.0,
) -> Tuple[pd.Series, pd.DataFrame, str]:
    """
    Gary Antonacci 的双动量思想推广：
    - 每月末按过去 lookback 日的累计收益排序，取 Top-N
    - 若所选标的过去 lookback 收益 <= 0，则该仓位换成 safe_ticker
    """
    all_t = list(dict.fromkeys(pool + [safe_ticker]))
    px = _aligned_close(all_t, start=start, end=end)
    pool_px = px[pool]

    # 月末调仓日
    rebal_dates = px.resample(rebalance).last().index
    rebal_dates = [d for d in rebal_dates if d in px.index]

    weights = pd.DataFrame(0.0, index=px.index, columns=px.columns)
    current = pd.Series(0.0, index=px.columns)

    mom = pool_px.pct_change(lookback)

    for d in px.index:
        if d in rebal_dates and not mom.loc[d].isna().any():
            ranked = mom.loc[d].sort_values(ascending=False)
            chosen = ranked.head(top_n)
            new = pd.Series(0.0, index=px.columns)
            w_each = 1.0 / top_n
            for t, m in chosen.items():
                if m > 0:
                    new[t] = w_each
                else:
                    new[safe_ticker] = new[safe_ticker] + w_each
            current = new
        weights.loc[d] = current

    equity = backtest_weights(px, weights, fee_bps=fee_bps)
    name = f"DualMom_L{lookback}_TopN{top_n}_{rebalance}"
    return equity, weights, name


# ===================== 策略 3: 波动率目标 + 趋势过滤 ===================== #

def strat_vol_target_trend(
    risk_ticker: str = "TQQQ",
    safe_ticker: str = "BIL",
    signal_ticker: str = "QQQ",
    sma_window: int = 200,
    target_vol: float = 0.35,   # 目标年化波动 35%
    vol_window: int = 20,
    max_leverage: float = 1.0,
    start: Optional[str] = "2010-03-01",
    end: Optional[str] = None,
    fee_bps: float = 1.0,
) -> Tuple[pd.Series, pd.DataFrame, str]:
    """
    1. 趋势过滤：仅当 signal_ticker > SMA 时启用风险仓位；否则全仓 safe_ticker
    2. 波动率目标：根据 risk_ticker 近 vol_window 日的年化波动，缩放权重 = min(target/realized, max_lev)
    """
    sig_full = download_one(signal_ticker)["Close"]
    sma = sig_full.rolling(sma_window).mean()
    trend_on = (sig_full > sma).astype(float)

    px = _aligned_close([risk_ticker, safe_ticker], start=start, end=end)
    trend_on = trend_on.reindex(px.index).ffill().fillna(0.0)

    risk_ret = px[risk_ticker].pct_change()
    realized_vol = risk_ret.rolling(vol_window).std() * np.sqrt(252)
    scale = (target_vol / realized_vol).clip(upper=max_leverage).fillna(0.0)
    scale = scale.shift(1).fillna(0.0)

    w_risk = trend_on * scale
    w_risk = w_risk.clip(0.0, max_leverage)
    w_safe = 1.0 - w_risk

    weights = pd.DataFrame(0.0, index=px.index, columns=px.columns)
    weights[risk_ticker] = w_risk
    weights[safe_ticker] = w_safe.clip(lower=0.0)

    equity = backtest_weights(px, weights, fee_bps=fee_bps)
    name = f"VolTgt{int(target_vol*100)}_{risk_ticker}_SMA{sma_window}"
    return equity, weights, name


# ===================== 策略 4: Hedgefundie All-Weather (UPRO/TMF) ===================== #

def strat_hedgefundie(
    risk_ticker: str = "UPRO",
    bond_ticker: str = "TMF",
    weight_risk: float = 0.55,
    rebalance: str = "QE",
    start: Optional[str] = "2010-03-01",
    end: Optional[str] = None,
    fee_bps: float = 1.0,
) -> Tuple[pd.Series, pd.DataFrame, str]:
    """经典 Hedgefundie 配置：55% UPRO + 45% TMF，季度再平衡。"""
    px = _aligned_close([risk_ticker, bond_ticker], start=start, end=end)
    rebal_dates = px.resample(rebalance).last().index
    rebal_dates = [d for d in rebal_dates if d in px.index]

    weights = pd.DataFrame(0.0, index=px.index, columns=px.columns)
    current = pd.Series({risk_ticker: weight_risk, bond_ticker: 1 - weight_risk})
    weights.iloc[0] = current
    for d in px.index:
        if d in rebal_dates:
            current = pd.Series({risk_ticker: weight_risk, bond_ticker: 1 - weight_risk})
        weights.loc[d] = current

    equity = backtest_weights(px, weights, fee_bps=fee_bps)
    name = f"Hedgefundie_{int(weight_risk*100)}/{int((1-weight_risk)*100)}_{risk_ticker}/{bond_ticker}"
    return equity, weights, name


# ===================== 策略 5: 纳指动量 Top-N + 大盘趋势过滤 ===================== #

def strat_momentum_stocks(
    universe: List[str],
    benchmark: str = "QQQ",
    safe_ticker: str = "BIL",
    lookback: int = 126,
    skip: int = 21,
    top_n: int = 5,
    sma_window: int = 200,
    rebalance: str = "ME",
    start: Optional[str] = "2012-01-01",
    end: Optional[str] = None,
    fee_bps: float = 5.0,
) -> Tuple[pd.Series, pd.DataFrame, str]:
    """
    Jegadeesh & Titman 横截面动量：过去 lookback 日收益（跳过最近 skip 日的反转）。
    叠加 benchmark > SMA 的大盘趋势过滤：弱势期完全持现金。
    """
    all_t = list(dict.fromkeys(universe + [safe_ticker]))
    px = _aligned_close(all_t, start=start, end=end)
    univ_px = px[universe]

    # 大盘趋势
    bench_full = download_one(benchmark)["Close"]
    sma = bench_full.rolling(sma_window).mean()
    trend_on = (bench_full > sma).astype(float).reindex(px.index).ffill().fillna(0.0)

    # 动量 (跳过最近 skip 日)
    mom = univ_px.shift(skip).pct_change(lookback - skip)

    rebal_dates = px.resample(rebalance).last().index
    rebal_dates = [d for d in rebal_dates if d in px.index]

    weights = pd.DataFrame(0.0, index=px.index, columns=px.columns)
    current = pd.Series(0.0, index=px.columns)

    for d in px.index:
        if d in rebal_dates and not mom.loc[d].isna().all():
            if trend_on.loc[d] >= 0.5:
                ranked = mom.loc[d].dropna().sort_values(ascending=False)
                chosen = ranked.head(top_n).index.tolist()
                new = pd.Series(0.0, index=px.columns)
                if len(chosen) > 0:
                    w = 1.0 / len(chosen)
                    for t in chosen:
                        new[t] = w
                current = new
            else:
                current = pd.Series(0.0, index=px.columns)
                current[safe_ticker] = 1.0
        weights.loc[d] = current

    equity = backtest_weights(px, weights, fee_bps=fee_bps)
    name = f"MomTop{top_n}_L{lookback}S{skip}_SMA{sma_window}_{rebalance}"
    return equity, weights, name
