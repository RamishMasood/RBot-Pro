#!/usr/bin/env python3
"""
RBot Pro - Strategic Backtesting Engine
Validates strategy performance against historical market data.
"""

import json
import os
import requests
from datetime import datetime, timedelta
from fast_analysis import analyze_timeframe, run_strategies, MIN_CONFIDENCE

# --- GLOBAL REQUEST CONFIGURATION ---
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36'
}

def safe_request(url, retries=2):
    import time
    for i in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=12)
            r.raise_for_status()
            return r
        except:
            time.sleep(1 + i)
    return None

# --- CONFIGURATION ---
DEFAULT_BACKTEST_LIMIT = 500  # Number of candles to backtest
DEFAULT_TIMEFRAMES = ['1h', '4h', '15m']
DEFAULT_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
INITIAL_BALANCE = 10000.0
RISK_PER_TRADE = 0.01  # 1%

class Backtester:
    def __init__(self, symbols=None, timeframes=None, limit=DEFAULT_BACKTEST_LIMIT):
        self.symbols = symbols or DEFAULT_SYMBOLS
        self.timeframes = timeframes or DEFAULT_TIMEFRAMES
        self.limit = limit
        self.results = {}
        self.balance = INITIAL_BALANCE
        self.trades_history = []

    def fetch_history(self, symbol, timeframe, limit=1000):
        """Fetch historical klines from Binance API"""
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={timeframe}&limit={limit}"
        try:
            r = safe_request(url)
            if r and r.status_code == 200:
                data = r.json()
                # Process into internal format: [time, open, high, low, close, volume]
                return [[float(x) for x in k[:6]] for k in data]
        except Exception as e:
            print(f"Error fetching history for {symbol} {timeframe}: {e}")
        return []

    def run(self):
        print("\n" + "="*80)
        print("🏛️  RBOT PRO STRATEGIC BACKTESTER")
        print("="*80)
        print(f"Starting balance: ${INITIAL_BALANCE}")
        print(f"Symbols: {', '.join(self.symbols)}")
        print(f"Timeframes: {', '.join(self.timeframes)}")
        print(f"History Depth: {self.limit} candles")
        print("="*80 + "\n")

        for symbol in self.symbols:
            self.results[symbol] = {
                'total_trades': 0,
                'wins': 0,
                'losses': 0,
                'pnl': 0.0,
                'win_rate': 0.0
            }

            for tf in self.timeframes:
                print(f"⏳ Backtesting {symbol} on {tf}...")
                history = self.fetch_history(symbol, tf, self.limit + 250) # Get extra for indicators
                if not history: continue

                # Lookback requirement for indicator stabilization (e.g. EMA200)
                warmup = 200
                active_trade = None
                
                # Simulation Loop (Replay historical candles)
                for i in range(warmup, len(history)):
                    current_slice = history[:i+1]
                    current_candle = current_slice[-1]
                    low = current_candle[3]
                    high = current_candle[2]
                    close = current_candle[4]

                    # 1. Manage Active Trade (Check Entry or SL/TP)
                    if active_trade:
                        if active_trade.get('tracking_status') == 'WAITING':
                            entry_type = str(active_trade.get('entry_type', 'LIMIT')).upper()
                            entry_p = float(active_trade['entry'])
                            triggered = False
                            
                            if active_trade['type'] == 'LONG':
                                if entry_type == 'LIMIT' and low <= entry_p: triggered = True
                                elif entry_type in ['STOP-MARKET', 'STOP_LIMIT', 'STOP'] and high >= entry_p: triggered = True
                            else: # SHORT
                                if entry_type == 'LIMIT' and high >= entry_p: triggered = True
                                elif entry_type in ['STOP-MARKET', 'STOP_LIMIT', 'STOP'] and low <= entry_p: triggered = True
                                
                            if triggered:
                                active_trade['tracking_status'] = 'RUNNING'
                                # Optional: continue to check SL/TP in same candle if wanted, 
                                # but usually safer to wait for next candle in 1m simulation
                            else:
                                continue # Still waiting for entry

                        # Check Stop Loss
                        hit_sl = False
                        if active_trade['type'] == 'LONG' and low <= active_trade['sl']: hit_sl = True
                        elif active_trade['type'] == 'SHORT' and high >= active_trade['sl']: hit_sl = True
                        
                        if hit_sl:
                            self.results[symbol]['losses'] += 1
                            self.results[symbol]['pnl'] -= active_trade['risk_amount']
                            active_trade = None
                            continue
                            
                        # Check Take Profit (TP1)
                        hit_tp = False
                        if active_trade['type'] == 'LONG' and high >= active_trade['tp1']: hit_tp = True
                        elif active_trade['type'] == 'SHORT' and low <= active_trade['tp1']: hit_tp = True

                        if hit_tp:
                            self.results[symbol]['wins'] += 1
                            # Profit = risk_amount * risk_reward
                            self.results[symbol]['pnl'] += active_trade['risk_amount'] * active_trade['risk_reward']
                            active_trade = None
                            continue

                    # 2. Scan for New Signals (if no active trade)
                    if not active_trade:
                        try:
                            # Prepare kline dicts for indicator engine
                            klines = []
                            for k in current_slice:
                                klines.append({
                                    'time': k[0], 'open': k[1], 'high': k[2], 'low': k[3], 'close': k[4], 'volume': k[5]
                                })
                            
                            # Run Indicator Analysis
                            analysis = analyze_timeframe(klines, tf)
                            if not analysis: continue
                            
                            # Run All Strategies
                            trades = run_strategies(symbol, {tf: analysis})
                            
                            # Filter for high confidence
                            valid_trades = [t for t in trades if t.get('confidence_score', 0) >= MIN_CONFIDENCE]
                            
                            if valid_trades:
                                trade = valid_trades[0]
                                self.results[symbol]['total_trades'] += 1
                                
                                # Use $10,000 balance / 1% risk ($100) per trade for PnL simulation
                                trade['risk_amount'] = 100.0 
                                entry_type = str(trade.get('entry_type', 'MARKET')).upper()
                                trade['tracking_status'] = 'RUNNING' if entry_type == 'MARKET' else 'WAITING'
                                active_trade = trade
                        except Exception as e:
                            continue

        print("\n" + "="*80)
        print("✅ BACKTEST COMPLETE")
        print("="*80)
        self.print_summary()

    def print_summary(self):
        print("\nSYMBOL      TRADES    WINS    LOSSES    WIN%      PnL")
        print("-" * 65)
        for sym, res in self.results.items():
            wr = (res['wins'] / res['total_trades'] * 100) if res['total_trades'] > 0 else 0
            print(f"{sym:<11} {res['total_trades']:<9} {res['wins']:<7} {res['losses']:<9} {wr:.1f}%    ${res['pnl']:>8.2f}")
        print("-" * 65)

if __name__ == "__main__":
    bt = Backtester()
    bt.run()
