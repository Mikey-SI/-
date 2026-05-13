"""
量化回测核心引擎
- 数据下载（yfinance，本地缓存）
- 回测/指标计算（年化收益、年化波动、夏普、最大回撤、卡玛、胜率）
- 通用绘图
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Dict, Iterable, Optional

import numpy as np
import pandas as pd
import yfinance as yf

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)


# ----------------------------- 数据 ----------------------------- #

def _cache_path(ticker: str) -> str:
    return os.path.join(DATA_DIR, f"{ticker.replace('^','_').replace('=','_')}.csv")


def download_one(ticker: str, start: str = "2000-01-01", end: Optional[str] = None,
                 refresh: bool = False, max_retries: int = 4) -> pd.DataFrame:
    """下载单标的价格(优先用本地缓存)。返回带 Close/Open/High/Low/Volume 的 DataFrame。"""
    path = _cache_path(ticker)
    if not refresh and os.path.exists(path):
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        return df
    last_err: Optional[Exception] = None
    for attempt in range(max_retries):
        try:
            raw = yf.download(ticker, start=start, end=end, progress=False,
                              auto_adjust=True, threads=False)
            if raw is None or raw.empty:
                raise RuntimeError("空数据")
            if isinstance(raw.columns, pd.MultiIndex):
                raw.columns = raw.columns.get_level_values(0)
            raw = raw[["Open", "High", "Low", "Close", "Volume"]].dropna()
            raw.index = pd.to_datetime(raw.index)
            raw.to_csv(path)
            return raw
        except Exception as e:
            last_err = e
            time.sleep(1.0 + attempt * 1.5)
    raise RuntimeError(f"下载 {ticker} 失败: {last_err}")


def get_prices(tickers: Iterable[str], start: str = "2000-01-01",
               end: Optional[str] = None, refresh: bool = False) -> pd.DataFrame:
    """返回所有 ticker 的 Close 收盘价 DataFrame (列=ticker)。"""
    closes = {}
    for t in tickers:
        try:
            df = download_one(t, start=start, end=end, refresh=refresh)
            closes[t] = df["Close"]
        except Exception as e:
            print(f"  [WARN] {t} 下载失败: {e}")
    out = pd.concat(closes, axis=1).sort_index()
    return out


# ----------------------------- 指标 ----------------------------- #

TRADING_DAYS = 252


@dataclass
class Metrics:
    cagr: float
    vol: float
    sharpe: float
    sortino: float
    max_dd: float
    calmar: float
    win_rate: float
    total_return: float
    years: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "CAGR": self.cagr, "Vol": self.vol, "Sharpe": self.sharpe,
            "Sortino": self.sortino, "MaxDD": self.max_dd, "Calmar": self.calmar,
            "WinRate": self.win_rate, "TotalRet": self.total_return, "Years": self.years,
        }


def compute_metrics(equity: pd.Series, rf: float = 0.0) -> Metrics:
    """根据净值曲线计算指标。equity: 净值（起点为1）。"""
    equity = equity.dropna()
    if len(equity) < 2:
        return Metrics(0, 0, 0, 0, 0, 0, 0, 0, 0)
    rets = equity.pct_change().dropna()
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    total_ret = float(equity.iloc[-1] / equity.iloc[0] - 1)
    cagr = (1 + total_ret) ** (1 / max(years, 1e-9)) - 1
    vol = float(rets.std() * np.sqrt(TRADING_DAYS))
    excess = rets - rf / TRADING_DAYS
    sharpe = float(excess.mean() / (rets.std() + 1e-12) * np.sqrt(TRADING_DAYS))
    downside = rets[rets < 0]
    sortino = float(excess.mean() / (downside.std() + 1e-12) * np.sqrt(TRADING_DAYS))
    dd_series = equity / equity.cummax() - 1
    max_dd = float(dd_series.min())
    calmar = cagr / abs(max_dd) if max_dd < 0 else np.nan
    win_rate = float((rets > 0).mean())
    return Metrics(cagr, vol, sharpe, sortino, max_dd, calmar, win_rate, total_ret, years)


def print_metrics(name: str, m: Metrics) -> None:
    print(f"=== {name} ===")
    print(f"  期间       : {m.years:.1f} 年")
    print(f"  年化收益   : {m.cagr*100:7.2f}%")
    print(f"  年化波动   : {m.vol*100:7.2f}%")
    print(f"  夏普比率   : {m.sharpe:7.2f}")
    print(f"  索提诺     : {m.sortino:7.2f}")
    print(f"  最大回撤   : {m.max_dd*100:7.2f}%")
    print(f"  卡玛比率   : {m.calmar:7.2f}")
    print(f"  日胜率     : {m.win_rate*100:7.2f}%")
    print(f"  累计收益   : {m.total_return*100:7.2f}%")


# ----------------------------- 回测 ----------------------------- #

def backtest_weights(prices: pd.DataFrame, weights: pd.DataFrame,
                     fee_bps: float = 1.0) -> pd.Series:
    """
    根据每日目标权重回测，按收盘价调仓，扣除调仓换手 * fee_bps/10000 的成本。
    prices: 列=ticker，行=日期 (收盘价)
    weights: 同形状的目标权重 (允许行和 != 1, 表示可有现金或杠杆)
    返回净值曲线（起点=1.0）。
    """
    prices = prices.copy().sort_index().ffill()
    weights = weights.reindex(prices.index).ffill().fillna(0.0)
    rets = prices.pct_change().fillna(0.0)
    # 第t日的策略收益 = 上一日权重 * 当日收益
    w_lag = weights.shift(1).fillna(0.0)
    strat_ret = (w_lag * rets).sum(axis=1)
    # 换手成本：|w_t - w_{t-1}|.sum() * fee
    turnover = (weights - w_lag).abs().sum(axis=1)
    cost = turnover * (fee_bps / 10000.0)
    net = strat_ret - cost
    equity = (1 + net).cumprod()
    equity.iloc[0] = 1.0
    return equity


def buy_and_hold(prices: pd.Series) -> pd.Series:
    p = prices.dropna()
    return p / p.iloc[0]
