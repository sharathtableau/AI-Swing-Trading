"""
Indicator Engine: all technical indicators, backward-looking only.

Added per Weinstein/PivotBoss guide:
  ma30w       — 30-week MA (150 days), the primary systemic filter
  ma30w_slope — slope of ma30w to confirm Stage 2 (rising MA)
  ema8/ema13  — completes the 8-13-21 EMA momentum stack
  adr5        — 5-period Average Daily Range (ADR) for stop sizing
  atr14       — Average True Range for trailing stops
  avg_mdr3    — 5-period average of the 3-day range (MDR) for PivotBoss targets
"""
import numpy as np
import pandas as pd

import config


def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period, min_periods=period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int = config.RSI_PERIOD) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def avg_volume(series: pd.Series, period: int = config.AVG_VOL_PERIOD) -> pd.Series:
    return series.rolling(window=period, min_periods=period).mean()


def week52_high(series: pd.Series) -> pd.Series:
    return series.rolling(window=252, min_periods=126).max()


def atr(df: pd.DataFrame, period: int = config.ATR_PERIOD) -> pd.Series:
    """Average True Range — used for ATR-based trailing stops."""
    hl = df["high"] - df["low"]
    hc = (df["high"] - df["close"].shift(1)).abs()
    lc = (df["low"]  - df["close"].shift(1)).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.ewm(com=period - 1, min_periods=period).mean()


def avg_mdr(df: pd.DataFrame,
            n: int = config.MDR_DAYS,
            avg_period: int = config.MDR_AVG_PERIOD) -> pd.Series:
    """
    Multiple Day Range (MDR): rolling n-day high-low range, averaged over avg_period.
    Used in PivotBoss target formula: FDL + (Avg MDR × multiplier).
    """
    hhv = df["high"].rolling(window=n, min_periods=n).max()
    llv = df["low"].rolling(window=n, min_periods=n).min()
    return (hhv - llv).rolling(window=avg_period, min_periods=avg_period).mean()


def compute_all(df: pd.DataFrame) -> pd.DataFrame:
    """Add all indicators to a copy of the OHLCV DataFrame."""
    df = df.copy()

    # ── Trend MAs ─────────────────────────────────────────────────────────────
    df["sma50"]      = sma(df["close"], config.SMA_FAST)
    df["sma200"]     = sma(df["close"], config.SMA_SLOW)
    # Weinstein 30-week MA (primary systemic filter)
    df["ma30w"]      = sma(df["close"], config.MA_WEEKLY)
    df["ma30w_slope"]= (
        (df["ma30w"] - df["ma30w"].shift(config.MA_SLOPE_LOOKBACK))
        / df["ma30w"].shift(config.MA_SLOPE_LOOKBACK)
    )

    # ── EMA Stack (8-13-21) ───────────────────────────────────────────────────
    df["ema8"]       = ema(df["close"], config.EMA_FAST)
    df["ema13"]      = ema(df["close"], config.EMA_MID)
    df["ema21"]      = ema(df["close"], config.EMA_TREND)

    # ── Momentum ──────────────────────────────────────────────────────────────
    df["rsi14"]      = rsi(df["close"])

    # ── Volume ────────────────────────────────────────────────────────────────
    df["avg_vol20"]  = avg_volume(df["volume"])

    # ── Range / Volatility ───────────────────────────────────────────────────
    df["high52w"]    = week52_high(df["high"])
    df["daily_range"]= df["high"] - df["low"]
    # ADR: 5-period average of (high - low) — used for ADR stop sizing
    df["adr5"]       = df["daily_range"].rolling(window=config.ADR_PERIOD, min_periods=config.ADR_PERIOD).mean()
    df["atr14"]      = atr(df)
    # MDR: 5-period average of the 3-day high-low range — PivotBoss target engine
    df["avg_mdr3"]   = avg_mdr(df)

    # ── Breakout Support ──────────────────────────────────────────────────────
    # Resistance shifted by 1 to avoid including today's high (no look-ahead)
    df["resistance"] = df["high"].shift(1).rolling(
        window=config.BREAKOUT_LOOKBACK, min_periods=config.BREAKOUT_LOOKBACK
    ).max()

    return df
