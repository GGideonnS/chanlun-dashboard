#!/usr/bin/env python3
"""
Chan Theory (缠论) Dashboard — Interactive K-line chart with chanlun analysis.

Usage:
    streamlit run app.py
    # or double-click chanlun.exe (PyInstaller build)
"""

import streamlit as st
import pandas as pd

from data import fetch_stock_data
from engine import (
    find_fractals,
    build_bi,
    build_xian_duan,
    find_zhongshu,
    detect_divergence,
    get_zhongshu_list,
    get_bi_segments,
    get_buy_sell_summary,
)
from viz.chart import build_chanlun_chart
from ui.interpretation import generate_interpretation
from utils.symbol_resolver import search_suggestions, MARKET_LABELS
from utils.cache import get_cached, set_cache

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="缠论看板｜ChanLun Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    .main .block-container { padding-top: 1rem; }
    .stButton button { width: 100%; }
</style>
""", unsafe_allow_html=True)

# ── Initialize session state ─────────────────────────────────────────────────
for key, default in {
    "df": None, "meta": None, "analyzed": False,
    "level": "daily", "symbol": "", "market": "US",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ── Header ───────────────────────────────────────────────────────────────────
col_title, col_search = st.columns([3, 5])

with col_title:
    st.markdown("# 📊 缠论看板")

with col_search:
    with st.form("search_form", border=False):
        c1, c2, c3, c4 = st.columns([3, 1.5, 1, 1])

        with c1:
            symbol_input = st.text_input(
                "股票代码",
                value=st.session_state.symbol,
                placeholder="输入代码: AAPL / 9988.HK / 600519",
                label_visibility="collapsed",
            ).strip()

        with c2:
            market = st.selectbox(
                "市场",
                options=["US", "HK", "CN"],
                format_func=lambda x: MARKET_LABELS[x],
                label_visibility="collapsed",
            )

        with c3:
            level = st.selectbox(
                "级别",
                options=["daily", "30min", "60min", "weekly", "monthly"],
                format_func=lambda x: {
                    "daily": "日线", "30min": "30分钟",
                    "60min": "60分钟", "weekly": "周线", "monthly": "月线",
                }[x],
                label_visibility="collapsed",
            )

        with c4:
            submitted = st.form_submit_button("🔍 分析", use_container_width=True)

# ── Suggestions ─────────────────────────────────────────────────────────────
if symbol_input:
    suggestions = search_suggestions(symbol_input, market)
    if suggestions and not submitted:
        with st.expander(f"💡 匹配结果 ({len(suggestions)})", expanded=len(suggestions) <= 3):
            cols = st.columns(min(len(suggestions), 4))
            for i, (code, name, mkt) in enumerate(suggestions):
                with cols[i % 4]:
                    st.caption(f"{MARKET_LABELS.get(mkt, mkt)}")
                    st.markdown(f"**{code}**")
                    st.caption(name)


# ── Main pipeline ────────────────────────────────────────────────────────────
if submitted and symbol_input:
    symbol = symbol_input.strip()
    st.session_state.symbol = symbol
    st.session_state.market = market
    st.session_state.level = level

    with st.spinner(f"正在获取 {symbol} {level} 数据..."):
        try:
            # Try cache first
            df = get_cached(symbol, level)
            meta = None

            if df is None:
                df, meta = fetch_stock_data(symbol, period=level)
                set_cache(symbol, level, df)
            else:
                from data.fetcher import resolve_symbol
                sym, mkt, disp = resolve_symbol(symbol)
                from data.fetcher import LEVEL_LABELS
                meta = {
                    "symbol": sym, "display": disp, "name": disp,
                    "market": mkt, "period": level,
                    "level_label": LEVEL_LABELS.get(level, level),
                    "bars": len(df), "latest_price": float(df["close"].iloc[-1]),
                }

            st.session_state.meta = meta

            with st.spinner("缠论分析中: 分型→笔→线段→中枢→背驰→买卖点..."):
                df = find_fractals(df)
                df = build_bi(df)
                df = build_xian_duan(df)
                df = find_zhongshu(df)
                df = detect_divergence(df)

                from engine.buy_sell_points import find_buy_sell_points
                df = find_buy_sell_points(df)

            # Clean all boolean columns — fill NaN with False
            bool_cols = [c for c in df.columns if c.startswith((
                "top_fractal", "bottom_fractal", "bi_", "xd_",
                "zs_", "buy_", "sell_", "top_div", "bottom_div",
            ))]
            for col in bool_cols:
                df[col] = df[col].fillna(False).astype(bool)

            st.session_state.df = df
            st.session_state.analyzed = True

        except Exception as e:
            st.error(f"❌ 数据获取失败: {e}")
            st.session_state.analyzed = False


# ── Display chart and analysis ───────────────────────────────────────────────
if st.session_state.analyzed and st.session_state.df is not None:
    df = st.session_state.df
    meta = st.session_state.meta or {}

    # ━ Price summary bar ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    latest = df["close"].iloc[-1]
    prev = df["close"].iloc[-2] if len(df) > 1 else latest
    change = latest - prev
    change_pct = (change / prev * 100) if prev else 0

    cols = st.columns([2, 1, 1, 1, 1, 1])
    with cols[0]:
        st.markdown(f"### {meta.get('display', '—')}   ${latest:.2f}")
    with cols[1]:
        color = "green" if change >= 0 else "red"
        st.markdown(f"**:{color}[{change:+.2f} ({change_pct:+.2f}%)]**")
    with cols[2]:
        st.markdown(f"**最高**: {df['high'].iloc[-1]:.2f}")
    with cols[3]:
        st.markdown(f"**最低**: {df['low'].iloc[-1]:.2f}")
    with cols[4]:
        st.markdown(f"**量**: {df['volume'].iloc[-1]:,.0f}")
    with cols[5]:
        st.caption(f"{meta.get('level_label', '')} | {meta.get('bars', 0)} 根K线")

    # ━ Chart ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    st.markdown("---")
    fig = build_chanlun_chart(df, meta)
    st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True})

    # ━ Chan Theory Stats ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    bi_segs = get_bi_segments(df)
    zhongshu_list = get_zhongshu_list(df)
    buy_sell = get_buy_sell_summary(df)
    has_div = df["top_divergence"].any() or df["bottom_divergence"].any()

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("笔 (Bi)", len(bi_segs))
    with c2:
        st.metric("中枢 (ZS)", len(zhongshu_list))
    with c3:
        st.metric("买卖点", len(buy_sell))
    with c4:
        st.metric("顶分型", int(df["top_fractal"].sum()))
    with c5:
        st.metric("底分型", int(df["bottom_fractal"].sum()))

    # ━ Interpretation ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    st.markdown("---")
    text = generate_interpretation(df, meta)
    st.markdown(text)

    # ━ Raw data toggle ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    with st.expander("📋 查看原始数据"):
        st.dataframe(df.tail(30), use_container_width=True)

else:
    # ── Landing state ─────────────────────────────────────────────────────
    st.markdown("---")
    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("### 🇺🇸 美股示例")
        for code, name in [
            ("AAPL", "Apple"), ("NVDA", "NVIDIA"), ("MSFT", "Microsoft"),
            ("AMD", "AMD"), ("SMCI", "Super Micro"),
        ]:
            if st.button(f"{code} — {name}", key=f"us_{code}"):
                st.session_state.symbol = code
                st.rerun()

    with c2:
        st.markdown("### 🇭🇰 港股示例")
        for code, name in [
            ("0700.HK", "腾讯"), ("9988.HK", "阿里巴巴"),
            ("3690.HK", "美团"), ("1810.HK", "小米"),
        ]:
            if st.button(f"{code} — {name}", key=f"hk_{code}"):
                st.session_state.symbol = code
                st.rerun()

    with c3:
        st.markdown("### 🇨🇳 A股示例")
        for code, name in [
            ("600519.SS", "茅台"), ("300750.SZ", "宁德时代"),
            ("000858.SZ", "五粮液"), ("601318.SS", "中国平安"),
        ]:
            if st.button(f"{code} — {name}", key=f"cn_{code}"):
                st.session_state.symbol = code
                st.rerun()

    st.info(
        "💡 **缠论看板**基于缠中说禅《教你炒股票》理论，自动识别**分型、笔、线段、中枢、背驰、买卖点**。"
        "输入代码或点击上方示例开始分析。支持美股、港股、A股，多级别切换。"
    )
