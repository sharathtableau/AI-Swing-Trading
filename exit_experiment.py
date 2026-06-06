#!/usr/bin/env python3
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
"""
Entry-set x Exit-policy search.

The first experiment showed two things on out-of-sample data:
  * Wide trailing stops (3-4xATR) beat the tight 2xATR default.
  * Base Breakout EARNS under a wide trail; EMA Pullback (the highest-volume
    setup) BLEEDS and drags the whole system negative.

This script searches a small, principled grid: a few entry-set subsets crossed
with the wide-trail exits. Every combo is scored on the TEST (out-of-sample)
half only. Train numbers are shown solely to flag instability/overfitting.

A combo is only a real candidate if it clears TWO bars at once:
  (1) test-half profit factor > 1.0, AND
  (2) enough test trades to not be noise  (MIN_TEST_TRADES below).
A great PF on 8 trades is not a strategy.

We deliberately test a handful of defensible combos, NOT a fine grid — fitting a
fine grid to the test half would just re-introduce the overfitting we're trying
to avoid.

Run:  python exit_experiment.py            (full universe — slow but real)
      python exit_experiment.py 60         (first 60 stocks — fast smoke test)
"""
from data import load_all_stocks, load_index
from backtest import run_backtest, setup_breakdown

MIN_TEST_TRADES = 25   # below this, a test-half PF is treated as noise

# Entry subsets to test (None = all setups).
SETUP_SETS = [
    ("All setups",            None),
    ("Drop EMA+Weinstein",    {"Base Breakout", "VCP Breakout", "Wyckoff Spring"}),
    ("Base + VCP only",       {"Base Breakout", "VCP Breakout"}),
    ("Base Breakout only",    {"Base Breakout"}),
]

# Wide-trail exits that won the first experiment.
EXITS = [
    ("3xATR",            {"atr_mult": 3.0}),
    ("4xATR",            {"atr_mult": 4.0}),
    ("3xATR + BE@1R",    {"atr_mult": 3.0, "breakeven_r": 1.0}),
]


def _phase(trades, phase):
    return [t for t in trades if t.get("phase") == phase]


def _summ(trades):
    if not trades:
        return dict(n=0, win=0.0, payoff=0.0, pf=0.0, pnl=0.0, exp=0.0)
    pnls    = [t["pnl"] for t in trades]
    winners = [p for p in pnls if p > 0]
    losers  = [p for p in pnls if p <= 0]
    gp      = sum(winners)
    gl      = abs(sum(losers))
    avg_w   = gp / len(winners) if winners else 0.0
    avg_l   = gl / len(losers)  if losers  else 0.0
    return dict(
        n=len(trades),
        win=len(winners) / len(trades) * 100,
        payoff=(avg_w / avg_l) if avg_l > 0 else 0.0,
        pf=(gp / gl) if gl > 0 else (999.0 if gp > 0 else 0.0),
        pnl=sum(pnls),
        exp=sum(pnls) / len(trades),
    )


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None

    print("Loading data...")
    index_df   = load_index()
    all_stocks = load_all_stocks()
    if not all_stocks:
        print("ERROR: No stock data available.")
        sys.exit(1)
    if limit:
        keys       = list(all_stocks.keys())[:limit]
        all_stocks = {k: all_stocks[k] for k in keys}
    print(f"Universe: {len(all_stocks)} stocks\n")

    hdr = (f"{'Entry set':<22}{'Exit':<16}{'Phase':<6}{'Trades':>7}{'Win%':>7}"
           f"{'Payoff':>8}{'PF':>7}{'Exp/Trd':>9}{'TotalPnL':>13}")
    print(hdr)
    print("-" * len(hdr))

    candidates = []   # (combo_name, test_summary, trades)
    for sname, allowed in SETUP_SETS:
        for ename, ep in EXITS:
            res = run_backtest(all_stocks, index_df,
                               exit_policy=ep, allowed_setups=allowed)
            if "error" in res:
                print(f"{sname:<22}{ename:<16} ERROR: {res['error']}")
                continue
            trades = res["trades"]
            combo  = f"{sname} / {ename}"
            for phase in ("train", "test"):
                s   = _summ(_phase(trades, phase))
                tag = "TRAIN" if phase == "train" else "TEST"
                flag = ""
                if phase == "test" and s["pf"] > 1.0 and s["n"] >= MIN_TEST_TRADES:
                    flag = "  <== CANDIDATE"
                print(f"{sname:<22}{ename:<16}{tag:<6}{s['n']:>7}{s['win']:>6.1f}%"
                      f"{s['payoff']:>8.2f}{s['pf']:>7.2f}{s['exp']:>9,.0f}"
                      f"{s['pnl']:>13,.0f}{flag}")
            ts = _summ(_phase(trades, "test"))
            candidates.append((combo, ts, _phase(trades, "test")))
            print()

    # Rank surviving candidates by test PF.
    valid = [(c, ts, tr) for c, ts, tr in candidates
             if ts["pf"] > 1.0 and ts["n"] >= MIN_TEST_TRADES]
    print("=" * 70)
    if not valid:
        print("NO combo cleared test-PF > 1.0 with >= "
              f"{MIN_TEST_TRADES} out-of-sample trades.")
        print("Honest read: no validated edge here. Don't trade it live.")
        return
    valid.sort(key=lambda x: x[1]["pf"], reverse=True)
    print(f"{len(valid)} candidate(s) cleared both bars. Best by test PF:\n")
    best_c, best_ts, best_tr = valid[0]
    print(f"  {best_c}")
    print(f"  test trades={best_ts['n']}  win={best_ts['win']:.1f}%  "
          f"payoff={best_ts['payoff']:.2f}  PF={best_ts['pf']:.2f}  "
          f"total PnL=Rs {best_ts['pnl']:,.0f}")
    print("\n  Per-setup (out-of-sample) under this combo:")
    rows = setup_breakdown(best_tr)
    print(f"    {'Setup':<20}{'Trades':>7}{'Win%':>7}{'Payoff':>8}{'PF':>7}{'TotalPnL':>12}")
    for r in rows:
        print(f"    {r['setup']:<20}{r['trades']:>7}{r['win_rate_pct']:>6.1f}%"
              f"{r['payoff']:>8.2f}{r['profit_factor']:>7.2f}{r['total_pnl']:>12,.0f}")


if __name__ == "__main__":
    main()
