# -*- coding: utf-8 -*-
"""
市场配置文件
"""
from __future__ import annotations

MARKETS = {
    # A股主要指数
    "sh000001": {"name": "上证指数", "market": "SH", "type": "index"},
    "sz399001": {"name": "深证成指", "market": "SZ", "type": "index"},
    "sh000300": {"name": "沪深300", "market": "SH", "type": "index"},

    # 商品期货
    "SHFE.rb": {"name": "螺纹钢", "market": "SHFE", "type": "futures"},
    "DCE.m": {"name": "豆粕", "market": "DCE", "type": "futures"},
    "CZCE.MA": {"name": "甲醇", "market": "CZCE", "type": "futures"},

    # 数字货币
    "BTC.USDT": {"name": "比特币", "market": "BINANCE", "type": "crypto"},
}

# 各市场的交易时间（北京时间）
TRADING_HOURS = {
    "SH": {  # A股
        "morning": ("09:30", "11:30"),
        "afternoon": ("13:00", "15:00"),
    },
    "SHFE": {  # 国内期货
        "night1": ("21:00", "23:00"),
        "morning": ("09:00", "10:15"),
        "morning2": ("10:30", "11:30"),
        "afternoon": ("13:30", "15:00"),
    },
    "BINANCE": {  # 币安（24小时）
        "always": ("00:00", "23:59"),
    },
}

# 交易所接口配置
EXCHANGE_CONFIG = {
    "ctp": {
        "broker_id": "9999",
        "front": ["tcp://127.0.0.1:41205"],
    },
    "sopt": {
        "enabled": True,
    },
}

# 股票行业分类（申万一级）
INDUSTRIES = [
    "银行", "非银金融", "房地产", "医药生物", "电子",
    "计算机", "传媒", "通信", "食品饮料", "家用电器",
    "汽车", "机械设备", "电气设备", "化工", "建筑材料",
    "建筑装饰", "交通运输", "农林牧渔", "商贸零售", "纺织服装",
]

# 高频量化重仓股（用于反量化监控）
QUANT_HEAVY_STOCKS = [
    "000001", "000002", "600036", "600519", "601318",
    "601398", "601939", "600000", "000858", "601166",
]
