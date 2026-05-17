"""
Market Regime Filter — Stan Weinstein Stage Analysis applied to the index.

Primary filter: 30-week MA (MA30w) with slope check.
  Stage 2 Bullish → index close > rising MA30w          ← only state that allows entries
  Neutral         → index close > MA30w but MA flat/ambiguous
  Stage 4 Bearish → index close < falling MA30w         ← capital preservation mode

Secondary confirmation: RSI(14) > 50 adds momentum weight.
"""
import pandas as pd

import config
from indicators import compute_all


def get_regime(index_df: pd.DataFrame) -> dict:
    df = compute_all(index_df)
    if df.empty or len(df) < config.MA_WEEKLY:
        return {"regime": "Unknown", "details": {}}

    row = df.iloc[-1]

    close       = float(row["close"])
    ma30w       = float(row["ma30w"])    if pd.notna(row.get("ma30w"))       else None
    slope       = float(row["ma30w_slope"]) if pd.notna(row.get("ma30w_slope")) else None
    rsi14       = float(row["rsi14"])    if pd.notna(row.get("rsi14"))       else None
    sma200      = float(row["sma200"])   if pd.notna(row.get("sma200"))      else None

    above_ma30w = (ma30w is not None) and (close > ma30w)
    ma_rising   = (slope is not None) and (slope > config.MA_SLOPE_MIN)
    ma_falling  = (slope is not None) and (slope < -config.MA_SLOPE_MIN)
    rsi_ok      = (rsi14 is not None) and (rsi14 > config.REGIME_RSI_THRESHOLD)

    # Stage 2: price above clearly rising 30w MA → execution zone
    if above_ma30w and ma_rising and rsi_ok:
        regime = "Bullish"
    elif above_ma30w and ma_rising:
        regime = "Neutral"          # MA rising but RSI weak — be selective
    elif not above_ma30w and ma_falling:
        regime = "Bearish"          # Stage 4 — stay cash
    else:
        regime = "Neutral"          # Stage 1/3 transition — observe

    return {
        "regime": regime,
        "details": {
            "index_close":  round(close, 2),
            "ma30w":        round(ma30w,  2) if ma30w  is not None else None,
            "ma30w_slope":  round(slope,  5) if slope  is not None else None,
            "ma_rising":    ma_rising,
            "sma200":       round(sma200, 2) if sma200 is not None else None,
            "rsi14":        round(rsi14,  2) if rsi14  is not None else None,
            "rsi_healthy":  rsi_ok,
            "above_ma30w":  above_ma30w,
        },
    }


def get_regime_on_date(index_df_with_indicators: pd.DataFrame,
                       date: pd.Timestamp) -> str:
    """Fast per-date regime lookup used inside the backtester (no re-computation)."""
    if date not in index_df_with_indicators.index:
        return "Unknown"
    row = index_df_with_indicators.loc[date]

    above   = pd.notna(row.get("ma30w"))       and row["close"] > row["ma30w"]
    rising  = pd.notna(row.get("ma30w_slope")) and row["ma30w_slope"] > config.MA_SLOPE_MIN
    falling = pd.notna(row.get("ma30w_slope")) and row["ma30w_slope"] < -config.MA_SLOPE_MIN
    rsi_ok  = pd.notna(row.get("rsi14"))       and row["rsi14"] > config.REGIME_RSI_THRESHOLD

    if above and rising and rsi_ok:
        return "Bullish"
    if above and rising:
        return "Neutral"
    if not above and falling:
        return "Bearish"
    return "Neutral"


def is_tradeable(regime_info: dict) -> bool:
    return regime_info.get("regime") == "Bullish"
