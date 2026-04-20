# -*- coding: utf-8 -*-
"""
自适应复合策略
根据市场状态自动切换最优子策略
"""
from __future__ import annotations

import pandas as pd
from typing import Dict, List, Optional

from .base import BaseStrategy, Signal
from ..signals.regime_detector import MarketRegime


class AdaptiveStrategy(BaseStrategy):
    """
    自适应复合策略

    核心理念：没有万能策略，市场状态决定策略适配性。
    本策略根据 RegimeDetector 判断当前市场环境，
    动态选择胜率最高的子策略。

    策略切换逻辑：
    - 趋势上涨 → 动量突破（追涨）
    - 趋势下跌 → 现金/空头（回避）
    - 区间震荡 → 均值回归（高抛低吸）
    - 高波动市 → 突破+对冲（谨慎）
    - 低波动市 → 突破系统（蓄势待发）
    """

    def __init__(
        self,
        regime_detector,        # RegimeDetector 实例
        sub_strategies: Optional[Dict[str, BaseStrategy]] = None,
    ):
        super().__init__(name="adaptive_composite")
        self.regime_detector = regime_detector

        # 默认子策略映射
        self.sub_strategies: Dict[str, BaseStrategy] = sub_strategies or {}

    def register_sub_strategy(self, regime: str, strategy: BaseStrategy):
        """注册子策略"""
        self.sub_strategies[regime] = strategy

    def generate_signal(
        self,
        df: pd.DataFrame,
        regime: Optional[str] = None,
        **kwargs
    ) -> Signal:
        """
        生成复合信号
        """
        if regime is None:
            regime = self.regime_detector.detect_current(df)
            if isinstance(regime, MarketRegime):
                regime = regime.value

        # 获取当前市场状态对应的策略参数
        params = self.regime_detector.get_strategy_params(
            MarketRegime(regime) if regime in [e.value for e in MarketRegime] else MarketRegime.UNKNOWN
        )

        recommended_strategy = params.get("strategy", "momentum")

        # 根据推荐策略选择子策略
        sub_strategy = self.sub_strategies.get(recommended_strategy)

        if sub_strategy is None:
            # 无对应子策略，返回中性
            return Signal(
                direction=0,
                reason=f"市场={regime}, 推荐={recommended_strategy}, 无子策略",
                metadata={"regime": regime, "params": params},
            )

        # 调用子策略
        signal = sub_strategy.generate_signal(df, regime=regime, **kwargs)
        signal.metadata["regime"] = regime
        signal.metadata["recommended_strategy"] = recommended_strategy
        signal.metadata["position_size"] = params.get("position_size", 0.5)

        return signal

    def get_current_regime(self, df: pd.DataFrame) -> MarketRegime:
        """获取当前市场状态"""
        return self.regime_detector.detect_current(df)

    def get_portfolio_adjustment(self, regime: MarketRegime) -> float:
        """
        根据市场状态返回组合仓位调整系数
        用于整体仓位管理
        """
        adjustments = {
            MarketRegime.TREND_UP: 1.0,
            MarketRegime.TREND_DOWN: 0.3,
            MarketRegime.RANGE_BOUND: 0.6,
            MarketRegime.HIGH_VOL: 0.4,
            MarketRegime.LOW_VOL: 0.8,
            MarketRegime.UNKNOWN: 0.2,
        }
        return adjustments.get(regime, 0.5)
