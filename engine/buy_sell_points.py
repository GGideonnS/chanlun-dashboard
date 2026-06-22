"""Three-type buy/sell points (三类买卖点) detection."""

import pandas as pd
import numpy as np
from .zhongshu import get_zhongshu_list


def find_buy_sell_points(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detect Type 1/2/3 buy points and sell points.

    Type 1 Buy: bottom divergence at the end of a downtrend
    Type 2 Buy: pullback after first rally, testing support
    Type 3 Buy: breakout above Zhongshu then successful retest of ZG

    Type 1 Sell: top divergence at the end of an uptrend
    Type 2 Sell: rally after first decline, testing resistance
    Type 3 Sell: breakdown below Zhongshu then failed retest of ZD
    """
    df = df.copy()
    for col in ["buy_1", "buy_2", "buy_3", "sell_1", "sell_2", "sell_3"]:
        df[col] = False
    df["signal"] = ""  # "B1", "B2", "B3", "S1", "S2", "S3"

    zhongshu_zones = get_zhongshu_list(df)

    # --- Type 1 Buy: bottom divergence ---
    for idx in df.index:
        if df.loc[idx, "bottom_divergence"]:
            # Must be in or near a downtrend
            recent = df.iloc[max(0, idx - 5) : idx + 1]
            if recent["close"].iloc[-1] < recent["close"].iloc[0]:
                df.loc[idx, "buy_1"] = True
                df.loc[idx, "signal"] = "B1"

    # --- Type 1 Sell: top divergence ---
    for idx in df.index:
        if df.loc[idx, "top_divergence"]:
            recent = df.iloc[max(0, idx - 5) : idx + 1]
            if recent["close"].iloc[-1] > recent["close"].iloc[0]:
                df.loc[idx, "sell_1"] = True
                df.loc[idx, "signal"] = "S1"

    # --- Type 3 Buy: breakout + retest of ZG ---
    for zs in zhongshu_zones:
        zg = zs["zg"]
        end = zs["end_idx"]

        # Find first close above ZG after zhongshu
        for idx in range(end + 1, min(len(df), end + 50)):
            if df.loc[idx, "close"] > zg:
                # Then check for pullback that stays above ZG
                for pullback_idx in range(idx + 1, min(len(df), idx + 20)):
                    if df.loc[pullback_idx, "low"] <= zg * 1.005:
                        if df.loc[pullback_idx, "close"] > zg:
                            df.loc[pullback_idx, "buy_3"] = True
                            df.loc[pullback_idx, "signal"] = "B3"
                        break
                break

    # --- Type 3 Sell: breakdown + retest of ZD ---
    for zs in zhongshu_zones:
        zd = zs["zd"]
        end = zs["end_idx"]

        for idx in range(end + 1, min(len(df), end + 50)):
            if df.loc[idx, "close"] < zd:
                for rally_idx in range(idx + 1, min(len(df), idx + 20)):
                    if df.loc[rally_idx, "high"] >= zd * 0.995:
                        if df.loc[rally_idx, "close"] < zd:
                            df.loc[rally_idx, "sell_3"] = True
                            df.loc[rally_idx, "signal"] = "S3"
                        break
                break

    # --- Type 2 Buy: retest after first rally (check support above prior low) ---
    buy_1_points = df[df["buy_1"]]
    for b1_idx in buy_1_points.index:
        # After B1, price should rally then pull back (not below B1 low)
        look_ahead = min(len(df), b1_idx + 20)
        rally_found = False
        for idx in range(b1_idx + 3, look_ahead):
            if not rally_found and df.loc[idx, "close"] > df.loc[b1_idx, "close"] * 1.02:
                rally_found = True
                continue
            if rally_found and df.loc[idx, "low"] < df.loc[idx - 1, "low"]:
                if df.loc[idx, "low"] > df.loc[b1_idx, "low"]:
                    df.loc[idx, "buy_2"] = True
                    df.loc[idx, "signal"] = "B2"
                break

    # --- Type 2 Sell: retest after first decline ---
    sell_1_points = df[df["sell_1"]]
    for s1_idx in sell_1_points.index:
        look_ahead = min(len(df), s1_idx + 20)
        decline_found = False
        for idx in range(s1_idx + 3, look_ahead):
            if not decline_found and df.loc[idx, "close"] < df.loc[s1_idx, "close"] * 0.98:
                decline_found = True
                continue
            if decline_found and df.loc[idx, "high"] > df.loc[idx - 1, "high"]:
                if df.loc[idx, "high"] < df.loc[s1_idx, "high"]:
                    df.loc[idx, "sell_2"] = True
                    df.loc[idx, "signal"] = "S2"
                break

    return df


def get_buy_sell_summary(df: pd.DataFrame) -> list[dict]:
    """Extract all buy/sell signals as a list for display."""
    signals = []
    signal_cols = {
        "buy_1": "B1-一类买点",
        "buy_2": "B2-二类买点",
        "buy_3": "B3-三类买点",
        "sell_1": "S1-一类卖点",
        "sell_2": "S2-二类卖点",
        "sell_3": "S3-三类卖点",
    }

    for col, label in signal_cols.items():
        for idx in df[df[col]].index:
            row = df.loc[idx]
            signals.append({
                "date": str(idx)[:10],
                "type": label,
                "price": round(float(row["close"]), 2),
                "direction": "buy" if "buy" in col else "sell",
            })

    signals.sort(key=lambda x: x["date"])
    return signals
