"""
Risk Engine — Weinstein + PivotBoss guide compliant.

Position Sizing:
  (Account Equity × 0.01) / Stop Distance = Position Size   [1% Rule]

Stop Loss:
  ADR Stop: entry − 50% of 5-period ADR          (primary — per guide)
  Swing Low: below recent swing low / EMA21      (fallback)

Trailing Stops:
  ATR-based: current_price − (ATR_TRAIL_MULT × ATR14)       [Stage 2 advance]
  Percentage: simple % trail                                 [fallback]

Scaling (3-5-7 Rule):
  Scale out 1/3 of shares at +3%, +5%, +7% gains.

Free Trade Technique:
  Once the Primary Target (Normal Lite) is reached, move SL to break-even.
  The remaining position runs risk-free on a trailing stop.
"""
import config


# ─── Position Sizing ──────────────────────────────────────────────────────────

def position_size(capital: float, entry: float, stop_loss: float) -> int:
    """
    Shares = (Capital × RISK_PER_TRADE) / (Entry − Stop Loss)
    Capped at MAX_CAPITAL_PER_TRADE × capital.
    """
    risk_per_share = entry - stop_loss
    if risk_per_share <= 0 or entry <= 0:
        return 0
    shares_risk = int((capital * config.RISK_PER_TRADE) / risk_per_share)
    shares_cap  = int((capital * config.MAX_CAPITAL_PER_TRADE) / entry)
    return min(shares_risk, shares_cap)


# ─── Trade Validation ─────────────────────────────────────────────────────────

def validate_trade(signal: dict, available_cash: float) -> tuple:
    """Returns (is_valid: bool, reason: str)."""
    entry     = signal["entry"]
    stop_loss = signal["stop_loss"]
    target    = signal.get("primary_target", signal.get("target", 0))
    shares    = signal.get("position_size", 0)

    risk = entry - stop_loss
    if risk <= 0:
        return False, "Stop loss at or above entry"

    rr = (target - entry) / risk
    if rr < config.MIN_RISK_REWARD:
        return False, f"R:R {rr:.2f} below minimum {config.MIN_RISK_REWARD}"

    sl_pct = risk / entry
    if sl_pct > config.MAX_SL_PERCENT:
        return False, f"SL {sl_pct:.1%} exceeds max {config.MAX_SL_PERCENT:.0%}"

    if shares > 0 and (shares * entry) > available_cash:
        return False, "Insufficient cash"

    return True, "OK"


# ─── Trailing Stops ───────────────────────────────────────────────────────────

def atr_trailing_stop(current_price: float, atr14: float,
                      current_sl: float,
                      multiplier: float = config.ATR_TRAIL_MULT) -> float:
    """
    ATR-based trailing stop: current_price − (multiplier × ATR).
    Used during Stage 2 advance to lock in unrealised gains.
    Never lowers the stop.
    """
    if atr14 > 0:
        new_sl = round(current_price - multiplier * atr14, 2)
        return max(current_sl, new_sl)
    return current_sl


def trailing_stop(current_price: float, entry: float, current_sl: float,
                  trigger_gain: float = 0.05) -> float:
    """
    Percentage-based trailing stop (fallback when ATR is unavailable).
    Activates once position is up >= trigger_gain %; trails at trigger_gain below price.
    Minimum: break-even (entry).  Never lowers the stop.
    """
    if (current_price - entry) / entry >= trigger_gain:
        trail  = current_price * (1 - trigger_gain)
        new_sl = max(current_sl, entry, trail)
        return round(new_sl, 2)
    return current_sl


# ─── 3-5-7 Scaling Rule ───────────────────────────────────────────────────────

def scaling_exits(current_price: float, entry: float,
                  total_shares: int, scaled_out: int) -> dict:
    """
    Returns how many shares to sell at this price point under the 3-5-7 Rule.

    scaled_out: shares already sold in prior scale-outs.
    Returns {"shares_to_sell": int, "level_hit": str | None}.
    """
    gain_pct   = (current_price - entry) / entry
    third      = total_shares // 3
    levels_hit = []

    for level in config.SCALE_LEVELS:
        if gain_pct >= level:
            levels_hit.append(level)

    levels_already_sold = min(scaled_out // max(third, 1), len(config.SCALE_LEVELS))
    new_levels = len(levels_hit) - levels_already_sold

    if new_levels > 0 and third > 0:
        return {
            "shares_to_sell": third * new_levels,
            "level_hit": f"+{levels_hit[levels_already_sold]:.0%}",
        }
    return {"shares_to_sell": 0, "level_hit": None}


# ─── Free Trade Technique ────────────────────────────────────────────────────

def free_trade_stop(entry: float, current_sl: float) -> float:
    """
    Called when the Primary Target (Normal Lite) is reached.
    Moves SL to break-even — position now carries zero initial risk.
    Never lowers the existing stop.
    """
    return max(current_sl, entry)
