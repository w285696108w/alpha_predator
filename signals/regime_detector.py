# -*- coding: utf-8 -*-
"""
市场状态检测模块 - 纯Python实现
"""
from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import mean, rolling_mean, rolling_std, pct_change
from enum import Enum


class MarketRegime(Enum):
    TREND_UP = "trend_up"
    TREND_DOWN = "trend_down"
    RANGE_BOUND = "range_bound"
    HIGH_VOL = "high_vol"
    LOW_VOL = "low_vol"
    UNKNOWN = "unknown"


class RegimeDetector:
    """市场状态检测器"""

    def __init__(
        self,
        fast_ma: int = 5,
        slow_ma: int = 20,
        vol_window: int = 20,
        vol_high_threshold: float = 1.5,
        vol_low_threshold: float = 0.5,
    ):
        self.fast_ma = fast_ma
        self.slow_ma = slow_ma
        self.vol_window = vol_window
        self.vol_high_threshold = vol_high_threshold
        self.vol_low_threshold = vol_low_threshold

    def detect(self, close: list) -> list:
        """
        检测市场状态序列
        Returns: list of MarketRegime
        """
        n = len(close)
        if n < self.slow_ma + 2:
            return [MarketRegime.UNKNOWN] * n

        ma_fast = rolling_mean(close, self.fast_ma)
        ma_slow = rolling_mean(close, self.slow_ma)

        returns = pct_change(close)
        vol = rolling_std(returns, self.vol_window)
        vol_ma_long = rolling_mean(vol, self.vol_window)
        vol_ratio = [v / (vol_ma_long[i] if vol_ma_long[i] > 0 else 1.0)
                     for i, v in enumerate(vol)]

        regimes = []
        for i in range(n):
            hv = vol_ratio[i] > self.vol_high_threshold
            lv = vol_ratio[i] < self.vol_low_threshold
            up = ma_fast[i] > ma_slow[i]
            down = ma_fast[i] < ma_slow[i]

            if hv:
                regimes.append(MarketRegime.HIGH_VOL)
            elif lv:
                regimes.append(MarketRegime.LOW_VOL)
            elif up:
                regimes.append(MarketRegime.TREND_UP)
            elif down:
                regimes.append(MarketRegime.TREND_DOWN)
            else:
                regimes.append(MarketRegime.RANGE_BOUND)

        return regimes

    def detect_current(self, close: list) -> MarketRegime:
        """检测当前市场状态"""
        regimes = self.detect(close)
        return regimes[-1] if regimes else MarketRegime.UNKNOWN

    def get_strategy_params(self, regime: MarketRegime) -> dict:
        """根据市场状态返回策略参数"""
        params = {
            MarketRegime.TREND_UP: {
                "strategy": "momentum",
                "stop_loss": 0.05,
                "take_profit": 0.15,
                "position_size": 0.8,
            },
            MarketRegime.TREND_DOWN: {
                "strategy": "cash",
                "stop_loss": 0.03,
                "take_profit": 0.10,
                "position_size": 0.3,
            },
            MarketRegime.RANGE_BOUND: {
                "strategy": "mean_reversion",
                "stop_loss": 0.03,
                "take_profit": 0.05,
                "position_size": 0.5,
            },
            MarketRegime.HIGH_VOL: {
                "strategy": "volatility_breakout",
                "stop_loss": 0.08,
                "take_profit": 0.20,
                "position_size": 0.4,
            },
            MarketRegime.LOW_VOL: {
                "strategy": "breakout",
                "stop_loss": 0.04,
                "take_profit": 0.08,
                "position_size": 0.6,
            },
            MarketRegime.UNKNOWN: {
                "strategy": "cash",
                "stop_loss": 0.0,
                "take_profit": 0.0,
                "position_size": 0.0,
            },
        }
        return params.get(regime, params[MarketRegime.UNKNOWN])

    def is_circuit_breaker(self, close: list, threshold: float = 0.07) -> bool:
        """判断是否触发熔断"""
        if len(close) < 2:
            return False
        change = abs(close[-1] / close[-2] - 1)
        return change > threshold
