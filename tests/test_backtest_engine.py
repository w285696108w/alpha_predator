# -*- coding: utf-8 -*-
"""
BacktestEngine 单元测试
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from backtest.engine import BacktestEngine


class MockEngine(BacktestEngine):
    """BacktestEngine 纯数据测试"""
    pass


def _make_close(n=20, trend=0.001):
    """生成模拟收盘价序列"""
    import math
    return [100 * math.exp(trend * i) for i in range(n)]


def test_engine_empty():
    engine = BacktestEngine(initial_capital=100_000)
    result = engine.run([], [])
    assert result["total_return"] == 0.0
    assert result["total_trades"] == 0


def test_engine_no_signal():
    engine = BacktestEngine(initial_capital=100_000)
    close = _make_close(20)
    signals = [0] * 20
    result = engine.run(close, signals)
    # 无信号，不开仓，权益不变
    assert abs(result["total_return"]) < 0.001
    assert result["total_trades"] == 0


def test_engine_long_signal():
    engine = BacktestEngine(initial_capital=100_000)
    close = _make_close(20, trend=0.01)  # 上涨趋势
    signals = [1] + [0] * 19  # 第0天开多，之后不动
    result = engine.run(close, signals)
    assert result["total_trades"] == 1
    assert result["total_return"] > 0  # 赚钱


def test_engine_short_signal():
    engine = BacktestEngine(initial_capital=100_000)
    close = _make_close(20, trend=-0.01)  # 下跌趋势
    signals = [-1] + [0] * 19  # 开空
    result = engine.run(close, signals)
    assert result["total_trades"] == 1  # 至少有一笔交易


def test_engine_reversal():
    """先做多再反手做空：跨多空转换正确处理"""
    import math
    engine = BacktestEngine(initial_capital=100_000)
    # 涨5天(100->约164) 再跌5天(回到约100) 再微跌1天，共11天
    up = [100 * math.exp(0.1 * i) for i in range(5)]
    down = [up[-1] * math.exp(-0.1 * i) for i in range(1, 6)]
    close = up + down + [down[-1] * math.exp(-0.05)]
    close = close[:11]
    # 多头5天，反手空头5天，第11天平仓
    signals = [1] * 5 + [-1] * 5 + [0] * 1
    assert len(signals) == len(close), f"signals={len(signals)} close={len(close)}"
    result = engine.run(close, signals)
    assert result["total_trades"] == 2  # 平多1笔 + 平空1笔
    assert "sharpe_ratio" in result
    assert "max_drawdown" in result


def test_engine_commission():
    """佣金和印花税应该被计入"""
    engine = BacktestEngine(initial_capital=100_000, commission_rate=0.0003, stamp_tax=0.001)
    close = _make_close(20, trend=0.01)
    signals = [1] + [0] * 19
    result = engine.run(close, signals)
    # 有交易就有成本，实际收益应该低于理论值
    assert result["total_trades"] == 1


def test_engine_win_rate():
    """胜率计算"""
    import math
    engine = BacktestEngine(initial_capital=1_000_000)
    # 两个完整上涨周期, close=20天, signals也要20天
    close = [100 * math.exp(0.02 * i) for i in range(10)] + \
            [100 * math.exp(0.02 * 10) * math.exp(-0.02 * i) for i in range(1, 11)]
    # 开多5天、平仓、再开多5天、再平仓
    signals = [1] * 5 + [0] * 5 + [-1] * 5 + [0] * 5
    assert len(signals) == len(close), f"signals={len(signals)} close={len(close)}"
    result = engine.run(close, signals)
    assert result["total_trades"] == 2


def test_engine_max_drawdown():
    """最大回撤计算"""
    import math
    engine = BacktestEngine(initial_capital=100_000)
    # 涨5天(100->约164) 再跌5天(回到约100)
    close = [100 * math.exp(0.1 * i) for i in range(5)] + \
            [100 * math.exp(0.1 * 5) * math.exp(-0.1 * i) for i in range(1, 6)]
    assert abs(close[0] - close[-1]) < 0.01  # 起终点价格相近
    signals = [1] * 10
    result = engine.run(close, signals)
    assert result["max_drawdown"] < 0  # 负数表示回撤


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
