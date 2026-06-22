"""Generate human-readable Chan Theory interpretation from analyzed data."""

import pandas as pd

from engine import get_zhongshu_list, get_bi_segments, get_buy_sell_summary


def generate_interpretation(df: pd.DataFrame, meta: dict) -> str:
    """
    Produce detailed Chan Theory interpretation text in Chinese.
    Covers: trend type, current zhongshu, latest bi, divergence status,
    active buy/sell signals, and a trade suggestion.
    """
    lines = []
    level = meta.get("level_label", "日线")

    # ── 1. Trend Type ─────────────────────────────────────────────
    close = df["close"]
    if len(close) >= 40:
        ma20 = close.rolling(20).mean()
        ma60 = close.rolling(60).mean()
        if ma20.iloc[-1] > ma60.iloc[-1]:
            trend = f"**{level}级别：上涨趋势**（MA20 > MA60）"
        elif ma20.iloc[-1] < ma60.iloc[-1]:
            trend = f"**{level}级别：下跌趋势**（MA20 < MA60）"
        else:
            trend = f"**{level}级别：盘整格局**（MA20 ≈ MA60）"
    else:
        trend = f"**{level}级别：上涨趋势**"

    lines.append(f"## 走势分析\n{trend}")

    # ── 2. Zhongshu Status ────────────────────────────────────────
    zhongshu_list = get_zhongshu_list(df)
    if zhongshu_list:
        zs = zhongshu_list[-1]  # Latest zhongshu
        zg = zs["zg"]
        zd = zs["zd"]
        current = close.iloc[-1]

        lines.append(f"\n## 中枢分析")
        lines.append(f"- **当前中枢**: ¥{zd:.2f} — ¥{zg:.2f}（第{zs['period']}个中枢）")
        lines.append(f"- **中枢区间宽度**: ¥{zg - zd:.2f}（{(zg - zd) / zd * 100:.1f}%）")

        # Position relative to zhongshu
        if current > zg:
            lines.append(f"- **当前位置**: 中枢上沿**上方** ¥{current - zg:.2f}")
            lines.append(f"  - ⚠️ 已突破中枢上沿，若不能有效站稳，可能形成**第三类卖点**的反向")
        elif current < zd:
            lines.append(f"- **当前位置**: 中枢下沿**下方** ¥{zd - current:.2f}")
            lines.append(f"  - ⚠️ 已跌破中枢下沿，若反弹不能回到中枢内，可能确认**第三类卖点**")
        else:
            lines.append(f"- **当前位置**: **中枢震荡中**（¥{current:.2f}）")
            lines.append(f"  - 中枢震荡策略：下沿附近关注买点，上沿附近关注卖点")

        # Check zhongshu destruction/extension
        seg_count = zs.get("segment_count", 3)
        if seg_count > 3:
            lines.append(f"- **中枢延伸**: 已包含 {zs['segment_count']} 个线段，中枢级别提升中")
    else:
        lines.append(f"\n## 中枢分析\n- 当前级别尚未形成标准中枢（需至少3个线段重叠）")

    # ── 3. Latest Bi Status ───────────────────────────────────────
    bi_segs = get_bi_segments(df)
    if bi_segs:
        latest_bi = bi_segs[-1]
        direction_cn = "向上笔" if latest_bi["direction"] == "up" else "向下笔"
        lines.append(f"\n## 最近笔分析")
        lines.append(f"- **当前笔**: {direction_cn}，从 ¥{latest_bi['start_val']:.2f} → ¥{latest_bi['end_val']:.2f}")
        pct = abs(latest_bi["end_val"] - latest_bi["start_val"]) / latest_bi["start_val"] * 100
        lines.append(f"- **幅度**: {pct:.1f}%")

        if len(bi_segs) >= 2:
            prev_bi = bi_segs[-2]
            pct_prev = abs(prev_bi["end_val"] - prev_bi["start_val"]) / prev_bi["start_val"] * 100
            lines.append(f"- **前一笔**: {prev_bi['direction']}，幅度 {pct_prev:.1f}%")

    # ── 4. Divergence Analysis ────────────────────────────────────
    has_top = df["top_divergence"].any()
    has_bottom = df["bottom_divergence"].any()
    recent_div = df.iloc[-10:]

    top_div_recent = recent_div[recent_div["top_divergence"]]
    bottom_div_recent = recent_div[recent_div["bottom_divergence"]]

    lines.append(f"\n## 背驰分析")

    if len(top_div_recent) > 0:
        strength = top_div_recent["divergence_strength"].iloc[-1]
        lines.append(f"- ⚠️ **顶背驰信号**（强度: {strength:.0%}）")
        lines.append(f"  - 价格创新高但 MACD 面积缩小 → 上涨力度衰竭")
        lines.append(f"  - 对应**第一类卖点**，建议减仓或设止盈")
    elif len(bottom_div_recent) > 0:
        strength = bottom_div_recent["divergence_strength"].iloc[-1]
        lines.append(f"- ✅ **底背驰信号**（强度: {strength:.0%}）")
        lines.append(f"  - 价格创新低但 MACD 面积缩小 → 下跌力度衰竭")
        lines.append(f"  - 对应**第一类买点**，可分批建仓")
    else:
        # Check overall area trend
        macd_recent = df.iloc[-20:]["MACD_area"] if "MACD_area" in df.columns else pd.Series()
        if len(macd_recent) >= 10:
            if macd_recent.iloc[-1] > macd_recent.iloc[-10]:
                lines.append(f"- MACD 动能**增强**中，趋势延续概率较大")
            else:
                lines.append(f"- MACD 动能**减弱**中，关注背驰形成")
        else:
            lines.append(f"- 当前无明显背驰信号")

    # ── 5. Buy / Sell Signals ─────────────────────────────────────
    buy_sell = get_buy_sell_summary(df)
    recent_signals = [s for s in buy_sell if len(s["date"]) > 0]

    lines.append(f"\n## 买卖点信号")

    active_buys = [s for s in recent_signals if s["direction"] == "buy"]
    active_sells = [s for s in recent_signals if s["direction"] == "sell"]

    if active_buys:
        for s in active_buys[-3:]:
            lines.append(f"- 🟢 {s['date']}: **{s['type']}** @ ¥{s['price']}")
    else:
        lines.append(f"- 当前无活跃买点")

    if active_sells:
        for s in active_sells[-3:]:
            lines.append(f"- 🔴 {s['date']}: **{s['type']}** @ ¥{s['price']}")

    # ── 6. Trade Suggestion ───────────────────────────────────────
    lines.append(f"\n## 操作建议")

    if len(top_div_recent) > 0:
        lines.append(f"> ⚠️ 顶背驰 + 中枢上沿 → **建议减仓**，等待回调到中枢下沿再评估")
    elif len(bottom_div_recent) > 0:
        lines.append(f"> ✅ 底背驰信号 → 可**分批建仓**，止损设在最近低点下方3%")
    elif zhongshu_list:
        current = close.iloc[-1]
        zg = zhongshu_list[-1]["zg"]
        zd = zhongshu_list[-1]["zd"]
        if current > zg:
            lines.append(f"> 价格在中枢上沿，**观望**为主。突破有效则追涨，否则等待回落")
        elif current < zd:
            lines.append(f"> 价格跌破中枢下沿，**谨慎**。若反弹重回中枢可轻仓试多")
        else:
            mid = (zg + zd) / 2
            if current < mid:
                lines.append(f"> 中枢震荡偏下 → 可在下沿附近**轻仓试多**，止损 ¥{zd * 0.98:.2f}")
            else:
                lines.append(f"> 中枢震荡偏上 → 可持有，上沿附近考虑部分止盈")
    else:
        lines.append(f"> 走势结构未完成，建议**等待中枢形成**后再操作")

    lines.append(f"\n---")
    lines.append(f"*分析基于{level}K线，切换级别可获更多信号确认。*")
    lines.append(f"*📌 最新2-3根K线的分型/笔/中枢尚未确认，需后续走势验证。这是缠论特征，所有级别同理。缠论仅供参考，不构成投资建议。*")

    return "\n".join(lines)
