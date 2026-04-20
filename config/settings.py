# -*- coding: utf-8 -*-
"""
AlphaPredator 全局配置
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class AlphaConfig:
    """Alpha信号配置"""
    vwap_window: int = 20          # VWAP计算窗口（分钟）
    vol_zscore_threshold: float = 2.0  # 成交量Z-score阈值
    order_flow_short: int = 5      # 订单流短期窗口
    order_flow_long: int = 20      # 订单流长期窗口
    sentiment_threshold: float = 0.6  # 情绪极值阈值


@dataclass
class AntiQuantConfig:
    """反量化机制配置"""
    high_freq_window: int = 50     # 高频检测窗口（秒）
    tick_density_threshold: float = 0.8  # 分时成交密度阈值
    trailing_stop_pct: float = 0.10  # 追踪止损回撤比例
    iv_low_threshold: float = 20.0   # 低隐波率阈值（买入对冲）
    iv_high_threshold: float = 50.0  # 高隐波率阈值（卖出对冲）
    cash_reserve_ratio: float = 0.30  # 现金预留比例


@dataclass
class RiskConfig:
    """风控配置"""
    max_single_position: float = 0.03  # 单笔仓位上限（占总资金%）
    max_industry_exposure: float = 0.15  # 单行业上限
    max_portfolio_var_95: float = 0.05  # 组合VaR上限（95%）
    max_portfolio_var_99: float = 0.10  # 组合VaR上限（99%）
    kelly_fraction: float = 0.5     # 凯利公式保守系数
    circuit_breaker_pct: float = 0.07  # 熔断阈值（大盘涨跌%）
    stop_loss_pct: float = 0.05    # 固定止损比例


@dataclass
class ExecutionConfig:
    """执行配置"""
    algorithm: str = "twap"        # 执行算法: twap/vwap/pov
    max_order_size: int = 10000    # 单笔最大股数
    slice_interval: int = 60      # 分片间隔（秒）
    min_order_interval: int = 5    # 最小下单间隔（秒）
    target_pov: float = 0.05       # POV目标成交量比例
    slippage_bps: float = 5.0      # 预期滑点（基点）


@dataclass
class BacktestConfig:
    """回测配置"""
    start_date: str = "2025-01-01"
    end_date: str = "2026-01-01"
    initial_capital: float = 1_000_000.0  # 初始资金100万
    commission_rate: float = 0.0003   # 手续费万三
    stamp_tax: float = 0.001         # 印花税千一（卖出）
    data_freq: str = "1min"         # 数据频率


@dataclass
class GlobalConfig:
    """全局配置"""
    alpha: AlphaConfig = field(default_factory=AlphaConfig)
    anti_quant: AntiQuantConfig = field(default_factory=AntiQuantConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    backtest: BacktestConfig = field(default_factory=BacktestConfig)

    # 数据源配置
    data_source: str = "akshare"     # akshare / tushare / custom
    alternative_source: str = "jomics"  # 舆情数据源

    # 日志级别
    log_level: str = "INFO"

    def to_dict(self) -> Dict:
        """序列化配置"""
        return {
            "alpha": self.alpha.__dict__,
            "anti_quant": self.anti_quant.__dict__,
            "risk": self.risk.__dict__,
            "execution": self.execution.__dict__,
            "backtest": self.backtest.__dict__,
        }


# 全局单例
CONFIG = GlobalConfig()
