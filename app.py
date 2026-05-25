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
def strat_ema_trend_pullback(df: pd.DataFrame) -> dict:
    """EMA Trend Pullback: pullback to EMA20 inside uptrend (EMA20>EMA200). BUY/SELL/NEUTRAL."""
    try:
        if len(df) < 30:
            return {"signal": "NEUTRAL", "regime": "unknown", "reason": "Insufficient data", "detail": {}}
        l    = df.iloc[-1]
        cmp  = float(l["close"])
        ema20 = float(l.get("ema21", l.get("ema8", cmp)))
        ema200= float(df["close"].rolling(200, min_periods=50).mean().iloc[-1])
        dist  = (cmp - ema20) / max(ema20, 0.01) * 100
        if ema20 > ema200:
            regime = "trending_up"
            if -1.0 <= dist <= 3.0:
                signal, reason = "BUY",     f"Pullback to EMA20 in uptrend ({dist:+.1f}%)"
            elif dist > 3.0:
                signal, reason = "NEUTRAL", f"Extended above EMA20 (+{dist:.1f}%) — wait"
            else:
                signal, reason = "SELL",    f"Below EMA20 in uptrend ({dist:+.1f}%)"
        else:
            regime = "trending_down"
            signal, reason = "SELL", "EMA20 < EMA200 — downtrend structure"
        return {"signal": signal, "regime": regime, "reason": reason,
                "detail": {"ema20": round(ema20,2), "ema200": round(ema200,2), "dist_pct": round(dist,2)}}
    except Exception:
        return {"signal": "NEUTRAL", "regime": "unknown", "reason": "Error", "detail": {}}


def strat_rsi_mean_reversion(df: pd.DataFrame) -> dict:
    """RSI Mean Reversion: RSI pulled back to 40-55 = healthy pullback buy zone."""
    try:
        if len(df) < 20:
            return {"signal": "NEUTRAL", "regime": "ranging", "reason": "Insufficient data", "detail": {}}
        l    = df.iloc[-1]
        rsi  = float(l["rsi"])
        adx  = float(l.get("adx", 20))
        ema50= float(df["close"].rolling(50, min_periods=20).mean().iloc[-1])
        cmp  = float(l["close"])
        dist_ema50 = (cmp - ema50) / max(ema50, 0.01) * 100
        regime = "ranging" if adx < 25 else "trending"
        if   40 <= rsi <= 55: signal, reason = "BUY",     f"RSI {rsi:.1f} — mean-reversion zone"
        elif 55 < rsi <= 65:  signal, reason = "NEUTRAL", f"RSI {rsi:.1f} — moderate, wait for pullback"
        elif rsi > 70:        signal, reason = "SELL",    f"RSI {rsi:.1f} — overbought"
        elif rsi < 30:        signal, reason = "SELL",    f"RSI {rsi:.1f} — oversold into weakness"
        else:                 signal, reason = "NEUTRAL", f"RSI {rsi:.1f} — neutral zone"
        return {"signal": signal, "regime": regime, "reason": reason,
                "detail": {"rsi": round(rsi,1), "ema50": round(ema50,2),
                           "dist_ema50_pct": round(dist_ema50,2), "adx": round(adx,1)}}
    except Exception:
        return {"signal": "NEUTRAL", "regime": "ranging", "reason": "Error", "detail": {}}


def strat_bollinger_squeeze(df: pd.DataFrame) -> dict:
    """BB Squeeze: width < 20th pct = energy coiling. BUY at lower band, SELL at upper+expanding."""
    try:
        if len(df) < 25:
            return {"signal": "NEUTRAL", "regime": "normal", "reason": "Insufficient data", "detail": {}}
        l       = df.iloc[-1]
        bb_u    = float(l["bb_upper"]); bb_l = float(l["bb_lower"]); bb_m = float(l["bb_mid"])
        cmp     = float(l["close"])
        bb_w    = (bb_u - bb_l) / max(bb_m, 0.01)
        hist_w  = ((df["bb_upper"] - df["bb_lower"]) / df["bb_mid"].replace(0, 0.001)).tail(50)
        rank    = float((hist_w < bb_w).mean() * 100)
        pvb     = (cmp - bb_m) / max(bb_u - bb_m, 0.01)
        squeeze = rank < 20
        regime  = "squeeze" if squeeze else ("expanding" if rank > 70 else "normal")
        if squeeze and pvb <= 0.2:
            signal, reason = "BUY",     f"BB Squeeze ✓ (rank {rank:.0f}%) — coiling at mid/lower band"
        elif squeeze and pvb > 0.5:
            signal, reason = "NEUTRAL", f"BB Squeeze ✓ but near upper band — wait"
        elif rank > 70 and pvb > 0.8:
            signal, reason = "SELL",    f"BB expanding at upper band (rank {rank:.0f}%) — blow-off risk"
        else:
            signal, reason = "NEUTRAL", f"BB rank {rank:.0f}%, price at {pvb*100:.0f}% of band"
        return {"signal": signal, "regime": regime, "reason": reason,
                "detail": {"bb_width_rank": round(rank,1), "price_vs_bands": round(pvb,3),
                           "squeeze": squeeze, "vol": round(float(l.get("vol_ratio",1)),2)}}
    except Exception:
        return {"signal": "NEUTRAL", "regime": "normal", "reason": "Error", "detail": {}}


def strat_fair_value_gap(df: pd.DataFrame) -> dict:
    """Fair Value Gap (ICT): 3-candle imbalance acting as support/resistance."""
    try:
        if len(df) < 10:
            return {"signal": "NEUTRAL", "regime": "no_imbalance", "reason": "Insufficient data", "detail": {}}
        cmp = float(df["close"].iloc[-1])
        bull_fvgs, bear_fvgs = [], []
        lb = df.tail(20)
        for i in range(1, len(lb) - 1):
            ph = float(lb.iloc[i-1]["high"]); pl = float(lb.iloc[i-1]["low"])
            nh = float(lb.iloc[i+1]["high"]); nl = float(lb.iloc[i+1]["low"])
            if ph < nl and (ph + nl)/2 < cmp * 0.99:
                bull_fvgs.append({"low": round(ph,2), "high": round(nl,2), "mid": round((ph+nl)/2,2)})
            if pl > nh and (pl + nh)/2 > cmp * 1.01:
                bear_fvgs.append({"low": round(nh,2), "high": round(pl,2), "mid": round((pl+nh)/2,2)})
        if bull_fvgs:
            n = sorted(bull_fvgs, key=lambda x: abs(x["mid"]-cmp))[0]
            return {"signal": "BUY",  "regime": "imbalance_support",
                    "reason": f"Bullish FVG support @ {n['low']:,.2f}–{n['high']:,.2f}",
                    "detail": {"bullish_fvgs": bull_fvgs[:3], "bearish_fvgs": bear_fvgs[:3], "nearest": n}}
        if bear_fvgs:
            n = sorted(bear_fvgs, key=lambda x: abs(x["mid"]-cmp))[0]
            return {"signal": "SELL", "regime": "imbalance_resistance",
                    "reason": f"Bearish FVG resistance @ {n['low']:,.2f}–{n['high']:,.2f}",
                    "detail": {"bullish_fvgs": bull_fvgs[:3], "bearish_fvgs": bear_fvgs[:3], "nearest": n}}
        return {"signal": "NEUTRAL", "regime": "no_imbalance",
                "reason": "No unfilled FVGs in last 20 bars", "detail": {"bullish_fvgs":[], "bearish_fvgs":[], "nearest":{}}}
    except Exception:
        return {"signal": "NEUTRAL", "regime": "no_imbalance", "reason": "Error", "detail": {}}


def strat_macd_momentum(df: pd.DataFrame) -> dict:
    """MACD Momentum: histogram direction and signal-line crossovers."""
    try:
        if len(df) < 30:
            return {"signal": "NEUTRAL", "regime": "neutral", "reason": "Insufficient data", "detail": {}}
        l = df.iloc[-1]; p = df.iloc[-2]
        ml  = float(l.get("macd_line", l.get("macd", 0)) or 0)
        sl  = float(l.get("macd_signal", l.get("macd_sig", 0)) or 0)
        hist= float(l["macd_hist"]); ph = float(p["macd_hist"])
        pm  = float(p.get("macd_line", p.get("macd", 0)) or 0)
        ps  = float(p.get("macd_signal", p.get("macd_sig", 0)) or 0)
        cup = (ml > sl) and (pm <= ps)
        cdn = (ml < sl) and (pm >= ps)
        if   cup:                signal, reason, regime = "BUY",     "MACD crossed above signal ✓", "bullish"
        elif cdn:                signal, reason, regime = "SELL",    "MACD crossed below signal", "bearish"
        elif hist > 0 and hist > ph: signal, reason, regime = "BUY", f"Histogram rising & positive ({hist:+.3f})", "bullish"
        elif hist < 0 and hist < ph: signal, reason, regime = "SELL", f"Histogram falling & negative ({hist:+.3f})", "bearish"
        elif hist > 0:           signal, reason, regime = "NEUTRAL", "MACD positive but slowing", "neutral"
        else:                    signal, reason, regime = "NEUTRAL", "No MACD edge", "neutral"
        return {"signal": signal, "regime": regime, "reason": reason,
                "detail": {"macd": round(ml,4), "signal_line": round(sl,4),
                           "hist": round(hist,4), "prev_hist": round(ph,4),
                           "cross_up": cup, "cross_dn": cdn}}
    except Exception:
        return {"signal": "NEUTRAL", "regime": "neutral", "reason": "Error", "detail": {}}


def detect_wyckoff_spring(df: pd.DataFrame, support: list) -> tuple:
    """
    Wyckoff Spring: price briefly punches BELOW a key support level (stop-hunt)
    then closes back ABOVE it — high-conviction institutional absorption.

    Returns (hit: bool, label: str, spring_low: float)
    """
    try:
        if len(df) < 10 or not support:
            return False, "", 0.0

        # Use the nearest significant support below current price
        cmp = float(df["close"].iloc[-1])
        key_sups = sorted([s for s in support if s < cmp * 1.03], reverse=True)
        if not key_sups:
            return False, "", 0.0
        key_s = key_sups[0]

        # Look back up to 10 bars for the spring candle
        lookback = df.tail(10)
        for i in range(len(lookback) - 1, -1, -1):
            row = lookback.iloc[i]
            low_v   = float(row["low"])
            close_v = float(row["close"])
            high_v  = float(row["high"])

            # Conditions:
            # 1. Wick punched below support (false breakdown)
            # 2. Candle closed back above support (recovery)
            # 3. Close is in the upper 40% of the candle (bullish close)
            # 4. Volume is not panic-dump level (vol_ratio < 4x — we want absorption, not capitulation)
            candle_range = max(high_v - low_v, 0.01)
            close_pct    = (close_v - low_v) / candle_range

            if (low_v < key_s * 0.999 and
                    close_v > key_s * 1.001 and
                    close_pct >= 0.40):
                # Extra check: volume should be elevated but not panic-extreme
                vr = float(row.get("vol_ratio", 1.0)) if hasattr(row, "get") else 1.0
                try:
                    vr = float(lookback["vol_ratio"].iloc[i])
                except Exception:
                    vr = 1.0
                if vr < 5.0:   # absorbed, not dumped
                    spring_low = round(low_v, 2)
                    bars_ago   = len(lookback) - 1 - i
                    label = (f"Wyckoff Spring @ ₹{spring_low:,.2f} "
                             f"({'today' if bars_ago == 0 else f'{bars_ago}d ago'}) — institutional stop-hunt absorbed")
                    return True, label, spring_low

        return False, "", 0.0
    except Exception:
        return False, "", 0.0


def detect_volume_dryup(df: pd.DataFrame) -> tuple:
    """
    Volume Dry-Up (Float Lockup): 5-day avg volume drops below 50% of 20-day avg
    AND price range stays tight (< 4% move over 5 days).

    Strong hands have absorbed the float — spring-loaded for the next move.
    Returns (hit: bool, label: str)
    """
    try:
        if len(df) < 22:
            return False, ""

        vol_5d  = float(df["volume"].tail(5).mean())
        vol_20d = float(df["volume"].tail(20).mean())
        if vol_20d == 0:
            return False, ""

        vol_ratio = vol_5d / vol_20d

        hi5 = float(df["high"].tail(5).max())
        lo5 = float(df["low"].tail(5).min())
        price_range_pct = (hi5 - lo5) / max(lo5, 0.01) * 100

        if vol_ratio < 0.50 and price_range_pct < 4.0:
            label = (f"Volume Dry-Up ✓ — 5d vol is {vol_ratio*100:.0f}% of norm, "
                     f"price range {price_range_pct:.1f}% (float locked up)")
            return True, label

        return False, ""
    except Exception:
        return False, ""


def detect_absorption(df: pd.DataFrame) -> tuple:
    """
    Institutional Absorption: high-volume DOWN bars where close is in the
    upper 50% of the candle — sellers are hitting bids but price barely moves.
    Institutions are silently absorbing every sell order.

    Returns (hit: bool, label: str)
    """
    try:
        if len(df) < 10:
            return False, ""

        lookback    = df.tail(10)
        vol_20d_avg = float(df["volume"].tail(20).mean()) if len(df) >= 20 else float(df["volume"].mean())
        if vol_20d_avg == 0:
            return False, ""

        absorb_count = 0
        for i in range(len(lookback)):
            row    = lookback.iloc[i]
            open_v = float(row["open"])
            close_v= float(row["close"])
            high_v = float(row["high"])
            low_v  = float(row["low"])
            vol_v  = float(row["volume"])

            candle_range = max(high_v - low_v, 0.01)
            close_pct    = (close_v - low_v) / candle_range   # 0=wick bottom, 1=wick top

            # Down bar (close < open), high volume (≥ 1.3x avg), closes in upper half
            if (close_v < open_v and
                    vol_v >= vol_20d_avg * 1.3 and
                    close_pct >= 0.50):
                absorb_count += 1

        if absorb_count >= 2:
            label = (f"Absorption Pattern ✓ — {absorb_count} high-vol down bars closing "
                     f"in upper half over last 10 sessions (institutions absorbing supply)")
            return True, label

        return False, ""
    except Exception:
        return False, ""


def score(df: pd.DataFrame, nifty_ret: float = 0.0, live_price: float = 0.0, is_entry: bool = True) -> dict:
    """
    is_entry=True  → strategy confluence filter applies for new entries.
    is_entry=False → strategies shown as info only, no verdict change (monitoring holds).
    """
    l = df.iloc[-1]; p = df.iloc[-2]; r5 = df.tail(5)
    support, resistance = find_sr(df)
    pattern  = candle_pattern(df)
    stage_code, stage_label = detect_stage(df)
    vcp_hit, vcp_label      = detect_vcp(df)
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

    # ── Institutional Pattern Bonus (L3 extensions — capped at 25 total) ─────
    spring_hit,  spring_label,  spring_low = detect_wyckoff_spring(df, support)
    voldry_hit,  voldry_label              = detect_volume_dryup(df)
    absorb_hit,  absorb_label              = detect_absorption(df)

    if spring_hit:
        l3 += 8
        details["spring"] = {
            "label": "Wyckoff Spring (Stop-Hunt Reversal)",
            "value": spring_label,
            "score": 8, "max": 8, "status": "green",
        }
    if voldry_hit:
        l3 += 5
        details["voldry"] = {
            "label": "Volume Dry-Up (Float Lockup)",
            "value": voldry_label,
            "score": 5, "max": 5, "status": "green",
        }
    if absorb_hit:
        l3 += 4
        details["absorption"] = {
            "label": "Absorption (Institutional Supply Absorption)",
            "value": absorb_label,
            "score": 4, "max": 4, "status": "green",
        }
    l3 = min(l3, 25)   # hard cap

    # ── Strategy Confluence (5 independent strategies) ─────────────────────
    strats = {
        "EMA Trend Pullback": strat_ema_trend_pullback(df),
        "RSI Mean Reversion": strat_rsi_mean_reversion(df),
        "Bollinger Squeeze":  strat_bollinger_squeeze(df),
        "Fair Value Gap":     strat_fair_value_gap(df),
        "MACD Momentum":      strat_macd_momentum(df),
    }
    buy_count  = sum(1 for s in strats.values() if s["signal"] == "BUY")
    sell_count = sum(1 for s in strats.values() if s["signal"] == "SELL")
    total_strats = len(strats)

    if   buy_count == 5: conf_pts = 15
    elif buy_count == 4: conf_pts = 10
    elif buy_count == 3: conf_pts =  6
    elif buy_count == 2: conf_pts =  3
    elif buy_count == 1: conf_pts =  1
    else:                conf_pts =  0
    if sell_count >= 4:  conf_pts -= 10
    elif sell_count >= 3:conf_pts -=  6
    elif sell_count >= 2:conf_pts -=  3

    conf_label  = f"{buy_count}/{total_strats} BUY  ·  {sell_count}/{total_strats} SELL"
    conf_status = "green" if buy_count >= 3 else ("amber" if buy_count >= 2 else "red")
    details["confluence"] = {
        "label": "Strategy Confluence (5 strategies)", "value": conf_label,
        "score": conf_pts, "max": 15, "status": conf_status, "strategies": strats,
    }

    # ── Score assembly ────────────────────────────────────────────────────────
    raw = l1 + l2 + l3 + conf_pts
    if stage_code=="4":   total=min(raw,40); capped=True
    elif stage_code=="3": total=min(raw,50); capped=True
    elif l1<20:           total=min(raw,50); capped=True
    elif l1<30 or recent_bearish: total=min(raw,68); capped=True
    else:                 total=raw; capped=False

    if total>=75:   verdict,vcol = "STRONG BUY", C["green"]
    elif total>=55: verdict,vcol = "WATCHLIST",  C["amber"]
    else:           verdict,vcol = "AVOID",       C["red"]

    # ── Strategy confluence filter (new entries only) ───────────────────────
    conf_downgraded = False
    if is_entry:
        if sell_count >= 3 and buy_count == 0:
            if verdict == "STRONG BUY":
                verdict, vcol = "WATCHLIST", C["amber"]; conf_downgraded = True
            elif verdict == "WATCHLIST":
                verdict, vcol = "AVOID",     C["red"];   conf_downgraded = True
        elif sell_count >= 4 and verdict == "STRONG BUY":
            verdict, vcol = "WATCHLIST", C["amber"]; conf_downgraded = True

    atr  = float(l["atr"])
    cmp  = float(l["close"])
    adr  = float(l["adr5"]) if not pd.isna(l.get("adr5",float("nan"))) else atr
    mdr  = float(l["mdr"])  if not pd.isna(l.get("mdr", float("nan"))) else atr*1.5

    # ── Institutional entry logic ─────────────────────────────────────────────
    # Institutions accumulate WITHIN the base near support/EMA, not at breakouts.
    # Breakout chasing = retail trap. Smart money has already loaded before the move.
    ema21_val = float(l.get("ema21", 0) or 0)
    ema50_val = float(l.get("ema50", l.get("ma150", 0)) or 0)
    bb_mid_v  = float(l.get("bb_mid", cmp) or cmp)
    breakout_trigger = 0.0   # stored separately as confirmation level

    if verdict=="STRONG BUY":
        # Wyckoff Spring on a STRONG BUY = highest-conviction institutional entry
        if spring_hit and spring_low > 0:
            entry  = round(spring_low * 1.001, 2)
            elabel = "Entry (Wyckoff Spring — institutional demand confirmed)"
        else:
            # Price AT or just above support — enter on limit near demand zone
            near_s = sorted([s for s in support if s < cmp*0.998], reverse=True)
            entry  = round(near_s[0]*1.002, 2) if near_s and (cmp-near_s[0])/cmp < 0.04 else round(cmp-0.4*adr, 2)
            elabel = "Entry (demand zone)"
        triggers = sorted([r for r in resistance if r > cmp*1.003])
        breakout_trigger = triggers[0] if triggers else round(cmp*1.03, 2)

    elif verdict=="WATCHLIST":
        # Wyckoff Spring = highest-conviction entry, overrides all other labels
        if spring_hit and spring_low > 0:
            entry  = round(spring_low * 1.001, 2)
            elabel = "Accumulate (Wyckoff Spring — institutional stop-hunt zone)"
        else:
            # Institutional accumulation: build position INSIDE the base, NOT at breakout
            # Priority 1 — Support within base (2–8% below CMP): institutional limit zone
            base_sup = sorted([s for s in support if cmp*0.92 <= s <= cmp*0.999], reverse=True)
            # Priority 2 — EMA21 pullback: institutions add at rising EMA21 (< CMP by 2%+)
            ema21_pb = ema21_val if ema21_val > 0 and cmp > ema21_val*1.02 else 0
            # Priority 3 — EMA50 pullback: deeper pullback accumulation
            ema50_pb = ema50_val if ema50_val > 0 and cmp > ema50_val*1.02 and ema21_pb == 0 else 0
            # Priority 4 — BB midline: fair-value accumulation when BB is contracting
            bb_entry = bb_mid_v if bb_mid_v > 0 and cmp > bb_mid_v*1.015 else 0

            if base_sup:
                entry  = round(base_sup[0]*1.001, 2)
                elabel = "Accumulate (near base support)"
            elif ema21_pb > 0:
                entry  = round(ema21_pb*1.001, 2)
                elabel = "Accumulate (EMA21 pullback)"
            elif ema50_pb > 0:
                entry  = round(ema50_pb*1.001, 2)
                elabel = "Accumulate (EMA50 pullback)"
            elif bb_entry > 0:
                entry  = round(bb_entry, 2)
                elabel = "Accumulate (BB mid / fair value)"
            else:
                entry  = round(cmp - 0.35*adr, 2)
                elabel = "Accumulate (slight pullback)"

        # Breakout trigger = confirmation level (shown separately, NOT the entry)
        triggers = sorted([r for r in resistance if r > cmp*1.003])
        breakout_trigger = triggers[0] if triggers else round(cmp*1.02, 2)

    else:
        entry  = round(cmp-0.5*adr, 2); elabel = "Entry (N/A)"

    # SL: below demand zone, not below entry — tighter institutional stop
    if verdict in ("STRONG BUY","WATCHLIST") and entry > 0:
        sl_sup = sorted([s for s in support if s < entry*0.999], reverse=True)
        sl = round(sl_sup[0]*0.998, 2) if sl_sup and (entry-sl_sup[0])/entry < 0.06 else round(entry-0.4*adr, 2)
    else:
        sl = round(entry-0.5*adr, 2)

    t1 = round(entry+0.75*mdr, 2)
    t2 = round(entry+1.00*mdr, 2)
    t3 = round(entry+1.50*mdr, 2)
    rr = round((t1-entry)/max(entry-sl, 0.01), 2)

    bb_pct = float((l["close"]-l["bb_lower"])/max(l["bb_upper"]-l["bb_lower"],0.01)*100)
    return {
        "total":total,"raw":raw,"capped":capped,"l1":l1,"l2":l2,"l3":l3,
        "verdict":verdict,"vcol":vcol,"details":details,
        "support":support,"resistance":resistance,
        "stage":stage_code,"stage_label":stage_label,
        "vcp":vcp_hit,"vcp_label":vcp_label,"cmp":cmp,
        "trade":{"entry":entry,"entry_label":elabel,"sl":sl,"t1":t1,"t2":t2,"t3":t3,"rr":rr,
                 "atr":round(atr,2),"adr":round(adr,2),"mdr":round(mdr,2),
                 "breakout_trigger":round(breakout_trigger,2),
                 "scale1":round(entry*1.03,2),"scale2":round(entry*1.05,2),"scale3":round(entry*1.07,2)},
        "bb_pct":round(bb_pct,1),"rsi":rsi,"adx":adx_val,
        "rs_vs_nifty":round(rs_vs_nifty,1),"vol_ratio":vr,
        "bb_width":round(float((l["bb_upper"]-l["bb_lower"])/l["bb_mid"]),4),
        "conf_pts": conf_pts, "buy_count": buy_count, "sell_count": sell_count,
        "conf_downgraded": conf_downgraded, "strats": strats,
        "spring_hit": spring_hit, "spring_label": spring_label, "spring_low": spring_low,
        "voldry_hit": voldry_hit, "voldry_label": voldry_label,
        "absorb_hit": absorb_hit, "absorb_label": absorb_label,
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
            st.session_state["_holdings_src"] = "supabase"
            return rows if rows else []
        except Exception as e:
            st.session_state["_holdings_src"] = "supabase_error"
    else:
        st.session_state["_holdings_src"] = "no_supabase"

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
    hl = [h for h in hl if h["symbol"] != symbol]
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
                "Buy Signals": sd.get("buy_count", 0),
                "Sell Signals": sd.get("sell_count", 0),
                "Confluence": f"{sd.get('buy_count',0)}/{len(sd.get('strats',{}))} BUY"}
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
        bt_line = ""
        if sd["verdict"] == "WATCHLIST" and tr.get("breakout_trigger", 0) > 0:
            bt_line = kpi_row("⚡ Breakout Confirm above", f"₹{tr['breakout_trigger']:,.2f}", C["amber"])
        trade_html = (kpi_row(tr["entry_label"],      f"₹{tr['entry']:,.2f}", entry_col) +
                      kpi_row("Stop Loss (below demand)", f"₹{tr['sl']:,.2f}", C["red"]) +
                      bt_line +
                      kpi_row("T1 — Book 70%",        f"₹{tr['t1']:,.2f}",    C["green"]) +
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
    if "confluence" in sd["details"]:
        d_conf = sd["details"]["confluence"]
        st.markdown(pill_html(d_conf["label"], d_conf["value"],
                              max(d_conf["score"],0), d_conf["max"], d_conf["status"]),
                    unsafe_allow_html=True)

    # ── Strategy Confluence Panel ──────────────────────────────────────────────
    strats_d = sd.get("strats", {})
    if strats_d:
        st.markdown("<hr>", unsafe_allow_html=True)
        buy_c   = sd.get("buy_count",  0)
        sell_c  = sd.get("sell_count", 0)
        n_s     = len(strats_d)
        c_down  = sd.get("conf_downgraded", False)
        agg_col = C["green"] if buy_c >= 3 else (C["amber"] if buy_c >= 2 else C["red"])
        agg_ico = "✅" if buy_c >= 3 else ("🟡" if buy_c >= 2 else "🔴")
        _dh     = (f"<div style='font-size:12px;color:{C['red']};margin-top:4px;font-family:DM Sans'>"
                   f"⬇ Verdict downgraded — bearish strategy confluence</div>") if c_down else ""
        st.markdown(
            f"<div style='background:{hex_rgba(agg_col,0.10)};border:2px solid {hex_rgba(agg_col,0.5)};"
            f"border-radius:12px;padding:14px 20px;margin-bottom:14px;display:flex;align-items:center;gap:16px'>"
            f"<span style='font-size:28px'>{agg_ico}</span>"
            f"<div><div style='font-family:JetBrains Mono,monospace;font-size:18px;font-weight:700;color:{agg_col}'>"
            f"Strategy Confluence: {buy_c}/{n_s} BUY · {sell_c}/{n_s} SELL</div>"
            f"<div style='font-family:DM Sans,sans-serif;font-size:13px;color:{C['muted']};margin-top:2px'>"
            f"{'Strong agreement — high-conviction setup ✓' if buy_c >= 4 else 'Partial agreement — review signals below' if buy_c >= 2 else 'Bearish consensus — avoid long entries'}"
            f"</div>{_dh}</div></div>",
            unsafe_allow_html=True)

        st.markdown(
            f"<p style='font-family:DM Sans;font-size:12px;font-weight:500;color:{C['muted']};"
            f"text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px'>"
            f"Individual Strategy Signals</p>", unsafe_allow_html=True)

        sig_col_map = {{"BUY": C["green"], "SELL": C["red"], "NEUTRAL": C["amber"]}}
        sig_ico_map = {{"BUY": "🟢", "SELL": "🔴", "NEUTRAL": "🟡"}}
        strat_cols  = st.columns(n_s)
        for ci, (sname, sdata) in enumerate(strats_d.items()):
            ss = sdata.get("signal","NEUTRAL"); sr = sdata.get("reason","")
            sc = sig_col_map.get(ss, C["muted"]); sico = sig_ico_map.get(ss, "🟡")
            srg = sdata.get("regime","")
            with strat_cols[ci]:
                st.markdown(
                    f"<div style='background:{C['card']};border:1px solid {hex_rgba(sc,0.4)};"
                    f"border-radius:10px;padding:12px 14px;height:100%'>"
                    f"<div style='font-size:10px;color:{C['muted']};font-family:DM Sans;margin-bottom:4px'>{sname}</div>"
                    f"<div style='font-size:14px;font-weight:700;color:{sc};font-family:JetBrains Mono'>{sico} {ss}</div>"
                    f"<div style='font-size:10px;color:{C['text']};font-family:DM Sans;margin-top:5px'>{sr}</div>"
                    f"<div style='font-size:10px;color:{C['dim']};font-family:DM Sans;font-style:italic;margin-top:3px'>{srg}</div>"
                    f"</div>", unsafe_allow_html=True)

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

    _src = st.session_state.get("_holdings_src", "")
    if _src == "supabase_error":
        st.warning("⚠️ Could not connect to Supabase — showing local data only. Check your SUPABASE_URL / SUPABASE_KEY secrets.")
    elif _src == "no_supabase":
        st.info("💡 No Supabase configured — holdings won't persist across reloads. Add SUPABASE_URL + SUPABASE_KEY in Streamlit Secrets.")

    if not holdings:
        st.markdown(f"""
        <div style='text-align:center;padding:40px 20px;background:{C['card']};
                    border:1px solid {C['border']};border-radius:12px;margin-top:1rem'>
            <div style='font-size:40px;margin-bottom:12px'>📦</div>
            <div style='font-size:18px;font-weight:600;color:{C['text']};margin-bottom:8px'>No holdings yet</div>
            <div style='font-size:13px;color:{C['muted']}'>
                Go to <b>Watchlist</b> → click <b>📥 Purchased</b> on any stock to track it here
            </div>
        </div>""", unsafe_allow_html=True)

        st.markdown("#### ➕ Re-add a Holding Manually")
        st.caption("Use this if your holdings were lost after a redeploy.")
        ra1, ra2, ra3, ra4 = st.columns(4)
        ra_sym   = ra1.text_input("NSE Symbol",    key="ra_sym",   placeholder="e.g. ADVAIT").upper().strip()
        ra_entry = ra2.number_input("Entry Price ₹", key="ra_entry", min_value=0.01, value=100.0, step=0.5)
        ra_qty   = ra3.number_input("Qty",           key="ra_qty",   min_value=1,    value=1,     step=1)
        ra_co    = ra4.text_input("Company name",  key="ra_co",    placeholder="optional")
        if st.button("💾 Save Holding", key="ra_save", type="primary"):
            if ra_sym:
                co = ra_co or ra_sym
                add_holding(ra_sym, co, float(ra_entry), int(ra_qty))
                st.success(f"Added {ra_sym} @ ₹{ra_entry:,.2f}")
                st.rerun()
            else:
                st.error("Enter a symbol first.")
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
                f"<div style='{_card_s};border-left:3px solid {_pnl_clr}'>"
                f"<div style='font-size:11px;color:{C['muted']};font-family:DM Sans'>Overall P&L</div>"
                f"<div style='font-size:20px;font-weight:700;color:{_pnl_clr};font-family:JetBrains Mono,monospace;margin-top:2px'>"
                f"{_pnl_sign}₹{abs(_tot_pnl):,.0f}</div></div>", unsafe_allow_html=True)
        with ps4:
            st.markdown(
                f"<div style='{_card_s};border-left:3px solid {_pnl_clr}'>"
                f"<div style='font-size:11px;color:{C['muted']};font-family:DM Sans'>Returns</div>"
                f"<div style='font-size:20px;font-weight:700;color:{_pnl_clr};font-family:JetBrains Mono,monospace;margin-top:2px'>"
                f"{_pnl_arrow}&nbsp;{abs(_tot_pnl_pct):.2f}%</div></div>", unsafe_allow_html=True)

    # Summary badge row
    badge_items = []
    if hold_count:    badge_items.append(f"<span style='color:{C['green']};font-weight:600'>● HOLD {hold_count}</span>")
    if partial_count: badge_items.append(f"<span style='color:{C['amber']};font-weight:600'>◑ BOOK PARTIAL {partial_count}</span>")
    if caution_count: badge_items.append(f"<span style='color:{C['amber']};font-weight:600'>⚠ CAUTION {caution_count}</span>")
    if exit_count:    badge_items.append(f"<span style='color:{C['red']};font-weight:600'>✕ EXIT {exit_count}</span>")
    if badge_items:
        st.markdown(
            "<div style='display:flex;gap:18px;flex-wrap:wrap;margin-bottom:8px'>" +
            "  ".join(badge_items) + "</div>",
            unsafe_allow_html=True)

    with st.expander("➕ Add / Update Holding"):
        a1, a2, a3, a4 = st.columns(4)
        add_sym   = a1.text_input("NSE Symbol", key="add_hld_sym", placeholder="e.g. WIPRO").upper().strip()
        add_entry = a2.number_input("Entry Price ₹", key="add_hld_entry", min_value=0.01, value=100.0, step=0.5)
        add_qty   = a3.number_input("Qty", key="add_hld_qty", min_value=1, value=1, step=1)
        add_co    = a4.text_input("Company", key="add_hld_co", placeholder="optional")
        if st.button("💾 Save", key="add_hld_save", type="primary"):
            if add_sym:
                add_holding(add_sym, add_co or add_sym, float(add_entry), int(add_qty))
                st.success(f"Saved {add_sym} @ ₹{add_entry:,.2f}"); st.rerun()
            else:
                st.error("Enter a symbol.")


# ── TAB: BACKTEST ──────────────────────────────────────────────────────────────
def tab_backtest():
    st.markdown("### 🧪 Strategy Backtest")
    st.caption("Walk-forward validation · 70% train / 30% test split · signals from full scoring engine")

    with st.expander("ℹ️ How the backtest works", expanded=False):
        st.markdown(
            "- Signals are generated using the **same 3-layer scoring engine** (L1 Trend + L2 Momentum + L3 Setup).\n"
            "- Entry is simulated at **next-day open** to avoid look-ahead bias.\n"
            "- Exit on **ATR trailing stop** (2×ATR) or **T1 target** hit, whichever comes first.\n"
            "- **Walk-forward split**: first 70% of dates = train, last 30% = test.\n"
            "- Thresholds: CAGR > 15% · Win rate > 40% · Max drawdown < 25% · R:R ≥ 1:2"
        )

    bt_results = st.session_state.get("bt_results")

    symbols_input = st.text_area(
        "NSE Symbols (comma-separated)",
        value="RELIANCE,TCS,INFY,HDFCBANK,ICICIBANK",
        height=68,
    )
    bt_capital = st.number_input("Starting Capital (₹)", value=1_000_000, step=50_000)

    if st.button("▶ Run Backtest", type="primary"):
        symbols = [s.strip().upper() for s in symbols_input.split(",") if s.strip()]
        if not symbols:
            st.error("Enter at least one symbol.")
        else:
            with st.spinner("Fetching data and running simulation…"):
                stock_data = {}
                errors = []
                prog = st.progress(0)
                for idx_s, sym in enumerate(symbols):
                    try:
                        df_s = fetch_ohlcv(sym)
                        stock_data[sym] = add_indicators(df_s)
                    except Exception as e:
                        errors.append(f"{sym}: {e}")
                    prog.progress((idx_s + 1) / len(symbols))
                prog.empty()

                if errors:
                    st.warning("Could not load: " + ", ".join(errors))

                if not stock_data:
                    st.error("No data loaded — cannot run backtest.")
                    return

                try:
                    nifty_df = fetch_ohlcv("^NSEI")
                except Exception:
                    nifty_df = list(stock_data.values())[0].copy()

                # Simple internal backtest using scoring engine
                all_trades = []
                equity_curve = [bt_capital]
                cash = bt_capital

                for sym, df_bt in stock_data.items():
                    if len(df_bt) < 60:
                        continue
                    split = int(len(df_bt) * 0.70)
                    test_df = df_bt.iloc[split:].reset_index(drop=True)

                    for i in range(5, len(test_df) - 5):
                        row_df = test_df.iloc[:i+1]
                        try:
                            sd_bt = score(row_df, is_entry=True)
                        except Exception:
                            continue
                        if sd_bt["verdict"] not in ("STRONG BUY", "WATCHLIST"):
                            continue

                        entry_i = i + 1
                        if entry_i >= len(test_df):
                            continue

                        entry_p  = float(test_df.iloc[entry_i]["open"])
                        sl_p     = sd_bt["trade"]["sl"]
                        t1_p     = sd_bt["trade"]["t1"]
                        atr_v    = sd_bt["trade"]["atr"]
                        tsl      = entry_p - 2.0 * atr_v

                        exit_p, exit_reason = entry_p, "End"
                        for j in range(entry_i + 1, min(entry_i + 30, len(test_df))):
                            c = float(test_df.iloc[j]["close"])
                            h = float(test_df.iloc[j]["high"])
                            l = float(test_df.iloc[j]["low"])
                            tsl = max(tsl, c - 2.0 * atr_v)
                            if l <= sl_p:
                                exit_p = sl_p; exit_reason = "Stop Loss"; break
                            if l <= tsl:
                                exit_p = tsl; exit_reason = "Trail Stop"; break
                            if h >= t1_p:
                                exit_p = t1_p; exit_reason = "T1 Target"; break
                        else:
                            exit_p = float(test_df.iloc[min(entry_i+29, len(test_df)-1)]["close"])
                            exit_reason = "Time Exit"

                        shares   = max(1, int((cash * 0.10) / entry_p))
                        pnl      = (exit_p - entry_p) * shares
                        pnl_pct  = (exit_p - entry_p) / max(entry_p, 0.01) * 100
                        cash    += pnl
                        equity_curve.append(cash)

                        all_trades.append({
                            "symbol": sym, "entry": round(entry_p, 2), "exit": round(exit_p, 2),
                            "pnl": round(pnl, 2), "pnl_pct": round(pnl_pct, 2),
                            "exit_reason": exit_reason, "verdict": sd_bt["verdict"],
                        })

                if not all_trades:
                    st.info("No signals triggered during the test period.")
                    return

                trades_df = pd.DataFrame(all_trades)
                wins      = trades_df[trades_df["pnl"] > 0]
                losses    = trades_df[trades_df["pnl"] <= 0]
                win_rate  = len(wins) / len(trades_df) * 100
                total_pnl = trades_df["pnl"].sum()
                avg_win   = wins["pnl"].mean() if len(wins) else 0
                avg_loss  = losses["pnl"].mean() if len(losses) else 0
                rr_ratio  = abs(avg_win / avg_loss) if avg_loss != 0 else 0
                max_dd    = 0.0
                peak      = bt_capital
                for eq in equity_curve:
                    if eq > peak: peak = eq
                    dd = (peak - eq) / peak * 100
                    max_dd = max(max_dd, dd)

                st.session_state["bt_results"] = {
                    "trades": trades_df, "equity": equity_curve,
                    "win_rate": win_rate, "total_pnl": total_pnl,
                    "avg_win": avg_win, "avg_loss": avg_loss,
                    "rr_ratio": rr_ratio, "max_dd": max_dd,
                    "capital": bt_capital,
                }
                bt_results = st.session_state["bt_results"]

    if bt_results:
        st.divider()
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Trades",       len(bt_results["trades"]))
        m2.metric("Win Rate",     f"{bt_results['win_rate']:.1f}%",
                  delta="✓ OK" if bt_results["win_rate"] >= 40 else "✗ Below 40%")
        m3.metric("Total P&L",    f"₹{bt_results['total_pnl']:,.0f}")
        m4.metric("R:R Ratio",    f"{bt_results['rr_ratio']:.2f}",
                  delta="✓ OK" if bt_results["rr_ratio"] >= 2 else "✗ Below 2")
        m5.metric("Max Drawdown", f"{bt_results['max_dd']:.1f}%",
                  delta="✓ OK" if bt_results["max_dd"] <= 25 else "✗ Above 25%")

        eq = bt_results["equity"]
        if len(eq) > 1:
            fig_eq = go.Figure()
            fig_eq.add_trace(go.Scatter(
                y=eq, mode="lines", name="Equity",
                line=dict(color=C["green"], width=2),
                fill="tozeroy", fillcolor=hex_rgba(C["green"], 0.1),
            ))
            fig_eq.update_layout(
                title="Equity Curve", paper_bgcolor=C["bg"], plot_bgcolor=C["bg"],
                font=dict(color=C["text"]), height=300, margin=dict(l=10, r=10, t=40, b=10),
                xaxis=dict(showgrid=False), yaxis=dict(showgrid=False),
            )
            st.plotly_chart(fig_eq, key="bt_equity_chart")

        st.markdown("#### Trade Log")
        td_show = bt_results["trades"].copy()
        td_show["pnl_pct"] = td_show["pnl_pct"].map(lambda x: f"{x:+.1f}%")
        td_show["pnl"]     = td_show["pnl"].map(lambda x: f"₹{x:,.0f}")
        st.dataframe(td_show, use_container_width=True)


# ── MAIN APP ───────────────────────────────────────────────────────────────────
def main():
    _init_state()
    capital, risk_pct, max_pos, max_sl_pct, tg_token, tg_chat = render_sidebar()

    st.markdown(
        f"<h1 style='font-family:JetBrains Mono,monospace;font-size:22px;"
        f"color:{C['text']};margin-bottom:4px'>📈 NSE Swing Trader</h1>",
        unsafe_allow_html=True,
    )

    tabs = st.tabs(["🔍 Analyse", "📊 Screener", "⭐ Watchlist",
                    "📦 Holdings", "💼 Portfolio", "🧪 Backtest"])
    t_analyse, t_screen, t_watch, t_hld, t_port, t_back = tabs

    stocks_df = load_nse_stocks()

    with t_analyse: tab_analyse(stocks_df, capital)
    with t_screen:  tab_screener(stocks_df)
    with t_watch:   tab_watchlist()
    with t_hld:     tab_holdings()
    with t_port:    tab_portfolio(capital, risk_pct, tg_token, tg_chat)
    with t_back:    tab_backtest()


main()
