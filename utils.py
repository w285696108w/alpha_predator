# -*- coding: utf-8 -*-
"""
Pure-Python numeric utilities (no numpy)
兼容老旧CPU，所有计算均使用标准库实现
"""
from __future__ import annotations

import math
import statistics
from typing import List, Optional


def mean(data: List[float]) -> float:
    if not data:
        return 0.0
    return sum(data) / len(data)


def std(data: List[float]) -> float:
    if len(data) < 2:
        return 0.0
    return statistics.stdev(data)


def variance(data: List[float]) -> float:
    if len(data) < 2:
        return 0.0
    return statistics.variance(data)


def percentile(data: List[float], q: float) -> float:
    """计算分位数"""
    if not data:
        return 0.0
    s = sorted(data)
    idx = (len(s) - 1) * q / 100
    lo = int(math.floor(idx))
    hi = int(math.ceil(idx))
    if lo == hi:
        return s[lo]
    return s[lo] + (s[hi] - s[lo]) * (idx - lo)


def rolling_mean(values: List[float], window: int) -> List[float]:
    """移动平均"""
    n = len(values)
    result = []
    for i in range(n):
        start = max(0, i - window + 1)
        window_data = values[start:i + 1]
        result.append(mean(window_data))
    return result


def rolling_std(values: List[float], window: int) -> List[float]:
    """移动标准差"""
    n = len(values)
    result = []
    for i in range(n):
        start = max(0, i - window + 1)
        window_data = values[start:i + 1]
        result.append(std(window_data))
    return result


def rolling_max(values: List[float], window: int) -> List[float]:
    """移动最大值"""
    n = len(values)
    result = []
    for i in range(n):
        start = max(0, i - window + 1)
        window_data = values[start:i + 1]
        result.append(max(window_data))
    return result


def rolling_min(values: List[float], window: int) -> List[float]:
    """移动最小值"""
    n = len(values)
    result = []
    for i in range(n):
        start = max(0, i - window + 1)
        window_data = values[start:i + 1]
        result.append(min(window_data))
    return result


def rolling_sum(values: List[float], window: int) -> List[float]:
    """移动求和"""
    n = len(values)
    result = []
    for i in range(n):
        start = max(0, i - window + 1)
        window_data = values[start:i + 1]
        result.append(sum(window_data))
    return result


def pct_change(values: List[float], period: int = 1) -> List[float]:
    """百分比变化"""
    result = [0.0] * min(period, len(values))
    for i in range(period, len(values)):
        if values[i - period] != 0:
            result.append((values[i] - values[i - period]) / values[i - period])
        else:
            result.append(0.0)
    return result


def zscore(data: List[float]) -> List[float]:
    """Z-score 标准化"""
    m = mean(data)
    s = std(data)
    if s == 0:
        return [0.0] * len(data)
    return [(x - m) / s for x in data]


def ewm_mean(values: List[float], span: int) -> List[float]:
    """指数加权移动平均"""
    alpha = 2.0 / (span + 1)
    result = [values[0]] if values else []
    for v in values[1:]:
        result.append(alpha * v + (1 - alpha) * result[-1])
    return result


def typical_price(high: List[float], low: List[float], close: List[float]) -> List[float]:
    return [(h + l + c) / 3 for h, l, c in zip(high, low, close)]


def vwap(close: List[float], high: List[float], low: List[float],
         volume: List[float], window: int) -> List[float]:
    """成交量加权平均价"""
    tp = typical_price(high, low, close)
    result = []
    for i in range(len(tp)):
        start = max(0, i - window + 1)
        num = sum(tp[j] * volume[j] for j in range(start, i + 1))
        den = sum(volume[j] for j in range(start, i + 1))
        result.append(num / den if den > 0 else tp[i])
    return result


def rsi(close: List[float], period: int = 14) -> List[float]:
    """RSI相对强弱"""
    if len(close) < 2:
        return [50.0] * len(close)

    deltas = [0.0] + [close[i] - close[i - 1] for i in range(1, len(close))]
    gains = [max(d, 0) for d in deltas]
    losses = [abs(min(d, 0)) for d in deltas]

    result = [50.0] * period  # 初始填充

    avg_gain = mean(gains[:period]) if period > 0 else 0
    avg_loss = mean(losses[:period]) if period > 0 else 0

    for i in range(period, len(close)):
        if i > period:
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            result.append(100.0)
        else:
            rs = avg_gain / avg_loss
            result.append(100.0 - (100.0 / (1.0 + rs)))

    return result


def atr(high: List[float], low: List[float], close: List[float],
        period: int = 14) -> List[float]:
    """Average True Range"""
    if len(close) < 2:
        return [0.0] * len(close)

    tr = [0.0]
    for i in range(1, len(close)):
        h, l, c = high[i], low[i], close[i - 1]
        tr.append(max(h - l, abs(h - c), abs(l - c)))

    return rolling_mean(tr, period)


def macd(close: List[float], fast: int = 12, slow: int = 26,
         signal: int = 9) -> tuple[List[float], List[float], List[float]]:
    """MACD指标"""
    ema_fast = ewm_mean(close, fast)
    ema_slow = ewm_mean(close, slow)
    macd_line = [f - s for f, s in zip(ema_fast, ema_slow)]
    signal_line = ewm_mean(macd_line, signal)
    histogram = [m - s for m, s in zip(macd_line, signal_line)]
    return macd_line, signal_line, histogram


def bollinger_bands(close: List[float], window: int = 20,
                    nb_std: float = 2.0) -> tuple[List[float], List[float], List[float]]:
    """布林带"""
    ma = rolling_mean(close, window)
    sd = rolling_std(close, window)
    upper = [m + nb_std * s for m, s in zip(ma, sd)]
    lower = [m - nb_std * s for m, s in zip(ma, sd)]
    return upper, ma, lower


def rank(data: List[float]) -> List[float]:
    """百分位排名 (0~1)"""
    if not data:
        return []
    sorted_data = sorted(enumerate(data), key=lambda x: x[1])
    n = len(data)
    result = [0.0] * n
    for rank_val, (idx, _) in enumerate(sorted_data):
        result[idx] = rank_val / (n - 1) if n > 1 else 0.5
    return result


def sharpe_ratio(returns: List[float], risk_free: float = 0.03) -> float:
    """夏普比率"""
    if len(returns) < 2:
        return 0.0
    ann_ret = mean(returns) * 252
    ann_vol = std(returns) * math.sqrt(252)
    if ann_vol == 0:
        return 0.0
    return (ann_ret - risk_free) / ann_vol
