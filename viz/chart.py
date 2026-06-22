"""Plotly K-line chart with Chan Theory annotations."""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from . import theme
from engine import (
    get_bi_segments,
    get_zhongshu_list,
    get_buy_sell_summary,
)


def build_chanlun_chart(
    df: pd.DataFrame,
    meta: dict,
) -> go.Figure:
    """
    Build interactive Plotly chart with:
    - Candlestick OHLC
    - Fractal markers (top/bottom)
    - Bi stroke lines
    - Zhongshu overlay zones
    - Buy/Sell point markers
    - MACD subplot
    """
    # Reset index for plotting
    plot_df = df.reset_index()
    date_col = plot_df.columns[0]

    # ── Create subplots ──────────────────────────────────────────────
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.75, 0.25],
        subplot_titles=(meta.get("name", meta["display"]), "MACD"),
    )

    # ── Row 1: Candlestick + annotations ─────────────────────────────
    fig.add_trace(
        go.Candlestick(
            x=plot_df[date_col],
            open=plot_df["open"],
            high=plot_df["high"],
            low=plot_df["low"],
            close=plot_df["close"],
            name="K线",
            increasing=dict(line=dict(color=theme.BULL_COLOR), fillcolor=theme.BULL_COLOR),
            decreasing=dict(line=dict(color=theme.BEAR_COLOR), fillcolor=theme.BEAR_COLOR),
            showlegend=True,
        ),
        row=1, col=1,
    )

    # Fractal markers
    top_frac = plot_df[plot_df["top_fractal"]]
    bottom_frac = plot_df[plot_df["bottom_fractal"]]

    if len(top_frac) > 0:
        fig.add_trace(
            go.Scatter(
                x=top_frac[date_col],
                y=top_frac["high"] * 1.005,
                mode="markers",
                marker=dict(
                    symbol="triangle-down",
                    size=theme.FRACTAL_SIZE,
                    color=theme.TOP_FRACTAL_COLOR,
                    line=dict(width=1, color="#fff"),
                ),
                name="顶分型",
                hovertemplate="顶分型<br>%{x}<br>¥%{y:.2f}<extra></extra>",
            ),
            row=1, col=1,
        )

    if len(bottom_frac) > 0:
        fig.add_trace(
            go.Scatter(
                x=bottom_frac[date_col],
                y=bottom_frac["low"] * 0.995,
                mode="markers",
                marker=dict(
                    symbol="triangle-up",
                    size=theme.FRACTAL_SIZE,
                    color=theme.BOTTOM_FRACTAL_COLOR,
                    line=dict(width=1, color="#fff"),
                ),
                name="底分型",
                hovertemplate="底分型<br>%{x}<br>¥%{y:.2f}<extra></extra>",
            ),
            row=1, col=1,
        )

    # Bi stroke lines
    bi_segs = get_bi_segments(df)
    for seg in bi_segs:
        fig.add_trace(
            go.Scatter(
                x=[plot_df[date_col].iloc[seg["start_idx"]],
                   plot_df[date_col].iloc[seg["end_idx"]]],
                y=[seg["start_val"], seg["end_val"]],
                mode="lines",
                line=dict(color=theme.BI_COLOR, width=1.5, dash="dot"),
                name="笔 (Bi)",
                showlegend=False,
                hovertemplate="笔 (%{direction})<extra></extra>",
            ),
            row=1, col=1,
        )

    # Zhongshu zones
    zhongshu_zones = get_zhongshu_list(df)
    if zhongshu_zones:
        for zs in zhongshu_zones:
            fig.add_trace(
                go.Scatter(
                    x=[
                        plot_df[date_col].iloc[zs["start_idx"]],
                        plot_df[date_col].iloc[zs["end_idx"]],
                    ],
                    y=[zs["zg"], zs["zg"]],
                    mode="lines",
                    line=dict(color=theme.ZS_LINE, width=1, dash="dash"),
                    name=f"中枢#{zs['period']} ZG",
                    showlegend=False,
                ),
                row=1, col=1,
            )
            fig.add_trace(
                go.Scatter(
                    x=[
                        plot_df[date_col].iloc[zs["start_idx"]],
                        plot_df[date_col].iloc[zs["end_idx"]],
                    ],
                    y=[zs["zd"], zs["zd"]],
                    mode="lines",
                    line=dict(color=theme.ZS_LINE, width=1, dash="dash"),
                    name=f"中枢#{zs['period']} ZD",
                    showlegend=False,
                ),
                row=1, col=1,
            )
            # Fill zone
            fig.add_trace(
                go.Scatter(
                    x=[
                        plot_df[date_col].iloc[zs["start_idx"]],
                        plot_df[date_col].iloc[zs["end_idx"]],
                        plot_df[date_col].iloc[zs["end_idx"]],
                        plot_df[date_col].iloc[zs["start_idx"]],
                    ],
                    y=[zs["zg"], zs["zg"], zs["zd"], zs["zd"]],
                    fill="toself",
                    fillcolor=theme.ZS_FILL,
                    line=dict(width=0),
                    name=f"中枢{zs['period']}",
                    showlegend=True,
                    hoverinfo="skip",
                ),
                row=1, col=1,
            )

    # Buy/Sell points
    buy_sell = get_buy_sell_summary(df)
    for bs in buy_sell:
        color = {
            "B1-一类买点": theme.B1_COLOR, "B2-二类买点": theme.B2_COLOR,
            "B3-三类买点": theme.B3_COLOR, "S1-一类卖点": theme.S1_COLOR,
            "S2-二类卖点": theme.S2_COLOR, "S3-三类卖点": theme.S3_COLOR,
        }.get(bs["type"], "#fff")

        symbol_type = "triangle-up" if bs["direction"] == "buy" else "triangle-down"
        y_pos = df.loc[bs["date"] if bs["date"] in df.index else df.index[0], "low"] * 0.98 \
            if bs["direction"] == "buy" else df.loc[bs["date"] if bs["date"] in df.index else df.index[0], "high"] * 1.02

        # Actually use close price for marker position
        y_pos = bs["price"] * (0.97 if bs["direction"] == "buy" else 1.03)

        fig.add_trace(
            go.Scatter(
                x=[bs["date"]],
                y=[y_pos],
                mode="markers+text",
                marker=dict(
                    symbol=symbol_type,
                    size=theme.BUY_SELL_SIZE,
                    color=color,
                    line=dict(width=1, color="#fff"),
                ),
                text=bs["type"][:2],
                textposition="bottom center" if bs["direction"] == "buy" else "top center",
                textfont=dict(size=10, color=color),
                name=bs["type"],
                showlegend=True,
                hovertemplate=f"{bs['type']}<br>%{{x}}<br>¥{bs['price']}<extra></extra>",
            ),
            row=1, col=1,
        )

    # ── Row 2: MACD ─────────────────────────────────────────────────
    if "DIF" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=plot_df[date_col], y=df["DIF"],
                mode="lines", name="DIF",
                line=dict(color=theme.DIF_COLOR, width=1),
            ),
            row=2, col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=plot_df[date_col], y=df["DEA"],
                mode="lines", name="DEA",
                line=dict(color=theme.DEA_COLOR, width=1),
            ),
            row=2, col=1,
        )

        # MACD bars
        macd_vals = df["MACD_bar"].values
        colors = [theme.MACD_BULL if v >= 0 else theme.MACD_BEAR for v in macd_vals]

        fig.add_trace(
            go.Bar(
                x=plot_df[date_col], y=df["MACD_bar"],
                name="MACD",
                marker=dict(color=colors),
                opacity=0.7,
            ),
            row=2, col=1,
        )

        # Divergence highlights
        top_div = df[df["top_divergence"]]
        bottom_div = df[df["bottom_divergence"]]

        if len(top_div) > 0:
            fig.add_trace(
                go.Scatter(
                    x=top_div.index, y=[top_div["high"].max() * 1.02] * len(top_div),
                    mode="markers",
                    marker=dict(symbol="circle", size=8, color=theme.S1_COLOR, opacity=0.6),
                    name="顶背驰",
                    hovertemplate="顶背驰<extra></extra>",
                ),
                row=1, col=1,
            )

        if len(bottom_div) > 0:
            fig.add_trace(
                go.Scatter(
                    x=bottom_div.index, y=[bottom_div["low"].min() * 0.98] * len(bottom_div),
                    mode="markers",
                    marker=dict(symbol="circle", size=8, color=theme.B1_COLOR, opacity=0.6),
                    name="底背驰",
                    hovertemplate="底背驰<extra></extra>",
                ),
                row=1, col=1,
            )

    # ── Layout ────────────────────────────────────────────────────────
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=theme.BG_COLOR,
        plot_bgcolor=theme.PLOT_BG,
        font=dict(color=theme.TEXT_COLOR),
        xaxis_rangeslider_visible=False,
        height=theme.CHART_HEIGHT + theme.MACD_HEIGHT,
        margin=theme.MARGIN,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=1.12,
            xanchor="left",
            x=0,
            font=dict(size=10),
        ),
        hovermode="x unified",
    )

    fig.update_xaxes(
        showgrid=True, gridcolor=theme.GRID_COLOR,
        zeroline=False, row=1, col=1,
    )
    fig.update_xaxes(
        showgrid=True, gridcolor=theme.GRID_COLOR,
        zeroline=False, row=2, col=1,
    )
    fig.update_yaxes(
        title_text="价格", showgrid=True,
        gridcolor=theme.GRID_COLOR, row=1, col=1,
    )
    fig.update_yaxes(
        title_text="MACD", showgrid=True,
        gridcolor=theme.GRID_COLOR, row=2, col=1,
    )

    return fig
