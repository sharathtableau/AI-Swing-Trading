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

# ─── 3-5-7 Scaling Rule ───────────────────────────────────────────────────────
SCALE_LEVELS = [0.03, 0.05, 0.07]  # Scale out 1/3 of position at each gain level

# ─── Regime Filter ────────────────────────────────────────────────────────────
REGIME_RSI_THRESHOLD = 50
INDEX_SYMBOL = "^NSEI"        # Nifty 50

# ─── Screener Thresholds ──────────────────────────────────────────────────────
MIN_RSI_SCREEN = 55
NEAR_52W_HIGH_THRESHOLD = 0.90  # Within 10% of 52-week high

# ─── Data ─────────────────────────────────────────────────────────────────────
DATA_DIR = "data"
HISTORICAL_YEARS = 5

# ─── Universe ─────────────────────────────────────────────────────────────────
NIFTY50_STOCKS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS",
    "LT.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS", "TITAN.NS",
    "NESTLEIND.NS", "WIPRO.NS", "HCLTECH.NS", "ULTRACEMCO.NS", "BAJFINANCE.NS",
    "BAJAJFINSV.NS", "TECHM.NS", "SUNPHARMA.NS", "ONGC.NS", "NTPC.NS",
    "POWERGRID.NS", "COALINDIA.NS", "TATAMOTORS.NS", "JSWSTEEL.NS", "TATASTEEL.NS",
    "ADANIENT.NS", "ADANIPORTS.NS", "DRREDDY.NS", "DIVISLAB.NS", "CIPLA.NS",
    "APOLLOHOSP.NS", "BPCL.NS", "GRASIM.NS", "HEROMOTOCO.NS", "M&M.NS",
    "EICHERMOT.NS", "BRITANNIA.NS", "TATACONSUM.NS", "HINDALCO.NS", "VEDL.NS",
    "SBILIFE.NS", "HDFCLIFE.NS", "INDUSINDBK.NS", "BAJAJ-AUTO.NS", "UPL.NS",
]

SECTOR_MAP = {
    "RELIANCE.NS":   "Energy",        "TCS.NS":        "IT",
    "HDFCBANK.NS":   "Banking",       "INFY.NS":       "IT",
    "ICICIBANK.NS":  "Banking",       "HINDUNILVR.NS": "FMCG",
    "ITC.NS":        "FMCG",          "SBIN.NS":       "Banking",
    "BHARTIARTL.NS": "Telecom",       "KOTAKBANK.NS":  "Banking",
    "LT.NS":         "Infrastructure","AXISBANK.NS":   "Banking",
    "ASIANPAINT.NS": "Paints",        "MARUTI.NS":     "Auto",
    "TITAN.NS":      "Consumer",      "NESTLEIND.NS":  "FMCG",
    "WIPRO.NS":      "IT",            "HCLTECH.NS":    "IT",
    "ULTRACEMCO.NS": "Cement",        "BAJFINANCE.NS": "Finance",
    "BAJAJFINSV.NS": "Finance",       "TECHM.NS":      "IT",
    "SUNPHARMA.NS":  "Pharma",        "ONGC.NS":       "Energy",
    "NTPC.NS":       "Power",         "POWERGRID.NS":  "Power",
    "COALINDIA.NS":  "Mining",        "TATAMOTORS.NS": "Auto",
    "JSWSTEEL.NS":   "Steel",         "TATASTEEL.NS":  "Steel",
    "ADANIENT.NS":   "Diversified",   "ADANIPORTS.NS": "Infrastructure",
    "DRREDDY.NS":    "Pharma",        "DIVISLAB.NS":   "Pharma",
    "CIPLA.NS":      "Pharma",        "APOLLOHOSP.NS": "Healthcare",
    "BPCL.NS":       "Energy",        "GRASIM.NS":     "Diversified",
    "HEROMOTOCO.NS": "Auto",          "M&M.NS":        "Auto",
    "EICHERMOT.NS":  "Auto",          "BRITANNIA.NS":  "FMCG",
    "TATACONSUM.NS": "FMCG",          "HINDALCO.NS":   "Metals",
    "VEDL.NS":       "Metals",        "SBILIFE.NS":    "Insurance",
    "HDFCLIFE.NS":   "Insurance",     "INDUSINDBK.NS": "Banking",
    "BAJAJ-AUTO.NS": "Auto",          "UPL.NS":        "Chemicals",
}

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
