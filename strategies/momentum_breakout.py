# -*- coding: utf-8 -*-
"""
动量突破策略 + 自适应止损
融合海龟突破 + RSI修正 + 追踪止损
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Optional

from .base import BaseStrategy, Signal


class MomentumBreakoutStrategy(BaseStrategy):
    """
    动量突破策略（基于海龟交易法改进）

    核心逻辑：
    1. 大盘过滤：沪深300指数多头排列时开仓，空头排列时空仓
    2. 选股：动量排名靠前（前20%）
    3. 择时：突破20日唐奇安通道高点 + RSI修正（强势回调入场）
    4. 止损：ATR动态止损 + 追踪止损
    5. 出场：从最高点回撤10%或RSI>80止盈
    """

    def __init__(
        self,
        breakout_period: int = 20,      # 唐奇安通道周期
        atr_period: int = 14,            # ATR周期
        atr_multiplier: float = 2.0,    # ATR倍数止损
        rsi_entry_threshold: float = 45,  # RSI回调入场阈值
        rsi_exit_threshold: float = 80,   # RSI超买止盈阈值
        trailing_stop_pct: float = 0.10,  # 追踪止损回撤比例
        lookback: int = 252,             # 动量计算周期
        min_momentum_rank: float = 0.8,  # 最小动量排名（前20%）
    ):
        super().__init__(name="momentum_breakout")
        self.breakout_period = breakout_period
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier
        self.rsi_entry_threshold = rsi_entry_threshold
        self.rsi_exit_threshold = rsi_exit_threshold
        self.trailing_stop_pct = trailing_stop_pct
        self.lookback = lookback
        self.min_momentum_rank = min_momentum_rank

    def _compute_atr(self, df: pd.DataFrame) -> pd.Series:
        """计算ATR"""
        high = df["high"]
        low = df["low"]
        close = df["close"]
        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs(),
        ], axis=1).max(axis=1)
        atr = tr.rolling(self.atr_period).mean()
        return atr

    def _compute_rsi(self, series: pd.Series, period: int = 14) -> pd.Series:
        """计算RSI"""
        delta = series.diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gain / loss.replace(0, np.inf)
        return 100 - (100 / (1 + rs))

    def _compute_donchian(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算唐奇安通道"""
        return pd.DataFrame({
            "upper": df["high"].rolling(self.breakout_period).max().shift(1),
            "lower": df["low"].rolling(self.breakout_period).min().shift(1),
            "middle": ((df["high"].rolling(self.breakout_period).max().shift(1) +
                        df["low"].rolling(self.breakout_period).min().shift(1)) / 2),
        })

    def _compute_momentum_rank(self, df: pd.DataFrame) -> float:
        """计算动量排名（0~1）"""
        ret = df["close"].pct_change(self.lookback)
        rank = ret.rank(pct=True).iloc[-1]
        return rank

    def generate_signal(
        self,
        df: pd.DataFrame,
        regime: Optional[str] = None,
        benchmark_df: Optional[pd.DataFrame] = None,
        **kwargs
    ) -> Signal:
        """
        生成交易信号
        """
        if len(df) < self.breakout_period + 5:
            return Signal(0, reason="数据不足")

        close = df["close"]
        high = df["high"]
        low = df["low"]

        # 1. 大盘过滤
        if benchmark_df is not None and len(benchmark_df) > 20:
            bm_ma5 = benchmark_df["close"].rolling(5).mean().iloc[-1]
            bm_ma20 = benchmark_df["close"].rolling(20).mean().iloc[-1]
            if bm_ma5 < bm_ma20:
                return Signal(0, reason="大盘空头排列，禁止开多")

        # 2. 动量过滤
        mom_rank = self._compute_momentum_rank(df)
        if mom_rank < self.min_momentum_rank:
            return Signal(0, reason=f"动量排名不足 ({mom_rank:.2f} < {self.min_momentum_rank})")

        # 3. 唐奇安通道
        dc = self._compute_donchian(df)
        upper = dc["upper"].iloc[-1]
        lower = dc["lower"].iloc[-1]

        # 4. RSI
        rsi = self._compute_rsi(close).iloc[-1]
        rsi_prev = self._compute_rsi(close).iloc[-2]

        # 5. ATR止损
        atr = self._compute_atr(df).iloc[-1]
        entry_price = close.iloc[-1]

        current_high = high.iloc[-1]
        prev_high = high.iloc[-2]

        # ── 开多信号 ──
        # 突破唐奇安高点 且 RSI<45回调（强势股回调入场）
        breakout = current_high > upper and prev_high <= upper
        rsi_pullback = rsi < self.rsi_entry_threshold and rsi_prev >= self.rsi_entry_threshold

        if breakout and rsi_pullback:
            stop_loss = entry_price - self.atr_multiplier * atr
            return Signal(
                direction=1,
                strength=mom_rank,
                reason=f"海龟突破+RSI回调({rsi:.1f})入场",
                metadata={
                    "entry_price": entry_price,
                    "stop_loss": stop_loss,
                    "atr": atr,
                }
            )

        # ── 开空信号（仅允许做空在高波动下行趋势）──
        if regime == "high_vol" and rsi > 70:
            breakdown = low.iloc[-1] < lower and low.iloc[-2] >= lower
            if breakdown:
                stop_loss = entry_price + self.atr_multiplier * atr
                return Signal(
                    direction=-1,
                    strength=0.6,
                    reason=f"高波动+RSI超买({rsi:.1f})做空",
                    metadata={
                        "entry_price": entry_price,
                        "stop_loss": stop_loss,
                    }
                )

        # ── 出场信号 ──
        # 从最高点回撤超过10%
        if self.has_position(kwargs.get("symbol", "")):
            highest = kwargs.get("highest_price", entry_price)
            drawdown = (entry_price - highest) / highest if highest > 0 else 0
            if abs(drawdown) > self.trailing_stop_pct:
                return Signal(0, reason=f"追踪止损(drawdown={drawdown:.1%})")

        # RSI超买止盈
        if rsi > self.rsi_exit_threshold:
            return Signal(0, reason=f"RSI超买止盈({rsi:.1f}>{self.rsi_exit_threshold})")

        return Signal(0, reason="无信号")
