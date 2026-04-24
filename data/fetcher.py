# -*- coding: utf-8 -*-
"""
数据获取层 - 支持多种真实数据源

数据源架构（可插拔）:
  - "mock":      MockFetcher 纯模拟数据（无网络依赖，适合开发/测试/CI）
  - "akshare":   AKShareFetcher A股实时/历史（HTTP，新浪财经）
  - "baostock":  BaostockFetcher A股历史（HTTP，无需注册）
  - "tushare":   TushareFetcher Tushare Pro API（需token，积分≥120）

切换方式: 修改 config/settings.py 中 GlobalConfig.data_source.source
         或在实例化 DataManager 时传入 source 参数
"""
from __future__ import annotations

import sys as _sys
import os as _os
from abc import ABC, abstractmethod
from datetime import date, timedelta
from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
# 数据源基类
# ─────────────────────────────────────────────────────────────────────────────

class BaseDataFetcher(ABC):
    """数据源抽象基类"""

    @abstractmethod
    def get_bars(self, symbol: str, start: date, end: date,
                 freq: str = "1D") -> dict:
        """
        获取K线数据

        Args:
            symbol: 股票代码，如 "000001"（深市）或 "600000"（沪市）
            start:  开始日期
            end:    结束日期
            freq:   频率 "1D"(日线) / "1W"(周线) / "1M"(月线)

        Returns:
            dict: {"open": [...], "high": [...], "low": [...],
                   "close": [...], "volume": [...]}
            至少需要 2 条数据，少于 2 条返回空 dict
        """
        ...

    def normalize_symbol(self, symbol: str) -> str:
        """规范化股票代码（不同数据源格式不同），子类可覆盖"""
        return symbol.upper()


# ─────────────────────────────────────────────────────────────────────────────
# 数据源1: 模拟数据（保留用于测试/CI）
# ─────────────────────────────────────────────────────────────────────────────

class MockFetcher(BaseDataFetcher):
    """
    纯模拟数据发生器（无网络依赖）

    生成5种市场形态的合成OHLCV:
      seed=42   强势趋势
      seed=137  区间震荡
      seed=256  反弹市
      seed=999  高波动
      seed=1    大盘基准
    """

    PHASES = ["strong_uptrend", "range_bound", "rebound", "high_volatility", "benchmark"]

    def __init__(self, seed: int = 42, initial_price: float = 100.0,
                 phase: Optional[str] = None):
        import random
        self.seed = seed
        self.initial_price = initial_price
        self.phase = phase or self.PHASES[seed % len(self.PHASES)]
        self._rng = random.Random(seed)

    def get_bars(self, symbol: str, start: date, end: date,
                 freq: str = "1D") -> dict:
        import math
        days = (end - start).days + 1
        if days < 2:
            return {}
        n = min(days, 252)
        phase = self.phase

        if phase == "strong_uptrend":
            mu, sigma, vol_boost = 0.0006, 0.010, 1.0
        elif phase == "range_bound":
            mu, sigma, vol_boost = 0.0, 0.008, 0.8
        elif phase == "rebound":
            mu, sigma, vol_boost = 0.0003, 0.014, 1.2
        elif phase == "high_volatility":
            mu, sigma, vol_boost = 0.0, 0.022, 2.0
        else:
            mu, sigma, vol_boost = 0.0002, 0.012, 1.0

        rng = self._rng
        close_prices = [self.initial_price]
        volume_list = [1_000_000 + rng.randint(-50_000, 50_000)]

        for i in range(1, n):
            daily_ret = rng.gauss(mu, sigma * vol_boost)
            p = close_prices[-1] * (1 + daily_ret)
            ma = sum(close_prices[max(0, i - 20):i]) / min(20, i)
            if abs(p - ma) / ma > 0.15:
                p = ma * (1 + rng.gauss(0, 0.01))
            p = max(p, 1.0)
            close_prices.append(p)
            vol = 1_000_000 * (1 + abs(daily_ret) * 10) + rng.randint(-50_000, 50_000)
            volume_list.append(int(max(100_000, vol)))

        open_prices = close_prices[:-1]
        open_prices.insert(0, self.initial_price * (1 + rng.gauss(0, 0.005)))
        high_prices = [max(o, c) + abs(rng.gauss(0, 0.005 * c))
                       for o, c in zip(open_prices, close_prices)]
        low_prices = [min(o, c) - abs(rng.gauss(0, 0.005 * c))
                      for o, c in zip(open_prices, close_prices)]
        high_prices[0] = max(open_prices[0], close_prices[0])
        low_prices[0] = min(open_prices[0], close_prices[0])

        return {
            "open":   [round(x, 2) for x in open_prices],
            "high":   [round(x, 2) for x in high_prices],
            "low":    [round(x, 2) for x in low_prices],
            "close":  [round(x, 2) for x in close_prices],
            "volume": volume_list,
        }


# ─────────────────────────────────────────────────────────────────────────────
# 数据源2: AKShare（A股，新浪财经，无需Token）
# ─────────────────────────────────────────────────────────────────────────────

class AKShareFetcher(BaseDataFetcher):
    """AKShare A股数据获取器（无需注册/API Key）"""

    def __init__(self, adjust: str = "qfq"):
        self.adjust = adjust

    def normalize_symbol(self, symbol: str) -> str:
        s = symbol.upper().strip().replace(".SH", "").replace(".SZ", "")
        if s.startswith("6"):
            return f"{s}.SH"
        elif s.startswith(("0", "3")):
            return f"{s}.SZ"
        return s

    def get_bars(self, symbol: str, start: date, end: date,
                 freq: str = "1D") -> dict:
        sym = self.normalize_symbol(symbol)
        period_map = {"1D": "daily", "D": "daily", "1W": "weekly",
                      "W": "weekly", "1M": "monthly", "M": "monthly"}
        period = period_map.get(freq, "daily")
        try:
            import akshare as ak
            df = ak.stock_zh_a_hist(
                symbol=sym.split(".")[0],
                period=period,
                start_date=start.strftime("%Y%m%d"),
                end_date=end.strftime("%Y%m%d"),
                adjust=self.adjust,
            )
            if df is None or df.empty:
                return {}
            df = df.sort_values("日期")
            return {
                "open":   df["开盘"].tolist(),
                "high":   df["最高"].tolist(),
                "low":    df["最低"].tolist(),
                "close":  df["收盘"].tolist(),
                "volume": [int(v) for v in df["成交量"].tolist()],
            }
        except Exception as e:
            print(f"[AKShareFetcher] {sym} failed: {e}, falling back to MockFetcher")
            seed_map = {"000001": 42, "600000": 137, "000300": 1, "000016": 256, "399006": 999}
            seed = seed_map.get(sym.split(".")[0], hash(sym) % 9999)
            return MockFetcher(seed=seed).get_bars(symbol, start, end, freq)


# ─────────────────────────────────────────────────────────────────────────────
# 数据源3: Baostock（免费，无需注册）
# ─────────────────────────────────────────────────────────────────────────────

class BaostockFetcher(BaseDataFetcher):
    """
    Baostock 免费行情获取器（完全免费，无需注册/Token）
    股票代码格式: "sh.600000" / "sz.000001"
    """

    _login_done = False

    def __init__(self, adjust: str = "2"):
        self.adjust = adjust

    def normalize_symbol(self, symbol: str) -> str:
        s = symbol.upper().strip().replace(".SH", "").replace(".SZ", "")
        if s.startswith("6"):
            return f"sh.{s}"
        elif s.startswith(("0", "3")):
            return f"sz.{s}"
        return f"sh.{s}"

    @classmethod
    def _ensure_login(cls):
        if not cls._login_done:
            try:
                import baostock as bs
                bs.login()
                cls._login_done = True
            except Exception as e:
                print(f"[BaostockFetcher] login failed: {e}")
                raise

    def get_bars(self, symbol: str, start: date, end: date,
                 freq: str = "1D") -> dict:
        sym = self.normalize_symbol(symbol)
        try:
            self._ensure_login()
            import baostock as bs
            freq_map = {"1D": "d", "D": "d", "1W": "w", "W": "w"}
            bfreq = freq_map.get(freq, "d")
            rs = bs.query_history_k_data_plus(
                sym,
                "date,open,high,low,close,volume",
                start_date=start.strftime("%Y-%m-%d"),
                end_date=end.strftime("%Y-%m-%d"),
                frequency=bfreq,
                adjust=self.adjust,
            )
            if rs.error_code != "0":
                raise RuntimeError(f"Baostock error: {rs.error_msg}")
            dates, opens, highs, lows, closes, volumes = [], [], [], [], [], []
            while rs.error_code == "0" and rs.next():
                row = rs.get_row_data()
                if row[1]:
                    dates.append(row[0])
                    opens.append(float(row[1]))
                    highs.append(float(row[2]))
                    lows.append(float(row[3]))
                    closes.append(float(row[4]))
                    volumes.append(int(float(row[5])))
            if not dates:
                return {}
            return {"open": opens, "high": highs, "low": lows,
                    "close": closes, "volume": volumes}
        except Exception as e:
            print(f"[BaostockFetcher] {sym} failed: {e}, falling back to MockFetcher")
            seed_map = {"000001": 42, "600000": 137, "000300": 1, "000016": 256, "399006": 999}
            raw = symbol.split(".")[-1]
            seed = seed_map.get(raw, hash(sym) % 9999)
            return MockFetcher(seed=seed).get_bars(symbol, start, end, freq)

    @classmethod
    def logout(cls):
        if cls._login_done:
            try:
                import baostock as bs
                bs.logout()
                cls._login_done = False
            except Exception:
                pass


# ─────────────────────────────────────────────────────────────────────────────
# 数据源4: Tushare Pro（需Token）
# ─────────────────────────────────────────────────────────────────────────────

class TushareFetcher(BaseDataFetcher):
    """
    Tushare Pro API 数据获取器
    需要注册 https://tushare.pro 注册获取 token
    积分≥120 才能调用大部分数据接口
    """

    def __init__(self, token: str = ""):
        import os as _os
        self.token = token or _os.environ.get("TUSHARE_TOKEN", "")

    def _get_token(self) -> str:
        if self.token:
            return self.token
        try:
            from config.settings import CONFIG
            return CONFIG.data_source.tushare_token
        except Exception:
            return ""

    def normalize_symbol(self, symbol: str) -> str:
        s = symbol.upper().strip()
        if "." in s:
            return s
        if s.startswith("6"):
            return f"{s}.SH"
        elif s.startswith(("0", "3")):
            return f"{s}.SZ"
        return s

    def get_bars(self, symbol: str, start: date, end: date,
                 freq: str = "1D") -> dict:
        sym = self.normalize_symbol(symbol)
        token = self._get_token()
        if not token:
            print("[TushareFetcher] No token, falling back to MockFetcher")
            seed_map = {"000001": 42, "600000": 137, "000300": 1, "000016": 256, "399006": 999}
            seed = seed_map.get(sym.split(".")[0], hash(sym) % 9999)
            return MockFetcher(seed=seed).get_bars(symbol, start, end, freq)
        try:
            import tushare as ts
            pro = ts.pro_api(token)
            df = pro.daily(
                ts_code=sym,
                start_date=start.strftime("%Y%m%d"),
                end_date=end.strftime("%Y%m%d"),
            )
            if df is None or df.empty:
                return {}
            df = df.sort_values("trade_date")
            return {
                "open":   df["open"].tolist(),
                "high":   df["high"].tolist(),
                "low":    df["low"].tolist(),
                "close":  df["close"].tolist(),
                "volume": [int(v) for v in df["vol"].tolist()],
            }
        except Exception as e:
            print(f"[TushareFetcher] {sym} failed: {e}, falling back to MockFetcher")
            seed_map = {"000001": 42, "600000": 137, "000300": 1, "000016": 256, "399006": 999}
            seed = seed_map.get(sym.split(".")[0], hash(sym) % 9999)
            return MockFetcher(seed=seed).get_bars(symbol, start, end, freq)


# ─────────────────────────────────────────────────────────────────────────────
# 数据管理器（工厂模式）
# ─────────────────────────────────────────────────────────────────────────────

class DataManager:
    """
    数据管理器 - 统一入口，按配置或参数选择数据源

    用法:
        # 方式1: 读取全局配置
        mgr = DataManager()
        bars = mgr.get_bars("000001", date(2025,1,1), date(2025,7,1))

        # 方式2: 覆盖全局配置，指定数据源
        mgr = DataManager(source="baostock")
        bars = mgr.get_bars("000001", date(2025,1,1), date(2025,7,1))

        # 方式3: 直接注入 fetcher 实例（用于测试）
        mgr = DataManager(fetcher=MockFetcher(seed=42))
    """

    # 数据源 → 类 映射表
    FETCHER_MAP = {
        "mock":      MockFetcher,
        "akshare":   AKShareFetcher,
        "baostock":  BaostockFetcher,
        "tushare":   TushareFetcher,
    }

    def __init__(self, source: Optional[str] = None,
                 fetcher: Optional[BaseDataFetcher] = None):
        if fetcher is not None:
            self.fetcher = fetcher
            self.source = "custom"
        else:
            self.source = source or self._get_default_source()
            self.fetcher = self._create_fetcher(self.source)

    @staticmethod
    def _get_default_source() -> str:
        try:
            from config.settings import CONFIG
            return CONFIG.data_source.source
        except Exception:
            return "mock"

    def _create_fetcher(self, source: str) -> BaseDataFetcher:
        cls = self.FETCHER_MAP.get(source)
        if cls is None:
            print(f"[DataManager] Unknown source '{source}', "
                  f"available: {list(self.FETCHER_MAP.keys())}, using mock")
            cls = MockFetcher
        try:
            return cls()
        except Exception as e:
            print(f"[DataManager] Init {cls.__name__} failed: {e}, using MockFetcher")
            return MockFetcher()

    def get_bars(self, symbol: str, start: date, end: date,
                 freq: str = "1D") -> dict:
        bars = self.fetcher.get_bars(symbol, start, end, freq)
        if not bars or not bars.get("close") or len(bars["close"]) < 2:
            return {}
        return bars

    def set_source(self, source: str):
        """运行时切换数据源"""
        self.source = source
        self.fetcher = self._create_fetcher(source)
