# -*- coding: utf-8 -*-
"""
策略基类
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import numpy as np
import pandas as pd
from typing import Dict, Optional, List


class Signal:
    """交易信号"""

    def __init__(
        self,
        direction: int,        # 1=做多, -1=做空, 0=空仓
        strength: float = 1.0,  # 信号强度 0~1
        reason: str = "",
        metadata: Optional[Dict] = None,
    ):
        self.direction = direction
        self.strength = strength
        self.reason = reason
        self.metadata = metadata or {}

    def __repr__(self):
        dir_str = {1: "LONG", -1: "SHORT", 0: "FLAT"}
        return f"Signal({dir_str[self.direction]}, strength={self.strength:.2f}, {self.reason})"


class Position:
    """持仓"""

    def __init__(
        self,
        symbol: str,
        direction: int,
        quantity: float,
        entry_price: float,
        entry_date,
        stop_loss: float,
        take_profit: Optional[float] = None,
    ):
        self.symbol = symbol
        self.direction = direction  # 1=long, -1=short, 0=flat
        self.quantity = quantity
        self.entry_price = entry_price
        self.entry_date = entry_date
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.highest_price = entry_price
        self.unrealized_pnl = 0.0
        self.realized_pnl = 0.0

    @property
    def market_value(self) -> float:
        return self.quantity * self.entry_price

    def update_highest(self, current_price: float):
        if self.direction == 1:
            self.highest_price = max(self.highest_price, current_price)
        else:
            self.highest_price = min(self.highest_price, current_price)

    def check_stop_loss(self, current_price: float) -> bool:
        if self.direction == 1:
            return current_price < self.stop_loss
        elif self.direction == -1:
            return current_price > self.stop_loss
        return False

    def check_take_profit(self, current_price: float) -> bool:
        if self.take_profit is None:
            return False
        if self.direction == 1:
            return current_price >= self.take_profit
        elif self.direction == -1:
            return current_price <= self.take_profit
        return False


class BaseStrategy(ABC):
    """
    策略基类
    所有策略必须实现 generate_signal 方法
    """

    def __init__(self, name: str = "base"):
        self.name = name
        self.positions: Dict[str, Position] = {}
        self.signal_history: List[Signal] = []

    @abstractmethod
    def generate_signal(
        self,
        df: pd.DataFrame,
        regime: Optional[str] = None,
        **kwargs
    ) -> Signal:
        """
        生成交易信号

        Args:
            df: K线数据（需包含 OHLCV）
            regime: 市场状态
            **kwargs: 其他参数

        Returns:
            Signal对象
        """
        pass

    def on_bar(self, bar: pd.Series, **kwargs) -> Optional[Signal]:
        """逐根K线处理（可选实现，用于实时交易）"""
        return None

    def get_position(self, symbol: str) -> Optional[Position]:
        """获取持仓"""
        return self.positions.get(symbol)

    def has_position(self, symbol: str) -> bool:
        """是否有持仓"""
        pos = self.positions.get(symbol)
        return pos is not None and pos.quantity > 0

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.name}>"
