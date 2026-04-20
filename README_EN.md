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
