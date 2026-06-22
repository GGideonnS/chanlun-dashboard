"""Chan Theory (缠论) computation engine."""

from .fractals import find_fractals
from .bi import build_bi, get_bi_segments
from .xian_duan import build_xian_duan
from .zhongshu import find_zhongshu, get_zhongshu_list
from .divergence import detect_divergence, compute_macd
from .buy_sell_points import find_buy_sell_points, get_buy_sell_summary
from .multi_level import compute_resonance

__all__ = [
    "find_fractals",
    "build_bi",
    "get_bi_segments",
    "build_xian_duan",
    "find_zhongshu",
    "get_zhongshu_list",
    "detect_divergence",
    "compute_macd",
    "find_buy_sell_points",
    "get_buy_sell_summary",
    "compute_resonance",
]
