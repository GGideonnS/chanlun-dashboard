"""
UI 组件库 — 缠论看板通用组件

包含：
1. 侧边栏组件
2. 信号汇总卡片
3. 快捷操作面板
4. 状态指示器
5. 导出功能
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime


def render_sidebar(meta: dict, df: pd.DataFrame):
    """渲染侧边栏 — 快捷操作 + 设置"""
    with st.sidebar:
        st.markdown("## ⚙️ 控制面板")

        # 股票信息
        if meta:
            st.markdown(f"**{meta.get('display', '')}** {meta.get('name', '')}")
            st.caption(f"{meta.get('level_label', '')} | {meta.get('bars', 0)} 根K线")
            st.caption(f"最新价: ${meta.get('latest_price', 0):.2f}")

        st.markdown("---")

        # 图表设置
        st.markdown("### 📊 图表设置")
        show_ma = st.checkbox("显示均线", value=True, key="show_ma")
        show_bi = st.checkbox("显示笔", value=True, key="show_bi")
        show_zs = st.checkbox("显示中枢", value=True, key="show_zs")
        show_signals = st.checkbox("显示买卖点", value=True, key="show_signals")

        st.markdown("---")

        # 快捷股票
        st.markdown("### 🔥 热门股票")
        hot_stocks = {
            "US": ["AAPL", "NVDA", "MSFT", "TSLA", "AMD"],
            "HK": ["0700.HK", "9988.HK", "1810.HK"],
            "CN": ["600519.SS", "300750.SZ", "000858.SZ"],
        }
        market = meta.get("market", "US") if meta else "US"
        for code in hot_stocks.get(market, []):
            if st.button(code, key=f"side_{code}", use_container_width=True):
                st.session_state.symbol = code
                st.rerun()

        st.markdown("---")

        # 导出
        st.markdown("### 📥 导出")
        if df is not None:
            csv = df.to_csv()
            st.download_button(
                "下载 CSV",
                csv,
                file_name=f"chanlun_{meta.get('display', 'data')}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True,
            )

    return show_ma, show_bi, show_zs, show_signals


def render_signal_summary(df: pd.DataFrame):
    """渲染信号汇总卡片"""
    from engine import get_bi_segments, get_zhongshu_list, get_buy_sell_summary

    bi_segs = get_bi_segments(df)
    zhongshu_list = get_zhongshu_list(df)
    buy_sell = get_buy_sell_summary(df)

    # 买入/卖出信号统计
    buy_count = len([s for s in buy_sell if s["direction"] == "buy"])
    sell_count = len([s for s in buy_sell if s["direction"] == "sell"])

    # 最近信号
    recent_buy = [s for s in buy_sell if s["direction"] == "buy"][-1] if buy_count > 0 else None
    recent_sell = [s for s in buy_sell if s["direction"] == "sell"][-1] if sell_count > 0 else None

    # 中枢位置
    zs = zhongshu_list[-1] if zhongshu_list else None
    current = float(df["close"].iloc[-1])
    zs_position = "—"
    zs_color = "normal"
    if zs:
        if current > zs["zg"]:
            zs_position = "上方"
            zs_color = "inverse"
        elif current < zs["zd"]:
            zs_position = "下方"
            zs_color = "inverse"
        else:
            zs_position = "震荡中"
            zs_color = "normal"

    # 渲染卡片
    cols = st.columns(5)

    with cols[0]:
        if bi_segs:
            last_dir = "↑" if bi_segs[-1]["direction"] == "up" else "↓"
            delta = f"最新: {last_dir}"
        else:
            delta = None
        st.metric("笔 (Bi)", len(bi_segs), delta=delta)

    with cols[1]:
        st.metric(
            "中枢 (ZS)",
            len(zhongshu_list),
            delta=f"位置: {zs_position}" if zs else None,
            delta_color=zs_color,
        )

    with cols[2]:
        st.metric(
            "买点",
            buy_count,
            delta=recent_buy["type"][:2] if recent_buy else None,
            delta_color="normal",
        )

    with cols[3]:
        st.metric(
            "卖点",
            sell_count,
            delta=recent_sell["type"][:2] if recent_sell else None,
            delta_color="off",
        )

    with cols[4]:
        # 趋势判断
        from engine.ma_system import get_trend_type, get_kiss_summary
        trend = get_trend_type(df)
        kiss = get_kiss_summary(df)
        position = "女上位" if kiss["in_female_position"] else "男上位"

        st.metric(
            "走势",
            trend,
            delta=position,
            delta_color="normal" if kiss["in_female_position"] else "off",
        )


def render_quick_actions(symbol: str, meta: dict):
    """渲染快捷操作面板"""
    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        if st.button("📊 分时图", use_container_width=True):
            st.session_state.level = "5min"
            st.session_state.symbol = symbol
            st.rerun()

    with c2:
        if st.button("📈 日K线", use_container_width=True):
            st.session_state.level = "daily"
            st.session_state.symbol = symbol
            st.rerun()

    with c3:
        if st.button("📉 周K线", use_container_width=True):
            st.session_state.level = "weekly"
            st.session_state.symbol = symbol
            st.rerun()

    with c4:
        if st.button("🔄 刷新数据", use_container_width=True):
            st.cache_data.clear()
            st.rerun()


def render_loading_state(message: str = "加载中..."):
    """渲染加载状态"""
    with st.spinner(message):
        st.empty()


def render_error_state(error: str):
    """渲染错误状态"""
    st.error(f"❌ {error}")
    st.info("💡 提示: 请检查股票代码是否正确，或稍后重试")


def render_empty_state():
    """渲染空状态 — 引导用户"""
    st.markdown("---")

    # 标题
    st.markdown("""
    <div style='text-align: center; padding: 2rem;'>
        <h1 style='color: #FFD54F;'>📊 缠论看板</h1>
        <p style='color: #C9D1D9; font-size: 1.2rem;'>
            基于缠中说禅《教你炒股票》理论<br>
            自动识别分型、笔、线段、中枢、背驰、买卖点
        </p>
    </div>
    """, unsafe_allow_html=True)

    # 快捷入口
    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("### 🇺🇸 美股")
        for code, name in [
            ("AAPL", "Apple"), ("NVDA", "NVIDIA"), ("MSFT", "Microsoft"),
            ("TSLA", "Tesla"), ("AMD", "AMD"),
        ]:
            if st.button(f"{code} — {name}", key=f"us_{code}", use_container_width=True):
                st.session_state.symbol = code
                st.session_state.market = "US"
                st.rerun()

    with c2:
        st.markdown("### 🇭🇰 港股")
        for code, name in [
            ("0700.HK", "腾讯"), ("9988.HK", "阿里巴巴"),
            ("1810.HK", "小米"), ("3690.HK", "美团"),
        ]:
            if st.button(f"{code} — {name}", key=f"hk_{code}", use_container_width=True):
                st.session_state.symbol = code
                st.session_state.market = "HK"
                st.rerun()

    with c3:
        st.markdown("### 🇨🇳 A股")
        for code, name in [
            ("600519.SS", "茅台"), ("300750.SZ", "宁德时代"),
            ("000858.SZ", "五粮液"), ("601318.SS", "中国平安"),
        ]:
            if st.button(f"{code} — {name}", key=f"cn_{code}", use_container_width=True):
                st.session_state.symbol = code
                st.session_state.market = "CN"
                st.rerun()

    st.markdown("---")
    st.info(
        "💡 **缠论看板** — 基于缠中说禅《教你炒股票》理论\n\n"
        "**功能**：分型 → 笔 → 线段 → 中枢 → 背驰 → 买卖点\n\n"
        "**支持**：美股/港股/A股 | 日线/30分/60分/周线/月线\n\n"
        "输入代码或点击上方示例开始分析"
    )
