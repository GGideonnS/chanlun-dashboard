"""
历史回测模块 — 统计买卖点信号的历史胜率

功能：
1. 信号发出后的N日收益统计
2. 胜率/盈亏比计算
3. 各类信号对比
"""

import pandas as pd
import numpy as np
from .buy_sell_points import get_buy_sell_summary


def backtest_signals(df: pd.DataFrame, hold_days: list[int] = None) -> dict:
    """
    对历史买卖点信号进行回测。

    Args:
        df: 含有买卖点信号的 DataFrame
        hold_days: 持仓天数列表，默认 [1, 3, 5, 10, 20]

    Returns:
        回测结果字典
    """
    if hold_days is None:
        hold_days = [1, 3, 5, 10, 20]

    signals = get_buy_sell_summary(df)
    if not signals:
        return {"signals": [], "summary": {}, "hold_days": hold_days, "total_signals": 0}

    # 构建日期→收盘价映射
    date_to_close = {}
    date_to_pos = {}
    dates = list(df.index)
    for i, dt in enumerate(dates):
        date_str = str(dt)[:10]
        date_to_close[date_str] = float(df["close"].iloc[i])
        date_to_pos[date_str] = i

    results = []
    for sig in signals:
        sig_date = sig["date"]
        if sig_date not in date_to_pos:
            continue

        sig_pos = date_to_pos[sig_date]
        sig_price = sig["price"]
        is_buy = sig["direction"] == "buy"

        row = {
            "date": sig_date,
            "type": sig["type"],
            "direction": sig["direction"],
            "entry_price": sig_price,
        }

        for days in hold_days:
            target_pos = sig_pos + days
            if target_pos < len(dates):
                target_date = str(dates[target_pos])[:10]
                target_price = date_to_close.get(target_date, sig_price)
                pnl_pct = (target_price - sig_price) / sig_price * 100
                if not is_buy:
                    pnl_pct = -pnl_pct  # 卖点取反
                row[f"pnl_{days}d"] = round(pnl_pct, 2)
            else:
                row[f"pnl_{days}d"] = None

        results.append(row)

    # 汇总统计
    summary = {}
    for days in hold_days:
        col = f"pnl_{days}d"
        buy_results = [r for r in results if r["direction"] == "buy" and r.get(col) is not None]
        sell_results = [r for r in results if r["direction"] == "sell" and r.get(col) is not None]

        if buy_results:
            buy_pnls = [r[col] for r in buy_results]
            summary[f"buy_{days}d"] = {
                "count": len(buy_pnls),
                "win_rate": round(sum(1 for p in buy_pnls if p > 0) / len(buy_pnls) * 100, 1),
                "avg_return": round(np.mean(buy_pnls), 2),
                "max_return": round(max(buy_pnls), 2),
                "min_return": round(min(buy_pnls), 2),
            }

        if sell_results:
            sell_pnls = [r[col] for r in sell_results]
            summary[f"sell_{days}d"] = {
                "count": len(sell_pnls),
                "win_rate": round(sum(1 for p in sell_pnls if p > 0) / len(sell_pnls) * 100, 1),
                "avg_return": round(np.mean(sell_pnls), 2),
                "max_return": round(max(sell_pnls), 2),
                "min_return": round(min(sell_pnls), 2),
            }

    return {
        "signals": results,
        "summary": summary,
        "hold_days": hold_days,
        "total_signals": len(results),
    }


def format_backtest_report(bt: dict) -> str:
    """格式化回测报告为 Markdown 文本。"""
    lines = ["## 历史回测结果\n"]

    if not bt or bt.get("total_signals", 0) == 0:
        lines.append("暂无历史信号数据可供回测。")
        return "\n".join(lines)

    total = bt.get("total_signals", 0)
    lines.append(f"**信号总数**: {total} 个\n")

    # 按持仓天数展示
    for days in bt["hold_days"]:
        lines.append(f"### 持仓 {days} 天\n")

        for direction, label in [("buy", "买点"), ("sell", "卖点")]:
            key = f"{direction}_{days}d"
            if key in bt["summary"]:
                s = bt["summary"][key]
                lines.append(f"**{label}**: {s['count']}个信号")
                lines.append(f"- 胜率: **{s['win_rate']}%**")
                lines.append(f"- 平均收益: {s['avg_return']:+.2f}%")
                lines.append(f"- 最大收益: {s['max_return']:+.2f}%")
                lines.append(f"- 最大亏损: {s['min_return']:+.2f}%")
                lines.append("")

    # 最近信号详情
    recent = bt["signals"][-5:] if len(bt["signals"]) > 5 else bt["signals"]
    if recent:
        lines.append("### 最近信号详情\n")
        lines.append("| 日期 | 类型 | 入场价 | 1日 | 5日 | 10日 |")
        lines.append("|------|------|--------|-----|-----|------|")
        for r in recent:
            pnl1_val = r.get('pnl_1d')
            pnl5_val = r.get('pnl_5d')
            pnl10_val = r.get('pnl_10d')
            pnl1 = f"{pnl1_val:+.2f}%" if pnl1_val is not None else "-"
            pnl5 = f"{pnl5_val:+.2f}%" if pnl5_val is not None else "-"
            pnl10 = f"{pnl10_val:+.2f}%" if pnl10_val is not None else "-"
            lines.append(
                f"| {r['date']} | {r['type']} | {r['entry_price']} | "
                f"{pnl1} | {pnl5} | {pnl10} |"
            )

    return "\n".join(lines)
