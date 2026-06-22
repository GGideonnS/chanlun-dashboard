"""Simple file-based cache for stock data (24h TTL)."""

import json
import os
import time
from datetime import datetime, timezone

import pandas as pd

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", ".cache")
CACHE_TTL = 14400  # 4 hours — ensure intraday freshness
CACHE_VERSION = 2  # bump to invalidate old-format caches


def _ensure_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)


def _cache_key(symbol: str, period: str) -> str:
    return f"{symbol.replace('.', '_')}_{period}.json"


def get_cached(symbol: str, period: str) -> pd.DataFrame | None:
    """Return cached DataFrame if fresh, else None."""
    _ensure_dir()
    key = _cache_key(symbol, period)
    path = os.path.join(CACHE_DIR, key)
    if not os.path.exists(path):
        return None

    try:
        with open(path, "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return None

    age = time.time() - data.get("ts", 0)
    if age > CACHE_TTL:
        return None

    df = pd.DataFrame(data["rows"])
    if "Date" in df.columns or "index" in df.columns:
        idx_col = "Date" if "Date" in df.columns else "index"
        df[idx_col] = pd.to_datetime(df[idx_col], utc=True)
        df = df.set_index(idx_col)
    return df


def set_cache(symbol: str, period: str, df: pd.DataFrame) -> None:
    """Cache DataFrame to disk."""
    _ensure_dir()
    key = _cache_key(symbol, period)
    path = os.path.join(CACHE_DIR, key)

    export = df.reset_index()
    data = {
        "ts": time.time(),
        "symbol": symbol,
        "period": period,
        "rows": export.to_dict(orient="records"),
    }
    with open(path, "w") as f:
        json.dump(data, f, default=str)
