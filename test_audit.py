"""Audit test - check for type issues in all engine outputs"""
import pandas as pd
from data import fetch_stock_data
from engine import *

df_raw, meta = fetch_stock_data('AAPL', period='daily')

# Run full pipeline
df = compute_ma(df_raw)
df = find_fractals(df, use_containment=True)
df = build_bi(df)
df = build_xian_duan(df)
df = find_zhongshu(df)
df = detect_divergence(df)
df = find_buy_sell_points(df)

# Check all string columns
from engine.bi import get_bi_segments
from engine.buy_sell_points import get_buy_sell_summary
from engine.zhongshu import get_zhongshu_list

bi = get_bi_segments(df)
signals = get_buy_sell_summary(df)
zs = get_zhongshu_list(df)

errors = []

# Check bi direction
for i, b in enumerate(bi):
    d = b["direction"]
    if d not in ("up", "down"):
        errors.append(f"bi[{i}] direction={d!r} (expected 'up' or 'down')")
    sv = b["start_val"]
    ev = b["end_val"]
    if not isinstance(sv, (int, float)):
        errors.append(f"bi[{i}] start_val={sv!r} (expected number)")
    if not isinstance(ev, (int, float)):
        errors.append(f"bi[{i}] end_val={ev!r} (expected number)")

# Check signals direction
for i, s in enumerate(signals):
    d = s["direction"]
    if d not in ("buy", "sell"):
        errors.append(f"signal[{i}] direction={d!r}")
    t = s["type"]
    if not isinstance(t, str) or len(t) < 2:
        errors.append(f"signal[{i}] type={t!r}")
    p = s["price"]
    if not isinstance(p, (int, float)):
        errors.append(f"signal[{i}] price={p!r}")

# Check zhongshu zg/zd
for i, z in enumerate(zs):
    zg = z.get("zg")
    zd = z.get("zd")
    if not isinstance(zg, (int, float)) or zg <= 0:
        errors.append(f"zs[{i}] zg={zg!r}")
    if not isinstance(zd, (int, float)) or zd <= 0:
        errors.append(f"zs[{i}] zd={zd!r}")

# Check DataFrame string columns
for col in ["bi_direction", "signal", "kiss_type"]:
    if col in df.columns:
        sample = df[col].dropna().head(5)
        for idx, val in sample.items():
            if not isinstance(val, str):
                errors.append(f"df[{col}] at {idx} = {val!r} (expected str)")

# Check DataFrame bool columns
for col in df.columns:
    if df[col].dtype == bool or col.startswith(("top_", "bottom_", "bi_", "buy_", "sell_", "xd_", "zs_")):
        if df[col].dtype != bool:
            try:
                df[col] = df[col].fillna(False).astype(bool)
            except:
                errors.append(f"df[{col}] dtype={df[col].dtype} cannot convert to bool")

if errors:
    print("ERRORS FOUND:")
    for e in errors:
        print(f"  - {e}")
else:
    print("ALL CHECKS PASSED")

print(f"\nSummary:")
print(f"  Bi segments: {len(bi)}")
print(f"  Signals: {len(signals)}")
print(f"  Zhongshu: {len(zs)}")
