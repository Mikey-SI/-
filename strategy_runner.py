"""Daily runner for the momentum + leveraged-ETF strategy.

Strategy summary (see 量化/策略说明.md for full rules):
  - Universe: 28 large-cap US stocks
  - Bench:    QQQ  (SMA200 / SMA20 regime filter)
  - Levered:  TQQQ (added on strong-bull)
  - Safe:     BIL  (full position when bear)

Each run:
  1. Pull recent daily price data via yfinance for all symbols.
  2. Determine regime via QQQ vs SMA200 / SMA20.
  3. Rank universe by lookback momentum (126d return skipping last 21d).
  4. Output target weights for the next rebalance.
  5. Write JSON snapshot to docs/data/strategy_signal.json.
  6. Email a digest to all configured recipients.

The script is intentionally self-contained so it can run on GitHub Actions
without pulling the heavier backtesting code in 量化/.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Dict, List

import pandas as pd
import yfinance as yf


UNIVERSE: List[str] = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AMD", "AVGO",
    "NFLX", "CRM", "ORCL", "ADBE", "QCOM", "INTC", "LRCX", "ASML", "TSM",
    "MU", "JPM", "V", "MA", "JNJ", "PG", "UNH", "HD", "WMT", "DIS",
]
LEVERAGE_TICKER = "TQQQ"
BENCH_TICKER = "QQQ"
SAFE_TICKER = "BIL"

LOOKBACK = 126
SKIP = 21
TOP_N = 3
SMA_LONG = 200
SMA_SHORT = 20
LEVERAGE_ALLOC = 0.20

BJ_TZ = timezone(timedelta(hours=8))
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "docs", "data", "strategy_signal.json")


@dataclass
class Signal:
    timestamp: str
    bench_close: float
    sma200: float
    sma20: float
    regime: str  # strong_bull | weak_bull | bear
    leverage_alloc: float
    momentum_scores: Dict[str, float]
    selected: List[str]
    weights: Dict[str, float]
    notes: str

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "signal": "BUY" if self.regime != "bear" else "HOLD-CASH",
            "regime": self.regime,
            "bench_close": round(self.bench_close, 2),
            "sma200": round(self.sma200, 2),
            "sma20": round(self.sma20, 2),
            "leverage_alloc": self.leverage_alloc,
            "selected": self.selected,
            "weights": {k: round(v, 4) for k, v in self.weights.items()},
            "top_momentum": {k: round(v, 4) for k, v in sorted(self.momentum_scores.items(), key=lambda kv: -kv[1])[:10]},
            "notes": self.notes,
        }


def fetch_history(tickers: List[str], period: str = "13mo") -> pd.DataFrame:
    """Download daily Close prices for all tickers via yfinance."""
    closes: Dict[str, pd.Series] = {}
    for t in tickers:
        try:
            df = yf.download(t, period=period, progress=False, auto_adjust=True, threads=False)
            if df is None or df.empty:
                continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            closes[t] = df["Close"].dropna()
        except Exception as e:
            print(f"[warn] download {t} failed: {e}")
    if not closes:
        raise RuntimeError("No price data downloaded.")
    out = pd.concat(closes, axis=1).sort_index().ffill()
    return out


def build_signal(prices: pd.DataFrame) -> Signal:
    bench = prices[BENCH_TICKER].dropna()
    last = bench.iloc[-1]
    sma_l = bench.rolling(SMA_LONG).mean().iloc[-1]
    sma_s = bench.rolling(SMA_SHORT).mean().iloc[-1]

    universe_px = prices[UNIVERSE].dropna(how="all")
    momentum = universe_px.shift(SKIP).pct_change(LOOKBACK - SKIP).iloc[-1].dropna()
    momentum_scores = momentum.to_dict()

    notes_parts = []
    weights: Dict[str, float] = {}
    selected: List[str] = []
    if pd.isna(sma_l) or last <= sma_l:
        regime = "bear"
        lev = 0.0
        weights[SAFE_TICKER] = 1.0
        notes_parts.append("QQQ <= SMA200, holding 100% BIL.")
    else:
        strong = (not pd.isna(sma_s)) and last > sma_s
        regime = "strong_bull" if strong else "weak_bull"
        lev = LEVERAGE_ALLOC if strong else 0.0
        stock_total = 1.0 - lev
        ranked = momentum.sort_values(ascending=False)
        selected = ranked.head(TOP_N).index.tolist()
        if selected:
            w_each = stock_total / len(selected)
            for t in selected:
                weights[t] = w_each
        if lev > 0:
            weights[LEVERAGE_TICKER] = lev
        notes_parts.append(f"QQQ > SMA200; {'strong bull (SMA20 also broken)' if strong else 'weak bull (below SMA20)'}.")
        notes_parts.append(f"Top-{TOP_N} momentum names selected.")

    notes_parts.append(
        "Rebalance executes on last trading day of each month; intra-month positions are held."
    )

    return Signal(
        timestamp=datetime.now(BJ_TZ).strftime("%Y-%m-%d %H:%M %Z"),
        bench_close=float(last),
        sma200=float(sma_l) if not pd.isna(sma_l) else float("nan"),
        sma20=float(sma_s) if not pd.isna(sma_s) else float("nan"),
        regime=regime,
        leverage_alloc=lev,
        momentum_scores=momentum_scores,
        selected=selected,
        weights=weights,
        notes=" ".join(notes_parts),
    )


def write_signal_json(signal: Signal, path: str = OUTPUT_PATH) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(signal.to_dict(), f, ensure_ascii=False, indent=2, default=str)
    print(f"[ok] wrote {path}")


def format_email_html(signal: Signal) -> str:
    rows = "".join(
        f"<tr><td style='padding:6px 10px;border-bottom:1px solid #1e1e2e;color:#fff;font-weight:600'>{t}</td>"
        f"<td style='padding:6px 10px;border-bottom:1px solid #1e1e2e;color:#00d26a;text-align:right'>{w*100:.2f}%</td></tr>"
        for t, w in sorted(signal.weights.items(), key=lambda kv: -kv[1])
    )
    momentum_rows = "".join(
        f"<tr><td style='padding:5px 10px;border-bottom:1px solid #1e1e2e;color:#c0c0d0'>{t}</td>"
        f"<td style='padding:5px 10px;border-bottom:1px solid #1e1e2e;color:#c0c0d0;text-align:right'>{s*100:.2f}%</td></tr>"
        for t, s in sorted(signal.momentum_scores.items(), key=lambda kv: -kv[1])[:10]
    )
    regime_color = {
        "strong_bull": "#00d26a",
        "weak_bull": "#ffd60a",
        "bear": "#e63946",
    }.get(signal.regime, "#c0c0d0")
    return f"""
    <div style='font-family:Inter,Segoe UI,sans-serif;background:#0a0a0f;color:#c0c0d0;padding:24px;'>
      <h2 style='color:#fff;border-bottom:2px solid #e63946;padding-bottom:8px'>📈 Momentum + Leverage Strategy — Daily Signal</h2>
      <p style='color:#8888a0;font-size:13px'>Generated {signal.timestamp}</p>

      <div style='margin:18px 0'>
        <span style='display:inline-block;padding:4px 14px;border-radius:12px;background:{regime_color};color:#0a0a0f;font-weight:700;letter-spacing:1px'>
          {signal.regime.upper().replace('_', ' ')}
        </span>
      </div>

      <table style='border-collapse:collapse;font-size:13px;margin-bottom:18px'>
        <tr><td style='padding:4px 12px;color:#8888a0'>QQQ close</td><td style='padding:4px 12px;color:#fff'>{signal.bench_close:.2f}</td></tr>
        <tr><td style='padding:4px 12px;color:#8888a0'>SMA200</td><td style='padding:4px 12px;color:#fff'>{signal.sma200:.2f}</td></tr>
        <tr><td style='padding:4px 12px;color:#8888a0'>SMA20</td><td style='padding:4px 12px;color:#fff'>{signal.sma20:.2f}</td></tr>
        <tr><td style='padding:4px 12px;color:#8888a0'>Leverage allocation</td><td style='padding:4px 12px;color:#fff'>{signal.leverage_alloc*100:.0f}%</td></tr>
      </table>

      <h3 style='color:#fff'>🎯 Target Weights</h3>
      <table style='border-collapse:collapse;width:320px;background:#12121a'>{rows}</table>

      <h3 style='color:#fff;margin-top:24px'>Top-10 Momentum Snapshot (105d look-back)</h3>
      <table style='border-collapse:collapse;width:320px;background:#12121a'>{momentum_rows}</table>

      <p style='color:#707090;font-size:12px;margin-top:24px;line-height:1.6'>{signal.notes}</p>
      <p style='color:#404060;font-size:11px;margin-top:20px'>Automated by GitHub Actions / Alpha Signal</p>
    </div>
    """


def send_strategy_email(signal: Signal) -> None:
    try:
        from email_service import send_email
    except Exception as e:
        print(f"[warn] email module unavailable: {e}")
        return
    subject = f"📈 Strategy Signal · {signal.regime.replace('_', ' ').title()} · {signal.timestamp[:10]}"
    html = format_email_html(signal)
    try:
        ok = send_email(subject, html)
        print(f"[email] sent={ok}")
    except Exception as e:
        print(f"[warn] email send failed: {e}")


def main() -> int:
    tickers = list(dict.fromkeys(UNIVERSE + [BENCH_TICKER, LEVERAGE_TICKER, SAFE_TICKER]))
    print(f"[info] downloading {len(tickers)} tickers...")
    prices = fetch_history(tickers)
    print(f"[info] last bar: {prices.index[-1].date()}")
    signal = build_signal(prices)
    print(f"[signal] regime={signal.regime} weights={signal.weights}")
    write_signal_json(signal)
    if "--no-email" not in sys.argv:
        send_strategy_email(signal)
    return 0


if __name__ == "__main__":
    sys.exit(main())
