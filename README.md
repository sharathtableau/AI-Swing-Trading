# 📈 NSE Swing Trader

A comprehensive swing trading analysis tool for NSE-listed Indian stocks, built with Streamlit. Combines a 3-layer scoring engine, Gomathi Shankar CPR methodology, and live market data into a single dashboard — accessible from desktop or iPhone.

---

## Features

### 5 Tabs

**🔍 Analyse**
- Search any NSE stock with autocomplete
- Live price feed with real-time CPR position check
- 3-layer swing score (Trend / Momentum / Setup) out of 100
- Gomathi Shankar CPR signal: CONFIRM / NEUTRAL / CAUTION / REJECT
- PivotBoss S/R levels (R1–R4, S1–S4) with nearest level highlighted
- Interactive candlestick chart with EMA 8/13/21/50, 30-Week MA, Bollinger Bands, MACD, CPR lines
- Trade setup card: Entry · ADR Stop · T1 (70%) · T2 (45%) · T3 Runner · R:R
- Position sizing based on your capital and risk % settings

**📊 Screener**
- Scan Nifty 50 / Next 50 / Midcap 150 / Smallcap / All 300+ / All NSE (~2000 stocks)
- Custom symbol input (comma-separated)
- Parallel scanning with up to 20 workers — full Midcap 150 in ~2 minutes
- Results table: Score · Verdict · CPR Signal · Trend/Mom/Setup layers · Entry · SL · R:R
- "Above Daily CPR only" filter (CONFIRM + NEUTRAL stocks only)
- Sector Rotation breakdown and Stage 1 Accumulation expander
- One-click "Add all STRONG BUY to Watchlist"

**👁 Watchlist**
- Persistent JSON-based watchlist (session state fallback on cloud)
- Live rescoring of all watchlist stocks on demand
- Individual charts, trade setup cards, and remove buttons

**💼 Portfolio**
- Open position tracking with entry price, quantity, current value
- ATR trailing stop calculation
- Free trade technique (scale-out at T1 to make SL free)
- Telegram alert integration — test from sidebar

**📈 Backtest**
- Event-driven backtest over any universe and time period
- Equity curve, win rate, Sharpe ratio, CAGR output
- Configurable max positions, SL%, and risk per trade

---

## Scoring Engine

Scores are built from 3 independent layers — max 100 points:

| Layer | Max | What it measures |
|---|---|---|
| L1 Trend | 40 | Stage 2 advance, EMA alignment, 52-week position, Supertrend |
| L2 Momentum | 35 | RSI, MACD, ADX, 10/20-day momentum vs Nifty |
| L3 Setup | 25 | Volume surge, VCP pattern, candle quality |

**Verdict thresholds:**

| Score | Verdict |
|---|---|
| ≥ 75 | STRONG BUY |
| 55–74 | WATCHLIST |
| < 55 | AVOID |

---

## CPR Filter (Gomathi Shankar Methodology)

Based on *"Secret of Pivot Boss"* by Frank Ochoa and Gomathi Shankar's CPR methodology. CPR levels are calculated fresh each day from the **previous session's** High / Low / Close.

**Formulas:**
```
Pivot = (H + L + C) / 3
BC    = (H + L) / 2
TC    = (Pivot − BC) + Pivot
```

**Four signal levels — act as a hard filter gate:**

| Signal | Condition | Score Impact | Verdict Effect |
|---|---|---|---|
| ✅ CONFIRM | Above TC + Narrow CPR and/or above Weekly CPR | +6 to +10 pts | No change |
| 🟡 NEUTRAL | Above TC, wide CPR | +3 pts | No change |
| ⚠️ CAUTION | Inside CPR zone | −4 pts | STRONG BUY → WATCHLIST |
| 🚫 REJECT | Below BC | −12 pts | STRONG BUY → WATCHLIST, WATCHLIST → AVOID |

The CPR position is evaluated against the **live price** during market hours, not yesterday's close.

---

## Indicators (Pure NumPy — zero external TA libraries)

All indicators are implemented from scratch using NumPy/Pandas:

- EMA (8, 9, 13, 21, 50, 200)
- SMA / 30-Week MA
- RSI (14)
- MACD (12/26/9)
- Bollinger Bands (20, 2σ)
- ATR (14)
- ADX (14)
- Supertrend (10, 3.0)
- VCP (Volatility Contraction Pattern)
- Weinstein Stage detection

---

## Setup — Run Locally

**Requirements:** Python 3.12+

```bash
# 1. Clone or download this repo
cd "AI Swing Trading"

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
streamlit run app.py
```

App opens at `http://localhost:8501`

---

## Deploy to Streamlit Cloud (Free, Permanent)

1. Push `app.py` and `requirements.txt` to a GitHub repository
2. Go to [share.streamlit.io](https://share.streamlit.io) → sign in with GitHub
3. Click **New app** → select your repo → set main file to `app.py` → **Deploy**
4. Your app gets a permanent public URL in ~3 minutes

**Access on iPhone:** Open the URL in Safari → Share → Add to Home Screen

---

## Sidebar Settings

| Setting | Default | Description |
|---|---|---|
| Capital (₹) | 10,00,000 | Total trading capital for position sizing |
| Risk per trade (%) | 1.0% | Max loss per trade as % of capital |
| Max positions | 10 | Max concurrent open trades |
| Max SL% allowed | 10% | Filters out setups with stop-loss wider than this |
| Telegram Bot Token | — | For push alerts from Portfolio tab |
| Telegram Chat ID | — | Your Telegram chat/channel ID |

---

## Stock Universes

| Universe | Count |
|---|---|
| Nifty 50 | 50 |
| Nifty Next 50 | 50 |
| Nifty Midcap 150 | ~100 |
| Nifty Smallcap | ~100 |
| Nifty 100 | 100 |
| All 300+ | 300+ |
| All NSE Listed | ~2000 |

---

## Notes

- Price data is fetched from **Yahoo Finance** via `yfinance` (NSE suffix `.NS`)
- OHLCV data is cached for 10 minutes; live price cached for 60 seconds
- Watchlist persists in `watchlist.json` locally; resets on Streamlit Cloud restart (session-state fallback active)
- The app uses no paid APIs or data subscriptions

---

## Disclaimer

This tool is for **educational and research purposes only**. It does not constitute financial advice. Always do your own research before making any investment decisions. Past performance of any signal or backtest does not guarantee future results.
