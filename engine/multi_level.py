"""Multi-timeframe resonance analysis."""

import pandas as pd
import numpy as np


def compute_resonance(results: dict[str, pd.DataFrame]) -> dict:
    """
    Check signal resonance across multiple timeframes.

    results = {"daily": df_daily, "30min": df_30min, "weekly": df_weekly, ...}

    Returns dict with resonance score and details.
    """
    if not results:
        return {"score": 0, "details": [], "conclusion": "无数据"}

    buy_signals = {}
    sell_signals = {}

    for level_name, df in results.items():
        b1 = list(df[df["buy_1"]].index)
        b2 = list(df[df["buy_2"]].index)
        b3 = list(df[df["buy_3"]].index)
        s1 = list(df[df["sell_1"]].index)
        s2 = list(df[df["sell_2"]].index)
        s3 = list(df[df["sell_3"]].index)

        buy_signals[level_name] = {"B1": len(b1), "B2": len(b2), "B3": len(b3)}
        sell_signals[level_name] = {"S1": len(s1), "S2": len(s2), "S3": len(s3)}

    # Compute resonance: how many levels agree
    total_buy = sum(
        1 for v in buy_signals.values()
        if v["B1"] + v["B2"] + v["B3"] > 0
    )
    total_sell = sum(
        1 for v in sell_signals.values()
        if v["S1"] + v["S2"] + v["S3"] > 0
    )

    details = []
    for level_name in results:
        b = buy_signals[level_name]
        s = sell_signals[level_name]
        details.append(
            f"{level_name}: 买点B1×{b['B1']} B2×{b['B2']} B3×{b['B3']} "
            f"卖点S1×{s['S1']} S2×{s['S2']} S3×{s['S3']}"
        )

    total_levels = len(results)
    if total_buy >= total_levels * 0.6:
        conclusion = "多级别共振看多，信号置信度高"
        score = total_buy / total_levels
    elif total_sell >= total_levels * 0.6:
        conclusion = "多级别共振看空，信号置信度高"
        score = -total_sell / total_levels
    else:
        conclusion = "多级别信号不一致，建议观望"
        score = 0

    return {
        "score": round(score, 2),
        "details": details,
        "conclusion": conclusion,
        "buy_signals": buy_signals,
        "sell_signals": sell_signals,
    }
