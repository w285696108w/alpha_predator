# -*- coding: utf-8 -*-
"""
数据获取模块 - 纯Python实现
"""
from __future__ import annotations

import math
import logging
from abc import ABC, abstractmethod
from datetime import datetime, date
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


def _df_to_lists(df):
    """将 pandas DataFrame 转为字典列表（兼容纯 Python）"""
    if df is None or df.empty:
        return None
    return {
        "open": df["open"].tolist(),
        "high": df["high"].tolist(),
        "low": df["low"].tolist(),
        "close": df["close"].tolist(),
        "volume": df["volume"].tolist(),
        "index": [str(d) for d in df.index],
    }


class BaseDataFetcher(ABC):
    """数据获取基类"""

    @abstractmethod
    def get_bars(self, symbol: str, start: date, end: date, freq: str = "1D"):
        pass

    @abstractmethod
    def get_realtime_quote(self, symbol: str) -> Dict:
        pass


class MockFetcher(BaseDataFetcher):
    """模拟数据（无依赖）"""

    def __init__(self, seed: int = 42):
        import random
        self.rng = random.Random(seed)

    def get_bars(self, symbol: str, start: date, end: date, freq: str = "1D"):
        """生成模拟K线数据 - 包含多种市场形态以触发Alpha信号"""
        from datetime import timedelta

        dates = []
        current = start
        while current <= end:
            if current.weekday() < 5:
                dates.append(current)
            current += timedelta(days=1)

        n = len(dates)
        closes = []
        opens = []
        highs = []
        lows = []
        volumes = []

        # 分段生成不同市场形态，确保触发Alpha信号
        # 阶段1(0~25%): 下跌 → RSI<30买入信号
        # 阶段2(25~50%): 反弹趋势 → 趋势跟踪信号
        # 阶段3(50~75%): 震荡 → BB突破/回归信号
        # 阶段4(75~100%): 上涨 → RSI>70超买信号

        n1 = int(n * 0.25)   # 下跌
        n2 = int(n * 0.25)   # 反弹
        n3 = int(n * 0.25)   # 震荡
        n4 = n - n1 - n2 - n3  # 上涨

        price = 10.0

        # 阶段1：下跌 (price -20%)
        for i in range(n1):
            change = -0.008 - self.rng.uniform(0.0, 0.005)
            price *= (1 + change)
            closes.append(round(price, 2))

        # 阶段2：反弹上涨 (price +30%)
        for i in range(n2):
            change = 0.01 + self.rng.uniform(-0.003, 0.008)
            price *= (1 + change)
            closes.append(round(price, 2))

        # 阶段3：震荡 (+/-15% 波动)
        for i in range(n3):
            wave = math.sin(i / (n3 / 6)) * 0.007
            change = wave + self.rng.uniform(-0.003, 0.003)
            price *= (1 + change)
            closes.append(round(price, 2))

        # 阶段4：上涨 (+25%)
        for i in range(n4):
            change = 0.008 + self.rng.uniform(-0.002, 0.006)
            price *= (1 + change)
            closes.append(round(price, 2))

        # 生成OHLV
        for i, close_px in enumerate(closes):
            open_px = close_px * (1 + self.rng.uniform(-0.008, 0.008))
            high_px = max(close_px, open_px) * (1 + self.rng.uniform(0.002, 0.02))
            low_px = min(close_px, open_px) * (1 - self.rng.uniform(0.002, 0.02))
            vol = int(self.rng.uniform(5e5, 3e6))
            opens.append(round(open_px, 2))
            highs.append(round(high_px, 2))
            lows.append(round(low_px, 2))
            volumes.append(vol)

        return {
            "symbol": symbol,
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volumes,
            "dates": [str(d) for d in dates],
        }

    def get_realtime_quote(self, symbol: str) -> Dict:
        bars = self.get_bars(symbol, date.today(), date.today())
        return {
            "code": symbol,
            "price": bars["close"][-1] if bars else 10.0,
            "change_pct": 0.0,
        }


class DataManager:
    """数据管理器"""

    def __init__(self, source: str = "mock"):
        if source == "akshare":
            try:
                import akshare
                self.fetcher = AKShareFetcher()
                self.source = "akshare"
            except ImportError:
                logger.warning("AKShare 未安装，使用模拟数据")
                self.fetcher = MockFetcher()
                self.source = "mock"
        else:
            self.fetcher = MockFetcher()
            self.source = "mock"

        self._cache: Dict[str, Dict] = {}

    def get_bars(self, symbol: str, start: date, end: date,
                 freq: str = "1D") -> Optional[Dict]:
        """获取K线数据"""
        bars = self.fetcher.get_bars(symbol, start, end, freq)
        if bars and len(bars.get("close", [])) > 0:
            self._cache[symbol] = bars
        return bars

    def get_latest_price(self, symbol: str) -> float:
        """获取最新价格"""
        bars = self._cache.get(symbol)
        if bars:
            return bars["close"][-1]
        return 10.0

    def get_closes(self, symbol: str) -> List[float]:
        bars = self._cache.get(symbol, {})
        return bars.get("close", [])

    def get_ohlcv_lists(self, symbol: str, start: date, end: date) -> Optional[Dict]:
        """获取 OHLCV 数据（字典列表格式）"""
        bars = self.get_bars(symbol, start, end)
        if not bars:
            return None
        return {
            "open": bars["open"],
            "high": bars["high"],
            "low": bars["low"],
            "close": bars["close"],
            "volume": bars["volume"],
        }
