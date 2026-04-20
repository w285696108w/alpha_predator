# -*- coding: utf-8 -*-
"""
Alpha信号生成模块 - 纯Python实现
"""
from __future__ import annotations

from typing import Dict, List, Optional
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import (
    mean, std, rolling_mean, rolling_std, rolling_max, rolling_min,
    pct_change, zscore, ewm_mean, typical_price, vwap as _vwap,
    rsi as _rsi, atr as _atr, macd as _macd, bollinger_bands as _bb,
    rank, percentile
)


class AlphaSignalGenerator:
    """
    综合Alpha信号生成器 - 纯Python版
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

    def compute_all(self, ohlcv: Dict[str, List[float]]) -> Dict[str, List[float]]:
        """
        计算所有Alpha信号
        """
        close = ohlcv["close"]
        high = ohlcv["high"]
        low = ohlcv["low"]
        volume = ohlcv["volume"]
        n = len(close)

        # RSI
        rsi_vals = _rsi(close, 14)

        # MACD
        macd_line, signal_line, histogram = _macd(close)

        # 布林带
        bb_upper, bb_middle, bb_lower = _bb(close)

        # 动量
        mom_5 = pct_change(close, 5)
        mom_10 = pct_change(close, 10)
        mom_20 = pct_change(close, 20)

        mom_rank_5 = rank(mom_5)
        mom_rank_10 = rank(mom_10)
        mom_rank_20 = rank(mom_20)

        # ATR（用于止损）
        atr_vals = _atr(high, low, close)

        # 订单流（简化版）
        ret = pct_change(close)
        vol_change = pct_change(volume)
        order_flow = [0.0] * n
        for i in range(1, n):
            vol_ch = max(vol_change[i], 0) + 1
            if ret[i] > 0:
                order_flow[i] = order_flow[i - 1] + volume[i] * vol_ch
            else:
                order_flow[i] = order_flow[i - 1] - volume[i] * vol_ch

        # 信号生成
        sig_rsi = [0.0] * n
        for i in range(n):
            if rsi_vals[i] < 30:
                sig_rsi[i] = 1.0
            elif rsi_vals[i] > 70:
                sig_rsi[i] = -1.0

        sig_macd = [0.0] * n
        for i in range(n):
            sig_macd[i] = 1.0 if macd_line[i] > signal_line[i] else -1.0

        sig_bb = [0.0] * n
        for i in range(n):
            if close[i] < bb_lower[i]:
                sig_bb[i] = 1.0
            elif close[i] > bb_upper[i]:
                sig_bb[i] = -1.0

        sig_mom = [0.0] * n
        for i in range(n):
            if mom_rank_10[i] > 0.7:
                sig_mom[i] = 1.0
            elif mom_rank_10[i] < 0.3:
                sig_mom[i] = -1.0

        # 背离检测
        divergence = [0.0] * n
        lookback = 20
        for i in range(lookback, n):
            price_slice = close[i - lookback:i + 1]
            rsi_slice = rsi_vals[i - lookback:i + 1]

            price_at_high = close[i] >= max(price_slice)
            price_at_low = close[i] <= min(price_slice)
            rsi_at_high = rsi_vals[i] >= max(rsi_slice)
            rsi_at_low = rsi_vals[i] <= min(rsi_slice)

            if price_at_low and not rsi_at_low:
                divergence[i] = 1.0  # 底背离 → 买入
            elif price_at_high and not rsi_at_high:
                divergence[i] = -1.0  # 顶背离 → 卖出

        # 综合Alpha分数
        alpha_score = [0.0] * n
        for i in range(n):
            alpha_score[i] = (
                sig_rsi[i] * 0.15 +
                sig_macd[i] * 0.20 +
                sig_bb[i] * 0.20 +
                sig_mom[i] * 0.15 +
                divergence[i] * 0.30
            )
            alpha_score[i] = max(-1.0, min(1.0, alpha_score[i]))

        return {
            "close": close,
            "high": high,
            "low": low,
            "open": ohlcv.get("open", close),
            "volume": volume,
            "rsi": rsi_vals,
            "macd": macd_line,
            "macd_signal": signal_line,
            "macd_hist": histogram,
            "bb_upper": bb_upper,
            "bb_middle": bb_middle,
            "bb_lower": bb_lower,
            "momentum_5": mom_5,
            "momentum_10": mom_10,
            "momentum_20": mom_20,
            "momentum_rank_5": mom_rank_5,
            "momentum_rank_10": mom_rank_10,
            "momentum_rank_20": mom_rank_20,
            "order_flow": order_flow,
            "divergence": divergence,
            "atr": atr_vals,
            "signal_rsi": sig_rsi,
            "signal_macd": sig_macd,
            "signal_bb": sig_bb,
            "signal_momentum": sig_mom,
            "alpha_scores": alpha_score,
        }

    def rank_signals(self, scores: Dict[str, float]) -> List[tuple]:
        """对多只股票信号排序"""
        sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_items
