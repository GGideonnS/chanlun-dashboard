"""Three-type buy/sell points (三类买卖点) detection."""

import pandas as pd
import numpy as np
from .zhongshu import get_zhongshu_list


def _pos(df, idx) -> int:
    """Convert any index value to positional integer."""
    try:
        return df.index.get_loc(idx)
    except (KeyError, TypeError):
        return int(idx)


def find_buy_sell_points(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detect Type 1/2/3 buy points and sell points.
    Uses positional indices throughout for safety with all index types.
    """
    df = df.copy()
    for col in ["buy_1", "buy_2", "buy_3", "sell_1", "sell_2", "sell_3"]:
        df[col] = False
    df["signal"] = ""
    n = len(df)

    zhongshu_zones = get_zhongshu_list(df)

    # --- Type 1 Buy: bottom divergence at end of downtrend ---
    for pos in range(n):
        if df["bottom_divergence"].iloc[pos]:
            recent = df.iloc[max(0, pos - 5): pos + 1]
            if recent["close"].iloc[-1] < recent["close"].iloc[0]:
                df.iloc[pos, df.columns.get_loc("buy_1")] = True
                df.iloc[pos, df.columns.get_loc("signal")] = "B1"

    # --- Type 1 Sell: top divergence at end of uptrend ---
    for pos in range(n):
        if df["top_divergence"].iloc[pos]:
            recent = df.iloc[max(0, pos - 5): pos + 1]
            if recent["close"].iloc[-1] > recent["close"].iloc[0]:
                df.iloc[pos, df.columns.get_loc("sell_1")] = True
                df.iloc[pos, df.columns.get_loc("signal")] = "S1"

    # --- Type 3 Buy: breakout above ZG + successful retest ---
    for zs in zhongshu_zones:
        zg = zs["zg"]
        end = _pos(df, zs["end_idx"])
        for pos in range(end + 1, min(n, end + 50)):
            if df["close"].iloc[pos] > zg:
                for pb_pos in range(pos + 1, min(n, pos + 20)):
                    if df["low"].iloc[pb_pos] <= zg * 1.005:
                        if df["close"].iloc[pb_pos] > zg:
                            df.iloc[pb_pos, df.columns.get_loc("buy_3")] = True
                            df.iloc[pb_pos, df.columns.get_loc("signal")] = "B3"
                        break
                break

    # --- Type 3 Sell: breakdown below ZD + failed retest ---
    for zs in zhongshu_zones:
        zd = zs["zd"]
        end = _pos(df, zs["end_idx"])
        for pos in range(end + 1, min(n, end + 50)):
            if df["close"].iloc[pos] < zd:
                for rally_pos in range(pos + 1, min(n, pos + 20)):
                    if df["high"].iloc[rally_pos] >= zd * 0.995:
                        if df["close"].iloc[rally_pos] < zd:
                            df.iloc[rally_pos, df.columns.get_loc("sell_3")] = True
                            df.iloc[rally_pos, df.columns.get_loc("signal")] = "S3"
                        break
                break

    # --- Type 2 Buy: retest after first rally ---
    for b1_pos in range(n):
        if df["buy_1"].iloc[b1_pos]:
            b1_close = df["close"].iloc[b1_pos]
            b1_low = df["low"].iloc[b1_pos]
            rally_found = False
            for pos in range(b1_pos + 3, min(n, b1_pos + 20)):
                if not rally_found and df["close"].iloc[pos] > b1_close * 1.02:
                    rally_found = True
                    continue
                if rally_found and df["low"].iloc[pos] < df["low"].iloc[pos - 1]:
                    if df["low"].iloc[pos] > b1_low:
                        df.iloc[pos, df.columns.get_loc("buy_2")] = True
                        df.iloc[pos, df.columns.get_loc("signal")] = "B2"
                    break

    # --- Type 2 Sell: retest after first decline ---
    for s1_pos in range(n):
        if df["sell_1"].iloc[s1_pos]:
            s1_close = df["close"].iloc[s1_pos]
            s1_high = df["high"].iloc[s1_pos]
            decline_found = False
            for pos in range(s1_pos + 3, min(n, s1_pos + 20)):
                if not decline_found and df["close"].iloc[pos] < s1_close * 0.98:
                    decline_found = True
                    continue
                if decline_found and df["high"].iloc[pos] > df["high"].iloc[pos - 1]:
                    if df["high"].iloc[pos] < s1_high:
                        df.iloc[pos, df.columns.get_loc("sell_2")] = True
                        df.iloc[pos, df.columns.get_loc("signal")] = "S2"
                    break

    # Clean boolean columns
    for col in ["buy_1", "buy_2", "buy_3", "sell_1", "sell_2", "sell_3"]:
        df[col] = df[col].fillna(False).astype(bool)
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
        for idx in df[df[col].fillna(False)].index:
            row = df.loc[idx]
            signals.append({
                "date": str(idx)[:10],
                "type": label,
                "price": round(float(row["close"]), 2),
                "direction": "buy" if "buy" in col else "sell",
            })

    signals.sort(key=lambda x: x["date"])
    return signals
