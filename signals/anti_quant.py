# -*- coding: utf-8 -*-
"""
反量化机制模块 - 纯Python实现
"""
from __future__ import annotations

from typing import Dict, List, Tuple, Optional
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import mean, std, rolling_mean, rolling_std, pct_change


class AntiQuantEngine:
    """
    反量化策略引擎

    量化资金的三大命门：
    1. 预设方案死板 → 识别量化信号，做反向操作
    2. 极端行情失效 → 高波动时主动减仓/对冲
    3. 流动性踩踏 → 检测流动性枯竭信号，提前退出
    """

    def __init__(
        self,
        trailing_stop_pct: float = 0.10,
        tick_density_threshold: float = 0.8,
        cash_reserve_ratio: float = 0.30,
    ):
        self.trailing_stop_pct = trailing_stop_pct
        self.tick_density_threshold = tick_density_threshold
        self.cash_reserve_ratio = cash_reserve_ratio

    def detect_high_freq_pattern(self, prices: List[float],
                                  window: int = 50) -> Tuple[bool, float]:
        """
        检测高频量化T+0模式
        """
        if len(prices) < window:
            return False, 0.0
        recent = prices[-window:]
        rounded = [round(p, 2) for p in recent]
        freq = {}
        for p in rounded:
            freq[p] = freq.get(p, 0) + 1
        max_density = max(freq.values()) / len(recent) if freq else 0.0
        return max_density > self.tick_density_threshold, max_density

    def detect_end_of_day_opportunity(
        self,
        open_prices: List[float],
        close_prices: List[float],
    ) -> Tuple[str, float]:
        """
        尾盘套利机会检测
        """
        if not open_prices or not close_prices:
            return "hold", 0.0
        day_return = (close_prices[-1] / open_prices[0]) - 1.0
        if day_return > 0.03:
            return "sell_early", abs(day_return) * 5
        elif day_return < -0.03:
            return "buy_early", abs(day_return) * 5
        return "hold", 0.0

    def detect_liquidity_crisis(self, close: List[float],
                                 volume: List[float],
                                 window: int = 20) -> Tuple[bool, str]:
        """
        流动性踩踏检测
        """
        if len(close) < window * 3:
            return False, "GREEN"

        returns = pct_change(close)
        vol = rolling_std(returns, window)
        vol_ma_long = mean(vol[-window * 2:]) if len(vol) >= window * 2 else mean(vol)
        vol_now = vol[-1] if vol else 0.0
        vol_ratio = vol_now / vol_ma_long if vol_ma_long > 0 else 1.0

        vol_now_avg = mean(volume[-window:]) if len(volume) >= window else mean(volume)
        vol_long_avg = mean(volume) if volume else 1.0
        vol_ratio_vol = vol_now_avg / vol_long_avg if vol_long_avg > 0 else 1.0

        if vol_ratio > 2.5 and vol_ratio_vol < 0.5:
            return True, "RED"
        elif vol_ratio > 1.75:
            return True, "YELLOW"
        return False, "GREEN"

    def iv_hedge_decision(self, iv: float, spot_return: float) -> Tuple[str, float]:
        """隐波率对冲决策"""
        if iv < 20:
            return "long_volatility", min(0.2, abs(spot_return) * 2)
        elif iv > 50:
            return "short_volatility", 0.1
        return "no_hedge", 0.0

    def compute_trailing_stop(
        self,
        entry_price: float,
        current_price: float,
        highest_since_entry: float,
        trailing_pct: Optional[float] = None,
    ) -> Tuple[bool, float, float]:
        """追踪止损"""
        trailing_pct = trailing_pct or self.trailing_stop_pct
        stop_price = highest_since_entry * (1 - trailing_pct)
        drawdown = (current_price - highest_since_entry) / highest_since_entry
        should_stop = current_price < stop_price
        return should_stop, stop_price, drawdown

    def detect_institutional_footprint(
        self, close: List[float], high: List[float],
        low: List[float], volume: List[float],
        vwap_window: int = 20,
    ) -> Tuple[str, float]:
        """
        识别机构建仓痕迹
        """
        if len(close) < vwap_window + 1:
            return "no_signal", 0.0

        tp = [(h + l + c) / 3 for h, l, c in zip(high, low, close)]
        vwap_vals = rolling_mean(
            [tp[i] * volume[i] / mean(volume[max(0, i - vwap_window + 1):i + 1])
             for i in range(len(tp))],
            vwap_window
        )

        # 简化 vwap 计算
        vwap_simple = _vwap_simple(tp, volume, vwap_window)

        vwap_dev = (close[-1] - vwap_simple[-1]) / vwap_simple[-1] if vwap_simple[-1] else 0.0

        vol_ma = mean(volume[-vwap_window:]) if len(volume) >= vwap_window else mean(volume)
        vol_now = volume[-1]
        vol_ratio = vol_now / vol_ma if vol_ma > 0 else 1.0

        if vwap_dev < -0.01 and vol_ratio > 1.5:
            return "follow_institutional_long", min(vol_ratio * 20, 95)
        elif vwap_dev > 0.01 and vol_ratio > 1.5:
            return "follow_institutional_short", min(vol_ratio * 20, 95)
        return "no_signal", 0.0

    def compute_anti_quant_score(self, close: List[float], high: List[float],
                                  low: List[float], volume: List[float]) -> Dict:
        """
        综合反量化评分
        """
        scores = []
        crisis, level = self.detect_liquidity_crisis(close, volume)

        if crisis:
            if level == "RED":
                scores.append(-30)
            elif level == "YELLOW":
                scores.append(-10)

        inst_sig, inst_conf = self.detect_institutional_footprint(close, high, low, volume)
        if inst_sig == "follow_institutional_long":
            scores.append(inst_conf * 0.4)
        elif inst_sig == "follow_institutional_short":
            scores.append(-inst_conf * 0.4)

        eod_sig, eod_conf = self.detect_end_of_day_opportunity([close[0]], close)
        if eod_sig == "buy_early":
            scores.append(eod_conf * 0.2)
        elif eod_sig == "sell_early":
            scores.append(-eod_conf * 0.2)

        total_score = sum(scores)
        total_score = max(-100.0, min(100.0, total_score))

        if total_score > 20:
            action = "buy"
        elif total_score < -20:
            action = "sell"
        else:
            action = "hold"

        risk = "HIGH" if level == "RED" else ("MEDIUM" if level == "YELLOW" else "LOW")

        return {
            "score": total_score,
            "action": action,
            "confidence": abs(total_score),
            "risk_level": risk,
            "liquidity_alert": level,
        }


def _vwap_simple(typical: List[float], volume: List[float], window: int) -> List[float]:
    """简化VWAP"""
    result = []
    for i in range(len(typical)):
        start = max(0, i - window + 1)
        num = sum(typical[j] * volume[j] for j in range(start, i + 1))
        den = sum(volume[j] for j in range(start, i + 1))
        result.append(num / den if den > 0 else typical[i])
    return result
