# -*- coding: utf-8 -*-
"""
回测引擎 - 纯Python实现
"""
from __future__ import annotations

import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import percentile, mean, std


class BacktestEngine:
    """
    向量化回测引擎 - 无numpy依赖
    """

    def __init__(
        self,
        initial_capital: float = 1_000_000.0,
        commission_rate: float = 0.0003,
        stamp_tax: float = 0.001,
        slippage_rate: float = 0.0005,
    ):
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.stamp_tax = stamp_tax
        self.slippage_rate = slippage_rate

    def run(
        self,
        close: list,
        signals: list,
        position_sizing: list = None,
    ) -> dict:
        """
        运行回测
        """
        n = len(close)
        if n < 2 or not signals:
            return self._empty_result()

        if position_sizing is None:
            position_sizing = [0.3] * n  # 默认30%仓位，避免过度杠杆

        cash = self.initial_capital
        position = 0.0       # 持仓股数（正=多头，负=空头）
        entry_price = 0.0     # 开仓价格
        entry_commission = 0.0  # 开仓时支付的佣金
        trades = []
        equity = []
        peak_equity = self.initial_capital
        max_drawdown = 0.0

        for i in range(n):
            current_price = close[i]
            signal = signals[i]
            size = position_sizing[i] if i < len(position_sizing) else 0.3

            # 滑点
            buy_price = current_price * (1 + self.slippage_rate)
            sell_price = current_price * (1 - self.slippage_rate)

            # ── 平仓 ──
            # 两种情况需要平仓：信号为0，或者信号方向与持仓方向相反（多转空/空转多）
            if (signal == 0 or (position != 0 and signal * position < 0)) and position != 0:
                if position > 0:
                    # 平多：按卖价结算
                    gross = position * sell_price
                    commission = gross * self.commission_rate
                    tax = gross * self.stamp_tax
                    net = gross - commission - tax
                    pnl = net - position * entry_price - entry_commission
                    cash += net
                else:
                    # 平空：按买价结算
                    shares = abs(position)
                    gross = shares * buy_price
                    commission = gross * self.commission_rate
                    net = gross + commission
                    pnl = shares * entry_price - net - entry_commission
                    cash += net

                trades.append({
                    "index": i,
                    "direction": 1 if position > 0 else -1,
                    "price": sell_price if position > 0 else buy_price,
                    "quantity": abs(position),
                    "pnl": pnl,
                    "entry_price": entry_price,
                })
                position = 0.0
                entry_price = 0.0
                entry_commission = 0.0

            # ── 开仓 ──
            elif signal != 0 and position == 0:
                # 仓位上限：总资本的 size%
                available = cash * size
                num_shares = int(available / buy_price / 100) * 100
                if num_shares > 0:
                    cost = num_shares * buy_price
                    commission = cost * self.commission_rate
                    cash -= (cost + commission)
                    position = num_shares * signal
                    entry_price = buy_price
                    entry_commission = commission

            # ── 权益计算 ──
            if position > 0:
                equity_value = cash + position * current_price
            elif position < 0:
                equity_value = cash + abs(position) * entry_price - abs(position) * current_price
            else:
                equity_value = cash

            # 更新峰值和最大回撤
            if equity_value > peak_equity:
                peak_equity = equity_value
            drawdown = (peak_equity - equity_value) / peak_equity if peak_equity > 0 else 0.0
            if drawdown > max_drawdown:
                max_drawdown = drawdown

            equity.append(equity_value)

        # ── 计算绩效指标 ──
        if not equity:
            return self._empty_result()

        returns = []
        for i in range(1, len(equity)):
            if equity[i - 1] != 0:
                ret = (equity[i] - equity[i - 1]) / equity[i - 1]
                returns.append(ret)
            else:
                returns.append(0.0)

        total_return = (equity[-1] / self.initial_capital - 1)
        ann_ret = self._annualized_return(equity, len(returns))
        sharpe = self._sharpe_ratio(returns)

        return {
            "equity_curve": equity,
            "trades": trades,
            "total_return": total_return,
            "annualized_return": ann_ret,
            "max_drawdown": -max_drawdown,
            "sharpe_ratio": sharpe,
            "calmar_ratio": ann_ret / abs(max_drawdown) if max_drawdown > 0 else 0.0,
            "win_rate": len([t for t in trades if t["pnl"] > 0]) / max(len(trades), 1),
            "total_trades": len(trades),
            "avg_pnl": mean([t["pnl"] for t in trades]) if trades else 0.0,
            "max_consecutive_loss": self._max_consecutive_loss(trades),
        }

    def _annualized_return(self, equity: list, n_returns: int) -> float:
        if len(equity) < 2 or n_returns == 0:
            return 0.0
        total = equity[-1] / self.initial_capital
        years = len(equity) / 252
        return total ** (1 / years) - 1 if years > 0 else 0.0

    def _sharpe_ratio(self, returns: list, risk_free: float = 0.03) -> float:
        if len(returns) < 2:
            return 0.0
        ann_ret = mean(returns) * 252
        vol = std(returns) * math.sqrt(252)
        return (ann_ret - risk_free) / vol if vol != 0 else 0.0

    def _max_consecutive_loss(self, trades: list) -> int:
        if not trades:
            return 0
        max_loss = 0
        current = 0
        for t in trades:
            if t["pnl"] < 0:
                current += 1
                max_loss = max(max_loss, current)
            else:
                current = 0
        return max_loss

    def _empty_result(self) -> dict:
        return {
            "equity_curve": [],
            "trades": [],
            "total_return": 0.0,
            "annualized_return": 0.0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0,
            "calmar_ratio": 0.0,
            "win_rate": 0.0,
            "total_trades": 0,
            "avg_pnl": 0.0,
            "max_consecutive_loss": 0,
        }
