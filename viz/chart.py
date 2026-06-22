"""Plotly K-line chart with Chan Theory annotations."""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from . import theme
from engine import get_bi_segments, get_zhongshu_list, get_buy_sell_summary

# Signal type descriptions for hover tooltips
SIGNAL_DESC = {
    "B1-一类买点": "一类买点：下跌背驰形成，女上位的最后一吻。买入信号最强，建议分批建仓。",
    "B2-二类买点": "二类买点：女上位第一吻后的回调，不创新低。确认趋势反转，可加仓。",
    "B3-三类买点": "三类买点：向上离开中枢后回测ZG不破。突破确认，轻仓追涨。",
    "S1-一类卖点": "一类卖点：上涨背驰形成，男上位的最后一吻。卖出信号最强，建议减仓。",
    "S2-二类卖点": "二类卖点：男上位第一吻后的反弹，不创新高。确认趋势转空，应止盈。",
    "S3-三类卖点": "三类卖点：向下离开中枢后回抽ZD不破。跌破确认，及时止损。",
}

FRACTAL_DESC = {
    "top": "顶分型：中间K线高点最高，且左右K线不包含。上涨笔可能在此结束，关注卖点。",
    "bottom": "底分型：中间K线低点最低，且左右K线不包含。下跌笔可能在此结束，关注买点。",
}


def _get_ohlc(df):
    """Return OHLC columns, preferring raw (pre-containment) values."""
    plot_df = df.reset_index()
    date_col = plot_df.columns[0]
    o = plot_df["raw_open"] if "raw_open" in plot_df.columns else plot_df["open"]
    h = plot_df["raw_high"] if "raw_high" in plot_df.columns else plot_df["high"]
    l = plot_df["raw_low"] if "raw_low" in plot_df.columns else plot_df["low"]
    c = plot_df["raw_close"] if "raw_close" in plot_df.columns else plot_df["close"]
    return plot_df, date_col, o, h, l, c


def build_chanlun_chart(df: pd.DataFrame, meta: dict) -> go.Figure:
    """Build interactive Plotly chart with Candlestick + Chan Theory + MACD."""

    plot_df, date_col, o, h, l, c = _get_ohlc(df)
    # Map processed index positions to dates
    idx_to_date = plot_df[date_col].tolist()

    # ── Subplots ───────────────────────────────────────────────────
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03,
        row_heights=[0.75, 0.25],
        subplot_titles=(f"{meta.get('name', meta['display'])} — {meta.get('level_label', '')}",
                        "MACD 背驰"),
    )

    # ── Candlestick (raw OHLC) ─────────────────────────────────────
    fig.add_trace(
        go.Candlestick(
            x=plot_df[date_col],
            open=o, high=h, low=l, close=c,
            name="K线",
            increasing=dict(line=dict(color=theme.BULL_COLOR), fillcolor=theme.BULL_COLOR),
            decreasing=dict(line=dict(color=theme.BEAR_COLOR), fillcolor=theme.BEAR_COLOR),
            hovertemplate=(
                "日期: %{x|%Y-%m-%d}<br>"
                "开: ¥%{open:.2f}<br>高: ¥%{high:.2f}<br>"
                "低: ¥%{low:.2f}<br>收: ¥%{close:.2f}<extra></extra>"
            ),
        ),
        row=1, col=1,
    )

    # ── Fractal markers ─────────────────────────────────────────────
    top_frac = plot_df[plot_df.get("top_fractal", pd.Series(False, index=plot_df.index)).fillna(False)]
    bottom_frac = plot_df[plot_df.get("bottom_fractal", pd.Series(False, index=plot_df.index)).fillna(False)]

    for frac_df, direction, color_key, desc_key in [
        (top_frac, "顶分型 → 上涨笔可能结束", theme.TOP_FRACTAL_COLOR, "top"),
        (bottom_frac, "底分型 → 下跌笔可能结束", theme.BOTTOM_FRACTAL_COLOR, "bottom"),
    ]:
        if len(frac_df) > 0:
            marker_y = (
                frac_df["raw_high"] * 1.005
                if "raw_high" in frac_df.columns
                else frac_df["high"] * 1.005
            )
            fig.add_trace(
                go.Scatter(
                    x=frac_df[date_col],
                    y=marker_y,
                    mode="markers",
                    marker=dict(
                        symbol="triangle-down" if direction.startswith("顶") else "triangle-up",
                        size=theme.FRACTAL_SIZE, color=color_key,
                        line=dict(width=1, color="#fff"),
                    ),
                    name="顶分型" if direction.startswith("顶") else "底分型",
                    hovertemplate=(
                        f"<b>{'顶分型' if direction.startswith('顶') else '底分型'}</b><br>"
                        f"%{{x|%Y-%m-%d}}<br>¥%{{y:.2f}}<br>"
                        f"<i>{FRACTAL_DESC[desc_key]}</i><extra></extra>"
                    ),
                ),
                row=1, col=1,
            )

    # ── Bi strokes ──────────────────────────────────────────────────
    bi_segs = get_bi_segments(df)
    for i, seg in enumerate(bi_segs):
        s_date = idx_to_date[seg["start_idx"]] if seg["start_idx"] < len(idx_to_date) else ""
        e_date = idx_to_date[seg["end_idx"]] if seg["end_idx"] < len(idx_to_date) else ""
        dir_cn = "向上笔 ↑" if seg["direction"] == "up" else "向下笔 ↓"
        pct = (
            abs(seg["end_val"] - seg["start_val"]) / seg["start_val"] * 100
            if seg["start_val"] else 0
        )
        fig.add_trace(
            go.Scatter(
                x=[s_date, e_date],
                y=[seg["start_val"], seg["end_val"]],
                mode="lines+markers",
                line=dict(color=theme.BI_COLOR, width=1.5, dash="dot"),
                marker=dict(size=4, color=theme.BI_COLOR),
                name=f"笔 #{i + 1}",
                showlegend=False,
                hovertemplate=(
                    f"<b>笔 (Bi) #{i + 1}</b> — {dir_cn}<br>"
                    f"{s_date} → {e_date}<br>"
                    f"¥{seg['start_val']:.2f} → ¥{seg['end_val']:.2f}<br>"
                    f"幅度: {pct:.1f}%<extra></extra>"
                ),
            ),
            row=1, col=1,
        )

    # ── Zhongshu ────────────────────────────────────────────────────
    zhongshu_zones = get_zhongshu_list(df)
    for zs in zhongshu_zones:
        s_date = idx_to_date[zs["start_idx"]] if zs["start_idx"] < len(idx_to_date) else ""
        e_date = idx_to_date[zs["end_idx"]] if zs["end_idx"] < len(idx_to_date) else ""
        seg_count = zs.get("segment_count", 3)
        width_pct = (zs["zg"] - zs["zd"]) / zs["zd"] * 100 if zs["zd"] else 0

        # ZG line
        fig.add_trace(go.Scatter(
            x=[s_date, e_date], y=[zs["zg"], zs["zg"]],
            mode="lines",
            line=dict(color=theme.ZS_LINE, width=1, dash="dash"),
            name=f"中枢#{zs['period']} ZG",
            showlegend=False, hoverinfo="skip",
        ), row=1, col=1)
        # ZD line
        fig.add_trace(go.Scatter(
            x=[s_date, e_date], y=[zs["zd"], zs["zd"]],
            mode="lines",
            line=dict(color=theme.ZS_LINE, width=1, dash="dash"),
            name=f"中枢#{zs['period']} ZD",
            showlegend=False, hoverinfo="skip",
        ), row=1, col=1)
        # Fill
        fig.add_trace(go.Scatter(
            x=[s_date, e_date, e_date, s_date],
            y=[zs["zg"], zs["zg"], zs["zd"], zs["zd"]],
            fill="toself", fillcolor=theme.ZS_FILL, line=dict(width=0),
            name=f"中枢{zs['period']}：¥{zs['zd']:.2f}-¥{zs['zg']:.2f} ({seg_count}段，宽{width_pct:.1f}%)",
            hovertemplate=(
                f"<b>缠中说禅走势中枢 #{zs['period']}</b><br>"
                f"ZG (上沿): ¥{zs['zg']:.2f}<br>"
                f"ZD (下沿): ¥{zs['zd']:.2f}<br>"
                f"中枢区间: ¥{zs['zd']:.2f} — ¥{zs['zg']:.2f}<br>"
                f"包含 {seg_count} 个线段<br>区间宽度: {width_pct:.1f}%<br>"
                f"<i>中枢震荡策略：下沿附近关注买点，上沿附近关注卖点</i><extra></extra>"
            ),
        ), row=1, col=1)

    # ── Buy/Sell points ─────────────────────────────────────────────
    buy_sell = get_buy_sell_summary(df)
    signal_colors = {
        "B1-一类买点": theme.B1_COLOR, "B2-二类买点": theme.B2_COLOR,
        "B3-三类买点": theme.B3_COLOR, "S1-一类卖点": theme.S1_COLOR,
        "S2-二类卖点": theme.S2_COLOR, "S3-三类卖点": theme.S3_COLOR,
    }
    for bs in buy_sell:
        color = signal_colors.get(bs["type"], "#fff")
        sym = "triangle-up" if bs["direction"] == "buy" else "triangle-down"
        y_pos = bs["price"] * (0.96 if bs["direction"] == "buy" else 1.04)

        fig.add_trace(go.Scatter(
            x=[bs["date"]], y=[y_pos],
            mode="markers+text",
            marker=dict(
                symbol=sym, size=theme.BUY_SELL_SIZE, color=color,
                line=dict(width=1.5, color="#fff"),
            ),
            text=bs["type"][:2],
            textposition="bottom center" if bs["direction"] == "buy" else "top center",
            textfont=dict(size=10, color=color, family="Arial Black"),
            name=bs["type"],
            hovertemplate=(
                f"<b>{bs['type']}</b><br>"
                f"日期: %{{x|%Y-%m-%d}}<br>"
                f"价格: ¥{bs['price']:.2f}<br>"
                f"<i>{SIGNAL_DESC.get(bs['type'], '')}</i><extra></extra>"
            ),
        ), row=1, col=1)

    # ── MACD ────────────────────────────────────────────────────────
    if "DIF" in df.columns:
        fig.add_trace(go.Scatter(
            x=plot_df[date_col], y=df["DIF"],
            mode="lines", name="DIF (快线)",
            line=dict(color=theme.DIF_COLOR, width=1),
            hovertemplate="DIF: %{y:.4f}<extra></extra>",
        ), row=2, col=1)
        fig.add_trace(go.Scatter(
            x=plot_df[date_col], y=df["DEA"],
            mode="lines", name="DEA (慢线)",
            line=dict(color=theme.DEA_COLOR, width=1),
            hovertemplate="DEA: %{y:.4f}<extra></extra>",
        ), row=2, col=1)

        macd_vals = df["MACD_bar"].values
        colors = [theme.MACD_BULL if v >= 0 else theme.MACD_BEAR for v in macd_vals]
        fig.add_trace(go.Bar(
            x=plot_df[date_col], y=df["MACD_bar"],
            name="MACD柱",
            marker=dict(color=colors), opacity=0.7,
            hovertemplate="MACD: %{y:.4f}<extra></extra>",
        ), row=2, col=1)

        # Divergence markers
        top_div = df[df["top_divergence"]]
        bottom_div = df[df["bottom_divergence"]]

        if len(top_div) > 0:
            y_max = max(
                top_div["raw_high"].max() if "raw_high" in top_div.columns else top_div["high"].max(),
                top_div["high"].max(),
            )
            fig.add_trace(go.Scatter(
                x=top_div.index, y=[y_max * 1.02] * len(top_div),
                mode="markers",
                marker=dict(symbol="circle", size=10, color=theme.S1_COLOR, opacity=0.7,
                           line=dict(width=1, color="#fff")),
                name="顶背驰",
                hovertemplate=(
                    f"<b>⚠️ 顶背驰</b><br>"
                    f"%{{x|%Y-%m-%d}}<br>"
                    f"<i>价格创新高，但MACD动能面积缩小<br>"
                    f"上涨力度衰竭 → 对应一类卖点</i><extra></extra>"
                ),
            ), row=1, col=1)

        if len(bottom_div) > 0:
            y_min = min(
                bottom_div["raw_low"].min() if "raw_low" in bottom_div.columns else bottom_div["low"].min(),
                bottom_div["low"].min(),
            )
            fig.add_trace(go.Scatter(
                x=bottom_div.index, y=[y_min * 0.98] * len(bottom_div),
                mode="markers",
                marker=dict(symbol="circle", size=10, color=theme.B1_COLOR, opacity=0.7,
                           line=dict(width=1, color="#fff")),
                name="底背驰",
                hovertemplate=(
                    f"<b>✅ 底背驰</b><br>"
                    f"%{{x|%Y-%m-%d}}<br>"
                    f"<i>价格创新低，但MACD动能面积缩小<br>"
                    f"下跌力度衰竭 → 对应一类买点</i><extra></extra>"
                ),
            ), row=1, col=1)

    # ── Layout ──────────────────────────────────────────────────────
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=theme.BG_COLOR,
        plot_bgcolor=theme.PLOT_BG,
        font=dict(color=theme.TEXT_COLOR, size=11),
        dragmode="pan",               # pan mode, no box-zoom select
        height=theme.CHART_HEIGHT + theme.MACD_HEIGHT,
        margin=theme.MARGIN,
        legend=dict(
            orientation="h", yanchor="top", y=1.15,
            xanchor="left", x=0, font=dict(size=10),
        ),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#1a1a2e", font_size=12, font_family="Microsoft YaHei"),
    )

    # X-axis: range slider (bottom scrollbar) + date labels
    fig.update_xaxes(
        showgrid=True, gridcolor=theme.GRID_COLOR, zeroline=False,
        tickformat="%m/%d\n%Y",
        rangeslider_visible=True,
        rangeslider_thickness=0.08,
        row=1, col=1,
    )
    fig.update_xaxes(
        showgrid=True, gridcolor=theme.GRID_COLOR, zeroline=False,
        tickformat="%m/%d\n%Y",
        title_text="← 拖动下方滑条选择时间范围 | 滚轮缩放 | 拖拽平移 →",
        row=2, col=1,
    )
    fig.update_yaxes(
        title_text="价格", showgrid=True,
        gridcolor=theme.GRID_COLOR,
        fixedrange=False,  # allow scroll-wheel y zoom
        row=1, col=1,
    )
    fig.update_yaxes(
        title_text="MACD", showgrid=True,
        gridcolor=theme.GRID_COLOR,
        fixedrange=False,
        row=2, col=1,
    )

    return fig
