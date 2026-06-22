"""Stock code auto-completion and suggestions."""

SUGGESTIONS = {
    "US": [
        ("AAPL", "Apple Inc."),
        ("MSFT", "Microsoft Corp."),
        ("GOOGL", "Alphabet Inc."),
        ("AMZN", "Amazon.com Inc."),
        ("META", "Meta Platforms Inc."),
        ("NVDA", "NVIDIA Corp."),
        ("TSLA", "Tesla Inc."),
        ("AMD", "Advanced Micro Devices"),
        ("INTC", "Intel Corp."),
        ("AVGO", "Broadcom Inc."),
        ("SMCI", "Super Micro Computer"),
        ("MU", "Micron Technology"),
        ("TSM", "TSMC (ADR)"),
        ("ASML", "ASML Holding"),
        ("BABA", "Alibaba Group"),
        ("JD", "JD.com"),
        ("NIO", "NIO Inc."),
        ("PLTR", "Palantir Technologies"),
        ("SNOW", "Snowflake Inc."),
        ("CRM", "Salesforce Inc."),
        ("ORCL", "Oracle Corp."),
        ("ANET", "Arista Networks"),
        ("DELL", "Dell Technologies"),
        ("HPE", "Hewlett Packard Enterprise"),
        ("MRVL", "Marvell Technology"),
        ("QCOM", "Qualcomm Inc."),
    ],
    "HK": [
        ("0700.HK", "腾讯控股"),
        ("9988.HK", "阿里巴巴-SW"),
        ("0941.HK", "中国移动"),
        ("2318.HK", "中国平安"),
        ("3690.HK", "美团-W"),
        ("9618.HK", "京东集团-SW"),
        ("9999.HK", "网易-S"),
        ("1810.HK", "小米集团-W"),
        ("1024.HK", "快手-W"),
        ("2015.HK", "理想汽车-W"),
        ("9866.HK", "蔚来-SW"),
        ("2269.HK", "药明生物"),
        ("1211.HK", "比亚迪股份"),
        ("0005.HK", "汇丰控股"),
    ],
    "CN": [
        ("600519.SS", "贵州茅台"),
        ("000858.SZ", "五粮液"),
        ("601318.SS", "中国平安"),
        ("000333.SZ", "美的集团"),
        ("002415.SZ", "海康威视"),
        ("300750.SZ", "宁德时代"),
        ("603288.SS", "海天味业"),
        ("000651.SZ", "格力电器"),
        ("002594.SZ", "比亚迪"),
        ("601012.SS", "隆基绿能"),
        ("300059.SZ", "东方财富"),
        ("688981.SS", "中芯国际"),
        ("601857.SS", "中国石油"),
        ("000725.SZ", "京东方A"),
    ],
}

MARKET_LABELS = {"US": "🇺🇸 美股", "HK": "🇭🇰 港股", "CN": "🇨🇳 A股"}


def search_suggestions(query: str, market: str | None = None) -> list[tuple[str, str, str]]:
    """Search for matching stocks. Returns [(code, name, market), ...]."""
    query = query.upper().strip()
    results = []

    for mkt in ("US", "HK", "CN"):
        if market and mkt != market:
            continue
        for code, name in SUGGESTIONS[mkt]:
            if query in code.upper() or query.lower() in name.lower():
                results.append((code, name, mkt))
    return results[:10]
