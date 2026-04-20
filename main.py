# -*- coding: utf-8 -*-
"""
AlphaPredator 主入口
支持实时监控模式（模拟/实盘切换）
"""
from __future__ import annotations

import argparse
import logging
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.fetcher import DataManager
from signals.alpha_signals import AlphaSignalGenerator
from signals.regime_detector import RegimeDetector
from signals.anti_quant import AntiQuantEngine
from strategies.momentum_breakout import MomentumBreakoutStrategy
from strategies.adaptive import AdaptiveStrategy
from risk.position_manager import KellyPositionManager
from config.settings import CONFIG

logging.basicConfig(
    level=getattr(logging, CONFIG.log_level),
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


class AlphaPredator:
    """
    AlphaPredator 主控制器

    流程：
    1. 数据采集 → 2. Alpha信号 → 3. 市场状态 → 4. 反量化分析
    → 5. 策略决策 → 6. 仓位管理 → 7. 执行 → 8. 风控监控
    """

    def __init__(self, mode: str = "paper"):
        self.mode = mode  # paper=模拟盘, live=实盘
        self.data_manager = DataManager(CONFIG.data_source)
        self.alpha_gen = AlphaSignalGenerator()
        self.regime_detector = RegimeDetector()
        self.anti_quant = AntiQuantEngine(
            trailing_stop_pct=CONFIG.anti_quant.trailing_stop_pct,
            cash_reserve_ratio=CONFIG.anti_quant.cash_reserve_ratio,
        )
        self.position_mgr = KellyPositionManager(
            kelly_fraction=CONFIG.risk.kelly_fraction,
            max_position_pct=CONFIG.risk.max_single_position,
            max_total_exposure=0.8,
        )
        self.strategy = MomentumBreakoutStrategy()
        self.positions = {}  # symbol -> Position
        self.cash = CONFIG.backtest.initial_capital
        self.equity = self.cash

        logger.info(f"AlphaPredator 初始化完成 (mode={mode})")

    def scan_opportunities(self, symbols: list) -> list:
        """
        扫描全市场机会，返回排序后的候选股票
        """
        candidates = []

        for symbol in symbols:
            try:
                df = self.data_manager.get_ohlcv(symbol, None, None, freq="1D")
                if df is None or len(df) < 60:
                    continue

                # 计算信号
                df_signals = self.alpha_gen.compute_all(df)

                # 检测市场状态
                regime = self.regime_detector.detect_current(df)

                # 反量化分析
                anti_result = self.anti_quant.compute_anti_quant_score(df_signals)

                # 策略信号
                signal = self.strategy.generate_signal(
                    df_signals,
                    regime=regime.value if hasattr(regime, "value") else str(regime),
                )

                # 组合评分
                composite_score = (
                    df_signals["alpha_score"].iloc[-1] * 0.4 +
                    anti_result["score"] / 100 * 0.3 +
                    (1 if signal.direction != 0 else 0) * signal.strength * 0.3
                )

                candidates.append({
                    "symbol": symbol,
                    "score": composite_score,
                    "signal": signal,
                    "regime": regime.value if hasattr(regime, "value") else regime,
                    "anti_result": anti_result,
                    "latest_price": df["close"].iloc[-1],
                })

            except Exception as e:
                logger.warning(f"{symbol} 扫描失败: {e}")

        # 按评分排序
        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates

    def place_order(self, symbol: str, direction: int, quantity: int, price: float):
        """
        下单（模拟/实盘）
        """
        if self.mode == "paper":
            logger.info(f"[模拟] {'买入' if direction > 0 else '卖出'} {symbol} x{quantity} @ {price:.2f}")
        else:
            # TODO: 实盘接口（券商API/CTP/通达信等）
            logger.info(f"[实盘] {'买入' if direction > 0 else '卖出'} {symbol} x{quantity} @ {price:.2f}")

    def run(self, symbols: list, interval: int = 300):
        """
        主循环（定时扫描 + 信号处理）
        """
        logger.info(f"主循环启动，监控 {len(symbols)} 只股票，每 {interval}s 扫描一次")

        while True:
            timestamp = datetime.now().strftime("%H:%M:%S")
            logger.info(f"\n{'='*50}\n[{timestamp}] 开始扫描...")

            # 熔断检查
            index_df = self.data_manager.get_ohlcv("000300", None, None, freq="1D")
            if self.regime_detector.is_circuit_breaker(index_df, CONFIG.risk.circuit_breaker_pct):
                logger.warning("🚨 检测到市场熔断！全仓清空！")
                self.close_all_positions()
                continue

            candidates = self.scan_opportunities(symbols)

            if not candidates:
                logger.info("当前无候选机会")
                continue

            top = candidates[0]
            logger.info(f"最优机会: {top['symbol']} 评分={top['score']:.3f} 信号={top['signal']}")
            logger.info(f"  市场状态: {top['regime']}")
            logger.info(f"  反量化: {top['anti_result']}")

            # 仓位管理
            available_capital = self.cash * (1 - CONFIG.anti_quant.cash_reserve_ratio)

            # 止盈止损检查
            self.check_exits()

            # 开仓
            sig = top["signal"]
            if sig.direction != 0 and sig.strength > 0.5:
                price = top["latest_price"]
                stop_loss = sig.metadata.get("stop_loss", price * (1 - CONFIG.risk.stop_loss_pct))
                position_value = available_capital * top["anti_result"].get("confidence", 50) / 100
                shares = int(position_value / price / 100) * 100

                if shares > 0:
                    self.place_order(top["symbol"], sig.direction, shares, price)
                    self.cash -= shares * price

            logger.info(f"当前权益: {self.cash:,.2f} | 持仓: {list(self.positions.keys())}")

            import time
            time.sleep(interval)

    def check_exits(self):
        """检查止盈止损"""
        # TODO: 遍历持仓，检查止损
        pass

    def close_all_positions(self):
        """全仓清空"""
        for symbol, pos in list(self.positions.items()):
            self.place_order(symbol, -pos.direction, pos.quantity, pos.entry_price)
        self.positions.clear()


def main():
    parser = argparse.ArgumentParser(description="AlphaPredator 交易系统")
    parser.add_argument("--mode", choices=["paper", "live"], default="paper",
                        help="运行模式: paper=模拟盘, live=实盘")
    parser.add_argument("--symbols", nargs="+",
                        default=["000001", "600036", "600519", "601318", "000858"],
                        help="监控股票列表")
    parser.add_argument("--interval", type=int, default=300,
                        help="扫描间隔(秒)")
    args = parser.parse_args()

    runner = AlphaPredator(mode=args.mode)
    runner.run(args.symbols, args.interval)


if __name__ == "__main__":
    main()
