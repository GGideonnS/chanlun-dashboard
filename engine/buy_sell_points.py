"""
Three-type buy/sell points (三类买卖点) detection.

基于缠中说禅《教你炒股票》定义：
- 第一类买点: 男上位最后一吻后出现的背驰式下跌构成
- 第二类买点: 女上位第一吻后出现的下跌构成
- 第三类买点: 次级别走势向上离开中枢，回试低点不跌破ZG
- 第一类卖点: 与第一类买点对称
- 第二类卖点: 与第二类买点对称
- 第三类卖点: 次级别走势向下离开中枢，回抽高点不升破ZD
"""

import pandas as pd
import numpy as np
from .zhongshu import get_zhongshu_list


def _pos(df, idx) -> int:
    """Convert any index value to positional integer."""
    try:
        return df.index.get_loc(idx)
    except (KeyError, TypeError):
        return int(idx)


def _has_male_position(df, pos, lookback=5) -> bool:
    """检查是否处于男上位 (短期均线在长期均线之下)"""
    if "male_position" in df.columns:
        return bool(df["male_position"].iloc[max(0, pos - lookback):pos + 1].any())
    return True


def _has_female_position(df, pos, lookback=5) -> bool:
    """检查是否处于女上位 (短期均线在长期均线之上)"""
    if "female_position" in df.columns:
        return bool(df["female_position"].iloc[max(0, pos - lookback):pos + 1].any())
    return True


def _recent_kiss_type(df, pos, lookback=10) -> str:
    """获取最近的吻类型"""
    if "kiss_type" in df.columns:
        recent = df["kiss_type"].iloc[max(0, pos - lookback):pos + 1]
        if "shiwen" in recent.values:
            return "shiwen"
        elif "chunwen" in recent.values:
            return "chunwen"
        elif "feiwen" in recent.values:
            return "feiwen"
    return "none"


def find_buy_sell_points(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detect Type 1/2/3 buy points and sell points.

    基于缠论原定义，结合均线系统：
    - B1: 男上位 + 湿吻后 + 背驰下跌
    - B2: 女上位 + 第一吻后 + 回调不破前低
    - B3: 向上离开中枢 + 回测不破ZG
    - S1: 女上位 + 湿吻后 + 背驰上涨
    - S2: 男上位 + 第一吻后 + 反弹不创新高
    - S3: 向下离开中枢 + 回抽不破ZD
    """
    df = df.copy()
    for col in ["buy_1", "buy_2", "buy_3", "sell_1", "sell_2", "sell_3"]:
        df[col] = False
    df["signal"] = ""
    n = len(df)

    zhongshu_zones = get_zhongshu_list(df)

    # --- Type 1 Buy: 男上位最后一吻后背驰下跌 ---
    for pos in range(n):
        if not df["bottom_divergence"].iloc[pos]:
            continue

        # 检查是否处于男上位
        if not _has_male_position(df, pos):
            continue

        # 检查是否有湿吻（均线交叉）
        kiss = _recent_kiss_type(df, pos)
        if kiss != "shiwen":
            continue

        # 下跌趋势确认
        recent = df.iloc[max(0, pos - 5): pos + 1]
        if recent["close"].iloc[-1] < recent["close"].iloc[0]:
            df.iloc[pos, df.columns.get_loc("buy_1")] = True
            df.iloc[pos, df.columns.get_loc("signal")] = "B1"

    # --- Type 1 Sell: 女上位最后一吻后背驰上涨 ---
    for pos in range(n):
        if not df["top_divergence"].iloc[pos]:
            continue

        # 检查是否处于女上位
        if not _has_female_position(df, pos):
            continue

        # 检查是否有湿吻
        kiss = _recent_kiss_type(df, pos)
        if kiss != "shiwen":
            continue

        # 上涨趋势确认
        recent = df.iloc[max(0, pos - 5): pos + 1]
        if recent["close"].iloc[-1] > recent["close"].iloc[0]:
            df.iloc[pos, df.columns.get_loc("sell_1")] = True
            df.iloc[pos, df.columns.get_loc("signal")] = "S1"

    # --- Type 3 Buy: 向上离开中枢 + 回测不破ZG ---
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

    # --- Type 3 Sell: 向下离开中枢 + 回抽不破ZD ---
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

    # --- Type 2 Buy: 女上位第一吻后回调不破前低 ---
    buy_1_positions = [pos for pos in range(n) if df["buy_1"].iloc[pos]]

    for b1_pos in buy_1_positions:
        b1_close = df["close"].iloc[b1_pos]
        b1_low = df["low"].iloc[b1_pos]

        # 从B1后寻找反弹
        rally_found = False
        for pos in range(b1_pos + 3, min(n, b1_pos + 30)):
            if not rally_found:
                if df["close"].iloc[pos] > b1_close * 1.02:
                    rally_found = True
                continue

            # 反弹后回调
            if df["low"].iloc[pos] < df["low"].iloc[pos - 1]:
                # 回调不破B1低点
                if df["low"].iloc[pos] > b1_low:
                    # 检查是否进入女上位
                    if _has_female_position(df, pos):
                        df.iloc[pos, df.columns.get_loc("buy_2")] = True
                        df.iloc[pos, df.columns.get_loc("signal")] = "B2"
                break

    # --- Type 2 Sell: 男上位第一吻后反弹不创新高 ---
    sell_1_positions = [pos for pos in range(n) if df["sell_1"].iloc[pos]]

    for s1_pos in sell_1_positions:
        s1_close = df["close"].iloc[s1_pos]
        s1_high = df["high"].iloc[s1_pos]

        # 从S1后寻找下跌
        decline_found = False
        for pos in range(s1_pos + 3, min(n, s1_pos + 30)):
            if not decline_found:
                if df["close"].iloc[pos] < s1_close * 0.98:
                    decline_found = True
                continue

            # 下跌后反弹
            if df["high"].iloc[pos] > df["high"].iloc[pos - 1]:
                # 反弹不破S1高点
                if df["high"].iloc[pos] < s1_high:
                    # 检查是否进入男上位
                    if _has_male_position(df, pos):
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
