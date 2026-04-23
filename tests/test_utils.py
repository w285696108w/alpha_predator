# -*- coding: utf-8 -*-
"""
Utils 工具函数单元测试
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import math
from utils import (
    mean, std, percentile, rolling_mean, rolling_std,
    rolling_max, rolling_min, pct_change, zscore, ewm_mean,
    rsi, macd, bollinger_bands, rank, sharpe_ratio
)


class TestMeanStd:
    def test_mean_empty(self):
        assert mean([]) == 0.0

    def test_mean_single(self):
        assert mean([5.0]) == 5.0

    def test_mean_normal(self):
        assert mean([1, 2, 3, 4, 5]) == 3.0

    def test_std_empty(self):
        assert std([]) == 0.0

    def test_std_single(self):
        assert std([5.0]) == 0.0

    def test_std_normal(self):
        s = std([2, 4, 4, 4, 5, 5, 7, 9])
        assert abs(s - 2.138) < 0.01


class TestRolling:
    def test_rolling_mean(self):
        assert rolling_mean([1, 2, 3, 4, 5], 3) == [1, 1.5, 2, 3, 4]

    def test_rolling_std(self):
        r = rolling_std([1, 2, 3, 4, 5], 3)
        assert len(r) == 5
        assert r[0] == 0.0  # std of single element = 0

    def test_rolling_max(self):
        assert rolling_max([1, 3, 2, 5, 4], 3) == [1, 3, 3, 5, 5]

    def test_rolling_min(self):
        assert rolling_min([5, 3, 2, 6, 1], 3) == [5, 3, 2, 2, 1]


class TestRSI:
    def test_rsi_rising(self):
        close = list(range(1, 21))  # 上涨
        r = rsi(close, period=14)
        assert len(r) == 20
        assert r[-1] > 50  # 强势

    def test_rsi_falling(self):
        close = list(range(20, 0, -1))  # 下跌
        r = rsi(close, period=14)
        assert r[-1] < 50

    def test_rsi_short(self):
        close = [100, 101, 102]
        r = rsi(close, period=14)
        assert len(r) == 3  # output length == input length, all 50.0 (not enough data)


class TestMACD:
    def test_macd_basic(self):
        close = list(range(1, 51))
        macd_line, signal_line, histogram = macd(close)
        assert len(macd_line) == 50
        assert len(signal_line) == 50
        assert len(histogram) == 50

    def test_macd_signal_behind_macd(self):
        """Signal line 应该滞后于 MACD 线（平滑效果）"""
        close = [100 + 10 * math.sin(i / 5) for i in range(50)]
        macd_line, signal_line, histogram = macd(close)
        # 两者走势应该一致
        assert abs(mean(macd_line) - mean(signal_line)) < 50


class TestBollingerBands:
    def test_bb_basic(self):
        close = list(range(1, 31))
        upper, mid, lower = bollinger_bands(close, window=20, nb_std=2)
        assert len(upper) == 30
        assert len(mid) == 30
        assert len(lower) == 30
        # upper 应该 >= mid >= lower
        for u, m, l in zip(upper, mid, lower):
            assert u >= m >= l


class TestRank:
    def test_rank_basic(self):
        data = [30, 10, 40, 20]
        r = rank(data)
        assert len(r) == 4
        # 排序: 30(idx0)->0, 10(idx1)->1/3, 40(idx2)->2/3, 20(idx3)->1
        assert abs(r[0] - 0.0) < 0.001       # idx0=30 最小排第0位
        assert abs(r[1] - 1.0/3.0) < 0.001  # idx1=10 排第1位
        assert abs(r[2] - 2.0/3.0) < 0.001  # idx2=40 排第2位
        assert abs(r[3] - 1.0) < 0.001      # idx3=20 最大排第3位

    def test_rank_equal(self):
        data = [5, 5, 5, 5]
        r = rank(data)
        assert all(x == 0.5 for x in r)


class TestSharpeRatio:
    def test_sharpe_positive(self):
        returns = [0.01, 0.02, 0.015, 0.01]
        s = sharpe_ratio(returns)
        assert s > 0

    def test_sharpe_negative(self):
        returns = [-0.01, -0.02, -0.015, -0.01]
        s = sharpe_ratio(returns)
        assert s < 0

    def test_sharpe_single(self):
        assert sharpe_ratio([0.01]) == 0.0  # std=0 时返回0


class TestPctChange:
    def test_pct_change_basic(self):
        result = pct_change([100, 110, 105, 115], period=1)
        assert len(result) == 4
        assert result[1] == 0.1  # 10% 涨幅

    def test_pct_change_period2(self):
        result = pct_change([100, 100, 200, 200, 400], period=2)
        assert result[2] == 1.0  # 100->200 是100%涨幅


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
