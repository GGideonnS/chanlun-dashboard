"""Test chanlun pipeline"""
from data import fetch_stock_data
from engine import *
from engine.bi import get_bi_segments
from engine.zhongshu import get_zhongshu_list
from engine.buy_sell_points import find_buy_sell_points, get_buy_sell_summary

df_raw, meta = fetch_stock_data('AAPL', period='daily')
print(f"Data: {meta['bars']} bars, {meta['start']} to {meta['end']}")

df = find_fractals(df_raw, use_containment=True)
print(f"Fractals: top={int(df['top_fractal'].sum())}, bottom={int(df['bottom_fractal'].sum())}")

df = build_bi(df)
bi = get_bi_segments(df)
print(f"Bi: {len(bi)} segments")

df = build_xian_duan(df)
df = find_zhongshu(df)
zs = get_zhongshu_list(df)
print(f"Zhongshu: {len(zs)} zones")
for z in zs:
    print(f"  ZG={z['zg']:.2f}, ZD={z['zd']:.2f}, segments={z.get('segment_count',0)}")

df = detect_divergence(df)
df = find_buy_sell_points(df)
signals = get_buy_sell_summary(df)
print(f"Signals: {len(signals)}")
for s in signals[-5:]:
    print(f"  {s['date']}: {s['type']} @ {s['price']}")
print("OK")
