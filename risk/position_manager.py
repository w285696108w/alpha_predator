# -*- coding: utf-8 -*-
"""
仓位管理模块
核心：凯利公式 + 风险平价 + 动态调整
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Dict, Optional


class KellyPositionManager:
    """
    基于凯利公式的仓位管理器

    公式: f* = (p * b - q) / b
    其中:
    - p = 胜率（历史胜率或主观估计）
    - q = 败率 (1 - p)
    - b = 盈亏比 (平均盈利 / 平均亏损)

    保守使用: 半凯利 (f* * 0.5)
    """

    def __init__(
        self,
        kelly_fraction: float = 0.5,       # 凯利系数（保守程度）
        max_position_pct: float = 0.03,     # 单笔最大仓位%
        max_industry_pct: float = 0.15,     # 单行业最大仓位%
        max_total_exposure: float = 0.80,  # 最大总仓位暴露
    ):
        self.kelly_fraction = kelly_fraction
        self.max_position_pct = max_position_pct
        self.max_industry_pct = max_industry_pct
        self.max_total_exposure = max_total_exposure

        # 交易统计
        self.trade_history: list = []

    def compute_kelly_fraction(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
    ) -> float:
        """
        计算凯利最优仓位比例

        Args:
            win_rate: 胜率 (0~1)
            avg_win: 平均盈利金额
            avg_loss: 平均亏损金额（正数）

        Returns:
            kelly_fraction: 最优仓位比例
        """
        if avg_loss <= 0 or win_rate <= 0 or avg_win <= 0:
            return 0.0

        b = avg_win / avg_loss  # 盈亏比
        p = win_rate
        q = 1 - p

        kelly = (p * b - q) / b

        # 凯利公式在胜率<盈亏比倒数时为负，无意义
        if kelly <= 0:
            return 0.0

        # 应用保守系数（半凯利）
        return min(kelly * self.kelly_fraction, self.max_position_pct)

    def update_trade_stats(
        self,
        symbol: str,
        pnl: float,
        win: bool,
    ):
        """更新交易统计"""
        self.trade_history.append({"symbol": symbol, "pnl": pnl, "win": win})

    def compute_position_from_stats(
        self,
        symbol: str,
        total_capital: float,
        entry_price: float,
        stop_loss_price: float,
    ) -> Dict:
        """
        基于历史统计计算仓位

        Returns:
            dict: {"shares": int, "position_value": float, "risk_pct": float}
        """
        # 计算该品种历史胜率和盈亏比
        relevant_trades = [t for t in self.trade_history if t["symbol"] == symbol]
        if len(relevant_trades) >= 10:
            wins = [t["pnl"] for t in relevant_trades if t["win"]]
            losses = [t["pnl"] for t in relevant_trades if not t["win"]]

            win_rate = len(wins) / len(relevant_trades)
            avg_win = np.mean(wins) if wins else 0
            avg_loss = abs(np.mean(losses)) if losses else entry_price * 0.05

            kelly_pct = self.compute_kelly_fraction(win_rate, avg_win, avg_loss)
        else:
            # 数据不足，用保守默认值
            kelly_pct = self.max_position_pct * 0.5

        # 风险预算：根据止损距离调整
        risk_per_share = abs(entry_price - stop_loss_price)
        if risk_per_share > 0:
            # 允许的最大损失 = 资金 * 仓位% * 止损%
            # 所以仓位 = (资金 * 仓位%) / 每股风险
            max_position_value = total_capital * kelly_pct
            shares = int(max_position_value / entry_price)
            shares = max(100, shares)  # 最少100股

            risk_pct = (shares * risk_per_share) / total_capital
        else:
            shares = 0
            risk_pct = 0.0

        return {
            "shares": shares,
            "position_value": shares * entry_price,
            "risk_pct": risk_pct,
            "kelly_pct": kelly_pct,
        }

    def check_industry_limit(
        self,
        current_industry_exposure: float,
        new_position_pct: float,
    ) -> bool:
        """检查行业仓位限制"""
        return (current_industry_exposure + new_position_pct) <= self.max_industry_pct

    def check_total_limit(
        self,
        current_total_exposure: float,
        new_position_pct: float,
    ) -> bool:
        """检查总仓位限制"""
        return (current_total_exposure + new_position_pct) <= self.max_total_exposure


class PortfolioRiskMonitor:
    """
    组合风险监控器
    实时监控VaR、组合敞口、最大回撤
    """

    def __init__(
        self,
        var_95: float = 0.05,
        var_99: float = 0.10,
    ):
        self.var_95 = var_95
        self.var_99 = var_99
        self.peak_value = 0.0
        self.max_drawdown = 0.0

    def update_peak(self, current_value: float):
        """更新峰值"""
        if current_value > self.peak_value:
            self.peak_value = current_value

    def compute_drawdown(self, current_value: float) -> float:
        """计算当前回撤"""
        if self.peak_value == 0:
            return 0.0
        return (self.peak_value - current_value) / self.peak_value

    def compute_portfolio_var(
        self,
        positions: Dict[str, Dict],
        returns: pd.DataFrame,
        confidence: float = 0.95,
    ) -> float:
        """
        计算组合VaR（基于历史模拟法）

        Args:
            positions: {symbol: {"weight": float, "value": float}}
            returns: 历史收益率 DataFrame
            confidence: 置信度

        Returns:
            VaR: 最大损失金额
        """
        if returns.empty or not positions:
            return 0.0

        total_value = sum(p["value"] for p in positions.values())
        if total_value == 0:
            return 0.0

        # 组合收益率 = 权重 * 收益率
        portfolio_returns = pd.Series(0.0, index=returns.index)
        for symbol, pos in positions.items():
            if symbol in returns.columns:
                portfolio_returns += pos["weight"] * returns[symbol]

        # 取置信度对应的分位点
        q = 1 - confidence
        var_pct = portfolio_returns.quantile(q)
        var_amount = abs(var_pct * total_value)
        return var_amount

    def check_risk_limits(
        self,
        current_value: float,
        positions: Dict,
        returns: pd.DataFrame,
    ) -> Dict[str, bool]:
        """
        检查各项风控指标是否超限

        Returns:
            dict: {"var_95_ok": bool, "var_99_ok": bool, "drawdown_ok": bool, ...}
        """
        self.update_peak(current_value)
        drawdown = self.compute_drawdown(current_value)

        var_95 = self.compute_portfolio_var(positions, returns, 0.95)
        var_99 = self.compute_portfolio_var(positions, returns, 0.99)

        return {
            "var_95_ok": var_95 <= self.var_95 * current_value,
            "var_99_ok": var_99 <= self.var_99 * current_value,
            "drawdown_ok": drawdown <= 0.15,  # 最大回撤15%
            "peak_ok": self.peak_value > 0,
        }
