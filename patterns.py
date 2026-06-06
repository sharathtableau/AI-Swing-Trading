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
    Volatility Contraction Pattern (Minervini), implemented faithfully.

    A real VCP is NOT three narrower daily candles. It is a SERIES of
    progressively shallower price pullbacks as supply is absorbed, with
    volume drying up, ending in a tight coil near the highs ready to break.

    We model it as three stacked contraction legs of VCP_LEG days each:

        leg1 (oldest) → leg2 (middle) → leg3 (most recent)

    Conditions, all required:
      • Each leg's high-low range contracts: range(leg3) < range(leg2) < range(leg1)
      • Higher lows: the recent leg's low sits above the prior leg's low
        (demand stepping in higher — absorption, not breakdown)
      • Final leg is genuinely tight: range(leg3)/price <= VCP_FINAL_TIGHT
      • Volume drying up: recent-leg avg volume <= VCP_VOL_DRYUP × base avg volume
      • Coiled near the top: close >= VCP_NEAR_TOP × high of the whole base
    """
    leg  = config.VCP_LEG
    hi   = df["high"]
    lo   = df["low"]

    def _range(shift_legs: int) -> pd.Series:
        s = shift_legs * leg
        h = hi.shift(s).rolling(leg, min_periods=leg).max()
        l = lo.shift(s).rolling(leg, min_periods=leg).min()
        return h - l

    r3 = _range(0)   # most recent leg
    r2 = _range(1)   # middle leg
    r1 = _range(2)   # oldest leg

    low3 = lo.shift(0).rolling(leg, min_periods=leg).min()
    low2 = lo.shift(leg).rolling(leg, min_periods=leg).min()

    contracting = (r3 < r2) & (r2 < r1)
    higher_lows = low3 > low2
    final_tight = (r3 / df["close"].replace(0, np.nan)) <= config.VCP_FINAL_TIGHT

    base_days  = leg * 3
    recent_vol = df["volume"].rolling(leg, min_periods=leg).mean()
    base_vol   = df["volume"].rolling(base_days, min_periods=base_days).mean()
    vol_dryup  = recent_vol <= (config.VCP_VOL_DRYUP * base_vol)

    base_high  = hi.rolling(base_days, min_periods=base_days).max()
    near_top   = df["close"] >= (config.VCP_NEAR_TOP * base_high)

    return (contracting & higher_lows & final_tight & vol_dryup & near_top).fillna(False)


def detect_wyckoff_spring(df: pd.DataFrame) -> pd.Series:
    """
    Wyckoff Spring: a shakeout that briefly breaks below the support of a
    trading range and immediately reclaims it on a bullish bar, trapping
    sellers right before the markup. One of the highest-quality A+ entries.

    Conditions:
      • Support = lowest low of the prior SPRING_SUPPORT_LOOKBACK days
      • Today's low pierces that support (false breakdown)
      • The undercut is shallow (<= SPRING_MAX_UNDERCUT below support) — a
        shakeout, not a genuine breakdown
      • Close reclaims back above support on a bullish (close > open) bar
    """
    support   = df["low"].shift(1).rolling(
        config.SPRING_SUPPORT_LOOKBACK, min_periods=config.SPRING_SUPPORT_LOOKBACK
    ).min()
    broke     = df["low"] < support
    shallow   = df["low"] >= support * (1 - config.SPRING_MAX_UNDERCUT)
    reclaimed = df["close"] > support
    bullish   = df["close"] > df.get("open", df["close"].shift(1))
    return (broke & shallow & reclaimed & bullish).fillna(False)


def detect_base_breakout(df: pd.DataFrame) -> pd.Series:
    """
    Weinstein Stage-1 → Stage-2 base breakout (the textbook A+ buy).

    Unlike a naked 20-day-high breakout, this requires that price was
    consolidating in a base, is above a flat-to-rising 30-week MA, and is
    breaking out FRESH (not already extended) on conviction volume.

    Conditions:
      • A base (short or linear) existed within the last BREAKOUT_BASE_WINDOW days
      • Close clears prior resistance (top of the base)
      • Breakout is fresh: close <= resistance × (1 + BREAKOUT_MAX_EXTENSION)
      • Volume >= VOLUME_MULTIPLIER × average (institutional conviction)
      • Above the 30-week MA, with the MA not falling (Stage 1-turning-2 / Stage 2)
    """
    base_flag = (df.get("base_formation", False) | df.get("linear_base", False))
    base_recent = base_flag.shift(1).rolling(
        config.BREAKOUT_BASE_WINDOW, min_periods=1
    ).max().fillna(0).astype(bool)

    breakout   = df["close"] > df["resistance"]
    fresh      = df["close"] <= df["resistance"] * (1 + config.BREAKOUT_MAX_EXTENSION)
    vol_ok     = df["volume"] > config.VOLUME_MULTIPLIER * df["avg_vol20"]

    ma         = df.get("ma30w", pd.Series(np.nan, index=df.index))
    slope      = df.get("ma30w_slope", pd.Series(0.0, index=df.index))
    above_ma   = df["close"] > ma
    ma_ok      = slope >= -config.MA_SLOPE_MIN     # flat-to-rising (not Stage 4)

    return (base_recent & breakout & fresh & vol_ok & above_ma & ma_ok).fillna(False)


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
    """
    Short base: a TIGHT sideways consolidation over BASE_FORMATION_WEEKS,
    measured on true intrabar high/low range (<= BASE_FORMATION_RANGE, 10%).
    Previously used close-only range at 2x the band, which flagged ~97% of all
    bars on large caps — that detected nothing and made the A+ grade useless.
    """
    days      = config.BASE_FORMATION_WEEKS * 5
    high_roll = df["high"].rolling(window=days, min_periods=days).max()
    low_roll  = df["low"].rolling(window=days, min_periods=days).min()
    range_pct = (high_roll - low_roll) / low_roll.replace(0, np.nan)
    return (range_pct <= config.BASE_FORMATION_RANGE).fillna(False)


def detect_linear_base(df: pd.DataFrame) -> pd.Series:
    """
    Extended linear base >= LINEAR_BASE_WEEKS (6+ weeks), true high/low range
    <= 12%. "Big Base = Big Move" — multi-month consolidation stores energy.
    Tightened from 15% close-only to 12% high/low for the same reason as above.
    """
    days      = config.LINEAR_BASE_WEEKS * 5
    high_roll = df["high"].rolling(window=days, min_periods=days).max()
    low_roll  = df["low"].rolling(window=days, min_periods=days).min()
    range_pct = (high_roll - low_roll) / low_roll.replace(0, np.nan)
    return (range_pct <= 0.12).fillna(False)


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


def relative_strength_margin(df: pd.DataFrame, index_df: pd.DataFrame,
                             lookback: int = 63) -> pd.Series:
    """
    Numeric RS: stock return minus index return over the window. Used to grade
    *how strong* a leader is (an A+ wants a clear margin, not a hairline win).
    """
    stock_ret = df["close"].pct_change(lookback)
    idx_ret   = index_df["close"].reindex(df.index).pct_change(lookback)
    return (stock_ret - idx_ret).fillna(0.0)


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
    # Base flags first — base_breakout depends on them
    df["base_formation"]      = detect_base_formation(df)
    df["linear_base"]         = detect_linear_base(df)
    df["volume_decay"]        = detect_volume_decay(df)
    df["breakout"]            = detect_breakout(df)
    df["base_breakout"]       = detect_base_breakout(df)
    df["vcp"]                 = detect_vcp(df)
    df["wyckoff_spring"]      = detect_wyckoff_spring(df)
    df["ema_crossover"]       = detect_ema_crossover(df)
    df["weinstein_pullback"]  = detect_weinstein_pullback(df)
    df["expansion_3dr"]       = detect_3dr_expansion(df)
    df["ema_pullback"]        = detect_ema_pullback(df)
    df["relative_strength"]   = detect_relative_strength(df, index_df)
    df["rs_margin"]           = relative_strength_margin(df, index_df)
    return df
