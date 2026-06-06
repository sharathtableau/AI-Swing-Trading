#!/usr/bin/env python3
import sys
# Force UTF-8 on Windows terminals so box-drawing characters print correctly
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
"""
Swing Trading AI Agent — CLI Entry Point

Commands:
  backtest   Run historical backtesting with optional walk-forward validation
  live       Run daily market scan (dry-run by default; --execute to record trades)
  screen     Run screener and print current signals
  portfolio  Show portfolio status and open positions

Examples:
  python main.py backtest --walk-forward
  python main.py backtest --stocks 20
  python main.py live
  python main.py live --execute
  python main.py screen
  python main.py portfolio
"""
import argparse
import json
import sys
from datetime import datetime


# ─── Command Handlers ─────────────────────────────────────────────────────────

def cmd_backtest(args):
    from data import load_all_stocks, load_index
    from backtest import run_backtest, run_walk_forward, validate_strategy

    print("Loading data...")
    index_df   = load_index()
    all_stocks = load_all_stocks()

    if not all_stocks:
        print("ERROR: No stock data available. Run with internet access to download.")
        sys.exit(1)

    if args.stocks:
        keys       = list(all_stocks.keys())[: args.stocks]
        stock_data = {k: all_stocks[k] for k in keys}
    else:
        stock_data = all_stocks

    print(f"Running backtest on {len(stock_data)} stocks...\n")

    if args.walk_forward:
        result = run_walk_forward(stock_data, index_df)
        if "error" in result:
            print(f"ERROR: {result['error']}")
            sys.exit(1)
        _print_walk_forward(result)
    else:
        result     = run_backtest(stock_data, index_df)
        if "error" in result:
            print(f"ERROR: {result['error']}")
            sys.exit(1)
        metrics    = result["metrics"]
        validation = validate_strategy(metrics)
        _print_metrics(metrics)
        _print_validation(validation)
        _print_sample_trades(result["trades"])
        _print_breakdowns(result["trades"])

    _save_report(result)


def cmd_live(args):
    from live import daily_run

    dry_run = not args.execute
    if not dry_run:
        confirm = input("\nLIVE MODE: trades will be recorded. Type YES to confirm: ")
        if confirm.strip() != "YES":
            print("Aborted.")
            sys.exit(0)

    result = daily_run(dry_run=dry_run)
    _print_output_summary(result)


def cmd_screen(args):
    from data import load_all_stocks, load_index
    from indicators import compute_all
    from patterns import compute_all_patterns, rank_sectors
    from regime import get_regime, is_tradeable
    from signals import generate_signals
    import config

    print("Running screener...")
    index_df   = load_index()
    regime_info= get_regime(index_df)
    print(f"Regime: {regime_info['regime']}\n")

    if not is_tradeable(regime_info):
        print("Market not bullish — screener paused.")
        return

    stock_data   = load_all_stocks()
    sector_ranks = rank_sectors(stock_data)
    all_signals  = []

    for symbol, df in stock_data.items():
        df_ind = compute_all(df)
        df_pat = compute_all_patterns(df_ind, index_df)
        sigs   = generate_signals(symbol, df_pat)
        for s in sigs:
            s["sector"]      = config.SECTOR_MAP.get(symbol, "Unknown")
            s["sector_rank"] = sector_ranks.get(s["sector"], 99)
        all_signals.extend(sigs)

    if not all_signals:
        print("No signals today.")
        return

    conf_order = {"High": 0, "Medium": 1, "Low": 2}
    all_signals.sort(key=lambda s: (conf_order.get(s["confidence"], 3), s.get("sector_rank", 99)))

    print(f"{'Symbol':<15} {'Setup':<15} {'Entry':>8} {'SL':>8} {'Target':>8} "
          f"{'R:R':>5} {'Conf':<8} {'Sector'}")
    print("-" * 85)
    for s in all_signals:
        print(f"{s['symbol']:<15} {s['setup']:<15} {s['entry']:>8.2f} "
              f"{s['stop_loss']:>8.2f} {s['target']:>8.2f} "
              f"{s['risk_reward']:>5.1f} {s['confidence']:<8} {s.get('sector','')}")
    print(f"\nTotal: {len(all_signals)} signal(s)")


def cmd_portfolio(args):
    from portfolio import load_portfolio, get_portfolio_summary

    state   = load_portfolio()
    summary = get_portfolio_summary(state)

    print("\n═══ Portfolio Status ══════════════════════════════════")
    for k, v in summary.items():
        print(f"  {k:<22} {v}")

    if state["positions"]:
        print("\n  Open Positions:")
        print(f"  {'Symbol':<15} {'Setup':<15} {'Entry':>8} {'Current':>8} {'PnL%':>7} {'SL':>8}")
        print("  " + "-" * 65)
        for sym, pos in state["positions"].items():
            pnl_pct = (pos["current_price"] - pos["entry"]) / pos["entry"] * 100
            print(f"  {sym:<15} {pos['setup']:<15} {pos['entry']:>8.2f} "
                  f"{pos['current_price']:>8.2f} {pnl_pct:>+7.1f}% "
                  f"{pos.get('trailing_sl', pos['stop_loss']):>8.2f}")

    if state["closed_trades"]:
        recent = state["closed_trades"][-5:]
        print(f"\n  Last {len(recent)} Closed Trades:")
        print(f"  {'Symbol':<12} {'Exit Reason':<14} {'PnL%':>7} {'PnL (₹)':>12}")
        print("  " + "-" * 50)
        for t in recent:
            print(f"  {t['symbol']:<12} {t.get('exit_reason','?'):<14} "
                  f"{t['pnl_pct']:>+7.1f}% {t['pnl']:>12,.2f}")


# ─── Print Helpers ────────────────────────────────────────────────────────────

def _print_metrics(m: dict):
    print("═══ Backtest Metrics ══════════════════════════════════")
    labels = {
        "total_trades":     "Total Trades",
        "winners":          "Winners",
        "losers":           "Losers",
        "win_rate_pct":     "Win Rate (%)",
        "avg_win":          "Avg Win (₹)",
        "avg_loss":         "Avg Loss (₹)",
        "profit_factor":    "Profit Factor",
        "total_return_pct": "Total Return (%)",
        "cagr_pct":         "CAGR (%)",
        "max_drawdown_pct": "Max Drawdown (%)",
        "sharpe_ratio":     "Sharpe Ratio",
    }
    for key, label in labels.items():
        val = m.get(key, "N/A")
        print(f"  {label:<24} {val}")
    print()


def _print_validation(v: dict):
    print("═══ Strategy Validation ═══════════════════════════════")
    for rule, passed in v["rules"].items():
        mark = "✓" if passed else "✗"
        print(f"  [{mark}] {rule}")
    print(f"\n  Verdict: {v['verdict']}\n")


def _print_sample_trades(trades: list, n: int = 10):
    if not trades:
        return
    print(f"═══ Sample Trades (last {min(n, len(trades))}) ═══════════════════════")
    print(f"  {'Symbol':<12} {'Setup':<15} {'Entry→Exit':^22} {'PnL%':>7} {'Reason'}")
    print("  " + "-" * 72)
    for t in trades[-n:]:
        sign = "+" if t["pnl_pct"] >= 0 else ""
        dates = f"{t['entry_date']} → {t['exit_date']}"
        print(f"  {t['symbol']:<12} {t['setup']:<15} {dates:^22} "
              f"{sign}{t['pnl_pct']:>6.1f}%  {t['reason']}")
    print()


def _print_setup_breakdown(trades: list, title: str):
    from backtest import setup_breakdown
    rows = setup_breakdown(trades)
    if not rows:
        return
    print(f"═══ {title} ═══")
    print(f"  {'Setup':<18}{'Trades':>7}{'Win%':>7}{'AvgWin':>9}{'AvgLoss':>9}"
          f"{'Payoff':>8}{'PF':>7}{'TotalPnL':>12}{'Exp/Trd':>10}")
    print("  " + "-" * 96)
    for r in rows:
        print(f"  {r['setup']:<18}{r['trades']:>7}{r['win_rate_pct']:>6.1f}%"
              f"{r['avg_win']:>9,.0f}{r['avg_loss']:>9,.0f}{r['payoff']:>8.2f}"
              f"{r['profit_factor']:>7.2f}{r['total_pnl']:>12,.0f}{r['expectancy']:>10,.0f}")
    earners  = [r["setup"] for r in rows if r["total_pnl"] > 0]
    bleeders = [r["setup"] for r in rows if r["total_pnl"] < 0]
    print()
    if earners:
        print(f"  [+] Earners: {', '.join(earners)}")
    if bleeders:
        print(f"  [-] Bleeders (candidates to CUT): {', '.join(bleeders)}")
    print()


def _print_breakdowns(trades: list):
    """Overall + out-of-sample per-setup performance."""
    _print_setup_breakdown(trades, "Per-Setup Breakdown — ALL trades")
    test_tr = [t for t in trades if t.get("phase") == "test"]
    if test_tr:
        _print_setup_breakdown(
            test_tr, "Per-Setup Breakdown — OUT-OF-SAMPLE (test half only)")


def _print_walk_forward(result: dict):
    m = result["full_metrics"]
    print("═══ Walk-Forward Report ═══════════════════════════════")
    split = result["split"]
    print(f"  Train period: {split['train_start']} → {split['train_end']}")
    print(f"  Test  period: {split['test_start']}  → {split['test_end']}")
    print(f"\n  Train trades: {result['train_trades']}  |  "
          f"Win rate: {result['train_win_rate']:.1f}%  |  "
          f"CAGR: {result.get('train_cagr', '?')}%")
    print(f"  Test  trades: {result['test_trades']}   |  "
          f"Win rate: {result['test_win_rate']:.1f}%\n")
    _print_metrics(m)
    _print_validation(result["validation"])
    _print_sample_trades(result.get("trades", []))
    _print_breakdowns(result.get("trades", []))


def _print_output_summary(output: dict):
    print(f"\n  Regime:   {output['market_regime']}")
    print(f"  Signals:  {len(output.get('trades', []))}")
    print(f"  Exits:    {len(output.get('exits', []))}")
    print(f"  Portfolio value: ₹{output['portfolio'].get('total_value', '?'):,.2f}")


def _save_report(result: dict):
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"backtest_report_{ts}.json"
    save = {k: v for k, v in result.items() if k != "equity_curve"}
    if "equity_curve" in result and not result["equity_curve"].empty:
        save["equity_curve"] = result["equity_curve"].reset_index().to_dict("records")
    if "trades" in result:
        save["trades"] = result.get("trades", [])
    with open(path, "w") as f:
        json.dump(save, f, indent=2, default=str)
    print(f"  Report saved → {path}")


# ─── Argument Parser ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="Swing Trading AI Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    bt = sub.add_parser("backtest", help="Historical backtesting")
    bt.add_argument("--walk-forward", action="store_true",
                    help="70/30 walk-forward validation")
    bt.add_argument("--stocks", type=int, default=None,
                    help="Limit number of stocks (faster testing)")

    lv = sub.add_parser("live", help="Daily market scan")
    lv.add_argument("--execute", action="store_true",
                    help="Record trades (default: dry run)")

    sub.add_parser("screen",    help="Run screener only")
    sub.add_parser("portfolio", help="Show portfolio status")

    args = parser.parse_args()

    if args.command == "backtest":
        cmd_backtest(args)
    elif args.command == "live":
        cmd_live(args)
    elif args.command == "screen":
        cmd_screen(args)
    elif args.command == "portfolio":
        cmd_portfolio(args)


if __name__ == "__main__":
    main()
