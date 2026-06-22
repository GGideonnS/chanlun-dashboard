"""
均线系统 (MA System) — 缠论核心框架

基于缠中说禅《教你炒股票》第14课：
- 飞吻: 短期均线略略走平后继续按原来趋势进行下去
- 唇吻: 短期均线靠近长期均线但不跌破或升破
- 湿吻: 短期均线跌破或升破长期均线甚至出现反复缠绕
- 男上位: 短期均线在长期均线之下
- 女上位: 短期均线在长期均线之上
"""

import pandas as pd
import numpy as np


def compute_ma(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算均线系统
    MA5/MA10/MA20/MA60 + 男上位/女上位/吻类型
    """
    df = df.copy()

    # 计算均线
    df["ma5"] = df["close"].rolling(5, min_periods=1).mean()
    df["ma10"] = df["close"].rolling(10, min_periods=1).mean()
    df["ma20"] = df["close"].rolling(20, min_periods=1).mean()
    df["ma60"] = df["close"].rolling(60, min_periods=1).mean()

    # 男上位/女上位判断 (基于 MA5 vs MA60)
    df["male_position"] = df["ma5"] < df["ma60"]  # 男上位: 短期均线在长期均线之下
    df["female_position"] = df["ma5"] > df["ma60"]  # 女上位: 短期均线在长期均线之上

    # 检测吻类型
    df["kiss_type"] = "none"  # none / feiwen / chunwen / shiwen

    for i in range(2, len(df)):
        ma5_curr = df["ma5"].iloc[i]
        ma5_prev = df["ma5"].iloc[i - 1]
        ma5_prev2 = df["ma5"].iloc[i - 2]
        ma20_curr = df["ma20"].iloc[i]
        ma20_prev = df["ma20"].iloc[i - 1]

        if pd.isna(ma5_curr) or pd.isna(ma20_curr):
            continue

        # 计算MA5斜率
        slope = ma5_curr - ma5_prev
        slope_prev = ma5_prev - ma5_prev2

        # 检测MA5与MA20的距离变化
        dist_curr = abs(ma5_curr - ma20_curr)
        dist_prev = abs(ma5_prev - ma20_prev)

        # 判断是否在均线交叉附近
        ma5_above_ma20 = ma5_curr > ma20_curr
        ma5_above_ma20_prev = ma5_prev > ma20_prev

        if ma5_above_ma20 == ma5_above_ma20_prev:
            # 没有交叉
            if dist_curr < dist_prev * 0.5 and abs(slope) < abs(slope_prev) * 0.3:
                # 飞吻: 靠近后走平，继续原方向
                df.iloc[i, df.columns.get_loc("kiss_type")] = "feiwen"
            elif dist_curr < ma20_curr * 0.01:
                # 唇吻: 靠近但不跌破/升破
                df.iloc[i, df.columns.get_loc("kiss_type")] = "chunwen"
        else:
            # 发生了交叉 → 湿吻
            df.iloc[i, df.columns.get_loc("kiss_type")] = "shiwen"

    # 清理
    for col in ["male_position", "female_position"]:
        df[col] = df[col].fillna(False).astype(bool)

    return df


def get_trend_type(df: pd.DataFrame) -> str:
    """
    判断当前走势类型
    基于缠论定义：
    - 上涨: 高点递增 + 低点递增
    - 下跌: 高点递减 + 低点递减
    - 盘整: 其他情况
    """
    if len(df) < 20:
        return "unknown"

    recent = df.tail(20)

    # 检查高点和低点的趋势
    highs = recent["high"].values
    lows = recent["low"].values

    # 简单线性回归斜率
    x = np.arange(len(highs))
    high_slope = np.polyfit(x, highs, 1)[0]
    low_slope = np.polyfit(x, lows, 1)[0]

    if high_slope > 0 and low_slope > 0:
        return "上涨"
    elif high_slope < 0 and low_slope < 0:
        return "下跌"
    else:
        return "盘整"


def get_kiss_summary(df: pd.DataFrame) -> dict:
    """获取最近的吻信息"""
    default = {
        "last_kiss": "none",
        "kiss_distribution": {},
        "in_male_position": False,
        "in_female_position": False,
    }

    if "kiss_type" not in df.columns or "male_position" not in df.columns:
        return default

    recent = df.tail(10)

    try:
        kiss_counts = recent["kiss_type"].value_counts().to_dict()
        return {
            "last_kiss": recent["kiss_type"].iloc[-1],
            "kiss_distribution": kiss_counts,
            "in_male_position": bool(recent["male_position"].iloc[-1]),
            "in_female_position": bool(recent["female_position"].iloc[-1]),
        }
    except Exception:
        return default
