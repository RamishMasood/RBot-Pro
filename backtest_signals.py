#!/usr/bin/env python3
"""
Backtester for signals_history.json
Backtests signals older than 5 minutes using Binance or MEXC historical data.
Includes conflict filtering.
"""

import json
import requests
import time
from datetime import datetime, timedelta
import os
import sys
import io
from concurrent.futures import ThreadPoolExecutor, as_completed

# Force UTF-8 stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Configuration
SIGNALS_FILE = 'signals_history.json'
BINANCE_API = 'https://api.binance.com/api/v3/klines'
MEXC_API = 'https://contract.mexc.com/api/v1/contract/kline'
MIN_AGE_MINUTES = 5

def get_utc_timestamp(dt_str):
    """
    Parses a local datetime string "YYYY-MM-DD HH:MM:SS" and returns UTC timestamp in milliseconds.
    """
    dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
    return int(dt.timestamp() * 1000)

def fetch_candles_binance(symbol, start_time_ms, limit=1000):
    """Fetch 1m candles from Binance starting from start_time_ms"""
    # Align start time to 1m candle (floor to nearest minute)
    start_time_ms = (start_time_ms // 60000) * 60000
    url = f"{BINANCE_API}?symbol={symbol}&interval=1m&startTime={start_time_ms}&limit={limit}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return r.json()
        return []
    except Exception as e:
        # print(f"  Binance error: {e}")
        return []

def fetch_candles_mexc(symbol, start_time_ms, limit=1000):
    """Fetch 1m candles from MEXC Futures"""
    # Convert symbol BTCUSDT -> BTC_USDT
    if 'USDT' in symbol and '_' not in symbol:
        mexc_symbol = symbol.replace('USDT', '_USDT')
    else:
        mexc_symbol = symbol
        
        
    # Align start time to 1m candle (floor to nearest minute)
    start_sec = (start_time_ms // 1000) // 60 * 60
    end_sec = start_sec + (limit * 60)
    
    url = f"{MEXC_API}/{mexc_symbol}?interval=Min1&start={start_sec}&end={end_sec}"
    
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        if data.get('success') and 'data' in data:
            d = data['data']
            # MEXC returns parsing-friendly dict of lists
            # We need to convert to list of [time, open, high, low, close, vol]
            # time in MEXC response is seconds usually, need to check if response is consistent
            # Actually standard MEXC contract response has time list.
            
            candles = []
            if 'time' in d:
                count = len(d['time'])
                for i in range(count):
                    # Format: [time(ms), open, high, low, close, vol]
                    # MEXC time in this endpoint is usually seconds
                    ts = int(d['time'][i]) * 1000
                    o = float(d['open'][i])
                    h = float(d['high'][i])
                    l = float(d['low'][i])
                    c = float(d['close'][i])
                    v = float(d['vol'][i])
                    candles.append([ts, o, h, l, c, v])
            return candles
        return []
    except Exception as e:
        # print(f"  MEXC error: {e}")
        return []

def fetch_candles_mexc_spot(symbol, start_time_ms, limit=1000):
    """Fetch 1m candles from MEXC Spot if Contract API fails"""
    start_time_ms = (start_time_ms // 60000) * 60000
    url = f"https://api.mexc.com/api/v3/klines?symbol={symbol}&interval=1m&startTime={start_time_ms}&limit={limit}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            candles = []
            if isinstance(data, list):
                for row in data:
                    ts = int(row[0]) 
                    o = float(row[1])
                    h = float(row[2])
                    l = float(row[3])
                    c = float(row[4])
                    v = float(row[5])
                    candles.append([ts, o, h, l, c, v])
            return candles
        return []
    except Exception:
        return []

def fetch_candles_bybit(symbol, start_time_ms, limit=1000):
    """Fetch 1m candles from Bybit"""
    # Bybit uses 'start' in ms
    url = f"https://api.bybit.com/v5/market/kline?category=linear&symbol={symbol}&interval=1&start={start_time_ms}&limit={limit}"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        if data.get('result') and data['result'].get('list'):
            candles = []
            # Bybit returns newest first
            for k in reversed(data['result']['list']):
                candles.append([int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])])
            return candles
        return []
    except Exception:
        return []

def fetch_candles_bitget(symbol, start_time_ms, limit=1000):
    """Fetch 1m candles from Bitget"""
    # Bitget uses 'startTime' in ms
    url = f"https://api.bitget.com/api/v2/mix/market/candles?productType=USDT-FUTURES&symbol={symbol}&granularity=1m&startTime={start_time_ms}&limit={limit}"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        if data.get('data'):
            candles = []
            for k in data['data']:
                candles.append([int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])])
            # Ensure chronological
            if candles and candles[0][0] > candles[-1][0]:
                candles.reverse()
            return candles
        return []
    except Exception:
        return []

def fetch_candles_okx(symbol, start_time_ms, limit=100):
    """Fetch 1m candles from OKX"""
    # OKX uses 'before' in ms to get data newer than that time
    okx_symbol = symbol.replace('USDT', '-USDT-SWAP') if 'USDT' in symbol and '-' not in symbol else symbol
    url = f"https://www.okx.com/api/v5/market/candles?instId={okx_symbol}&bar=1m&before={start_time_ms + 1}&limit={limit}"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        if data.get('data'):
            candles = []
            # OKX returns newest first
            for k in reversed(data['data']):
                candles.append([int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])])
            return candles
        return []
    except Exception:
        return []

def fetch_candles_kucoin(symbol, start_time_ms, limit=1000):
    """Fetch 1m candles from KuCoin"""
    # KuCoin uses 'start' in seconds
    start_sec = start_time_ms // 1000
    kucoin_symbol = symbol.replace('USDT', '-USDT') if 'USDT' in symbol and '-' not in symbol else symbol
    url = f"https://api.kucoin.com/api/v1/market/candles?type=1min&symbol={kucoin_symbol}&startAt={start_sec}&limit={limit}"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        if data.get('data'):
            candles = []
            # KuCoin returns newest first
            for k in reversed(data['data']):
                candles.append([int(k[0]) * 1000, float(k[1]), float(k[3]), float(k[4]), float(k[2]), float(k[5])])
            return candles
        return []
    except Exception:
        return []

def fetch_candles_gateio(symbol, start_time_ms, limit=1000):
    """Fetch 1m candles from Gate.io"""
    # Gate.io uses 'from' in seconds
    start_sec = start_time_ms // 1000
    gate_symbol = symbol.replace('USDT', '_USDT') if 'USDT' in symbol and '_' not in symbol else symbol
    url = f"https://api.gateio.ws/api/v4/futures/usdt/candlesticks?contract={gate_symbol}&interval=1m&from={start_sec}&limit={limit}"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        if data and isinstance(data, list):
            candles = []
            for k in data:
                candles.append([int(k.get('t', 0)) * 1000, float(k.get('o', 0)), float(k.get('h', 0)), float(k.get('l', 0)), float(k.get('c', 0)), float(k.get('v', 0))])
            return candles
        return []
    except Exception:
        return []

def fetch_candles_htx(symbol, start_time_ms, limit=1000):
    """Fetch 1m candles from HTX"""
    # HTX uses 'from' in seconds
    start_sec = start_time_ms // 1000
    htx_symbol = symbol.lower()
    url = f"https://api.huobi.pro/market/history/kline?symbol={htx_symbol}&period=1min&size={limit}&from={start_sec}"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        if data.get('data'):
            candles = []
            for k in reversed(data['data']):
                candles.append([int(k.get('id', 0)) * 1000, float(k.get('open', 0)), float(k.get('high', 0)), float(k.get('low', 0)), float(k.get('close', 0)), float(k.get('vol', 0))])
            return candles
        return []
    except Exception:
        return []

def fetch_candles(symbol, start_time_ms, exchange, limit=1000):
    exchange = str(exchange).upper()
    if exchange == 'MEXC':
        candles = fetch_candles_mexc(symbol, start_time_ms, limit)
        if not candles:
             candles = fetch_candles_mexc_spot(symbol, start_time_ms, limit)
        return candles
    elif exchange == 'BINANCE':
        return fetch_candles_binance(symbol, start_time_ms, limit)
    elif exchange == 'BYBIT':
        return fetch_candles_bybit(symbol, start_time_ms, limit)
    elif exchange == 'BITGET':
        return fetch_candles_bitget(symbol, start_time_ms, limit)
    elif exchange == 'OKX':
        return fetch_candles_okx(symbol, start_time_ms, limit)
    elif exchange == 'KUCOIN':
        return fetch_candles_kucoin(symbol, start_time_ms, limit)
    elif exchange == 'GATEIO' or exchange == 'GATE':
        return fetch_candles_gateio(symbol, start_time_ms, limit)
    elif exchange == 'HTX' or exchange == 'HUOBI':
        return fetch_candles_htx(symbol, start_time_ms, limit)
    else:
        # Final fallback
        return fetch_candles_binance(symbol, start_time_ms, limit)

def run_backtest():
    if not os.path.exists(SIGNALS_FILE):
        print(f"Error: {SIGNALS_FILE} not found.")
        return

    print("Loading signals...")
    print("🏆 Filtering for ELITE quality signals only...")
    try:
        with open(SIGNALS_FILE, 'r', encoding='utf-8') as f:
            signals = json.load(f)
    except Exception as e:
        print(f"Error reading {SIGNALS_FILE}: {e}")
        return

    # Filter loop
    backtestable_signals = []
    now = datetime.now()
    skipped_conflicts = 0
    skipped_non_elite = 0
    
    for sig in signals:
        try:
            # 1. Filter Conflict Warning
            conflict = sig.get('conflict_warning')
            if conflict:
                skipped_conflicts += 1
                continue

            # 2. Filter Signal Quality - Only ELITE signals
            signal_quality = sig.get('signal_quality', '').upper()
            if signal_quality != 'ELITE':
                skipped_non_elite += 1
                continue

            # 3. Filter Age
            ts_str = sig['timestamp']
            sig_dt = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S')
            age = now - sig_dt
            
            if age.total_seconds() >= MIN_AGE_MINUTES * 60:
                sig['_dt'] = sig_dt
                sig['_age_str'] = str(age).split('.')[0]
                backtestable_signals.append(sig)
                
        except Exception as e:
            continue

    print(f"Found {len(signals)} total signals.")
    print(f"Skipped {skipped_conflicts} conflicting signals.")
    print(f"Skipped {skipped_non_elite} non-ELITE signals (filtering for ELITE only).")
    
    if not backtestable_signals:
        print("No eligible signals strictly older than 5 minutes found.")
        return

    print(f"Backtesting {len(backtestable_signals)} eligible signals using Exchange specific data...\n")
    
    results = {
        'total': 0,
        'wins': 0,
        'losses': 0,
        'pending': 0,
        'total_pnl': 0.0,
        'no_data': 0
    }
    # Per-strategy / timeframe performance (for deeper audit)
    # Keys: (strategy_name, timeframe)
    combo_stats = {}
    
    print(f"{'TIME':<20} {'SYMBOL':<10} {'EXCH':<8} {'TYPE':<6} {'STATUS':<10} {'PnL %':<10} {'AGE':<10}")
    print("-" * 90)
    
    def process_signal(sig):
        symbol = sig['symbol']
        direction = sig['type']
        exchange = sig.get('exchange', 'Binance')
        entry = float(sig['entry'])
        tp1 = float(sig['tp1'])
        sl = float(sig['sl'])
        
        start_ms = get_utc_timestamp(sig['timestamp'])
        
        # Use specific exchange fetcher
        candles = fetch_candles(symbol, start_ms, exchange)
        
        outcome = "PENDING"
        pnl = 0.0
        
        if candles:
            last_close = float(candles[-1][4])
            for c in candles:
                c_high = float(c[2])
                c_low = float(c[3])
                
                if direction == 'LONG':
                    if c_low <= sl:
                        outcome = "LOSS"
                        pnl = (sl - entry) / entry * 100
                        break
                    if c_high >= tp1:
                        outcome = "WIN"
                        pnl = (tp1 - entry) / entry * 100
                        break
                elif direction == 'SHORT':
                    if c_high >= sl:
                        outcome = "LOSS"
                        pnl = (entry - sl) / entry * 100
                        break
                    if c_low <= tp1:
                        outcome = "WIN"
                        pnl = (entry - tp1) / entry * 100
                        break

            if outcome == 'PENDING':
                if direction == 'LONG':
                    pnl = (last_close - entry) / entry * 100
                else:
                    pnl = (entry - last_close) / entry * 100
        else:
            outcome = "NO_DATA"

        return {
            'sig': sig,
            'outcome': outcome,
            'pnl': pnl,
            'exchange': exchange
        }

    futures = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        for sig in backtestable_signals:
            futures.append(executor.submit(process_signal, sig))
            
    collected_results = []
    for future in as_completed(futures):
        res = future.result()
        collected_results.append(res)
        
        results['total'] += 1
        outcome = res['outcome']
        pnl = res['pnl']
        
        if outcome == 'WIN':
            results['wins'] += 1
            results['total_pnl'] += pnl
        elif outcome == 'LOSS':
            results['losses'] += 1
            results['total_pnl'] += pnl
        elif outcome == 'PENDING':
            results['pending'] += 1
        else:
            results['no_data'] += 1
            
    collected_results.sort(key=lambda x: x['sig']['timestamp'])
    
    for res in collected_results:
        sig = res['sig']
        outcome = res['outcome']
        pnl = res['pnl']
        symbol = sig['symbol']
        direction = sig['type']
        exchange = res['exchange']
        
        color = " "
        if outcome == "WIN": color = "✅"
        elif outcome == "LOSS": color = "❌"
        elif outcome == "PENDING": color = "⏳"
        
        pnl_str = f"{pnl:+.2f}%"
        # TIME (20) | SYMBOL (10) | EXCH (8) | TYPE (6) | STATUS (4) | OUTCOME (8) | PNL (8) | AGE
        print(f"{sig['timestamp']:<20} {symbol:<10} {exchange:<8} {direction:<6} {color:<2} {outcome:<8} {pnl_str:>8}    {sig['_age_str']}")

        # --- Aggregate per-strategy / timeframe stats ---
        strategy = sig.get('strategy', 'UNKNOWN')
        timeframe = sig.get('timeframe', 'N/A')
        key = (strategy, timeframe)
        if key not in combo_stats:
            combo_stats[key] = {
                'total': 0,
                'wins': 0,
                'losses': 0,
                'pending': 0,
                'no_data': 0,
                'pnl': 0.0
            }
        stats = combo_stats[key]
        stats['total'] += 1
        if outcome == 'WIN':
            stats['wins'] += 1
            stats['pnl'] += pnl
        elif outcome == 'LOSS':
            stats['losses'] += 1
            stats['pnl'] += pnl
        elif outcome == 'PENDING':
            stats['pending'] += 1
        else:
            stats['no_data'] += 1

    print("-" * 90)
    print("SUMMARY")
    print(f"Total Signals: {results['total']}")
    win_rate = (results['wins'] / (results['wins'] + results['losses']) * 100) if (results['wins'] + results['losses']) > 0 else 0
    print(f"Wins: {results['wins']}  Losses: {results['losses']}  Pending: {results['pending']}  NoData: {results['no_data']}")
    print(f"Realized Win Rate (excluding pending): {win_rate:.1f}%")
    print(f"Total Realized PnL (sum %): {results['total_pnl']:.2f}%")

    # Detailed per-strategy/timeframe breakdown (ELITE signals only)
    if combo_stats:
        print("\nPER-STRATEGY/TIMEFRAME PERFORMANCE (ELITE signals)")
        print(f"{'STRATEGY':<28} {'TF':<6} {'TOTAL':<6} {'W':<4} {'L':<4} {'PEND':<5} {'NO':<4} {'WIN%':<7} {'PnL%':<9}")
        print("-" * 90)
        # Sort by total signals desc, then win-rate desc
        def _sort_key(item):
            (strategy, tf), s = item
            wins = s['wins']
            losses = s['losses']
            wr = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0.0
            return (-s['total'], -wr)

        for (strategy, tf), s in sorted(combo_stats.items(), key=_sort_key):
            total = s['total']
            wins = s['wins']
            losses = s['losses']
            pending = s['pending']
            no_data = s['no_data']
            wr = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0.0
            pnl_sum = s['pnl']
            print(f"{strategy[:26]:<28} {tf:<6} {total:<6} {wins:<4} {losses:<4} {pending:<5} {no_data:<4} {wr:>6.1f}% {pnl_sum:>8.2f}%")

if __name__ == "__main__":
    run_backtest()
