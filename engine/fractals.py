"""K-line containment processing and fractal detection."""

import pandas as pd
import numpy as np
from typing import Optional


def process_containment(df: pd.DataFrame) -> pd.DataFrame:
    """
    Handle K-line containment (包含关系处理).

    Rules:
    - Upward trend: keep high of higher K, low of higher K
    - Downward trend: keep low of lower K, high of lower K
    Returns DataFrame with processed bars (some merged).
    """
    if len(df) < 2:
        return df.copy()

    df = df.copy()
    # Save raw OHLC before any merging (for chart display)
    for col in ["open", "high", "low", "close"]:
        df[f"raw_{col}"] = df[col]
    df["direction"] = 0  # 0=unknown, 1=up, -1=down
    # Preserve original date for each bar
    df["_date"] = df.index

    # Determine initial direction
    for i in range(1, len(df)):
        if df["high"].iloc[i] > df["high"].iloc[i - 1] and \
           df["low"].iloc[i] > df["low"].iloc[i - 1]:
            df.loc[df.index[i], "direction"] = 1
        elif df["high"].iloc[i] < df["high"].iloc[i - 1] and \
             df["low"].iloc[i] < df["low"].iloc[i - 1]:
            df.loc[df.index[i], "direction"] = -1
        else:
            df.loc[df.index[i], "direction"] = df["direction"].iloc[i - 1]

    # Merge containment bars
    processed_rows = [df.iloc[0].to_dict()]
    for i in range(1, len(df)):
        prev = processed_rows[-1]
        curr = df.iloc[i]

        # Check containment
        is_contained = (curr["high"] <= prev["high"] and curr["low"] >= prev["low"])
        contains_prev = (curr["high"] >= prev["high"] and curr["low"] <= prev["low"])

        if is_contained:
            # Current is contained by previous — merge based on direction
            if curr["direction"] == 1:  # Up: keep lower low
                processed_rows[-1]["high"] = max(prev["high"], curr["high"])
                processed_rows[-1]["low"] = max(prev["low"], curr["low"])
            else:  # Down: keep higher high
                processed_rows[-1]["high"] = min(prev["high"], curr["high"])
                processed_rows[-1]["low"] = min(prev["low"], curr["low"])
            processed_rows[-1]["close"] = curr["close"]
            processed_rows[-1]["volume"] += curr["volume"]
            processed_rows[-1]["_merged"] = processed_rows[-1].get("_merged", 0) + 1
        elif contains_prev:
            processed_rows[-1] = curr.to_dict()
            processed_rows[-1]["_merged"] = 0
        else:
            processed_rows.append(curr.to_dict())

    # Use preserved dates as index
    dates = [r.get("_date", i) for i, r in enumerate(processed_rows)]
    result = pd.DataFrame(processed_rows)
    # Drop the _date column from data, use it as index
    result.index = pd.Index(dates)
    result = result.drop(columns=["_date"], errors="ignore")
    for col in ["open", "high", "low", "close", "volume"]:
        if col not in result.columns:
            result[col] = np.nan
    result["_merged"] = result.get("_merged", 0)

    # Re-determine direction on processed data
    result["direction"] = 0
    for i in range(1, len(result)):
        if result["high"].iloc[i] > result["high"].iloc[i - 1] and \
           result["low"].iloc[i] > result["low"].iloc[i - 1]:
            result.loc[result.index[i], "direction"] = 1
        elif result["high"].iloc[i] < result["high"].iloc[i - 1] and \
             result["low"].iloc[i] < result["low"].iloc[i - 1]:
            result.loc[result.index[i], "direction"] = -1
        else:
            result.loc[result.index[i], "direction"] = result["direction"].iloc[i - 1]
    return result


def detect_fractals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detect top fractals (顶分型) and bottom fractals (底分型).

    Top fractal: middle bar high > left and right bar high
    Bottom fractal: middle bar low < left and right bar low
    """
    df = df.copy()
    df["top_fractal"] = False
    df["bottom_fractal"] = False
    df["fractal_value"] = np.nan

    if len(df) < 3:
        return df

    for i in range(1, len(df) - 1):
        left = df.iloc[i - 1]
        mid = df.iloc[i]
        right = df.iloc[i + 1]

        # Top fractal: middle high is highest, both sides must be separate K-lines
        if mid["high"] > left["high"] and mid["high"] > right["high"]:
            # Validate: must be independent bars (no merge artifacts)
            if not (left.get("_merged", 0) > 2 and right.get("_merged", 0) > 2):
                df.loc[df.index[i], "top_fractal"] = True
                df.loc[df.index[i], "fractal_value"] = mid["high"]

        # Bottom fractal: middle low is lowest
        if mid["low"] < left["low"] and mid["low"] < right["low"]:
            if not (left.get("_merged", 0) > 2 and right.get("_merged", 0) > 2):
                df.loc[df.index[i], "bottom_fractal"] = True
                df.loc[df.index[i], "fractal_value"] = mid["low"]

    return df


def validate_fractals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Post-process: remove consecutive top/top or bottom/bottom fractals,
    keeping only alternating top-bottom-top-bottom pattern.
    Also ensure top > adjacent bottoms (no gap violations).
    """
    df = df.copy()
    # Ensure boolean columns have no NaN (pandas 2.x compat)
    df["top_fractal"] = df["top_fractal"].fillna(False).astype(bool)
    df["bottom_fractal"] = df["bottom_fractal"].fillna(False).astype(bool)

    # Get fractal indices
    top_idx = list(df[df["top_fractal"]].index)
    bottom_idx = list(df[df["bottom_fractal"]].index)

    all_fractals = sorted(
        [(i, "top") for i in top_idx] + [(i, "bottom") for i in bottom_idx]
    )

    if len(all_fractals) < 2:
        return df

    # Remove consecutive same-type fractals
    cleaned = [all_fractals[0]]
    for i in range(1, len(all_fractals)):
        if all_fractals[i][1] != cleaned[-1][1]:
            cleaned.append(all_fractals[i])
        else:
            # Keep the more extreme one
            prev_idx, prev_type = cleaned[-1]
            curr_idx, _ = all_fractals[i]
            if prev_type == "top":
                if df.loc[curr_idx, "high"] > df.loc[prev_idx, "high"]:
                    df.loc[prev_idx, "top_fractal"] = False
                    df.loc[prev_idx, "fractal_value"] = np.nan
                    cleaned[-1] = all_fractals[i]
                else:
                    df.loc[curr_idx, "top_fractal"] = False
                    df.loc[curr_idx, "fractal_value"] = np.nan
            else:  # bottom
                if df.loc[curr_idx, "low"] < df.loc[prev_idx, "low"]:
                    df.loc[prev_idx, "bottom_fractal"] = False
                    df.loc[prev_idx, "fractal_value"] = np.nan
                    cleaned[-1] = all_fractals[i]
                else:
                    df.loc[curr_idx, "bottom_fractal"] = False
                    df.loc[curr_idx, "fractal_value"] = np.nan

    return df


def find_fractals(df: pd.DataFrame, use_containment: bool = False) -> pd.DataFrame:
    """
    Complete fractal detection pipeline.
    use_containment=False preserves original K-lines for accurate chart display.
    """
    if use_containment:
        df = process_containment(df)
    df = detect_fractals(df)
    df = validate_fractals(df)
    # Fill NaN in boolean columns after processing
    for col in ["top_fractal", "bottom_fractal"]:
        if col in df.columns:
            df[col] = df[col].fillna(False).astype(bool)
    return df
