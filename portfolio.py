"""
Portfolio Manager — tracks positions, cash, P&L, and sector exposure.
State persisted to portfolio_state.json between sessions.

Added per Weinstein/PivotBoss guide:
  scale_out_position()  — 3-5-7 Rule: partial exits at 3%, 5%, 7% gain
  free_trade_stop()     — move SL to break-even once Primary Target is reached
  update_prices()       — uses ATR trailing stop when ATR data is available
"""
import json
import os
from datetime import datetime
from typing import Dict, Tuple

import config
from risk import (
    atr_trailing_stop, free_trade_stop, position_size,
    scaling_exits, trailing_stop,
)

PORTFOLIO_FILE = "portfolio_state.json"


# ─── State I/O ────────────────────────────────────────────────────────────────

def _default_state() -> dict:
    return {
        "capital":       config.CAPITAL,
        "cash":          config.CAPITAL,
        "positions":     {},
        "closed_trades": [],
        "created_at":    datetime.now().isoformat(),
    }


def load_portfolio() -> dict:
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE) as f:
            return json.load(f)
    return _default_state()


def save_portfolio(state: dict) -> None:
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)


# ─── Queries ──────────────────────────────────────────────────────────────────

def _sector_exposure(state: dict) -> Dict[str, float]:
    exposure: Dict[str, float] = {}
    for symbol, pos in state["positions"].items():
        sector = config.SECTOR_MAP.get(symbol, "Unknown")
        exposure[sector] = exposure.get(sector, 0.0) + pos["shares"] * pos["current_price"]
    return exposure


def _portfolio_value(state: dict) -> float:
    invested = sum(p["shares"] * p["current_price"] for p in state["positions"].values())
    return state["cash"] + invested


def can_add_position(state: dict, symbol: str, entry: float,
                     shares: int) -> Tuple[bool, str]:
    if len(state["positions"]) >= config.MAX_POSITIONS:
        return False, f"Max {config.MAX_POSITIONS} positions reached"
    if symbol in state["positions"]:
        return False, f"Already holding {symbol}"

    trade_value = entry * shares
    if trade_value > state["cash"]:
        return False, "Insufficient cash"

    total  = _portfolio_value(state)
    sector = config.SECTOR_MAP.get(symbol, "Unknown")
    current_sector = _sector_exposure(state).get(sector, 0.0)
    if total > 0 and (current_sector + trade_value) / total > config.MAX_SECTOR_EXPOSURE:
        return False, f"Sector {sector} would exceed {config.MAX_SECTOR_EXPOSURE:.0%} limit"

    return True, "OK"


# ─── Open / Close / Scale ─────────────────────────────────────────────────────

def open_position(state: dict, symbol: str, entry: float, stop_loss: float,
                  target: float, shares: int, setup: str, date: str,
                  secondary_target: float = 0.0) -> dict:
    state["positions"][symbol] = {
        "symbol":           symbol,
        "setup":            setup,
        "entry":            entry,
        "stop_loss":        stop_loss,
        "trailing_sl":      stop_loss,
        "target":           target,            # Primary Target (Normal Lite)
        "secondary_target": secondary_target,  # Normal target
        "shares":           shares,
        "total_shares":     shares,            # original count for scaling math
        "scaled_out":       0,                 # shares already sold via 3-5-7
        "current_price":    entry,
        "open_date":        date,
        "free_trade":       False,             # True once Primary Target hit
    }
    state["cash"] -= entry * shares
    return state


def close_position(state: dict, symbol: str, exit_price: float,
                   reason: str, date: str) -> dict:
    if symbol not in state["positions"]:
        return state
    pos = state["positions"].pop(symbol)
    pnl = (exit_price - pos["entry"]) * pos["shares"]
    state["cash"] += exit_price * pos["shares"]
    state["closed_trades"].append({
        **pos,
        "exit_price":  round(exit_price, 2),
        "exit_date":   date,
        "exit_reason": reason,
        "pnl":         round(pnl, 2),
        "pnl_pct":     round((exit_price - pos["entry"]) / pos["entry"] * 100, 2),
    })
    return state


def scale_out_position(state: dict, symbol: str, current_price: float,
                       date: str) -> Tuple[dict, dict]:
    """
    3-5-7 Rule: sell 1/3 of original position at each gain threshold.
    Returns (updated_state, scale_event | None).
    """
    if symbol not in state["positions"]:
        return state, {}

    pos    = state["positions"][symbol]
    result = scaling_exits(
        current_price, pos["entry"],
        pos["total_shares"], pos["scaled_out"]
    )
    shares_to_sell = result["shares_to_sell"]
    if shares_to_sell <= 0 or shares_to_sell > pos["shares"]:
        return state, {}

    pnl = (current_price - pos["entry"]) * shares_to_sell
    state["cash"]       += current_price * shares_to_sell
    pos["shares"]       -= shares_to_sell
    pos["scaled_out"]   += shares_to_sell

    # Free Trade Technique: once Primary Target hit, move SL to break-even
    if current_price >= pos["target"] and not pos["free_trade"]:
        pos["trailing_sl"] = free_trade_stop(pos["entry"], pos["trailing_sl"])
        pos["free_trade"]  = True

    event = {
        "symbol":        symbol,
        "action":        "SCALE_OUT",
        "level":         result["level_hit"],
        "shares_sold":   shares_to_sell,
        "price":         round(current_price, 2),
        "pnl":           round(pnl, 2),
        "shares_remaining": pos["shares"],
        "free_trade":    pos["free_trade"],
        "date":          date,
    }
    return state, event


# ─── Price Update + Trailing Stops ───────────────────────────────────────────

def update_prices(state: dict, prices: Dict[str, float],
                  atr_data: Dict[str, float] = None) -> dict:
    """
    Refresh current prices and advance trailing stops.
    Uses ATR-based trailing when atr_data is provided; falls back to % trail.
    """
    atr_data = atr_data or {}
    for symbol, pos in state["positions"].items():
        if symbol not in prices:
            continue
        price = prices[symbol]
        pos["current_price"] = price

        atr14 = atr_data.get(symbol, 0.0)
        if atr14 > 0:
            pos["trailing_sl"] = atr_trailing_stop(price, atr14, pos["trailing_sl"])
        else:
            pos["trailing_sl"] = trailing_stop(price, pos["entry"], pos["trailing_sl"])

    return state


# ─── Summary ─────────────────────────────────────────────────────────────────

def get_portfolio_summary(state: dict) -> dict:
    invested   = sum(p["shares"] * p["current_price"] for p in state["positions"].values())
    total_val  = state["cash"] + invested
    realized   = sum(t["pnl"] for t in state["closed_trades"])
    unrealized = sum(
        (p["current_price"] - p["entry"]) * p["shares"]
        for p in state["positions"].values()
    )
    return {
        "total_value":      round(total_val, 2),
        "cash":             round(state["cash"], 2),
        "invested":         round(invested, 2),
        "open_positions":   len(state["positions"]),
        "closed_trades":    len(state["closed_trades"]),
        "realized_pnl":     round(realized, 2),
        "unrealized_pnl":   round(unrealized, 2),
        "total_return_pct": round((total_val - state["capital"]) / state["capital"] * 100, 2),
    }
