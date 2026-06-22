"""Price pivot zone (中枢 / Zhongshu) identification."""

import pandas as pd
import numpy as np
from .xian_duan import get_xd_segments


def find_zhongshu(df: pd.DataFrame) -> pd.DataFrame:
    """
    Identify Zhongshu (中枢) — overlapping zones of 3+ consecutive Xian Duan.

    ZG = Zhongshu high (中枢上沿) = max of segment lows in overlap
    ZD = Zhongshu low (中枢下沿) = min of segment highs in overlap

    Rules:
    - At least 3 consecutive Xian Duan overlap
    - Zhongshu extension: can extend beyond 3 segments
    - Zhongshu destruction: a segment leaves and doesn't return
    """
    df = df.copy()
    df["zs_active"] = False
    df["zs_zg"] = np.nan  # Zhongshu upper bound
    df["zs_zd"] = np.nan  # Zhongshu lower bound
    df["zs_period"] = 0         # Which Zhongshu this belongs to (1, 2, 3...)
    df["zs_segment_count"] = 0  # How many segments in this zhongshu
    df["zs_phase"] = ""   # "forming", "stable", "extending", "destroyed"

    xd_segs = get_xd_segments(df)
    if len(xd_segs) < 3:
        return df

    zhongshu_list = []

    for j in range(len(xd_segs) - 2):
        seg1 = xd_segs[j]
        seg2 = xd_segs[j + 1]
        seg3 = xd_segs[j + 2]

        # Each segment must have valid high/low
        if any(s["high"] is None or s["low"] is None for s in [seg1, seg2, seg3]):
            continue

        # Three segments must overlap
        overlap_high = min(seg1["high"], seg2["high"], seg3["high"])
        overlap_low = max(seg1["low"], seg2["low"], seg3["low"])

        if overlap_high <= overlap_low:
            continue

        zg = overlap_low   # ZG = min of segment highs (the narrower bound)
        zd = overlap_high  # ZD = max of segment lows — wait, let me fix

        # Correct Zhongshu calculation:
        # The overlap zone of N segments:
        # High side: the LOWEST of all segment highs
        # Low side: the HIGHEST of all segment lows
        all_highs = [seg1["high"], seg2["high"], seg3["high"]]
        all_lows = [seg1["low"], seg2["low"], seg3["low"]]

        # ZG = highest of the lows (最强支撑)
        # ZD = lowest of the highs (最弱压力)
        zg_val = max(all_lows)
        zd_val = min(all_highs)

        # Extend to include more overlapping segments
        k = j + 3
        while k < len(xd_segs):
            s = xd_segs[k]
            if s["high"] is None or s["low"] is None:
                break
            if s["high"] > zg_val and s["low"] < zd_val:
                # This segment also overlaps — extend
                zd_val = min(zd_val, s["high"])
                zg_val = max(zg_val, s["low"])
                k += 1
            else:
                break

        zhongshu_list.append({
            "start_idx": seg1["start_idx"],
            "end_idx": xd_segs[k - 1]["end_idx"],
            "zg": round(zg_val, 2),
            "zd": round(zd_val, 2),
            "segment_count": k - j,
        })

    # Mark on DataFrame
    current_zs = 0
    for zs in zhongshu_list:
        current_zs += 1
        for idx in df.index:
            if zs["start_idx"] <= idx <= zs["end_idx"]:
                df.loc[idx, "zs_active"] = True
                df.loc[idx, "zs_zg"] = zs["zg"]
                df.loc[idx, "zs_zd"] = zs["zd"]
                df.loc[idx, "zs_period"] = current_zs
                df.loc[idx, "zs_segment_count"] = zs["segment_count"]

    # Ensure boolean columns have no NaN
    for col in ["zs_active"]:
        if col in df.columns:
            df[col] = df[col].fillna(False).astype(bool)
    return df


def get_zhongshu_list(df: pd.DataFrame) -> list[dict]:
    """Extract zhongshu as distinct zones for charting. idx values are actual DataFrame index."""
    zones = []
    if not df["zs_active"].any():
        return zones

    current_zg = None
    current_zd = None
    current_start = None
    current_end = None
    current_period = None
    current_seg_count = 0

    for idx in df.index:
        if df.loc[idx, "zs_active"]:
            zg = df.loc[idx, "zs_zg"]
            zd = df.loc[idx, "zs_zd"]
            period = df.loc[idx, "zs_period"]
            seg_count = df.loc[idx, "zs_segment_count"]

            if period != current_period:
                if current_period is not None:
                    zones.append({
                        "start_idx": current_start,
                        "end_idx": current_end,
                        "zg": float(current_zg),
                        "zd": float(current_zd),
                        "period": int(current_period),
                        "segment_count": int(current_seg_count),
                    })
                current_zg, current_zd = zg, zd
                current_start = idx
                current_period = period
                current_seg_count = seg_count
            current_end = idx
        else:
            if current_period is not None:
                zones.append({
                    "start_idx": current_start,
                    "end_idx": current_end,
                    "zg": float(current_zg),
                    "zd": float(current_zd),
                    "period": int(current_period),
                    "segment_count": int(current_seg_count),
                })
                current_period = None

    if current_period is not None:
        zones.append({
            "start_idx": current_start,
            "end_idx": current_end,
            "zg": float(current_zg),
            "zd": float(current_zd),
            "period": int(current_period),
            "segment_count": int(current_seg_count),
        })

    return zones
