"""Stroke (笔 / Bi) construction from validated fractals."""

import pandas as pd
import numpy as np
from typing import Optional


def build_bi(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build strokes (笔) from validated fractals.

    Rules:
    - Bi starts at a valid fractal (top or bottom)
    - Bi ends at the next alternating fractal
    - Must have >= 5 K-lines between start and end (inclusive)
    - Bi direction: upward=bottom→top, downward=top→bottom
    """
    df = df.copy()
    df["bi_start"] = False
    df["bi_end"] = False
    df["bi_value"] = np.nan
    df["bi_direction"] = ""  # "up" or "down"

    if len(df) < 3:
        return df

    # Collect valid fractals
    fractals = []
    for i in df.index:
        if df.loc[i, "top_fractal"]:
            fractals.append((i, "top", df.loc[i, "high"]))
        elif df.loc[i, "bottom_fractal"]:
            fractals.append((i, "bottom", df.loc[i, "low"]))

    if len(fractals) < 2:
        return df

    # Build alternating bi strokes
    bi_list = []
    i = 0
    while i < len(fractals) - 1:
        start_idx, start_type, start_val = fractals[i]
        end_idx, end_type, end_val = fractals[i + 1]

        # Must alternate types
        if start_type == end_type:
            i += 1
            continue

        # Must span >= 5 K-lines (inclusive of fractal bars)
        dist = list(df.index).index(end_idx) - list(df.index).index(start_idx)
        if dist < 4:  # at least 5 bars means distance >= 4
            # Skip this pair, try next
            i += 1
            continue

        direction = "up" if start_type == "bottom" else "down"

        bi_list.append({
            "start_idx": start_idx,
            "end_idx": end_idx,
            "start_val": start_val,
            "end_val": end_val,
            "direction": direction,
        })
        i += 1

    # Mark on DataFrame
    for bi_item in bi_list:
        df.loc[bi_item["start_idx"], "bi_start"] = True
        df.loc[bi_item["end_idx"], "bi_end"] = True
        df.loc[bi_item["end_idx"], "bi_value"] = bi_item["end_val"]
        df.loc[bi_item["end_idx"], "bi_direction"] = bi_item["direction"]

    return df


def get_bi_segments(df: pd.DataFrame) -> list[dict]:
    """
    Extract bi segments as list for charting.
    Returns [{start_idx, end_idx, start_val, end_val, direction}, ...]
    """
    segments = []
    fractal_indices = list(
        df[df["bi_start"] | df["bi_end"]].index
    )

    for j in range(len(fractal_indices) - 1):
        start = fractal_indices[j]
        end = fractal_indices[j + 1]
        start_row = df.loc[start]
        end_row = df.loc[end]

        direction = "up" if end_row.get("bi_value", 0) > start_row.get(
            "high" if start_row.get("top_fractal") else "low", 0
        ) else "down"

        segments.append({
            "start_idx": int(start),
            "end_idx": int(end),
            "start_val": float(
                start_row["high"] if start_row.get("top_fractal") else start_row["low"]
            ),
            "end_val": float(
                end_row["high"] if end_row.get("top_fractal") else end_row["low"]
            ),
            "direction": str(end_row.get("bi_direction", direction)),
        })
    return segments
