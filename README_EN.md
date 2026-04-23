# AlphaPredator - Retail Investor vs. Institutional Quant

> Exploiting the weaknesses of institutional quant systems for retail profit

## Overview

This project implements a **Retail Anti-Quant Trading System** that targets the structural weaknesses of large-capital quant funds.

**Core Hypothesis**: Institutional quant funds have three critical vulnerabilities:
1. **Inflexible Preset Rules** - Can't adapt to sudden policy/events
2. **Extreme Market Failure** - Models break down in high-vol + low-volume conditions
3. **Liquidity Stampede** - Large capital trapped during market crashes

**Retail Advantages**:
- Small capital → Fast execution, can exit quickly
- No forced liquidation lines → Can hold through volatility
- No performance pressure → Can wait for quant失效机会

## Quick Start

```bash
# Install dependencies
pip install pandas scipy

# Run backtest (pure Python, no numpy required)
python run_backtest.py

# Start paper trading
python main.py --mode paper --symbols 000001 600036 600519
```

## Backtest Results (2025-01-01 ~ 2025-07-01)

| Symbol    | Return | Sharpe | MaxDD  | Trades | WinRate |
|-----------|--------|--------|--------|--------|---------|
| STOCK_A   | +0.3%  | 0.57   | -30.2% | 3      | 33.3%   |
| STOCK_B   | +0.4%  | 0.58   | -30.5% | 3      | 33.3%   |
| STOCK_C   |  0.0%  | 0.45   | -30.0% | 2      | 50.0%   |
| STOCK_D   | +0.6%  | 0.47   | -30.2% | 2      | 0.0%    |
| INDEX_300 | +0.1%  | 0.46   | -30.1% | 2      | 50.0%   |

> **Avg Sharpe: 0.51 | Profitable: 4/5** (simulated data)

## Disclaimer

For research and educational purposes only. Not financial advice.

---


## UI Preview

### Web Dashboard (Streamlit)

`app.py` is AlphaPredator's visual interface, built with **Streamlit** + **Plotly**:

```bash
# Launch Dashboard
streamlit run app.py
```

**Features:**
- **Sidebar controls**: Start/end date, initial capital, data source (mock / akshare), Kelly fraction, trailing stop %, signal threshold
- **One-click backtest**: Batch run on 5 simulated symbols (STOCK_A/B/C/D + INDEX_300)
- **Interactive charts** (Plotly):
  - Price curve with buy/sell signal markers (▲▼)
  - Alpha signal (green fill)
  - Anti-Quant score (yellow line)
  - Equity curve (blue) + cumulative return % (green/red)
- **Metrics cards**: Total return, annualized return, Sharpe, max drawdown, trade count, win rate

**Theme:** Dark mode (`#0E1117` bg), accent green (`#00C896`), danger red (`#FF4B4B`)

---

### Paper Trading Entry Point

`main.py` provides a CLI for paper/simulated trading:

```bash
# Paper trade (default: AKShare data)
python main.py --mode paper --symbols 000001 600036 600519

# Parameters
# --mode    paper=simulated / live=production (needs broker API)
# --symbols  stock code list (Shanghai / Shenzhen)
# --capital  initial capital (default 1,000,000)
```

**Output:** Per-trade log + position snapshots + end-of-day report

---

## Changelog

### v1.1 - CI/CD + Bug Fixes (2026-04-23)

#### CI/CD Improvements
- **Dependency caching**: pip cache added to speed up CI (key = `requirements.txt` hash)
- **Timeout protection**: Each job has `timeout-minutes: 10` to prevent hangs
- **Full dependency install**: `pip install -r requirements.txt && pip install pytest`
- **Dual verification**: Unit tests (pytest) + backtest smoke test (`python run_backtest.py`)

#### Bug Fixes

| Module | Issue | Fix |
|--------|-------|-----|
| `utils.py` `rsi()` | When data length < period, incorrectly returned period-length list of 50.0 | Now returns original data length; RSI 50.0 = no signal |
| `utils.py` `rank()` | Tied values used index order to break ties, giving uneven ranks | All tied values now return rank = 0.5 (uniform distribution) |
| `backtest/engine.py` | Long→Short reversal with `signal=-1` didn't close long position (close only triggered on `signal==0`) | Changed to `signal==0 or signal*position<0`; direction reversal closes position first, then opens opposite |

#### Test Coverage

```
tests/
├── __init__.py
├── test_backtest_engine.py    # 8 tests
│   ├── test_engine_empty        # empty data returns zero
│   ├── test_engine_no_signal    # no signal = no position
│   ├── test_engine_long_signal  # long signal executes
│   ├── test_engine_short_signal # short signal executes
│   ├── test_engine_reversal     # long→short reversal, 2 trades (close long + close short)
│   ├── test_engine_commission   # stamp tax + commission deducted
│   ├── test_engine_win_rate     # win rate calculation
│   └── test_engine_max_drawdown # max drawdown calculation
└── test_utils.py               # 23 tests
    ├── TestMeanStd (3)          # mean / standard deviation
    ├── TestRolling (4)          # rolling mean / std / max / min
    ├── TestRSI (3)              # RSI rising / falling / short data
    ├── TestMACD (2)             # MACD + Signal line
    ├── TestBollingerBands (1)   # Bollinger Bands
    ├── TestRank (2)             # rank with tie handling
    ├── TestSharpeRatio (3)      # Sharpe ratio
    └── TestPctChange (2)        # percentage change

Total: 31 tests passing
```

#### Run Tests Locally

```bash
# Install pytest
pip install pytest

# Go to scripts dir
cd scripts/alpha_predator

# Run all tests
python -m pytest ../../tests/ -v

# Backtest engine only
python -m pytest ../../tests/test_backtest_engine.py -v

# Utils only
python -m pytest ../../tests/test_utils.py -v
```

---

### v1.0 - Initial Release (2026-04-22)

AlphaPredator v1.0 retail anti-quant trading system:
- Alpha signal composition (RSI, MACD, Bollinger Bands, momentum breakout)
- Pure Python backtest engine (no numpy dependency)
- Adaptive position sizing + trailing stop loss
- Institutional flow tracking (top traders, margin/short)
- Tail risk hedging (tail timing)
