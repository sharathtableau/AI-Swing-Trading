"""
NSE Swing Trader — 3-Layer Swing Score Tool
Analyse · Screener · Watchlist · Portfolio · Backtest
"""
import warnings; warnings.filterwarnings("ignore")
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests, json, os, urllib.request
from io import StringIO
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

st.set_page_config(page_title="NSE Swing Trader", page_icon="📈",
                   layout="wide", initial_sidebar_state="expanded")

# ── COLOURS ────────────────────────────────────────────────────────────────────
C = {
    "bg":"#08090d","card":"#0f1117","border":"#1e2030","border2":"#2d3047",
    "green":"#00d97e","red":"#ff4560","amber":"#ffa600","blue":"#4361ee",
    "purple":"#ab47bc","text":"#e8eaed","muted":"#8b8fa8","dim":"#3d3f53",
}

def hex_rgba(h, a):
    h = h.lstrip("#")
    r,g,b = int(h[0:2],16),int(h[2:4],16),int(h[4:6],16)
    return f"rgba({r},{g},{b},{a})"

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');
html,body,.stApp{{background:{C['bg']} !important;color:{C['text']};font-family:'DM Sans',sans-serif;}}
.main .block-container{{padding-top:1.2rem;padding-bottom:3rem;max-width:1400px;}}
#MainMenu,footer,header{{visibility:hidden;}}

/* ── Sidebar base ──────────────────────────────────────────────────────── */
section[data-testid="stSidebar"]{{
    background:{C['card']};
    border-right:1px solid {C['border']};
}}
/* All text inside sidebar should be visible */
section[data-testid="stSidebar"] *{{color:{C['text']} !important;}}
section[data-testid="stSidebar"] label{{
    color:{C['text']} !important;
    font-size:13px !important;
    font-weight:500 !important;
    font-family:'DM Sans',sans-serif !important;
}}
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] div{{color:{C['text']} !important;}}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3{{
    color:{C['text']} !important;
    font-family:'DM Sans',sans-serif !important;
}}
/* Sidebar number inputs */
section[data-testid="stSidebar"] input{{
    background:{C['bg']} !important;
    color:{C['text']} !important;
    border:1px solid {C['border']} !important;
    border-radius:6px !important;
    font-family:'JetBrains Mono',monospace !important;
    font-size:13px !important;
}}
/* Sidebar slider track */
section[data-testid="stSidebar"] .stSlider [data-testid="stSliderThumb"]{{
    background:{C['blue']} !important;
}}
section[data-testid="stSidebar"] .stSlider [data-baseweb="slider"] [role="slider"]{{
    background:{C['blue']} !important;
}}
/* Sidebar step +/- buttons */
section[data-testid="stSidebar"] .stNumberInput button{{
    background:{C['border']} !important;
    color:{C['text']} !important;
    border:1px solid {C['border2']} !important;
}}
section[data-testid="stSidebar"] .stNumberInput button:hover{{
    background:{C['border2']} !important;
}}
/* Sidebar divider */
section[data-testid="stSidebar"] hr{{border-color:{C['border2']};}}
/* Success / warning / error inside sidebar */
section[data-testid="stSidebar"] .stAlert p{{color:#111 !important;}}

/* ── Global widgets ─────────────────────────────────────────────────────── */
div[data-baseweb="select"]>div{{background:{C['card']} !important;border-color:{C['border']} !important;color:{C['text']} !important;}}
div[data-baseweb="select"] span{{color:{C['text']} !important;}}
div[data-baseweb="select"] input{{color:{C['text']} !important;background:transparent !important;}}
div[data-baseweb="popover"] li{{background:{C['card']} !important;color:{C['text']} !important;}}
div[data-baseweb="popover"] li span{{color:{C['text']} !important;}}
div[data-baseweb="popover"] li:hover{{background:{C['border']} !important;}}
div[data-baseweb="popover"] li:hover span{{color:{C['text']} !important;}}
[data-baseweb="option"]{{color:{C['text']} !important;background:{C['card']} !important;}}
[aria-selected="true"][data-baseweb="option"]{{background:{C['border2']} !important;}}
.stButton>button{{background:{C['blue']} !important;color:white !important;border:none !important;border-radius:8px !important;font-family:'DM Sans',sans-serif !important;font-weight:500 !important;height:42px !important;}}
.stButton>button:hover{{background:#3451db !important;}}
div[data-testid="stMetricValue"]{{font-size:20px;font-weight:700;color:{C['text']};}}
div[data-testid="stMetricLabel"]{{font-size:11px;color:{C['muted']};text-transform:uppercase;letter-spacing:.5px;}}
button[data-baseweb="tab"]{{font-size:14px;font-weight:600;color:{C['muted']};}}
button[data-baseweb="tab"][aria-selected="true"]{{color:{C['blue']} !important;border-bottom-color:{C['blue']} !important;}}
hr{{border-color:{C['border']};margin:1.2rem 0;}}
</style>
""", unsafe_allow_html=True)

# ── NSE STOCK LIST (for Analyse tab search/suggestions) ───────────────────────
FALLBACK_STOCKS = [
    ("RELIANCE","Reliance Industries"),("TCS","Tata Consultancy Services"),
    ("HDFCBANK","HDFC Bank"),("INFY","Infosys"),("ICICIBANK","ICICI Bank"),
    ("HINDUNILVR","Hindustan Unilever"),("SBIN","State Bank of India"),
    ("BAJFINANCE","Bajaj Finance"),("BHARTIARTL","Bharti Airtel"),
    ("KOTAKBANK","Kotak Mahindra Bank"),("ITC","ITC Ltd"),("LT","Larsen & Toubro"),
    ("AXISBANK","Axis Bank"),("ASIANPAINT","Asian Paints"),("MARUTI","Maruti Suzuki"),
    ("TITAN","Titan Company"),("SUNPHARMA","Sun Pharmaceutical"),
    ("ULTRACEMCO","UltraTech Cement"),("WIPRO","Wipro"),("HCLTECH","HCL Technologies"),
    ("NTPC","NTPC"),("POWERGRID","Power Grid Corp"),("ONGC","ONGC"),
    ("COALINDIA","Coal India"),("TECHM","Tech Mahindra"),("ADANIENT","Adani Enterprises"),
    ("ADANIPORTS","Adani Ports"),("TATASTEEL","Tata Steel"),("JSWSTEEL","JSW Steel"),
    ("HINDALCO","Hindalco Industries"),("BAJAJ-AUTO","Bajaj Auto"),
    ("EICHERMOT","Eicher Motors"),("HEROMOTOCO","Hero MotoCorp"),
    ("TATACONSUM","Tata Consumer"),("BRITANNIA","Britannia Industries"),
    ("NESTLEIND","Nestle India"),("DIVISLAB","Divi's Labs"),("CIPLA","Cipla"),
    ("DRREDDY","Dr. Reddy's"),("APOLLOHOSP","Apollo Hospitals"),
    ("BPCL","Bharat Petroleum"),("IOC","Indian Oil Corp"),("GRASIM","Grasim Industries"),
    ("INDUSINDBK","IndusInd Bank"),("M&M","Mahindra & Mahindra"),
    ("TATAMOTORS","Tata Motors"),("BAJAJFINSV","Bajaj Finserv"),
    ("HDFCLIFE","HDFC Life Insurance"),("SBILIFE","SBI Life Insurance"),
    ("ICICIPRULI","ICICI Prudential"),("PIDILITIND","Pidilite Industries"),
    ("BERGEPAINT","Berger Paints"),("HAVELLS","Havells India"),("VOLTAS","Voltas"),
    ("POLYCAB","Polycab India"),("DIXON","Dixon Technologies"),("ASTRAL","Astral Ltd"),
    ("PERSISTENT","Persistent Systems"),("MPHASIS","Mphasis"),("COFORGE","Coforge"),
    ("LTIM","LTIMindtree"),("ZOMATO","Zomato"),("IRCTC","IRCTC"),
    ("DMART","Avenue Supermarts"),("TRENT","Trent Ltd"),("VEDL","Vedanta"),
    ("NMDC","NMDC"),("SAIL","SAIL"),("BANKBARODA","Bank of Baroda"),
    ("PNB","Punjab National Bank"),("FEDERALBNK","Federal Bank"),
    ("IDFCFIRSTB","IDFC First Bank"),("BANDHANBNK","Bandhan Bank"),
    ("CANBK","Canara Bank"),("CHOLAFIN","Cholamandalam Finance"),
    ("MUTHOOTFIN","Muthoot Finance"),("SRF","SRF Ltd"),("DEEPAKNTR","Deepak Nitrite"),
    ("AARTIIND","Aarti Industries"),("JUBLFOOD","Jubilant Foodworks"),
    ("INDIGO","IndiGo Airlines"),("DLF","DLF"),("GODREJPROP","Godrej Properties"),
    ("BEL","Bharat Electronics"),("HAL","Hindustan Aeronautics"),
    ("BHEL","BHEL"),("ABB","ABB India"),("SIEMENS","Siemens India"),
    ("RECLTD","REC Ltd"),("PFC","Power Finance Corp"),("IRFC","IRFC"),
    ("RVNL","Rail Vikas Nigam"),("ADANIGREEN","Adani Green Energy"),
    ("TATAPOWER","Tata Power"),("NHPC","NHPC"),("SJVN","SJVN"),
    ("CUMMINSIND","Cummins India"),("TORNTPHARM","Torrent Pharma"),
    ("ALKEM","Alkem Laboratories"),("AUROPHARMA","Aurobindo Pharma"),
    ("BIOCON","Biocon"),("INDUSTOWER","Indus Towers"),
    ("OBEROIRLTY","Oberoi Realty"),("PRESTIGE","Prestige Estates"),
    ("PAGEIND","Page Industries"),("ABBOTINDIA","Abbott India"),
    ("INOXWIND","Inox Wind"),("SUZLON","Suzlon Energy"),
    ("CESC","CESC"),("ADANITRANS","Adani Transmission"),
    ("GRINDWELL","Grindwell Norton"),("SCHAEFFLER","Schaeffler India"),
    ("ABB","ABB India"),("HONAUT","Honeywell Automation"),
    # Smallcap additions
    ("AJANTPHARM","Ajanta Pharma"),("CAMS","CAMS"),("CANFINHOME","Can Fin Homes"),
    ("FINEORG","Fine Organics"),("HAPPSTMNDS","Happiest Minds"),
    ("LATENTVIEW","LatentView Analytics"),("NAVINFLUOR","Navin Fluorine"),
    ("SOLARINDS","Solar Industries"),("ROUTE","Route Mobile"),
    ("SAFARI","Safari Industries"),("SYMPHONY","Symphony Ltd"),
    ("VGUARD","V-Guard"),("METROPOLIS","Metropolis Healthcare"),
    ("AAVAS","Aavas Financiers"),("ERIS","Eris Lifesciences"),
    ("OLECTRA","Olectra Greentech"),("KPITTECH","KPIT Technologies"),
    ("TATAELXSI","Tata Elxsi"),("CDSL","CDSL"),("IREDA","IREDA"),
]

@st.cache_data(ttl=86400)
def load_nse_stocks() -> pd.DataFrame:
    headers = {"User-Agent": "Mozilla/5.0"}
    frames = []
    try:
        r = requests.get("https://archives.nseindia.com/content/equities/EQUITY_L.csv",
                         headers=headers, timeout=8)
        r.raise_for_status()
        eq = pd.read_csv(StringIO(r.text))[["SYMBOL","NAME OF COMPANY"]].dropna()
        eq.columns = ["symbol","name"]
        frames.append(eq)
    except Exception:
        pass
    try:
        r = requests.get("https://archives.nseindia.com/content/equities/eq_etfseclist.csv",
                         headers=headers, timeout=8)
        r.raise_for_status()
        etf = pd.read_csv(StringIO(r.text))
        sc = [c for c in etf.columns if "symbol" in c.lower()][0]
        nc = [c for c in etf.columns if "name" in c.lower() or "security" in c.lower()][0]
        etf = etf[[sc,nc]].dropna(); etf.columns = ["symbol","name"]
        frames.append(etf)
    except Exception:
        pass
    if frames:
        df = pd.concat(frames, ignore_index=True).drop_duplicates(subset="symbol")
        df["display"] = df["symbol"] + "  —  " + df["name"].str.title()
        return df.reset_index(drop=True)
    df = pd.DataFrame(FALLBACK_STOCKS, columns=["symbol","name"])
    df["display"] = df["symbol"] + "  —  " + df["name"]
    return df

# ── DATA FETCHING ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=600)
def fetch_ohlcv(symbol: str, period: str = "1y") -> pd.DataFrame:
    for suffix in [".NS", ".BO"]:
        try:
            df = yf.download(symbol + suffix, period=period, interval="1d",
                             progress=False, auto_adjust=True)
            if not df.empty:
                break
        except Exception:
            continue
    if df.empty:
        raise ValueError(f"No data for {symbol}")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    return df[["open","high","low","close","volume"]].dropna()

@st.cache_data(ttl=60)
def fetch_live_price(symbol: str) -> dict:
    try:
        t = yf.Ticker(symbol + ".NS")
        fi = t.fast_info
        price = float(fi.last_price)
        prev  = float(fi.previous_close)
        chg   = round(price - prev, 2)
        pct   = round(chg / prev * 100, 2)
        return {"price": price, "change": chg, "pct": pct}
    except Exception:
        return {"price": 0.0, "change": 0.0, "pct": 0.0}

@st.cache_data(ttl=3600)
def fetch_index() -> pd.DataFrame:
    try:
        df = yf.download("^NSEI", period="2y", interval="1d",
                         progress=False, auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [c.lower() for c in df.columns]
        return df[["open","high","low","close","volume"]].dropna()
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def fetch_nifty_3m_return() -> float:
    try:
        nf = yf.download("^NSEI", period="4mo", interval="1d",
                         progress=False, auto_adjust=True)
        if isinstance(nf.columns, pd.MultiIndex):
            nf.columns = nf.columns.get_level_values(0)
        nf.columns = [c.lower() for c in nf.columns]
        c = nf["close"].dropna()
        return float((c.iloc[-1]-c.iloc[-63])/c.iloc[-63]*100) if len(c)>=63 else 0.0
    except Exception:
        return 0.0

# ── PURE NUMPY/PANDAS INDICATOR ENGINE (no pandas_ta / numba) ────────────────
def _ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()

def _sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n).mean()

def _rsi(s: pd.Series, n: int = 14) -> pd.Series:
    delta = s.diff()
    gain  = delta.clip(lower=0)
    loss  = (-delta).clip(lower=0)
    ag    = gain.ewm(com=n-1, adjust=False).mean()
    al    = loss.ewm(com=n-1, adjust=False).mean()
    return 100 - 100 / (1 + ag / al.replace(0, 1e-10))

def _atr(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.Series:
    hl = high - low
    hc = (high - close.shift(1)).abs()
    lc = (low  - close.shift(1)).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.ewm(com=n-1, adjust=False).mean()

def _macd(s: pd.Series, fast=12, slow=26, sig=9):
    m = _ema(s, fast) - _ema(s, slow)
    signal = _ema(m, sig)
    return m, signal, m - signal

def _bbands(s: pd.Series, n=20, std_mult=2):
    mid   = _sma(s, n)
    sigma = s.rolling(n).std()
    return mid + std_mult*sigma, mid, mid - std_mult*sigma

def _adx(high: pd.Series, low: pd.Series, close: pd.Series, n=14) -> pd.Series:
    atr  = _atr(high, low, close, n)
    up   = high.diff();  dn = (-low.diff())
    pdm  = np.where((up > dn) & (up > 0), up, 0.0)
    ndm  = np.where((dn > up) & (dn > 0), dn, 0.0)
    pdms = pd.Series(pdm, index=high.index).ewm(com=n-1, adjust=False).mean()
    ndms = pd.Series(ndm, index=high.index).ewm(com=n-1, adjust=False).mean()
    pdi  = 100 * pdms / atr.replace(0, 1e-10)
    ndi  = 100 * ndms / atr.replace(0, 1e-10)
    dx   = (pdi - ndi).abs() / (pdi + ndi).replace(0, 1e-10) * 100
    return dx.ewm(com=n-1, adjust=False).mean()

def _supertrend(high: pd.Series, low: pd.Series, close: pd.Series, n=10, mult=3.0):
    atr_arr = _atr(high, low, close, n).values
    h = high.values; l = low.values; c = close.values
    mid = (h + l) / 2
    upper = mid + mult * atr_arr
    lower = mid - mult * atr_arr
    fu = upper.copy(); fl = lower.copy()
    direction = np.ones(len(c), dtype=int)
    st_val    = np.full(len(c), np.nan)
    for i in range(1, len(c)):
        fu[i] = upper[i] if (upper[i] < fu[i-1] or c[i-1] > fu[i-1]) else fu[i-1]
        fl[i] = lower[i] if (lower[i] > fl[i-1] or c[i-1] < fl[i-1]) else fl[i-1]
        if   c[i] > fu[i-1]: direction[i] =  1
        elif c[i] < fl[i-1]: direction[i] = -1
        else:                 direction[i] =  direction[i-1]
        st_val[i] = fl[i] if direction[i] == 1 else fu[i]
    return pd.Series(st_val, index=close.index), pd.Series(direction, index=close.index)

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    c = df["close"]; h = df["high"]; l = df["low"]
    for n in [8, 9, 13, 21, 50]:
        df[f"ema{n}"] = _ema(c, n)
    df["ema200"] = _ema(c, min(200, max(50, len(df)//2)))
    df["ma150"]  = _sma(c, min(150, max(30, len(df)-5)))
    df["daily_range"] = h - l
    df["adr5"] = _sma(df["daily_range"], 5)
    df["hhv3"] = h.rolling(3).max()
    df["llv3"] = l.rolling(3).min()
    df["3dr"]  = df["hhv3"] - df["llv3"]
    df["mdr"]  = _sma(df["3dr"], 5)
    df["rsi"]  = _rsi(c)
    df["macd"], df["macd_sig"], df["macd_hist"] = _macd(c)
    df["st_val"], df["st_dir"] = _supertrend(h, l, c)
    df["bb_upper"], df["bb_mid"], df["bb_lower"] = _bbands(c)
    df["atr"]  = _atr(h, l, c)
    df["adx"]  = _adx(h, l, c)
    df["vol_ma20"]  = _sma(df["volume"], 20)
    df["vol_ratio"] = df["volume"] / df["vol_ma20"]
    df["chg10d"]    = c.pct_change(10) * 100
    df["high52w"]   = h.rolling(252, min_periods=126).max()
    df["support20"] = l.shift(1).rolling(20).min()
    df["resistance20"] = h.shift(1).rolling(20).max()
    core = ["ema8","ema13","ema21","rsi","macd_hist","bb_upper","bb_lower","atr","adx","vol_ratio"]
    return df.dropna(subset=core).reset_index(drop=False)

def detect_stage(df: pd.DataFrame) -> tuple:
    l   = df.iloc[-1]
    cmp = float(l["close"])
    col = "ma150" if "ma150" in df.columns else "ema50"
    ma  = float(l[col]) if not pd.isna(l[col]) else cmp
    lb_med = min(20, len(df)-1)
    pm = float(df[col].iloc[-lb_med]); pm = ma if pd.isna(pm) else pm
    slope_med = (ma - pm) / max(pm, 0.01) * 100
    lb_sht = min(8, len(df)-1)
    ps = float(df[col].iloc[-lb_sht]); ps = ma if pd.isna(ps) else ps
    slope_sht = (ma - ps) / max(ps, 0.01) * 100
    above_ma = cmp > ma
    recent_cross = False
    if above_ma and len(df) >= 10:
        recent_cross = any(float(df["close"].iloc[-i]) < float(df[col].iloc[-i]) for i in range(2,11))
    if above_ma and slope_med > 0.3:
        return "2", "Stage 2 — Advancing"
    elif above_ma and recent_cross:
        return "1→2", "Stage 1→2 — Base Breakout ↑"
    elif above_ma and slope_sht > -0.2:
        return "1→2", "Stage 1→2 — Transitioning"
    elif above_ma:
        return "1→2", "Stage 1→2 — Early Recovery"
    elif not above_ma and slope_med > -0.3:
        return "3", "Stage 3 — Distribution/Basing"
    else:
        return "4", "Stage 4 — Declining"

def detect_vcp(df: pd.DataFrame) -> tuple:
    if len(df) < 20:
        return False, "Insufficient data"
    segs = []
    for i in range(4):
        s = df.iloc[-(4-i)*5:-(3-i)*5 if i < 3 else len(df)]
        r = (s["high"].max()-s["low"].min()) / float(s["close"].mean())
        segs.append(r)
    contracting  = all(segs[i] > segs[i+1]*0.88 for i in range(3))
    tightest_now = segs[-1] == min(segs)
    vol_now  = float(df["volume"].iloc[-5:].mean())
    vol_prev = float(df["volume"].iloc[-20:-5].mean())
    vol_decay = vol_now < vol_prev * 0.92
    if contracting and vol_decay and tightest_now:
        return True, "VCP Confirmed"
    elif contracting or (vol_decay and tightest_now):
        return False, "Partial contraction"
    return False, "No contraction"

def find_sr(df: pd.DataFrame, lookback: int = 60, window: int = 10):
    sub = df.tail(lookback)
    highs, lows = [], []
    for i in range(window, len(sub)-window):
        if sub["high"].iloc[i] == sub["high"].iloc[i-window:i+window].max():
            highs.append(float(sub["high"].iloc[i]))
        if sub["low"].iloc[i]  == sub["low"].iloc[i-window:i+window].min():
            lows.append(float(sub["low"].iloc[i]))
    resistance = sorted(set(highs), reverse=True)[:3] or [float(df["high"].max())]
    support    = sorted(set(lows))[:3]            or [float(df["low"].min())]
    return support, resistance

def candle_pattern(df: pd.DataFrame) -> str:
    c = df.iloc[-1]; p = df.iloc[-2]
    body    = abs(c["close"]-c["open"])
    lo_wick = min(c["close"],c["open"])-c["low"]
    up_wick = c["high"]-max(c["close"],c["open"])
    rng     = c["high"]-c["low"]
    if rng == 0: return "Neutral"
    bull = c["close"] > c["open"]
    if bull and lo_wick > 2*body and up_wick < 0.15*rng: return "Hammer"
    if (bull and p["close"]<p["open"] and c["open"]<p["close"] and c["close"]>p["open"]):
        return "Bullish Engulfing"
    if body < 0.07*rng: return "Doji"
    if bull and body > 0.65*rng: return "Bullish Marubozu"
    if not bull and body > 0.65*rng: return "Bearish Marubozu"
    return "Bullish" if bull else "Bearish"

# ── 3-LAYER SCORING ENGINE ─────────────────────────────────────────────────────
def compute_cpr(df: pd.DataFrame, live_price: float = 0.0) -> dict:
    """
    Gomathi Shankar CPR (Central Pivot Range) Methodology.
    Daily CPR  → use previous session's H/L/C
    Weekly CPR → use previous week's H/L/C
    Monthly CPR→ use previous month's H/L/C

    Formulas:
        Pivot = (H + L + C) / 3
        BC    = (H + L) / 2
        TC    = (Pivot − BC) + Pivot   [TC always >= BC]

    CPR width < 0.5% of pivot → Narrow → trending day expected
    CPR width > 0.5% of pivot → Wide   → sideways / reversal likely
    Virgin CPR = price never touched CPR zone (strong magnet level)
    """
    if df is None or len(df) < 5:
        return {}
    try:
        df_t = df.copy()
        df_t.index = pd.to_datetime(df_t.index)

        # ── Daily CPR (previous session) ─────────────────────────────────────
        prev = df_t.iloc[-2]
        h, l, c = float(prev["high"]), float(prev["low"]), float(prev["close"])
        pivot = (h + l + c) / 3
        bc    = (h + l) / 2
        tc    = (pivot - bc) + pivot
        tc, bc = max(tc, bc), min(tc, bc)          # guarantee TC ≥ BC
        width_pct = (tc - bc) / pivot * 100 if pivot > 0 else 0

        # Virgin CPR: did today's candle touch the CPR zone?
        today  = df_t.iloc[-1]
        virgin = not (float(today["high"]) >= bc and float(today["low"]) <= tc)

        # Consecutive virgin sessions (look back up to 6 bars)
        consec_virgin = 0
        for i in range(2, min(8, len(df_t) - 1)):
            sess  = df_t.iloc[-i]
            prev2 = df_t.iloc[-i - 1]
            h2, l2, c2 = float(prev2["high"]), float(prev2["low"]), float(prev2["close"])
            p2  = (h2 + l2 + c2) / 3
            b2  = (h2 + l2) / 2
            t2  = max((p2 - b2) + p2, b2)
            b2  = min((p2 - b2) + p2, b2)
            if not (float(sess["high"]) >= b2 and float(sess["low"]) <= t2):
                consec_virgin += 1
            else:
                break

        # ── PivotBoss S/R levels (Frank Ochoa formula used by KGS) ─────────────
        # R1–R4 resistances, S1–S4 supports — all derived from prev session H/L
        r1 = round(2 * pivot - l,            2)
        r2 = round(pivot + (h - l),          2)
        r3 = round(h + 2 * (pivot - l),      2)
        r4 = round(r3 + (h - l),             2)
        s1 = round(2 * pivot - h,            2)
        s2 = round(pivot - (h - l),          2)
        s3 = round(l - 2 * (h - pivot),      2)
        s4 = round(s3 - (h - l),             2)

        daily = {
            "pivot": round(pivot, 2), "tc": round(tc, 2), "bc": round(bc, 2),
            "width_pct": round(width_pct, 3),
            "narrow": width_pct < 0.5,
            "virgin": virgin, "consec_virgin": consec_virgin,
            # PivotBoss levels
            "r1": r1, "r2": r2, "r3": r3, "r4": r4,
            "s1": s1, "s2": s2, "s3": s3, "s4": s4,
            # Previous Day High/Low
            "pd_high": round(h, 2), "pd_low": round(l, 2),
        }

        # ── Weekly CPR + PivotBoss + Prev Week H/L ────────────────────────────
        weekly_raw = df_t.resample("W").agg(
            {"high": "max", "low": "min", "close": "last"}).dropna()
        weekly: dict = {}
        if len(weekly_raw) >= 2:
            pw   = weekly_raw.iloc[-2]
            wh, wl, wc = float(pw["high"]), float(pw["low"]), float(pw["close"])
            wp   = (wh + wl + wc) / 3
            wbc  = (wh + wl) / 2
            wtc  = (wp - wbc) + wp
            wtc, wbc = max(wtc, wbc), min(wtc, wbc)
            weekly = {
                "pivot": round(wp, 2), "tc": round(wtc, 2), "bc": round(wbc, 2),
                "width_pct": round((wtc - wbc) / wp * 100 if wp > 0 else 0, 3),
                "r1": round(2*wp - wl, 2), "r2": round(wp + (wh-wl), 2),
                "s1": round(2*wp - wh, 2), "s2": round(wp - (wh-wl), 2),
                "pw_high": round(wh, 2), "pw_low": round(wl, 2),
            }

        # ── Monthly CPR + PivotBoss + Prev Month H/L ─────────────────────────
        monthly_raw = df_t.resample("ME").agg(
            {"high": "max", "low": "min", "close": "last"}).dropna()
        monthly: dict = {}
        if len(monthly_raw) >= 2:
            pm   = monthly_raw.iloc[-2]
            mh, ml, mc = float(pm["high"]), float(pm["low"]), float(pm["close"])
            mp   = (mh + ml + mc) / 3
            mbc  = (mh + ml) / 2
            mtc  = (mp - mbc) + mp
            mtc, mbc = max(mtc, mbc), min(mtc, mbc)
            monthly = {
                "pivot": round(mp, 2), "tc": round(mtc, 2), "bc": round(mbc, 2),
                "width_pct": round((mtc - mbc) / mp * 100 if mp > 0 else 0, 3),
                "r1": round(2*mp - ml, 2), "r2": round(mp + (mh-ml), 2),
                "s1": round(2*mp - mh, 2), "s2": round(mp - (mh-ml), 2),
                "pm_high": round(mh, 2), "pm_low": round(ml, 2),
            }

        # ── Price position vs daily CPR ───────────────────────────────────────
        # Use live intraday price if provided (market open), else last candle close
        last_close = float(df_t.iloc[-1]["close"])
        cmp = live_price if live_price > 0 else last_close
        if   cmp > tc:  pos = "above"   # bullish bias
        elif cmp < bc:  pos = "below"   # bearish bias
        else:           pos = "inside"  # indecision / magnet

        # ── Multi-timeframe alignment ─────────────────────────────────────────
        weekly_bullish  = bool(weekly  and cmp > weekly.get("tc",  0))
        monthly_bullish = bool(monthly and cmp > monthly.get("tc", 0))

        # Price vs PivotBoss key levels (nearest R/S)
        above_r1 = cmp > r1
        above_r2 = cmp > r2
        below_s1 = cmp < s1
        below_s2 = cmp < s2

        return {
            "daily": daily, "weekly": weekly, "monthly": monthly,
            "price_position": pos, "cmp": cmp,
            "weekly_bullish": weekly_bullish, "monthly_bullish": monthly_bullish,
            "above_r1": above_r1, "above_r2": above_r2,
            "below_s1": below_s1, "below_s2": below_s2,
        }
    except Exception:
        return {}


def score(df: pd.DataFrame, nifty_ret: float = 0.0, live_price: float = 0.0, is_entry: bool = True) -> dict:
    """
    is_entry=True  → full CPR gate applies (Analyse tab / Screener — deciding whether to buy)
    is_entry=False → CPR shown as info only, no verdict downgrade (Watchlist / Portfolio — monitoring holds)
    """
    l = df.iloc[-1]; p = df.iloc[-2]; r5 = df.tail(5)
    support, resistance = find_sr(df)
    pattern  = candle_pattern(df)
    stage_code, stage_label = detect_stage(df)
    vcp_hit, vcp_label      = detect_vcp(df)
    cpr_data = compute_cpr(df, live_price=live_price)   # ← Gomathi Shankar CPR (uses live price when available)
    details = {}

    _b10 = min(10,len(df)-2); _b5 = min(5,len(df)-2); _b20 = min(20,len(df)-2)
    _c10 = float(df["close"].iloc[-_b10-1]); _c5 = float(df["close"].iloc[-_b5-1])
    _c20 = float(df["close"].iloc[-_b20-1])
    recent_10d = (float(l["close"])-_c10)/max(_c10,0.01)*100
    recent_5d  = (float(l["close"])-_c5) /max(_c5, 0.01)*100
    recent_20d = (float(l["close"])-_c20)/max(_c20,0.01)*100
    recent_bearish = ((recent_10d < -1.5 and recent_5d < 0.5) or recent_20d < -5.0)

    # L1 Trend (40 pts)
    if stage_code == "2":
        if   recent_10d >  0.5: d_stage = 20
        elif recent_10d > -1.5: d_stage = 15
        elif recent_10d > -4.0: d_stage = 8
        else:                   d_stage = 4
    elif "Base Breakout" in stage_label: d_stage = 18
    elif stage_code == "1→2":            d_stage = 12
    elif stage_code == "3":              d_stage = 4
    else:                                d_stage = 0
    details["stage"] = {"label":"Weinstein Stage (30-wk MA)","value":stage_label,
        "score":d_stage,"max":20,"status":("green" if stage_code=="2" else "amber" if stage_code=="1→2" else "red")}

    st_bull = l["st_dir"] == 1
    d_st = 10 if st_bull else 0
    details["supertrend"] = {"label":"Supertrend (10,3)","value":"Bullish" if st_bull else "Bearish",
        "score":d_st,"max":10,"status":"green" if st_bull else "red"}

    e8,e13,e21 = float(l["ema8"]),float(l["ema13"]),float(l["ema21"])
    full_cross = e8>e13>e21; part_cross = e8>e13
    d_ema = 10 if full_cross else (6 if part_cross else 0)
    details["ema"] = {"label":"EMA Crossover 8/13/21","value":f"8:{e8:.0f}  13:{e13:.0f}  21:{e21:.0f}",
        "score":d_ema,"max":10,"status":"green" if full_cross else ("amber" if part_cross else "red")}
    l1 = d_stage + d_st + d_ema

    # L2 Momentum (35 pts)
    rsi = float(l["rsi"])
    if   50<=rsi<=65: d_rsi = 12
    elif 45<=rsi<50 or 65<rsi<=70: d_rsi = 7
    elif rsi > 70:   d_rsi = 2
    else:            d_rsi = 0
    details["rsi"] = {"label":"RSI (14)","value":f"{rsi:.1f}  ({'ideal' if 50<=rsi<=65 else 'overbought' if rsi>70 else 'oversold' if rsi<35 else 'ok'})",
        "score":d_rsi,"max":12,"status":"green" if d_rsi>=7 else ("amber" if d_rsi>0 else "red")}

    mh,pmh = float(l["macd_hist"]),float(p["macd_hist"])
    if mh>0 and mh>pmh: d_macd=10
    elif mh>0:          d_macd=6
    elif mh>pmh:        d_macd=3
    else:               d_macd=0
    details["macd"] = {"label":"MACD Histogram","value":f"{mh:+.3f}  ({'↑ rising' if mh>pmh else '↓ falling'})",
        "score":d_macd,"max":10,"status":"green" if d_macd>=6 else ("amber" if d_macd>0 else "red")}

    adx_val = float(l["adx"])
    price_up = r5["close"].iloc[-1] > r5["close"].iloc[0]
    rsi_up   = r5["rsi"].iloc[-1]   > r5["rsi"].iloc[0]
    aligned  = (price_up == rsi_up)
    if aligned and adx_val>25: d_adx=8
    elif aligned:              d_adx=5
    elif adx_val>25:           d_adx=3
    else:                      d_adx=0
    details["adx"] = {"label":"ADX + Momentum Align","value":f"ADX:{adx_val:.1f}  {'No divergence' if aligned else 'Divergence!'}",
        "score":d_adx,"max":8,"status":"green" if d_adx>=5 else ("amber" if d_adx>0 else "red")}

    stock_3m = float((l["close"]-df["close"].iloc[-63])/df["close"].iloc[-63]*100) if len(df)>=63 else 0.0
    rs_vs_nifty = stock_3m - nifty_ret
    if rs_vs_nifty>5: d_rs=5
    elif rs_vs_nifty>0: d_rs=3
    elif rs_vs_nifty>-5: d_rs=1
    else: d_rs=0
    details["rs"] = {"label":"Rel. Strength vs Nifty 50","value":f"Stock 3M:{stock_3m:+.1f}%  Nifty:{nifty_ret:+.1f}%  RS:{rs_vs_nifty:+.1f}%",
        "score":d_rs,"max":5,"status":"green" if d_rs>=3 else ("amber" if d_rs>0 else "red")}

    if recent_10d>=2.0 and recent_5d>=0.5: d_mom=5
    elif recent_10d>=0.0: d_mom=3
    elif recent_10d>=-2.0: d_mom=1
    else: d_mom=0
    details["momentum"] = {"label":"Recent Price Momentum",
        "value":f"5d:{recent_5d:+.1f}%  10d:{recent_10d:+.1f}%  20d:{recent_20d:+.1f}%"+("  ⚠ Downtrend" if recent_bearish else ""),
        "score":d_mom,"max":5,"status":"green" if d_mom>=3 else ("amber" if d_mom>0 else "red")}
    l2 = d_rsi+d_macd+d_adx+d_rs+d_mom

    # L3 Setup (25 pts)
    vr = float(l["vol_ratio"])
    if vr>=2.0: d_vol=10
    elif vr>=1.5: d_vol=7
    elif vr>=1.2: d_vol=4
    elif vr>=1.0: d_vol=2
    else: d_vol=0
    details["volume"] = {"label":"Volume vs 20-day Avg","value":f"{vr:.2f}x avg  {'(2x breakout!)' if vr>=2 else ''}",
        "score":d_vol,"max":10,"status":"green" if d_vol>=7 else ("amber" if d_vol>0 else "red")}

    broke_r = any(float(l["close"])>r*0.99 and float(p["close"])<r*1.01 for r in resistance[:2])
    above_s = any(float(l["close"])>s for s in support[:2])
    if vcp_hit:   d_vcp=10
    elif broke_r: d_vcp=8
    elif above_s: d_vcp=4
    else:         d_vcp=0
    details["vcp"] = {"label":"VCP / S&R Breakout",
        "value":vcp_label if vcp_hit else ("Breakout confirmed!" if broke_r else ("Above support" if above_s else "No setup")),
        "score":d_vcp,"max":10,"status":"green" if d_vcp>=8 else ("amber" if d_vcp>0 else "red")}

    strong_candles = ["Hammer","Bullish Engulfing","Bullish Marubozu"]
    if pattern in strong_candles: d_candle=5
    elif pattern=="Bullish": d_candle=3
    elif pattern=="Doji":    d_candle=2
    else:                    d_candle=0
    details["candle"] = {"label":"Candlestick Pattern","value":pattern,
        "score":d_candle,"max":5,"status":"green" if d_candle>=3 else ("amber" if d_candle>0 else "red")}
    l3 = d_vol+d_vcp+d_candle

    # ── CPR Filter Gate (Gomathi Shankar — trade confirmation layer) ──────────
    # 4 signal levels: CONFIRM → NEUTRAL → CAUTION → REJECT
    # Acts as a proper filter: REJECT downgrades verdict; CONFIRM adds score.
    cpr_signal = "NO DATA"
    cpr_pts    = 0
    cpr_label  = "CPR: no data"
    cpr_status = "red"
    cpr_reasons: list = []

    if cpr_data:
        pos   = cpr_data.get("price_position", "")
        daily = cpr_data.get("daily", {})
        tc_v  = daily.get("tc", 0)
        bc_v  = daily.get("bc", 0)
        narrow    = daily.get("narrow", False)
        virgin    = daily.get("virgin", False)
        consec_v  = daily.get("consec_virgin", 0)
        wk_bull   = cpr_data.get("weekly_bullish",  False)
        mo_bull   = cpr_data.get("monthly_bullish", False)
        above_r1  = cpr_data.get("above_r1", False)

        # ── Step 1: base signal from price vs daily CPR ───────────────────────
        if pos == "above":
            # Price is above TC — bullish bias
            if narrow and wk_bull:
                cpr_signal = "CONFIRM"      # strongest: narrow + above weekly
                cpr_pts    = 10
                cpr_reasons.append(f"Above TC ₹{tc_v:,.2f}")
                cpr_reasons.append("Narrow CPR ✓ — trending day expected")
                cpr_reasons.append("Above Weekly CPR ✓")
            elif narrow:
                cpr_signal = "CONFIRM"      # narrow CPR alone still confirms
                cpr_pts    = 7
                cpr_reasons.append(f"Above TC ₹{tc_v:,.2f}")
                cpr_reasons.append("Narrow CPR ✓ — trending day expected")
            elif wk_bull:
                cpr_signal = "CONFIRM"      # above both daily & weekly CPR
                cpr_pts    = 6
                cpr_reasons.append(f"Above TC ₹{tc_v:,.2f}")
                cpr_reasons.append("Above Weekly CPR ✓")
            else:
                cpr_signal = "NEUTRAL"      # above daily TC but wide / weekly below
                cpr_pts    = 3
                cpr_reasons.append(f"Above TC ₹{tc_v:,.2f} but wide CPR — caution")

        elif pos == "inside":
            # Price is inside CPR zone — indecision / magnet
            cpr_signal = "CAUTION"
            cpr_pts    = -4
            cpr_reasons.append(f"Inside CPR zone ₹{bc_v:,.2f}–₹{tc_v:,.2f}")
            cpr_reasons.append("Wait for breakout above TC or reject below BC")

        else:
            # Price is below BC — bearish; reject long trades
            cpr_signal = "REJECT"
            cpr_pts    = -12
            cpr_reasons.append(f"Below BC ₹{bc_v:,.2f} — bearish bias")
            cpr_reasons.append("Avoid long entries until price reclaims CPR")

        # ── Step 2: bonus / penalty adjustments ──────────────────────────────
        if virgin and pos == "above":
            cpr_pts += 3
            tag = f"Virgin CPR ✓ ({consec_v} consecutive days)" if consec_v >= 2 else "Virgin CPR ✓"
            cpr_reasons.append(tag)

        if mo_bull and pos == "above":
            cpr_pts += 2
            cpr_reasons.append("Above Monthly CPR ✓ — all 3 TF aligned")

        if above_r1 and pos == "above":
            cpr_pts += 1
            cpr_reasons.append("Above R1 — strong momentum")

        # ── Step 3: determine signal colour ───────────────────────────────────
        cpr_status_map = {
            "CONFIRM": "green", "NEUTRAL": "amber",
            "CAUTION": "amber", "REJECT":  "red", "NO DATA": "red",
        }
        cpr_status = cpr_status_map[cpr_signal]
        cpr_label  = f"[{cpr_signal}] " + "  ·  ".join(cpr_reasons)

    cpr_pts = max(cpr_pts, -12)   # floor
    details["cpr"] = {
        "label": "CPR Filter (KGS)", "value": cpr_label,
        "score": max(cpr_pts, 0), "max": 16, "status": cpr_status,
    }

    # ── Score assembly ────────────────────────────────────────────────────────
    raw = l1 + l2 + l3 + cpr_pts
    if stage_code=="4":   total=min(raw,40); capped=True
    elif stage_code=="3": total=min(raw,50); capped=True
    elif l1<20:           total=min(raw,50); capped=True
    elif l1<30 or recent_bearish: total=min(raw,68); capped=True
    else:                 total=raw; capped=False

    if total>=75:   verdict,vcol = "STRONG BUY", C["green"]
    elif total>=55: verdict,vcol = "WATCHLIST",  C["amber"]
    else:           verdict,vcol = "AVOID",       C["red"]

    # ── CPR hard filter: only applies when evaluating a NEW entry ─────────────
    # For existing holds (is_entry=False), CPR is shown as info but never
    # changes the verdict — swing trades exit via ATR stop / Supertrend, not CPR.
    cpr_downgraded = False
    if is_entry:
        if cpr_signal == "REJECT":
            if verdict == "STRONG BUY":
                verdict, vcol = "WATCHLIST", C["amber"]
                cpr_downgraded = True
            elif verdict == "WATCHLIST":
                verdict, vcol = "AVOID", C["red"]
                cpr_downgraded = True
        elif cpr_signal == "CAUTION" and verdict == "STRONG BUY":
            verdict, vcol = "WATCHLIST", C["amber"]
            cpr_downgraded = True

    atr  = float(l["atr"])
    cmp  = float(l["close"])
    adr  = float(l["adr5"]) if not pd.isna(l.get("adr5",float("nan"))) else atr
    mdr  = float(l["mdr"])  if not pd.isna(l.get("mdr", float("nan"))) else atr*1.5

    if verdict=="STRONG BUY":
        near_s = sorted([s for s in support if s<cmp*0.998], reverse=True)
        entry  = round(near_s[0]*1.002,2) if near_s and (cmp-near_s[0])/cmp<0.03 else round(cmp-0.5*adr,2)
        elabel = "Entry (limit)"
    elif verdict=="WATCHLIST":
        triggers = sorted([r for r in resistance if r>cmp*1.003])
        entry  = triggers[0] if triggers else round(cmp*1.02,2)
        elabel = "Trigger (breakout)"
    else:
        entry  = round(cmp-0.5*adr,2); elabel="Entry (N/A)"

    sl = round(entry-0.5*adr,2)
    t1 = round(entry+0.75*mdr,2)
    t2 = round(entry+1.00*mdr,2)
    t3 = round(entry+1.50*mdr,2)
    rr = round((t1-entry)/max(entry-sl,0.01),2)

    bb_pct = float((l["close"]-l["bb_lower"])/max(l["bb_upper"]-l["bb_lower"],0.01)*100)
    return {
        "total":total,"raw":raw,"capped":capped,"l1":l1,"l2":l2,"l3":l3,
        "verdict":verdict,"vcol":vcol,"details":details,
        "support":support,"resistance":resistance,
        "stage":stage_code,"stage_label":stage_label,
        "vcp":vcp_hit,"vcp_label":vcp_label,"cmp":cmp,
        "trade":{"entry":entry,"entry_label":elabel,"sl":sl,"t1":t1,"t2":t2,"t3":t3,"rr":rr,
                 "atr":round(atr,2),"adr":round(adr,2),"mdr":round(mdr,2),
                 "scale1":round(entry*1.03,2),"scale2":round(entry*1.05,2),"scale3":round(entry*1.07,2)},
        "bb_pct":round(bb_pct,1),"rsi":rsi,"adx":adx_val,
        "rs_vs_nifty":round(rs_vs_nifty,1),"vol_ratio":vr,
        "bb_width":round(float((l["bb_upper"]-l["bb_lower"])/l["bb_mid"]),4),
        "cpr": cpr_data, "cpr_pts": cpr_pts,
        "cpr_signal": cpr_signal, "cpr_downgraded": cpr_downgraded,
        "cpr_reasons": cpr_reasons,
    }

# ── CHART ──────────────────────────────────────────────────────────────────────
def make_chart(df: pd.DataFrame, sd: dict, symbol: str) -> go.Figure:
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                        row_heights=[0.58,0.21,0.21], vertical_spacing=0.02)
    bg, pbg = C["bg"], C["card"]

    fig.add_trace(go.Candlestick(x=df.index, open=df["open"], high=df["high"],
        low=df["low"], close=df["close"], name="Price",
        increasing_line_color=C["green"], decreasing_line_color=C["red"],
        increasing_fillcolor=hex_rgba(C["green"],0.85),
        decreasing_fillcolor=hex_rgba(C["red"],0.85)), row=1, col=1)

    for col_n, color, name in [("ema8",C["blue"],"EMA 8"),("ema13",C["amber"],"EMA 13"),
                                ("ema21",C["green"],"EMA 21"),("ema50",C["purple"],"EMA 50")]:
        if col_n in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df[col_n],
                line=dict(color=color,width=1.2), name=name, opacity=0.85), row=1, col=1)

    if "ma150" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["ma150"],
            line=dict(color="rgba(255,255,255,0.6)",width=2.0,dash="dot"),
            name="30W MA"), row=1, col=1)

    bull_df = df[df["st_dir"]==1]; bear_df = df[df["st_dir"]==-1]
    fig.add_trace(go.Scatter(x=bull_df.index, y=bull_df["st_val"], mode="markers",
        marker=dict(color=C["green"],size=3), name="ST Bull"), row=1, col=1)
    fig.add_trace(go.Scatter(x=bear_df.index, y=bear_df["st_val"], mode="markers",
        marker=dict(color=C["red"],size=3), name="ST Bear"), row=1, col=1)

    for s in sd["support"][:2]:
        fig.add_hline(y=s, line=dict(color=hex_rgba(C["green"],0.4),width=1,dash="dash"),
            annotation_text=f"S ₹{s:.0f}", annotation_font=dict(color=C["green"],size=10), row=1,col=1)
    for r in sd["resistance"][:2]:
        fig.add_hline(y=r, line=dict(color=hex_rgba(C["red"],0.4),width=1,dash="dash"),
            annotation_text=f"R ₹{r:.0f}", annotation_font=dict(color=C["red"],size=10), row=1,col=1)

    # ── CPR + PivotBoss Levels (KGS / Gomathi Shankar) ───────────────────────
    _cpr = sd.get("cpr", {})
    if _cpr:
        _dcpr = _cpr.get("daily", {})
        if _dcpr:
            _tc  = _dcpr.get("tc");  _bc = _dcpr.get("bc");  _pp = _dcpr.get("pivot")
            _vc  = " ★" if _dcpr.get("virgin") else ""
            # CPR zone — green TC, red BC, yellow pivot
            if _tc:
                fig.add_hline(y=_tc, line=dict(color="rgba(80,220,130,0.80)", width=1.8, dash="dashdot"),
                    annotation_text=f"D-TC ₹{_tc:.0f}{_vc}", annotation_font=dict(color="#50dc82", size=10), row=1, col=1)
            if _pp:
                fig.add_hline(y=_pp, line=dict(color="rgba(255,210,50,0.60)", width=1.2, dash="dot"),
                    annotation_text=f"Pivot ₹{_pp:.0f}", annotation_font=dict(color="#ffd232", size=9), row=1, col=1)
            if _bc:
                fig.add_hline(y=_bc, line=dict(color="rgba(255,100,100,0.75)", width=1.8, dash="dashdot"),
                    annotation_text=f"D-BC ₹{_bc:.0f}", annotation_font=dict(color="#ff6464", size=10), row=1, col=1)
            # PivotBoss Resistance R1–R4 (green dots gradient)
            for _lbl, _val, _op in [("R1", _dcpr.get("r1"), 0.65),
                                     ("R2", _dcpr.get("r2"), 0.50),
                                     ("R3", _dcpr.get("r3"), 0.38),
                                     ("R4", _dcpr.get("r4"), 0.25)]:
                if _val:
                    fig.add_hline(y=_val, line=dict(color=f"rgba(0,200,80,{_op})", width=1.0, dash="dot"),
                        annotation_text=f"{_lbl} ₹{_val:.0f}", annotation_font=dict(color="#00c850", size=9), row=1, col=1)
            # PivotBoss Support S1–S4 (red dots gradient)
            for _lbl, _val, _op in [("S1", _dcpr.get("s1"), 0.65),
                                     ("S2", _dcpr.get("s2"), 0.50),
                                     ("S3", _dcpr.get("s3"), 0.38),
                                     ("S4", _dcpr.get("s4"), 0.25)]:
                if _val:
                    fig.add_hline(y=_val, line=dict(color=f"rgba(255,60,60,{_op})", width=1.0, dash="dot"),
                        annotation_text=f"{_lbl} ₹{_val:.0f}", annotation_font=dict(color="#ff3c3c", size=9), row=1, col=1)
            # Previous Day High/Low (white dashed)
            _pdh = _dcpr.get("pd_high"); _pdl = _dcpr.get("pd_low")
            if _pdh:
                fig.add_hline(y=_pdh, line=dict(color="rgba(255,255,255,0.30)", width=1.0, dash="dash"),
                    annotation_text=f"PDH ₹{_pdh:.0f}", annotation_font=dict(color="#aaaaaa", size=9), row=1, col=1)
            if _pdl:
                fig.add_hline(y=_pdl, line=dict(color="rgba(255,255,255,0.20)", width=1.0, dash="dash"),
                    annotation_text=f"PDL ₹{_pdl:.0f}", annotation_font=dict(color="#aaaaaa", size=9), row=1, col=1)

        # Weekly CPR + Prev Week H/L (blue tones)
        _wcpr = _cpr.get("weekly", {})
        if _wcpr:
            _wtc, _wbc = _wcpr.get("tc"), _wcpr.get("bc")
            if _wtc:
                fig.add_hline(y=_wtc, line=dict(color="rgba(100,180,255,0.55)", width=2.0, dash="dash"),
                    annotation_text=f"W-TC ₹{_wtc:.0f}", annotation_font=dict(color="#64b4ff", size=10), row=1, col=1)
            if _wbc:
                fig.add_hline(y=_wbc, line=dict(color="rgba(100,180,255,0.38)", width=1.5, dash="dash"),
                    annotation_text=f"W-BC ₹{_wbc:.0f}", annotation_font=dict(color="#64b4ff", size=9), row=1, col=1)
            _pwh = _wcpr.get("pw_high"); _pwl = _wcpr.get("pw_low")
            if _pwh:
                fig.add_hline(y=_pwh, line=dict(color="rgba(100,180,255,0.25)", width=1.0, dash="longdash"),
                    annotation_text=f"PWH ₹{_pwh:.0f}", annotation_font=dict(color="#64b4ff", size=9), row=1, col=1)
            if _pwl:
                fig.add_hline(y=_pwl, line=dict(color="rgba(100,180,255,0.18)", width=1.0, dash="longdash"),
                    annotation_text=f"PWL ₹{_pwl:.0f}", annotation_font=dict(color="#64b4ff", size=9), row=1, col=1)

        # Monthly CPR + Prev Month H/L (purple tones)
        _mcpr = _cpr.get("monthly", {})
        if _mcpr:
            _mtc, _mbc = _mcpr.get("tc"), _mcpr.get("bc")
            if _mtc:
                fig.add_hline(y=_mtc, line=dict(color="rgba(200,120,255,0.50)", width=2.2, dash="dash"),
                    annotation_text=f"M-TC ₹{_mtc:.0f}", annotation_font=dict(color="#c878ff", size=10), row=1, col=1)
            if _mbc:
                fig.add_hline(y=_mbc, line=dict(color="rgba(200,120,255,0.35)", width=1.6, dash="dash"),
                    annotation_text=f"M-BC ₹{_mbc:.0f}", annotation_font=dict(color="#c878ff", size=9), row=1, col=1)
            _pmh = _mcpr.get("pm_high"); _pml = _mcpr.get("pm_low")
            if _pmh:
                fig.add_hline(y=_pmh, line=dict(color="rgba(200,120,255,0.22)", width=1.0, dash="longdash"),
                    annotation_text=f"PMH ₹{_pmh:.0f}", annotation_font=dict(color="#c878ff", size=9), row=1, col=1)
            if _pml:
                fig.add_hline(y=_pml, line=dict(color="rgba(200,120,255,0.15)", width=1.0, dash="longdash"),
                    annotation_text=f"PML ₹{_pml:.0f}", annotation_font=dict(color="#c878ff", size=9), row=1, col=1)

    tr = sd["trade"]
    fig.add_hline(y=tr["entry"],line=dict(color=hex_rgba(C["blue"],0.8),width=1.8),
        annotation_text=f"Entry ₹{tr['entry']:.0f}",annotation_font=dict(color=C["blue"],size=10),row=1,col=1)
    fig.add_hline(y=tr["sl"],line=dict(color=hex_rgba(C["red"],0.7),width=1.5,dash="dot"),
        annotation_text=f"SL ₹{tr['sl']:.0f}",annotation_font=dict(color=C["red"],size=10),row=1,col=1)
    fig.add_hline(y=tr["t1"],line=dict(color=hex_rgba(C["green"],0.5),width=1.2,dash="dot"),
        annotation_text=f"T1 ₹{tr['t1']:.0f}",annotation_font=dict(color=C["green"],size=10),row=1,col=1)
    fig.add_hline(y=tr["t2"],line=dict(color=hex_rgba(C["green"],0.7),width=1.5,dash="dot"),
        annotation_text=f"T2 ₹{tr['t2']:.0f}",annotation_font=dict(color=C["green"],size=10),row=1,col=1)
    fig.add_hline(y=tr["t3"],line=dict(color=hex_rgba(C["green"],0.9),width=1.8,dash="dash"),
        annotation_text=f"T3 ₹{tr['t3']:.0f}",annotation_font=dict(color=C["green"],size=10),row=1,col=1)

    fig.add_trace(go.Bar(x=df.index, y=df["macd_hist"],
        marker_color=[C["green"] if v>=0 else C["red"] for v in df["macd_hist"]],
        name="MACD Hist", opacity=0.75), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index,y=df["macd"],line=dict(color=C["blue"],width=1.2),name="MACD"),row=2,col=1)
    fig.add_trace(go.Scatter(x=df.index,y=df["macd_sig"],line=dict(color=C["amber"],width=1.2,dash="dot"),name="Signal"),row=2,col=1)

    fig.add_trace(go.Scatter(x=df.index,y=df["rsi"],line=dict(color=C["purple"],width=1.5),name="RSI"),row=3,col=1)
    for lvl,col in [(70,C["red"]),(30,C["green"])]:
        fig.add_hline(y=lvl,line=dict(color=hex_rgba(col,0.3),width=1,dash="dash"),row=3,col=1)
    fig.add_hline(y=50,line=dict(color="rgba(255,255,255,0.08)",width=1,dash="dot"),row=3,col=1)

    fig.update_layout(paper_bgcolor=bg,plot_bgcolor=pbg,
        font=dict(color=C["muted"],family="JetBrains Mono",size=11),
        xaxis_rangeslider_visible=False, showlegend=True,
        legend=dict(bgcolor=hex_rgba(C["card"],0.9),bordercolor=C["border"],borderwidth=1,font=dict(size=10)),
        height=680, margin=dict(l=60,r=100,t=10,b=20))
    for i in range(1,4):
        fig.update_xaxes(gridcolor=hex_rgba(C["border"],0.8),showgrid=True,zeroline=False,row=i,col=1)
        fig.update_yaxes(gridcolor=hex_rgba(C["border"],0.8),showgrid=True,zeroline=False,row=i,col=1)
    fig.update_yaxes(title_text="Price (₹)",row=1,col=1)
    fig.update_yaxes(title_text="MACD",row=2,col=1)
    fig.update_yaxes(title_text="RSI",row=3,col=1,range=[0,100])
    return fig

def make_gauge(total: int, verdict: str, vcol: str) -> go.Figure:
    fig = go.Figure(go.Indicator(mode="gauge+number", value=total,
        domain={"x":[0,1],"y":[0,1]},
        title={"text":verdict,"font":{"size":17,"color":vcol,"family":"DM Sans"}},
        number={"font":{"size":54,"color":C["text"],"family":"JetBrains Mono"}},
        gauge={"axis":{"range":[0,100],"tickwidth":1,"tickcolor":C["border"],
                       "tickfont":{"color":C["muted"],"size":10}},
               "bar":{"color":vcol,"thickness":0.24},"bgcolor":C["card"],"borderwidth":0,
               "steps":[{"range":[0,55],"color":hex_rgba(C["red"],0.08)},
                        {"range":[55,75],"color":hex_rgba(C["amber"],0.08)},
                        {"range":[75,100],"color":hex_rgba(C["green"],0.08)}],
               "threshold":{"line":{"color":vcol,"width":3},"thickness":0.75,"value":total}}))
    fig.update_layout(paper_bgcolor=C["bg"],font={"color":C["muted"]},
                      height=240,margin=dict(l=20,r=20,t=30,b=5))
    return fig

# ── HTML HELPERS ───────────────────────────────────────────────────────────────
def bar_html(label, sv, mv, color):
    pct = int(sv/mv*100)
    return (f"<div style='margin-bottom:11px'>"
            f"<div style='display:flex;justify-content:space-between;margin-bottom:4px'>"
            f"<span style='font-family:DM Sans,sans-serif;font-size:13px;color:{C['muted']}'>{label}</span>"
            f"<span style='font-family:JetBrains Mono,monospace;font-size:12px;color:{C['text']}'>{sv}"
            f"<span style='color:{C['dim']}'>/{mv}</span></span></div>"
            f"<div style='background:{C['border']};border-radius:4px;height:7px;overflow:hidden'>"
            f"<div style='background:{color};width:{pct}%;height:100%;border-radius:4px'></div></div></div>")

def pill_html(label, value, sv, mv, status):
    sc = {"green":C["green"],"red":C["red"],"amber":C["amber"]}.get(status,C["muted"])
    bg = {"green":hex_rgba(C["green"],0.08),"red":hex_rgba(C["red"],0.08),"amber":hex_rgba(C["amber"],0.08)}.get(status,"transparent")
    return (f"<div style='background:{bg};border:1px solid {sc}30;border-radius:8px;padding:9px 13px;margin-bottom:7px'>"
            f"<div style='display:flex;justify-content:space-between;align-items:center'>"
            f"<div><span style='font-family:DM Sans,sans-serif;font-size:11px;color:{C['muted']}'>{label}</span><br>"
            f"<span style='font-family:JetBrains Mono,monospace;font-size:12px;color:{sc}'>{value}</span></div>"
            f"<span style='font-family:JetBrains Mono,monospace;font-size:11px;color:{C['dim']}'>{sv}/{mv}</span>"
            f"</div></div>")

def kpi_row(label, value, color=None):
    c = color or C["text"]
    return (f"<div style='display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid {C['border']}'>"
            f"<span style='font-family:DM Sans,sans-serif;font-size:13px;color:{C['muted']}'>{label}</span>"
            f"<span style='font-family:JetBrains Mono,monospace;font-size:13px;color:{c}'>{value}</span></div>")

# ── STOCK UNIVERSES ────────────────────────────────────────────────────────────
NIFTY50 = ["RELIANCE","TCS","HDFCBANK","INFY","ICICIBANK","HINDUNILVR","ITC","SBIN",
    "BHARTIARTL","KOTAKBANK","LT","AXISBANK","ASIANPAINT","MARUTI","TITAN","NESTLEIND",
    "WIPRO","HCLTECH","ULTRACEMCO","BAJFINANCE","BAJAJFINSV","TECHM","SUNPHARMA","ONGC",
    "NTPC","POWERGRID","COALINDIA","TATAMOTORS","JSWSTEEL","TATASTEEL","ADANIENT",
    "ADANIPORTS","DRREDDY","DIVISLAB","CIPLA","APOLLOHOSP","BPCL","GRASIM","HEROMOTOCO",
    "M&M","EICHERMOT","BRITANNIA","TATACONSUM","HINDALCO","VEDL","SBILIFE","HDFCLIFE",
    "INDUSINDBK","BAJAJ-AUTO","UPL"]

NEXT50 = ["ADANIGREEN","ADANIPOWER","AMBUJACEM","BANDHANBNK","BANKBARODA","BEL","BERGEPAINT",
    "BOSCHLTD","CANBK","COLPAL","CONCOR","DABUR","DMART","FEDERALBNK","GAIL","GODREJCP",
    "GODREJPROP","HAVELLS","ICICIGI","ICICIPRULI","INDHOTEL","INDUSTOWER","IRCTC","JUBLFOOD",
    "LUPIN","MARICO","MOTHERSON","MPHASIS","NAUKRI","OBEROIRLTY","OFSS","PAGEIND",
    "PIDILITIND","PNB","RECLTD","SAIL","SHREECEM","SIEMENS","SRF","TATACOMM","TATAELXSI",
    "TATAPOWER","TORNTPHARM","TRENT","UNIONBANK","ZOMATO","POLYCAB","MUTHOOTFIN",
    "PERSISTENT","CHOLAFIN"]

MIDCAP = list(dict.fromkeys([
    # Nifty Midcap 150 — full list (auto-deduped)
    "ABFRL","ASTRAL","AUBANK","AUROPHARMA","BALKRISIND","BATAINDIA","BIOCON","COFORGE",
    "CROMPTON","CUMMINSIND","DEEPAKNTR","EMAMILTD","ESCORTS","GLENMARK","GNFC","HONAUT",
    "IGL","IRFC","KANSAINER","LTTS","MAXHEALTH","MFSL","NATIONALUM","PIIND","PFC","RBLBANK",
    "SJVN","SUNDARMFIN","SUPREMEIND","SYNGENE","TORNTPOWER","VOLTAS","ZYDUSLIFE","ABCAPITAL",
    "ALKEM","CDSL","CRISIL","GLAXO","IDFCFIRSTB","INDIAMART","KPITTECH","LAURUSLABS",
    "TATAELXSI","TRENT","POLYCAB","CHOLAFIN","PERSISTENT","MPHASIS","PAGEIND","PVRINOX",
    "DIXON","NAUKRI","DMART","IRCTC","OBEROIRLTY","GODREJPROP","PRESTIGE","PHOENIXLTD",
    "METROPOLIS","LALPATHLAB","MANKIND","SUNDRMFAST","APOLLOTYRE","CEAT","MRF",
    "WHIRLPOOL","BLUESTARCO","ORIENTELEC","ABBOTINDIA","TORNTPHARM","LUPIN",
    "JUBLFOOD","INDIGO","GMRINFRA","INDUSTOWER","DLF",
    "RVNL","HAL","BEL","BHEL","COCHINSHIP","MAZAGON","GRINDWELL","ABB","SIEMENS",
    "RECLTD","NHPC","TATAPOWER","ADANIGREEN","NTPC",
    "KAJARIACER","CERA","SUNTV","ZEEL","NETWORK18","TV18BRDCST",
    "MASTEK","INTELLECT",
    "KARURVSYS","CITYUNIONB","DCBBANK","EQUITASBNK","UJJIVANSFB",
    "JKCEMENT","RAMCOCEM","HEIDELBERG","BIRLAMONEY","AIAENG","THERMAX",
]))

SMALLCAP = list(dict.fromkeys([
    # Nifty Smallcap 100 + additional quality names
    "AJANTPHARM","APLLTD","CAMS","CANFINHOME","CHAMBLFERT","CLEAN","FINEORG",
    "GALAXYSURF","GRINDWELL","GSPL","HAPPSTMNDS","HFCL","INDIGOPNTS","JKCEMENT","JKPAPER",
    "KPRMILL","LATENTVIEW","METROBRAND","NAVINFLUOR","NEWGEN","NOCIL","POLYMED","PRINCEPIPE",
    "ROUTE","SAFARI","SHYAMMETL","SOLARINDS","SUMICHEM","SUPPETRO","THYROCARE","TIMETECHNO",
    "VAIBHAVGBL","WELSPUNLIV","ZYDUSWELL","PGHL","OLECTRA","SPANDANA","SEQUENT","SUPRAJIT",
    "SYMPHONY","VSTIND","VGUARD","WESTLIFE","METROPOLIS","AAVAS","ERIS","RAINBOW","RVNL",
    "IREDA","INOXWIND","SUZLON","RITES","IRCON","NBCC","HUDCO","RAILTEL",
    "ANGELONE","CDSL","BSE","MCX","NSDL","CAMSSBK",
    "APTUS","HOMEFIRST","AAVAS","CREDITACC","SPANDANA","FUSION",
    "BIKAJI","DEVYANI","SAPPHIRE","DODLA","HATSUN","PARAG","CCIL",
    "APLAPOLLO","RATNAMANI","JINDALSAW","WELSPUNIND","TEXRAIL",
    "LXCHEM","TANLA","DATAMATICS","MPHASIS","RATEGAIN","ZENSAR",
    "EQUITASBNK","UJJIVANSFB","ESAFSFB","SURYODAY","FINCARE",
    "PNCINFRA","KNR","ASHOKA","HG INFRA","GPPL","CONCOR",
    "VIPIND","CAMPUS","BATAINDIA","RELAXO","LIBERTY","LEHAR",
    "MEDPLUS","SUVENPHAR","NEULANDLAB","GRANULES","SOLARA",
    "SWSOLAR","WEBSOL","WAAREE","PREMIER","GOLDENKA",
    "NUVOCO","PRSMJOHNSN","SOMANYCERA","ORIENTBELL",
]))

SECTOR_MAP = {
    # Nifty 50
    "RELIANCE":"Energy","TCS":"IT","HDFCBANK":"Banking","INFY":"IT","ICICIBANK":"Banking",
    "HINDUNILVR":"FMCG","ITC":"FMCG","SBIN":"Banking","BHARTIARTL":"Telecom","KOTAKBANK":"Banking",
    "LT":"Infrastructure","AXISBANK":"Banking","ASIANPAINT":"Paints","MARUTI":"Auto","TITAN":"Consumer",
    "NESTLEIND":"FMCG","WIPRO":"IT","HCLTECH":"IT","ULTRACEMCO":"Cement","BAJFINANCE":"Finance",
    "BAJAJFINSV":"Finance","TECHM":"IT","SUNPHARMA":"Pharma","ONGC":"Energy","NTPC":"Power",
    "POWERGRID":"Power","COALINDIA":"Mining","TATAMOTORS":"Auto","JSWSTEEL":"Steel","TATASTEEL":"Steel",
    "ADANIENT":"Diversified","ADANIPORTS":"Infrastructure","DRREDDY":"Pharma","DIVISLAB":"Pharma",
    "CIPLA":"Pharma","APOLLOHOSP":"Healthcare","BPCL":"Energy","GRASIM":"Diversified",
    "HEROMOTOCO":"Auto","M&M":"Auto","EICHERMOT":"Auto","BRITANNIA":"FMCG","TATACONSUM":"FMCG",
    "HINDALCO":"Metals","VEDL":"Metals","SBILIFE":"Insurance","HDFCLIFE":"Insurance",
    "INDUSINDBK":"Banking","BAJAJ-AUTO":"Auto","UPL":"Chemicals",
    # Next 50
    "ADANIGREEN":"Power","ADANIPOWER":"Power","AMBUJACEM":"Cement","BANDHANBNK":"Banking",
    "BANKBARODA":"Banking","BEL":"Defence","BERGEPAINT":"Paints","BOSCHLTD":"Auto",
    "CANBK":"Banking","COLPAL":"FMCG","CONCOR":"Logistics","DABUR":"FMCG","DMART":"Retail",
    "FEDERALBNK":"Banking","GAIL":"Energy","GODREJCP":"FMCG","GODREJPROP":"Real Estate",
    "HAVELLS":"Consumer","ICICIGI":"Insurance","ICICIPRULI":"Insurance","INDHOTEL":"Hotels",
    "INDUSTOWER":"Telecom","IRCTC":"Tourism","JUBLFOOD":"QSR","LUPIN":"Pharma","MARICO":"FMCG",
    "MOTHERSON":"Auto","MPHASIS":"IT","NAUKRI":"Tech","OBEROIRLTY":"Real Estate","OFSS":"IT",
    "PAGEIND":"Consumer","PIDILITIND":"Chemicals","PNB":"Banking","RECLTD":"Finance","SAIL":"Steel",
    "SHREECEM":"Cement","SIEMENS":"Industrials","SRF":"Chemicals","TATACOMM":"Telecom",
    "TATAELXSI":"IT","TATAPOWER":"Power","TORNTPHARM":"Pharma","TRENT":"Retail",
    "UNIONBANK":"Banking","ZOMATO":"Tech","POLYCAB":"Cables","MUTHOOTFIN":"Finance",
    "PERSISTENT":"IT","CHOLAFIN":"Finance",
    # Midcap
    "ABFRL":"Retail","ASTRAL":"Pipes","AUBANK":"Banking","AUROPHARMA":"Pharma",
    "BALKRISIND":"Tyres","BATAINDIA":"Consumer","BIOCON":"Pharma","COFORGE":"IT",
    "CROMPTON":"Consumer","CUMMINSIND":"Industrials","DEEPAKNTR":"Chemicals","EMAMILTD":"FMCG",
    "ESCORTS":"Auto","GLENMARK":"Pharma","GNFC":"Chemicals","HONAUT":"Industrials",
    "IGL":"Energy","IRFC":"Finance","KANSAINER":"Paints","LTTS":"IT","MAXHEALTH":"Healthcare",
    "MFSL":"Finance","NATIONALUM":"Metals","PIIND":"Chemicals","PFC":"Finance","RBLBANK":"Banking",
    "SJVN":"Power","SUNDARMFIN":"Finance","SUPREMEIND":"Plastics","SYNGENE":"Pharma",
    "TORNTPOWER":"Power","VOLTAS":"Consumer","ZYDUSLIFE":"Pharma","ABCAPITAL":"Finance",
    "ALKEM":"Pharma","CDSL":"Finance","CRISIL":"Finance","GLAXO":"Pharma","IDFCFIRSTB":"Banking",
    "INDIAMART":"Tech","KPITTECH":"IT","LAURUSLABS":"Pharma","PVRINOX":"Entertainment",
    "DIXON":"Electronics","HAL":"Defence","ABB":"Industrials","BHEL":"Industrials",
    "RVNL":"Infrastructure","IREDA":"Finance","INOXWIND":"Renewable","SUZLON":"Renewable",
    "RECLTD":"Finance","NHPC":"Power","ADANIGREEN":"Power","PRESTIGE":"Real Estate",
    "DLF":"Real Estate","PHOENIXLTD":"Real Estate","METROPOLIS":"Healthcare",
    "LALPATHLAB":"Healthcare","MANKIND":"Pharma","APOLLOTYRE":"Tyres","CEAT":"Tyres","MRF":"Tyres",
    "JUBLFOOD":"QSR","INDIGO":"Aviation","GMRINFRA":"Infrastructure",
    # Smallcap
    "AJANTPHARM":"Pharma","APLLTD":"Pharma","CAMS":"Finance","CANFINHOME":"Finance",
    "CHAMBLFERT":"Chemicals","FINEORG":"Chemicals","GALAXYSURF":"Chemicals","GRINDWELL":"Industrials",
    "GSPL":"Energy","HAPPSTMNDS":"IT","HFCL":"Telecom","INDIGOPNTS":"Paints","JKCEMENT":"Cement",
    "JKPAPER":"Paper","KPRMILL":"Textiles","LATENTVIEW":"IT","NAVINFLUOR":"Chemicals",
    "NEWGEN":"IT","NOCIL":"Chemicals","POLYMED":"Healthcare","PRINCEPIPE":"Pipes","ROUTE":"IT",
    "SAFARI":"Consumer","SOLARINDS":"Chemicals","SUMICHEM":"Chemicals","THYROCARE":"Healthcare",
    "VAIBHAVGBL":"Consumer","WELSPUNLIV":"Textiles","ZYDUSWELL":"FMCG","OLECTRA":"Auto",
    "SUPRAJIT":"Auto","SYMPHONY":"Consumer","VGUARD":"Consumer","WESTLIFE":"QSR",
    "AAVAS":"Finance","ERIS":"Pharma","RAINBOW":"Healthcare","ANGELONE":"Finance",
    "MCX":"Finance","BSE":"Finance","APTUS":"Finance","BIKAJI":"FMCG",
    "GRANULES":"Pharma","NEULANDLAB":"Pharma","SOLARA":"Pharma","TANLA":"Tech",
    "ZENSAR":"IT","RATEGAIN":"IT","DATAMATICS":"IT",
}

SCREENER_LISTS = {
    "Nifty 50":         list(dict.fromkeys(NIFTY50)),
    "Nifty Next 50":    list(dict.fromkeys(NEXT50)),
    "Nifty Midcap 150": list(dict.fromkeys(MIDCAP)),
    "Nifty Smallcap":   list(dict.fromkeys(SMALLCAP)),
    "Nifty 100":        list(dict.fromkeys(NIFTY50+NEXT50)),
    "All 300+":         list(dict.fromkeys(NIFTY50+NEXT50+MIDCAP+SMALLCAP)),
}

# ── WATCHLIST STORAGE ──────────────────────────────────────────────────────────
# Priority: 1) Supabase (persistent, cloud-safe)  2) Local JSON  3) session_state
WATCHLIST_FILE = os.path.join(os.path.dirname(__file__), "watchlist.json")

def _get_supabase():
    """Return a Supabase client if credentials are configured, else None."""
    try:
        url = st.secrets.get("SUPABASE_URL", "")
        key = st.secrets.get("SUPABASE_KEY", "")
        if not url or not key:
            return None
        from supabase import create_client
        return create_client(url, key)
    except Exception:
        return None

def load_watchlist() -> list:
    sb = _get_supabase()
    if sb:
        try:
            rows = sb.table("watchlist").select("symbol,company").execute().data
            return rows if rows else []
        except Exception:
            pass
    try:
        with open(WATCHLIST_FILE, "r") as f:
            return json.load(f)
    except Exception:
        pass
    return st.session_state.get("_watchlist", [])

def save_watchlist(wl: list):
    """Save full watchlist — used only for local JSON / session_state paths."""
    try:
        with open(WATCHLIST_FILE, "w") as f:
            json.dump(wl, f, indent=2)
    except Exception:
        st.session_state["_watchlist"] = wl

def add_to_watchlist(symbol: str, company: str) -> bool:
    sb = _get_supabase()
    if sb:
        try:
            existing = sb.table("watchlist").select("symbol").eq("symbol", symbol).execute().data
            if existing:
                return False
            sb.table("watchlist").insert({"symbol": symbol, "company": company}).execute()
            return True
        except Exception:
            pass
    # fallback: local file / session_state
    wl = load_watchlist()
    if not any(w["symbol"] == symbol for w in wl):
        wl.append({"symbol": symbol, "company": company})
        save_watchlist(wl)
        return True
    return False

def remove_from_watchlist(symbol: str):
    sb = _get_supabase()
    if sb:
        try:
            sb.table("watchlist").delete().eq("symbol", symbol).execute()
            return
        except Exception:
            pass
    save_watchlist([w for w in load_watchlist() if w["symbol"] != symbol])

# ── HOLDINGS STORAGE ───────────────────────────────────────────────────────────
# Supabase table: holdings (symbol, company, entry_price, qty, entry_date)
# Fallback: holdings.json
HOLDINGS_FILE = os.path.join(os.path.dirname(__file__), "holdings.json")

def load_holdings() -> list:
    sb = _get_supabase()
    if sb:
        try:
            rows = sb.table("holdings").select("*").execute().data
            return rows if rows else []
        except Exception:
            pass
    try:
        with open(HOLDINGS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        pass
    return st.session_state.get("_holdings", [])

def save_holdings(hl: list):
    try:
        with open(HOLDINGS_FILE, "w") as f:
            json.dump(hl, f, indent=2)
    except Exception:
        st.session_state["_holdings"] = hl

def add_holding(symbol: str, company: str, entry_price: float, qty: int) -> bool:
    sb = _get_supabase()
    entry_date = datetime.now().strftime("%Y-%m-%d")
    if sb:
        try:
            existing = sb.table("holdings").select("symbol").eq("symbol", symbol).execute().data
            if existing:
                # Update entry price and qty if re-adding
                sb.table("holdings").update({
                    "entry_price": entry_price, "qty": qty, "entry_date": entry_date
                }).eq("symbol", symbol).execute()
                return True
            sb.table("holdings").insert({
                "symbol": symbol, "company": company,
                "entry_price": entry_price, "qty": qty, "entry_date": entry_date
            }).execute()
            return True
        except Exception:
            pass
    hl = load_holdings()
    hl = [h for h in hl if h["symbol"] != symbol]   # replace if exists
    hl.append({"symbol": symbol, "company": company,
               "entry_price": entry_price, "qty": qty, "entry_date": entry_date})
    save_holdings(hl)
    return True

def remove_holding(symbol: str):
    sb = _get_supabase()
    if sb:
        try:
            sb.table("holdings").delete().eq("symbol", symbol).execute()
            return
        except Exception:
            pass
    save_holdings([h for h in load_holdings() if h["symbol"] != symbol])

# ── HOLD / EXIT SIGNAL ENGINE ──────────────────────────────────────────────────
def get_hold_exit_signal(sd: dict, entry_price: float) -> dict:
    """
    Swing trading exit logic — priority order:
    1. SL breached (ATR stop)      → EXIT immediately
    2. Supertrend flipped bearish  → EXIT immediately
    3. Stage 4 / 3 detected        → EXIT / CAUTION
    4. T2 hit                      → HOLD, trail stop
    5. T1 hit                      → BOOK PARTIAL (70%), make SL free
    6. Score < 45                  → CAUTION, watch closely
    7. Everything intact           → HOLD
    """
    cmp        = sd.get("cmp", entry_price)
    tr         = sd.get("trade", {})
    t1         = tr.get("t1", 0)
    t2         = tr.get("t2", 0)
    t3         = tr.get("t3", 0)
    stage      = sd.get("stage", "")
    total      = sd.get("total", 0)
    st_detail  = sd.get("details", {}).get("supertrend", {})
    st_bull    = st_detail.get("value", "Bullish") == "Bullish"
    pnl_pct    = (cmp - entry_price) / max(entry_price, 0.01) * 100

    # ── ATR stop anchored to ACTUAL entry price (not score's hypothetical entry)
    # tr["sl"] is calculated from score's hypothetical entry (can be above CMP
    # for WATCHLIST stocks whose entry = breakout trigger). Always rebase to real entry.
    atr_val  = tr.get("atr", 0)
    adr_val  = tr.get("adr", 0)
    if atr_val > 0:
        atr_stop = round(entry_price - 1.5 * atr_val, 2)
    elif adr_val > 0:
        atr_stop = round(entry_price - adr_val, 2)
    else:
        atr_stop = round(entry_price * 0.93, 2)       # 7% hard-stop fallback

    # Re-derive targets from actual entry price using same ADR/MDR ratios
    adr = adr_val or atr_val or (entry_price * 0.01)
    mdr = tr.get("mdr", adr * 1.5)
    if t1 == 0:  t1 = round(entry_price + 0.75 * mdr, 2)
    if t2 == 0:  t2 = round(entry_price + 1.00 * mdr, 2)
    if t3 == 0:  t3 = round(entry_price + 1.50 * mdr, 2)

    _base = {"atr_stop": atr_stop, "t1": t1, "t2": t2, "t3": t3}
    _base = {"atr_stop": atr_stop, "t1": t1, "t2": t2, "t3": t3}
    # ── Priority 1: Hard stop hit ─────────────────────────────────────────────
    if atr_stop > 0 and cmp < atr_stop:
        return {**_base,
            "signal": "EXIT NOW", "color": C["red"], "urgency": "high",
            "reason": f"Stop Loss breached — CMP ₹{cmp:,.2f} < ATR Stop ₹{atr_stop:,.2f}",
            "action": "Exit full position immediately. Loss-limiting — no exceptions.",
        }

    # ── Priority 2: Supertrend flipped bearish ────────────────────────────────
    if not st_bull:
        return {**_base,
            "signal": "EXIT NOW", "color": C["red"], "urgency": "high",
            "reason": "Supertrend flipped Bearish — short-term trend reversed",
            "action": f"Exit if SL at ₹{atr_stop:,.2f} not already triggered. Don't wait.",
        }

    # ── Priority 3: Stage deterioration ──────────────────────────────────────
    if stage == "4":
        return {**_base,
            "signal": "EXIT", "color": C["red"], "urgency": "high",
            "reason": "Stock entered Stage 4 — declining phase, institutional selling",
            "action": "Exit position. Stage 4 can persist for months.",
        }
    if stage == "3":
        return {**_base,
            "signal": "CAUTION", "color": C["amber"], "urgency": "medium",
            "reason": "Stage 3 — distribution / topping pattern detected",
            "action": f"Tighten stop to ₹{atr_stop:,.2f}. Exit if price breaks below.",
        }

    # ── Priority 4: T2 hit — trail stop, ride T3 ─────────────────────────────
    if t2 > 0 and cmp >= t2:
        return {**_base,
            "signal": "HOLD", "color": C["green"], "urgency": "low",
            "reason": f"T2 ₹{t2:,.2f} hit (+{((t2-entry_price)/entry_price*100):.1f}%) ✓ — trade is running",
            "action": f"Trail stop to T1 ₹{t1:,.2f}. Target T3 ₹{t3:,.2f}. Let the runner ride.",
        }

    # ── Priority 5: T1 hit — book partial, make trade free ────────────────────
    if t1 > 0 and cmp >= t1:
        return {**_base,
            "signal": "BOOK PARTIAL", "color": C["blue"], "urgency": "low",
            "reason": f"T1 ₹{t1:,.2f} hit (+{((t1-entry_price)/entry_price*100):.1f}%) ✓ — first target reached",
            "action": f"Book 70% of position. Move SL to entry ₹{entry_price:,.2f} (free trade). Hold 30% for T2 ₹{t2:,.2f}.",
        }

    # ── Priority 6: Score deteriorated badly ──────────────────────────────────
    if total < 45:
        return {**_base,
            "signal": "CAUTION", "color": C["amber"], "urgency": "medium",
            "reason": f"Score dropped to {total}/100 — momentum weakening",
            "action": f"Watch closely. Exit if CMP closes below ₹{atr_stop:,.2f}.",
        }

    # ── Priority 7: All clear — hold the swing ────────────────────────────────
    pnl_str = f"{pnl_pct:+.1f}%"
    return {
        "signal": "HOLD", "color": C["green"], "urgency": "low",
        "reason": f"Swing intact — Stage {stage}, Supertrend Bullish, score {total}/100 ({pnl_str} from entry)",
        "action": f"Hold. Stop at ₹{atr_stop:,.2f}. Next target T1 ₹{t1:,.2f}.",
    }

# ── SCREENER ───────────────────────────────────────────────────────────────────
def _score_one(sym: str, nifty_ret: float = 0.0):
    try:
        raw = fetch_ohlcv(sym)
        ind = add_indicators(raw)
        if len(ind) < 5: return None
        live_px = fetch_live_price(sym).get("price", 0.0) or 0.0
        sd = score(ind, nifty_ret=nifty_ret, live_price=live_px)
        tr = sd["trade"]
        return {"Symbol":sym,"Score":sd["total"],"Verdict":sd["verdict"],
                "Stage":sd.get("stage_label",""),"L1 Trend":sd["l1"],
                "L2 Momentum":sd["l2"],"L3 Setup":sd["l3"],
                "CMP":f"₹{sd['cmp']:,.2f}","Entry":f"₹{tr['entry']:,.2f}",
                "SL":f"₹{tr['sl']:,.2f}","R:R":f"{tr['rr']}x",
                "Sector": SECTOR_MAP.get(sym, "Other"),
                "CPR Signal": sd.get("cpr_signal", "—"),
                "CPR Pts": sd.get("cpr_pts", 0),
                "CPR": sd.get("cpr", {}).get("price_position", "—")}
    except Exception: return None

def run_screener(symbols: list, workers: int = 20) -> pd.DataFrame:
    symbols = list(dict.fromkeys(symbols))   # deduplicate, preserve order
    results = []; total = len(symbols); done = {"n":0}
    prog = st.progress(0, text=f"Scanning 0 / {total}...")
    live_box = st.empty()
    nifty_ret = fetch_nifty_3m_return()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(_score_one, s, nifty_ret): s for s in symbols}
        for fut in as_completed(futures):
            sym = futures[fut]; done["n"] += 1
            pct = done["n"] / total
            prog.progress(pct, text=f"Scanning {done['n']} / {total}  —  {sym}")
            live_box.markdown(f"<span style='font-family:JetBrains Mono,monospace;font-size:11px;color:{C['muted']}'>{sym}</span>",
                              unsafe_allow_html=True)
            res = fut.result()
            if res: results.append(res)
    prog.empty(); live_box.empty()
    if not results: return pd.DataFrame()
    return pd.DataFrame(results).sort_values("Score",ascending=False).reset_index(drop=True)

# ── PORTFOLIO HELPERS ──────────────────────────────────────────────────────────
def position_size(capital, entry, sl, risk_pct=0.01, max_pct=0.20):
    risk = entry - sl
    if risk <= 0 or entry <= 0: return 0, 0.0
    shares = min(int((capital*risk_pct)/risk), int((capital*max_pct)/entry))
    return max(1,shares), round(shares*entry,2)

def identify_setup_from_score(sd: dict) -> str:
    if sd.get("vcp") and sd.get("stage")=="2": return "VCP Breakout"
    if sd.get("stage")=="2": return "Stage 2 Advance"
    if "1→2" in str(sd.get("stage","")): return "Weinstein Breakout"
    return "EMA Pullback"

def _send_telegram(token: str, chat: str, msg: str):
    if not token or not chat: return
    try:
        data = json.dumps({"chat_id":chat,"text":msg,"parse_mode":"Markdown"}).encode()
        req  = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage",
                                      data=data, headers={"Content-Type":"application/json"})
        urllib.request.urlopen(req, timeout=5)
    except Exception: pass

def get_regime(index_df: pd.DataFrame) -> dict:
    if index_df.empty or len(index_df) < 50:
        return {"regime":"Unknown","color":"#666","close":"—","ma30w":"—","rsi":"—","sma200":"—"}
    try:
        df = add_indicators(index_df)
        l  = df.iloc[-1]
        stage_code, _ = detect_stage(df)
        cmp   = float(l["close"]); rsi = float(l["rsi"])
        ma150 = float(l.get("ma150",cmp)); sma200 = float(l.get("ema200",cmp))
        if stage_code=="2" and rsi>50: regime,color = "Bullish", C["green"]
        elif stage_code=="4":          regime,color = "Bearish", C["red"]
        else:                          regime,color = "Neutral",  C["amber"]
        return {"regime":regime,"color":color,"close":f"{cmp:,.0f}",
                "ma30w":f"{ma150:,.0f}","rsi":f"{rsi:.1f}","sma200":f"{sma200:,.0f}"}
    except Exception:
        return {"regime":"Unknown","color":"#666","close":"—","ma30w":"—","rsi":"—","sma200":"—"}

# ── SESSION STATE + SIDEBAR ────────────────────────────────────────────────────
def _init_state():
    if "scr_results" not in st.session_state: st.session_state["scr_results"] = pd.DataFrame()
    if "bt_results"  not in st.session_state: st.session_state.bt_results = None
    if "portfolio"   not in st.session_state:
        st.session_state.portfolio = {"cash":1_000_000,"capital":1_000_000,
                                      "positions":{},"closed_trades":[]}

def render_sidebar():
    st.sidebar.title("⚙️ Settings")
    capital    = st.sidebar.number_input("Capital (₹)", value=1_000_000, step=50_000, min_value=10_000)
    risk_pct   = st.sidebar.slider("Risk per trade (%)", 0.5, 3.0, 1.0, 0.25) / 100
    max_pos    = st.sidebar.number_input("Max positions", value=10, min_value=1, max_value=30)
    max_sl_pct = st.sidebar.slider("Max SL% allowed", 5, 15, 10, 1) / 100
    st.sidebar.divider()
    st.sidebar.subheader("🔔 Telegram Alerts")
    tg_token = st.sidebar.text_input("Bot Token", type="password", key="tg_tok")
    tg_chat  = st.sidebar.text_input("Chat ID", key="tg_chat")
    if st.sidebar.button("Test Alert"):
        if tg_token and tg_chat:
            try:
                data = json.dumps({"chat_id":tg_chat,"text":"✅ NSE Swing Trader connected!"}).encode()
                req  = urllib.request.Request(f"https://api.telegram.org/bot{tg_token}/sendMessage",
                    data=data, headers={"Content-Type":"application/json"})
                urllib.request.urlopen(req, timeout=5)
                st.sidebar.success("Alert sent!")
            except Exception as e: st.sidebar.error(f"Failed: {e}")
        else: st.sidebar.warning("Enter token and chat ID first.")
    return capital, risk_pct, int(max_pos), max_sl_pct, tg_token, tg_chat

# ── TAB: ANALYSE ───────────────────────────────────────────────────────────────
def tab_analyse(stocks_df, capital):
    options = [""] + stocks_df["display"].tolist()
    # Clear button resets the selectbox via session state
    if st.session_state.get("_do_clear_search"):
        st.session_state["stock_sel"] = ""
        st.session_state["_do_clear_search"] = False
    col_s, col_x, col_b = st.columns([4.6, 0.4, 1])
    with col_s:
        chosen = st.selectbox("stock_search", options=options, index=0,
            placeholder="Type symbol or company name  (e.g. RELIANCE, HDFC Bank, TCS...)",
            label_visibility="collapsed", key="stock_sel")
    with col_x:
        if st.button("✕", key="clear_sel", help="Clear search",
                     use_container_width=True):
            st.session_state["_do_clear_search"] = True
            st.rerun()
    with col_b:
        st.button("Analyse", key="go_analyse")

    if not chosen:
        st.markdown(f"""
<div style="background:{C['card']};border:1px solid {C['border']};border-radius:14px;
     padding:50px 30px;text-align:center;margin-top:2rem">
  <div style="font-size:44px;margin-bottom:14px">📈</div>
  <h3 style="color:{C['text']};font-family:'DM Sans',sans-serif;margin:0 0 8px">Start typing a stock name above</h3>
  <p style="color:{C['muted']};font-family:'DM Sans',sans-serif;font-size:14px;margin:0">
    Weinstein Stage · Supertrend · EMA Stack · RSI · MACD · VCP · Volume · S/R Breakout
  </p>
</div>""", unsafe_allow_html=True)
        return

    sym  = chosen.split("  —  ")[0].strip()
    comp = chosen.split("  —  ")[1].strip() if "  —  " in chosen else sym

    with st.spinner(f"Fetching {sym} from NSE..."):
        try:
            raw_df = fetch_ohlcv(sym)
            df_ind = add_indicators(raw_df)
            if len(df_ind) < 5:
                st.error(f"Not enough price history for {sym}.")
                return
            live = fetch_live_price(sym)                         # ← fetch live price FIRST
            live_px = live["price"] if live["price"] else 0.0   # 0 = fallback to last close
            sd   = score(df_ind, nifty_ret=fetch_nifty_3m_return(), live_price=live_px)
        except Exception as e:
            st.error(f"Could not load {sym}. Check the symbol or try again. ({e})")
            return

    latest = df_ind.iloc[-1]
    price  = live["price"] if live["price"] else float(latest["close"])
    chg    = live["change"]; pct = live["pct"]
    chg_c  = C["green"] if chg >= 0 else C["red"]
    sign   = "+" if chg >= 0 else ""

    # Stock header
    st.markdown(
        f"<div style='background:{C['card']};border:1px solid {C['border']};"
        f"border-radius:12px;padding:18px 22px;margin-bottom:1rem'>"
        f"<div style='display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px'>"
        f"<div><span style='font-family:JetBrains Mono,monospace;font-size:21px;color:{C['text']};font-weight:500'>{sym}</span>"
        f"<span style='font-family:DM Sans,sans-serif;font-size:14px;color:{C['muted']};margin-left:10px'>{comp}</span>"
        f"<span style='background:{C['border']};border-radius:4px;padding:2px 8px;font-family:JetBrains Mono,monospace;"
        f"font-size:11px;color:{C['muted']};margin-left:8px'>NSE</span></div>"
        f"<div style='display:flex;gap:18px;align-items:baseline'>"
        f"<span style='font-family:JetBrains Mono,monospace;font-size:28px;color:{C['text']};font-weight:500'>₹{price:,.2f}</span>"
        f"<span style='font-family:JetBrains Mono,monospace;font-size:15px;color:{chg_c}'>{sign}{chg:.2f} ({sign}{pct:.2f}%)</span>"
        f"</div></div></div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1.1,1.4,1.3])
    with c1:
        st.plotly_chart(make_gauge(sd["total"],sd["verdict"],sd["vcol"]), config={"displayModeBar":False})
        if sd["capped"]:
            sc = sd.get("stage","?")
            cap_msg = (f"Stage {sc} — no long positions" if sc in ("3","4") else "Weak trend gate — score capped")
            st.markdown(f"<p style='text-align:center;color:{C['red']};font-family:JetBrains Mono,monospace;"
                        f"font-size:11px;margin-top:-10px'>{cap_msg}</p>", unsafe_allow_html=True)
        if sd.get("cpr_downgraded"):
            st.markdown(f"<p style='text-align:center;color:{C['red']};font-family:JetBrains Mono,monospace;"
                        f"font-size:11px;margin-top:2px'>🚫 CPR filter downgraded verdict</p>", unsafe_allow_html=True)

    with c2:
        st.markdown(f"<p style='font-family:DM Sans,sans-serif;font-size:12px;font-weight:500;"
                    f"color:{C['muted']};text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px'>Score Breakdown</p>",
                    unsafe_allow_html=True)
        l1c = C["green"] if sd["l1"]>=30 else (C["amber"] if sd["l1"]>=20 else C["red"])
        l2c = C["green"] if sd["l2"]>=25 else (C["amber"] if sd["l2"]>=15 else C["red"])
        l3c = C["green"] if sd["l3"]>=18 else (C["amber"] if sd["l3"]>=10 else C["red"])
        st.markdown(bar_html("Layer 1 — Trend Gate",sd["l1"],40,l1c) +
                    bar_html("Layer 2 — Momentum",  sd["l2"],40,l2c) +
                    bar_html("Layer 3 — Setup",      sd["l3"],25,l3c), unsafe_allow_html=True)

    with c3:
        tr = sd["trade"]
        entry_col  = C["blue"] if sd["verdict"]=="STRONG BUY" else (C["amber"] if sd["verdict"]=="WATCHLIST" else C["dim"])
        stage_col  = C["green"] if sd.get("stage")=="2" else (C["amber"] if "1→2" in str(sd.get("stage","")) else C["red"])
        vcp_badge  = (f"<span style='background:{hex_rgba(C['green'],0.15)};color:{C['green']};"
                      f"border:1px solid {C['green']}40;border-radius:4px;padding:1px 7px;font-size:11px'>VCP ✓</span>"
                      if sd.get("vcp") else "")
        st.markdown(f"<p style='font-family:DM Sans,sans-serif;font-size:12px;font-weight:500;"
                    f"color:{C['muted']};text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px'>"
                    f"Trade Setup · MDR Targets · 1% Rule</p>", unsafe_allow_html=True)
        st.markdown(f"<div style='margin-bottom:10px'>"
                    f"<span style='font-size:11px;font-family:DM Sans,sans-serif;color:{stage_col};font-weight:600'>"
                    f"{sd.get('stage_label','')}</span>&nbsp;&nbsp;{vcp_badge}</div>", unsafe_allow_html=True)
        trade_html = (kpi_row(tr["entry_label"],      f"₹{tr['entry']:,.2f}", entry_col) +
                      kpi_row("ADR Stop (50% ADR)",   f"₹{tr['sl']:,.2f}",    C["red"]) +
                      kpi_row("T1 — Normal Lite 70%", f"₹{tr['t1']:,.2f}",    C["green"]) +
                      kpi_row("T2 — Normal 45%",      f"₹{tr['t2']:,.2f}",    "#00a86b") +
                      kpi_row("T3 — Runner",           f"₹{tr['t3']:,.2f}",    "#00a86b") +
                      kpi_row("R:R",                   f"{tr['rr']}x",         C["amber"]) +
                      kpi_row("ADR / MDR",             f"₹{tr['adr']:,.0f}  /  ₹{tr['mdr']:,.0f}", C["muted"]))
        st.markdown(f"<div style='background:{C['card']};border:1px solid {C['border']};"
                    f"border-radius:10px;padding:12px 16px'>{trade_html}</div>", unsafe_allow_html=True)
        st.markdown(f"<p style='font-size:11px;color:{C['muted']};margin:10px 0 4px;"
                    f"font-family:DM Sans,sans-serif;font-weight:500'>3-5-7 Scaling Levels</p>", unsafe_allow_html=True)
        scale_html = (kpi_row("Scale Out 1 (+3%)", f"₹{tr['scale1']:,.2f}", C["green"]) +
                      kpi_row("Scale Out 2 (+5%)", f"₹{tr['scale2']:,.2f}", C["green"]) +
                      kpi_row("Scale Out 3 (+7%)", f"₹{tr['scale3']:,.2f}", C["green"]))
        st.markdown(f"<div style='background:{C['card']};border:1px solid {C['border']};"
                    f"border-radius:10px;padding:10px 16px'>{scale_html}</div>", unsafe_allow_html=True)
        st.markdown(f"<p style='font-size:11px;color:{C['muted']};margin:10px 0 4px;"
                    f"font-family:DM Sans,sans-serif;font-weight:500'>Position Sizing — 1% Rule</p>", unsafe_allow_html=True)
        acct = st.number_input("Account size (₹)", min_value=10000, max_value=100_000_000,
                               value=capital, step=50000, key=f"acct_{sym}", label_visibility="collapsed")
        risk_amt  = round(acct*0.01, 0)
        stop_dist = max(tr["entry"]-tr["sl"], 0.01)
        pos_size  = int(risk_amt/stop_dist)
        pos_value = round(pos_size*tr["entry"], 0)
        st.markdown(f"<div style='background:{C['card']};border:1px solid {C['border']};"
                    f"border-radius:10px;padding:10px 16px'>"
                    f"{kpi_row('1% Risk Amount', f'₹{risk_amt:,.0f}', C['amber'])}"
                    f"{kpi_row('Stop Distance', f'₹{stop_dist:.2f}', C['muted'])}"
                    f"{kpi_row('Position Size', f'{pos_size} shares', C['blue'])}"
                    f"{kpi_row('Position Value', f'₹{pos_value:,.0f}', C['text'])}"
                    f"</div>", unsafe_allow_html=True)

    # Chart
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown(f"<p style='font-family:DM Sans,sans-serif;font-size:12px;font-weight:500;"
                f"color:{C['muted']};text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px'>"
                f"12-Month Chart · EMA 8/13/21/50 · 30W MA · Supertrend · Entry/SL/T1/T2/T3</p>",
                unsafe_allow_html=True)
    st.plotly_chart(make_chart(df_ind, sd, sym), config={"displayModeBar":True})

    # Signal grid
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown(f"<p style='font-family:DM Sans,sans-serif;font-size:12px;font-weight:500;"
                f"color:{C['muted']};text-transform:uppercase;letter-spacing:.08em;margin-bottom:12px'>Signal Details</p>",
                unsafe_allow_html=True)
    layers = [("Layer 1 — Trend Gate",["stage","supertrend","ema"]),
              ("Layer 2 — Momentum",  ["rsi","macd","adx","rs","momentum"]),
              ("Layer 3 — Setup",     ["volume","vcp","candle"])]
    gc1,gc2,gc3 = st.columns(3)
    for col_w,(lname,keys) in zip([gc1,gc2,gc3],layers):
        with col_w:
            st.markdown(f"<p style='font-family:DM Sans,sans-serif;font-size:12px;"
                        f"color:{C['muted']};font-weight:500;margin-bottom:8px'>{lname}</p>", unsafe_allow_html=True)
            for k in keys:
                d = sd["details"][k]
                st.markdown(pill_html(d["label"],d["value"],d["score"],d["max"],d["status"]), unsafe_allow_html=True)
    if "cpr" in sd["details"]:
        d_cpr = sd["details"]["cpr"]
        st.markdown(pill_html(d_cpr["label"], d_cpr["value"], d_cpr["score"], d_cpr["max"], d_cpr["status"]),
                    unsafe_allow_html=True)

    # ── CPR Panel (Gomathi Shankar) ───────────────────────────────────────────
    cpr_d = sd.get("cpr", {})
    if cpr_d:
        st.markdown("<hr>", unsafe_allow_html=True)

        # ── CPR Signal banner ─────────────────────────────────────────────────
        cpr_sig   = sd.get("cpr_signal", "NO DATA")
        cpr_down  = sd.get("cpr_downgraded", False)
        cpr_rsns  = sd.get("cpr_reasons", [])
        sig_colors = {"CONFIRM": C["green"], "NEUTRAL": C["amber"],
                      "CAUTION": C["amber"], "REJECT": C["red"], "NO DATA": C["dim"]}
        sig_icons  = {"CONFIRM": "✅", "NEUTRAL": "🟡", "CAUTION": "⚠️", "REJECT": "🚫", "NO DATA": "—"}
        sig_descs  = {
            "CONFIRM": "All CPR conditions met — trade is confirmed by KGS filter",
            "NEUTRAL": "Price above TC but wide CPR — proceed with other filters strong",
            "CAUTION": "Price inside CPR zone — wait for breakout above TC before entry",
            "REJECT":  "Price below BC — CPR rejects this trade. Verdict downgraded." if cpr_down else
                       "Price below BC — bearish bias. Avoid long entries.",
            "NO DATA": "CPR data unavailable",
        }
        sig_c = sig_colors.get(cpr_sig, C["dim"])
        _down_html = (f"<div style='font-family:DM Sans,sans-serif;font-size:12px;color:{C['red']};margin-top:4px'>"
                      f"⬇ Verdict downgraded by CPR filter (was higher before CPR gate)</div>") if cpr_down else ""
        _rsns_html = (f"<div style='font-family:DM Sans,sans-serif;font-size:11px;color:{C['muted']};margin-top:6px'>"
                      + "  ·  ".join(cpr_rsns) + "</div>") if cpr_rsns else ""
        _banner_html = (
            f"<div style='background:{hex_rgba(sig_c,0.10)};border:2px solid {hex_rgba(sig_c,0.5)};"
            f"border-radius:12px;padding:14px 20px;margin-bottom:14px;display:flex;align-items:center;gap:16px'>"
            f"<span style='font-size:28px'>{sig_icons.get(cpr_sig, '—')}</span>"
            f"<div><div style='font-family:JetBrains Mono,monospace;font-size:18px;font-weight:700;color:{sig_c}'>"
            f"CPR: {cpr_sig}</div>"
            f"<div style='font-family:DM Sans,sans-serif;font-size:13px;color:{C['muted']};margin-top:2px'>"
            f"{sig_descs.get(cpr_sig, '')}</div>"
            f"{_down_html}{_rsns_html}</div></div>"
        )
        st.markdown(_banner_html, unsafe_allow_html=True)

        st.markdown(
            f"<p style='font-family:DM Sans,sans-serif;font-size:12px;font-weight:500;"
            f"color:{C['muted']};text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px'>"
            f"CPR — Central Pivot Range (Gomathi Shankar Methodology)</p>", unsafe_allow_html=True)

        daily_c   = cpr_d.get("daily",   {})
        weekly_c  = cpr_d.get("weekly",  {})
        monthly_c = cpr_d.get("monthly", {})
        pos_c     = cpr_d.get("price_position", "—")
        cpr_pts_v = sd.get("cpr_pts", 0)

        pos_color = C["green"] if pos_c=="above" else (C["red"] if pos_c=="below" else C["amber"])
        pos_label = {"above":"Above TC — Bullish ▲","below":"Below BC — Bearish ▼","inside":"Inside CPR — Indecision ↔"}.get(pos_c,"—")
        narrow_lbl= "Narrow ✓ — Trending day expected" if daily_c.get("narrow") else "Wide — Sideways / Reversal likely"
        narrow_col= C["green"] if daily_c.get("narrow") else C["amber"]
        virgin_lbl= f"Virgin CPR ✓ ({daily_c.get('consec_virgin',0)} consecutive)" if daily_c.get("virgin") else "CPR Tested (non-virgin)"
        virgin_col= C["green"] if daily_c.get("virgin") else C["muted"]
        mtf_bull  = ("🟢 All 3 TF Bullish" if cpr_d.get("weekly_bullish") and cpr_d.get("monthly_bullish")
                     else "🟡 Daily only" if pos_c=="above"
                     else "🔴 Bearish across TF")
        cpr_score_color = C["green"] if cpr_pts_v >= 5 else (C["amber"] if cpr_pts_v > 0 else C["red"])

        ca, cb, cc, cd = st.columns(4)
        with ca:
            st.markdown(f"<div style='background:{C['card']};border:1px solid {C['border']};border-radius:10px;padding:14px 16px;text-align:center'>"
                        f"<div style='font-size:11px;color:{C['muted']};font-family:DM Sans;margin-bottom:6px'>Daily CPR</div>"
                        f"<div style='font-size:13px;font-weight:700;color:{pos_color};font-family:JetBrains Mono'>{pos_label}</div>"
                        f"<div style='font-size:11px;color:{C['muted']};margin-top:6px;font-family:DM Sans'>"
                        f"TC ₹{daily_c.get('tc',0):,.2f}  |  BC ₹{daily_c.get('bc',0):,.2f}</div>"
                        f"<div style='font-size:10px;color:{C['dim']};font-family:DM Sans'>Pivot ₹{daily_c.get('pivot',0):,.2f}</div>"
                        f"</div>", unsafe_allow_html=True)
        with cb:
            wt = weekly_c.get("tc",0); wb = weekly_c.get("bc",0)
            w_col = C["green"] if cpr_d.get("weekly_bullish") else C["red"]
            w_lbl = "Above Weekly CPR ▲" if cpr_d.get("weekly_bullish") else "Below Weekly CPR ▼"
            st.markdown(f"<div style='background:{C['card']};border:1px solid {C['border']};border-radius:10px;padding:14px 16px;text-align:center'>"
                        f"<div style='font-size:11px;color:{C['muted']};font-family:DM Sans;margin-bottom:6px'>Weekly CPR</div>"
                        f"<div style='font-size:13px;font-weight:700;color:{w_col};font-family:JetBrains Mono'>{w_lbl if wt else 'N/A'}</div>"
                        f"<div style='font-size:11px;color:{C['muted']};margin-top:6px;font-family:DM Sans'>"
                        f"TC ₹{wt:,.2f}  |  BC ₹{wb:,.2f}</div>"
                        f"<div style='font-size:10px;color:{C['dim']};font-family:DM Sans'>Width {weekly_c.get('width_pct',0):.2f}%</div>"
                        f"</div>", unsafe_allow_html=True)
        with cc:
            st.markdown(f"<div style='background:{C['card']};border:1px solid {C['border']};border-radius:10px;padding:14px 16px;text-align:center'>"
                        f"<div style='font-size:11px;color:{C['muted']};font-family:DM Sans;margin-bottom:6px'>CPR Width & Virgin</div>"
                        f"<div style='font-size:12px;font-weight:600;color:{narrow_col};font-family:DM Sans'>{narrow_lbl}</div>"
                        f"<div style='font-size:12px;font-weight:600;color:{virgin_col};font-family:DM Sans;margin-top:4px'>{virgin_lbl}</div>"
                        f"<div style='font-size:11px;color:{C['muted']};margin-top:6px;font-family:DM Sans'>Width {daily_c.get('width_pct',0):.3f}%</div>"
                        f"</div>", unsafe_allow_html=True)
        with cd:
            st.markdown(f"<div style='background:{C['card']};border:1px solid {C['border']};border-radius:10px;padding:14px 16px;text-align:center'>"
                        f"<div style='font-size:11px;color:{C['muted']};font-family:DM Sans;margin-bottom:6px'>Multi-TF CPR Score</div>"
                        f"<div style='font-size:22px;font-weight:700;color:{cpr_score_color};font-family:JetBrains Mono'>{cpr_pts_v:+d}</div>"
                        f"<div style='font-size:12px;color:{cpr_score_color};font-family:DM Sans;margin-top:2px'>{mtf_bull}</div>"
                        f"<div style='font-size:10px;color:{C['dim']};font-family:DM Sans;margin-top:4px'>Monthly: {'Bullish ▲' if cpr_d.get('monthly_bullish') else 'Bearish ▼'}</div>"
                        f"</div>", unsafe_allow_html=True)

        # PivotBoss S/R table
        d_cpr_lv = daily_c
        cmp_now  = cpr_d.get("cmp", 0)
        if d_cpr_lv and cmp_now:
            st.markdown(f"<p style='font-family:DM Sans,sans-serif;font-size:11px;font-weight:600;"
                        f"color:{C['muted']};text-transform:uppercase;letter-spacing:.07em;margin:12px 0 6px'>"
                        f"PivotBoss S/R Levels (Frank Ochoa · Used by KGS)</p>", unsafe_allow_html=True)
            r_levels = [("R4", d_cpr_lv.get("r4",0)), ("R3", d_cpr_lv.get("r3",0)),
                        ("R2", d_cpr_lv.get("r2",0)), ("R1", d_cpr_lv.get("r1",0))]
            s_levels = [("S1", d_cpr_lv.get("s1",0)), ("S2", d_cpr_lv.get("s2",0)),
                        ("S3", d_cpr_lv.get("s3",0)), ("S4", d_cpr_lv.get("s4",0))]
            rows_html = ""
            for lbl, val in r_levels:
                is_near = abs(val - cmp_now) / max(cmp_now, 1) < 0.03
                col_    = C["green"] if val > cmp_now else C["muted"]
                fw      = "700" if is_near else "400"
                near_tag= "  ◀ near" if is_near else ""
                rows_html += (f"<tr><td style='color:{col_};font-weight:{fw};font-family:DM Sans'>{lbl}</td>"
                              f"<td style='color:{col_};font-family:JetBrains Mono;text-align:right'>₹{val:,.2f}{near_tag}</td></tr>")
            rows_html += (f"<tr style='background:rgba(255,210,50,0.08)'>"
                          f"<td style='color:#ffd232;font-weight:700;font-family:DM Sans'>Pivot</td>"
                          f"<td style='color:#ffd232;font-family:JetBrains Mono;text-align:right'>₹{d_cpr_lv.get('pivot',0):,.2f}</td></tr>")
            for lbl, val in s_levels:
                is_near = abs(val - cmp_now) / max(cmp_now, 1) < 0.03
                col_    = C["red"] if val < cmp_now else C["muted"]
                fw      = "700" if is_near else "400"
                near_tag= "  ◀ near" if is_near else ""
                rows_html += (f"<tr><td style='color:{col_};font-weight:{fw};font-family:DM Sans'>{lbl}</td>"
                              f"<td style='color:{col_};font-family:JetBrains Mono;text-align:right'>₹{val:,.2f}{near_tag}</td></tr>")
            st.markdown(
                f"<table style='width:100%;border-collapse:collapse;font-size:12px'>"
                f"<thead><tr><th style='text-align:left;color:{C['muted']};padding:2px 8px 6px;font-family:DM Sans'>Level</th>"
                f"<th style='text-align:right;color:{C['muted']};padding:2px 8px 6px;font-family:DM Sans'>Price</th></tr></thead>"
                f"<tbody>{rows_html}</tbody></table>", unsafe_allow_html=True)

    # Bollinger + indicator summary
    st.markdown("<hr>", unsafe_allow_html=True)
    e1, e2 = st.columns(2)
    with e1:
        bp   = sd["bb_pct"]
        bp_c = C["green"] if 40<=bp<=80 else (C["amber"] if bp>80 else C["red"])
        bp_lbl = ("Upper zone — caution" if bp>80 else "Mid-upper — ideal" if bp>50 else "Mid-lower" if bp>20 else "Lower zone — oversold")
        bb_lo = float(latest["bb_lower"]); bb_hi = float(latest["bb_upper"])
        st.markdown(f"<p style='font-family:DM Sans,sans-serif;font-size:12px;color:{C['muted']};"
                    f"font-weight:500;text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px'>Bollinger Band Position (%B)</p>"
                    f"<div style='background:{C['card']};border:1px solid {C['border']};border-radius:10px;padding:14px 16px'>"
                    f"<div style='display:flex;justify-content:space-between;margin-bottom:7px'>"
                    f"<span style='font-family:JetBrains Mono,monospace;font-size:13px;color:{bp_c}'>{bp_lbl}</span>"
                    f"<span style='font-family:JetBrains Mono,monospace;font-size:13px;color:{C['text']}'>{bp}%</span></div>"
                    f"<div style='background:{C['border']};border-radius:4px;height:8px;overflow:hidden'>"
                    f"<div style='background:{bp_c};width:{min(bp,100)}%;height:100%;border-radius:4px'></div></div>"
                    f"<div style='display:flex;justify-content:space-between;margin-top:7px'>"
                    f"<span style='font-family:JetBrains Mono,monospace;font-size:11px;color:{C['dim']}'>₹{bb_lo:.0f}</span>"
                    f"<span style='font-family:JetBrains Mono,monospace;font-size:11px;color:{C['dim']}'>₹{bb_hi:.0f}</span>"
                    f"</div></div>", unsafe_allow_html=True)
    with e2:
        adx_str = "Strong" if sd["adx"]>25 else "Weak"
        bbw_str = "Expanding" if sd["bb_width"]>0.05 else "Squeezing"
        rsi_c   = C["green"] if 45<=sd["rsi"]<=65 else (C["amber"] if 35<=sd["rsi"]<=70 else C["red"])
        adx_c   = C["green"] if sd["adx"]>25 else C["amber"]
        vol_c   = C["green"] if sd["vol_ratio"]>=1.5 else (C["amber"] if sd["vol_ratio"]>=1.0 else C["red"])
        ind_rows = (kpi_row("RSI (14)",  f"{sd['rsi']:.1f}", rsi_c) +
                    kpi_row("ADX (14)",  f"{sd['adx']:.1f} ({adx_str})", adx_c) +
                    kpi_row("BB Width",  f"{sd['bb_width']:.4f} ({bbw_str})", C["amber"]) +
                    kpi_row("Vol/Avg",   f"{sd['vol_ratio']:.2f}x", vol_c))
        st.markdown(f"<p style='font-family:DM Sans,sans-serif;font-size:12px;color:{C['muted']};"
                    f"font-weight:500;text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px'>Indicator Summary</p>"
                    f"<div style='background:{C['card']};border:1px solid {C['border']};"
                    f"border-radius:10px;padding:12px 16px'>{ind_rows}</div>", unsafe_allow_html=True)

    # Verdict bar
    st.markdown("<hr>", unsafe_allow_html=True)
    # Build AVOID message based on WHY it's AVOID — score issue vs CPR downgrade
    _cpr_sig   = sd.get("cpr_signal", "")
    _raw_score = sd.get("total", 0)
    _cpr_daily = sd.get("cpr", {}).get("daily", {})
    _bc_val    = _cpr_daily.get("bc", 0)
    _tc_val    = _cpr_daily.get("tc", 0)
    if sd["verdict"] == "AVOID" and _raw_score >= 55 and _cpr_sig in ("REJECT", "CAUTION"):
        _avoid_msg = (f"Score qualifies ({_raw_score}/100) but CPR signal is {_cpr_sig} — "
                      f"price is below the CPR zone (₹{_bc_val:,.2f}–₹{_tc_val:,.2f}). "
                      f"Wait for price to reclaim above ₹{_tc_val:,.2f} before entering.")
    else:
        _avoid_msg = f"Trend or momentum conditions not aligned. No actionable swing setup. Revisit when score crosses 55."

    v_descs = {
        "STRONG BUY": f"High-conviction swing setup. Enter near ₹{tr['entry']:.0f}, SL at ₹{tr['sl']:.0f}. Targets: ₹{tr['t1']:.0f} / ₹{tr['t2']:.0f}. R:R = {tr['rr']}x. Hold 3-7 sessions.",
        "WATCHLIST":  f"Setup forming. Wait for price to break above ₹{tr['entry']:.0f} on strong volume. Not ready yet.",
        "AVOID":      _avoid_msg,
    }
    vdesc = v_descs.get(sd["verdict"],""); vcol = sd["vcol"]; vtotal = sd["total"]
    st.markdown(f"<div style='background:rgba(0,0,0,0.05);border:1px solid {vcol}40;border-radius:12px;"
                f"padding:20px 24px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:14px'>"
                f"<div><span style='font-family:JetBrains Mono,monospace;font-size:22px;font-weight:500;color:{vcol}'>{sd['verdict']}</span>"
                f"<p style='font-family:DM Sans,sans-serif;font-size:13px;color:{C['muted']};margin:6px 0 0;max-width:580px'>{vdesc}</p></div>"
                f"<div style='text-align:right'><span style='font-family:JetBrains Mono,monospace;font-size:52px;"
                f"color:{vcol};font-weight:500'>{vtotal}</span>"
                f"<span style='font-family:JetBrains Mono,monospace;font-size:22px;color:{C['dim']}'>/100</span>"
                f"</div></div>", unsafe_allow_html=True)

    # Action buttons
    btn_c1, btn_c2, btn_c3 = st.columns([3,1,1])
    with btn_c2:
        if st.button("+ Watchlist", key="add_wl_analyse"):
            if add_to_watchlist(sym, comp): st.success(f"{sym} added to Watchlist!")
            else: st.info(f"{sym} already in Watchlist.")
    with btn_c3:
        report_text = (f"NSE Swing Score — {sym} ({comp})\nGenerated: {datetime.now().strftime('%d %b %Y %H:%M')}\n{'='*40}\n"
                       f"VERDICT: {sd['verdict']} ({vtotal}/100)\n\nL1 Trend: {sd['l1']}/40\nL2 Momentum: {sd['l2']}/40\nL3 Setup: {sd['l3']}/25\n\n"
                       f"TRADE SETUP\n{tr['entry_label']}: ₹{tr['entry']:.2f}\nStop Loss: ₹{tr['sl']:.2f}\nT1: ₹{tr['t1']:.2f}\nT2: ₹{tr['t2']:.2f}\nR:R: {tr['rr']}x\n")
        safe_text = report_text.replace("\\","\\\\").replace("`","'").replace("\n","\\n")
        st.markdown(f"<button onclick=\"navigator.clipboard.writeText('{safe_text}').then(()=>this.textContent='Copied!').catch(()=>this.textContent='Failed')\""
                    f" style='background:{C['border2']};border:1px solid {C['border']};border-radius:6px;color:{C['muted']};"
                    f"font-family:JetBrains Mono,monospace;font-size:12px;padding:6px 14px;cursor:pointer;width:100%'>Copy Report</button>",
                    unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center;color:{C['dim']};font-size:11px;font-family:JetBrains Mono,monospace;margin-top:2rem'>"
                f"Data via Yahoo Finance · {datetime.now().strftime('%d %b %Y %H:%M IST')} · Not financial advice</p>",
                unsafe_allow_html=True)

# ── TAB: SCREENER ──────────────────────────────────────────────────────────────
def tab_screener(stocks_df):
    st.markdown(f"<p style='font-family:DM Sans,sans-serif;font-size:13px;color:{C['muted']};margin-bottom:1rem'>"
                f"Scan any basket of NSE stocks in parallel and rank by swing score. "
                f"75+ = Strong Buy &nbsp;|&nbsp; 55-74 = Watchlist.</p>", unsafe_allow_html=True)
    all_nse = stocks_df["symbol"].tolist()
    basket_options = list(SCREENER_LISTS.keys()) + ["All NSE Listed (~2000 stocks)"]
    est_times = {"Nifty 50":"~1 min","Nifty Next 50":"~1 min","Nifty Midcap":"~2 min",
                 "Small Cap":"~1 min","Nifty 100":"~2 min","All 200":"~4 min",
                 "All NSE Listed (~2000 stocks)":"~8-12 min"}
    scr_c1,scr_c2,scr_c3,scr_c4 = st.columns([2,1,1,1])
    with scr_c1: basket = st.selectbox("Basket", basket_options, key="scr_basket")
    with scr_c2: min_score = st.number_input("Min score", min_value=0, max_value=100, value=55, step=5, key="scr_min")
    with scr_c3: workers = st.number_input("Workers", min_value=5, max_value=30, value=20, step=5, key="scr_workers")
    with scr_c4:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        cpr_filter = st.checkbox("Above Daily CPR only", value=False, key="scr_cpr",
                                 help="Filter: show only stocks trading above their Daily CPR Top (TC) — Bullish bias per Gomathi Shankar")
    custom_input = st.text_input("Custom symbols (comma-separated)", placeholder="e.g. ZOMATO, IRFC, SUZLON", key="scr_custom")
    n_stocks = len(all_nse) if basket=="All NSE Listed (~2000 stocks)" else len(SCREENER_LISTS.get(basket,[]))
    est = est_times.get(basket,"~2 min")
    st.markdown(f"<p style='font-family:JetBrains Mono,monospace;font-size:12px;color:{C['muted']};margin-bottom:8px'>"
                f"{n_stocks} stocks · {workers} parallel workers · Est. time: {est}</p>", unsafe_allow_html=True)

    run_scr = st.button("▶ Run Screener", use_container_width=False, key="run_screener")
    if run_scr:
        symbols = all_nse.copy() if basket=="All NSE Listed (~2000 stocks)" else SCREENER_LISTS[basket].copy()
        if custom_input.strip():
            extra = [s.strip().upper() for s in custom_input.split(",") if s.strip()]
            symbols = list(dict.fromkeys(extra+symbols))
        st.session_state["scr_results"] = run_screener(symbols, workers=int(workers))

    results_df = st.session_state["scr_results"]
    if results_df.empty and run_scr:
        st.warning("No results found. Check your internet connection and try again.")
    elif not results_df.empty:
        filtered = results_df[results_df["Score"]>=min_score].copy()
        if cpr_filter and "CPR Signal" in filtered.columns:
            filtered = filtered[filtered["CPR Signal"].isin(["CONFIRM", "NEUTRAL"])]
        st.markdown(f"<p style='font-family:JetBrains Mono,monospace;font-size:12px;color:{C['muted']};margin:8px 0'>"
                    f"{len(filtered)} stocks scored {min_score}+{' · CPR CONFIRM/NEUTRAL only ✓' if cpr_filter else ''} "
                    f"out of {len(results_df)} scanned</p>", unsafe_allow_html=True)
        if filtered.empty:
            st.info("No stocks meet the minimum score. Try lowering the Min score filter.")
            return
        def _fmt_entry(row):
            if row["Verdict"]=="STRONG BUY": return row["Entry"]+" ▸ Limit"
            elif row["Verdict"]=="WATCHLIST": return row["Entry"]+" ▸ Trigger"
            return "—"
        filtered["Entry"] = filtered.apply(_fmt_entry, axis=1)
        wl_syms = {w["symbol"] for w in load_watchlist()}
        filtered["WL"] = filtered["Symbol"].apply(lambda s:"✓" if s in wl_syms else "")
        filtered.insert(0,"⭐",False)
        base_cols = ["⭐","Symbol","Score","Verdict","CPR Signal","L1 Trend","L2 Momentum","L3 Setup","CMP","Entry","SL","R:R","WL"]
        disp_cols = [c for c in base_cols if c in filtered.columns]
        disp_df = filtered[disp_cols].copy()
        edited = st.data_editor(disp_df, use_container_width=True, hide_index=True,
            column_config={
                "⭐":          st.column_config.CheckboxColumn("⭐",help="Check to add to Watchlist",default=False,width="small"),
                "Score":       st.column_config.ProgressColumn("Score",min_value=0,max_value=100,format="%d"),
                "CPR Signal":  st.column_config.TextColumn("CPR 🔍",help="CONFIRM=bullish+narrow, NEUTRAL=above TC, CAUTION=inside CPR, REJECT=below BC"),
                "L1 Trend":    st.column_config.NumberColumn("Trend/40"),
                "L2 Momentum": st.column_config.NumberColumn("Mom/40"),
                "L3 Setup":    st.column_config.NumberColumn("Setup/25"),
                "WL":          st.column_config.TextColumn("WL",width="small"),
            },
            disabled=["Symbol","Score","Verdict","CPR Signal","L1 Trend","L2 Momentum","L3 Setup","CMP","Entry","SL","R:R","WL"])
        selected_syms = edited[edited["⭐"]]["Symbol"].tolist()
        st.markdown("<br>", unsafe_allow_html=True)
        btn_c1, btn_c2 = st.columns([2,3])
        with btn_c1:
            if selected_syms:
                if st.button(f"+ Add {len(selected_syms)} selected to Watchlist", key="add_selected_wl"):
                    added = sum(add_to_watchlist(s,s) for s in selected_syms)
                    st.success(f"Added {added} stock{'s' if added!=1 else ''} to Watchlist!"); st.rerun()
            else:
                st.markdown(f"<span style='font-size:12px;color:{C['muted']}'>☑ Check rows above then click Add to Watchlist</span>",
                            unsafe_allow_html=True)
        with btn_c2:
            strong_buys = filtered[filtered["Verdict"]=="STRONG BUY"]["Symbol"].tolist()
            if strong_buys:
                if st.button(f"+ Add all {len(strong_buys)} STRONG BUY to Watchlist", key="add_all_sb_wl"):
                    for s in strong_buys: add_to_watchlist(s,s)
                    st.success(f"Added {len(strong_buys)} stocks!"); st.rerun()

        # ── Sector Rotation ────────────────────────────────────────────────────
        if "Sector" in filtered.columns:
            with st.expander("🗂️ Sector Rotation — Score by Sector", expanded=False):
                sector_summary = (
                    filtered.groupby("Sector")
                    .agg(
                        Stocks      = ("Symbol",  "count"),
                        Avg_Score   = ("Score",   "mean"),
                        Strong_Buys = ("Verdict", lambda x: (x == "STRONG BUY").sum()),
                        Watchlist   = ("Verdict", lambda x: (x == "WATCHLIST").sum()),
                    )
                    .sort_values("Avg_Score", ascending=False)
                    .reset_index()
                )
                sector_summary["Avg_Score"] = sector_summary["Avg_Score"].round(1)
                sector_summary.columns = ["Sector","Stocks","Avg Score","Strong Buys","Watchlist"]
                st.dataframe(
                    sector_summary,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Avg Score": st.column_config.ProgressColumn("Avg Score", min_value=0, max_value=100, format="%.1f"),
                        "Strong Buys": st.column_config.NumberColumn("🟢 Strong Buys"),
                        "Watchlist":   st.column_config.NumberColumn("🟡 Watchlist"),
                    }
                )
                # Bar chart of top sectors
                if len(sector_summary) >= 2:
                    top_s = sector_summary.head(10)
                    bar_colors = [C["green"] if sb > 0 else C["amber"]
                                  for sb in top_s["Strong Buys"]]
                    fig_sec = go.Figure(go.Bar(
                        x=top_s["Sector"], y=top_s["Avg Score"],
                        marker_color=bar_colors,
                        text=top_s["Avg Score"].astype(str),
                        textposition="outside"
                    ))
                    fig_sec.update_layout(
                        title="Top Sectors by Avg Swing Score",
                        height=320,
                        plot_bgcolor=C["card"], paper_bgcolor=C["bg"],
                        font=dict(color="white", family="DM Sans, sans-serif"),
                        margin=dict(l=10, r=10, t=40, b=80),
                        xaxis=dict(tickangle=-30),
                        yaxis=dict(range=[0, 105])
                    )
                    st.plotly_chart(fig_sec, key="sec_rot_chart")

        # ── Stage 1 Accumulation ───────────────────────────────────────────────
        if "Stage" in filtered.columns:
            stage1_df = results_df[
                results_df["Stage"].astype(str).str.contains("1→2|Accum|Stage 1", na=False)
            ].copy()
            if not stage1_df.empty:
                with st.expander(f"🌱 Stage 1 Accumulation ({len(stage1_df)} stocks) — Weinstein Breakout Candidates", expanded=False):
                    st.markdown(
                        f"<p style='font-family:DM Sans,sans-serif;font-size:13px;color:{C['muted']};margin-bottom:8px'>"
                        f"These stocks are transitioning from Stage 1 (base) → Stage 2 (advance). "
                        f"Set price alerts at the pivot high — buy on volume breakout.</p>",
                        unsafe_allow_html=True
                    )
                    s1_disp = stage1_df[["Symbol","Score","Stage","CMP","SL"]].copy()
                    if "Sector" in stage1_df.columns:
                        s1_disp["Sector"] = stage1_df["Sector"]
                    s1_disp = s1_disp.sort_values("Score", ascending=False).reset_index(drop=True)
                    st.dataframe(s1_disp, use_container_width=True, hide_index=True)
                    s1_syms = s1_disp["Symbol"].tolist()
                    wl_add_c1, _ = st.columns([2, 3])
                    with wl_add_c1:
                        if st.button(f"+ Add all {len(s1_syms)} Stage 1→2 to Watchlist", key="add_stage1_wl"):
                            for s in s1_syms: add_to_watchlist(s, s)
                            st.success(f"Added {len(s1_syms)} stocks!"); st.rerun()

# ── TAB: WATCHLIST ─────────────────────────────────────────────────────────────
def tab_watchlist():
    wl = load_watchlist()
    if not wl:
        st.markdown(f"<div style='background:{C['card']};border:1px solid {C['border']};border-radius:14px;"
                    f"padding:40px 30px;text-align:center;margin-top:1rem'>"
                    f"<div style='font-size:36px;margin-bottom:12px'>⭐</div>"
                    f"<h3 style='color:{C['text']};font-family:DM Sans,sans-serif;margin:0 0 6px'>Your watchlist is empty</h3>"
                    f"<p style='color:{C['muted']};font-family:DM Sans,sans-serif;font-size:13px;margin:0'>"
                    f"Analyse a stock and click '+ Watchlist', or run the Screener and add picks.</p></div>",
                    unsafe_allow_html=True)
        return
    wl_top1, wl_top2 = st.columns([3,1])
    with wl_top1:
        st.markdown(f"<p style='font-family:DM Sans,sans-serif;font-size:13px;color:{C['muted']};margin-bottom:0'>"
                    f"{len(wl)} stock{'s' if len(wl)!=1 else ''} saved · Open any card to see chart & trade setup</p>",
                    unsafe_allow_html=True)
    with wl_top2:
        if st.button("Refresh All", key="rescore_all"):
            for itm in wl:
                for k in [f"wl_sd_{itm['symbol']}",f"wl_df_{itm['symbol']}"]:
                    st.session_state.pop(k,None)
            st.rerun()
    nifty_r = fetch_nifty_3m_return()
    for item in wl:
        s = item["symbol"]; cmp_name = item.get("company",s)
        if f"wl_sd_{s}" not in st.session_state:
            try:
                _r = fetch_ohlcv(s); _i = add_indicators(_r)
                if len(_i) >= 5:
                    # is_entry=False: monitoring a held position — CPR doesn't change verdict
                    st.session_state[f"wl_sd_{s}"] = score(_i, nifty_ret=nifty_r, is_entry=False)
                    st.session_state[f"wl_df_{s}"] = _i
            except Exception: pass
        cached_sd = st.session_state.get(f"wl_sd_{s}")
        cached_df = st.session_state.get(f"wl_df_{s}")
        rc1,rc2,rc3,rc4,rc5,rc6,rc7 = st.columns([1.4,2.2,1.2,1.0,1.8,1.4,0.7])
        with rc1:
            st.markdown(f"<span style='font-family:JetBrains Mono,monospace;font-size:14px;font-weight:700;color:{C['text']}'>{s}</span>",
                        unsafe_allow_html=True)
        with rc2:
            st.markdown(f"<span style='font-family:DM Sans,sans-serif;font-size:12px;color:{C['muted']}'>{cmp_name}</span>",
                        unsafe_allow_html=True)
        with rc3:
            if cached_sd:
                st.markdown(f"<span style='font-family:JetBrains Mono,monospace;font-size:13px;color:{C['text']}'>₹{cached_sd['cmp']:,.2f}</span>",
                            unsafe_allow_html=True)
        with rc4:
            if cached_sd:
                st.markdown(f"<span style='font-family:JetBrains Mono,monospace;font-size:13px;color:{C['muted']}'>{cached_sd['total']}/100</span>",
                            unsafe_allow_html=True)
        with rc5:
            if cached_sd:
                _vc = cached_sd["vcol"]; _v = cached_sd["verdict"]
                st.markdown(f"<span style='background:{hex_rgba(_vc,0.15)};color:{_vc};border:1px solid {_vc}50;"
                            f"border-radius:6px;padding:3px 10px;font-family:DM Sans,sans-serif;font-size:12px;font-weight:700'>{_v}</span>",
                            unsafe_allow_html=True)
        with rc6:
            # "📥 Purchased" — mark as bought, moves to Holdings tab
            if st.button("📥 Purchased", key=f"buy_{s}", help=f"Mark {s} as purchased"):
                st.session_state[f"buy_modal_{s}"] = True
        with rc7:
            if st.button("✕", key=f"rm_{s}", help=f"Remove {s}"):
                remove_from_watchlist(s)
                for k in [f"wl_sd_{s}",f"wl_df_{s}"]: st.session_state.pop(k,None)
                st.rerun()

        # ── Purchase form (shown inline when button clicked) ──────────────────
        if st.session_state.get(f"buy_modal_{s}"):
            with st.container():
                st.markdown(f"<div style='background:{C['card']};border:1px solid {C['blue']}60;"
                            f"border-radius:10px;padding:14px 18px;margin:6px 0 10px 0'>",
                            unsafe_allow_html=True)
                _default_entry = float(cached_sd["trade"]["entry"]) if cached_sd else 100.0
                _default_cmp   = float(cached_sd["cmp"]) if cached_sd else _default_entry
                bf1, bf2, bf3, bf4 = st.columns([1.5,1.5,1,1])
                with bf1:
                    _ep = st.number_input(f"Entry Price ₹ ({s})", min_value=0.01,
                                          value=_default_cmp, step=0.5, key=f"ep_{s}")
                with bf2:
                    _qty = st.number_input("Qty (shares)", min_value=1, value=10,
                                           step=1, key=f"qty_{s}")
                with bf3:
                    if st.button("✅ Confirm", key=f"confirm_buy_{s}"):
                        add_holding(s, cmp_name, float(_ep), int(_qty))
                        st.session_state.pop(f"buy_modal_{s}", None)
                        st.success(f"{s} added to Holdings!")
                        st.rerun()
                with bf4:
                    if st.button("Cancel", key=f"cancel_buy_{s}"):
                        st.session_state.pop(f"buy_modal_{s}", None)
                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
        with st.expander("📊 Chart & Trade Setup", expanded=False):
            if cached_sd is None or cached_df is None:
                st.warning(f"Could not load data for {s}.")
            else:
                sd2=cached_sd; df2=cached_df; tr2=sd2["trade"]
                v2=sd2["verdict"]; vc2=sd2["vcol"]
                entry_c = C["blue"] if v2=="STRONG BUY" else (C["amber"] if v2=="WATCHLIST" else C["dim"])
                stage_c2= C["green"] if sd2.get("stage")=="2" else (C["amber"] if "1→2" in str(sd2.get("stage","")) else C["red"])
                h1,h2,h3 = st.columns([1.5,1.5,1.5])
                with h1:
                    st.markdown(f"<div style='text-align:center;padding:8px;background:{C['card']};border:1px solid {C['border']};border-radius:8px'>"
                                f"<div style='font-size:11px;color:{C['muted']};font-family:DM Sans'>Score</div>"
                                f"<div style='font-size:22px;font-weight:700;color:{vc2};font-family:JetBrains Mono'>{sd2['total']}</div>"
                                f"<div style='font-size:12px;color:{vc2};font-family:DM Sans'>{v2}</div></div>", unsafe_allow_html=True)
                with h2:
                    st.markdown(f"<div style='text-align:center;padding:8px;background:{C['card']};border:1px solid {C['border']};border-radius:8px'>"
                                f"<div style='font-size:11px;color:{C['muted']};font-family:DM Sans'>Stage</div>"
                                f"<div style='font-size:13px;font-weight:600;color:{stage_c2};font-family:DM Sans'>{sd2.get('stage_label','')}</div>"
                                f"<div style='font-size:11px;color:{C['muted']};font-family:DM Sans'>{'VCP ✓' if sd2.get('vcp') else ''}</div></div>",
                                unsafe_allow_html=True)
                with h3:
                    st.markdown(f"<div style='text-align:center;padding:8px;background:{C['card']};border:1px solid {C['border']};border-radius:8px'>"
                                f"<div style='font-size:11px;color:{C['muted']};font-family:DM Sans'>L1 / L2 / L3</div>"
                                f"<div style='font-size:14px;font-weight:600;color:{C['text']};font-family:JetBrains Mono'>{sd2['l1']} / {sd2['l2']} / {sd2['l3']}</div>"
                                f"<div style='font-size:11px;color:{C['muted']};font-family:DM Sans'>Trend / Mom / Setup</div></div>",
                                unsafe_allow_html=True)
                # ── Hold guidance banner (CPR not used as exit signal) ──────────
                _sl2   = tr2["sl"]
                _st2   = sd2.get("details", {}).get("supertrend_val", None)
                _cpr2  = sd2.get("cpr_signal", "")
                _cpr2_color = {"CONFIRM": C["green"], "NEUTRAL": C["amber"],
                               "CAUTION": C["amber"], "REJECT": C["red"]}.get(_cpr2, C["muted"])
                _exit_msg = f"Hold while price stays above SL ₹{_sl2:,.2f}"
                if _st2:
                    _exit_msg += f" · Supertrend support ₹{_st2:,.2f}"
                _exit_msg += " · Exit on SL breach or Supertrend flip — not on daily CPR change"
                st.markdown(
                    f"<div style='background:rgba(67,97,238,0.08);border:1px solid {C['blue']}40;"
                    f"border-radius:8px;padding:10px 14px;margin-bottom:10px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px'>"
                    f"<span style='font-family:DM Sans,sans-serif;font-size:12px;color:{C['text']}'>"
                    f"📌 <b>Swing Hold</b> — {_exit_msg}</span>"
                    f"<span style='font-family:JetBrains Mono,monospace;font-size:11px;color:{_cpr2_color}'>"
                    f"CPR today: {_cpr2}</span></div>",
                    unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
                tc = [(tr2["entry_label"],f"₹{tr2['entry']:,.2f}",entry_c),("ADR Stop",f"₹{tr2['sl']:,.2f}",C["red"]),
                      ("T1 (70%)",f"₹{tr2['t1']:,.2f}",C["green"]),("T2 (45%)",f"₹{tr2['t2']:,.2f}","#00a86b"),
                      ("T3 Runner",f"₹{tr2['t3']:,.2f}","#00a86b"),("R:R",f"{tr2['rr']}x",C["amber"])]
                setup_html = "".join(f"<div style='flex:1;text-align:center;padding:8px 4px;background:{C['card']};"
                                     f"border:1px solid {C['border']};border-radius:8px;margin:0 3px'>"
                                     f"<div style='font-size:10px;color:{C['muted']};font-family:DM Sans'>{lbl}</div>"
                                     f"<div style='font-size:13px;font-weight:600;color:{col};font-family:JetBrains Mono'>{val}</div></div>"
                                     for lbl,val,col in tc)
                st.markdown(f"<div style='display:flex;gap:0;margin-bottom:12px'>{setup_html}</div>", unsafe_allow_html=True)
                st.markdown(f"<p style='font-family:DM Sans,sans-serif;font-size:11px;color:{C['muted']};margin-bottom:4px'>"
                            f"Daily · 1 Year · EMA 8/13/21/50 · 30-Week MA · Entry/SL/T1/T2/T3</p>", unsafe_allow_html=True)
                st.plotly_chart(make_chart(df2,sd2,s),
                                config={"displayModeBar":True}, key=f"wl_chart_{s}")
                sc_html = "".join(f"<div style='flex:1;text-align:center;padding:6px 4px;background:{C['card']};"
                                  f"border:1px solid {C['border']};border-radius:8px;margin:0 3px'>"
                                  f"<div style='font-size:10px;color:{C['muted']};font-family:DM Sans'>{lbl}</div>"
                                  f"<div style='font-size:12px;font-weight:600;color:{C['green']};font-family:JetBrains Mono'>₹{val:,.2f}</div></div>"
                                  for lbl,val in [("Scale +3%",tr2["scale1"]),("Scale +5%",tr2["scale2"]),("Scale +7%",tr2["scale3"])])
                st.markdown(f"<p style='font-size:11px;color:{C['muted']};font-family:DM Sans;margin:8px 0 4px'>3-5-7 Scaling Levels</p>"
                            f"<div style='display:flex;gap:0;margin-bottom:10px'>{sc_html}</div>", unsafe_allow_html=True)
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

# ── TAB: PORTFOLIO ─────────────────────────────────────────────────────────────
def tab_portfolio(capital, risk_pct, tg_token, tg_chat):
    port = st.session_state.portfolio
    port["capital"] = capital

    # Update live prices & ATR trailing stop
    for sym, pos in port["positions"].items():
        try:
            live = fetch_live_price(sym)
            cmp_ = live["price"] if live["price"] else pos["current_price"]
        except Exception:
            cmp_ = pos["current_price"]
        pos["current_price"] = cmp_
        try:
            df_ = fetch_ohlcv(sym); ind_ = add_indicators(df_)
            atr_ = float(ind_.iloc[-1]["atr"]) if len(ind_) > 0 else 0
        except Exception:
            atr_ = 0
        if atr_ > 0:
            new_tsl = round(cmp_ - 2.0*atr_, 2)
            pos["trailing_sl"] = max(pos.get("trailing_sl",pos["stop_loss"]), new_tsl)
        if cmp_ >= pos["target"] and not pos.get("free_trade"):
            pos["trailing_sl"] = max(pos["trailing_sl"], pos["entry"])
            pos["free_trade"] = True

    invested = sum(p["shares"]*p["current_price"] for p in port["positions"].values())
    total_val = port["cash"] + invested
    realized  = sum(t["pnl"] for t in port["closed_trades"])
    unrealzd  = sum((p["current_price"]-p["entry"])*p["shares"] for p in port["positions"].values())

    k1,k2,k3,k4,k5 = st.columns(5)
    k1.metric("Total Value",  f"₹{total_val:,.0f}", delta=f"{((total_val-capital)/capital*100):+.1f}%")
    k2.metric("Cash",         f"₹{port['cash']:,.0f}")
    k3.metric("Invested",     f"₹{invested:,.0f}")
    k4.metric("Unrealized",   f"₹{unrealzd:,.0f}", delta=f"₹{unrealzd:,.0f}")
    k5.metric("Realized P&L", f"₹{realized:,.0f}")
    st.divider()

    st.markdown("### Open Positions")
    if not port["positions"]:
        st.info("No open positions. Add from Watchlist or manually below.")
    else:
        for sym, pos in list(port["positions"].items()):
            cmp_    = pos["current_price"]
            pnl     = (cmp_-pos["entry"])*pos["shares"]
            pnl_pct = (cmp_-pos["entry"])/pos["entry"]*100
            gain    = pnl_pct/100
            scale_msg = ""
            for lvl,label in [(0.07,"+7%"),(0.05,"+5%"),(0.03,"+3%")]:
                if gain>=lvl: scale_msg=f"⚡ Scale at {label}!"; break
            border = C["green"] if pnl>=0 else C["red"]
            st.markdown(f"<div style='border-left:4px solid {border};padding:0 0 0 12px;'>", unsafe_allow_html=True)
            c1,c2,c3,c4,c5,c6,c7 = st.columns([1.5,0.8,0.8,0.8,0.8,0.8,0.4])
            c1.markdown(f"**{sym}**<br><small style='color:#aaa'>{pos.get('setup','')} {'🎯 FREE TRADE' if pos.get('free_trade') else ''}</small>",
                        unsafe_allow_html=True)
            c2.metric("Entry",    f"₹{pos['entry']:.2f}")
            c3.metric("CMP",      f"₹{cmp_:.2f}", delta=f"{pnl_pct:+.1f}%")
            c4.metric("Trail SL", f"₹{pos['trailing_sl']:.2f}")
            c5.metric("Target",   f"₹{pos['target']:.2f}")
            c6.metric("P&L",      f"₹{pnl:,.0f}", delta=scale_msg if scale_msg else None)
            if c7.button("✕", key=f"cp_{sym}"):
                pnl_close = (cmp_-pos["entry"])*pos["shares"]
                port["cash"] += cmp_*pos["shares"]
                port["closed_trades"].append({**pos,"exit_price":cmp_,
                    "exit_date":datetime.now().strftime("%Y-%m-%d"),
                    "pnl":round(pnl_close,2),"pnl_pct":round(pnl_pct,2),"exit_reason":"Manual"})
                del port["positions"][sym]
                _send_telegram(tg_token,tg_chat,f"📤 *Trade Closed*\n*{sym}* @ ₹{cmp_:.2f}\nP&L: ₹{pnl_close:,.0f} ({pnl_pct:+.1f}%)")
                st.rerun()
            st.markdown("</div><br>", unsafe_allow_html=True)

    with st.expander("➕ Open Position Manually"):
        sym_in = st.text_input("NSE Symbol (e.g. RELIANCE)").upper().strip()
        if sym_in:
            try:
                df_in = fetch_ohlcv(sym_in); ind_in = add_indicators(df_in)
                sd_in = score(ind_in); tr_in = sd_in["trade"]
                sh_in,_ = position_size(port["cash"], tr_in["entry"], tr_in["sl"], risk_pct)
                ci1,ci2,ci3 = st.columns(3)
                e_in = ci1.number_input("Entry ₹", value=float(tr_in["entry"]))
                s_in = ci2.number_input("Stop Loss ₹", value=float(tr_in["sl"]))
                t_in = ci3.number_input("Target T1 ₹", value=float(tr_in["t1"]))
                sh   = st.number_input("Shares", value=sh_in, min_value=1)
                if st.button("Open Position"):
                    cost = e_in*sh
                    if cost <= port["cash"]:
                        setup_lbl = identify_setup_from_score(sd_in)
                        port["positions"][sym_in] = {"symbol":sym_in,"setup":setup_lbl,
                            "entry":e_in,"stop_loss":s_in,"trailing_sl":s_in,"target":t_in,
                            "t2":tr_in["t2"],"t3":tr_in["t3"],"shares":sh,"total_shares":sh,
                            "current_price":e_in,"open_date":datetime.now().strftime("%Y-%m-%d"),"free_trade":False}
                        port["cash"] -= cost
                        st.success(f"Opened {sym_in}: {sh} shares @ ₹{e_in:.2f}"); st.rerun()
                    else: st.error("Insufficient cash.")
            except Exception as e: st.warning(f"Could not fetch data for {sym_in}: {e}")

    if port["closed_trades"]:
        st.divider(); st.markdown("### Closed Trades")
        td = pd.DataFrame(port["closed_trades"])
        cols_show = ["symbol","setup","entry","exit_price","pnl_pct","pnl","exit_reason","exit_date"]
        avail = [c for c in cols_show if c in td.columns]
        td_show = td[avail].copy(); td_show.columns = [c.replace("_"," ").title() for c in avail]
        if "Pnl Pct" in td_show.columns: td_show["Pnl Pct"] = td_show["Pnl Pct"].map(lambda x:f"{x:+.1f}%")
        if "Pnl" in td_show.columns: td_show["Pnl"] = td_show["Pnl"].map(lambda x:f"₹{x:,.0f}")
        st.dataframe(td_show, use_container_width=True)
        wins  = [t["pnl"] for t in port["closed_trades"] if t["pnl"]>0]
        losss = [t["pnl"] for t in port["closed_trades"] if t["pnl"]<=0]
        if port["closed_trades"]:
            m1,m2,m3 = st.columns(3)
            m1.metric("Win Rate", f"{len(wins)/len(port['closed_trades'])*100:.1f}%")
            m2.metric("Avg Win",  f"₹{np.mean(wins):,.0f}"  if wins  else "—")
            m3.metric("Avg Loss", f"₹{np.mean(losss):,.0f}" if losss else "—")

# ── TAB: HOLDINGS ──────────────────────────────────────────────────────────────
def tab_holdings():
    st.markdown("### 📦 My Holdings")
    st.caption("Swing trading exit monitor — scored against ATR Stop, Supertrend, Stage, and targets.")

    holdings = load_holdings()
    nifty_r  = fetch_nifty_3m_return()

    if not holdings:
        st.markdown(f"""
        <div style='text-align:center;padding:60px 20px;background:{C['card']};
                    border:1px solid {C['border']};border-radius:12px;margin-top:1rem'>
            <div style='font-size:40px;margin-bottom:12px'>📦</div>
            <div style='font-size:18px;font-weight:600;color:{C['text']};margin-bottom:8px'>No holdings yet</div>
            <div style='font-size:13px;color:{C['muted']}'>
                Go to <b>Watchlist</b> → click <b>📥 Purchased</b> on any stock to track it here
            </div>
        </div>""", unsafe_allow_html=True)
        return

    # Placeholder at top — filled with real totals after card loop
    _summary_slot = st.empty()
    total_invested = 0.0; total_current_value = 0.0
    hold_count = 0; exit_count = 0; caution_count = 0; partial_count = 0

    # ── Per-holding cards ─────────────────────────────────────────────────────
    for h in holdings:
        sym        = h["symbol"]
        company    = h.get("company", sym)
        entry_px   = float(h.get("entry_price", 0))
        qty        = int(h.get("qty", 1))
        entry_date = h.get("entry_date", "—")

        # Score the stock (monitoring mode — CPR doesn't affect verdict)
        cache_key = f"hld_sd_{sym}"
        if cache_key not in st.session_state:
            try:
                _r = fetch_ohlcv(sym); _i = add_indicators(_r)
                if len(_i) >= 5:
                    _lp = fetch_live_price(sym).get("price", 0.0) or 0.0
                    st.session_state[cache_key] = (score(_i, nifty_ret=nifty_r,
                                                         live_price=_lp, is_entry=False), _i)
            except Exception:
                st.session_state[cache_key] = None

        cached = st.session_state.get(cache_key)
        if cached is None:
            st.warning(f"Could not load data for {sym}")
            continue
        sd, df_h = cached

        cmp        = sd.get("cmp", entry_px)
        pnl        = (cmp - entry_px) * qty
        pnl_pct    = (cmp - entry_px) / max(entry_px, 0.01) * 100
        pnl_color  = C["green"] if pnl >= 0 else C["red"]
        pnl_sign   = "+" if pnl >= 0 else ""

        # Accumulate real portfolio totals using live CMP
        total_invested      += entry_px * qty
        total_current_value += cmp * qty

        sig        = get_hold_exit_signal(sd, entry_px)
        signal     = sig["signal"]
        sig_color  = sig["color"]
        reason     = sig["reason"]
        action     = sig["action"]
        atr_stop   = sig.get("atr_stop", 0)
        tgt1       = sig.get("t1", 0)

        # Count for summary
        if signal == "HOLD":             hold_count    += 1
        elif signal in ("EXIT NOW","EXIT"): exit_count += 1
        elif signal == "CAUTION":        caution_count += 1
        elif signal == "BOOK PARTIAL":   partial_count += 1

        # ── Card ──────────────────────────────────────────────────────────────
        border_color = sig_color
        st.markdown(
            f"<div style='background:{C['card']};border:1.5px solid {hex_rgba(border_color,0.5)};"
            f"border-radius:12px;padding:16px 20px;margin-bottom:12px'>",
            unsafe_allow_html=True)

        h1,h2,h3,h4,h5,h6 = st.columns([1.6,1.4,1.4,1.6,2.8,1.2])
        with h1:
            st.markdown(f"<div style='font-family:JetBrains Mono,monospace;font-size:15px;"
                        f"font-weight:700;color:{C['text']}'>{sym}</div>"
                        f"<div style='font-size:11px;color:{C['muted']};font-family:DM Sans'>{company[:20]}</div>",
                        unsafe_allow_html=True)
        with h2:
            sl_color = C["red"] if atr_stop > 0 and cmp < atr_stop * 1.03 else C["muted"]
            st.markdown(f"<div style='font-size:11px;color:{C['muted']};font-family:DM Sans'>Entry</div>"
                        f"<div style='font-family:JetBrains Mono,monospace;font-size:13px;color:{C['text']}'>₹{entry_px:,.2f}</div>"
                        f"<div style='font-size:10px;color:{sl_color};font-family:DM Sans'>"
                        f"SL ₹{atr_stop:,.2f}</div>",
                        unsafe_allow_html=True)
        with h3:
            st.markdown(f"<div style='font-size:11px;color:{C['muted']};font-family:DM Sans'>CMP</div>"
                        f"<div style='font-family:JetBrains Mono,monospace;font-size:13px;color:{C['text']}'>₹{cmp:,.2f}</div>"
                        f"<div style='font-size:11px;font-weight:600;color:{pnl_color};font-family:JetBrains Mono'>{pnl_sign}{pnl_pct:.1f}%</div>",
                        unsafe_allow_html=True)
        with h4:
            tgt1_pct = round((tgt1 - entry_px) / max(entry_px, 0.01) * 100, 1) if tgt1 else 0
            st.markdown(f"<div style='font-size:11px;color:{C['muted']};font-family:DM Sans'>P&L</div>"
                        f"<div style='font-family:JetBrains Mono,monospace;font-size:13px;color:{pnl_color}'>"
                        f"{pnl_sign}₹{abs(pnl):,.0f}</div>"
                        f"<div style='font-size:10px;color:{C['green']};font-family:DM Sans'>"
                        f"T1 ₹{tgt1:,.2f} (+{tgt1_pct:.1f}%)</div>",
                        unsafe_allow_html=True)
        with h5:
            st.markdown(
                f"<div style='background:{hex_rgba(sig_color,0.1)};border:1px solid {hex_rgba(sig_color,0.4)};"
                f"border-radius:8px;padding:8px 12px'>"
                f"<div style='font-family:DM Sans,sans-serif;font-size:13px;font-weight:700;color:{sig_color}'>"
                f"{signal}</div>"
                f"<div style='font-size:11px;color:{C['text']};font-family:DM Sans;margin-top:3px'>{reason}</div>"
                f"<div style='font-size:10px;color:{C['muted']};font-family:DM Sans;margin-top:4px'>"
                f"→ {action}</div></div>",
                unsafe_allow_html=True)
        with h6:
            if st.button("🔄 Refresh", key=f"ref_hld_{sym}"):
                st.session_state.pop(cache_key, None)
                st.rerun()
            if st.button("✕ Remove", key=f"del_hld_{sym}"):
                remove_holding(sym)
                st.session_state.pop(cache_key, None)
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    # ── Fill portfolio summary at top with real post-loop totals ─────────────
    _tot_pnl     = total_current_value - total_invested
    _tot_pnl_pct = (_tot_pnl / max(total_invested, 0.01)) * 100
    _pnl_clr     = C["green"] if _tot_pnl >= 0 else C["red"]
    _pnl_arrow   = "▲" if _tot_pnl >= 0 else "▼"
    _pnl_sign    = "+" if _tot_pnl >= 0 else ""
    _n           = len(holdings)
    _card_s      = f"background:{C['card']};border:1px solid {C['border']};border-radius:10px;padding:14px 18px;margin-bottom:14px"
    with _summary_slot.container():
        st.markdown(
            f"<div style='font-size:11px;color:{C['muted']};font-family:DM Sans;"
            f"text-transform:uppercase;letter-spacing:0.08em;margin-bottom:6px'>"
            f"Portfolio Summary &nbsp;·&nbsp; {_n} stock{'s' if _n!=1 else ''}</div>",
            unsafe_allow_html=True)
        ps1, ps2, ps3, ps4 = st.columns(4)
        with ps1:
            st.markdown(
                f"<div style='{_card_s}'>"
                f"<div style='font-size:11px;color:{C['muted']};font-family:DM Sans'>Invested</div>"
                f"<div style='font-size:20px;font-weight:700;color:{C['text']};font-family:JetBrains Mono,monospace;margin-top:2px'>"
                f"₹{total_invested:,.0f}</div></div>", unsafe_allow_html=True)
        with ps2:
            st.markdown(
                f"<div style='{_card_s}'>"
                f"<div style='font-size:11px;color:{C['muted']};font-family:DM Sans'>Current Value</div>"
                f"<div style='font-size:20px;font-weight:700;color:{C['text']};font-family:JetBrains Mono,monospace;margin-top:2px'>"
                f"₹{total_current_value:,.0f}</div></div>", unsafe_allow_html=True)
        with ps3:
            st.markdown(
                f"<div style='{_card_s}'>"
                f"<div style='font-size:11px;color:{C['muted']};font-family:DM Sans'>Overall P&amp;L</div>"
                f"<div style='font-size:20px;font-weight:700;color:{_pnl_clr};font-family:JetBrains Mono,monospace;margin-top:2px'>"
                f"{_pnl_sign}₹{abs(_tot_pnl):,.0f}</div></div>", unsafe_allow_html=True)
        with ps4:
            st.markdown(
                f"<div style='{_card_s}'>"
                f"<div style='font-size:11px;color:{C['muted']};font-family:DM Sans'>Returns</div>"
                f"<div style='font-size:20px;font-weight:700;color:{_pnl_clr};font-family:JetBrains Mono,monospace;margin-top:2px'>"
                f"{_pnl_arrow} {abs(_tot_pnl_pct):.2f}%</div></div>", unsafe_allow_html=True)

    # ── Signal counts ──────────────────────────────────────────────────────────
    st.divider()
    sc1,sc2,sc3,sc4 = st.columns(4)
    sc1.metric("✅ Hold",         hold_count)
    sc2.metric("🚨 Exit Signal",  exit_count,    delta="Action needed" if exit_count else None,
               delta_color="inverse" if exit_count else "off")
    sc3.metric("⚠️ Caution",      caution_count)
    sc4.metric("📤 Book Partial", partial_count)

    st.caption("Refresh individual holdings using 🔄 to get latest data. "
               "Exit signals are based on ATR Stop breach, Supertrend flip, and Stage analysis — not daily CPR changes.")

# ── TAB: BACKTEST ──────────────────────────────────────────────────────────────
def tab_backtest():
    st.subheader("📈 Strategy Backtest")
    st.caption("Event-driven backtest. Entry at next day open, exits at Stop or T1.")
    bc1,bc2,bc3 = st.columns(3)
    bt_univ   = bc1.selectbox("Universe", list(SCREENER_LISTS.keys())[:4], key="bt_univ")
    bt_limit  = bc2.number_input("Max stocks", value=30, min_value=5, max_value=150, step=5)
    bt_period = bc3.selectbox("Period", ["1y","2y","3y"], index=1, key="bt_per")
    if st.button("▶ Run Backtest", type="primary"):
        with st.spinner(f"Backtesting {bt_univ} ({bt_limit} stocks)…"):
            res = _run_backtest(SCREENER_LISTS[bt_univ][:bt_limit], bt_period)
        st.session_state.bt_results = res
    if st.session_state.bt_results:
        r = st.session_state.bt_results
        if "error" in r: st.error(r["error"]); return
        m1,m2,m3,m4,m5 = st.columns(5)
        m1.metric("Total Trades",  r["total_trades"])
        m2.metric("Win Rate",      f"{r['win_rate']:.1f}%")
        m3.metric("Avg R:R Won",   f"{r['avg_rr']:.2f}")
        m4.metric("Profit Factor", f"{r['profit_factor']:.2f}")
        m5.metric("Total Return",  f"{r['total_return']:.1f}%")
        m1b,m2b,m3b = st.columns(3)
        m1b.metric("CAGR",         f"{r['cagr']:.1f}%")
        m2b.metric("Max Drawdown", f"{r['max_dd']:.1f}%")
        m3b.metric("Sharpe Ratio", f"{r['sharpe']:.2f}")
        st.markdown("### Strategy Validation")
        checks = [("Win Rate > 40%",r["win_rate"]>40),("Profit Factor > 1.5",r["profit_factor"]>1.5),
                  ("Max Drawdown < 25%",r["max_dd"]<25),("Avg R:R (wins) > 1.5",r["avg_rr"]>1.5),("CAGR > 15%",r["cagr"]>15)]
        for label,ok in checks:
            (st.success if ok else st.error)(f"{'✓' if ok else '✗'}  {label}")
        if r.get("equity"):
            eq_df  = pd.DataFrame(r["equity"])
            fig_eq = go.Figure(go.Scatter(x=list(range(len(eq_df))),y=eq_df["value"],
                fill="tozeroy",line_color=C["green"],name="Portfolio Value"))
            fig_eq.update_layout(title="Equity Curve",height=300,
                plot_bgcolor=C["card"],paper_bgcolor=C["bg"],font_color="white",margin=dict(l=10,r=10,t=40,b=10))
            st.plotly_chart(fig_eq)
        if r.get("trades"):
            st.markdown("### Last 30 Trades")
            tdf = pd.DataFrame(r["trades"][-30:])
            disp_cols = [c for c in ["symbol","setup","entry_date","exit_date","entry","exit","pnl_pct","reason"] if c in tdf.columns]
            st.dataframe(tdf[disp_cols], use_container_width=True)

def _run_backtest(stocks: list, period: str = "2y") -> dict:
    all_trades = []; equity = [{"trade":0,"value":1_000_000}]; cash = 1_000_000
    for sym in stocks:
        try:
            df = fetch_ohlcv(sym, period=period)
            ind = add_indicators(df)
        except Exception: continue
        if len(ind) < 200: continue
        in_trade = False; entry_px = sl = target = 0.0
        for i in range(150, len(ind)-1):
            if in_trade:
                low_  = float(ind["low"].iloc[i])
                high_ = float(ind["high"].iloc[i])
                if low_ <= sl:
                    pnl_pct = round((sl-entry_px)/entry_px*100,2)
                    all_trades.append({"symbol":sym,"setup":_setup_label,
                        "entry_date":str(ind.index[_entry_i]),"exit_date":str(ind.index[i]),
                        "entry":round(entry_px,2),"exit":round(sl,2),"pnl_pct":pnl_pct,"reason":"Stop Loss"})
                    cash += sl*_shares; in_trade = False
                elif high_ >= target:
                    pnl_pct = round((target-entry_px)/entry_px*100,2)
                    all_trades.append({"symbol":sym,"setup":_setup_label,
                        "entry_date":str(ind.index[_entry_i]),"exit_date":str(ind.index[i]),
                        "entry":round(entry_px,2),"exit":round(target,2),"pnl_pct":pnl_pct,"reason":"Target Hit"})
                    cash += target*_shares; in_trade = False
                continue
            df_slice = ind.iloc[:i+1]
            try:
                sd_ = score(df_slice)
                if sd_["verdict"] != "STRONG BUY": continue
                tr_ = sd_["trade"]
                entry_px = float(ind["open"].iloc[i+1])
                sl = tr_["sl"]; target = tr_["t1"]
                if entry_px<=sl or target<=entry_px: continue
                risk_amt = 1_000_000*0.01
                _shares  = max(1, int(risk_amt/(entry_px-sl)))
                if _shares*entry_px > cash: continue
                cash -= _shares*entry_px; in_trade = True
                _setup_label = identify_setup_from_score(sd_)
                _entry_i = i+1; equity.append({"trade":len(all_trades),"value":cash})
            except Exception: continue
    if not all_trades: return {"error":"No trades generated. Try a wider universe or longer period."}
    pnls   = [t["pnl_pct"] for t in all_trades]
    wins   = [p for p in pnls if p>0]; losses = [p for p in pnls if p<=0]
    win_rate = len(wins)/len(pnls)*100 if pnls else 0
    avg_rr   = abs(np.mean(wins)/np.mean(losses)) if wins and losses else 0
    pf       = abs(sum(wins)/sum(losses)) if losses and sum(losses)!=0 else 99
    tot_ret  = float(np.sum(pnls))
    years    = {"1y":1,"2y":2,"3y":3}.get(period,2)
    cagr     = ((1+tot_ret/100)**(1/years)-1)*100 if tot_ret>-100 else -99
    cumul    = pd.Series([1.0]+[(1+p/100) for p in pnls]).cumprod()
    roll_max = cumul.cummax()
    max_dd   = float(abs(((cumul-roll_max)/roll_max).min()*100))
    arr      = np.array(pnls)/100
    sharpe   = float(np.mean(arr)/np.std(arr)*np.sqrt(252)) if np.std(arr)>0 else 0
    return {"total_trades":len(all_trades),"win_rate":win_rate,"avg_rr":avg_rr,
            "profit_factor":pf,"total_return":tot_ret,"cagr":cagr,"max_dd":max_dd,
            "sharpe":sharpe,"trades":all_trades,"equity":equity}

# ── MAIN ──────────────────────────────────────────────────────────────────────────────────
def main():
    _init_state()
    capital, risk_pct, max_pos, max_sl_pct, tg_token, tg_chat = render_sidebar()

    # Header
    st.markdown(f"""
<div style="padding:1rem 0 0.5rem">
  <span style="font-family:'JetBrains Mono',monospace;font-size:22px;color:{C['blue']};font-weight:500">NSE</span>
  <span style="font-family:'DM Sans',sans-serif;font-size:22px;color:{C['text']};font-weight:600"> Swing Trader</span>
  <p style="color:{C['muted']};font-size:13px;margin:3px 0 0;font-family:'DM Sans',sans-serif">
    3-layer swing score &middot; Live NSE data via Yahoo Finance &middot; 3-7 day setups
  </p>
</div>""", unsafe_allow_html=True)

    # Market regime banner
    with st.spinner("Fetching Nifty 50..."):
        index_df = fetch_index()
    regime = get_regime(index_df)
    emoji = {"Bullish":"🟢","Neutral":"🟡","Bearish":"🔴"}.get(regime["regime"],"⚪")
    color = regime["color"]
    st.markdown(
        f"<div style='background:{hex_rgba(color,0.08)};border:1px solid {hex_rgba(color,0.4)};border-radius:8px;"
        f"padding:10px 18px;margin-bottom:14px'>"
        f"<span style='font-size:18px'>{emoji}</span>&nbsp;&nbsp;"
        f"<strong>Market Regime: {regime['regime']}</strong>"
        f"&nbsp;|&nbsp;Nifty: <b>{regime.get('close','—')}</b>"
        f"&nbsp;|&nbsp;30W MA: <b>{regime.get('ma30w','—')}</b>"
        f"&nbsp;|&nbsp;RSI: <b>{regime.get('rsi','—')}</b>"
        f"{'&nbsp;&nbsp;⚠️ <b>Capital Preservation Mode</b>' if regime['regime']=='Bearish' else ''}"
        f"</div>", unsafe_allow_html=True)

    # Load stock list once
    stocks_df = load_nse_stocks()

    t0,t1,t2,t3,t4,t5 = st.tabs(["🔍 Analyse","📊 Screener","👁 Watchlist","📦 Holdings","💼 Portfolio","📈 Backtest"])
    with t0: tab_analyse(stocks_df, capital)
    with t1: tab_screener(stocks_df)
    with t2: tab_watchlist()
    with t3: tab_holdings()
    with t4: tab_portfolio(capital, risk_pct, tg_token, tg_chat)
    with t5: tab_backtest()

if __name__ == "__main__":
    main()
