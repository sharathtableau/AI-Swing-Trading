# ─── Trading Parameters ───────────────────────────────────────────────────────
CAPITAL = 1_000_000           # Starting capital (₹10 Lakhs)
MAX_POSITIONS = 10
MAX_CAPITAL_PER_TRADE = 0.20  # 20% of capital per trade
MAX_SECTOR_EXPOSURE = 0.30    # 30% max in any one sector
RISK_PER_TRADE = 0.01         # 1% of capital risked per trade (Weinstein 1% Rule)
MIN_RISK_REWARD = 2.0
MAX_SL_PERCENT = 0.10         # Reject trades with SL wider than 10%

# ─── Stan Weinstein Stage Analysis ───────────────────────────────────────────
MA_WEEKLY = 150               # 30 weeks × 5 trading days — primary systemic filter
MA_SLOPE_LOOKBACK = 10        # periods used to measure MA slope direction
MA_SLOPE_MIN = 0.0003         # minimum slope to classify MA as "rising" (0.03% over 10 days)

# ─── Indicator Periods ────────────────────────────────────────────────────────
SMA_FAST = 50
SMA_SLOW = 200
EMA_FAST = 8                  # 8-13-21 EMA crossover system
EMA_MID  = 13
EMA_TREND = 21
RSI_PERIOD = 14
AVG_VOL_PERIOD = 20
VOLUME_MULTIPLIER = 2.0       # PDF mandates 2× avg volume for breakout conviction
BREAKOUT_LOOKBACK = 20        # Resistance window (days)
VCP_PERIODS = 3
BASE_FORMATION_WEEKS = 3      # Short-term base
LINEAR_BASE_WEEKS = 6         # Extended multi-month base (Big Base = Big Move)
BASE_FORMATION_RANGE = 0.10   # ±10% price range for base

# ─── VCP (Minervini Volatility Contraction Pattern) ──────────────────────────
# A true VCP is a SERIES of progressively shallower pullbacks with volume
# drying up, ending tight near the highs ready to break out. Implemented as
# three stacked ~10-day sub-ranges that each contract, holding higher lows.
VCP_LEG = 10                  # length of each contraction leg (days)
VCP_FINAL_TIGHT = 0.10        # final leg range must be <= 10% of price (tight)
VCP_VOL_DRYUP = 0.90          # recent vol must be <= 90% of base vol (supply drying)
VCP_NEAR_TOP = 0.95           # close must be >= 95% of base high (coiled to break)

# ─── Wyckoff Spring (shakeout below support that reclaims) ────────────────────
SPRING_SUPPORT_LOOKBACK = 20  # window defining the trading-range support
SPRING_MAX_UNDERCUT = 0.05    # break may dip at most 5% below support (shakeout, not breakdown)

# ─── Base Breakout (Weinstein Stage-1 → Stage-2 breakout) ────────────────────
BREAKOUT_BASE_WINDOW = 5      # base must have existed within the last N days
BREAKOUT_MAX_EXTENSION = 0.05 # only take fresh breakouts (<=5% above resistance, no chasing)

# ─── A / A+ Setup Grading (confluence selectivity) ───────────────────────────
GRADE_APLUS_MIN = 6           # confluence score >= 6  → A+ (highest conviction)
GRADE_A_MIN = 4               # confluence score >= 4  → A (tradeable); below = skip
RS_STRONG_MARGIN = 0.05       # stock outperforming index by >=5% over RS window = strong leader

# ─── ADR / MDR — PivotBoss Volatility Targeting ──────────────────────────────
ADR_PERIOD = 5                # 5-period Average Daily Range for stops
ADR_STOP_PCT = 0.50           # Stop at 50% of ADR below entry
MDR_DAYS = 3                  # Multiple Day Range window (3DR)
MDR_AVG_PERIOD = 5            # 5-period average of the 3DR
MDR_NORMAL_LITE_MULT = 2.0    # Primary target: FDL + (Avg MDR × 2.0) — wider target for swing holds
MDR_NORMAL_MULT = 1.00        # Secondary target: FDL + Avg MDR — ~45% hit rate

# ─── ATR Trailing Stops ───────────────────────────────────────────────────────
ATR_PERIOD = 14
ATR_TRAIL_MULT = 2.0          # Trail at 2× ATR below current price
USE_ATR_TRAILING = True       # Backtest exit: use ATR trailing (documented method)
                              # combined with break-even floor once in profit.

# ─── Exit policy: let winners run ─────────────────────────────────────────────
# Backtest showed a 30% win rate with winners (~1.4× losers) cut too small to pay
# for the losers (PF 0.61). A low-win-rate trend system MUST let winners run far.
# With USE_FIXED_TARGET=False the hard profit target is ignored in the backtest
# exit and the position rides the ATR trailing stop until the trend breaks, so a
# few big runners can carry the system. The target is still computed for entry
# R:R grading — only the *exit* cap is removed.
USE_FIXED_TARGET = False

# ─── Transaction Costs & Slippage (NSE delivery swing trades) ────────────────
# Round-trip cost as a fraction of trade value, applied on BOTH entry and exit.
# Rough all-in estimate for delivery equity: brokerage + STT + exchange txn +
# SEBI + GST + stamp duty ≈ 0.10–0.12% per side. Slippage models the gap
# between the signalled price and the realistic fill.
TXN_COST_PCT = 0.0012         # 0.12% per side (entry and exit each)
SLIPPAGE_PCT = 0.0015         # 0.15% adverse slippage per side

# ─── 3-5-7 Scaling Rule ───────────────────────────────────────────────────────
SCALE_LEVELS = [0.03, 0.05, 0.07]  # Scale out 1/3 of position at each gain level

# ─── Regime Filter ────────────────────────────────────────────────────────────
REGIME_RSI_THRESHOLD = 50
INDEX_SYMBOL = "^NSEI"        # Nifty 50

# ─── Screener Thresholds ──────────────────────────────────────────────────────
MIN_RSI_SCREEN = 55
NEAR_52W_HIGH_THRESHOLD = 0.90  # Within 10% of 52-week high

# ─── Data ─────────────────────────────────────────────────────────────────────
import os as _os
import csv as _csv

DATA_DIR = "data"
HISTORICAL_YEARS = 5

# ─── Liquidity Filter (keep mid/small caps tradeable) ─────────────────────────
# Illiquid names give signals you can't actually fill. Require a minimum median
# daily traded value (price × volume) and a minimum price. Tune for your size.
MIN_PRICE = 20.0                  # skip penny stocks (< ₹20)
MIN_AVG_TURNOVER = 50_000_000     # ₹5 crore median daily turnover over 50 days
LIQUIDITY_LOOKBACK = 50

# ─── Universe ─────────────────────────────────────────────────────────────────
# The tradeable universe is the NSE Nifty-500 (large + mid + small caps), loaded
# from nifty500.csv. To refresh: download the latest constituents from
# https://archives.nseindia.com/content/indices/ind_nifty500list.csv and replace
# the file. Dummy/placeholder symbols (e.g. DUMMYVEDL*) are filtered out
# automatically. yfinance ticker = Symbol + ".NS".

_UNIVERSE_CSV = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "nifty500.csv")

# Map NSE "Industry" column → short sector label used by sector-rotation logic.
_INDUSTRY_TO_SECTOR = {
    "Financial Services": "Finance",
    "Information Technology": "IT",
    "Fast Moving Consumer Goods": "FMCG",
    "Automobile and Auto Components": "Auto",
    "Healthcare": "Pharma",
    "Oil Gas & Consumable Fuels": "Energy",
    "Power": "Power",
    "Metals & Mining": "Metals",
    "Capital Goods": "Capital Goods",
    "Construction": "Infrastructure",
    "Construction Materials": "Cement",
    "Chemicals": "Chemicals",
    "Consumer Services": "Consumer",
    "Consumer Durables": "Consumer Durables",
    "Telecommunication": "Telecom",
    "Realty": "Realty",
    "Services": "Services",
    "Textiles": "Textiles",
    "Diversified": "Diversified",
    "Media Entertainment & Publication": "Media",
}

# Fallback mega-cap list used only if nifty500.csv is missing.
_FALLBACK_STOCKS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS",
    "LT.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS", "TITAN.NS",
]


def _load_universe(csv_path: str = _UNIVERSE_CSV):
    """Parse the Nifty-500 CSV into (symbols list, sector map).

    Filters out dummy placeholders and non-EQ/BE series. Returns yfinance-style
    tickers (SYMBOL.NS). Falls back to a small mega-cap list if the file is
    absent so the app still imports.
    """
    symbols, sector_map = [], {}
    if not _os.path.exists(csv_path):
        return list(_FALLBACK_STOCKS), {}
    with open(csv_path, newline="", encoding="utf-8-sig") as fh:
        for row in _csv.DictReader(fh):
            sym = (row.get("Symbol") or "").strip()
            series = (row.get("Series") or "EQ").strip().upper()
            if not sym or sym.upper().startswith("DUMMY"):
                continue
            if series not in ("EQ", "BE"):
                continue
            ticker = f"{sym}.NS"
            symbols.append(ticker)
            industry = (row.get("Industry") or "").strip()
            sector_map[ticker] = _INDUSTRY_TO_SECTOR.get(industry, industry or "Unknown")
    # de-dup, preserve order
    seen = set()
    symbols = [s for s in symbols if not (s in seen or seen.add(s))]
    return symbols, sector_map


UNIVERSE, SECTOR_MAP = _load_universe()

# Backward-compatible alias: existing modules reference config.NIFTY50_STOCKS.
NIFTY50_STOCKS = UNIVERSE

# ─── Alerts ───────────────────────────────────────────────────────────────────
EMAIL_ENABLED = False
EMAIL_SENDER = ""
EMAIL_PASSWORD = ""
EMAIL_RECIPIENT = ""
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

TELEGRAM_ENABLED = False
TELEGRAM_TOKEN = ""
TELEGRAM_CHAT_ID = ""
