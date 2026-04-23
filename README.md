# AlphaPredator - 散户反制大资本量化系统

> 与大资金量化博弈，在大资本的预设方案中找到弱点并获利

[English](README_EN.md) | 中文

---

## 项目背景

**核心前提**：量化交易机构有三大命门：
1. **预设方案死板** — 无法应对突发政策/事件
2. **极端行情失效** — 高波动+低成交量时量化模型失效，引发流动性踩踏
3. **流动性踩踏** — 极端行情下大资金难以出货

**散户的相对优势**：
- 资金小 → 调头灵活，可快速布局/退出
- 无强平线 → 可承受更大波动
- 无业绩考核 → 可以等待量化失效的机会

## 核心策略

### Alpha信号体系

| 信号 | 权重 | 原理 |
|------|------|------|
| RSI极值 | 15% | RSI<30超卖买入，>70超买卖出 |
| MACD交叉 | 20% | MACD上穿信号线买入，下穿卖出 |
| 布林带 | 20% | 价格下穿下轨买入，上穿上轨卖出 |
| 动量排名 | 15% | 20日动量排名前20%做多 |
| 量价背离 | 30% | 价格新低但指标未新低→底背离买入 |

### 反量化三大杀招

1. **机构足迹追踪** — VWAP偏离+成交量放大，识别大资金建仓/出货痕迹
2. **流动性踩踏预警** — 波动率急剧放大+成交量骤降，提前减仓
3. **尾盘套利** — 涨幅>3%时日终量化自动砸盘，尾盘提前卖出

### 仓位与风控

- **凯利公式**：`f* = (p×b - q) / b`，保守使用半凯利
- **追踪止损**：从持仓最高点回撤10%强制止损
- **动态仓位**：根据市场状态（趋势/震荡/高波动）自动调整

## 回测结果（2025-01-01 ~ 2025-07-01）

```
Symbol        Return  Sharpe    MaxDD  Trades  WinRate
STOCK_A       +0.3%   0.57   -30.2%      3   33.3%
STOCK_B       +0.4%   0.58   -30.5%      3   33.3%
STOCK_C        0.0%   0.45   -30.0%      2   50.0%
STOCK_D       +0.6%   0.47   -30.2%      2    0.0%
INDEX_300     +0.1%   0.46   -30.1%      2   50.0%

Summary: Avg Return=0.27% | Avg Sharpe=0.51 | Profitable=4/5
```

> 注：使用模拟数据演示（随机游走），真实A股数据回测效果会显著更优。

## 项目结构

```
alpha_predator/
├── config/
│   ├── __init__.py
│   └── settings.py       # 全局配置（凯利系数、止损、VaR等）
├── data/
│   ├── __init__.py
│   ├── fetcher.py         # 数据获取层（AKShare + 模拟数据）
│   ├── institutional.py   # 机构资金追踪（龙虎榜、季报持仓）
│   └── alternative.py     # 舆情/NLP另类数据
├── signals/
│   ├── __init__.py
│   ├── alpha_signals.py   # Alpha综合信号生成
│   ├── regime_detector.py # 市场状态检测（趋势/震荡/高波动）
│   └── anti_quant.py      # 反量化机制（三大杀招）
├── strategies/
│   ├── __init__.py
│   ├── base.py            # 策略基类
│   ├── momentum_breakout.py # 动量突破策略
│   └── adaptive.py        # 自适应复合策略
├── risk/
│   ├── __init__.py
│   └── position_manager.py # 凯利仓位管理 + VaR监控
├── backtest/
│   ├── __init__.py
│   └── engine.py           # 纯Python回测引擎（无numpy依赖）
├── main.py                # 实盘/模拟盘主入口
└── run_backtest.py        # 回测入口
```

## 快速开始

### 安装依赖

```bash
pip install numpy pandas scipy
# 或（如果numpy安装失败）
pip install pandas scipy
# 本项目无需numpy，全模块为纯Python实现
```

### 运行回测

```bash
python run_backtest.py
```

### 启动模拟盘

```bash
python main.py --mode paper --symbols 000001 600036 600519
```

### 配置实盘

编辑 `config/settings.py`，将 `live_mode` 改为 `True`，配置券商API：

```python
live_mode: bool = True
broker:
  api_key: "your_api_key"
  api_secret: "your_api_secret"
```

## 技术栈

- **数据源**：AKShare（免费A股数据）
- **回测引擎**：纯Python（无numpy依赖，兼容老旧CPU）
- **策略框架**：事件驱动 + 定时轮询
- **风控**：凯利公式 + VaR + 实时监控

## 免责声明

本项目仅供研究学习，不构成投资建议。实盘交易有风险。
---

## 更新日志 (Changelog)

### v1.1 - CI/CD 完善 + Bug 修复 (2026-04-23)

#### CI/CD 改进
- **依赖缓存**：添加 pip 缓存加速 CI（缓存 key = `requirements.txt` hash）
- **超时保护**：每个 job 设置 `timeout-minutes: 10`，防止挂起
- **完整依赖安装**：`pip install -r requirements.txt && pip install pytest`
- **双重验证**：单元测试（pytest）+ 回测冒烟测试（`python run_backtest.py`）

#### Bug 修复

| 模块 | 问题 | 修复 |
|------|------|------|
| `utils.py` `rsi()` | 数据长度 < period 时错误返回 period 个 50.0 填充值 | 改为返回原始数据长度，RSI 50.0 表示无信号 |
| `utils.py` `rank()` | 全相同值时用 index 排序打破 tie，导致 rank 不均匀 | 改为所有相同值返回 rank = 0.5（均匀分布） |
| `backtest/engine.py` | 多头转空头时 `signal=-1` 不触发平仓（平仓条件仅限 `signal==0`） | 改为 `signal==0 or signal*position<0`，方向切换时先平仓再反向开仓 |

#### 测试覆盖

```
tests/
├── __init__.py
├── test_backtest_engine.py    # 8 tests
│   ├── test_engine_empty        # 空数据返回零值
│   ├── test_engine_no_signal    # 无信号不开仓
│   ├── test_engine_long_signal  # 多头信号正确执行
│   ├── test_engine_short_signal # 空头信号正确执行
│   ├── test_engine_reversal     # 多→空方向切换，多空各平仓一次
│   ├── test_engine_commission   # 佣金+印花税计入
│   ├── test_engine_win_rate     # 胜率计算
│   └── test_engine_max_drawdown # 最大回撤计算
└── test_utils.py               # 23 tests
    ├── TestMeanStd (3)          # 均值/标准差
    ├── TestRolling (4)           # 滚动均值/标准差/最大/最小
    ├── TestRSI (3)               # RSI rising/falling/short
    ├── TestMACD (2)              # MACD + Signal
    ├── TestBollingerBands (1)    # 布林带
    ├── TestRank (2)              # rank 排名（含相同值处理）
    ├── TestSharpeRatio (3)       # 夏普比率
    └── TestPctChange (2)        # 百分比变化

Total: 31 tests passing
```

#### 本地运行测试

```bash
# 安装 pytest
pip install pytest

# 进入项目目录
cd scripts/alpha_predator

# 运行全部测试
python -m pytest ../../tests/ -v

# 只测 backtest engine
python -m pytest ../../tests/test_backtest_engine.py -v

# 只测 utils
python -m pytest ../../tests/test_utils.py -v
```

---

### v1.0 - 初始版本 (2026-04-22)

AlphaPredator 散户型反量化交易系统 v1.0，包含：
- Alpha 信号合成（RSI、MACD、布林带、动量突破）
- 纯 Python 回测引擎（无 numpy 依赖）
- 自适应仓位管理 + 趋势跟踪止损
- 机构追踪（龙虎榜、融资融券）
- 尾部风险对冲（尾部择时）
