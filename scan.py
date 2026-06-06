#!/usr/bin/env python3
"""
scan.py — one-command A/A+ entry scanner across the full NSE Nifty-500 universe.

This is the production scan: it loads the whole universe (large + mid + small
caps), runs the strategy engine, keeps only A / A+ graded setups with a valid
entry/stop/target, ranks them, prints a table, and writes a timestamped CSV.

Run on your own machine (needs internet for yfinance):

    python scan.py                 # use cached data, grade A and better
    python scan.py --refresh       # re-download latest prices first (slower)
    python scan.py --min-grade A+  # only the highest-conviction setups
    python scan.py --top 30        # cap the table to the best 30
    python scan.py --no-liquidity  # don't apply the liquidity filter

Output CSV is written to:  signals/scan_YYYYMMDD_HHMMSS.csv
"""
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import argparse
import csv as _csv
from datetime import datetime
from pathlib import Path

import config
from data import load_all_stocks, load_index
from indicators import compute_all
from patterns import compute_all_patterns, rank_sectors
from signals import generate_signals

GRADE_RANK = {"A+": 0, "A": 1}
CONF_RANK = {"High": 0, "Medium": 1, "Low": 2}


def run_scan(refresh=False, min_grade="A", top=None, apply_liquidity=True):
    print("Loading index…")
    index_df = load_index(refresh=refresh)

    print(f"Loading universe ({len(config.UNIVERSE)} symbols)"
          f"{' with refresh (this can take several minutes)' if refresh else ' from cache'}…")
    stock_data = load_all_stocks(refresh=refresh, apply_liquidity=apply_liquidity,
                                 pause=0.15 if refresh else 0.0)
    if not stock_data:
        print("ERROR: no stock data. Run once with --refresh and internet access.")
        sys.exit(1)

    print(f"Scanning {len(stock_data)} liquid names for A/A+ setups…\n")
    sector_ranks = rank_sectors(stock_data)

    allowed = {"A+"} if min_grade.upper() == "A+" else {"A", "A+"}
    rows = []
    for symbol, df in stock_data.items():
        try:
            df_ind = compute_all(df)
            df_pat = compute_all_patterns(df_ind, index_df)
            sigs = generate_signals(symbol, df_pat)
        except Exception as e:
            print(f"  [WARN] {symbol}: {e}")
            continue
        last_close = float(df["close"].iloc[-1])
        for s in sigs:
            if s.get("grade") not in allowed:
                continue
            sector = config.SECTOR_MAP.get(symbol, "Unknown")
            entry = s["entry"]
            s["sector"] = sector
            s["sector_rank"] = sector_ranks.get(sector, 99)
            s["last_close"] = round(last_close, 2)
            # "good entry": how far price sits above the trigger (negative = still below)
            s["pct_above_entry"] = round((last_close - entry) / entry * 100, 2)
            s["risk_pct"] = round((entry - s["stop_loss"]) / entry * 100, 2)
            rows.append(s)

    if not rows:
        print(f"No {min_grade}+ setups today across the universe.")
        return []

    rows.sort(key=lambda s: (GRADE_RANK.get(s["grade"], 9),
                             CONF_RANK.get(s["confidence"], 3),
                             s.get("sector_rank", 99),
                             -s.get("risk_reward", 0)))
    if top:
        rows = rows[:top]

    _print_table(rows)
    out = _write_csv(rows)
    print(f"\n{len(rows)} setup(s).  CSV → {out}")
    return rows


def _print_table(rows):
    print(f"{'Symbol':<14}{'Setup':<16}{'Gr':<4}{'Entry':>9}{'Stop':>9}{'Target':>9}"
          f"{'R:R':>6}{'Risk%':>7}{'Conf':>8}  Sector")
    print("-" * 104)
    for s in rows:
        print(f"{s['symbol']:<14}{s['setup']:<16}{s['grade']:<4}"
              f"{s['entry']:>9.2f}{s['stop_loss']:>9.2f}{s['target']:>9.2f}"
              f"{s['risk_reward']:>6.1f}{s['risk_pct']:>6.1f}%{s['confidence']:>8}  {s['sector']}")


def _write_csv(rows):
    out_dir = Path("signals")
    out_dir.mkdir(exist_ok=True)
    path = out_dir / f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    cols = ["symbol", "setup", "grade", "grade_score", "grade_reasons", "confidence",
            "entry", "last_close", "pct_above_entry", "stop_loss", "risk_pct",
            "target", "secondary_target", "risk_reward", "stage", "sector",
            "sector_rank", "adr5", "avg_mdr3", "date"]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = _csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return path


def main():
    p = argparse.ArgumentParser(description="Scan the Nifty-500 for A/A+ swing setups")
    p.add_argument("--refresh", action="store_true", help="re-download prices first")
    p.add_argument("--min-grade", default="A", choices=["A", "A+"], help="minimum grade")
    p.add_argument("--top", type=int, default=None, help="cap table to N best setups")
    p.add_argument("--no-liquidity", action="store_true", help="disable liquidity filter")
    args = p.parse_args()
    run_scan(refresh=args.refresh, min_grade=args.min_grade, top=args.top,
             apply_liquidity=not args.no_liquidity)


if __name__ == "__main__":
    main()
