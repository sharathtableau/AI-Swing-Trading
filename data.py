"""
Data Engine: download, cache, and incrementally update OHLCV data.
- Auto-adjusts for splits/bonuses via yfinance auto_adjust=True
- Stores as Parquet for fast I/O; never overwrites historical rows
- Requires at least 1 year of data before a symbol is usable
"""
import contextlib
import io
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import yfinance as yf

import config

DATA_DIR = Path(config.DATA_DIR)
DATA_DIR.mkdir(exist_ok=True)


def _cache_path(symbol: str) -> Path:
    safe = symbol.replace("/", "_").replace("^", "IDX_").replace(".", "_")
    return DATA_DIR / f"{safe}.parquet"


def _download(symbol: str, start: str, end: str, silent: bool = False,
              retries: int = 2, pause: float = 1.0) -> pd.DataFrame:
    if start >= end:
        return pd.DataFrame()

    def _do():
        if silent:
            # Suppress stdout, stderr, and yfinance's own logger all at once
            _yf_log = logging.getLogger("yfinance")
            _old_lvl = _yf_log.level
            _yf_log.setLevel(logging.CRITICAL)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                d = yf.download(symbol, start=start, end=end, auto_adjust=True, progress=False)
            _yf_log.setLevel(_old_lvl)
        else:
            d = yf.download(symbol, start=start, end=end, auto_adjust=True, progress=False)
        return d

    df = pd.DataFrame()
    for attempt in range(retries + 1):
        try:
            df = _do()
            if not df.empty:
                break
        except Exception:
            df = pd.DataFrame()
        if attempt < retries:
            time.sleep(pause * (attempt + 1))  # linear backoff on rate-limit/transient errors
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


def passes_liquidity(df: pd.DataFrame) -> bool:
    """True if the symbol is liquid enough to trade at retail size.

    Requires last price >= MIN_PRICE and median daily turnover (close × volume)
    over LIQUIDITY_LOOKBACK days >= MIN_AVG_TURNOVER. Guards against signals on
    illiquid names you can't actually fill.
    """
    if df is None or df.empty:
        return False
    min_price = getattr(config, "MIN_PRICE", 0)
    min_turn = getattr(config, "MIN_AVG_TURNOVER", 0)
    lb = getattr(config, "LIQUIDITY_LOOKBACK", 50)
    if float(df["close"].iloc[-1]) < min_price:
        return False
    recent = df.tail(lb)
    turnover = (recent["close"] * recent["volume"]).median()
    return bool(turnover >= min_turn)


def load_all_stocks(refresh: bool = False, symbols: Optional[List[str]] = None,
                    apply_liquidity: bool = True, pause: float = 0.0,
                    verbose: bool = True) -> Dict[str, pd.DataFrame]:
    """Load the full universe robustly; skip symbols with thin history/liquidity.

    - Tolerates per-symbol failures (delisted, renamed, network) and keeps going.
    - Logs progress every 25 symbols so a ~500-name refresh is observable.
    - `pause` adds a small sleep between fetches to avoid rate-limiting on refresh.
    - `apply_liquidity` drops names below the config liquidity floor.
    """
    universe = symbols if symbols is not None else config.NIFTY50_STOCKS
    total = len(universe)
    result, failed, illiquid = {}, [], 0

    for i, symbol in enumerate(universe, 1):
        try:
            df = load_symbol(symbol, refresh=refresh)
            if df.empty or len(df) < 252:
                failed.append(symbol)
            elif apply_liquidity and not passes_liquidity(df):
                illiquid += 1
            else:
                result[symbol] = df
        except Exception as e:
            failed.append(symbol)
            if verbose:
                print(f"  [WARN] {symbol}: {e}")
        if pause and refresh:
            time.sleep(pause)
        if verbose and (i % 25 == 0 or i == total):
            print(f"  [{i}/{total}] loaded={len(result)} illiquid_skipped={illiquid} failed={len(failed)}")

    if verbose and failed:
        print(f"  [INFO] {len(failed)} symbols unavailable/thin: "
              f"{', '.join(failed[:15])}{' …' if len(failed) > 15 else ''}")
    return result


def load_index(refresh: bool = False) -> pd.DataFrame:
    return load_symbol(config.INDEX_SYMBOL, refresh=refresh)
