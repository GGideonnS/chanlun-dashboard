"""Stock data fetcher using yfinance."""

import logging
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

# Period mapping for different timeframes
PERIOD_CONFIG = {
    "1min":  ("7d",   "1m"),
    "5min":  ("1mo",  "5m"),
    "30min": ("1mo",  "30m"),
    "60min": ("2mo",  "1h"),
    "daily": ("1y",   "1d"),
    "weekly":("5y",   "1wk"),
    "monthly":("10y",  "1mo"),
}

# Display names
LEVEL_LABELS = {
    "1min": "1分钟",
    "5min": "5分钟",
    "30min": "30分钟",
    "60min": "60分钟",
    "daily": "日线",
    "weekly": "周线",
    "monthly": "月线",
}


def resolve_symbol(code: str) -> tuple[str, str, str]:
    """
    Resolve user input to yfinance symbol + market + display name.

    Examples:
        AAPL → (AAPL, US, AAPL)
        0700.HK → (0700.HK, HK, 0700.HK)
        600519.SS → (600519.SS, CN, 600519.SS)
        BABA → (BABA, US, BABA)
    """
    code = code.strip().upper()

    # Already full yfinance format
    if "." in code and len(code.split(".")[0]) > 0:
        suffix = code.split(".")[-1]
        if suffix in ("HK", "SS", "SZ", "T", "L", "PA"):
            if suffix == "HK":
                return code, "HK", code.replace(".HK", "")
            elif suffix in ("SS", "SZ"):
                return code, "CN", code
            return code, "US", code

    # Pure digits → A-share
    if code.isdigit():
        if len(code) == 6:
            if code.startswith(("6", "9")):
                return f"{code}.SS", "CN", code
            elif code.startswith(("0", "3")):
                return f"{code}.SZ", "CN", code
        return f"{code}.HK", "HK", code

    # Contains digits with HK prefix → assume HK
    if code.replace(".", "").isdigit() and len(code) == 5:
        return f"{code}.HK", "HK", code

    # Default: US ticker
    return code, "US", code


def fetch_stock_data(
    code: str,
    period: str = "daily",
    lookback: str | None = None,
) -> tuple[pd.DataFrame, dict]:
    """
    Fetch OHLCV data from yfinance.

    Args:
        code: Raw user input (AAPL / 0700.HK / 600519.SS)
        period: "daily" | "weekly" | "monthly" | "30min" | "60min" | "5min"

    Returns:
        (DataFrame with OHLCV, metadata dict)
    """
    symbol, market, display = resolve_symbol(code)
    yf_ticker = yf.Ticker(symbol)

    if period not in PERIOD_CONFIG:
        period = "daily"

    yf_period, interval = PERIOD_CONFIG[period]

    try:
        df = yf_ticker.history(period=yf_period, interval=interval)
        if df.empty:
            raise ValueError(f"No data returned for {symbol}")
    except Exception as e:
        raise ValueError(f"Failed to fetch {symbol}: {e}")

    # Normalize columns
    df = df.reset_index()
    if "Datetime" in df.columns:
        df = df.rename(columns={"Datetime": "Date"})
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date")

    # Standardize column names
    col_map = {
        "Open": "open", "High": "high", "Low": "low",
        "Close": "close", "Volume": "volume",
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    # Ensure required columns exist
    for col in ["open", "high", "low", "close", "volume"]:
        if col not in df.columns:
            df[col] = df.get("close", 0)

    # Drop rows with all NaN
    df = df.dropna(subset=["open", "high", "low", "close"], how="all")

    # Validate
    if len(df) < 5:
        raise ValueError(f"Insufficient data: {len(df)} bars for {symbol}")

    # Get company info
    try:
        info = yf_ticker.info
        name = info.get("longName") or info.get("shortName") or display
    except Exception:
        name = display

    meta = {
        "symbol": symbol,
        "display": display,
        "name": name,
        "market": market,
        "period": period,
        "level_label": LEVEL_LABELS.get(period, period),
        "bars": len(df),
        "start": str(df.index[0])[:10],
        "end": str(df.index[-1])[:10],
        "latest_price": float(df["close"].iloc[-1]),
        "currency": "USD" if market == "US" else "HKD" if market == "HK" else "CNY",
    }

    return df, meta
