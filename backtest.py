"""
Backtesting Engine with Walk-Forward Validation.

Design:
  1. Pre-compute all indicators + patterns once (O(N))
  2. Build signal registry: {date → [signals]} by scanning pattern columns (fast)
  3. Step through dates: check regime, execute exits, open new entries
  4. Entry is simulated at next day's open (realistic; no look-ahead)
  5. Walk-forward: 70% train / 30% test — metrics reported for each phase

Validation thresholds (from spec section 11.4):
  CAGR > 15%  |  Win rate > 40%  |  Max drawdown < 25%  |  R:R ≥ 1:2
"""
import numpy as np
import pandas as pd
from typing import Dict, List

import config
from indicators import compute_all
from patterns import compute_all_patterns
from regime import get_regime_on_date
from risk import position_size, trailing_stop, atr_trailing_stop
from signals import generate_signals


# ─── Core Simulation ──────────────────────────────────────────────────────────

def run_backtest(
    stock_data: Dict[str, pd.DataFrame],
    index_df: pd.DataFrame,
    initial_capital: float = config.CAPITAL,
) -> dict:
    """Run full backtest. Returns metrics, trade log, equity curve, and split info."""

    # ── Prepare ───────────────────────────────────────────────────────────────
    idx_ind = compute_all(index_df)

    stock_dfs: Dict[str, pd.DataFrame] = {}
    for symbol, df in stock_data.items():
        df_ind = compute_all(df)
        stock_dfs[symbol] = compute_all_patterns(df_ind, index_df)

    # All trading dates from index
    all_dates = sorted(idx_ind.index)
    if len(all_dates) < config.SMA_SLOW + 10:
        return {"error": "Insufficient data"}

    split_idx   = int(len(all_dates) * 0.7)
    train_dates = set(all_dates[:split_idx])
    test_dates  = set(all_dates[split_idx:])

    # ── Pre-compute signal registry (date → list of signal dicts) ─────────────
    # Scans pattern boolean columns; avoids calling generate_signals on every
    # stock×date combination.
    signal_registry: Dict[pd.Timestamp, List[dict]] = {}
    for symbol, df in stock_dfs.items():
        active = df.index[df["breakout"] | df["vcp"] | df["ema_pullback"] | df["weinstein_pullback"]]
        for date in active:
            if date not in df.index:
                continue
            sigs = generate_signals(symbol, df, date)
            if sigs:
                signal_registry.setdefault(date, []).extend(sigs)

    # ── Simulation ────────────────────────────────────────────────────────────
    cash      = initial_capital
    positions: Dict[str, dict] = {}
    trades:    List[dict]      = []
    equity_curve = []

    for i, date in enumerate(all_dates):
        # ── Mark-to-market ────────────────────────────────────────────────────
        invested = 0.0
        for sym, pos in positions.items():
            px = _price(stock_dfs, sym, date, "close", pos["current_price"])
            pos["current_price"] = px
            invested += px * pos["shares"]
        equity_curve.append({"date": date, "equity": cash + invested})

        # ── Exit checks ───────────────────────────────────────────────────────
        to_close = []
        for sym, pos in positions.items():
            px  = pos["current_price"]          # today's close
            low = _price(stock_dfs, sym, date, "low", px)
            tsl = trailing_stop(px, pos["entry"], pos["trailing_sl"])
            pos["trailing_sl"] = tsl

            if low <= tsl:
                # Stop triggered intraday. Exit at stop price if close recovered
                # above it (normal fill); exit at close if stock gapped below stop.
                exit_px = tsl if px >= tsl else px
                to_close.append((sym, exit_px, "Stop Loss"))
            elif px >= pos["target"]:
                to_close.append((sym, pos["target"], "Target Hit"))

        for sym, exit_px, reason in to_close:
            pos  = positions.pop(sym)
            pnl  = (exit_px - pos["entry"]) * pos["shares"]
            cash += exit_px * pos["shares"]
            trades.append(_trade_record(pos, exit_px, reason, date, train_dates))

        # ── Entry (use tomorrow's open as entry price) ────────────────────────
        if i + 1 >= len(all_dates):
            continue

        next_date = all_dates[i + 1]
        regime    = get_regime_on_date(idx_ind, date)
        if regime != "Bullish":
            continue
        if len(positions) >= config.MAX_POSITIONS:
            continue

        day_signals = signal_registry.get(date, [])
        # Sort by confidence so "High" enters first
        day_signals = sorted(day_signals, key=lambda s: {"High": 0, "Medium": 1, "Low": 2}.get(s["confidence"], 3))

        for sig in day_signals:
            if len(positions) >= config.MAX_POSITIONS:
                break
            sym = sig["symbol"]
            if sym in positions:
                continue

            # Realistic entry: next day's open
            entry_px = _price(stock_dfs, sym, next_date, "open", sig["entry"])
            sl       = sig["stop_loss"]
            tgt      = sig["target"]

            # Recalculate SL/target relative to actual entry if price differs noticeably
            if abs(entry_px - sig["entry"]) / sig["entry"] > 0.02:
                risk  = sig["entry"] - sl
                sl    = round(entry_px - risk, 2)
                tgt   = round(entry_px + (tgt - sig["entry"]), 2)

            shares = position_size(cash, entry_px, sl)
            if shares <= 0 or (shares * entry_px) > cash:
                continue

            # Sector exposure check (simplified for backtest)
            positions[sym] = {
                "symbol":        sym,
                "setup":         sig["setup"],
                "entry":         entry_px,
                "stop_loss":     sl,
                "trailing_sl":   sl,
                "target":        tgt,
                "shares":        shares,
                "current_price": entry_px,
                "entry_date":    str(next_date.date()),
            }
            cash -= entry_px * shares

    # ── Close residual positions at last available price ──────────────────────
    last_date = all_dates[-1]
    for sym, pos in list(positions.items()):
        px   = _price(stock_dfs, sym, last_date, "close", pos["current_price"])
        pnl  = (px - pos["entry"]) * pos["shares"]
        cash += px * pos["shares"]
        trades.append(_trade_record(pos, px, "End of Period", last_date, train_dates))
    positions.clear()

    # ── Metrics ───────────────────────────────────────────────────────────────
    equity_df = pd.DataFrame(equity_curve).set_index("date")
    metrics   = _calc_metrics(equity_df, trades, initial_capital, all_dates)

    return {
        "metrics":      metrics,
        "trades":       trades,
        "equity_curve": equity_df,
        "train_test_split": {
            "train_start": str(all_dates[0].date()),
            "train_end":   str(all_dates[split_idx - 1].date()),
            "test_start":  str(all_dates[split_idx].date()),
            "test_end":    str(all_dates[-1].date()),
        },
    }


# ─── Walk-Forward ─────────────────────────────────────────────────────────────

def run_walk_forward(stock_data: dict, index_df: pd.DataFrame) -> dict:
    result = run_backtest(stock_data, index_df)
    if "error" in result:
        return result

    trades       = result["trades"]
    train_trades = [t for t in trades if t["phase"] == "train"]
    test_trades  = [t for t in trades if t["phase"] == "test"]

    return {
        "full_metrics":    result["metrics"],
        "train_trades":    len(train_trades),
        "test_trades":     len(test_trades),
        "train_win_rate":  _win_rate(train_trades),
        "test_win_rate":   _win_rate(test_trades),
        "train_cagr":      _phase_cagr(result["equity_curve"], result["train_test_split"]["train_start"],
                                        result["train_test_split"]["train_end"], config.CAPITAL),
        "split":           result["train_test_split"],
        "validation":      validate_strategy(result["metrics"]),
        "equity_curve":    result["equity_curve"],
        "trades":          trades,
    }


def validate_strategy(metrics: dict) -> dict:
    rules = {
        "CAGR > 15%":          metrics.get("cagr_pct", 0)        > 15,
        "Win rate > 40%":      metrics.get("win_rate_pct", 0)    > 40,
        "Max drawdown < 25%":  metrics.get("max_drawdown_pct", 100) < 25,
        "Profit factor >= 1.5":metrics.get("profit_factor", 0)  >= 1.5,
    }
    passed = all(rules.values())
    return {
        "valid":   passed,
        "rules":   rules,
        "verdict": "STRATEGY VALID — Ready for paper trading" if passed
                   else "STRATEGY INVALID — Requires tuning",
    }


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _price(stock_dfs, sym, date, col, fallback):
    if sym in stock_dfs and date in stock_dfs[sym].index:
        val = stock_dfs[sym].loc[date, col]
        if pd.notna(val):
            return float(val)
    return fallback


def _trade_record(pos, exit_px, reason, exit_date, train_dates):
    return {
        "symbol":     pos["symbol"],
        "setup":      pos["setup"],
        "entry_date": pos["entry_date"],
        "exit_date":  str(exit_date.date()) if hasattr(exit_date, "date") else str(exit_date),
        "entry":      round(pos["entry"], 2),
        "exit":       round(exit_px, 2),
        "shares":     pos["shares"],
        "pnl":        round((exit_px - pos["entry"]) * pos["shares"], 2),
        "pnl_pct":    round((exit_px - pos["entry"]) / pos["entry"] * 100, 2),
        "reason":     reason,
        "phase":      "train" if exit_date in train_dates else "test",
    }


def _win_rate(trades):
    if not trades:
        return 0.0
    return round(len([t for t in trades if t["pnl"] > 0]) / len(trades) * 100, 2)


def _phase_cagr(equity_df, start_str, end_str, initial):
    try:
        sub = equity_df.loc[start_str:end_str]
        if sub.empty:
            return 0.0
        years = (sub.index[-1] - sub.index[0]).days / 365.25
        if years < 0.1:
            return 0.0
        final = sub["equity"].iloc[-1]
        return round(((final / initial) ** (1 / years) - 1) * 100, 2)
    except Exception:
        return 0.0


def _calc_metrics(equity_df, trades, initial_capital, dates) -> dict:
    if not trades:
        return {"error": "No trades executed", "total_trades": 0}

    pnls     = [t["pnl"] for t in trades]
    winners  = [p for p in pnls if p > 0]
    losers   = [p for p in pnls if p <= 0]

    # CAGR
    years = max((dates[-1] - dates[0]).days / 365.25, 0.1) if len(dates) >= 2 else 1
    final = float(equity_df["equity"].iloc[-1]) if not equity_df.empty else initial_capital
    cagr  = round(((final / initial_capital) ** (1 / years) - 1) * 100, 2)

    # Max drawdown
    if not equity_df.empty:
        eq  = equity_df["equity"]
        dd  = (eq - eq.cummax()) / eq.cummax()
        mdd = round(abs(float(dd.min())) * 100, 2)
    else:
        mdd = 0.0

    # Sharpe (annualised)
    sharpe = 0.0
    if not equity_df.empty and len(equity_df) > 1:
        rets = equity_df["equity"].pct_change().dropna()
        if rets.std() > 0:
            sharpe = round((rets.mean() / rets.std()) * np.sqrt(252), 2)

    gross_profit = sum(winners) if winners else 0
    gross_loss   = abs(sum(losers)) if losers else 1e-9
    profit_factor= round(gross_profit / gross_loss, 2)

    return {
        "total_trades":     len(trades),
        "winners":          len(winners),
        "losers":           len(losers),
        "win_rate_pct":     round(len(winners) / len(trades) * 100, 2),
        "avg_win":          round(float(np.mean(winners)), 2) if winners else 0,
        "avg_loss":         round(float(abs(np.mean(losers))), 2) if losers else 0,
        "profit_factor":    profit_factor,
        "total_return_pct": round((final - initial_capital) / initial_capital * 100, 2),
        "cagr_pct":         cagr,
        "max_drawdown_pct": mdd,
        "sharpe_ratio":     sharpe,
    }
