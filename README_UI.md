# 🔥 MEXC Real-Time Technical Analysis - Advanced UI | RBot Pro

Professional cryptocurrency technical analysis system with a fully customizable web interface, real-time streaming, and automated scheduling.

## ✨ Features

### 💻 Advanced Web UI
- **Modern Terminal-Style Interface** - Professional dark theme with real-time output streaming
- **Symbol Selector** - Choose which cryptocurrencies to analyze with multi-select and "Select All" button
- **Indicator Customization** - Enable/disable individual technical indicators
- **Live Output Terminal** - Real-time streaming of analysis results
- **Auto-Run Scheduling** - Run analysis automatically at 1, 3, 5, 10, or 15-minute intervals
- **Responsive Design** - Works on desktop and mobile browsers

### 📊 Technical Analysis
- **Multi-Timeframe Analysis** - 1m, 5m, 15m, 1h, 4h, 1d timeframes
- **Advanced Indicators** - RSI, EMA, MACD, Bollinger Bands, ATR, ADX, Order Blocks, Price Action
- **Confidence Scoring** - Adjustable confidence threshold (1-10/10) to control trade signal sensitivity
- **High-Quality Signals** - Minimum 2:1 risk/reward ratio, multi-timeframe confirmation

### ⚡ Performance
- **Parallel Analysis** - Analyzes up to 50+ coins concurrently
- **Live Streaming** - WebSocket-based real-time output to browser
- **Top 100 Coins** - Auto-load top 100 coins by trading volume
- **Fallback Data Sources** - MEXC primary, Binance fallback for reliability

## 🚀 Quick Start

### Start the Web UI Server
```bash
.venv\Scripts\python web_ui_server.py
```

Then open your browser to: **http://localhost:5000**

### Or Run Analysis from Terminal
```bash
# Default - top 50 coins, all indicators, min confidence 5/10
python fast_analysis.py

# Custom symbols and indicators
python fast_analysis.py --symbols "BTCUSDT,ETHUSDT,SOLUSDT" --indicators "RSI,MACD,BB" --min-confidence 6

# Custom symbols only
python fast_analysis.py --symbols "BTCUSDT,ETHUSDT"
```

## 🎮 Web UI Controls

### Main Controls
- **▶ START ANALYSIS** - Run analysis with selected settings
- **⏹ STOP** - Stop running analysis
- **✕ CLEAR OUTPUT** - Clear terminal output
- **Ctrl+Enter** - Keyboard shortcut to start
- **Ctrl+L** - Keyboard shortcut to clear

### Symbol Customization
- **Load Top 100 Coins** - Fetch latest top 100 coins by MEXC volume
- **Select All** - Check all available coins
- **Deselect All** - Uncheck all coins
- **Individual Selection** - Toggle individual coins on/off

### Indicator Selection
- **RSI** - Relative Strength Index (overbought/oversold detection)
- **EMA** - Exponential Moving Average (trend confirmation)
- **MACD** - Moving Average Convergence Divergence (momentum)
- **BB** - Bollinger Bands (volatility and support/resistance)
- **ATR** - Average True Range (volatility measurement)
- **ADX** - Average Directional Index (trend strength)
- **OB** - Order Blocks (institutional support/resistance zones)
- **PA** - Price Action (candlestick patterns and structure)

### Auto-Run Scheduling
1. Toggle **🤖 Auto-Run Analysis** ON
2. Select interval from dropdown:
   - Every 1 minute
   - Every 3 minutes
   - Every 5 minutes (default)
   - Every 10 minutes
   - Every 15 minutes
3. System automatically runs analysis at selected interval

### Confidence Adjustment
- Slide **🎯 Min Confidence** to set threshold (1-10)
- Lower = more trades but lower quality
- Higher = fewer trades but higher confidence
- Default: 5/10 (balanced)

## 📊 Output Information

Each analysis run displays:
- **Timeframes**: 1m, 5m, 15m, 1h, 4h, 1d
- **Symbols Analyzed**: Number of cryptocurrencies processed
- **Indicators Used**: Which technical indicators were calculated
- **Elapsed Time**: How long the analysis took
- **Output Lines**: Total number of output lines generated

### Trade Signals Include
- **Entry Price** - MARKET execution
- **Stop Loss** - Risk management level
- **Take Profit 1 & 2** - Exit targets
- **Risk/Reward Ratio** - Minimum 2:1 enforced
- **Confidence Score** - 1-10 rating
- **Expected Time** - Estimated duration to target
- **Technical Reasons** - Why the signal was generated

## 🔧 Configuration File Locations

- **Main Analysis Script**: `fast_analysis.py`
- **Web Server**: `web_ui_server.py`
- **UI HTML**: `templates/ui.html`
- **UI Stylesheet**: `static/advanced_style.css`
- **UI JavaScript**: `static/advanced_script.js`
- **Analysis Log**: `fast_analysis.log`

## 📋 Command-Line Arguments

```bash
python fast_analysis.py [OPTIONS]

Options:
  --symbols COINS           Comma-separated coin list (BTCUSDT,ETHUSDT,...)
  --indicators INDIC        Comma-separated indicators (RSI,EMA,MACD,...)
  --min-confidence NUM      Confidence threshold 1-10 (default: 5)
```

## 🌐 API Endpoints

The web server provides these REST endpoints:

- **GET /api/config** - Get current configuration
- **POST /api/config** - Update configuration
- **GET /api/available-coins** - Get top 100 coins
- **GET /** - Serve main UI page
- **WebSocket /socket.io** - Real-time output streaming

## 🎨 UI Customization

The UI automatically updates when you:
- Select/deselect coins or indicators
- Change confidence threshold
- Toggle auto-run scheduling
- Adjust auto-run interval

All settings are reflected in real-time on the interface.

## ⚙️ Automatic Scheduling (Scheduled Tasks)

To run the UI automatically on Windows:

1. Open Task Scheduler
2. Create Basic Task: `MEXC Auto-Analysis`
3. Trigger: At startup or on a schedule
4. Action: Run program `.venv\Scripts\python web_ui_server.py`
5. Working directory: Your workspace folder

For Unix/Linux cron:
```bash
*/5 * * * * cd /path/to/workspace && ./run_fast_analysis.bat
```

## 📈 Technical Analysis Details

### RSI (Relative Strength Index)
- Period: 14
- Overbought: >70 | Oversold: <30
- Used for: Momentum confirmation, reversal signals

### EMA (Exponential Moving Averages)
- Periods: 9, 21, 50, 200
- Used for: Trend identification, support/resistance

### MACD (Moving Average Convergence Divergence)
- Fast: 12, Slow: 26, Signal: 9
- Used for: Momentum and trend changes

### Bollinger Bands
- Period: 20, Deviation: 2
- Used for: Volatility, support/resistance, mean reversion

### ATR (Average True Range)
- Period: 14
- Used for: Stop loss sizing, profit taking

### ADX (Average Directional Index)
- Period: 14
- Used for: Trend strength assessment

### Order Blocks
- Lookback: 15 periods
- Used for: Institutional support/resistance zones

### Price Action
- Patterns: HH/HL, LL/LH, Engulfing, Reversals
- Used for: Structure confirmation

## 🔒 Data Sources

- **Primary**: MEXC Cryptocurrency Exchange API
- **Fallback**: Binance Public API (for reliability)
- **Update Frequency**: Real-time (as fast as API allows)

## 💡 Tips for Best Results

1. **Use Multiple Timeframes** - Always confirm signals across 1h and 4h
2. **Higher Confidence = Better Trades** - Set threshold to 6-7 for quality over quantity
3. **Select Specific Coins** - Focus on coins you're interested in trading
4. **Enable All Indicators** - More indicators = more accurate signals
5. **Auto-Run Every 5 Minutes** - Good balance between updates and server load
6. **Review Risk/Reward** - Only take trades with 2:1 or better

## 🐛 Troubleshooting

### Browser shows "Cannot connect"
- Make sure web_ui_server.py is running
- Check if another app is using port 5000
- Try: `netstat -ano | findstr :5000`

### No trades found
- Lower the confidence threshold
- Add more indicators
- Check if coins have enough volume

### Slow analysis
- Reduce number of selected coins
- Run less frequently
- Check your internet connection

### WebSocket errors
- Refresh the browser (Ctrl+R or Cmd+R)
- Clear browser cache and cookies
- Try a different browser

## 📝 License

For professional trading use only. Always do your own analysis.

## 🚀 Next Steps

1. Configure your preferred coins and indicators
2. Set auto-run interval to your preference
3. Monitor real-time signals via web UI
4. Execute trades based on generated signals
5. Adjust confidence threshold as needed

---

**Version 2.0** - Advanced Web UI with Full Customization
Built with Flask, Socket.IO, and Modern Web Technologies
