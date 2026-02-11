<p align="center">
  <img src="https://img.shields.io/badge/RBot%20Pro-v3.0-00ff00?style=for-the-badge&logo=bitcoin&logoColor=white&labelColor=0a0a0a" alt="Version" />
  <img src="https://img.shields.io/badge/Indicators-43-00d4ff?style=for-the-badge&labelColor=0a0a0a" alt="Indicators" />
  <img src="https://img.shields.io/badge/Strategies-34-ff3e3e?style=for-the-badge&labelColor=0a0a0a" alt="Strategies" />
  <img src="https://img.shields.io/badge/Timeframes-8-ffaa00?style=for-the-badge&labelColor=0a0a0a" alt="Timeframes" />
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white&labelColor=0a0a0a" alt="Python" />
  <img src="https://img.shields.io/badge/License-Proprietary-888888?style=for-the-badge&labelColor=0a0a0a" alt="License" />
</p>

<h1 align="center">🔥 RBot Pro — Elite Crypto Trading Signal Engine</h1>

<p align="center">
  <b>The World's Most Advanced Real-Time Cryptocurrency Technical Analysis System</b><br/>
    <i>43 Indicators · 34 Strategies · 8 Timeframes · 200+ Coins · 8 Exchanges Live Data</i>
</p>

<p align="center">
    <img src="https://img.shields.io/badge/Exchanges-8%20Supported-00ff88?style=flat-square&labelColor=1a1a1a" alt="Exchanges" />
      <img src="https://img.shields.io/badge/Binance%2FMEXC-Live-ffffff?style=flat-square&labelColor=1a1a1a" alt="Binance/MEXC" />
  <img src="https://img.shields.io/badge/Bitget%2FBybit-Live-00d4ff?style=flat-square&labelColor=1a1a1a" alt="Bitget/Bybit" />
  <img src="https://img.shields.io/badge/OKX%2FKuCoin-Live-ffffff?style=flat-square&labelColor=1a1a1a" alt="OKX/KuCoin" />
    <img src="https://img.shields.io/badge/Gateio%2FHTX-Live-00d4ff?style=flat-square&labelColor=1a1a1a" alt="Gate.io/HTX" />
  <img src="https://img.shields.io/badge/ICT%20%2F%20SMC-Elite-ff3e3e?style=flat-square&labelColor=1a1a1a" alt="ICT/SMC" />
</p>

---

## 📖 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [Intelligence Suite (43)](#-elite-2026-intelligence-suite--43-indicators)
- [Strategy Core (34)](#-proprietary-strategy-core--34-power-strategies)
- [Trade Engine](#-institutional-trade-engine-architecture)
- [Installation](#-installation)
- [Usage](#-usage)
- [Web UI Guide](#-web-ui-guide)
- [Trade Signal Format](#-trade-signal-format)
- [Risk Management](#-risk-management)
- [Pricing](#-rbot-pro-pricing)
- [Competitor Comparison](#-competitor-comparison)
- [FAQ](#-faq)
- [Disclaimer](#-disclaimer)

---

## 🌟 Overview

**RBot Pro** is a professional-grade, real-time cryptocurrency technical analysis and trading signal generation system. It connects directly to **8 major exchanges** (**MEXC, Binance, Bitget, Bybit, OKX, KuCoin, Gate.io, and HTX**), fetches live candlestick (kline) data, computes **43 advanced technical indicators** across **8 timeframes**, and runs **34 proprietary trading strategies** to identify high-confidence trade setups with precise entry, stop-loss, and take-profit levels.

Fully automated quantitative analysis on **200+ coins simultaneously** in under 2 minutes, scanning for institutional-grade setups using Smart Money Concepts (SMC), ICT methodology, and classical technical analysis.

### 🏆 Why RBot Pro?

| Feature | RBot Pro | Typical Bots |
|---------|----------|--------------|
| Indicators | **43** | 5–10 |
| Strategies | **34** | 1–3 |
| Timeframes | **8** simultaneous | 1–2 |
| Coins scanned | **200+** concurrent | 5–20 |
| ICT / SMC concepts | ✅ Full support | ❌ None |
| Kill Zone detection | ✅ London, NY, Asia | ❌ |
| Real-time Web UI | ✅ WebSocket streaming | ❌ CLI only |
| Visual Analysis Charts | ✅ **Integrated TradingView** | ❌ Text-only / External |
| Custom coin addition | ✅ Add any USDT pair | ❌ Fixed lists |
| Data source | Live data from 8 Exchanges | Delayed / single source |
| Codebase size | **4,100+ lines** of pure analysis logic | <500 lines |
| News & Sentiment | ✅ **Real-time Feed + AI Analysis** | ❌ None |
| Volatility Protection | ✅ **Flash Crash Protection** | ❌ None |

---

## 🚀 Key Features

### 📡 Live Data Pipeline
- **Multi-Exchange Hub**: Integrated with **MEXC, Binance, Bitget, Bybit, OKX, KuCoin, Gate.io, and HTX**.
- **Smart Fallback**: Optimized fetching with automatic failover across exchanges for maximum uptime.
- **Top 200 coins** fetched by 24h volume, sorted and deduplicated
- **Multi-threaded fetching** — up to 10 parallel data streams

### 💻 Professional Web UI
- **Dark terminal-style interface** with green-on-black aesthetic
- **Live WebSocket streaming** — real-time output as analysis runs
- **Trade Signal Cards** — beautifully rendered with entry/SL/TP/R:R and copy-to-clipboard
- **Symbol search & filter** — instantly find any coin
- **Add custom coins** — type any coin pair (e.g. `NMRUSDT`) and add it to the analysis
- **Select/Deselect All** buttons for coins, indicators, and timeframes
- **Confidence slider** — adjust minimum confidence threshold (1–10)
- **Auto-Run scheduling** — automatic re-analysis every 10s, 30s, 45s, 1m, 3m, 5m, 10m, or 15m
- **Visual Analysis Charts** — Full TradingView integration! Click "View Analysis" to see real-time candles with Entry, SL, TP, and indicator markers (FVG, MB, Squeeze, etc.) drawn directly on the chart.
- **Keyboard shortcuts** — `Ctrl+Enter` to start, `Ctrl+L` to clear
- **Responsive design** — works on desktop, tablet, and mobile

### ⚡ Performance
- **Concurrent analysis** — `ThreadPoolExecutor` with up to 10 workers
- **Thread-safe output** — `print_lock` prevents garbled console output
- **Queue-based streaming** — reliable WebSocket delivery via `queue.Queue`
- **UTF-8 everywhere** — full emoji and Unicode support on all platforms

### 🛑 Stop Control
- **Instant process termination** — kills entire process tree on Windows (`taskkill /F /T`)
- **Clean state reset** — properly resets UI buttons, status indicator, and timer
- **No zombie processes** — guaranteed cleanup via `try/finally`

### 📰 Market Intelligence & Volatility Protection (NEW)
- **Live Crypto News Feed** — Fetches real-time market news from top sources every 5 seconds.
- **AI Sentiment Analysis** — Auto-analyzes news headers to determine **Bullish** 🚀 / **Bearish** 🐻 / **Neutral** 😐 market sentiment.
- **Flash Volatility Scanner** — Monitors BTC price tick-by-tick. If a sudden pump or dump (>0.3% in 30s) is detected, a **RED WARNING BANNER** appears to protect you from entering bad trades.
- **Safe-Trade Protocol** — All trade signals generated during high volatility events are automatically tagged with a warning.

---

## 📊 Elite 2026 Intelligence Suite — 43 Indicators

RBot Pro computes **43 technical indicators** on every timeframe for every coin. Each indicator is implemented from scratch in pure Python with zero external TA library dependencies.

### 🚀 SuperScalp 2026 Scalping Suite (5)

| # | Indicator | Code | Description | Advantage |
|---|-----------|------|-------------|-----------|
| 1 | **Parabolic SAR** | `PSAR` | Parabolic Stop and Reverse for trend trailing | Perfect for 1m/3m trend reversals |
| 2 | **Triple EMA (TEMA)** | `TEMA` | Triple Exponential Moving Average with zero lag | Fastest MA for high-speed scalping |
| 3 | **Chandelier Exit** | `CHANDELIER` | Volatility-based trailing stop derived from ATR | Keeps you in winning trades longer |
| 4 | **Kaufman Adaptive MA** | `KAMA` | Adaptive MA that filters out market noise | Noise-free trend detection in 5m charts |
| 5 | **Volume Flow Indicator** | `VFI` | Advanced volume-based trend follower | Detects heavy institutional accumulation |

### 🔥 Elite 2026 Indicators (13)

| # | Indicator | Code | Description | Key Levels |
|---|-----------|------|-------------|------------|
| 1 | **Choppiness Index** | `CHOP` | Measures if market is trending or choppy (range-bound) | <38.2 = Trending, >61.8 = Choppy |
| 2 | **Vortex Indicator** | `VI` | Identifies trend direction via VI+ and VI- crossovers | VI+ > VI- = Bullish, VI- > VI+ = Bearish |
| 3 | **Schaff Trend Cycle** | `STC` | Combines MACD + Stochastic for earlier trend signals | >75 = Overbought, <25 = Oversold |
| 4 | **Donchian Channels** | `DON` | 20-period high/low channels for breakout detection | Upper = Resistance, Lower = Support |
| 5 | **SMC CHoCH** | `CHoCH` | Smart Money Change of Character — detects trend reversals | Bullish CHoCH = Downtrend break, Bearish = Uptrend break |
| 6 | **Keltner Channels** | `KC` | ATR-based volatility channels for mean reversion | Upper/Lower bands = Overbought/Oversold |
| 7 | **UT Bot Alerts** | `UTBOT` | ATR trailing stop system with BUY/SELL signals | Signal = BUY/SELL/NEUTRAL, Stop = trailing level |
| 8 | **Ultimate Oscillator** | `UO` | Multi-timeframe momentum (7, 14, 28 periods combined) | >70 = Overbought, <30 = Oversold |
| 9 | **Standard Deviation** | `STDEV` | Price volatility measurement for squeeze detection | High = Volatile, Low = Consolidation |
| 10 | **Volume Profile** | `VP` | Volume-at-price histogram with Point of Control (POC) | POC = Highest volume price level |
| 11 | **Supply/Demand Zones** | `SUPDEM` | Institutional supply/demand zones from volume clusters | Demand = Buy zone, Supply = Sell zone |
| 12 | **Fibonacci Retracement** | `FIB` | Auto-calculated Fibonacci levels (0.236, 0.382, 0.5, 0.618, 0.786) | Golden ratio levels for S/R |
| 13 | **ICT Wealth Division** | `ICT_WD` | Institutional phase detection (Accumulation, Markup, Distribution, Markdown) | Phase = current market cycle stage |

### 📈 Standard Indicators (25)

| # | Indicator | Code | Description | Parameters |
|---|-----------|------|-------------|------------|
| 14 | **RSI** | `RSI` | Relative Strength Index — momentum oscillator | Period: 14 |
| 15 | **EMA** | `EMA` | Exponential Moving Averages (9, 21, 50, 200) | Periods: 9, 21, 50, 200 |
| 16 | **MACD** | `MACD` | Moving Average Convergence Divergence — trend momentum | Fast: 12, Slow: 26, Signal: 9 |
| 17 | **Bollinger Bands** | `BB` | Volatility bands around a moving average | Period: 20, Deviation: 2σ |
| 18 | **ATR** | `ATR` | Average True Range — volatility in price units | Period: 14 |
| 19 | **ADX** | `ADX` | Average Directional Index — trend strength with DI+/DI- | Period: 14, Strong: >25 |
| 20 | **Order Blocks** | `OB` | Institutional order block detection (bullish + bearish) | Lookback: 15 candles |
| 21 | **Price Action** | `PA` | Candlestick pattern recognition (engulfing, reversals, HH/HL, LL/LH) | Last 5 candles |
| 22 | **Stochastic RSI** | `StochRSI` | RSI of RSI — ultra-sensitive momentum | K: 3, D: 3, Length: 14 |
| 23 | **OBV** | `OBV` | On-Balance Volume — volume-confirms-price indicator | Bullish/Bearish trend |
| 24 | **SuperTrend** | `ST` | ATR-based trend-following overlay | Period: 10, Multiplier: 3 |
| 25 | **VWAP** | `VWAP` | Volume-Weighted Average Price — intraday fair value | Anchored to session |
| 26 | **HMA** | `HMA` | Hull Moving Average — low-lag trend line | Period: 21 |
| 27 | **CMF** | `CMF` | Chaikin Money Flow — buying/selling pressure | Period: 20 |
| 28 | **Ichimoku Cloud** | `ICHI` | Full Ichimoku Kinkō Hyō (Tenkan, Kijun, Cloud) | Tenkan: 9, Kijun: 26, Senkou: 52 |
| 29 | **Fair Value Gap** | `FVG` | SMC Fair Value Gap detection (bullish + bearish) | Last 3 candles |
| 30 | **RSI Divergence** | `DIV` | Bullish/Bearish RSI divergence detection | Series analysis |
| 31 | **WaveTrend** | `WT` | LazyBear's WaveTrend Oscillator (WT1/WT2) | Channel: 10, Average: 21 |
| 32 | **TTM Squeeze** | `SQZ` | Bollinger-inside-Keltner squeeze + momentum release | BB: 20/2, KC: 20/1.5 |
| 33 | **Liquidity Sweep** | `LIQ` | Detects liquidation hunts (SMC concept) | Lookback: 30 candles |
| 34 | **Break of Structure** | `BOS` | Market structure shift detection (bullish/bearish BOS) | Lookback: 20 candles |
| 35 | **Money Flow Index** | `MFI` | Volume-weighted RSI (buying/selling pressure) | Period: 14 |
| 36 | **Fisher Transform** | `FISH` | Normalizes price to Gaussian distribution for turning points | Period: 10 |
| 37 | **Zero-Lag SMA** | `ZLSMA` | Lag-free moving average for fast scalping | Period: 32 |
| 38 | **True Strength Index** | `TSI` | Deep double-smoothed momentum oscillator | Long: 25, Short: 13 |

### 📐 Derived Calculations

In addition to the 38 core indicators, the engine also computes:

- **Trend Direction** — Bullish / Bearish / Neutral (via EMA stack: EMA9 > EMA21 > EMA50)
- **Trend Strength** — Weak / Strong / Very Strong (via ADX + SuperTrend alignment)
- **Support & Resistance** — Dynamic 20-period high/low levels
- **Relative Volume (RVOL)** — Current volume vs. 20-period average
- **Hull Suite Signal** — Trend change detection via Hull MA comparison

---

## 🎯 Proprietary Strategy Core — 34 Power Strategies

Every strategy produces trade signals with precise **Entry**, **Stop Loss**, **TP1**, **TP2**, **Risk/Reward Ratio**, **Confidence Score (1–10)**, and **Expected Resolution Time**.

### ⚔️ Core Strategies (7)

| # | Strategy | Function | Timeframe | Style | Description |
|---|----------|----------|-----------|-------|-------------|
| 1 | **Swing Trend** | `strategy_swing_trend` | 1h + 4h | Swing | Multi-timeframe trend alignment with EMA/RSI/ADX/SuperTrend confluence. Requires 1h + 4h agreement. |
| 2 | **Scalp Momentum** | `strategy_scalp_momentum` | 1m + 5m | Scalp | Ultra-fast momentum scalping on lower timeframes with RSI/EMA/MACD confirmation. |
| 3 | **Trend Pullback** | `strategy_trend_pullback` | 5m / 15m | Pullback | Stochastic RSI oversold/overbought cross within a confirmed trend (ADX > 20). |
| 4 | **Volatility Breakout** | `strategy_volatility_breakout` | 15m / 1h | Breakout | Bollinger Band squeeze breakout with ADX directional confirmation. |
| 5 | **SuperTrend Follow** | `strategy_supertrend_follow` | 5m / 15m | Trend | SuperTrend rebound entries with EMA alignment and VWAP confirmation. |
| 6 | **VWAP Reversion** | `strategy_vwap_reversion` | 5m / 15m | Mean Reversion | Price deviation from VWAP with RSI extremes for mean reversion scalps. |
| 7 | **Ichimoku TK Cross** | `strategy_ichimoku_tk` | 1h / 4h | Trend | Tenkan-Kijun cross above/below the Kumo cloud with trend confirmation. |

### 🧠 Advanced / SMC Strategies (11)

| # | Strategy | Function | Timeframe | Style | Description |
|---|----------|----------|-----------|-------|-------------|
| 8 | **FVG Gap Fill** | `strategy_fvg_gap_fill` | 5m / 15m | SMC | Fair Value Gap re-entry strategy with trend alignment. |
| 9 | **Divergence Pro** | `strategy_divergence_pro` | 15m / 1h | Reversal | RSI bullish/bearish divergence with OBV and trend confirmation. |
| 10 | **ADX Momentum** | `strategy_adx_momentum` | 15m / 1h | Momentum | DI+ / DI- crossover with strong ADX (>25) for directional momentum trades. |
| 11 | **Bollinger Reversion** | `strategy_bollinger_reversion` | 15m / 1h | Mean Reversion | Price touching lower/upper Bollinger Band with RSI extreme confirmation. |
| 12 | **Liquidity Grab Reversal** | `strategy_liquidity_grab_reversal` | 5m / 15m | SMC | Detects liquidity sweeps (stop hunts) and enters on the reversal. |
| 13 | **WaveTrend Extreme** | `strategy_wavetrend_extreme` | 5m / 15m | Reversal | WaveTrend WT1/WT2 at extreme oversold/overbought levels. |
| 14 | **Squeeze Breakout** | `strategy_squeeze_breakout` | 15m / 1h | Breakout | TTM Squeeze release with momentum direction and trend alignment. |
| 15 | **ZLSMA Fast Scalp** | `strategy_zlsma_fast_scalp` | 1m / 5m | Scalp | Zero-Lag SMA crossover with RSI for ultra-fast scalping entries. |
| 16 | **MFI Reversion** | `strategy_mfi_reversion` | 5m / 15m | Mean Reversion | Money Flow Index exhaustion (MFI < 20 or > 80) with reversal confirmation. |
| 17 | **Fisher Pivot** | `strategy_fisher_transform_pivot` | 5m / 15m | Reversal | Fisher Transform sign change for early pivot detection. |
| 18 | **Volume Spike Breakout** | `strategy_volume_spike_breakout` | 5m / 15m | Breakout | Extreme relative volume (RVOL > 3x) with price action breakout. |

### 🏅 Elite 2026 Strategies (10)

| # | Strategy | Function | Timeframe | Style | Description |
|---|----------|----------|-----------|-------|-------------|
| 19 | **SMC CHoCH** | `strategy_smc_choch` | 15m / 1h | SMC Reversal | Change of Character detection — identifies exact trend reversal points using market structure. |
| 20 | **Donchian Breakout** | `strategy_donchian_breakout` | 1h / 4h | Trend | 20-period Donchian Channel breakout with Choppiness Index trending confirmation. |
| 21 | **STC Momentum** | `strategy_stc_momentum` | 5m / 15m | Momentum | Schaff Trend Cycle bullish momentum release with RSI and trend alignment. |
| 22 | **Vortex Trend** | `strategy_vortex_trend` | 1h / 4h | Trend | Vortex VI+ > VI- crossover with Choppiness confirmation for strong trends. |
| 23 | **ICT Silver Bullet** | `strategy_ict_silver_bullet` | 5m / 15m | ICT | Fair Value Gap play during specific Kill Zones (London 07–10 UTC, New York 13–16 UTC, Asia 01–04 UTC). |
| 24 | **UT Bot Elite** | `strategy_utbot_elite` | 5m / 15m / 1h | Trend | UT Bot trailing stop BUY/SELL signal combined with STC momentum confirmation. |
| 25 | **Keltner Reversion** | `strategy_keltner_reversion` | 15m / 1h | Mean Reversion | Price below lower Keltner Channel band with RSI and StochRSI oversold confluence. |
| 26 | **Volatility Capitulation** | `strategy_volatility_capitulation` | 15m / 1h | Reversal | Panic selling detection (Price < Lower BB + RSI < 25 + ADX > 30) for contrarian entries. |
| 27 | **Momentum Confluence** | `strategy_momentum_confluence` | 5m / 15m | Confluence | Multi-indicator scoring system (RSI + MACD + StochRSI + ADX + EMA) — requires 4/5 alignment. |
| 28 | **ICT Wealth Division** | `strategy_ict_wealth_division` | 1h / 15m | ICT | Institutional phase detection (Accumulation → Markup → Distribution → Markdown) for early entries. |
| 29 | **Harmonic Gartley** | `strategy_harmonic_gartley` | 1h / 4h | Harmonic | Simplified Gartley 61.8%–78.6% Fibonacci retracement entries in trend direction. |
| 30 | **SMC Elite (MB+FVG)** | `strategy_smc_elite` | 5m-1h | SMC Elite | Premium fusion of Mitigation Blocks and Fair Value Gaps for high-probability institutional entries. |
| 31 | **Harmonic Pro Scanner** | `strategy_harmonic_pro` | 1h / 4h | Harmonic Pro | Full XABCD geometric verification for Gartley and Bat patterns with ultra-precise Fibonacci ratios. |

### 🚀 SuperScalp 2026 Strategies (3)

| # | Strategy | Function | Timeframe | Style | Description |
|---|----------|----------|-----------|-------|-------------|
| 32 | **PSAR-TEMA Scalp** | `strategy_psar_tema_scalp` | 1m / 3m | Scalp | PSAR-confirmed trend follow-through with TEMA-based fast entry alignment. |
| 33 | **KAMA-Vol Scalp** | `strategy_kama_volatility_scalp` | 3m / 5m | Scalp | Adaptive KAMA trend combined with Chandelier Exit for ultra-reliable volatility scalping. |
| 34 | **VFI Perfect Scalper** | `strategy_vfi_momentum_scalp` | 1m / 5m | Scalp | THE "PERFECT" SCALPER: Multi-indicator confluence (VFI + RSI + UO + ZLSMA) for institutional-grade accuracy. |

### 🏗️ Institutional Trade Engine (Architecture)

```
┌──────────────────────────────────────────────────────────────────────┐
│                        RBot Pro v3.0 Architecture                     │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────┐    ┌──────────────┐    ┌────────────────────────┐   │
│  │ 8 Live Exchanges │───▶│  Data Layer  │───▶│  Indicator Engine (43) │   │
│  │ MEXC, Binance,   │    │  get_klines  │    │  RSI, MACD, BB, ADX,  │   │
│  │ Bybit, Bitget,   │    │  200 candles  │    │  PSAR, TEMA, KAMA, ...│   │
│  │ OKX, KuCoin,     │    │  per TF       │    │  Ichimoku, FVG, ...   │   │
│  │ Gate.io, HTX     │    └──────┬───────┘    └───────────┬────────────┘   │
│  └─────────────────┘            │                        │               │
│                                 ▼                        ▼               │
│                        ┌────────────────┐    ┌────────────────────────┐   │
│                        │ Multi-Exchange │    │  Strategy Engine (34)  │   │
│                        │ Fallback Hub   │    │  Swing, Scalp, SMC,   │   │
│                        └────────────────┘    │  ICT, PSAR-TEMA, ...  │   │
│                                              └───────────┬────────────┘   │
│                                                          │               │
│                                                          ▼               │
│  ┌─────────────┐    ┌──────────────┐    ┌────────────────────────┐   │
│  │  Browser UI  │◀──│  WebSocket   │◀──│  Signal Generator      │   │
│  │  (Socket.IO) │    │  Streaming   │    │  Entry/SL/TP/R:R     │   │
│  └─────────────┘    └──────────────┘    └────────────────────────┘   │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │              RBot Pro Intelligent Control Hub (Local)             │ │
│  │      Institutional Trade Engine · Live WebSocket Sync · Multi-TF   │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```


---

## 📥 Installation

### Prerequisites

- **Python 3.10+** — [Download](https://python.org)
- **pip** — comes with Python
- Internet connection for live market data

### Step 1: Clone / Extract

```bash
# Extract or clone to your desired location
cd "D:\Documents\RBot-Pro"
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

Required packages:
```
flask
flask-socketio
requests
apscheduler
```

### Step 3: Launch

```bash
python web_ui_server.py
```

Open your browser: **http://localhost:5000**

---

## 🎮 Usage

### Web UI (Recommended)

```bash
python web_ui_server.py
# Open http://localhost:5000 in your browser
```


---

## 🖥️ Web UI Guide

### Layout

| Section | Location | Purpose |
|---------|----------|---------|
| **Header** | Top bar | Title + connection status indicator |
| **Sidebar** | Left panel | All configuration controls |
| **Live Terminal** | Center top | Real-time streaming analysis output |
| **Trade Signals** | Center bottom | Visual trade signal cards with copy button |
| **Info Panels** | Below signals | System info (timeframes, rules, strategies, data source) |

### Sidebar Controls

- **📊 Select Cryptocurrencies** — Checkbox list with search filter and custom coin addition
- **📈 Select Indicators** — All 38 indicators with Select All / Deselect All
- **⏱️ Select Timeframes** — 1m through 1d with Select All / Deselect All
- **🎯 Min Confidence** — Slider from 1 to 10
- **🤖 Auto-Run** — Toggle + interval selector (10s to 15m)
- **▶ START / ⏹ STOP / ✕ CLEAR** — Analysis control buttons
- **Stats Box** — Selected coins count, indicators count, output lines, elapsed time

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + Enter` | Start analysis |
| `Ctrl + L` | Clear terminal output |

### Adding Custom Coins

1. Type the coin name in the **"e.g. NMRUSDT"** field
2. Click **+ Add** (or press `Enter`)
3. The coin is automatically selected and ready for analysis
4. USDT is auto-appended if not included

---



---

## 📋 Trade Signal Format

Every trade signal includes:

```
┌─────────────────────────────────────────────────────────┐
│  [Strategy Name] TRADE — LONG/SHORT SYMBOL (Conf: X/10) │
├─────────────────────────────────────────────────────────┤
│  📍 Entry:       $0.014010 (MARKET/LIMIT/STOP-MARKET)    │
│  🛑 Stop Loss:   $0.014811                               │
│  🎯 TP1:         $0.012407                               │
│  🎯 TP2:         $0.010500                               │
│  💎 Risk/Reward: 2.0:1                                   │
│  ⏱  Expected:    4-12 hours                              │
│  📊 Indicators:  SQZ Release, Mom:-0.0004                │
│  🔍 Reason:      TTM Squeeze + ADX Momentum + Trend      │
│  🕒 Timestamp:   2026-02-11 10:15:32                     │
└─────────────────────────────────────────────────────────┘
```

### Copy to Clipboard Format

Each trade card has a 📋 copy button that generates a formatted message:

```
🔥 *[Squeeze Break] TRADE ALERT*
━━━━━━━━━━━━━━━━━━━━
🏢 *Exchange:* Binance
📈 *Signal:* 🔻 SELL TRIAUSDT (15m)
📍 *Entry:* $0.014010 (STOP-MARKET)
🛑 *SL:* $0.014811
🎯 *TP:* $0.012407
💎 *R/R:* 2.0:1
⏱ *Expected:* 8-24 hours
🔍 *Reason:* TTM Squeeze Downward Release + Strong ADX Momentum + Trend Alignment
━━━━━━━━━━━━━━━━━━━━
*RBot Pro 🤖 — World's Most Accurate AI Bot!* 🏆
```

---

## 🛡️ Risk Management

RBot Pro enforces strict risk management on every signal:

| Rule | Enforcement |
|------|-------------|
| **Minimum Risk/Reward** | 1.2:1 to 2:1 depending on strategy |
| **ATR-based Stop Loss** | Dynamic SL calculated from Average True Range |
| **Multi-timeframe confirmation** | Higher timeframe trend must align |
| **Confidence scoring** | Only signals above threshold are reported |
| **Kill Zone awareness** | ICT strategies only trigger during high-volume hours |
| **Trend strength filter** | ADX > 20–25 required for momentum strategies |

### Recommended Risk Rules

1. **Never risk more than 1–2% of your account per trade**
2. **Always use the provided Stop Loss level**
3. **Take partial profits at TP1, trail stop to breakeven**
4. **Higher confidence (8+/10) = bigger position size allowed**
5. **Lower confidence (5–6/10) = smaller position, tighter risk**

---

## 💰 RBot Pro Pricing

<table>
<tr>
<th align="center">🆓 Free Trial</th>
<th align="center">⭐ Starter</th>
<th align="center">🔥 Pro</th>
<th align="center">💎 Elite</th>
<th align="center">👑 Lifetime</th>
</tr>
<tr>
<td align="center"><b>$0</b><br/><i>7 days</i></td>
<td align="center"><b>$49</b><br/><i>/month</i></td>
<td align="center"><b>$129</b><br/><i>/month</i></td>
<td align="center"><b>$249</b><br/><i>/month</i></td>
<td align="center"><b>$999</b><br/><i>one-time</i></td>
</tr>
<tr>
<td>5 coins</td>
<td>2 Exchanges</td>
<td>4 Exchanges</td>
<td>All 8 Exchanges</td>
<td>All 8 Exchanges</td>
</tr>
<tr>
<td>8 indicators</td>
<td>20 indicators</td>
<td>All 38 indicators</td>
<td>All 38 indicators</td>
<td>All 38 indicators</td>
</tr>
<tr>
<td>3 strategies</td>
<td>12 strategies</td>
<td>All 31 strategies</td>
<td>All 31 strategies</td>
<td>All 31 strategies</td>
</tr>
<tr>
<td>Manual start only</td>
<td>Manual start</td>
<td>Auto-run scheduling</td>
<td>Auto-run + alerts</td>
<td>Auto-run + alerts</td>
</tr>
<tr>
<td>3 timeframes</td>
<td>5 timeframes</td>
<td>All 8 timeframes</td>
<td>All 8 timeframes</td>
<td>All 8 timeframes</td>
</tr>
<tr>
<td>—</td>
<td>—</td>
<td>Copy signals</td>
<td>Telegram/Discord bot</td>
<td>Telegram/Discord bot</td>
</tr>
<tr>
<td>—</td>
<td>Email support</td>
<td>Priority support</td>
<td>1-on-1 onboarding</td>
<td>Lifetime updates</td>
</tr>
</table>

### 🎁 Launch Special

> **First 100 customers**: Get **Elite** plan at **$99/month** (33% off) — *limited time offer*.

### 💳 Payment Methods

- Credit/Debit Card
- PayPal
- Cryptocurrency (BTC, ETH, USDT)

---

## 🏅 Competitor Comparison

| Feature | **RBot Pro** | TradingView | 3Commas | CryptoHopper | Cornix | Altrady |
|---------|-------------|-------------|---------|-------------|--------|---------|
| **Price** | $29–$149/mo | $15–$60/mo | $29–$99/mo | $24–$108/mo | $24–$60/mo | $27–$75/mo |
| **Indicators** | **38** | ~30 (manual) | ~5 | ~15 | ~5 | ~10 |
| **Strategies** | **31 automated** | Manual only | 3–5 | 5–10 | Relay only | ~5 |
| **ICT / SMC** | ✅ **Full** | Manual only | ❌ | ❌ | ❌ | ❌ |
| **Kill Zones** | ✅ Auto-detect | Manual | ❌ | ❌ | ❌ | ❌ |
| **Multi-TF Scan** | ✅ **8 TFs** | Manual | ❌ | 1–2 TFs | ❌ | ❌ |
| **Coins Scanned** | **200+** | 1 at a time | 10–50 | 10–30 | N/A | 10–50 |
| **Signal Gen** | ✅ **Automated** | ❌ Manual | ❌ Executes | ❌ Executes | ❌ Relays | ❌ Executes |
| **Live Web UI** | ✅ WebSocket | ✅ Charts | ✅ Dashboard | ✅ Dashboard | ❌ Telegram | ✅ Dashboard |
| **Self-Hosted** | ✅ **Local** | ❌ Cloud | ❌ Cloud | ❌ Cloud | ❌ Cloud | ❌ Cloud |
| **Open Source** | ✅ Full access | ❌ | ❌ | ❌ | ❌ | ❌ |

### Why RBot Pro Wins

1.  **🧠 Most Indicators**: 43 vs. industry average of 5–15
2.  **⚔️ Most Strategies**: 34 automated vs. 1–5 typical
3.  **📊 Visual Analysis**: Full TradingView charts for every signal with indicator overlays.
4.  **🏛️ ICT / Smart Money**: Only bot with full CHoCH, FVG, Silver Bullet, Wealth Division
4. **⚡ Speed**: 200+ coins in under 2 minutes with parallel processing
5. **🔒 Privacy**: Self-hosted — your data never leaves your machine
6. **💎 Signal Quality**: Multi-timeframe + multi-indicator confluence scoring
7. **📋 Copy-Ready**: One-click formatted signals for Telegram/WhatsApp sharing

---

## ❓ FAQ

**Q: Does RBot Pro execute trades automatically?**
A: No. RBot Pro is a **signal generation** system. It identifies trade setups and provides precise entry/SL/TP levels. You execute trades manually on your exchange. This is by design — it keeps you in control.

**Q: How accurate are the signals?**
A: Accuracy depends on market conditions and your confidence threshold setting. Higher confidence (8–10/10) signals have significantly better win rates. We recommend starting with confidence 7+ and only trading signals with R:R > 2:1.

**Q: Can I add coins not in the MEXC top 200?**
A: Yes! Use the **+ Add** button in the Web UI to add any USDT pair by name (e.g., `NMRUSDT`). The system will fetch its data from MEXC or Binance.

**Q: Does it work with exchanges other than MEXC?**
A: The data pipeline has a built-in **Binance fallback**. Any coin available on MEXC Futures or Binance Spot can be analyzed.

**Q: Can I run it 24/7?**
A: Yes. Use the **Auto-Run** feature with your preferred interval, or set up a Windows Task Scheduler job to launch the server on boot.

**Q: What's the minimum system requirement?**
A: Python 3.10+, 2GB RAM, stable internet connection. Works on Windows, macOS, and Linux.

---

## ⚠️ Disclaimer

> **Trading cryptocurrencies involves substantial risk of loss and is not suitable for every investor.** The signals generated by RBot Pro are based on technical analysis and algorithmic strategies. They do not constitute financial advice. Past performance does not guarantee future results. Always do your own research (DYOR) and never trade more than you can afford to lose. The authors of RBot Pro are not responsible for any financial losses incurred through the use of this software.

---

<p align="center">
  <b>RBot Pro v3.0</b> — Built with 🔥 for elite traders<br/>
  <i>43 Indicators · 34 Strategies · 8 Timeframes · 200+ Coins · Zero Compromise</i><br/><br/>
  <img src="https://img.shields.io/badge/Made%20with-Python-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/UI-Flask%20%2B%20SocketIO-00ff00?style=flat-square" alt="Flask" />
  <img src="https://img.shields.io/badge/Data-MEXC%20Live-ff3e3e?style=flat-square" alt="MEXC" />
  <img src="https://img.shields.io/badge/Status-Production%20Ready-00ff88?style=flat-square" alt="Status" />
</p>

---

*© 2026 RBot Pro. All rights reserved.*
