"""Full pipeline test"""
from data import fetch_stock_data
from engine import *
from engine.zhongshu import get_zhongshu_list
from engine.bi import get_bi_segments
from engine.buy_sell_points import find_buy_sell_points, get_buy_sell_summary
from engine.ma_system import get_kiss_summary, get_trend_type

df_raw, meta = fetch_stock_data('AAPL', period='daily')
df = compute_ma(df_raw)
df = find_fractals(df, use_containment=True)
df = build_bi(df)
df = build_xian_duan(df)
df = find_zhongshu(df)
df = detect_divergence(df)
df = find_buy_sell_points(df)

zs = get_zhongshu_list(df)
bi = get_bi_segments(df)
signals = get_buy_sell_summary(df)
kiss = get_kiss_summary(df)
trend = get_trend_type(df)

print(f"K线: {len(df)}根")
print(f"笔: {len(bi)}条")
print(f"中枢: {len(zs)}个")
for z in zs:
    print(f"  ZG={z['zg']:.2f}, ZD={z['zd']:.2f}")
print(f"买卖点: {len(signals)}个")
print(f"均线: 男上位={kiss['in_male_position']}, 女上位={kiss['in_female_position']}")
print(f"最近吻: {kiss['last_kiss']}")
print(f"走势: {trend}")
print("OK")
