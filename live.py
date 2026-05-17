"""
Live Execution Engine: daily workflow orchestrator.

Default mode: dry_run=True (signals only, no portfolio mutation).
Pass --execute to record actual positions.

Workflow:
  1. Fetch/update OHLCV data
  2. Market regime filter
  3. Compute indicators + patterns
  4. Generate & rank signals
  5. Validate risk rules
  6. Update portfolio (dry run or live)
  7. Check open position exits
  8. Persist output JSON + send alerts
"""
import json
import os
from datetime import datetime
from typing import Dict, List

import config
from data import load_all_stocks, load_index
from indicators import compute_all
from patterns import compute_all_patterns, rank_sectors
from portfolio import (
    can_add_position, close_position, get_portfolio_summary,
    load_portfolio, open_position, save_portfolio, update_prices,
)
from regime import get_regime, is_tradeable
from risk import position_size, validate_trade, trailing_stop
from signals import generate_signals

OUTPUT_DIR = "outputs"


def daily_run(dry_run: bool = True) -> dict:
    today = datetime.today().strftime("%Y-%m-%d")
    print(f"\n{'='*60}")
    print(f"  Swing Trading AI — {today}  {'[DRY RUN]' if dry_run else '[LIVE]'}")
    print(f"{'='*60}")

    # ── 1. Data ───────────────────────────────────────────────────────────────
    print("\n[1/8] Fetching market data...")
    index_df   = load_index(refresh=True)
    stock_data = load_all_stocks(refresh=True)
    print(f"      {len(stock_data)} stocks loaded.")

    # ── 2. Regime ─────────────────────────────────────────────────────────────
    print("\n[2/8] Checking market regime...")
    regime_info = get_regime(index_df)
    d = regime_info["details"]
    print(f"      Regime: {regime_info['regime']} | "
          f"Nifty: {d.get('index_close', '?')} | "
          f"SMA200: {d.get('sma200', '?')} | "
          f"RSI: {d.get('rsi14', '?')}")

    portfolio = load_portfolio()

    if not is_tradeable(regime_info):
        print("      ⚠  Not bullish — skipping signal scan.")
        output = _build_output(today, regime_info, portfolio, [], [])
        _persist(output, today)
        return output

    # ── 3. Sector ranking ─────────────────────────────────────────────────────
    print("\n[3/8] Ranking sectors...")
    sector_ranks = rank_sectors(stock_data)
    top_sectors  = set(s for s, r in sector_ranks.items() if r <= 5)
    print(f"      Top sectors: {', '.join(sorted(top_sectors))}")

    # ── 4-5. Pattern detection + signals ──────────────────────────────────────
    print("\n[4/8] Scanning for signals...")
    raw_signals: List[dict] = []
    for symbol, df in stock_data.items():
        df_ind = compute_all(df)
        df_pat = compute_all_patterns(df_ind, index_df)
        sigs   = generate_signals(symbol, df_pat)
        for s in sigs:
            s["sector"] = config.SECTOR_MAP.get(symbol, "Unknown")
            s["sector_rank"] = sector_ranks.get(s["sector"], 99)
        raw_signals.extend(sigs)
    print(f"      {len(raw_signals)} raw signals found.")

    # ── 6. Risk validation ────────────────────────────────────────────────────
    print("\n[5/8] Applying risk rules...")
    valid_signals = _filter_signals(raw_signals, portfolio)
    print(f"      {len(valid_signals)} signals passed risk validation.")

    # ── 7. Update portfolio ───────────────────────────────────────────────────
    print("\n[6/8] Updating portfolio...")
    if not dry_run:
        portfolio = _execute_entries(portfolio, valid_signals, today)
        save_portfolio(portfolio)
        print(f"      {len(valid_signals)} trade(s) recorded.")
    else:
        print(f"      [DRY RUN] Would open {len(valid_signals)} position(s).")

    # ── 8. Exit management ───────────────────────────────────────────────────
    print("\n[7/8] Checking open position exits...")
    current_prices = {
        sym: float(df.iloc[-1]["close"])
        for sym, df in stock_data.items()
        if sym in portfolio["positions"]
    }
    portfolio = update_prices(portfolio, current_prices)
    exits = _process_exits(portfolio, current_prices, today, dry_run)
    if not dry_run and exits:
        save_portfolio(portfolio)
    print(f"      {len(exits)} position(s) exited.")

    # ── 9. Output ─────────────────────────────────────────────────────────────
    print("\n[8/8] Generating output...")
    output = _build_output(today, regime_info, portfolio, valid_signals, exits)
    _persist(output, today)
    _send_alerts(output)
    print(f"\n✓ Scan complete — {len(valid_signals)} new signal(s), {len(exits)} exit(s).")
    return output


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _filter_signals(raw: List[dict], portfolio: dict) -> List[dict]:
    """Apply risk/portfolio rules and sort by confidence + sector rank."""
    out = []
    for sig in raw:
        if sig["symbol"] in portfolio["positions"]:
            continue
        shares = position_size(portfolio["cash"], sig["entry"], sig["stop_loss"])
        if shares <= 0:
            continue
        sig["position_size"] = shares
        sig["trade_value"]   = round(shares * sig["entry"], 2)
        ok, _ = validate_trade(sig, portfolio["cash"])
        if not ok:
            continue
        ok, _ = can_add_position(portfolio, sig["symbol"], sig["entry"], shares)
        if not ok:
            continue
        out.append(sig)

    conf_order = {"High": 0, "Medium": 1, "Low": 2}
    out.sort(key=lambda s: (conf_order.get(s["confidence"], 3), s.get("sector_rank", 99)))
    return out


def _execute_entries(portfolio: dict, signals: List[dict], today: str) -> dict:
    for sig in signals:
        if len(portfolio["positions"]) >= config.MAX_POSITIONS:
            break
        shares = sig.get("position_size", 0)
        ok, _ = can_add_position(portfolio, sig["symbol"], sig["entry"], shares)
        if ok:
            portfolio = open_position(
                portfolio, sig["symbol"], sig["entry"],
                sig["stop_loss"], sig["target"], shares,
                sig["setup"], today,
            )
    return portfolio


def _process_exits(portfolio: dict, prices: Dict[str, float],
                   today: str, dry_run: bool) -> List[dict]:
    exits = []
    for symbol, pos in list(portfolio["positions"].items()):
        px     = prices.get(symbol, pos.get("current_price", pos["entry"]))
        reason = None
        if px <= pos.get("trailing_sl", pos["stop_loss"]):
            reason = "Stop Loss"
        elif px >= pos["target"]:
            reason = "Target Hit"

        if reason:
            exits.append({
                "symbol":      symbol,
                "exit_price":  round(px, 2),
                "reason":      reason,
                "entry":       pos["entry"],
                "pnl":         round((px - pos["entry"]) * pos["shares"], 2),
                "pnl_pct":     round((px - pos["entry"]) / pos["entry"] * 100, 2),
            })
            if not dry_run:
                close_position(portfolio, symbol, px, reason, today)
    return exits


def _build_output(today, regime_info, portfolio, signals, exits) -> dict:
    summary = get_portfolio_summary(portfolio)
    return {
        "date":           today,
        "market_regime":  regime_info["regime"],
        "regime_details": regime_info["details"],
        "portfolio": {
            "capital":        config.CAPITAL,
            "total_value":    summary["total_value"],
            "cash":           summary["cash"],
            "positions":      summary["open_positions"],
            "unrealized_pnl": summary["unrealized_pnl"],
            "realized_pnl":   summary["realized_pnl"],
            "total_return_pct": summary["total_return_pct"],
        },
        "trades": signals,
        "exits":  exits,
    }


def _persist(output: dict, date: str) -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, f"signals_{date}.json")
    with open(path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"      Output → {path}")


def _send_alerts(output: dict) -> None:
    if config.EMAIL_ENABLED:
        _email_alert(output)
    if config.TELEGRAM_ENABLED:
        _telegram_alert(output)


def _email_alert(output: dict) -> None:
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    msg           = MIMEMultipart()
    msg["From"]   = config.EMAIL_SENDER
    msg["To"]     = config.EMAIL_RECIPIENT
    msg["Subject"] = f"Swing Signals {output['date']} [{output['market_regime']}]"
    msg.attach(MIMEText(json.dumps(output, indent=2, default=str), "plain"))
    try:
        with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as s:
            s.starttls()
            s.login(config.EMAIL_SENDER, config.EMAIL_PASSWORD)
            s.sendmail(config.EMAIL_SENDER, config.EMAIL_RECIPIENT, msg.as_string())
        print("      Email alert sent.")
    except Exception as e:
        print(f"      [WARN] Email failed: {e}")


def _telegram_alert(output: dict) -> None:
    import urllib.request

    lines = [f"*Swing Trading — {output['date']}*",
             f"Regime: {output['market_regime']}", ""]
    for t in output.get("trades", []):
        lines.append(f"• {t['symbol']} ({t['setup']})  "
                     f"Entry={t['entry']}  SL={t['stop_loss']}  T={t['target']}  "
                     f"R:R={t['risk_reward']}  [{t['confidence']}]")
    if not output.get("trades"):
        lines.append("No new signals today.")

    data = json.dumps({
        "chat_id": config.TELEGRAM_CHAT_ID,
        "text": "\n".join(lines),
        "parse_mode": "Markdown",
    }).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage",
        data=data, headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=10)
        print("      Telegram alert sent.")
    except Exception as e:
        print(f"      [WARN] Telegram failed: {e}")
