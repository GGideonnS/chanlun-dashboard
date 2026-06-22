"""Divergence (背驰) detection using MACD area comparison."""

import pandas as pd
import numpy as np


def compute_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9):
    """
    Compute MACD indicator on close prices.
    Returns DataFrame with DIF, DEA, MACD_bar columns.
    """
    df = df.copy()
    close = df["close"]

    # EMA calculations
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()

    df["DIF"] = ema_fast - ema_slow
    df["DEA"] = df["DIF"].ewm(span=signal, adjust=False).mean()
    df["MACD_bar"] = 2 * (df["DIF"] - df["DEA"])

    # MACD area (absolute value of bar for area computation)
    df["MACD_area"] = df["MACD_bar"].abs()
    return df


def detect_divergence(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detect Bei Chi (背驰) by comparing MACD areas between consecutive
    trending Bi segments.

    Top divergence (顶背驰): price makes higher high but MACD area shrinks
    Bottom divergence (底背驰): price makes lower low but MACD area shrinks
    """
    df = compute_macd(df)
    df["top_divergence"] = False
    df["bottom_divergence"] = False
    df["divergence_strength"] = 0.0  # 0-1 scale

    if len(df) < 20:
        return df

    # Find Bi segments to compare adjacent same-direction strokes
    bi_starts = df[df["bi_start"]]
    bi_ends = df[df["bi_end"]]

    if len(bi_starts) < 2:
        return df

    # Compare adjacent up strokes for top divergence
    up_strokes = []
    for _, row in bi_ends.iterrows():
        bd = str(row.get("bi_direction", "")).lower()
        if bd == "up" or bd == "True":
            up_strokes.append(row.name)

    for j in range(1, len(up_strokes)):
        curr_end = up_strokes[j]
        prev_end = up_strokes[j - 1]

        # Price: higher high
        if df.loc[curr_end, "high"] <= df.loc[prev_end, "high"]:
            continue

        # MACD area comparison
        curr_area = _get_area_for_bi(df, curr_end, "up")
        prev_area = _get_area_for_bi(df, prev_end, "up")

        if curr_area > 0 and prev_area > 0 and curr_area < prev_area * 0.8:
            df.loc[curr_end, "top_divergence"] = True
            df.loc[curr_end, "divergence_strength"] = 1 - (curr_area / prev_area)

    # Compare adjacent down strokes for bottom divergence
    down_strokes = []
    for _, row in bi_ends.iterrows():
        bd = str(row.get("bi_direction", "")).lower()
        if bd == "down" or bd == "false":
            down_strokes.append(row.name)

    for j in range(1, len(down_strokes)):
        curr_end = down_strokes[j]
        prev_end = down_strokes[j - 1]

        # Price: lower low
        if df.loc[curr_end, "low"] >= df.loc[prev_end, "low"]:
            continue

        # MACD area comparison
        curr_area = _get_area_for_bi(df, curr_end, "down")
        prev_area = _get_area_for_bi(df, prev_end, "down")

        if curr_area > 0 and prev_area > 0 and curr_area < prev_area * 0.8:
            df.loc[curr_end, "bottom_divergence"] = True
            df.loc[curr_end, "divergence_strength"] = 1 - (curr_area / prev_area)

    return df


def _pos(df, idx) -> int:
    """Convert any index value to positional integer."""
    try:
        return df.index.get_loc(idx)
    except (KeyError, TypeError):
        return int(idx)


def _get_area_for_bi(df: pd.DataFrame, end_idx, direction: str) -> float:
    """Sum MACD area for the Bi ending at end_idx."""
    end_pos = _pos(df, end_idx)
    # Look back to find the start of this Bi
    start_pos = None
    for p in range(end_pos - 1, max(0, end_pos - 30) - 1, -1):
        if p < 0:
            break
        if df["bi_start"].iloc[p] and p != end_pos:
            start_pos = p
            break

    if start_pos is None:
        start_pos = max(0, end_pos - 10)

    area = df["MACD_area"].iloc[start_pos: end_pos + 1].sum()
    return float(area)
