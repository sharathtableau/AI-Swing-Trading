"""
Pattern Detection — fully aligned with Weinstein + PivotBoss guide.

Stage Analysis (Weinstein):
  detect_stage()          — classifies each bar as Stage 1/2/3/4
  detect_stage2()         — boolean: execution zone (price > rising 30w MA)
  detect_stage1()         — boolean: accumulation/basing zone

Entry Patterns:
  detect_breakout()       — close > resistance on 2× volume
  detect_vcp()            — Volatility Contraction Pattern (supply exhaustion)
  detect_linear_base()    — extended 6-week+ base ("Big Base = Big Move")
  detect_base_formation() — short 3-week base
  detect_volume_decay()   — declining volume inside base (supply exhaustion signal)
  detect_ema_crossover()  — 8 > 13 > 21 EMA momentum stack (entry confirmation)
  detect_weinstein_pullback() — pullback to rising 30w MA after Stage 2 breakout
  detect_3dr_expansion()  — 3-day range exceeds Avg MDR (volatility expanding)
  detect_ema_pullback()   — price near rising EMA21 (short-term mean-reversion)
  detect_relative_strength() — stock outperforms index (Leader over Laggard)

Sector:
  rank_sectors()          — ranks sectors by 63-day return (sector rotation)
"""
import numpy as np
import pandas as pd

import config


# ─── Stan Weinstein Stage Analysis ───────────────────────────────────────────

def detect_stage(df: pd.DataFrame) -> pd.Series:
    """
    Classify each bar into Stage 1/2/3/4 using 30-week MA and its slope.

    Stage 1 — Accumulation: price near flat MA (±5%), MA slope flat
    Stage 2 — Advancing:    price above rising MA          ← Execution Zone
    Stage 3 — Distribution: price near flattening MA, was Stage 2
    Stage 4 — Declining:    price below falling MA
    """
    close = df["close"]
    ma    = df.get("ma30w", pd.Series(np.nan, index=df.index))
    slope = df.get("ma30w_slope", pd.Series(0.0, index=df.index))

    above     = close > ma
    below     = close < ma
    ma_rising = slope > config.MA_SLOPE_MIN
    ma_flat   = slope.abs() <= config.MA_SLOPE_MIN
    ma_fall   = slope < -config.MA_SLOPE_MIN
    near_ma   = ((close - ma).abs() / ma.replace(0, np.nan)) <= 0.05

    stage = pd.Series(0, index=df.index, dtype=int)
    stage[above & ma_rising]          = 2   # Advancing — buy zone
    stage[below & ma_fall]            = 4   # Declining — stay cash
    stage[near_ma & ma_flat & ~above] = 1   # Accumulation
    stage[above & ma_flat]            = 3   # Distribution topping
    return stage.fillna(0)


def detect_stage2(df: pd.DataFrame) -> pd.Series:
    """True when price is above a clearly rising 30-week MA (Stage 2 execution zone)."""
    above_ma  = df["close"] > df.get("ma30w", pd.Series(np.nan, index=df.index))
    ma_rising = df.get("ma30w_slope", pd.Series(0.0, index=df.index)) > config.MA_SLOPE_MIN
    return (above_ma & ma_rising).fillna(False)


def detect_stage1(df: pd.DataFrame) -> pd.Series:
    """True when price is basing near a flat 30-week MA (Stage 1 accumulation)."""
    ma      = df.get("ma30w", pd.Series(np.nan, index=df.index))
    near_ma = ((df["close"] - ma).abs() / ma.replace(0, np.nan)) <= 0.05
    ma_flat = df.get("ma30w_slope", pd.Series(0.0, index=df.index)).abs() <= config.MA_SLOPE_MIN
    return (near_ma & ma_flat).fillna(False)


# ─── Entry Patterns ───────────────────────────────────────────────────────────

def detect_breakout(df: pd.DataFrame) -> pd.Series:
    """Close exceeds prior resistance on 2× average volume (mandatory conviction)."""
    return (
        df["close"].gt(df["resistance"]) &
        df["volume"].gt(config.VOLUME_MULTIPLIER * df["avg_vol20"])
    ).fillna(False)


def detect_vcp(df: pd.DataFrame) -> pd.Series:
    """
    Volatility Contraction Pattern: 3 successive narrowing daily ranges.
    Represents institutional absorption of supply before breakout.
    """
    r = df["daily_range"]
    return ((r < r.shift(1)) & (r.shift(1) < r.shift(2))).fillna(False)


def detect_volume_decay(df: pd.DataFrame) -> pd.Series:
    """
    Volume declining over the base period — supply exhaustion signal.
    Recent 5-day avg volume < base-period avg volume.
    """
    days = config.BASE_FORMATION_WEEKS * 5
    recent_vol = df["volume"].rolling(window=5, min_periods=5).mean()
    base_vol   = df["volume"].rolling(window=days, min_periods=days).mean()
    return recent_vol.lt(base_vol).fillna(False)


def detect_base_formation(df: pd.DataFrame) -> pd.Series:
    """Short base: sideways >= BASE_FORMATION_WEEKS, price range <= 20%."""
    days      = config.BASE_FORMATION_WEEKS * 5
    high_roll = df["close"].rolling(window=days, min_periods=days).max()
    low_roll  = df["close"].rolling(window=days, min_periods=days).min()
    range_pct = (high_roll - low_roll) / low_roll.replace(0, np.nan)
    return (range_pct <= config.BASE_FORMATION_RANGE * 2).fillna(False)


def detect_linear_base(df: pd.DataFrame) -> pd.Series:
    """
    Extended linear base >= LINEAR_BASE_WEEKS (6+ weeks), range <= 15%.
    "Big Base = Big Move" — multi-month consolidation builds stored energy.
    """
    days      = config.LINEAR_BASE_WEEKS * 5
    high_roll = df["close"].rolling(window=days, min_periods=days).max()
    low_roll  = df["close"].rolling(window=days, min_periods=days).min()
    range_pct = (high_roll - low_roll) / low_roll.replace(0, np.nan)
    return (range_pct <= 0.15).fillna(False)


def detect_ema_crossover(df: pd.DataFrame) -> pd.Series:
    """
    8-13-21 EMA bullish momentum stack: EMA8 > EMA13 > EMA21, EMA8 still rising.
    Used as secondary momentum confirmation on breakout or Weinstein pullback.
    """
    return (
        df["ema8"].gt(df["ema13"]) &
        df["ema13"].gt(df["ema21"]) &
        df["ema8"].gt(df["ema8"].shift(1))  # EMA8 still climbing
    ).fillna(False)


def detect_weinstein_pullback(df: pd.DataFrame) -> pd.Series:
    """
    Weinstein Pullback: in Stage 2, price pulls back within 3% of rising 30-week MA.
    Entry opportunity when the initial breakout is missed.
    Confirmed further by EMA crossover (detect_ema_crossover).
    """
    in_stage2 = detect_stage2(df)
    ma        = df.get("ma30w", pd.Series(np.nan, index=df.index))
    near_ma   = ((df["close"] - ma).abs() / ma.replace(0, np.nan)) <= 0.03
    return (in_stage2 & near_ma).fillna(False)


def detect_3dr_expansion(df: pd.DataFrame) -> pd.Series:
    """
    3DR Expansion: current 3-day range exceeds its 5-period average (Avg MDR).
    Signals the start of a volatility expansion window — optimal entry timing.
    """
    hhv3  = df["high"].rolling(window=config.MDR_DAYS, min_periods=config.MDR_DAYS).max()
    llv3  = df["low"].rolling(window=config.MDR_DAYS, min_periods=config.MDR_DAYS).min()
    dr3   = hhv3 - llv3
    return dr3.gt(df.get("avg_mdr3", pd.Series(np.nan, index=df.index))).fillna(False)


def detect_ema_pullback(df: pd.DataFrame) -> pd.Series:
    """Price above rising EMA21 and pulling back within 3% of it."""
    ema_rising = df["ema21"] > df["ema21"].shift(3)
    above_ema  = df["close"] > df["ema21"]
    near_ema   = ((df["close"] - df["ema21"]).abs() / df["ema21"]) <= 0.03
    return (above_ema & ema_rising & near_ema).fillna(False)


def detect_relative_strength(df: pd.DataFrame, index_df: pd.DataFrame,
                              lookback: int = 63) -> pd.Series:
    """
    Leader over Laggard: stock's 63-day return exceeds index return.
    Mandatory filter per the guide — never trade laggards.
    """
    stock_ret = df["close"].pct_change(lookback)
    idx_ret   = index_df["close"].reindex(df.index).pct_change(lookback)
    return stock_ret.gt(idx_ret).fillna(False)


# ─── Sector Rotation ──────────────────────────────────────────────────────────

def rank_sectors(stock_data: dict, lookback: int = 63) -> dict:
    """Returns {sector: rank} where rank=1 is strongest (sector rotation filter)."""
    sector_returns: dict = {}
    for symbol, df in stock_data.items():
        sector = config.SECTOR_MAP.get(symbol, "Unknown")
        if len(df) < lookback:
            continue
        ret = (df["close"].iloc[-1] - df["close"].iloc[-lookback]) / df["close"].iloc[-lookback]
        sector_returns.setdefault(sector, []).append(float(ret))

    sector_avg = {s: float(np.mean(v)) for s, v in sector_returns.items()}
    ranked = sorted(sector_avg.items(), key=lambda x: x[1], reverse=True)
    return {s: rank for rank, (s, _) in enumerate(ranked, 1)}


# ─── Combined ─────────────────────────────────────────────────────────────────

def compute_all_patterns(df: pd.DataFrame, index_df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["stage"]               = detect_stage(df)
    df["stage2"]              = detect_stage2(df)
    df["stage1"]              = detect_stage1(df)
    df["breakout"]            = detect_breakout(df)
    df["vcp"]                 = detect_vcp(df)
    df["volume_decay"]        = detect_volume_decay(df)
    df["base_formation"]      = detect_base_formation(df)
    df["linear_base"]         = detect_linear_base(df)
    df["ema_crossover"]       = detect_ema_crossover(df)
    df["weinstein_pullback"]  = detect_weinstein_pullback(df)
    df["expansion_3dr"]       = detect_3dr_expansion(df)
    df["ema_pullback"]        = detect_ema_pullback(df)
    df["relative_strength"]   = detect_relative_strength(df, index_df)
    return df
