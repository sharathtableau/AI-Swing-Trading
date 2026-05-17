"""
Data Engine: download, cache, and incrementally update OHLCV data.
- Auto-adjusts for splits/bonuses via yfinance auto_adjust=True
- Stores as Parquet for fast I/O; never overwrites historical rows
- Requires at least 1 year of data before a symbol is usable
"""
import contextlib
import io
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict

import pandas as pd
import yfinance as yf

import config

DATA_DIR = Path(config.DATA_DIR)
DATA_DIR.mkdir(exist_ok=True)


def _cache_path(symbol: str) -> Path:
    safe = symbol.replace("/", "_").replace("^", "IDX_").replace(".", "_")
    return DATA_DIR / f"{safe}.parquet"


def _download(symbol: str, start: str, end: str, silent: bool = False) -> pd.DataFrame:
    if start >= end:
        return pd.DataFrame()
    if silent:
        # Suppress stdout, stderr, and yfinance's own logger all at once
        _yf_log = logging.getLogger("yfinance")
        _old_lvl = _yf_log.level
        _yf_log.setLevel(logging.CRITICAL)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            df = yf.download(symbol, start=start, end=end, auto_adjust=True, progress=False)
        _yf_log.setLevel(_old_lvl)
    else:
        df = yf.download(symbol, start=start, end=end, auto_adjust=True, progress=False)
    if df.empty:
        return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    df.index = pd.to_datetime(df.index)
    df.index.name = "date"
    cols = [c for c in ["open", "high", "low", "close", "volume"] if c in df.columns]
    return df[cols].dropna()


def load_symbol(symbol: str, refresh: bool = False) -> pd.DataFrame:
    """Return OHLCV DataFrame for symbol, using cache when possible."""
    path = _cache_path(symbol)

    if path.exists() and not refresh:
        df = pd.read_parquet(path)
        last = df.index[-1]
        today = pd.Timestamp(datetime.today().date())
        if last < today - timedelta(days=1):
            df = _append_latest(symbol, df, path)
        return df

    end   = datetime.today().strftime("%Y-%m-%d")
    start = (datetime.today() - timedelta(days=config.HISTORICAL_YEARS * 365 + 90)).strftime("%Y-%m-%d")
    # silent=False for the index (user-visible); silent=True for individual stocks
    # (load_all_stocks has its own try/except that prints a clean [WARN] line)
    is_index = symbol == config.INDEX_SYMBOL
    df = _download(symbol, start, end, silent=not is_index)
    if not df.empty:
        df.to_parquet(path)
    return df


def _append_latest(symbol: str, existing: pd.DataFrame, path: Path) -> pd.DataFrame:
    last  = existing.index[-1]
    start = (last + timedelta(days=1)).strftime("%Y-%m-%d")
    end   = datetime.today().strftime("%Y-%m-%d")
    # silent=True suppresses yfinance "possibly delisted" noise on weekends/holidays
    new = _download(symbol, start, end, silent=True)
    if new.empty:
        return existing
    combined = pd.concat([existing, new])
    combined = combined[~combined.index.duplicated(keep="last")].sort_index()
    combined.to_parquet(path)
    return combined


def load_all_stocks(refresh: bool = False) -> Dict[str, pd.DataFrame]:
    """Load all Nifty 50 stocks; skip symbols with insufficient history."""
    result = {}
    for symbol in config.NIFTY50_STOCKS:
        try:
            df = load_symbol(symbol, refresh=refresh)
            if not df.empty and len(df) >= 252:
                result[symbol] = df
        except Exception as e:
            print(f"  [WARN] {symbol}: {e}")
    return result


def load_index(refresh: bool = False) -> pd.DataFrame:
    return load_symbol(config.INDEX_SYMBOL, refresh=refresh)
