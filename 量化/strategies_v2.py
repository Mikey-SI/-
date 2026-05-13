"""
增强版策略集（第二轮）：
- 策略6：动量个股 Top-N + 杠杆 ETF 叠加（牛市加杠杆）
- 策略7：双均线 + 波动率刹车 + TQQQ（更平滑的趋势信号，避免假信号）
- 策略8：动态风险平价 UPRO/TMF/GLD/BIL（按动量 + 波动率反比分配权重）
"""
from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np
import pandas as pd

from engine import backtest_weights, download_one
from strategies import _aligned_close


# ===================== 策略 6：动量股 + TQQQ 杠杆叠加 ===================== #

def strat_mom_plus_leverage(
    universe: List[str],
    leverage_ticker: str = "TQQQ",
    benchmark: str = "QQQ",
    safe_ticker: str = "BIL",
    lookback: int = 126,
    skip: int = 21,
    top_n: int = 5,
    sma_long: int = 200,
    sma_short: int = 50,
    leverage_alloc: float = 0.25,   # 牛市时 25% 仓位换成 TQQQ (3x), 等效杠杆 = 1.5
    rebalance: str = "ME",
    start: Optional[str] = "2012-06-01",
    end: Optional[str] = None,
    fee_bps: float = 5.0,
) -> Tuple[pd.Series, pd.DataFrame, str]:
    """
    核心思路:
      - 大盘 SMA200 之上 = 牛市
      - 牛市再分两档:
          * 强牛 (SMA50 也站上): (1-leverage_alloc) * 动量Top-N + leverage_alloc * TQQQ
          * 弱牛 (仅站上 SMA200): 100% 动量Top-N (不加杠杆)
      - 大盘 SMA200 之下 = 熊市: 100% safe_ticker
    """
    all_t = list(dict.fromkeys(universe + [leverage_ticker, safe_ticker]))
    px = _aligned_close(all_t, start=start, end=end)
    univ_px = px[universe]

    bench_full = download_one(benchmark)["Close"]
    sma_l = bench_full.rolling(sma_long).mean()
    sma_s = bench_full.rolling(sma_short).mean()
    on_long = (bench_full > sma_l).astype(float).reindex(px.index).ffill().fillna(0.0)
    on_short = (bench_full > sma_s).astype(float).reindex(px.index).ffill().fillna(0.0)

    mom = univ_px.shift(skip).pct_change(lookback - skip)
    rebal_dates = set(px.resample(rebalance).last().index) & set(px.index)

    weights = pd.DataFrame(0.0, index=px.index, columns=px.columns)
    current = pd.Series(0.0, index=px.columns)

    for d in px.index:
        if d in rebal_dates and not mom.loc[d].isna().all():
            new = pd.Series(0.0, index=px.columns)
            if on_long.loc[d] >= 0.5:
                ranked = mom.loc[d].dropna().sort_values(ascending=False)
                chosen = ranked.head(top_n).index.tolist()
                strong = on_short.loc[d] >= 0.5
                lev_w = leverage_alloc if strong else 0.0
                stock_total = 1.0 - lev_w
                if len(chosen):
                    w_each = stock_total / len(chosen)
                    for t in chosen:
                        new[t] = w_each
                new[leverage_ticker] = new.get(leverage_ticker, 0.0) + lev_w
            else:
                new[safe_ticker] = 1.0
            current = new
        weights.loc[d] = current

    equity = backtest_weights(px, weights, fee_bps=fee_bps)
    name = f"MomLev{int(leverage_alloc*100)}_Top{top_n}_L{lookback}_SMA{sma_long}/{sma_short}"
    return equity, weights, name


# ===================== 策略 7：双均线 + 波动率刹车 + TQQQ ===================== #

def strat_dual_sma_vol_brake(
    signal_ticker: str = "QQQ",
    bull_ticker: str = "TQQQ",
    bear_ticker: str = "BIL",
    sma_long: int = 200,
    sma_short: int = 50,
    vol_window: int = 20,
    vol_threshold: float = 0.45,   # QQQ 年化波动 >45% 时强制减仓
    half_weight_when_weak: bool = True,
    fee_bps: float = 1.0,
    start: Optional[str] = "2010-03-01",
    end: Optional[str] = None,
) -> Tuple[pd.Series, pd.DataFrame, str]:
    """
    双均线 + 波动率刹车：
      - SMA200 之上 + SMA50 之上 + 波动正常 → 100% TQQQ
      - SMA200 之上但 SMA50 跌破 / 波动过高 → 50% TQQQ (减半, 减少回撤)
      - SMA200 之下 → 100% BIL
    """
    sig_full = download_one(signal_ticker)["Close"]
    sma_l = sig_full.rolling(sma_long).mean()
    sma_s = sig_full.rolling(sma_short).mean()
    vol = sig_full.pct_change().rolling(vol_window).std() * np.sqrt(252)

    px = _aligned_close([bull_ticker, bear_ticker], start=start, end=end)
    sig_full = sig_full.reindex(px.index).ffill()
    sma_l = sma_l.reindex(px.index).ffill()
    sma_s = sma_s.reindex(px.index).ffill()
    vol = vol.reindex(px.index).ffill().fillna(0.0)

    above_long = sig_full > sma_l
    above_short = sig_full > sma_s
    vol_ok = vol < vol_threshold

    w_bull = pd.Series(0.0, index=px.index)
    if half_weight_when_weak:
        full_signal = above_long & above_short & vol_ok
        half_signal = above_long & (~full_signal)
        w_bull[full_signal] = 1.0
        w_bull[half_signal] = 0.5
    else:
        w_bull[above_long & vol_ok] = 1.0

    w_bull = w_bull.shift(1).fillna(0.0)

    weights = pd.DataFrame(0.0, index=px.index, columns=px.columns)
    weights[bull_ticker] = w_bull
    weights[bear_ticker] = 1.0 - w_bull

    equity = backtest_weights(px, weights, fee_bps=fee_bps)
    name = f"DualSMA{sma_long}/{sma_short}_VolBrake_{bull_ticker}"
    return equity, weights, name


# ===================== 策略 8：动态风险平价 (UPRO/TMF/GLD/BIL) ===================== #

def strat_adaptive_rp(
    pool: List[str] = ("UPRO", "TMF", "GLD"),
    safe_ticker: str = "BIL",
    lookback_mom: int = 126,
    lookback_vol: int = 60,
    rebalance: str = "ME",
    momentum_filter: bool = True,
    start: Optional[str] = "2010-03-01",
    end: Optional[str] = None,
    fee_bps: float = 2.0,
) -> Tuple[pd.Series, pd.DataFrame, str]:
    """
    自适应风险平价:
      - 每月对 pool 中过去 126 日动量 > 0 的标的, 按 1/vol 加权
      - 动量 <= 0 的标的换为 safe_ticker
      - 这样 2022 年 TMF 暴跌时会被踢出, 避开双杀
    """
    pool = list(pool)
    all_t = list(dict.fromkeys(pool + [safe_ticker]))
    px = _aligned_close(all_t, start=start, end=end)
    rets = px[pool].pct_change()

    mom = px[pool].pct_change(lookback_mom)
    vol = rets.rolling(lookback_vol).std() * np.sqrt(252)

    rebal_dates = set(px.resample(rebalance).last().index) & set(px.index)
    weights = pd.DataFrame(0.0, index=px.index, columns=px.columns)
    current = pd.Series(0.0, index=px.columns)

    for d in px.index:
        if d in rebal_dates and not vol.loc[d].isna().any():
            new = pd.Series(0.0, index=px.columns)
            picks = []
            for t in pool:
                if (not momentum_filter) or mom.loc[d, t] > 0:
                    picks.append(t)
            if not picks:
                new[safe_ticker] = 1.0
            else:
                inv_vol = 1.0 / vol.loc[d, picks]
                w = inv_vol / inv_vol.sum()
                for t in picks:
                    new[t] = float(w[t])
            current = new
        weights.loc[d] = current

    equity = backtest_weights(px, weights, fee_bps=fee_bps)
    name = f"AdapRP_L{lookback_mom}_{'+'.join(pool)}"
    return equity, weights, name
