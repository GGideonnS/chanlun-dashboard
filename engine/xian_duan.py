"""Line segment (线段 / Xian Duan) construction from Bi strokes."""

import pandas as pd
import numpy as np
from .bi import get_bi_segments


def build_xian_duan(df: pd.DataFrame) -> pd.DataFrame:
    """
    Construct Xian Duan from Bi strokes.

    A Xian Duan is defined when 3 consecutive Bi strokes overlap:
    The overlap of stroke 1 and 3 forms the segment range.
    """
    df = df.copy()
    df["xd_start"] = False
    df["xd_end"] = False
    df["xd_high"] = np.nan
    df["xd_low"] = np.nan

    bi_segs = get_bi_segments(df)
    if len(bi_segs) < 3:
        return df

    xd_list = []

    for j in range(len(bi_segs) - 2):
        bi1 = bi_segs[j]
        bi2 = bi_segs[j + 1]
        bi3 = bi_segs[j + 2]

        # Must alternate: up-down-up or down-up-down
        if not (bi1["direction"] != bi2["direction"] != bi3["direction"]):
            continue

        # Check overlap: bi1 range and bi3 range must overlap
        if bi1["direction"] == "up":
            bi1_low = bi1["start_val"]
            bi1_high = bi1["end_val"]
        else:
            bi1_low = bi1["end_val"]
            bi1_high = bi1["start_val"]

        if bi3["direction"] == "up":
            bi3_low = bi3["start_val"]
            bi3_high = bi3["end_val"]
        else:
            bi3_low = bi3["end_val"]
            bi3_high = bi3["start_val"]

        overlap_low = max(bi1_low, bi3_low)
        overlap_high = min(bi1_high, bi3_high)

        if overlap_low < overlap_high:
            xd_list.append({
                "start_idx": bi1["start_idx"],
                "end_idx": bi3["end_idx"],
                "high": overlap_high,
                "low": overlap_low,
            })

    # Mark on DataFrame
    for xd in xd_list:
        if xd["start_idx"] < len(df):
            df.loc[xd["start_idx"], "xd_start"] = True
        if xd["end_idx"] < len(df):
            df.loc[xd["end_idx"], "xd_end"] = True
            df.loc[xd["end_idx"], "xd_high"] = xd["high"]
            df.loc[xd["end_idx"], "xd_low"] = xd["low"]

    # Ensure boolean columns have no NaN
    for col in ["xd_start", "xd_end"]:
        df[col] = df[col].fillna(False).astype(bool)
    return df


def _to_pos(df, idx) -> int:
    """Convert DataFrame index value to positional integer."""
    try:
        return df.index.get_loc(idx)
    except (KeyError, TypeError):
        return int(idx)


def get_xd_segments(df: pd.DataFrame) -> list[dict]:
    """Extract Xian Duan segments for charting."""
    segments = []
    start_points = df[df["xd_start"]]
    end_points = df[df["xd_end"]]

    for i, (_, end_row) in enumerate(end_points.iterrows()):
        if i < len(start_points):
            seg = {
                "start_idx": _to_pos(df, start_points.index[i]),
                "end_idx": _to_pos(df, end_row.name),
                "high": float(end_row["xd_high"]) if pd.notna(end_row["xd_high"]) else None,
                "low": float(end_row["xd_low"]) if pd.notna(end_row["xd_low"]) else None,
            }
            segments.append(seg)
    return segments
