# -*- coding: utf-8 -*-
"""
另类数据模块：新闻、舆情、社交媒体情绪分析
"""
from __future__ import annotations

import re
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """
    简单的情绪分析器（基于规则 + 关键词）
    生产环境可替换为 LLM 或专业情绪API（如 JOMICS、AKShare舆情）
    """

    # 正面词汇
    POSITIVE_WORDS = {
        "涨停", "暴涨", "大幅上涨", "突破", "创新高", "业绩增长",
        "超预期", "增持", "买入", "看好", "利润增长", "订单大增",
        "分红", "回购", "战略合作", "中标", "政策利好", "行业景气",
    }

    # 负面词汇
    NEGATIVE_WORDS = {
        "跌停", "暴跌", "大幅下跌", "破位", "创新低", "业绩下滑",
        "不及预期", "减持", "卖出", "看空", "利润下降", "订单减少",
        "亏损", "商誉减值", "监管问询", "处罚", "政策利空", "行业低迷",
    }

    # 极正面（强烈信号）
    STRONG_POSITIVE = {"业绩暴增", "净利润翻倍", "重大利好", "订单爆发", "国产替代"}
    # 极负面
    STRONG_NEGATIVE = {"业绩暴雷", "净利润腰斩", "重大利空", "财务造假", "退市风险"}

    def __init__(self, threshold: float = 0.6):
        self.threshold = threshold

    def score_sentiment(self, text: str) -> Tuple[float, str]:
        """
        评估文本情绪

        Returns:
            (score, label): score ∈ [-1, 1], label ∈ {bullish, bearish, neutral}
        """
        text = text.lower()
        pos_count = sum(1 for w in self.POSITIVE_WORDS if w in text)
        neg_count = sum(1 for w in self.NEGATIVE_WORDS if w in text)
        strong_pos = sum(2 for w in self.STRONG_POSITIVE if w in text)
        strong_neg = sum(2 for w in self.STRONG_NEGATIVE if w in text)

        pos_count += strong_pos
        neg_count += strong_neg

        total = pos_count + neg_count
        if total == 0:
            return 0.0, "neutral"

        score = (pos_count - neg_count) / total
        score = max(-1.0, min(1.0, score))

        if score > self.threshold:
            label = "bullish"
        elif score < -self.threshold:
            label = "bearish"
        else:
            label = "neutral"

        return score, label

    def score_news_batch(self, news_list: List[Dict]) -> pd.DataFrame:
        """
        批量评估新闻情绪

        Args:
            news_list: [{"title": str, "content": str, "pub_date": str}, ...]
        """
        records = []
        for news in news_list:
            text = f"{news.get('title', '')} {news.get('content', '')}"
            score, label = self.score_sentiment(text)
            records.append({
                "pub_date": news.get("pub_date"),
                "title": news.get("title", ""),
                "sentiment_score": score,
                "sentiment_label": label,
            })

        return pd.DataFrame(records)

    def aggregate_sentiment(
        self,
        df: pd.DataFrame,
        date_col: str = "pub_date",
        score_col: str = "sentiment_score"
    ) -> pd.Series:
        """
        按日期聚合情绪分数（用于择时）
        """
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col]).dt.date
        daily = df.groupby(date_col)[score_col].mean()
        return daily


class AlternativeDataManager:
    """
    另类数据管理器，统一获取各类非价格数据
    """

    def __init__(self):
        self.sentiment = SentimentAnalyzer()
        self._sentiment_cache: Dict[date, pd.DataFrame] = {}

    def get_news_sentiment(
        self,
        symbol: str,
        start: date,
        end: date
    ) -> pd.DataFrame:
        """
        获取某时间段内与股票相关的新闻情绪
        """
        # TODO: 接入真实新闻API（如AKShare、东方财富）
        # 目前返回模拟数据
        dates = pd.bdate_range(start, end)
        rng_seed = hash(symbol) % (2**31)
        rng = pd.np.random.default_rng(rng_seed)

        news = []
        for d in dates:
            n_articles = rng.integers(1, 5)
            for _ in range(n_articles):
                score = rng.normal(0.0, 0.4)
                score = max(-1.0, min(1.0, score))
                news.append({
                    "pub_date": d,
                    "title": f"{symbol}相关资讯",
                    "sentiment_score": score,
                })

        return pd.DataFrame(news)

    def get_market_breadth(self, date_str: str) -> Dict:
        """
        获取市场广度指标（上涨/下跌家数比）
        数据来源：AKShare 或 tushare
        """
        # 模拟数据
        return {
            "advance_decline_ratio": 1.2,
            "new_high_count": 50,
            "new_low_count": 30,
            "volume_ratio": 1.1,
        }

    def get_sector_flow(self, date_str: str) -> pd.DataFrame:
        """
        获取行业资金流向
        """
        import numpy as np
        rng = np.random.default_rng(int(datetime.now().timestamp()))

        industries = [
            "银行", "医药", "新能源", "半导体", "消费",
            "军工", "地产", "基建", "化工", "TMT",
        ]

        return pd.DataFrame({
            "industry": industries,
            "net_flow": rng.normal(0, 1e8, len(industries)),
            "pct_change": rng.normal(0, 0.02, len(industries)),
        }).sort_values("net_flow", ascending=False)
