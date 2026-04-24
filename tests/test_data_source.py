# -*- coding: utf-8 -*-
"""
DataSource / DataManager 单元测试

测试新的可插拔数据源架构:
  - MockFetcher: 纯本地模拟
  - BaostockFetcher: 免费行情（网络可用时）
  - DataManager: 工厂模式，支持运行时切换数据源
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import date
from data.fetcher import (
    DataManager, MockFetcher, BaostockFetcher,
    AKShareFetcher, TushareFetcher, BaseDataFetcher,
)


class TestMockFetcher:
    """MockFetcher 基础功能测试"""

    def test_generates_valid_bars(self):
        fetcher = MockFetcher(seed=42)
        bars = fetcher.get_bars("STOCK_A", date(2025, 1, 1), date(2025, 6, 30))
        assert "close" in bars
        assert "open" in bars
        assert "high" in bars
        assert "low" in bars
        assert "volume" in bars
        assert len(bars["close"]) >= 2

    def test_reproducible_with_same_seed(self):
        f1 = MockFetcher(seed=99)
        f2 = MockFetcher(seed=99)
        b1 = f1.get_bars("X", date(2025, 1, 1), date(2025, 3, 1))
        b2 = f2.get_bars("X", date(2025, 1, 1), date(2025, 3, 1))
        assert b1["close"] == b2["close"]

    def test_different_seeds_different_data(self):
        b42 = MockFetcher(seed=42).get_bars("X", date(2025, 1, 1), date(2025, 3, 1))
        b99 = MockFetcher(seed=99).get_bars("X", date(2025, 1, 1), date(2025, 3, 1))
        assert b42["close"] != b99["close"]

    def test_short_date_range(self):
        bars = MockFetcher(seed=42).get_bars("X", date(2025, 1, 1), date(2025, 1, 3))
        assert len(bars.get("close", [])) >= 2


class TestDataManagerFactory:
    """DataManager 工厂模式测试"""

    def test_default_is_mock(self):
        mgr = DataManager()
        assert mgr.source == "mock"
        bars = mgr.get_bars("TEST", date(2025, 1, 1), date(2025, 3, 1))
        assert len(bars.get("close", [])) >= 2

    def test_explicit_mock_source(self):
        mgr = DataManager(source="mock")
        assert mgr.source == "mock"
        bars = mgr.get_bars("TEST", date(2025, 1, 1), date(2025, 3, 1))
        assert len(bars.get("close", [])) >= 2

    def test_baostock_source_init(self):
        # 只验证实例化不报错（网络失败会降级到mock）
        mgr = DataManager(source="baostock")
        assert mgr.source == "baostock"
        bars = mgr.get_bars("000001", date(2025, 1, 1), date(2025, 3, 1))
        # baostock网络失败时降级到mock，所以仍应有数据
        assert len(bars.get("close", [])) >= 2

    def test_akshare_source_init(self):
        mgr = DataManager(source="akshare")
        assert mgr.source == "akshare"

    def test_tushare_source_init_no_token(self):
        # 无token时降级到mock
        mgr = DataManager(source="tushare")
        bars = mgr.get_bars("000001", date(2025, 1, 1), date(2025, 3, 1))
        assert len(bars.get("close", [])) >= 2

    def test_set_source_runtime(self):
        mgr = DataManager(source="mock")
        bars1 = mgr.get_bars("X", date(2025, 1, 1), date(2025, 3, 1))
        mgr.set_source("mock")
        bars2 = mgr.get_bars("X", date(2025, 1, 1), date(2025, 3, 1))
        assert bars1["close"] == bars2["close"]

    def test_custom_fetcher_injection(self):
        # 直接注入fetcher，绕过source
        custom = MockFetcher(seed=777)
        mgr = DataManager(fetcher=custom)
        assert mgr.source == "custom"
        bars = mgr.get_bars("X", date(2025, 1, 1), date(2025, 3, 1))
        assert len(bars.get("close", [])) >= 2

    def test_unknown_source_falls_back_to_mock(self):
        mgr = DataManager(source="unknown_source_xyz")
        bars = mgr.get_bars("X", date(2025, 1, 1), date(2025, 3, 1))
        assert len(bars.get("close", [])) >= 2  # 降级到mock

    def test_fetcher_map_has_all_sources(self):
        expected = {"mock", "akshare", "baostock", "tushare"}
        assert set(DataManager.FETCHER_MAP.keys()) == expected

    def test_get_bars_returns_empty_for_invalid_dates(self):
        mgr = DataManager()
        bars = mgr.get_bars("X", date(2025, 1, 1), date(2024, 1, 1))  # start > end
        # 行为取决于MockFetcher实现，至少不应崩溃
        assert isinstance(bars, dict)
