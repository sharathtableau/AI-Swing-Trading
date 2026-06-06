"""
Signal Engine — Weinstein + PivotBoss + Minervini + Wyckoff.

Pipeline alignment (2026-06-02): gates are now PER-SETUP so that the
differentiated high-conviction setups can actually trade:

  * Structural floor (all setups): relative strength, not Stage 3/4.
  * Momentum screen (RSI>55, above SMA50/200): applied to TREND setups only
    (Base Breakout, VCP, Weinstein Pullback, EMA Pullback) — these need an
    established uptrend.
  * Wyckoff Spring is a REVERSAL at support: it bypasses the momentum screen
    (a spring is a shakeout below support at low RSI) and uses its own grade,
    since the trend grade rubric structurally rejects setups made at lows.
  * Breakouts (Base Breakout, VCP Breakout) use a TIGHT PIVOT STOP just under
    resistance instead of a distant swing low, so they pass the 2R / max-SL
    validation that previously discarded ~75% of them.
"""
import pandas as pd
from typing import Dict, List, Tuple

import config


# ─── Stop Loss Calculations ───────────────────────────────────────────────────

def _adr_stop(row: pd.Series, entry: float) -> float:
    adr = float(row.get("adr5", 0) or 0)
    if adr > 0:
        return round(entry - config.ADR_STOP_PCT * adr, 2)
    return 0.0


def _swing_low_stop(df: pd.DataFrame, idx: int, entry: float,
                    lookback: int = 15) -> float:
    start     = max(0, idx - lookback)
    swing_low = float(df["low"].iloc[start:idx].min())
    ema21     = float(df["ema21"].iloc[idx])
    sl_raw    = max(swing_low, ema21) * 0.99
    return round(min(sl_raw, entry * 0.98), 2)


def _best_stop(row: pd.Series, df: pd.DataFrame, idx: int, entry: float) -> float:
    adr_sl = _adr_stop(row, entry)
    sw_sl  = _swing_low_stop(df, idx, entry)
    if adr_sl > 0 and adr_sl < entry:
        return min(adr_sl, sw_sl)
    return sw_sl


def _pivot_stop(row: pd.Series, entry: float) -> float:
    """Tight breakout stop: just under the breakout pivot (resistance).
    Capped so the stop is always below entry. This is the textbook breakout
    stop — risk is defined by the pivot you broke, not a distant swing low."""
    res = float(row.get("resistance", entry) or entry)
    sl  = min(res * 0.97, entry * 0.98)
    return round(sl, 2)


# ─── Target Calculations (PivotBoss ADR Method) ──────────────────────────────

def _pivotboss_targets(row: pd.Series, entry: float) -> Tuple[float, float]:
    mdr   = float(row.get("avg_mdr3", 0) or 0)
    fdl   = float(row.get("low", entry * 0.98))

    if mdr > 0:
        primary   = round(fdl + mdr * config.MDR_NORMAL_LITE_MULT, 2)
        secondary = round(fdl + mdr * config.MDR_NORMAL_MULT, 2)
        primary   = max(primary,   round(entry * 1.03, 2))
        secondary = max(secondary, round(entry * 1.06, 2))
        return primary, secondary

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


# ─── Screeners ────────────────────────────────────────────────────────────────

def _passes_base_screen(row: pd.Series) -> bool:
    """Structural floor for ANY setup: relative strength, not topping/declining."""
    if int(row.get("stage", 0)) in (3, 4):
        return False
    return bool(row.get("relative_strength", False))


def _passes_screener(row: pd.Series) -> bool:
    """Momentum/trend screen — required only for trend-continuation setups."""
    if not _passes_base_screen(row):
        return False
    return (
        pd.notna(row.get("sma50"))  and row["close"] > row["sma50"]  and
        pd.notna(row.get("sma200")) and row["close"] > row["sma200"] and
        pd.notna(row.get("rsi14"))  and row["rsi14"] > config.MIN_RSI_SCREEN
    )


def _passes_strict_trend(df: pd.DataFrame, idx: int) -> bool:
    """STRICT trend gate — mirrors the live app's score() Stage-2 requirement so
    the scan table never contradicts the Analyse tab.

    The app marks a name AVOID when its Layer-1 trend is weak (Layer-1 < 20).
    That happens for anything the app does NOT classify as a clean
    "Stage 2 — Advancing": price above the 30-week MA AND that MA rising
    > 0.3% over the prior ~20 bars. The scan's own stage flag uses a far looser
    slope (config.MA_SLOPE_MIN = 0.03%), so it was passing barely-rising
    "1→2 Transitioning" names (e.g. BSE) that the app rejects. Enforcing the
    app's exact 0.3%-over-20-bars test here closes that contradiction.

    This is deliberately conservative: it can drop a marginal setup the app
    might still rate WATCHLIST, but it will never show a setup the app AVOIDs.
    """
    if "ma30w" not in df.columns:
        return False
    ma    = df["ma30w"].iloc[idx]
    close = df["close"].iloc[idx]
    if pd.isna(ma) or pd.isna(close) or close <= ma:
        return False
    lb = min(20, idx)
    if lb <= 0:
        return False
    pm = df["ma30w"].iloc[idx - lb]
    if pd.isna(pm) or pm <= 0:
        return False
    slope_med = (ma - pm) / pm * 100          # % change in MA over ~20 bars
    return slope_med > 0.3                     # app's "Stage 2 — Advancing" cut


# ─── Confidence Score ─────────────────────────────────────────────────────────

def _confidence(row: pd.Series) -> str:
    score = 0
    if row.get("linear_base",    False): score += 2
    if row.get("base_formation", False): score += 1
    if row.get("volume_decay",   False): score += 1
    if row.get("ema_crossover",  False): score += 1
    if row.get("expansion_3dr",  False): score += 1
    if row.get("high52w",  0) > 0 and row["close"] / row["high52w"] >= config.NEAR_52W_HIGH_THRESHOLD:
        score += 1
    return "High" if score >= 3 else ("Medium" if score >= 1 else "Low")


# ─── A / A+ Setup Grade (confluence selectivity) ─────────────────────────────

def _grade_setup(row: pd.Series) -> Tuple[str, int, str]:
    """Trend-setup grade. Rewards bases, contraction, RS, proximity to highs."""
    score, reasons = 0, []

    if row.get("linear_base", False):
        score += 2; reasons.append("big base")
    elif row.get("base_formation", False):
        score += 1; reasons.append("base")

    if row.get("vcp", False):
        score += 2; reasons.append("VCP coil")
    if row.get("volume_decay", False):
        score += 1; reasons.append("vol dry-up")
    if row.get("ema_crossover", False):
        score += 1; reasons.append("EMA stack")
    if row.get("expansion_3dr", False):
        score += 1; reasons.append("range expansion")

    rsm = float(row.get("rs_margin", 0) or 0)
    if rsm >= config.RS_STRONG_MARGIN:
        score += 2; reasons.append("strong RS")
    elif rsm > 0:
        score += 1; reasons.append("RS leader")

    h52 = float(row.get("high52w", 0) or 0)
    if h52 > 0 and row["close"] / h52 >= config.NEAR_52W_HIGH_THRESHOLD:
        score += 1; reasons.append("near 52w high")

    if score >= config.GRADE_APLUS_MIN:
        grade = "A+"
    elif score >= config.GRADE_A_MIN:
        grade = "A"
    else:
        grade = ""
    return grade, score, ", ".join(reasons)


def _grade_spring(row: pd.Series) -> Tuple[str, int, str]:
    """Reversal grade for a Wyckoff Spring. A valid spring is itself a
    canonical high-conviction setup, so it floors at grade 'A'; strong relative
    strength or volume dry-up promotes it toward 'A+'."""
    score, reasons = 2, ["wyckoff spring"]
    rsm = float(row.get("rs_margin", 0) or 0)
    if rsm >= config.RS_STRONG_MARGIN:
        score += 2; reasons.append("strong RS")
    elif rsm > 0:
        score += 1; reasons.append("RS leader")
    if row.get("volume_decay", False):
        score += 1; reasons.append("vol dry-up")
    if row.get("linear_base", False) or row.get("base_formation", False):
        score += 1; reasons.append("range support")

    grade = "A+" if score >= config.GRADE_APLUS_MIN else "A"
    return grade, score, ", ".join(reasons)


# ─── Signal Builder ───────────────────────────────────────────────────────────

def _build_signal(symbol: str, setup: str, date, entry: float,
                  sl: float, primary_tgt: float, secondary_tgt: float,
                  conf: str, row: pd.Series,
                  grade: str = "", grade_score: int = 0,
                  grade_reasons: str = "") -> dict:
    risk = entry - sl
    rr   = round((primary_tgt - entry) / risk, 2) if risk > 0 else 0
    return {
        "symbol":           symbol,
        "setup":            setup,
        "date":             str(date.date()) if hasattr(date, "date") else str(date),
        "entry":            round(entry, 2),
        "stop_loss":        sl,
        "primary_target":   primary_tgt,
        "secondary_target": secondary_tgt,
        "target":           primary_tgt,
        "risk_reward":      rr,
        "confidence":       conf,
        "grade":            grade,
        "grade_score":      grade_score,
        "grade_reasons":    grade_reasons,
        "stage":            int(row.get("stage", 2)),
        "adr5":             round(float(row.get("adr5", 0) or 0), 2),
        "avg_mdr3":         round(float(row.get("avg_mdr3", 0) or 0), 2),
    }


# ─── Main ─────────────────────────────────────────────────────────────────────

def generate_signals(symbol: str, df: pd.DataFrame,
                     date: pd.Timestamp = None,
                     allowed_setups: set = None) -> List[Dict]:
    if date is None:
        date = df.index[-1]
    if date not in df.index:
        return []

    idx = df.index.get_loc(date)
    if idx < config.MA_WEEKLY:
        return []

    row   = df.loc[date]
    entry = float(row["close"])

    # Structural floor — applies to every setup.
    if not _passes_base_screen(row):
        return []

    momentum_ok             = _passes_screener(row)
    conf                    = _confidence(row)
    grade, gscore, greasons = _grade_setup(row)

    sl                 = _best_stop(row, df, idx, entry)
    primary, secondary = _pivotboss_targets(row, entry)
    if primary <= entry:
        primary   = _rr_target(entry, sl, config.MIN_RISK_REWARD)
        secondary = _rr_target(entry, sl, config.MIN_RISK_REWARD + 1)

    signals = []

    # ── Trend setups: require the momentum screen, an A/A+ trend grade, AND
    #    the app's strict clean-Stage-2 gate (so scan never contradicts Analyse) ──
    if momentum_ok and grade and _passes_strict_trend(df, idx):

        # 1. Base Breakout — tight pivot stop so it survives 2R / max-SL.
        if row.get("base_breakout", False):
            bb_sl  = _pivot_stop(row, entry)
            bb_tgt = _rr_target(entry, bb_sl, config.MIN_RISK_REWARD)
            bb_sec = _rr_target(entry, bb_sl, config.MIN_RISK_REWARD + 1)
            ok, _  = _valid_trade(entry, bb_sl, bb_tgt)
            if ok:
                signals.append(_build_signal(
                    symbol, "Base Breakout", date, entry, bb_sl, bb_tgt, bb_sec,
                    conf, row, grade, gscore, greasons
                ))

        # 2. VCP Breakout — tight pivot stop, 3R objective.
        if row.get("vcp", False) and row.get("base_breakout", False):
            vcp_sl  = _pivot_stop(row, entry)
            vcp_tgt = _rr_target(entry, vcp_sl, 3.0)
            ok, _   = _valid_trade(entry, vcp_sl, vcp_tgt)
            if ok:
                signals.append(_build_signal(
                    symbol, "VCP Breakout", date, entry, vcp_sl,
                    vcp_tgt, _rr_target(entry, vcp_sl, 4.0),
                    conf, row, grade, gscore, greasons
                ))

        # 4. Weinstein Pullback — pullback to rising 30w MA + EMA stack.
        if row.get("weinstein_pullback", False) and row.get("ema_crossover", False):
            ma30w  = float(row.get("ma30w", sl))
            wb_sl  = round(ma30w * 0.98, 2)
            wb_tgt = primary if primary > entry else _rr_target(entry, wb_sl)
            ok, _  = _valid_trade(entry, wb_sl, wb_tgt)
            if ok:
                signals.append(_build_signal(
                    symbol, "Weinstein Pullback", date, entry, wb_sl,
                    wb_tgt, secondary, conf, row, grade, gscore, greasons
                ))

        # 5. EMA Pullback — Stage-2 confirmed mean-reversion near rising EMA21.
        if row.get("ema_pullback", False) and row.get("stage2", False):
            ema_sl  = round(float(row["ema21"]) * 0.97, 2)
            ema_tgt = primary if primary > entry else _rr_target(entry, ema_sl)
            ok, _   = _valid_trade(entry, ema_sl, ema_tgt)
            if ok:
                signals.append(_build_signal(
                    symbol, "EMA Pullback", date, entry, ema_sl,
                    ema_tgt, secondary, conf, row, grade, gscore, greasons
                ))

    # ── Wyckoff Spring: reversal — bypasses momentum screen, own grade ──
    if row.get("wyckoff_spring", False):
        sgrade, sgs, sgr = _grade_spring(row)
        spring_low = float(row.get("low", entry * 0.98))
        sp_sl  = round(min(spring_low * 0.99, entry * 0.98), 2)
        sp_tgt = _rr_target(entry, sp_sl, config.MIN_RISK_REWARD)
        sp_sec = _rr_target(entry, sp_sl, config.MIN_RISK_REWARD + 1)
        ok, _  = _valid_trade(entry, sp_sl, sp_tgt)
        if ok:
            signals.append(_build_signal(
                symbol, "Wyckoff Spring", date, entry, sp_sl,
                sp_tgt, sp_sec, conf, row, sgrade, sgs, sgr
            ))

    # Optional setup isolation (experiments): keep only whitelisted setups
    # BEFORE the per-symbol dedup, so a kept setup is never crowded out by a
    # higher-R:R signal we're trying to exclude.
    if allowed_setups is not None:
        signals = [s for s in signals if s["setup"] in allowed_setups]

    seen: Dict[str, dict] = {}
    for sig in signals:
        key = sig["symbol"]
        if key not in seen or sig["risk_reward"] > seen[key]["risk_reward"]:
            seen[key] = sig
    return list(seen.values())
