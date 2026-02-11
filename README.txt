# RBot-Pro - MEXC Trading System

## Overview
RBot-Pro is a real-time cryptocurrency trading system that connects to MEXC exchange, analyzes market data, and identifies high-confidence trading opportunities.

## Features
- Real-time price monitoring
- Technical analysis (RSI, EMA, Support/Resistance)
- Automatic trade tracking
- High-confidence trade alerts
- Risk management (2:1 minimum R:R ratio)
- Multiple timeframe analysis (1m, 5m, 15m, 30m, 1h)

## Requirements
- Python 3.10 or higher
- requests library

## Installation

### 1. Install Python
Download and install Python 3.10+ from https://python.org

### 2. Install Dependencies
```bash
pip install requests
```

### 3. Extract RBot-Pro
Extract RBot-Pro.zip to your desired location, for example:
```
C:\Users\[YourName]\.openclaw\workspace\rbot-pro
```

## Running the System

### Quick Update (Manual)
```bash
cd C:\Users\[YourName]\.openclaw\workspace\rbot-pro
python final_update.py
```

### Fast Update
```bash
python fast_complete.py
```

### Auto Loop (Runs every 60 seconds)
```batch
auto_update.bat
```

### Create Auto Loop
```batch
@echo off
:loop
python final_update.py
timeout /t 60 /nobreak >nul
goto loop
```

## Files Description

| File | Purpose |
|------|----------|
| `final_update.py` | Complete trading system with all features |
| `fast_complete.py` | Faster version for quick updates |
| `auto_trading.py` | Automatic trading system |
| `my_trades.json` | Stores your active trades |
| `realtime.py` | Real-time price monitoring |

## Trade Setup Format

When you receive a trade alert, it includes:

```
>>> LONG BTC @ 10x [5m - SCALPING] | R:R 15:1
============================================
ENTRY TYPE:   LIMIT
ENTRY PRICE:  $68,500
STOP LOSS:    $68,200 (0.44%)
TAKE PROFIT 1: $68,800 (0.44%) <- First Target (1R)
TAKE PROFIT 2: $69,500 <- Final Target (15x R)
LEVERAGE:     10x
EXPECTED:     ~15 minutes

TECHNICAL ANALYSIS:
  RSI: 28.5
  Current Price: $68,650

WHY THIS TRADE:
  - RSI oversold (28)
  - EMA bullish crossover
  - Near strong support
```

## Trade Actions

### Entry Types
- **LIMIT**: Place order at specific price (recommended)
- **MARKET**: Execute immediately at current price

### Risk Management
- Always use STOP LOSS
- Minimum 2:1 Risk/Reward ratio
- Never risk more than 1-2% per trade

### Take Profits
- **TP1**: First target (1R profit)
- **TP2**: Final target (2-3x R profit)

## Cron Job (Auto Updates)

To set up automatic WhatsApp updates every minute:

```bash
openclaw cron add --name "MEXC Update" --every 60000 --message "Run final_update.py" --channel whatsapp
```

## Supported Exchanges
- MEXC (primary)

## Supported Coins
50+ major cryptocurrencies including:
BTC, ETH, SOL, BNB, XRP, ADA, DOGE, LTC, LINK, UNI, DOT, MATIC, ATOM, NEAR, ARB, OP, INJ, SEI, SUI, TON, TRX, and more...

## Timeframes
- 1m: Scalping (15 min hold)
- 3m: Scalping (30 min hold)
- 5m: Short-term (60 min hold)
- 15m: Swing (3 hour hold)
- 30m: Swing (6 hour hold)
- 1h: Long-term (12+ hour hold)

## Disclaimer
This software is for educational purposes only. Trading cryptocurrencies involves substantial risk of loss. Always do your own research and never trade more than you can afford to lose.

## Author
Created for cryptocurrency trading automation and education.

## Version
1.0 - February 2026
