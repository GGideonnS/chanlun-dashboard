"""
多级别共振分析模块

功能：
1. 同时分析多个时间级别（日线/30分钟/60分钟/周线）
2. 计算多级别共振评分
3. 识别高置信度信号
"""

import pandas as pd
import numpy as np
from . import (
    find_fractals, build_bi, build_xian_duan,
    find_zhongshu, detect_divergence, compute_ma,
)
from .buy_sell_points import find_buy_sell_points, get_buy_sell_summary
from .zhongshu import get_zhongshu_list


def analyze_single_level(df: pd.DataFrame, level_name: str) -> dict:
    """分析单个级别的缠论信号。"""
    result = {
        "level": level_name,
        "bars": len(df),
        "bi_count": 0,
        "zhongshu_count": 0,
        "buy_signals": [],
        "sell_signals": [],
        "trend": "unknown",
        "divergence": "none",
    }

    if len(df) < 30:
        return result

    try:
        df = compute_ma(df)
        df = find_fractals(df, use_containment=True)
        df = build_bi(df)
        df = build_xian_duan(df)
        df = find_zhongshu(df)
        df = detect_divergence(df)
        df = find_buy_sell_points(df)
    except Exception:
        return result

    from .bi import get_bi_segments
    from .ma_system import get_trend_type

    bi_segs = get_bi_segments(df)
    zs_list = get_zhongshu_list(df)
    signals = get_buy_sell_summary(df)

    result["bi_count"] = len(bi_segs)
    result["zhongshu_count"] = len(zs_list)
    result["buy_signals"] = [s for s in signals if s["direction"] == "buy"]
    result["sell_signals"] = [s for s in signals if s["direction"] == "sell"]
    result["trend"] = get_trend_type(df)

    # 背驰判断
    if df["top_divergence"].any():
        result["divergence"] = "top"
    elif df["bottom_divergence"].any():
        result["divergence"] = "bottom"

    # 中枢位置
    if zs_list:
        zs = zs_list[-1]
        current = float(df["close"].iloc[-1])
        if current > zs["zg"]:
            result["zhongshu_position"] = "above"
        elif current < zs["zd"]:
            result["zhongshu_position"] = "below"
        else:
            result["zhongshu_position"] = "inside"
    else:
        result["zhongshu_position"] = "none"

    return result


def compute_multi_level_resonance(results: list[dict]) -> dict:
    """
    计算多级别共振评分。

    评分规则：
    - 多个级别同方向信号 → 高分
    - 高级别（周线/日线）权重更高
    - 背驰 + 中枢位置一致 → 加分
    """
    if not results:
        return {
            "score": 0,
            "direction": "neutral",
            "confidence": "低",
            "details": [],
            "recommendation": "无数据",
        }

    # 权重配置
    level_weights = {
        "monthly": 4,
        "weekly": 3,
        "daily": 2,
        "60min": 1.5,
        "30min": 1,
    }

    buy_score = 0
    sell_score = 0
    details = []

    for r in results:
        level = r["level"]
        weight = level_weights.get(level, 1)

        # 基础信号分
        if r["buy_signals"]:
            buy_score += weight * len(r["buy_signals"]) * 0.5
            details.append(f"{level}: 买点×{len(r['buy_signals'])}")
        if r["sell_signals"]:
            sell_score += weight * len(r["sell_signals"]) * 0.5
            details.append(f"{level}: 卖点×{len(r['sell_signals'])}")

        # 趋势分
        if r["trend"] == "上涨":
            buy_score += weight * 0.3
        elif r["trend"] == "下跌":
            sell_score += weight * 0.3

        # 背驰分
        if r["divergence"] == "bottom":
            buy_score += weight * 0.5
            details.append(f"{level}: 底背驰")
        elif r["divergence"] == "top":
            sell_score += weight * 0.5
            details.append(f"{level}: 顶背驰")

        # 中枢位置分
        if r.get("zhongshu_position") == "below":
            buy_score += weight * 0.2
        elif r.get("zhongshu_position") == "above":
            sell_score += weight * 0.2

    # 计算总分
    total = buy_score + sell_score
    if total == 0:
        net_score = 0
    else:
        net_score = (buy_score - sell_score) / total

    # 判断方向和置信度
    if net_score > 0.3:
        direction = "看多"
        confidence = "高" if net_score > 0.5 else "中"
    elif net_score < -0.3:
        direction = "看空"
        confidence = "高" if net_score < -0.5 else "中"
    else:
        direction = "中性"
        confidence = "低"

    # 生成建议
    buy_levels = [r["level"] for r in results if r["buy_signals"]]
    sell_levels = [r["level"] for r in results if r["sell_signals"]]

    if direction == "看多" and confidence == "高":
        recommendation = f"多级别共振看多（{', '.join(buy_levels)}）→ 可分批建仓"
    elif direction == "看空" and confidence == "高":
        recommendation = f"多级别共振看空（{', '.join(sell_levels)}）→ 建议减仓/观望"
    elif direction == "看多":
        recommendation = f"偏多但信号不强 → 轻仓试探，等待更多确认"
    elif direction == "看空":
        recommendation = f"偏空但信号不强 → 减仓观望，等待明确信号"
    else:
        recommendation = "多级别信号不一致 → 建议观望"

    return {
        "score": round(net_score, 2),
        "buy_score": round(buy_score, 2),
        "sell_score": round(sell_score, 2),
        "direction": direction,
        "confidence": confidence,
        "details": details,
        "recommendation": recommendation,
        "level_results": results,
    }


def format_resonance_report(resonance: dict) -> str:
    """格式化共振报告为 Markdown。"""
    lines = ["## 多级别共振分析\n"]

    # 总评
    score = resonance["score"]
    direction = resonance["direction"]
    confidence = resonance["confidence"]

    if direction == "看多":
        emoji = "📈"
    elif direction == "看空":
        emoji = "📉"
    else:
        emoji = "➡️"

    lines.append(f"### {emoji} 综合评分: {score:+.2f} ({direction}, 置信度{confidence})\n")

    # 各级别状态
    lines.append("### 各级别状态\n")
    lines.append("| 级别 | K线数 | 笔 | 中枢 | 趋势 | 背驰 | 买点 | 卖点 |")
    lines.append("|------|-------|-----|------|------|------|------|------|")

    for r in resonance.get("level_results", []):
        div = {"top": "顶背驰", "bottom": "底背驰", "none": "-"}.get(r["divergence"], "-")
        lines.append(
            f"| {r['level']} | {r['bars']} | {r['bi_count']} | {r['zhongshu_count']} | "
            f"{r['trend']} | {div} | {len(r['buy_signals'])} | {len(r['sell_signals'])} |"
        )

    lines.append("")

    # 共振详情
    if resonance["details"]:
        lines.append("### 共振信号\n")
        for d in resonance["details"]:
            lines.append(f"- {d}")

    # 建议
    lines.append(f"\n### 操作建议\n> {resonance['recommendation']}")

    return "\n".join(lines)
