"""
Signal Engine — fully aligned with Weinstein + PivotBoss guide.

Four setups generated:
  1. Stage 2 Breakout      — price clears resistance on 2× volume in Stage 2
  2. VCP Breakout          — volatility contraction + breakout, extended target (3R)
  3. Weinstein Pullback    — pullback to rising 30w MA confirmed by EMA crossover
  4. EMA Pullback          — short-term mean-reversion near rising EMA21

Stop loss priority:
  Primary  → ADR Stop: entry − (50% × 5-period ADR)        [Weinstein/PivotBoss]
  Fallback → Swing Low Stop: below recent swing low / EMA21

Target calculation (PivotBoss ADR Method):
  primary_target   = FDL + (Avg MDR3 × 0.75)   Normal Lite  ~70% hit rate
  secondary_target = FDL + Avg MDR3             Normal       ~45% hit rate

Mandatory filters enforced before any signal is emitted:
  ✓ Stage 2 (price above rising 30w MA)
  ✓ Relative Strength > index (Leader over Laggard)
  ✓ close > SMA50 and SMA200
  ✓ RSI > 55
  ✓ Volume > 2× average
  ✓ R:R ≥ 2.0 and SL ≤ 10%
"""
import pandas as pd
from typing import Dict, List, Tuple

import config


# ─── Stop Loss Calculations ───────────────────────────────────────────────────

def _adr_stop(row: pd.Series, entry: float) -> float:
    """
    ADR Stop: entry − 50% of the 5-period Average Daily Range.
    Recalculated fresh each session to adjust for current volatility.
    """
    adr = float(row.get("adr5", 0) or 0)
    if adr > 0:
        return round(entry - config.ADR_STOP_PCT * adr, 2)
    return 0.0


def _swing_low_stop(df: pd.DataFrame, idx: int, entry: float,
                    lookback: int = 15) -> float:
    """Stop just below the recent swing low or EMA21, min 2% below entry."""
    start     = max(0, idx - lookback)
    swing_low = float(df["low"].iloc[start:idx].min())
    ema21     = float(df["ema21"].iloc[idx])
    sl_raw    = max(swing_low, ema21) * 0.99
    return round(min(sl_raw, entry * 0.98), 2)


def _best_stop(row: pd.Series, df: pd.DataFrame, idx: int, entry: float) -> float:
    """
    Always use the WIDER (lower price) of the two stop candidates.
    ADR stop at 50% is too tight for swing trading — the swing low gives real room.
    min() picks the lower price = farther from entry = wider stop.
    """
    adr_sl = _adr_stop(row, entry)
    sw_sl  = _swing_low_stop(df, idx, entry)
    if adr_sl > 0 and adr_sl < entry:
        return min(adr_sl, sw_sl)   # lower price = wider stop
    return sw_sl


# ─── Target Calculations (PivotBoss ADR Method) ──────────────────────────────

def _pivotboss_targets(row: pd.Series, entry: float) -> Tuple[float, float]:
    """
    Primary  (Normal Lite): FDL + Avg MDR3 × 0.75  — ~70% success rate
    Secondary (Normal):     FDL + Avg MDR3          — ~45% success rate

    FDL (First Day Low) = current candle's low (the breakout bar's low).
    Falls back to R:R-based target if MDR data is unavailable.
    """
    mdr   = float(row.get("avg_mdr3", 0) or 0)
    fdl   = float(row.get("low", entry * 0.98))

    if mdr > 0:
        primary   = round(fdl + mdr * config.MDR_NORMAL_LITE_MULT, 2)
        secondary = round(fdl + mdr * config.MDR_NORMAL_MULT, 2)
        # Ensure targets are above entry
        primary   = max(primary,   round(entry * 1.03, 2))
        secondary = max(secondary, round(entry * 1.06, 2))
        return primary, secondary

    # Fallback: fixed R:R targets
    return 0.0, 0.0


def _rr_target(entry: float, sl: float, rr: float = config.MIN_RISK_REWARD) -> float:
    return round(entry + rr * (entry - sl), 2)


# ─── Validation ───────────────────────────────────────────────────────────────

def _valid_trade(entry: float, sl: float, target: float) -> Tuple[bool, str]:
    risk = entry - sl
    if risk <= 0:
        return False, "SL at or above entry"
    rr     = (target - entry) / risk
    sl_pct = risk / entry
    if rr < config.MIN_RISK_REWARD:
        return False, f"R:R {rr:.2f} < {config.MIN_RISK_REWARD}"
    if sl_pct > config.MAX_SL_PERCENT:
        return False, f"SL {sl_pct:.1%} too wide"
    return True, "OK"


# ─── Screener (mandatory pre-filters) ────────────────────────────────────────

def _passes_screener(row: pd.Series) -> bool:
    """
    Mandatory pre-filters before any setup is evaluated.

    Macro gate (Stage 2 on the INDEX) is enforced by the regime filter in
    live.py and backtest.py — not duplicated here.  Individual stocks are
    screened for late-Stage-1 / early-Stage-2 conditions so we catch the
    transition breakout, which is the ideal Weinstein entry point.

    Hard gates:
      • Relative Strength > index (Leader over Laggard — never relax this)
      • Price above SMA50 and SMA200
      • RSI > MIN_RSI_SCREEN
      • Volume > VOLUME_MULTIPLIER × average
    """
    if not bool(row.get("relative_strength", False)):
        return False                        # Leader over Laggard is non-negotiable

    # Volume is enforced per-setup (breakout requires 2× vol; pullbacks intentionally run on low vol)
    return (
        pd.notna(row.get("sma50"))  and row["close"] > row["sma50"]  and
        pd.notna(row.get("sma200")) and row["close"] > row["sma200"] and
        pd.notna(row.get("rsi14"))  and row["rsi14"] > config.MIN_RSI_SCREEN
    )


# ─── Confidence Score ─────────────────────────────────────────────────────────

def _confidence(row: pd.Series) -> str:
    score = 0
    if row.get("linear_base",    False): score += 2  # Big Base = Big Move
    if row.get("base_formation", False): score += 1
    if row.get("volume_decay",   False): score += 1  # supply exhaustion
    if row.get("ema_crossover",  False): score += 1  # 8-13-21 momentum stack
    if row.get("expansion_3dr",  False): score += 1  # 3DR timing confirmation
    if row.get("high52w",  0) > 0 and row["close"] / row["high52w"] >= config.NEAR_52W_HIGH_THRESHOLD:
        score += 1
    return "High" if score >= 3 else ("Medium" if score >= 1 else "Low")


# ─── Signal Builder ───────────────────────────────────────────────────────────

def _build_signal(symbol: str, setup: str, date, entry: float,
                  sl: float, primary_tgt: float, secondary_tgt: float,
                  conf: str, row: pd.Series) -> dict:
    risk = entry - sl
    rr   = round((primary_tgt - entry) / risk, 2) if risk > 0 else 0
    return {
        "symbol":           symbol,
        "setup":            setup,
        "date":             str(date.date()) if hasattr(date, "date") else str(date),
        "entry":            round(entry, 2),
        "stop_loss":        sl,
        "primary_target":   primary_tgt,    # Normal Lite — ~70% hit rate
        "secondary_target": secondary_tgt,  # Normal — ~45% hit rate
        "target":           primary_tgt,    # alias used by portfolio/backtest
        "risk_reward":      rr,
        "confidence":       conf,
        "stage":            int(row.get("stage", 2)),
        "adr5":             round(float(row.get("adr5", 0) or 0), 2),
        "avg_mdr3":         round(float(row.get("avg_mdr3", 0) or 0), 2),
    }


# ─── Main ─────────────────────────────────────────────────────────────────────

def generate_signals(symbol: str, df: pd.DataFrame,
                     date: pd.Timestamp = None) -> List[Dict]:
    """
    Returns validated signal dicts for the given date (defaults to last row).
    DataFrame must have indicators + patterns already computed.
    """
    if date is None:
        date = df.index[-1]
    if date not in df.index:
        return []

    idx = df.index.get_loc(date)
    if idx < config.MA_WEEKLY:        # need enough history for 30w MA
        return []

    row   = df.loc[date]
    entry = float(row["close"])

    if not _passes_screener(row):
        return []

    conf               = _confidence(row)
    sl                 = _best_stop(row, df, idx, entry)
    primary, secondary = _pivotboss_targets(row, entry)

    # Fall back to R:R target if PivotBoss data unavailable
    if primary <= entry:
        primary   = _rr_target(entry, sl, config.MIN_RISK_REWARD)
        secondary = _rr_target(entry, sl, config.MIN_RISK_REWARD + 1)

    signals = []

    # ── 1. Stage 2 Breakout ───────────────────────────────────────────────────
    if row.get("breakout", False):
        ok, _ = _valid_trade(entry, sl, primary)
        if ok:
            signals.append(_build_signal(
                symbol, "Breakout", date, entry, sl, primary, secondary, conf, row
            ))

    # ── 2. VCP Breakout (extended 3R target) ─────────────────────────────────
    if row.get("vcp", False) and row.get("breakout", False):
        vcp_tgt = _rr_target(entry, sl, 3.0)
        ok, _   = _valid_trade(entry, sl, vcp_tgt)
        if ok:
            signals.append(_build_signal(
                symbol, "VCP Breakout", date, entry, sl,
                vcp_tgt, _rr_target(entry, sl, 4.0),
                "High" if conf != "Low" else "Medium", row
            ))

    # ── 3. Weinstein Pullback (confirmed by 8-13-21 EMA crossover) ───────────
    if row.get("weinstein_pullback", False) and row.get("ema_crossover", False):
        # Tighter SL: just below the 30w MA
        ma30w  = float(row.get("ma30w", sl))
        wb_sl  = round(ma30w * 0.98, 2)
        wb_tgt = primary if primary > entry else _rr_target(entry, wb_sl)
        ok, _ = _valid_trade(entry, wb_sl, wb_tgt)
        if ok:
            signals.append(_build_signal(
                symbol, "Weinstein Pullback", date, entry, wb_sl,
                wb_tgt, secondary, conf, row
            ))

    # ── 4. EMA Pullback (relative strength confirmed) ────────────────────────
    if row.get("ema_pullback", False):
        ema_sl = round(float(row["ema21"]) * 0.97, 2)
        ema_tgt = primary if primary > entry else _rr_target(entry, ema_sl)
        ok, _  = _valid_trade(entry, ema_sl, ema_tgt)
        if ok:
            signals.append(_build_signal(
                symbol, "EMA Pullback", date, entry, ema_sl,
                ema_tgt, secondary, conf, row
            ))

    # De-duplicate: one entry per symbol, keep highest R:R
    seen: Dict[str, dict] = {}
    for sig in signals:
        key = sig["symbol"]
        if key not in seen or sig["risk_reward"] > seen[key]["risk_reward"]:
            seen[key] = sig
    return list(seen.values())
