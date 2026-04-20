# -*- coding: utf-8 -*-
"""
机构资金追踪模块
核心功能：识别大资金的VWAP偏离和成交量异常，追踪建仓/出货信号
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Tuple, Optional


class InstitutionalTracker:
    """
    追踪机构资金行为，识别大资金建仓/出货信号。

    原理：
    - 大资金建仓时，价格小幅上涨但成交量显著放大（VWAP > 当前价）
    - 大资金出货时，价格小幅下跌但成交量放大（VWAP < 当前价）
    - 成交量异常用Z-score检测，超过2倍标准差视为显著
    """

    def __init__(self, vwap_window: int = 20, vol_zscore_threshold: float = 2.0):
        self.vwap_window = vwap_window
        self.zscore_threshold = vol_zscore_threshold

    def compute_vwap(self, df: pd.DataFrame) -> pd.Series:
        """计算成交量加权平均价"""
        typical = (df["high"] + df["low"] + df["close"]) / 3
        vwap = (typical * df["volume"]).rolling(self.vwap_window).sum() / \
               df["volume"].rolling(self.vwap_window).sum()
        return vwap

    def compute_volume_zscore(self, df: pd.DataFrame) -> pd.Series:
        """计算成交量Z-score，识别异常放量"""
        vol_ma = df["volume"].rolling(self.vwap_window).mean()
        vol_std = df["volume"].rolling(self.vwap_window).std()
        zscore = (df["volume"] - vol_ma) / vol_std
        return zscore

    def detect_vwap_deviation(self, df: pd.DataFrame) -> pd.Series:
        """
        检测VWAP偏离
        返回值: 正=价格被低估(机构可能买入)，负=价格被高估(机构可能卖出)
        """
        vwap = self.compute_vwap(df)
        deviation = (df["close"] - vwap) / vwap
        return deviation

    def detect_institutional_activity(
        self,
        df: pd.DataFrame,
        price_col: str = "close"
    ) -> pd.DataFrame:
        """
        综合机构活动检测

        Returns:
            DataFrame with columns:
            - vwap_deviation: VWAP偏离度
            - vol_zscore: 成交量Z分数
            - activity_score: 综合活动强度 (0-100)
            - signal: 1=建仓, -1=出货, 0=中性
        """
        vwap_dev = self.detect_vwap_deviation(df)
        vol_zscore = self.compute_volume_zscore(df)

        # 综合评分：建仓信号 = VWAP正偏离 + 放量
        #         出货信号 = VWAP负偏离 + 放量
        activity_score = np.abs(vol_zscore.clip(lower=0)) * 20 + np.abs(vwap_dev) * 50
        activity_score = activity_score.clip(upper=100)

        signal = np.where(
            (vwap_dev > 0.01) & (vol_zscore > self.zscore_threshold), 1,
            np.where(
                (vwap_dev < -0.01) & (vol_zscore > self.zscore_threshold), -1,
                0
            )
        )

        return pd.DataFrame({
            "vwap_deviation": vwap_dev,
            "vol_zscore": vol_zscore,
            "activity_score": activity_score,
            "signal": signal,
        }, index=df.index)

    def detect_large_order_flow(
        self,
        tick_data: pd.DataFrame
    ) -> Tuple[pd.Series, pd.Series]:
        """
        从分时成交数据检测大单资金流向

        Args:
            tick_data: DataFrame with columns:
                - price: 成交价
                - volume: 成交量
                - direction: 主动买入=1, 主动卖出=-1 (from Level2)

        Returns:
            (net_flow, flow_strength): 净流向和强度
        """
        tick_data = tick_data.copy()
        tick_data["flow"] = tick_data["volume"] * tick_data["direction"]
        tick_data["abs_flow"] = np.abs(tick_data["flow"])

        # 大单阈值：单笔超过平均成交额5倍
        avg_vol = tick_data["volume"].mean()
        large_order_mask = tick_data["volume"] > (avg_vol * 5)

        net_flow = tick_data.loc[large_order_mask, "flow"].sum()
        total_flow = tick_data.loc[large_order_mask, "abs_flow"].sum()

        flow_strength = net_flow / total_flow if total_flow > 0 else 0

        return net_flow, flow_strength

    def estimate_position_buildup(
        self,
        df: pd.DataFrame,
        lookback: int = 20
    ) -> pd.DataFrame:
        """
        估算持仓变化（基于量价关系推断）
        原理：价格上涨+持仓量增加 → 主力吸筹
              价格下跌+持仓量减少 → 主力派发
        """
        ret = df["close"].pct_change()
        vol_change = df["volume"].pct_change()

        # 吸筹指标：价格上涨 且 成交量增加
        accumulation = (ret > 0) & (vol_change > 0)
        # 派发指标：价格下跌 且 成交量增加
        distribution = (ret < 0) & (vol_change > 0)

        df_result = pd.DataFrame({
            "accumulation": accumulation.rolling(lookback).sum(),
            "distribution": distribution.rolling(lookback).sum(),
            "net_position_change": accumulation.astype(int) - distribution.astype(int),
        }, index=df.index)

        return df_result
