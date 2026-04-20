# -*- coding: utf-8 -*-
"""
回测入口脚本 - 纯Python实现
"""
from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import date, timedelta
from data.fetcher import DataManager, MockFetcher
from signals.alpha_signals import AlphaSignalGenerator
from signals.regime_detector import RegimeDetector
from signals.anti_quant import AntiQuantEngine
from backtest.engine import BacktestEngine
from config.settings import CONFIG


def run_single_backtest(symbol: str, seed: int, start: date, end: date) -> dict:
    """运行单个标的回测"""
    mgr = DataManager("mock")
    mgr.fetcher = MockFetcher(seed=seed)
    bars = mgr.get_bars(symbol, start, end, "1D")

    if not bars or not bars.get("close"):
        return None

    close = bars["close"]
    n = len(close)
    if n < 30:
        return None

    alpha_gen = AlphaSignalGenerator()
    regime_detector = RegimeDetector()
    anti_quant = AntiQuantEngine(
        trailing_stop_pct=CONFIG.anti_quant.trailing_stop_pct,
        cash_reserve_ratio=CONFIG.anti_quant.cash_reserve_ratio,
    )
    engine = BacktestEngine(
        initial_capital=CONFIG.backtest.initial_capital,
        commission_rate=CONFIG.backtest.commission_rate,
        stamp_tax=CONFIG.backtest.stamp_tax,
    )

    ohlcv = {
        "close": close, "high": bars["high"], "low": bars["low"],
        "open": bars["open"], "volume": bars["volume"],
    }
    sig_dict = alpha_gen.compute_all(ohlcv)
    alpha_scores = sig_dict.get("alpha_scores", sig_dict.get("alpha_score", []))

    # 反量化信号
    anti_scores = []
    for i in range(n):
        sub = {
            "close": close[max(0, i - 80):i + 1],
            "high": bars["high"][max(0, i - 80):i + 1],
            "low": bars["low"][max(0, i - 80):i + 1],
            "volume": bars["volume"][max(0, i - 80):i + 1],
        }
        r = anti_quant.compute_anti_quant_score(**sub)
        anti_scores.append(r["score"] / 100.0)

    # 综合信号
    combined = [alpha_scores[i] * 0.6 + anti_scores[i] * 0.4 for i in range(n)]

    # 大盘过滤
    regimes = regime_detector.detect(close)
    market_filter = []
    for r_obj in regimes:
        rv = r_obj.value if hasattr(r_obj, "value") else str(r_obj)
        market_filter.append(0.0 if rv in ("trend_down", "high_vol") else 1.0)

    # 交易信号
    trade_signals = []
    for i in range(n):
        if combined[i] > 0.25 and market_filter[i] == 1.0:
            trade_signals.append(1.0)
        elif combined[i] < -0.25:
            trade_signals.append(-1.0)
        else:
            trade_signals.append(0.0)

    result = engine.run(close, trade_signals)
    result["close_start"] = close[0]
    result["close_end"] = close[-1]
    result["data_days"] = n
    return result


def main():
    print("=" * 60)
    print("AlphaPredator Backtest Report")
    print("=" * 60)

    start = date.fromisoformat("2025-01-01")
    end = date.fromisoformat("2025-07-01")

    print(f"\nBacktest Period: {start} ~ {end}")
    print(f"Initial Capital: {CONFIG.backtest.initial_capital:,.0f}")
    print(f"Strategy: Alpha Momentum + Anti-Quant Composite")
    print(f"Risk Control: Kelly Sizing + Trailing Stop 10%")
    print(f"\n{'='*60}")
    print(f"{'Symbol':<12} {'Return':>10} {'Sharpe':>8} {'MaxDD':>10} {'Trades':>8} {'WinRate':>8} {'StockPrice':>12}")
    print(f"{'-'*60}")

    all_results = {}

    # 标的配置：不同种子=不同市场形态
    # A=强势趋势(低噪声), B=震荡市(高胜率), C=反弹市(高盈亏比)
    configs = [
        ("STOCK_A", 42, "Strong Uptrend"),
        ("STOCK_B", 137, "Range-Bound"),
        ("STOCK_C", 256, "Rebound"),
        ("STOCK_D", 999, "Volatility"),
        ("INDEX_300", 1, "Market Benchmark"),
    ]

    total_return_sum = 0.0
    sharpe_sum = 0.0

    for symbol, seed, desc in configs:
        result = run_single_backtest(symbol, seed, start, end)
        if result:
            all_results[symbol] = result
            total_ret = result["total_return"]
            sharpe = result["sharpe_ratio"]
            mdd = result["max_drawdown"]
            trades = result["total_trades"]
            win_rate = result["win_rate"]
            price_info = f"{result['close_start']:.2f} -> {result['close_end']:.2f}"

            marker = ""
            if total_ret > 0.05 and sharpe > 1.0:
                marker = " [EXCELLENT]"
            elif total_ret > 0:
                marker = " [POSITIVE]"

            print(f"{symbol:<12} {total_ret:>9.1%} {sharpe:>8.2f} {mdd:>9.1%} {trades:>8d} {win_rate:>7.1%} {price_info:>12}{marker}")

            total_return_sum += total_ret
            sharpe_sum += sharpe

    print(f"{'-'*60}")

    n = len(all_results)
    avg_ret = total_return_sum / n
    avg_sharpe = sharpe_sum / n
    positive_count = sum(1 for r in all_results.values() if r["total_return"] > 0)

    print(f"\nSummary: Avg Return={avg_ret:.2%} | Avg Sharpe={avg_sharpe:.2f} | Profitable={positive_count}/{n}")

    # Calculate portfolio equity curve
    print(f"\n{'='*60}")
    print("Strategy Logic Summary:")
    print("1. Alpha Signals    - RSI+MACD+BB+Momentum+Divergence Weighted Score")
    print("2. Anti-Quant      - Detect institutional footprint / liquidity trap / EOD arbitrage")
    print("3. Market Regime    - Auto-switch strategy based on trend/range/high-vol detection")
    print("4. Kelly Sizing    - Dynamic position sizing based on historical win rate & R/R")
    print("5. Trailing Stop   - Hard stop at 10% drawdown from peak")
    print(f"{'='*60}")
    print("\nOK: Backtest complete")


if __name__ == "__main__":
    main()
