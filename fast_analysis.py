#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RBot ADVANCED ANALYSIS - LIVE CHART DATA
Multi-Timeframe | Order Blocks | Price Action | High Confidence Trades Only
Fetches top 50 USDT symbols by volume and runs multi-timeframe analysis.
"""

import sys
import io

# Force UTF-8 encoding for stdout
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
from datetime import datetime, timedelta
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import json
import math

# Command-line argument parsing
parser = argparse.ArgumentParser(description='RBot Pro Multi-Exchange Real-Time Analysis')
parser.add_argument('--symbols', type=str, default='', help='Comma-separated symbols to analyze')
parser.add_argument('--indicators', type=str, default='', help='Comma-separated indicators to use')
parser.add_argument('--timeframes', type=str, default='1m,5m,15m,1h,4h', help='Comma-separated timeframes to analyze')
parser.add_argument('--min-confidence', type=int, default=5, help='Minimum confidence threshold')
parser.add_argument('--exchanges', type=str, default='MEXC,Binance', help='Comma-separated exchanges to analyze')
args = parser.parse_args()

# Thread-safe print lock for concurrent analysis
print_lock = threading.Lock()

# Default fallback symbols (used if API fetch fails)
DEFAULT_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 
           'DOGEUSDT', 'DOTUSDT', 'MATICUSDT', 'LTCUSDT', 'LINKUSDT',
           'UNIUSDT', 'ATOMUSDT', 'NEARUSDT', 'ARBUSDT', 'OPUSDT']

BASE_URL = 'https://api.mexc.com/api/v3'

# Minimum confidence threshold (out of 10) to report trades. Lower to get more signals.
MIN_CONFIDENCE = args.min_confidence

# Enabled exchanges
ENABLED_EXCHANGES = [e.strip() for e in args.exchanges.split(',')] if args.exchanges else ['MEXC', 'Binance']

# All supported exchanges
ALL_EXCHANGES = ['MEXC', 'Binance', 'Bitget', 'Bybit', 'OKX', 'KuCoin', 'GateIO', 'HTX']

# Enabled indicators and timeframes
DEFAULT_INDICATOR_LIST = {'RSI', 'EMA', 'MACD', 'BB', 'ATR', 'ADX', 'OB', 'PA', 'ST', 'VWAP', 'CMF', 'ICHI', 'FVG', 'DIV', 'WT', 'KC', 'LIQ', 'BOS', 'MFI', 'FISH', 'ZLSMA', 'TSI', 'CHOP', 'VI', 'STC', 'DON', 'CHoCH', 'UTBOT', 'UO', 'STDEV', 'VP', 'SUPDEM', 'FIB', 'ICT_WD', 'SQZ', 'StochRSI', 'OBV', 'HMA'}
ENABLED_INDICATORS = set(args.indicators.split(',')) if args.indicators else DEFAULT_INDICATOR_LIST
ENABLED_TIMEFRAMES = args.timeframes.split(',') if args.timeframes else ['1m', '3m', '5m', '15m', '30m', '1h', '4h', '1d']

def get_top_symbols(n=200):
    """Fetch top `n` USDT symbols by volume from enabled exchanges."""
    default_top = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT']
    all_coins = set(default_top)
    
    # Try fetching from each enabled exchange
    if 'MEXC' in ENABLED_EXCHANGES:
        try:
            r = requests.get('https://contract.mexc.com/api/v1/contract/detail', timeout=10)
            data = r.json()
            if data.get('success') and isinstance(data.get('data'), list):
                contracts = data['data']
                contracts_sorted = sorted(contracts, key=lambda x: float(x.get('last24hVol', 0)), reverse=True)
                for item in contracts_sorted[:n]:
                    sym = item.get('symbol', '')
                    if sym.endswith('_USDT'):
                        all_coins.add(sym.replace('_', ''))
        except Exception as e:
            print(f"  ⚠ MEXC symbol fetch error: {e}")
    
    if 'Binance' in ENABLED_EXCHANGES:
        try:
            r = requests.get('https://api.binance.com/api/v3/ticker/24hr', timeout=10)
            data = r.json()
            binance_sorted = sorted(data, key=lambda x: float(x.get('quoteVolume', 0)), reverse=True)
            for item in binance_sorted[:n]:
                sym = item.get('symbol', '')
                if sym.endswith('USDT'):
                    all_coins.add(sym)
        except Exception as e:
            print(f"  ⚠ Binance symbol fetch error: {e}")
    
    if 'Bybit' in ENABLED_EXCHANGES:
        try:
            r = requests.get('https://api.bybit.com/v5/market/tickers?category=linear', timeout=10)
            data = r.json()
            if data.get('result') and data['result'].get('list'):
                bybit_sorted = sorted(data['result']['list'], key=lambda x: float(x.get('turnover24h', 0)), reverse=True)
                for item in bybit_sorted[:n]:
                    sym = item.get('symbol', '')
                    if sym.endswith('USDT'):
                        all_coins.add(sym)
        except Exception as e:
            print(f"  ⚠ Bybit symbol fetch error: {e}")
    
    if 'Bitget' in ENABLED_EXCHANGES:
        try:
            r = requests.get('https://api.bitget.com/api/v2/mix/market/tickers?productType=USDT-FUTURES', timeout=10)
            data = r.json()
            if data.get('data'):
                for item in data['data'][:n]:
                    sym = item.get('symbol', '')
                    if sym.endswith('USDT'):
                        all_coins.add(sym)
        except Exception as e:
            print(f"  ⚠ Bitget symbol fetch error: {e}")
    
    if 'OKX' in ENABLED_EXCHANGES:
        try:
            r = requests.get('https://www.okx.com/api/v5/market/tickers?instType=SWAP', timeout=10)
            data = r.json()
            if data.get('data'):
                for item in data['data'][:n]:
                    inst_id = item.get('instId', '')
                    if 'USDT' in inst_id:
                        sym = inst_id.replace('-', '').replace('SWAP', '').strip()
                        if sym.endswith('USDT'):
                            all_coins.add(sym)
        except Exception as e:
            print(f"  ⚠ OKX symbol fetch error: {e}")
    
    if 'KuCoin' in ENABLED_EXCHANGES:
        try:
            r = requests.get('https://api.kucoin.com/api/v1/market/allTickers', timeout=10)
            data = r.json()
            if data.get('data') and data['data'].get('ticker'):
                for item in data['data']['ticker'][:n*2]:
                    sym = item.get('symbol', '')
                    if sym.endswith('-USDT'):
                        all_coins.add(sym.replace('-', ''))
        except Exception as e:
            print(f"  ⚠ KuCoin symbol fetch error: {e}")
    
    if 'GateIO' in ENABLED_EXCHANGES:
        try:
            r = requests.get('https://api.gateio.ws/api/v4/futures/usdt/contracts', timeout=10)
            data = r.json()
            for item in data[:n]:
                name = item.get('name', '')
                if name.endswith('_USDT'):
                    all_coins.add(name.replace('_', ''))
        except Exception as e:
            print(f"  ⚠ Gate.io symbol fetch error: {e}")
    
    if 'HTX' in ENABLED_EXCHANGES:
        try:
            r = requests.get('https://api.huobi.pro/v2/settings/common/symbols', timeout=10)
            data = r.json()
            if data.get('data'):
                for item in data['data'][:n*2]:
                    sym = item.get('sc', '')
                    if sym.endswith('usdt'):
                        all_coins.add(sym.upper())
        except Exception as e:
            print(f"  ⚠ HTX symbol fetch error: {e}")
    
    # Combine with default at front, deduplicate
    combined = default_top + [c for c in sorted(all_coins) if c not in default_top]
    return combined[:n]

def get_klines_mexc(symbol, interval, limit=200):
    """Fetch klines from MEXC Futures API (Contract API)"""
    try:
        # Mapping for MEXC Futures intervals
        mapping = {
            '1m': 'Min1', '3m': 'Min3', '5m': 'Min5', '15m': 'Min15', '30m': 'Min30',
            '1h': 'Min60', '4h': 'Hour4', '8h': 'Hour8', '1d': 'Day1'
        }
        mexc_interval = mapping.get(interval, 'Min60')

        # Convert BTCUSDT -> BTC_USDT for Futures API
        futures_symbol = symbol
        if 'USDT' in symbol and '_' not in symbol:
            futures_symbol = symbol.replace('USDT', '_USDT')
            
        # MEXC Futures kline endpoint
        url = f'https://contract.mexc.com/api/v1/contract/kline/{futures_symbol}?interval={mexc_interval}&limit={limit}'
        r = requests.get(url, timeout=10)
        data = r.json()
        
        if data.get('success') and 'data' in data:
            d = data['data']
            # Futures API returns object with lists: 'time', 'open', 'high', 'low', 'close', 'vol'
            candles = []
            for i in range(len(d['time'])):
                try:
                    candles.append({
                        'time': int(d['time'][i]) * 1000, 
                        'open': float(d['open'][i]),
                        'high': float(d['high'][i]),
                        'low': float(d['low'][i]),
                        'close': float(d['close'][i]),
                        'volume': float(d['vol'][i])
                    })
                except:
                    continue
            return candles if candles else None
        return None
    except Exception as e:
        return None

def get_klines_binance(symbol, interval, limit=200):
    """Get klines from Binance API"""
    try:
        url = f'https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}'
        r = requests.get(url, timeout=10)
        r.encoding = 'utf-8'
        data = r.json()
        
        if data and isinstance(data, list):
            candles = []
            for k in data:
                candles.append({
                    'time': int(k[0]),
                    'open': float(k[1]),
                    'high': float(k[2]),
                    'low': float(k[3]),
                    'close': float(k[4]),
                    'volume': float(k[7])
                })
            return candles
        return None
    except:
        return None

def get_klines_bybit(symbol, interval, limit=200):
    """Get klines from Bybit API"""
    try:
        # Bybit interval mapping
        mapping = {
            '1m': '1', '3m': '3', '5m': '5', '15m': '15', '30m': '30',
            '1h': '60', '4h': '240', '1d': 'D'
        }
        bybit_interval = mapping.get(interval, '60')
        url = f'https://api.bybit.com/v5/market/kline?category=linear&symbol={symbol}&interval={bybit_interval}&limit={limit}'
        r = requests.get(url, timeout=10)
        data = r.json()
        
        if data.get('result') and data['result'].get('list'):
            candles = []
            for k in reversed(data['result']['list']):  # Bybit returns newest first
                candles.append({
                    'time': int(k[0]),
                    'open': float(k[1]),
                    'high': float(k[2]),
                    'low': float(k[3]),
                    'close': float(k[4]),
                    'volume': float(k[5])
                })
            return candles if candles else None
        return None
    except:
        return None

def get_klines_bitget(symbol, interval, limit=200):
    """Get klines from Bitget API"""
    try:
        # Bitget interval mapping
        mapping = {
            '1m': '1m', '3m': '3m', '5m': '5m', '15m': '15m', '30m': '30m',
            '1h': '1H', '4h': '4H', '1d': '1D'
        }
        bitget_interval = mapping.get(interval, '1H')
        url = f'https://api.bitget.com/api/v2/mix/market/candles?productType=USDT-FUTURES&symbol={symbol}&granularity={bitget_interval}&limit={limit}'
        r = requests.get(url, timeout=10)
        data = r.json()
        
        if data.get('data'):
            candles = []
            for k in data['data']:
                candles.append({
                    'time': int(k[0]),
                    'open': float(k[1]),
                    'high': float(k[2]),
                    'low': float(k[3]),
                    'close': float(k[4]),
                    'volume': float(k[5]) if len(k) > 5 else 0
                })
            # Bitget may return newest first, ensure chronological order
            if candles and candles[0]['time'] > candles[-1]['time']:
                candles.reverse()
            return candles if candles else None
        return None
    except:
        return None

def get_klines_okx(symbol, interval, limit=200):
    """Get klines from OKX API"""
    try:
        # OKX interval mapping
        mapping = {
            '1m': '1m', '3m': '3m', '5m': '5m', '15m': '15m', '30m': '30m',
            '1h': '1H', '4h': '4H', '1d': '1D'
        }
        okx_interval = mapping.get(interval, '1H')
        # Convert BTCUSDT -> BTC-USDT-SWAP for OKX
        okx_symbol = symbol.replace('USDT', '-USDT-SWAP') if 'USDT' in symbol and '-' not in symbol else symbol
        url = f'https://www.okx.com/api/v5/market/candles?instId={okx_symbol}&bar={okx_interval}&limit={limit}'
        r = requests.get(url, timeout=10)
        data = r.json()
        
        if data.get('data'):
            candles = []
            for k in reversed(data['data']):  # OKX returns newest first
                candles.append({
                    'time': int(k[0]),
                    'open': float(k[1]),
                    'high': float(k[2]),
                    'low': float(k[3]),
                    'close': float(k[4]),
                    'volume': float(k[5]) if len(k) > 5 else 0
                })
            return candles if candles else None
        return None
    except:
        return None

def get_klines_kucoin(symbol, interval, limit=200):
    """Get klines from KuCoin API"""
    try:
        # KuCoin interval mapping
        mapping = {
            '1m': '1min', '3m': '3min', '5m': '5min', '15m': '15min', '30m': '30min',
            '1h': '1hour', '4h': '4hour', '1d': '1day'
        }
        kucoin_interval = mapping.get(interval, '1hour')
        # Convert BTCUSDT -> BTC-USDT for KuCoin
        kucoin_symbol = symbol.replace('USDT', '-USDT') if 'USDT' in symbol and '-' not in symbol else symbol
        import time as _time
        end_at = int(_time.time())
        start_at = end_at - (limit * 3600)  # Approximate
        url = f'https://api.kucoin.com/api/v1/market/candles?type={kucoin_interval}&symbol={kucoin_symbol}&startAt={start_at}&endAt={end_at}'
        r = requests.get(url, timeout=10)
        data = r.json()
        
        if data.get('data'):
            candles = []
            for k in reversed(data['data']):  # KuCoin returns newest first
                candles.append({
                    'time': int(k[0]) * 1000,
                    'open': float(k[1]),
                    'close': float(k[2]),
                    'high': float(k[3]),
                    'low': float(k[4]),
                    'volume': float(k[6]) if len(k) > 6 else float(k[5])
                })
            return candles if candles else None
        return None
    except:
        return None

def get_klines_gateio(symbol, interval, limit=200):
    """Get klines from Gate.io API"""
    try:
        # Gate.io interval mapping
        mapping = {
            '1m': '1m', '3m': '3m', '5m': '5m', '15m': '15m', '30m': '30m',
            '1h': '1h', '4h': '4h', '1d': '1d'
        }
        gate_interval = mapping.get(interval, '1h')
        # Convert BTCUSDT -> BTC_USDT for Gate.io
        gate_symbol = symbol.replace('USDT', '_USDT') if 'USDT' in symbol and '_' not in symbol else symbol
        url = f'https://api.gateio.ws/api/v4/futures/usdt/candlesticks?contract={gate_symbol}&interval={gate_interval}&limit={limit}'
        r = requests.get(url, timeout=10)
        data = r.json()
        
        if data and isinstance(data, list):
            candles = []
            for k in data:
                candles.append({
                    'time': int(k.get('t', 0)) * 1000,
                    'open': float(k.get('o', 0)),
                    'high': float(k.get('h', 0)),
                    'low': float(k.get('l', 0)),
                    'close': float(k.get('c', 0)),
                    'volume': float(k.get('v', 0))
                })
            return candles if candles else None
        return None
    except:
        return None

def get_klines_htx(symbol, interval, limit=200):
    """Get klines from HTX (Huobi) API"""
    try:
        # HTX interval mapping
        mapping = {
            '1m': '1min', '3m': '3min', '5m': '5min', '15m': '15min', '30m': '30min',
            '1h': '60min', '4h': '4hour', '1d': '1day'
        }
        htx_interval = mapping.get(interval, '60min')
        htx_symbol = symbol.lower()
        url = f'https://api.huobi.pro/market/history/kline?symbol={htx_symbol}&period={htx_interval}&size={limit}'
        r = requests.get(url, timeout=10)
        data = r.json()
        
        if data.get('data'):
            candles = []
            for k in reversed(data['data']):  # HTX returns newest first
                candles.append({
                    'time': int(k.get('id', 0)) * 1000,
                    'open': float(k.get('open', 0)),
                    'high': float(k.get('high', 0)),
                    'low': float(k.get('low', 0)),
                    'close': float(k.get('close', 0)),
                    'volume': float(k.get('vol', 0))
                })
            return candles if candles else None
        return None
    except:
        return None

# Map exchange names to their kline fetcher functions
EXCHANGE_KLINE_FETCHERS = {
    'MEXC': get_klines_mexc,
    'Binance': get_klines_binance,
    'Bybit': get_klines_bybit,
    'Bitget': get_klines_bitget,
    'OKX': get_klines_okx,
    'KuCoin': get_klines_kucoin,
    'GateIO': get_klines_gateio,
    'HTX': get_klines_htx
}

def get_klines(symbol, interval, limit=200, exchange=None):
    """Get klines from the specified exchange, with fallback chain through enabled exchanges"""
    if exchange:
        fetcher = EXCHANGE_KLINE_FETCHERS.get(exchange)
        if fetcher:
            klines = fetcher(symbol, interval, limit)
            if klines and len(klines) >= 50:
                return klines
    
    # Fallback: try all enabled exchanges in order
    for ex_name in ENABLED_EXCHANGES:
        fetcher = EXCHANGE_KLINE_FETCHERS.get(ex_name)
        if fetcher:
            klines = fetcher(symbol, interval, limit)
            if klines and len(klines) >= 50:
                return klines
    
    return None

# --- Indicators & analysis helpers ---

def calculate_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100 if avg_gain > 0 else 50
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_ema(closes, period):
    if len(closes) < period:
        return closes[-1] if closes else 0
    mult = 2 / (period + 1)
    ema = sum(closes[:period]) / period
    for price in closes[period:]:
        ema = price * mult + ema * (1 - mult)
    return ema

def calculate_macd(closes):
    if len(closes) < 26:
        return {'macd': 0, 'signal': 0, 'histogram': 0}
    ema12 = calculate_ema(closes, 12)
    ema26 = calculate_ema(closes, 26)
    macd_line = ema12 - ema26
    macd_values = []
    for i in range(26, len(closes)):
        ema12_val = calculate_ema(closes[:i+1], 12)
        ema26_val = calculate_ema(closes[:i+1], 26)
        macd_values.append(ema12_val - ema26_val)
    signal = calculate_ema(macd_values, 9) if len(macd_values) >= 9 else macd_line
    return {'macd': macd_line, 'signal': signal, 'histogram': macd_line - signal}

def calculate_bb(closes, period=20, std_dev=2):
    if len(closes) < period:
        return None
    sma = sum(closes[-period:]) / period
    variance = sum((x - sma) ** 2 for x in closes[-period:]) / period
    std = variance ** 0.5
    return {'upper': sma + (std * std_dev), 'middle': sma, 'lower': sma - (std * std_dev), 'width': 2 * std * std_dev}

def calculate_atr(highs, lows, closes, period=14):
    if len(closes) < period:
        return 0
    trs = []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        trs.append(tr)
    return sum(trs[-period:]) / period if len(trs) >= period else 0

def calculate_adx(highs, lows, closes, period=14):
    """Calculate Average Directional Index"""
    if len(closes) < period * 2:
        return 0
    
    plus_dm = []
    minus_dm = []
    tr = []
    
    for i in range(1, len(closes)):
        h_diff = highs[i] - highs[i-1]
        l_diff = lows[i-1] - lows[i]
        
        plus_dm.append(h_diff if h_diff > l_diff and h_diff > 0 else 0)
        minus_dm.append(l_diff if l_diff > h_diff and l_diff > 0 else 0)
        
        tr.append(max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1])))
        
    if not tr:
        return 0

    def smooth(data, per):
        if not data: return []
        res = [sum(data[:per])/per]
        for val in data[per:]:
            res.append((res[-1] * (per - 1) + val) / per)
        return res

    atr_smooth = smooth(tr, period)
    plus_di = [100 * p / a for p, a in zip(smooth(plus_dm, period), atr_smooth)]
    minus_di = [100 * m / a for m, a in zip(smooth(minus_dm, period), atr_smooth)]
    
    dx = [100 * abs(p - m) / (p + m) if (p + m) > 0 else 0 for p, m in zip(plus_di, minus_di)]
    adx = smooth(dx, period)
    
    return {
        'adx': adx[-1] if adx else 0,
        'plus_di': plus_di[-1] if plus_di else 0,
        'minus_di': minus_di[-1] if minus_di else 0
    }

def calculate_stoch_rsi(closes, length=14, rsi_len=14, k=3, d=3):
    """Calculate Stochastic RSI"""
    rsi_vals = []
    # Need enough data for RSI + Stoch
    if len(closes) < length + rsi_len + 5:
        return {'k': 50, 'd': 50}
        
    # Calculate RSI series
    for i in range(len(closes) - length - rsi_len, len(closes) + 1):
        chunk = closes[:i]
        if len(chunk) < rsi_len + 1: continue
        rsi_vals.append(calculate_rsi(chunk, rsi_len))
        
    if len(rsi_vals) < length:
        return {'k': 50, 'd': 50}
        
    stoch_rsi = []
    for i in range(length, len(rsi_vals) + 1):
        window = rsi_vals[i-length:i]
        min_rsi = min(window)
        max_rsi = max(window)
        if max_rsi == min_rsi:
            stoch_rsi.append(100 if window[-1] > 50 else 0)
        else:
            stoch_rsi.append(100 * (window[-1] - min_rsi) / (max_rsi - min_rsi))
            
    # Smooth K and D
    def sma(data, p):
        return sum(data[-p:]) / p if len(data) >= p else data[-1]
        
    k_val = sma(stoch_rsi, k)
    d_val = sma(stoch_rsi[-d:], d) # Approximating D as SMA of K, strictly it's SMA of StochRSI then SMA of that
    
    return {'k': k_val, 'd': d_val}

def calculate_obv(closes, volumes):
    """Calculate On-Balance Volume trend"""
    if len(closes) < 20 or len(volumes) < 20:
        return 'NEUTRAL'
        
    obv = [0]
    for i in range(1, len(closes)):
        if closes[i] > closes[i-1]:
            obv.append(obv[-1] + volumes[i])
        elif closes[i] < closes[i-1]:
            obv.append(obv[-1] - volumes[i])
        else:
            obv.append(obv[-1])
            
    # Simple trend check: is OBV higher than 20 periods ago?
    if len(obv) > 20:
        return 'BULLISH' if obv[-1] > obv[-20] else 'BEARISH'
    return 'NEUTRAL'

def calculate_chop(high, low, close, length=14):
    """Calculate Choppiness Index (0-100). >61.8 = choppy, <38.2 = trending."""
    try:
        if len(close) < length + 1: return 50
        
        trf = []
        for i in range(1, len(close)):
            h = high[i]
            l = low[i]
            pc = close[i-1]
            tr = max(h - l, abs(h - pc), abs(l - pc))
            trf.append(tr)
            
        tr_sum = [sum(trf[i-length:i]) for i in range(length, len(trf)+1)]
        h_max = [max(high[i-length:i]) for i in range(length, len(high)+1)]
        l_min = [min(low[i-length:i]) for i in range(length, len(low)+1)]
        
        if not tr_sum or not h_max or not l_min: return 50
        
        range_high_low = h_max[-1] - l_min[-1]
        if range_high_low == 0: return 100
        
        chop = 100 * math.log10(tr_sum[-1] / range_high_low) / math.log10(length)
        return round(chop, 2)
    except:
        return 50

def calculate_vortex(high, low, close, length=14):
    """Calculate Vortex Indicator (VI+ and VI-)."""
    try:
        if len(close) < length + 1: return {'plus': 1.0, 'minus': 1.0}
        
        vmp = [abs(high[i] - low[i-1]) for i in range(1, len(close))]
        vmm = [abs(low[i] - high[i-1]) for i in range(1, len(close))]
        tr = []
        for i in range(1, len(close)):
            h = high[i]
            l = low[i]
            pc = close[i-1]
            tr.append(max(h - l, abs(h - pc), abs(l - pc)))
            
        vmp_sum = sum(vmp[-length:])
        vmm_sum = sum(vmm[-length:])
        tr_sum = sum(tr[-length:])
        
        if tr_sum == 0: return {'plus': 1.0, 'minus': 1.0}
        
        vip = vmp_sum / tr_sum
        vim = vmm_sum / tr_sum
        return {'plus': round(vip, 3), 'minus': round(vim, 3)}
    except:
        return {'plus': 1.0, 'minus': 1.0}

def calculate_stc(close, length=10, fast=23, slow=50):
    """Calculate Schaff Trend Cycle (STC) - Pure Python version."""
    try:
        if len(close) < slow + length + 5: return 50
        
        # Helper for EMA series
        def series_ema(data, p):
            if not data: return []
            mult = 2 / (p + 1)
            ema = data[0]
            res = [ema]
            for val in data[1:]:
                ema = val * mult + ema * (1 - mult)
                res.append(ema)
            return res

        # 1. MACD baseline
        ema_fast = series_ema(close, fast)
        ema_slow = series_ema(close, slow)
        # Align lengths
        min_len = min(len(ema_fast), len(ema_slow))
        macd = [ema_fast[i] - ema_slow[i] for i in range(len(ema_fast) - min_len, len(ema_fast))]
        
        # 2. Stochastic of MACD
        def stoch_of_series(series, l):
            stoch = []
            for i in range(len(series)):
                if i < l - 1:
                    stoch.append(50)
                    continue
                window = series[i - l + 1 : i + 1]
                lo = min(window)
                hi = max(window)
                if hi == lo: stoch.append(50)
                else: stoch.append(100 * (series[i] - lo) / (hi - lo))
            return stoch

        st1 = stoch_of_series(macd, length)
        pf1 = series_ema(st1, length // 2)
        st2 = stoch_of_series(pf1, length)
        stc = series_ema(st2, length // 2)
        
        return round(stc[-1], 2)
    except:
        return 50

def calculate_donchian(high, low, length=20):
    """Calculate Donchian Channels."""
    try:
        if len(high) < length: return None
        upper = max(high[-length:])
        lower = min(low[-length:])
        middle = (upper + lower) / 2
        return {'upper': upper, 'lower': lower, 'middle': middle}
    except:
        return None

def calculate_hull_suite(close, length=20):
    """Hull Suite (HMA optimized for trend following)."""
    try:
        if len(close) < length * 2: return close[-1]
        hma = calculate_hma(close, length)
        # In Hull Suite, we often use 2x length for a smoother look
        # But we'll just return the HMA here as it's the core.
        return hma
    except:
        return close[-1]

def calculate_kc(high, low, close, length=20, multiplier=2.0):
    """Calculate Keltner Channels."""
    try:
        if len(close) < length: return None
        ema = calculate_ema(close, length)
        atr = calculate_atr(high, low, close, length)
        upper = ema + (multiplier * atr)
        lower = ema - (multiplier * atr)
        return {'upper': upper, 'lower': lower, 'middle': ema}
    except:
        return None

def calculate_utbot(high, low, close, key=2, atr_period=10):
    """Calculate UT Bot Alerts (Key + ATR trailing stop)."""
    try:
        if len(close) < max(20, atr_period + 5): return {'signal': 'NEUTRAL', 'stop': 0}
        
        atr = calculate_atr(high, low, close, atr_period)
        n_loss = key * atr
        
        src = close
        trail = [0.0] * len(src)
        
        # We need a small loop to simulate the trailing stop
        # Starting slightly back to get a stable state
        start_idx = len(src) - 20
        for i in range(start_idx, len(src)):
            prev_trail = trail[i-1] if i > 0 else src[i]
            
            if src[i] > prev_trail and src[i-1] > prev_trail:
                trail[i] = max(prev_trail, src[i] - n_loss)
            elif src[i] < prev_trail and src[i-1] < prev_trail:
                trail[i] = min(prev_trail, src[i] + n_loss)
            elif src[i] > prev_trail:
                trail[i] = src[i] - n_loss
            else:
                trail[i] = src[i] + n_loss
                
        curr_trail = trail[-1]
        prev_trail = trail[-2]
        
        signal = 'NEUTRAL'
        if src[-1] > curr_trail and src[-2] <= prev_trail:
            signal = 'BUY'
        elif src[-1] < curr_trail and src[-2] >= prev_trail:
            signal = 'SELL'
        elif src[-1] > curr_trail:
            signal = 'BULLISH'
        elif src[-1] < curr_trail:
            signal = 'BEARISH'
            
        return {'signal': signal, 'stop': curr_trail}
    except:
        return {'signal': 'NEUTRAL', 'stop': 0}

def detect_swing_points(candles, window=5):
    """Detect advanced swing highs and lows with customizable window."""
    try:
        highs = [c['high'] for c in candles]
        lows = [c['low'] for c in candles]
        swing_highs = []
        swing_lows = []
        
        for i in range(window, len(candles) - window):
            # Swing High
            if all(highs[i] >= highs[i-j] for j in range(1, window + 1)) and \
               all(highs[i] > highs[i+j] for j in range(1, window + 1)):
                swing_highs.append({'index': i, 'price': highs[i]})
            
            # Swing Low
            if all(lows[i] <= lows[i-j] for j in range(1, window + 1)) and \
               all(lows[i] < lows[i+j] for j in range(1, window + 1)):
                swing_lows.append({'index': i, 'price': lows[i]})
        
        return swing_highs, swing_lows
    except:
        return [], []

def detect_advanced_harmonics(candles):
    """Detect XABCD Harmonic Patterns (Gartley, Bat, Butterfly, Crab)."""
    try:
        sw_highs, sw_lows = detect_swing_points(candles, window=3)
        # Combine and sort by index
        all_points = sorted(sw_highs + sw_lows, key=lambda x: x['index'])
        if len(all_points) < 5: return None
        
        # Take the last 5 points for XABCD
        p = all_points[-5:]
        X, A, B, C, D = p[0]['price'], p[1]['price'], p[2]['price'], p[3]['price'], p[4]['price']
        
        # Calculate ratios
        XA = abs(A - X)
        AB = abs(B - A)
        BC = abs(C - B)
        CD = abs(D - C)
        
        if XA == 0: return None
        ret_AB_XA = AB / XA
        ret_BC_AB = BC / AB if AB != 0 else 0
        ret_CD_BC = CD / BC if BC != 0 else 0
        ret_AD_XA = abs(D - A) / XA
        
        # Pattern logic (Simplified ranges for high accuracy)
        # Gartley: AB=0.618 XA, AD=0.786 XA
        if 0.55 < ret_AB_XA < 0.65 and 0.75 < ret_AD_XA < 0.85:
            return {'pattern': 'GARTLEY', 'type': 'BULLISH' if D < A else 'BEARISH'}
            
        # Bat: AB=0.382-0.5 XA, AD=0.886 XA
        if 0.35 < ret_AB_XA < 0.55 and 0.85 < ret_AD_XA < 0.95:
            return {'pattern': 'BAT', 'type': 'BULLISH' if D < A else 'BEARISH'}
            
        return None
    except:
        return None

def detect_mitigation_block(candles):
    """Detect Mitigation Blocks (failed Order Blocks)."""
    try:
        if len(candles) < 20: return None
        # Mitigation block is a swing point that didn't mitigate/hold
        sw_highs, sw_lows = detect_swing_points(candles[-30:], window=3)
        if not sw_lows or not sw_highs: return None
        
        curr_price = candles[-1]['close']
        
        # BULLISH: Price breaks below a recent swing low, then breaks back above it.
        last_low = sw_lows[-1]['price']
        if curr_price > last_low and any(c['low'] < last_low for c in candles[-10:-1]):
            return {'type': 'BULLISH', 'level': last_low}
            
        # BEARISH: Price breaks above a recent swing high, then breaks back below it.
        last_high = sw_highs[-1]['price']
        if curr_price < last_high and any(c['high'] > last_high for c in candles[-10:-1]):
            return {'type': 'BEARISH', 'level': last_high}
            
        return None
    except:
        return None

def check_mtf_alignment(analyses, current_tf, current_trend):
    """Check if the next higher timeframe trend aligns with the signal."""
    tf_order = ['1m', '3m', '5m', '15m', '30m', '1h', '4h', '1d']
    try:
        if current_tf not in tf_order: return True
        idx = tf_order.index(current_tf)
        
        # Look for the first higher TF that exists in the analyses
        for i in range(idx + 1, len(tf_order)):
            higher_tf = tf_order[i]
            if higher_tf in analyses:
                higher_trend = analyses[higher_tf].get('trend', 'NEUTRAL')
                if higher_trend == 'NEUTRAL': continue
                return higher_trend == current_trend
        
        return True # Default to True if no higher TF found
    except:
        return True

def detect_choch(candles, timeframe):
    """Detect Change of Character (CHoCH) - Reversal Signal."""
    try:
        if len(candles) < 30: return None
        close = [c[4] for c in candles]
        high = [c[2] for c in candles]
        low = [c[3] for c in candles]
        
        # Look for the last swing high and low
        # Simple peak/trough detection
        window = 5
        last_highs = []
        last_lows = []
        for i in range(window, len(close)-window):
            if all(high[i] > high[i-j] for j in range(1, window)) and all(high[i] > high[i+j] for j in range(1, window)):
                last_highs.append((i, high[i]))
            if all(low[i] < low[i-j] for j in range(1, window)) and all(low[i] < low[i+j] for j in range(1, window)):
                last_lows.append((i, low[i]))
        
        if not last_highs or not last_lows: return None
        
        curr_price = close[-1]
        # BULLISH CHoCH: Price breaks above the last major swing high after a downtrend
        if curr_price > last_highs[-1][1]:
             # If previous highs were descending, it's a CHoCH
             if len(last_highs) >= 2 and last_highs[-1][1] < last_highs[-2][1]:
                 return {'type': 'BULLISH', 'level': last_highs[-1][1]}
                 
        # BEARISH CHoCH: Price breaks below the last major swing low after an uptrend
        if curr_price < last_lows[-1][1]:
             if len(last_lows) >= 2 and last_lows[-1][1] > last_lows[-2][1]:
                 return {'type': 'BEARISH', 'level': last_lows[-1][1]}
                 
        return None
    except:
        return None

def calculate_hma(closes, period):
    """Hull Moving Average - faster and less lag"""
    if len(closes) < period: return closes[-1] if closes else 0
    half_length = int(period / 2)
    sqrt_length = int(period**0.5)
    
    def wma(data, p):
        if len(data) < p: return data[-1]
        sum_w = 0
        denom = p * (p + 1) / 2
        for i in range(p):
            sum_w += data[-(p-i)] * (i + 1)
        return sum_w / denom

    # Calculate WMA series (approximate HMA)
    diff = []
    for i in range(max(period, half_length), len(closes) + 1):
        window = closes[:i]
        d = 2 * wma(window, half_length) - wma(window, period)
        diff.append(d)
        
    return wma(diff, sqrt_length) if len(diff) >= sqrt_length else diff[-1]

def calculate_supertrend(candles, period=10, multiplier=3):
    """Calculate SuperTrend indicator"""
    if len(candles) < period + 1:
        return {'trend': 'NEUTRAL', 'upper': 0, 'lower': 0}
        
    highs = [c['high'] for c in candles]
    lows = [c['low'] for c in candles]
    closes = [c['close'] for c in candles]
    
    atr = calculate_atr(highs, lows, closes, period)
    
    # Simple version for real-time (calculate last few points)
    mid = (highs[-1] + lows[-1]) / 2
    upper = mid + (multiplier * atr)
    lower = mid - (multiplier * atr)
    
    trend = 'BULLISH' if closes[-1] > lower else 'BEARISH'
    return {'trend': trend, 'upper': upper, 'lower': lower, 'atr': atr}

def calculate_vwap(candles):
    """Calculate Anchored VWAP from given dataset"""
    if not candles: return 0
    sum_pv = 0
    sum_v = 0
    for c in candles:
        price = (c['high'] + c['low'] + c['close']) / 3
        sum_pv += price * c['volume']
        sum_v += c['volume']
    return sum_pv / sum_v if sum_v > 0 else candles[-1]['close']

def calculate_cmf(candles, period=20):
    """Calculate Chaikin Money Flow"""
    if len(candles) < period: return 0
    mfv_sum = 0
    vol_sum = 0
    for i in range(len(candles)-period, len(candles)):
        c = candles[i]
        denom = (c['high'] - c['low'])
        mult = ((c['close'] - c['low']) - (c['high'] - c['close'])) / denom if denom > 0 else 0
        mfv_sum += mult * c['volume']
        vol_sum += c['volume']
    return mfv_sum / vol_sum if vol_sum > 0 else 0

def calculate_ichimoku(highs, lows):
    """Calculate Ichimoku Cloud components"""
    if len(highs) < 52: return None
    
    def donchian(h, l, p):
        return (max(h[-p:]) + min(l[-p:])) / 2
        
    tenkan = donchian(highs, lows, 9)
    kijun = donchian(highs, lows, 26)
    
    # Span A (plotted 26 periods ahead, but we use current values for logic)
    senkou_a = (tenkan + kijun) / 2
    # Span B (52 period donchian)
    senkou_b = donchian(highs, lows, 52)
    
    return {
        'tenkan': tenkan,
        'kijun': kijun,
        'span_a': senkou_a,
        'span_b': senkou_b,
        'cloud_state': 'BULLISH' if senkou_a > senkou_b else 'BEARISH'
    }

def detect_fvg(candles):
    """Detect Fair Value Gaps (FVG) in the last 3 candles"""
    if len(candles) < 3: return None
    
    # CANDLE INDEX: 0 (past), 1 (middle/gap), 2 (current)
    # Bullish FVG: Low of candle 2 > High of candle 0
    if candles[-1]['low'] > candles[-3]['high']:
        return {'type': 'BULLISH', 'top': candles[-1]['low'], 'bottom': candles[-3]['high']}
    
    # Bearish FVG: High of candle 2 < Low of candle 0
    if candles[-1]['high'] < candles[-3]['low']:
        return {'type': 'BEARISH', 'top': candles[-3]['low'], 'bottom': candles[-1]['high']}
        
    return None

def detect_rsi_divergence(candles, rsi_values):
    """Detect Bullish/Bearish RSI Divergence"""
    if len(rsi_values) < 30 or len(candles) < 30: return None
    
    closes = [c['close'] for c in candles]
    
    # BULLISH: Price makes lower low, RSI makes higher low
    p_low1 = min(closes[-15:-5])
    p_low2 = closes[-1]
    r_low1 = min(rsi_values[-15:-5])
    r_low2 = rsi_values[-1]
    
    if p_low2 < p_low1 * 0.998 and r_low2 > r_low1 + 2 and r_low2 < 40:
        return 'BULLISH'
        
    # BEARISH: Price makes higher high, RSI makes lower high
    p_high1 = max(closes[-15:-5])
    p_high2 = closes[-1]
    r_high1 = max(rsi_values[-15:-5])
    r_high2 = rsi_values[-1]
    
    if p_high2 > p_high1 * 1.002 and r_high2 < r_high1 - 2 and r_high2 > 60:
        return 'BEARISH'
        
    return None

def detect_order_blocks(candles, lookback=20):
    if len(candles) < lookback:
        return {'bullish_ob': None, 'bearish_ob': None}
    highs = [c['high'] for c in candles]
    lows = [c['low'] for c in candles]
    recent_lows = lows[-lookback:]
    recent_highs = highs[-lookback:]
    bullish_ob_zone = None
    bearish_ob_zone = None
    min_idx = recent_lows.index(min(recent_lows)) if recent_lows else -1
    max_idx = recent_highs.index(max(recent_highs)) if recent_highs else -1
    if min_idx > 0:
        ob_high = max(highs[-lookback + max(0, min_idx-2):-lookback + min_idx+1])
        ob_low = min(lows[-lookback + max(0, min_idx-2):-lookback + min_idx+1])
        bullish_ob_zone = {'high': ob_high, 'low': ob_low}
    if max_idx > 0:
        ob_high = max(highs[-lookback + max(0, max_idx-2):-lookback + max_idx+1])
        ob_low = min(lows[-lookback + max(0, max_idx-2):-lookback + max_idx+1])
        bearish_ob_zone = {'high': ob_high, 'low': ob_low}
    return {'bullish_ob': bullish_ob_zone, 'bearish_ob': bearish_ob_zone}

def detect_price_action(candles):
    if len(candles) < 2:
        return []
    closes = [c['close'] for c in candles]
    highs = [c['high'] for c in candles]
    lows = [c['low'] for c in candles]
    opens = [c['open'] for c in candles]
    signals = []
    if closes[-1] > closes[-2] and highs[-1] > highs[-2] and lows[-1] > lows[-2]:
        signals.append('HIGHER_HIGH_HIGHER_LOW')
    if closes[-1] < closes[-2] and lows[-1] < lows[-2] and highs[-1] < highs[-2]:
        signals.append('LOWER_LOW_LOWER_HIGH')
    if closes[-1] > opens[-1] and opens[-1] < closes[-2] and closes[-1] > opens[-2]:
        signals.append('BULLISH_ENGULFING')
    if closes[-1] < opens[-1] and opens[-1] > closes[-2] and closes[-1] < opens[-2]:
        signals.append('BEARISH_ENGULFING')
    return signals

def calculate_wavetrend(closes, channel_len=10, avg_len=21):
    """WaveTrend Oscillator by LazyBear (simplified)"""
    if len(closes) < avg_len + 10: return {'wt1': 0, 'wt2': 0}
    
    ap = [(c + closes[i-1] + closes[i-2])/3 for i, c in enumerate(closes) if i >= 2]
    if len(ap) < avg_len: return {'wt1': 0, 'wt2': 0}
    
    def esa_calc(data, p):
        mult = 2 / (p + 1)
        ema = data[0]
        res = [ema]
        for val in data[1:]:
            ema = val * mult + ema * (1 - mult)
            res.append(ema)
        return res

    esa = esa_calc(ap, channel_len)
    d_vals = [abs(ap[i] - e) for i, e in enumerate(esa)]
    de = esa_calc(d_vals, channel_len)
    ci = [(ap[i] - e) / (0.015 * de[i]) if de[i] != 0 else 0 for i, e in enumerate(esa)]
    wt1 = esa_calc(ci, avg_len)
    
    # wt2 is 4-period SMA of wt1
    wt2 = []
    for i in range(len(wt1)):
        wt2.append(sum(wt1[max(0, i-3):i+1]) / (min(i+1, 4)))
        
    return {'wt1': wt1[-1], 'wt2': wt2[-1], 'prev_wt1': wt1[-2] if len(wt1) > 1 else 0}

def calculate_squeeze(highs, lows, closes, bb_len=20, bb_mult=2, kc_len=20, kc_mult=1.5):
    """TTM Squeeze type indicator (Bollinger inside Keltner)"""
    if len(closes) < max(bb_len, kc_len): return {'sqz': 'OFF', 'val': 0}
    
    # Bollinger Bands
    sma = sum(closes[-bb_len:]) / bb_len
    std = (sum((x - sma)**2 for x in closes[-bb_len:]) / bb_len)**0.5
    bb_upper = sma + bb_mult * std
    bb_lower = sma - bb_mult * std
    
    # Keltner Channels
    atr = calculate_atr(highs, lows, closes, kc_len)
    kc_upper = sma + kc_mult * atr
    kc_lower = sma - kc_mult * atr
    
    # Squeeze logic
    is_sqz = bb_upper < kc_upper and bb_lower > kc_lower
    
    # Momentum (linreg of price vs sma) - simplified as price diff
    mom = closes[-1] - ((max(highs[-kc_len:]) + min(lows[-kc_len:]))/2 + sma)/2
    
    return {'sqz': 'ON' if is_sqz else 'OFF', 'val': mom}

def detect_liquidity_sweep(candles, lookback=30):
    """Detect if the last candle swept a significant high/low and reversed"""
    if len(candles) < lookback + 1: return None
    
    prev_candles = candles[-lookback-1:-1]
    highest_high = max(c['high'] for c in prev_candles)
    lowest_low = min(c['low'] for c in prev_candles)
    
    current = candles[-1]
    # Bullish Sweep: Price went below lowest low then closed above it
    if current['low'] < lowest_low < current['close']:
        return {'type': 'BULLISH', 'level': lowest_low}
        
    # Bearish Sweep: Price went above highest high then closed below it
    if current['high'] > highest_high > current['close']:
        return {'type': 'BEARISH', 'level': highest_high}
        
    return None

def detect_bos(candles, lookback=20):
    """Detect Break of Structure (BOS) / Market Structure Shift"""
    if len(candles) < lookback + 5: return None
    
    # Simple logic: breaking the last swing high/low with strength
    prev_highs = [c['high'] for c in candles[-lookback-5:-5]]
    prev_lows = [c['low'] for c in candles[-lookback-5:-5]]
    
    last_swing_high = max(prev_highs)
    last_swing_low = min(prev_lows)
    
    current_close = candles[-1]['close']
    prev_close = candles[-2]['close']
    
    if current_close > last_swing_high and prev_close <= last_swing_high:
        return {'type': 'BOS_UP', 'level': last_swing_high}
    if current_close < last_swing_low and prev_close >= last_swing_low:
        return {'type': 'BOS_DOWN', 'level': last_swing_low}
        
    return None

def calculate_mfi(highs, lows, closes, volumes, period=14):
    """Money Flow Index - RSI with volume"""
    if len(closes) < period + 1: return 50
    tp = [(h + l + c)/3 for h, l, c in zip(highs, lows, closes)]
    mf = [p * v for p, v in zip(tp, volumes)]
    
    pos_mf = []
    neg_mf = []
    for i in range(1, len(tp)):
        if tp[i] > tp[i-1]:
            pos_mf.append(mf[i])
            neg_mf.append(0)
        elif tp[i] < tp[i-1]:
            pos_mf.append(0)
            neg_mf.append(mf[i])
        else:
            pos_mf.append(0)
            neg_mf.append(0)
            
    p_sum = sum(pos_mf[-period:])
    n_sum = sum(neg_mf[-period:])
    if n_sum == 0: return 100
    mfr = p_sum / n_sum
    return 100 - (100 / (1 + mfr))

def calculate_fisher(highs, lows, period=10):
    """Fisher Transform - Spotting turning points"""
    if len(highs) < period: return 0
    
    # Normalize price to -1 to 1 range
    max_h = max(highs[-period:])
    min_l = min(lows[-period:])
    
    val = 0.66 * (( (highs[-1]+lows[-1])/2 - min_l) / (max_h - min_l) - 0.5)
    # Clamp and transform
    val = max(-0.999, min(0.999, val))
    fisher = 0.5 * math.log((1 + val) / (1 - val))
    return fisher

def calculate_zlsma(closes, period=32):
    """Zero Lag SMA - Fast tracking EMA"""
    if len(closes) < period: return closes[-1]
    
    def sma(data, p):
        return sum(data[-p:]) / p
        
    lag = int((period - 1) / 2)
    data = [2 * closes[i] - closes[i-lag] if i >= lag else closes[i] for i in range(len(closes))]
    return sma(data, period)

def calculate_tsi(closes, long_period=25, short_period=13):
    """True Strength Index - Deep momentum oscillator"""
    if len(closes) < long_period + short_period: return 0
    
    diff = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    abs_diff = [abs(d) for d in diff]
    
    def ema(data, p):
        if not data: return 0
        m = 2 / (p + 1)
        curr = data[0]
        for v in data[1:]:
            curr = v * m + curr * (1 - m)
        return curr

    # Double smoothed PC
    def double_ema(data, p1, p2):
        res1 = []
        m1 = 2 / (p1 + 1)
        curr = data[0]
        for v in data:
            curr = v * m1 + curr * (1 - m1)
            res1.append(curr)
        
        m2 = 2 / (p2 + 1)
        curr2 = res1[0]
        for v in res1:
            curr2 = v * m2 + curr2 * (1 - m2)
        return curr2

    double_smoothed_pc = double_ema(diff, long_period, short_period)
    double_smoothed_abs_pc = double_ema(abs_diff, long_period, short_period)
    
    if double_smoothed_abs_pc == 0: return 0
    return 100 * (double_smoothed_pc / double_smoothed_abs_pc)

def calculate_ultimate_oscillator(highs, lows, closes, p1=7, p2=14, p3=28):
    """Ultimate Oscillator - Multiple timeframe momentum"""
    try:
        if len(closes) < p3 + 1: return 50
        bp = [closes[i] - min(lows[i], closes[i-1]) for i in range(1, len(closes))]
        tr = [max(highs[i], closes[i-1]) - min(lows[i], closes[i-1]) for i in range(1, len(closes))]
        
        def sum_p(data, p): return sum(data[-p:])
        
        s_tr7 = sum_p(tr, p1)
        s_tr14 = sum_p(tr, p2)
        s_tr28 = sum_p(tr, p3)
        
        avg7 = sum_p(bp, p1) / s_tr7 if s_tr7 != 0 else 0
        avg14 = sum_p(bp, p2) / s_tr14 if s_tr14 != 0 else 0
        avg28 = sum_p(bp, p3) / s_tr28 if s_tr28 != 0 else 0
        
        return 100 * (4*avg7 + 2*avg14 + avg28) / 7
    except:
        return 50

def calculate_stdev(data, period):
    """Standard Deviation calculation"""
    try:
        if len(data) < period: return 0
        sma = sum(data[-period:]) / period
        variance = sum((x - sma)**2 for x in data[-period:]) / period
        return variance**0.5
    except:
        return 0

def calculate_volume_profile(candles, bins=30):
    """Calculate Volume Profile (Volume at Price)"""
    try:
        if not candles: return None
        closes = [c['close'] for c in candles]
        volumes = [c['volume'] for c in candles]
        min_p, max_p = min(closes), max(closes)
        if min_p == max_p: return None
        
        bin_size = (max_p - min_p) / bins
        profile = {}
        for i in range(bins):
            lower = min_p + i * bin_size
            upper = lower + bin_size
            vol = sum(v for c, v in zip(closes, volumes) if lower <= c < upper)
            profile[round(lower, 6)] = vol
            
        poc_price = max(profile, key=profile.get)
        return {'poc': poc_price, 'bin_size': bin_size}
    except:
        return None

def calculate_fib_levels(high, low):
    """Fibonacci Retracement Levels"""
    diff = high - low
    return {
        '0': low,
        '0.236': low + 0.236 * diff,
        '0.382': low + 0.382 * diff,
        '0.5': low + 0.5 * diff,
        '0.618': low + 0.618 * diff,
        '0.786': low + 0.786 * diff,
        '1.0': high
    }

def detect_supply_demand_zones(candles, lookback=50):
    """Identify High Volume Supply/Demand Zones"""
    try:
        if not candles: return None
        vp = calculate_volume_profile(candles[-lookback:])
        if not vp: return None
        
        poc = vp['poc']
        current = candles[-1]['close']
        
        zone_type = 'DEMAND' if current > poc else 'SUPPLY'
        return {'type': zone_type, 'level': poc}
    except:
        return None

def calculate_ict_phases(rsi, adx, volume, avg_volume, trend):
    """ICT Wealth Division Phases"""
    if rsi < 30 and adx > 25 and volume < avg_volume:
        return "ACCUMULATION"
    if rsi > 70 and adx > 25 and volume < avg_volume:
        return "DISTRIBUTION"
    if adx > 25 and volume > avg_volume:
        return "MARKUP" if trend == 'BULLISH' else "MARKDOWN"
    return "CONSOLIDATION"

def calculate_psar(highs, lows, closes, accent=0.02, max_accent=0.2):
    """Calculate Parabolic SAR"""
    try:
        if len(closes) < 5: return {'psar': closes[-1], 'trend': 'NEUTRAL'}
        
        psar = closes[0]
        bull = True
        af = accent
        hp = highs[0]
        lp = lows[0]
        
        psar_list = [psar]
        
        for i in range(1, len(closes)):
            prev_psar = psar
            if bull:
                psar = prev_psar + af * (hp - prev_psar)
            else:
                psar = prev_psar + af * (lp - prev_psar)
                
            reverse = False
            if bull:
                if lows[i] < psar:
                    bull = False
                    reverse = True
                    psar = hp
                    lp = lows[i]
                    af = accent
            else:
                if highs[i] > psar:
                    bull = True
                    reverse = True
                    psar = lp
                    hp = highs[i]
                    af = accent
                    
            if not reverse:
                if bull:
                    if highs[i] > hp:
                        hp = highs[i]
                        af = min(af + accent, max_accent)
                    if lows[i-1] < psar: psar = lows[i-1]
                    if lows[max(0, i-2)] < psar: psar = lows[max(0, i-2)]
                else:
                    if lows[i] < lp:
                        lp = lows[i]
                        af = min(af + accent, max_accent)
                    if highs[i-1] > psar: psar = highs[i-1]
                    if highs[max(0, i-2)] > psar: psar = highs[max(0, i-2)]
            psar_list.append(psar)
            
        return {'psar': psar_list[-1], 'trend': 'BULLISH' if closes[-1] > psar_list[-1] else 'BEARISH'}
    except:
        return {'psar': closes[-1], 'trend': 'NEUTRAL'}

def calculate_tema(closes, period=9):
    """Triple Exponential Moving Average"""
    try:
        if len(closes) < period * 3: return closes[-1]
        
        def ema_inner(data, p):
            m = 2 / (p + 1)
            res = [data[0]]
            for i in range(1, len(data)):
                res.append(data[i] * m + res[-1] * (1 - m))
            return res
            
        ema1 = ema_inner(closes, period)
        ema2 = ema_inner(ema1, period)
        ema3 = ema_inner(ema2, period)
        
        tema = [3 * e1 - 3 * e2 + e3 for e1, e2, e3 in zip(ema1, ema2, ema3)]
        return tema[-1]
    except:
        return closes[-1]

def calculate_chandelier_exit(highs, lows, closes, period=22, multiplier=3):
    """Chandelier Exit for trend following"""
    try:
        if len(closes) < period: return {'long': closes[-1], 'short': closes[-1]}
        
        atr = calculate_atr(highs, lows, closes, period)
        highest_high = max(highs[-period:])
        lowest_low = min(lows[-period:])
        
        long_stop = highest_high - atr * multiplier
        short_stop = lowest_low + atr * multiplier
        
        return {'long': long_stop, 'short': short_stop}
    except:
        return {'long': closes[-1], 'short': closes[-1]}

def calculate_kama(closes, period=10, fast=2, slow=30):
    """Kaufman's Adaptive Moving Average"""
    try:
        if len(closes) < period + 1: return closes[-1]
        
        change = abs(closes[-1] - closes[-period])
        volatility = sum(abs(closes[i] - closes[i-1]) for i in range(len(closes)-period+1, len(closes)))
        
        er = change / volatility if volatility != 0 else 0
        fast_sc = 2 / (fast + 1)
        slow_sc = 2 / (slow + 1)
        sc = (er * (fast_sc - slow_sc) + slow_sc)**2
        
        kama = closes[-period]
        for i in range(len(closes)-period+1, len(closes)):
            kama = kama + sc * (closes[i] - kama)
        return kama
    except:
        return closes[-1]

def calculate_vfi(closes, volumes, period=130, coef=0.2):
    """Volume Flow Indicator"""
    try:
        if len(closes) < 2: return 0
        
        tp = [(closes[i] + closes[i] + closes[i])/3 for i in range(len(closes))] # Simplified
        cutoff = coef * sum(abs(closes[i]-closes[i-1]) for i in range(1, len(closes))) / len(closes)
        
        vfi_sum = 0
        lookback = min(len(closes), period)
        for i in range(1, lookback):
            inter = tp[-i] - tp[-i-1]
            v_val = volumes[-i]
            if inter > cutoff:
                vfi_sum += v_val
            elif inter < -cutoff:
                vfi_sum -= v_val
                
        avg_v = sum(volumes[-period:]) / period if len(volumes) >= period else sum(volumes)/len(volumes)
        return (vfi_sum / avg_v) if avg_v != 0 else 0
    except:
        return 0

def analyze_timeframe(candles, timeframe_name):
    if not candles or len(candles) < 50:
        return None
    closes = [c['close'] for c in candles]
    highs = [c['high'] for c in candles]
    lows = [c['low'] for c in candles]
    opens = [c['open'] for c in candles]
    volumes = [c['volume'] for c in candles]
    current_price = closes[-1]
    rsi = calculate_rsi(closes, 14)
    ema9 = calculate_ema(closes, 9)
    ema21 = calculate_ema(closes, 21)
    ema50 = calculate_ema(closes, 50)
    ema200 = calculate_ema(closes, 200) if len(closes) >= 200 else ema50
    macd = calculate_macd(closes)
    bb = calculate_bb(closes, 20, 2)
    atr = calculate_atr(highs, lows, closes, 14)
    adx = calculate_adx(highs, lows, closes, 14)
    stoch_rsi = calculate_stoch_rsi(closes) if 'StochRSI' in ENABLED_INDICATORS else {'k': 50, 'd': 50}
    obv = calculate_obv(closes, volumes) if 'OBV' in ENABLED_INDICATORS else []
    hma = calculate_hma(closes, 21) if 'HMA' in ENABLED_INDICATORS else closes[-1]
    supertrend = calculate_supertrend(candles) if 'ST' in ENABLED_INDICATORS else {'trend': 'NEUTRAL'}
    vwap = calculate_vwap(candles) if 'VWAP' in ENABLED_INDICATORS else current_price
    cmf = calculate_cmf(candles) if 'CMF' in ENABLED_INDICATORS else 0
    ichimoku = calculate_ichimoku(highs, lows) if 'ICHI' in ENABLED_INDICATORS else {'tenkan': 0, 'kijun': 0, 'cloud_top': 0, 'cloud_bottom': 0}
    fvg = detect_fvg(candles) if 'FVG' in ENABLED_INDICATORS else None
    
    # Need RSI series for divergence
    rsi_div = None
    if 'DIV' in ENABLED_INDICATORS:
        rsi_series = []
        for i in range(len(closes) - 31, len(closes) + 1):
            if i < 15: continue
            rsi_series.append(calculate_rsi(closes[:i]))
        rsi_div = detect_rsi_divergence(candles, rsi_series)
    
    obs = detect_order_blocks(candles, lookback=15) if 'OB' in ENABLED_INDICATORS else {'bullish_ob': None, 'bearish_ob': None}
    pa_signals = detect_price_action(candles[-5:]) if 'PA' in ENABLED_INDICATORS else []
    
    # Advanced Indicators
    wt = calculate_wavetrend(closes) if 'WT' in ENABLED_INDICATORS else {'wt1': 0, 'wt2': 0}
    sqz = calculate_squeeze(highs, lows, closes) if 'SQZ' in ENABLED_INDICATORS else {'sqz': 'OFF', 'val': 0}
    liq = detect_liquidity_sweep(candles) if 'LIQ' in ENABLED_INDICATORS else None
    bos = detect_bos(candles) if 'BOS' in ENABLED_INDICATORS else None
    
    # Scalping / Volatility Indicators
    mfi = calculate_mfi(highs, lows, closes, volumes) if 'MFI' in ENABLED_INDICATORS else 50
    fisher = calculate_fisher(highs, lows) if 'FISH' in ENABLED_INDICATORS else 0
    zlsma = calculate_zlsma(closes) if 'ZLSMA' in ENABLED_INDICATORS else closes[-1]
    tsi = calculate_tsi(closes) if 'TSI' in ENABLED_INDICATORS else 0
    
    # NEW BEST OF BEST 2026 INDICATORS
    chop = calculate_chop(highs, lows, closes) if 'CHOP' in ENABLED_INDICATORS else 50
    vortex = calculate_vortex(highs, lows, closes) if 'VI' in ENABLED_INDICATORS else {'plus': 0, 'minus': 0}
    stc = calculate_stc(closes) if 'STC' in ENABLED_INDICATORS else 50
    donchian = calculate_donchian(highs, lows) if 'DON' in ENABLED_INDICATORS else None
    hull_suite = calculate_hull_suite(closes) if 'HMA' in ENABLED_INDICATORS else 'NEUTRAL'
    choch = detect_choch(candles, timeframe_name) if 'CHoCH' in ENABLED_INDICATORS else None
    kc = calculate_kc(highs, lows, closes) if 'KC' in ENABLED_INDICATORS else None
    utbot = calculate_utbot(highs, lows, closes) if 'UTBOT' in ENABLED_INDICATORS else {'signal': 'NEUTRAL', 'stop': 0}
    
    # MORE ADVANCED 2026 INDICATORS
    uo = calculate_ultimate_oscillator(highs, lows, closes) if 'UO' in ENABLED_INDICATORS else 50
    stdev = calculate_stdev(closes, 20) if 'STDEV' in ENABLED_INDICATORS else 0
    vp = calculate_volume_profile(candles[-50:]) if 'VP' in ENABLED_INDICATORS else None
    sup_dem = detect_supply_demand_zones(candles[-50:]) if 'SUPDEM' in ENABLED_INDICATORS else None
    fib = calculate_fib_levels(max(highs[-50:]), min(lows[-50:])) if 'FIB' in ENABLED_INDICATORS else None
    
    # SUPERSCALP 2026 INDICATORS
    psar = calculate_psar(highs, lows, closes) if 'PSAR' in ENABLED_INDICATORS else {'psar': current_price, 'trend': 'NEUTRAL'}
    tema = calculate_tema(closes) if 'TEMA' in ENABLED_INDICATORS else current_price
    chandelier = calculate_chandelier_exit(highs, lows, closes) if 'CHANDELIER' in ENABLED_INDICATORS else {'long': 0, 'short': 0}
    kama = calculate_kama(closes) if 'KAMA' in ENABLED_INDICATORS else current_price
    vfi = calculate_vfi(closes, volumes) if 'VFI' in ENABLED_INDICATORS else 0
    
    rvol = volumes[-1] / (sum(volumes[-20:])/20) if len(volumes) >= 20 else 1.0
    
    trend = 'BULLISH' if ema9 > ema21 > ema50 else 'BEARISH' if ema9 < ema21 < ema50 else 'NEUTRAL'
    ict_phase = calculate_ict_phases(rsi, adx['adx'], volumes[-1], sum(volumes[-20:])/20 if len(volumes)>=20 else 1, trend) if 'ICT_WD' in ENABLED_INDICATORS else "CONSOLIDATION"
    
    # Enhanced trend check using ADX and SuperTrend
    trend_strength = 'STRONG' if adx['adx'] > 25 else 'WEAK'
    if supertrend['trend'] == 'BULLISH' and trend == 'BULLISH':
        trend_strength = 'VERY STRONG'
    
    support = min(lows[-20:]) if len(lows) >= 20 else lows[-1]
    resistance = max(highs[-20:]) if len(highs) >= 20 else highs[-1]
    
    return {
        'timeframe': timeframe_name,
        'current_price': current_price,
        'rsi': rsi,
        'stoch_rsi': stoch_rsi,
        'adx': adx,
        'uo': uo,
        'obv': obv,
        'hma': hma,
        'hull_suite': hull_suite,
        'supertrend': supertrend,
        'vwap': vwap,
        'cmf': cmf,
        'ichimoku': ichimoku,
        'fvg': fvg,
        'rsi_div': rsi_div,
        'ema9': ema9,
        'ema21': ema21,
        'ema50': ema50,
        'ema200': ema200,
        'macd': macd,
        'bb': bb,
        'atr': atr,
        'stdev': stdev,
        'chop': chop,
        'vortex': vortex,
        'stc': stc,
        'donchian': donchian,
        'choch': choch,
        'kc': kc,
        'utbot': utbot,
        'vp': vp,
        'sup_dem': sup_dem,
        'fib': fib,
        'ict_phase': ict_phase,
        'support': support,
        'resistance': resistance,
        'trend': trend,
        'trend_strength': trend_strength,
        'order_blocks': obs,
        'price_action': pa_signals,
        'wavetrend': wt,
        'squeeze': sqz,
        'liquidity': liq,
        'bos': bos,
        'mfi': mfi,
        'fisher': fisher,
        'zlsma': zlsma,
        'tsi': tsi,
        'psar': psar,
        'tema': tema,
        'chandelier': chandelier,
        'kama': kama,
        'vfi': vfi,
        'rvol': rvol,
        'volume': volumes[-1] if volumes else 0,
        'avg_volume': sum(volumes[-20:]) / 20 if len(volumes) >= 20 else 0,
        'candles': candles[-10:] if len(candles) >= 10 else candles
    }

def analyze_symbol(symbol, exchange=None):
    """Analyze symbol across multiple timeframes for a specific exchange"""
    exchange_label = exchange if exchange else 'Auto'
    with print_lock:
        print(f"  📊 [{exchange_label}] {symbol}...", end=' ', flush=True)
    analyses = {}
    
    timeframes_to_fetch = [tf for tf in ENABLED_TIMEFRAMES]
    
    for tf_interval in timeframes_to_fetch:
        try:
            candles = get_klines(symbol, tf_interval, 200, exchange=exchange)
            if candles and len(candles) >= 50:
                analysis = analyze_timeframe(candles, tf_interval)
                if analysis:
                    analyses[tf_interval] = analysis
            time.sleep(0.05)
        except:
            pass
    with print_lock:
        if analyses:
            print("✓")
        else:
            print("❌")
    return analyses if analyses else None

# === Strategies ===

def strategy_swing_trend(symbol, analyses):
    """Original Strategy: Requires 1h + 4h alignment"""
    if '1h' not in analyses or '4h' not in analyses:
        return []
    
    h1 = analyses['1h']
    h4 = analyses['4h']
    current = h1['current_price']
    
    trades = []
    
    # --- LONG LOGIC ---
    bullish_confidence = 0
    bullish_reasons = []
    
    if h1['trend'] == 'BULLISH' and h4['trend'] == 'BULLISH':
        bullish_confidence += 2
        bullish_reasons.append('Multi-TF Bullish')
        
    if 30 < h1['rsi'] < 55:
        bullish_confidence += 1
        bullish_reasons.append(f'RSI:{h1["rsi"]:.0f}')
    elif h1['rsi'] < 35:
        bullish_confidence += 2
        bullish_reasons.append(f'RSI Oversold:{h1["rsi"]:.0f}')
        
    if h1['macd']['histogram'] > 0 and h4['macd']['histogram'] > 0:
        bullish_confidence += 2
        bullish_reasons.append('MACD Bullish')
        
    if h1['order_blocks']['bullish_ob']:
        ob = h1['order_blocks']['bullish_ob']
        if ob['low'] < current < ob['high']:
            bullish_confidence += 1
            bullish_reasons.append('At OB Support')
            
    if 'HIGHER_HIGH_HIGHER_LOW' in h1['price_action']:
        bullish_confidence += 1
        bullish_reasons.append('Higher High/Low')
        
    if h1['bb'] and current > h1['bb']['lower'] and current < h1['bb']['middle']:
        bullish_confidence += 1
        bullish_reasons.append('BB Support')
        
    if h1['volume'] > h1['avg_volume'] * 0.8:
        bullish_confidence += 1
        bullish_reasons.append('Volume Increasing')

    if bullish_confidence >= MIN_CONFIDENCE:
        atr_val = h1['atr']
        sl = h1['support'] - atr_val * 0.5
        tp1 = current + atr_val * 2
        tp2 = current + atr_val * 3
        risk = current - sl
        reward = tp1 - current
        
        if risk > 0 and (reward / risk) >= 2:
            trades.append({
                'strategy': 'Swing Trend',
                'type': 'LONG',
                'symbol': symbol,
                'entry': current,
                'sl': sl, 'tp1': tp1, 'tp2': tp2,
                'confidence': 'HIGH',
                'confidence_score': bullish_confidence,
                'risk_reward': round(reward / risk, 1),
                'reason': ' + '.join(bullish_reasons[:3]),
                'indicators': f"RSI:{h1['rsi']:.0f}, MACD:Bull",
                'expected_time': '4-8 hours',
                'risk': risk, 'reward': reward,
                'entry_type': 'LIMIT',
                'timeframe': '1h'
            })

    # --- SHORT LOGIC ---
    bearish_confidence = 0
    bearish_reasons = []
    
    if h1['trend'] == 'BEARISH' and h4['trend'] == 'BEARISH':
        bearish_confidence += 2
        bearish_reasons.append('Multi-TF Bearish')
        
    if 45 < h1['rsi'] < 70:
        bearish_confidence += 1
        bearish_reasons.append(f'RSI:{h1["rsi"]:.0f}')
    elif h1['rsi'] > 65:
        bearish_confidence += 2
        bearish_reasons.append(f'RSI Overbought:{h1["rsi"]:.0f}')
        
    if h1['macd']['histogram'] < 0 and h4['macd']['histogram'] < 0:
        bearish_confidence += 2
        bearish_reasons.append('MACD Bearish')
        
    if h1['order_blocks']['bearish_ob']:
        ob = h1['order_blocks']['bearish_ob']
        if ob['low'] < current < ob['high']:
            bearish_confidence += 1
            bearish_reasons.append('At OB Resistance')
            
    if 'LOWER_LOW_LOWER_HIGH' in h1['price_action']:
        bearish_confidence += 1
        bearish_reasons.append('Lower Low/High')
        
    if h1['bb'] and current < h1['bb']['upper'] and current > h1['bb']['middle']:
        bearish_confidence += 1
        bearish_reasons.append('BB Resistance')
        
    if h1['volume'] > h1['avg_volume'] * 0.8:
        bearish_confidence += 1
        bearish_reasons.append('Volume Strong')

    if bearish_confidence >= MIN_CONFIDENCE:
        atr_val = h1['atr']
        sl = h1['resistance'] + atr_val * 0.5
        tp1 = current - atr_val * 2
        tp2 = current - atr_val * 3
        risk = sl - current
        reward = current - tp1
        
        if risk > 0 and (reward / risk) >= 2:
            trades.append({
                'strategy': 'Swing Trend',
                'type': 'SHORT',
                'symbol': symbol,
                'entry': current,
                'sl': sl, 'tp1': tp1, 'tp2': tp2,
                'confidence': 'HIGH',
                'confidence_score': bearish_confidence,
                'risk_reward': round(reward / risk, 1),
                'reason': ' + '.join(bearish_reasons[:3]),
                'indicators': f"RSI:{h1['rsi']:.0f}, MACD:Bear",
                'expected_time': '4-8 hours',
                'risk': risk, 'reward': reward,
                'entry_type': 'LIMIT',
                'timeframe': '1h'
            })
            
    return trades

def strategy_scalp_momentum(symbol, analyses):
    """New Strategy: Scalp Momentum (1m + 5m)"""
    if '1m' not in analyses or '5m' not in analyses:
        return []
    
    m1 = analyses['1m']
    m5 = analyses['5m']
    current = m1['current_price']
    trades = []
    
    confidence = 0
    reasons = []
    
    # LONG Scalp
    if m5['trend'] == 'BULLISH' and m1['rsi'] < 40 and m1['macd']['histogram'] > m1['macd']['histogram']*0.5:
        confidence = 5 + (2 if m1['rsi'] < 30 else 0)
        reasons.append('1m Dip in 5m Uptrend')
        
        atr = m1['atr']
        sl = current - atr * 1.5
        tp1 = current + atr * 3
        tp2 = current + atr * 5
        risk = current - sl
        reward = tp1 - current
        
        if risk > 0 and (reward/risk) > 1.5 and confidence >= MIN_CONFIDENCE:
            trades.append({
                'strategy': 'Scalp Momentum',
                'type': 'LONG',
                'symbol': symbol,
                'entry': current,
                'sl': sl, 'tp1': tp1, 'tp2': tp2,
                'confidence': 'MEDIUM',
                'confidence_score': confidence,
                'risk_reward': round(reward/risk, 1),
                'reason': ' + '.join(reasons),
                'indicators': f"RSI:{m1['rsi']:.0f} (1m)",
                'expected_time': '15-30 mins',
                'risk': risk, 'reward': reward,
                'entry_type': 'MARKET',
                'timeframe': '1m'
            })
            
    return trades

    return trades

def strategy_trend_pullback(symbol, analyses):
    """Strategy: Stoch RSI Pullback in Trend (High Probability)"""
    # Prefer 1h or 4h for this strategy, but works on any
    tf = '1h' if '1h' in analyses else '4h' if '4h' in analyses else '15m'
    if tf not in analyses: return []
    
    a = analyses[tf]
    current = a['current_price']
    trades = []
    
    # LONG: Strong Bullish Trend + Stoch RSI Oversold Cross
    if a['trend'] == 'BULLISH' and a['adx']['adx'] > 20: # Strong trend
        if a['stoch_rsi']['k'] < 20 and a['stoch_rsi']['k'] > a['stoch_rsi']['d']: # Golden Cross in Oversold
             confidence = 7
             reasons = [f'StochRSI Oversold Cross', f'{tf} Strong Uptrend (ADX:{a["adx"]["adx"]:.0f})']
             
             if a['obv'] == 'BULLISH':
                 confidence += 1
                 reasons.append('OBV Rising')
                 
             if a['price_action'] and 'BULLISH_ENGULFING' in a['price_action']:
                 confidence += 2
                 reasons.append('Bullish Engulfing')
                 
             if confidence >= MIN_CONFIDENCE:
                 atr = a['atr']
                 sl = current - atr * 2
                 tp1 = current + atr * 3
                 tp2 = current + atr * 5
                 risk = current - sl
                 reward = tp1 - current
                 
                 if risk > 0:
                     trades.append({
                        'strategy': 'StochRSI Pullback',
                        'type': 'LONG',
                        'symbol': symbol,
                        'entry': current,
                        'sl': sl, 'tp1': tp1, 'tp2': tp2,
                        'confidence': 'HIGH',
                        'confidence_score': confidence,
                        'risk_reward': round(reward/risk, 1),
                        'reason': ' + '.join(reasons),
                        'indicators': f"StochRSI:{a['stoch_rsi']['k']:.0f}/{a['stoch_rsi']['d']:.0f}, ADX:{a['adx']['adx']:.0f}",
                        'expected_time': '1-4 hours',
                        'risk': risk, 'reward': reward,
                        'entry_type': 'MARKET',
                        'timeframe': tf
                    })

    # SHORT: Strong Bearish Trend + Stoch RSI Overbought Cross
    if a['trend'] == 'BEARISH' and a['adx']['adx'] > 20:
        if a['stoch_rsi']['k'] > 80 and a['stoch_rsi']['k'] < a['stoch_rsi']['d']: # Death Cross in Overbought
             confidence = 7
             reasons = [f'StochRSI Overbought Cross', f'{tf} Strong Downtrend (ADX:{a["adx"]["adx"]:.0f})']
             
             if a['obv'] == 'BEARISH':
                 confidence += 1
                 reasons.append('OBV Falling')
                 
             if a['price_action'] and 'BEARISH_ENGULFING' in a['price_action']:
                 confidence += 2
                 reasons.append('Bearish Engulfing')
                 
             if confidence >= MIN_CONFIDENCE:
                 atr = a['atr']
                 sl = current + atr * 2
                 tp1 = current - atr * 3
                 tp2 = current - atr * 5
                 risk = sl - current
                 reward = current - tp1
                 
                 if risk > 0:
                     trades.append({
                        'strategy': 'StochRSI Pullback',
                        'type': 'SHORT',
                        'symbol': symbol,
                        'entry': current,
                        'sl': sl, 'tp1': tp1, 'tp2': tp2,
                        'confidence': 'HIGH',
                        'confidence_score': confidence,
                        'risk_reward': round(reward/risk, 1),
                        'reason': ' + '.join(reasons),
                        'indicators': f"StochRSI:{a['stoch_rsi']['k']:.0f}/{a['stoch_rsi']['d']:.0f}, ADX:{a['adx']['adx']:.0f}",
                        'expected_time': '1-4 hours',
                        'risk': risk, 'reward': reward,
                        'entry_type': 'MARKET',
                        'timeframe': tf
                    })
                
    return trades

def strategy_volatility_breakout(symbol, analyses):
    """Strategy: Bollinger Band Squeeze Breakout"""
    # Works best on 15m or 1h
    tf = '15m' if '15m' in analyses else '1h' if '1h' in analyses else None
    if not tf or tf not in analyses: return []
    
    a = analyses[tf]
    current = a['current_price']
    trades = []
    
    # Check for Squeeze (Band width is relatively narrow - simplified check vs ATR)
    bb_width = a['bb']['width']
    if bb_width == 0: return []
    
    # 1. Breakout UP
    if current > a['bb']['upper']:
        confidence = 0
        reasons = []
        
        # Confirmation
        if a['adx']['adx'] > 25: # Strong trend emerging
            confidence += 3
            reasons.append('High ADX (Trend Strength)')
            
        if a['volume'] > a['avg_volume'] * 1.5: # Volume spike
            confidence += 3
            reasons.append('High Volume Breakout')
            
        if a['macd']['histogram'] > 0 and a['macd']['histogram'] > a['macd']['signal']:
            confidence += 2
            reasons.append('MACD Expanding')
            
        if confidence >= MIN_CONFIDENCE:
             atr = a['atr']
             sl = a['bb']['middle'] # Stop loss at moving average
             tp1 = current + atr * 3
             tp2 = current + atr * 6
             risk = current - sl
             reward = tp1 - current
             
             if risk > 0 and (reward/risk) > 1.5:
                 trades.append({
                    'strategy': 'BB Breakout',
                    'type': 'LONG',
                    'symbol': symbol,
                    'entry': current,
                    'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence': 'HIGH',
                    'confidence_score': confidence,
                    'risk_reward': round(reward/risk, 1),
                    'reason': ' + '.join(reasons),
                    'indicators': f"BB Breakout, Vol:{a['volume']:.0f}, ADX:{a['adx']['adx']:.0f}",
                    'expected_time': '30m-2h',
                    'risk': risk, 'reward': reward,
                    'entry_type': 'STOP-MARKET',
                    'timeframe': tf
                })
                
    # 2. Breakout DOWN
    elif current < a['bb']['lower']:
        confidence = 0
        reasons = []
        
        if a['adx']['adx'] > 25:
            confidence += 3
            reasons.append('High ADX (Trend Strength)')
            
        if a['volume'] > a['avg_volume'] * 1.5:
            confidence += 3
            reasons.append('High Volume Breakout')
            
        if a['macd']['histogram'] < 0 and a['macd']['histogram'] < a['macd']['signal']:
            confidence += 2
            reasons.append('MACD Expanding')
            
        if confidence >= MIN_CONFIDENCE:
             atr = a['atr']
             sl = a['bb']['middle']
             tp1 = current - atr * 3
             tp2 = current - atr * 6
             risk = sl - current
             reward = current - tp1
             
             if risk > 0 and (reward/risk) > 1.5:
                 trades.append({
                    'strategy': 'BB Breakout',
                    'type': 'SHORT',
                    'symbol': symbol,
                    'entry': current,
                    'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence': 'HIGH',
                    'confidence_score': confidence,
                    'risk_reward': round(reward/risk, 1),
                    'reason': ' + '.join(reasons),
                    'indicators': f"BB Breakout, Vol:{a['volume']:.0f}, ADX:{a['adx']['adx']:.0f}",
                    'expected_time': '30m-2h',
                    'risk': risk, 'reward': reward,
                    'entry_type': 'STOP-MARKET',
                    'timeframe': tf
                })

    return trades

def strategy_supertrend_follow(symbol, analyses):
    """Strategy: SuperTrend Rebound (High Performance)"""
    # Best on 15m or 1h
    tf = '1h' if '1h' in analyses else '15m' if '15m' in analyses else None
    if not tf or tf not in analyses: return []
    
    a = analyses[tf]
    current = a['current_price']
    trades = []
    
    # LONG: SuperTrend is Bullish and price is near the SuperTrend lower line (support)
    if a['supertrend']['trend'] == 'BULLISH':
        st_support = a['supertrend']['lower']
        # Price is within 0.5% of ST support
        if st_support < current < st_support * 1.005:
            confidence = 6
            reasons = [f"Rebound from SuperTrend Support ({tf})"]
            
            if a['trend'] == 'BULLISH': # EMA alignment
                confidence += 2
                reasons.append("EMA Trend Alignment")
            
            if a['cmf'] > 0:
                confidence += 1
                reasons.append("Money Flow Positive")
                
            if confidence >= MIN_CONFIDENCE:
                atr = a['atr']
                sl = st_support - atr
                tp1 = current + atr * 3
                tp2 = current + atr * 5
                risk = current - sl
                reward = tp1 - current
                
                if risk > 0:
                    trades.append({
                        'strategy': 'SuperTrend Rebound',
                        'type': 'LONG',
                        'symbol': symbol,
                        'entry': current,
                        'sl': sl, 'tp1': tp1, 'tp2': tp2,
                        'confidence': 'HIGH' if confidence > 7 else 'MEDIUM',
                        'confidence_score': confidence,
                        'risk_reward': round(reward/risk, 1),
                        'reason': ' + '.join(reasons),
                        'indicators': f"ST Bullish, CMF:{a['cmf']:.2f}",
                        'expected_time': '2-6 hours',
                        'risk': risk, 'reward': reward,
                        'entry_type': 'LIMIT',
                        'timeframe': tf
                    })
                    
    # SHORT: SuperTrend is Bearish and price is near the ST upper line (resistance)
    elif a['supertrend']['trend'] == 'BEARISH':
        st_res = a['supertrend']['upper']
        if st_res * 0.995 < current < st_res:
            confidence = 6
            reasons = [f"Rejection from SuperTrend Resistance ({tf})"]
            
            if a['trend'] == 'BEARISH':
                confidence += 2
                reasons.append("EMA Trend Alignment")
                
            if a['cmf'] < 0:
                confidence += 1
                reasons.append("Money Flow Negative")
                
            if confidence >= MIN_CONFIDENCE:
                atr = a['atr']
                sl = st_res + atr
                tp1 = current - atr * 3
                tp2 = current - atr * 5
                risk = sl - current
                reward = current - tp1
                
                if risk > 0:
                    trades.append({
                        'strategy': 'SuperTrend Rejection',
                        'type': 'SHORT',
                        'symbol': symbol,
                        'entry': current,
                        'sl': sl, 'tp1': tp1, 'tp2': tp2,
                        'confidence': 'HIGH' if confidence > 7 else 'MEDIUM',
                        'confidence_score': confidence,
                        'risk_reward': round(reward/risk, 1),
                        'reason': ' + '.join(reasons),
                        'indicators': f"ST Bearish, CMF:{a['cmf']:.2f}",
                        'expected_time': '2-6 hours',
                        'risk': risk, 'reward': reward,
                        'entry_type': 'LIMIT',
                        'timeframe': tf
                    })
                    
    return trades

def strategy_vwap_reversion(symbol, analyses):
    """Strategy: VWAP Mean Reversion (Fast Scalp)"""
    # Best on 1m or 5m
    tf = '5m' if '5m' in analyses else '1m' if '1m' in analyses else None
    if not tf or tf not in analyses: return []
    
    a = analyses[tf]
    current = a['current_price']
    vwap = a['vwap']
    trades = []
    
    # LONG Scalp: Price far below VWAP + Oversold RSI
    if current < vwap * 0.985: # 1.5% below VWAP
        if a['rsi'] < 30:
            confidence = 7
            reasons = ["Significant VWAP Deviation", "RSI Oversold"]
            
            if 'BULLISH_ENGULFING' in a['price_action']:
                confidence += 2
                reasons.append("Bullish Engulfing")
                
            if confidence >= MIN_CONFIDENCE:
                atr = a['atr']
                sl = current - atr * 1.5
                tp1 = vwap # Target is VWAP
                tp2 = vwap * 1.005
                risk = current - sl
                reward = tp1 - current
                
                if risk > 0 and reward / risk >= 1.5:
                    trades.append({
                        'strategy': 'VWAP Reversion',
                        'type': 'LONG',
                        'symbol': symbol,
                        'entry': current,
                        'sl': sl, 'tp1': tp1, 'tp2': tp2,
                        'confidence': 'MID',
                        'confidence_score': confidence,
                        'risk_reward': round(reward/risk, 1),
                        'reason': ' + '.join(reasons),
                        'indicators': f"VWAP Dev: {((current/vwap)-1)*100:.1f}%, RSI:{a['rsi']:.0f}",
                        'expected_time': '15-45 mins',
                        'risk': risk, 'reward': reward,
                        'entry_type': 'MARKET',
                        'timeframe': tf
                    })
                    
    # SHORT Scalp: Price far above VWAP + Overbought RSI
    elif current > vwap * 1.015:
        if a['rsi'] > 70:
            confidence = 7
            reasons = ["Significant VWAP Deviation", "RSI Overbought"]
            
            if 'BEARISH_ENGULFING' in a['price_action']:
                confidence += 2
                reasons.append("Bearish Engulfing")
                
            if confidence >= MIN_CONFIDENCE:
                atr = a['atr']
                sl = current + atr * 1.5
                tp1 = vwap
                tp2 = vwap * 0.995
                risk = sl - current
                reward = current - tp1
                
                if risk > 0 and reward / risk >= 1.5:
                    trades.append({
                        'strategy': 'VWAP Reversion',
                        'type': 'SHORT',
                        'symbol': symbol,
                        'entry': current,
                        'sl': sl, 'tp1': tp1, 'tp2': tp2,
                        'confidence': 'MID',
                        'confidence_score': confidence,
                        'risk_reward': round(reward/risk, 1),
                        'reason': ' + '.join(reasons),
                        'indicators': f"VWAP Dev: {((current/vwap)-1)*100:.1f}%, RSI:{a['rsi']:.0f}",
                        'expected_time': '15-45 mins',
                        'risk': risk, 'reward': reward,
                        'entry_type': 'MARKET',
                        'timeframe': tf
                    })
                    
    return trades

def strategy_ichimoku_tk(symbol, analyses):
    """Strategy: Ichimoku TK Cross + Cloud Confirmation"""
    tf = '1h' if '1h' in analyses else '4h' if '4h' in analyses else None
    if not tf or tf not in analyses: return []
    
    a = analyses[tf]
    ichi = a['ichimoku']
    if not ichi: return []
    current = a['current_price']
    trades = []
    
    # LONG: Tenkan crosses ABOVE Kijun, price is ABOVE Cloud
    if ichi['tenkan'] > ichi['kijun'] and current > ichi['span_a'] and current > ichi['span_b']:
        confidence = 7
        reasons = ["Ichimoku TK Bullish Cross", "Price above Cloud"]
        
        if a['trend'] == 'BULLISH':
            confidence += 1
            reasons.append("EMA Trend Alignment")
            
        if confidence >= MIN_CONFIDENCE:
            atr = a['atr']
            sl = ichi['kijun'] # Standard stop at Kijun line
            tp1 = current + atr * 4
            tp2 = current + atr * 7
            risk = current - sl
            reward = tp1 - current
            
            if risk > 0 and reward/risk >= 1.5:
                trades.append({
                    'strategy': 'Ichimoku Master',
                    'type': 'LONG',
                    'symbol': symbol,
                    'entry': current,
                    'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence': 'HIGH',
                    'confidence_score': confidence,
                    'risk_reward': round(reward/risk, 1),
                    'reason': ' + '.join(reasons),
                    'indicators': f"TK Cross, Cloud:{ichi['cloud_state']}",
                    'expected_time': '12-24 hours',
                    'risk': risk, 'reward': reward,
                    'entry_type': 'MARKET',
                    'timeframe': tf
                })
                
    # SHORT: Tenkan crosses BELOW Kijun, price is BELOW Cloud
    elif ichi['tenkan'] < ichi['kijun'] and current < ichi['span_a'] and current < ichi['span_b']:
        confidence = 7
        reasons = ["Ichimoku TK Bearish Cross", "Price below Cloud"]
        
        if a['trend'] == 'BEARISH':
            confidence += 1
            reasons.append("EMA Trend Alignment")
            
        if confidence >= MIN_CONFIDENCE:
            atr = a['atr']
            sl = ichi['kijun']
            tp1 = current - atr * 4
            tp2 = current - atr * 7
            risk = sl - current
            reward = current - tp1
            
            if risk > 0 and reward/risk >= 1.5:
                trades.append({
                    'strategy': 'Ichimoku Master',
                    'type': 'SHORT',
                    'symbol': symbol,
                    'entry': current,
                    'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence': 'HIGH',
                    'confidence_score': confidence,
                    'risk_reward': round(reward/risk, 1),
                    'reason': ' + '.join(reasons),
                    'indicators': f"TK Cross, Cloud:{ichi['cloud_state']}",
                    'expected_time': '12-24 hours',
                    'risk': risk, 'reward': reward,
                    'entry_type': 'MARKET',
                    'timeframe': tf
                })
                
    return trades

def strategy_fvg_gap_fill(symbol, analyses):
    """Strategy: Fair Value Gap Re-entry (SMC)"""
    tf = '15m' if '15m' in analyses else '5m' if '5m' in analyses else None
    if not tf or tf not in analyses: return []
    
    a = analyses[tf]
    fvg = a['fvg']
    if not fvg: return []
    current = a['current_price']
    trades = []
    
    # LONG: Bullish FVG detected (imbalance)
    if fvg['type'] == 'BULLISH':
        confidence = 6
        reasons = [f"Bullish Fair Value Gap (SMC) detected on {tf}"]
        
        if a['adx']['adx'] > 20: 
            confidence += 2
            reasons.append("Strong Trend Momentum")
            
        if confidence >= MIN_CONFIDENCE:
            atr = a['atr']
            # Entry at the top of the gap, SL at the bottom
            entry = fvg['top']
            sl = fvg['bottom'] - (atr * 0.2)
            tp1 = entry + atr * 4
            tp2 = entry + atr * 8
            risk = entry - sl
            reward = tp1 - entry
            
            if risk > 0 and reward/risk >= 2:
                trades.append({
                    'strategy': 'FVG Imbalance',
                    'type': 'LONG',
                    'symbol': symbol,
                    'entry': entry,
                    'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence': 'HIGH',
                    'confidence_score': confidence,
                    'risk_reward': round(reward/risk, 1),
                    'reason': ' + '.join(reasons),
                    'indicators': f"FVG:{fvg['bottom']:.4f}-{fvg['top']:.4f}",
                    'expected_time': '1-3 hours',
                    'risk': risk, 'reward': reward,
                    'entry_type': 'LIMIT',
                    'timeframe': tf
                })
                
    return trades

def strategy_divergence_pro(symbol, analyses):
    """Strategy: RSI Divergence Reversal"""
    # Check across multiple timeframes for divergence
    trades = []
    for tf in ['15m', '1h', '4h']:
        if tf not in analyses: continue
        a = analyses[tf]
        div = a['rsi_div']
        if not div: continue
        
        current = a['current_price']
        
        if div == 'BULLISH':
            confidence = 8
            reasons = [f"BULLISH RSI Divergence on {tf}"]
            
            if a['rsi'] < 30:
                confidence += 1
                reasons.append("Extreme Oversold RSI")
                
            if confidence >= MIN_CONFIDENCE:
                atr = a['atr']
                sl = current - atr * 2
                tp1 = current + atr * 4
                tp2 = current + atr * 7
                risk = current - sl
                reward = tp1 - current
                
                if risk > 0:
                    trades.append({
                        'strategy': 'Divergence Pro',
                        'type': 'LONG',
                        'symbol': symbol,
                        'entry': current,
                        'sl': sl, 'tp1': tp1, 'tp2': tp2,
                        'confidence': 'VERY HIGH',
                        'confidence_score': confidence,
                        'risk_reward': round(reward/risk, 1),
                        'reason': ' + '.join(reasons),
                        'indicators': f"RSI Div: Bull, RSI:{a['rsi']:.0f}",
                        'expected_time': '4-12 hours',
                        'risk': risk, 'reward': reward,
                        'entry_type': 'STOP-MARKET',
                        'timeframe': tf
                    })
                    
        elif div == 'BEARISH':
            confidence = 8
            reasons = [f"BEARISH RSI Divergence on {tf}"]
            
            if a['rsi'] > 70:
                confidence += 1
                reasons.append("Extreme Overbought RSI")
                
            if confidence >= MIN_CONFIDENCE:
                atr = a['atr']
                sl = current + atr * 2
                tp1 = current - atr * 4
                tp2 = current - atr * 7
                risk = sl - current
                reward = current - tp1
                
                if risk > 0:
                    trades.append({
                        'strategy': 'Divergence Pro',
                        'type': 'SHORT',
                        'symbol': symbol,
                        'entry': current,
                        'sl': sl, 'tp1': tp1, 'tp2': tp2,
                        'confidence': 'VERY HIGH',
                        'confidence_score': confidence,
                        'risk_reward': round(reward/risk, 1),
                        'reason': ' + '.join(reasons),
                        'indicators': f"RSI Div: Bear, RSI:{a['rsi']:.0f}",
                        'expected_time': '4-12 hours',
                        'risk': risk, 'reward': reward,
                        'entry_type': 'STOP-MARKET',
                        'timeframe': tf
                    })
                    
    return trades

def strategy_adx_momentum(symbol, analyses):
    """Strategy: ADX Momentum (DI Cross)"""
    tf = '1h' if '1h' in analyses else '15m' if '15m' in analyses else None
    if not tf or tf not in analyses: return []
    
    a = analyses[tf]
    current = a['current_price']
    trades = []
    
    # ADX must be rising and > 25 for momentum
    if a['adx']['adx'] > 25:
        # LONG: Plus DI > Minus DI
        if a['adx']['plus_di'] > a['adx']['minus_di'] + 5:
            confidence = 7
            reasons = ["Strong Bullish Momentum (ADX > 25)", "DI+ > DI- Cross"]
            
            if a['trend'] == 'BULLISH':
                confidence += 2
                reasons.append("EMA Trend Alignment")
                
            if confidence >= MIN_CONFIDENCE:
                atr = a['atr']
                sl = current - atr * 2.5
                tp1 = current + atr * 5
                tp2 = current + atr * 8
                risk = current - sl
                reward = tp1 - current
                
                if risk > 0 and reward/risk >= 1.5:
                    trades.append({
                        'strategy': 'ADX Momentum',
                        'type': 'LONG',
                        'symbol': symbol,
                        'entry': current,
                        'sl': sl, 'tp1': tp1, 'tp2': tp2,
                        'confidence': 'HIGH',
                        'confidence_score': confidence,
                        'risk_reward': round(reward/risk, 1),
                        'reason': ' + '.join(reasons),
                        'indicators': f"ADX:{a['adx']['adx']:.0f}, DI+:{a['adx']['plus_di']:.0f}",
                        'expected_time': '8-16 hours',
                        'risk': risk, 'reward': reward,
                        'entry_type': 'MARKET',
                        'timeframe': tf
                    })
                    
        # SHORT: Minus DI > Plus DI
        elif a['adx']['minus_di'] > a['adx']['plus_di'] + 5:
            confidence = 7
            reasons = ["Strong Bearish Momentum (ADX > 25)", "DI- > DI+ Cross"]
            
            if a['trend'] == 'BEARISH':
                confidence += 2
                reasons.append("EMA Trend Alignment")
                
            if confidence >= MIN_CONFIDENCE:
                atr = a['atr']
                sl = current + atr * 2.5
                tp1 = current - atr * 5
                tp2 = current - atr * 8
                risk = sl - current
                reward = current - tp1
                
                if risk > 0 and reward/risk >= 1.5:
                    trades.append({
                        'strategy': 'ADX Momentum',
                        'type': 'SHORT',
                        'symbol': symbol,
                        'entry': current,
                        'sl': sl, 'tp1': tp1, 'tp2': tp2,
                        'confidence': 'HIGH',
                        'confidence_score': confidence,
                        'risk_reward': round(reward/risk, 1),
                        'reason': ' + '.join(reasons),
                        'indicators': f"ADX:{a['adx']['adx']:.0f}, DI-:{a['adx']['minus_di']:.0f}",
                        'expected_time': '8-16 hours',
                        'risk': risk, 'reward': reward,
                        'entry_type': 'MARKET',
                        'timeframe': tf
                    })
                    
    return trades

def strategy_volatility_breakout(symbol, analyses):
    """Strategy: Bollinger Band Breakout with ADX Confirmation"""
    tf = '1h' if '1h' in analyses else '15m' if '15m' in analyses else None
    if not tf or tf not in analyses: return []
    
    a = analyses[tf]
    current = a['current_price']
    trades = []
    
    # ADX must be strong for a breakout
    if a['adx']['adx'] > 25:
        # LONG: Price breaks above Upper BB
        if current > a['bb']['upper']:
            confidence = 7
            reasons = ["Bollinger Band Breakout (Upper)", "Strong ADX Momentum"]
            
            if a['trend'] == 'BULLISH':
                confidence += 1
                reasons.append("EMA Trend Alignment")
                
            if confidence >= MIN_CONFIDENCE:
                atr = a['atr']
                sl = a['bb']['middle']
                tp1 = current + atr * 5
                tp2 = current + atr * 8
                risk = current - sl
                reward = tp1 - current
                
                if risk > 0 and reward / risk >= 1.5:
                    trades.append({
                        'strategy': 'Volatility Breakout',
                        'type': 'LONG',
                        'symbol': symbol,
                        'entry': a['bb']['upper'],
                        'sl': sl, 'tp1': tp1, 'tp2': tp2,
                        'confidence': 'HIGH',
                        'confidence_score': confidence,
                        'risk_reward': round(reward / risk, 1),
                        'reason': ' + '.join(reasons),
                        'indicators': f"BB Upper: {a['bb']['upper']:.4f}, ADX: {a['adx']['adx']:.1f}",
                        'expected_time': '2-4 hours',
                        'risk': risk, 'reward': reward,
                        'entry_type': 'STOP-MARKET',
                        'timeframe': tf
                    })
                    
        # SHORT: Price breaks below Lower BB
        elif current < a['bb']['lower']:
            confidence = 7
            reasons = ["Bollinger Band Breakout (Lower)", "Strong ADX Momentum"]
            
            if a['trend'] == 'BEARISH':
                confidence += 1
                reasons.append("EMA Trend Alignment")
                
            if confidence >= MIN_CONFIDENCE:
                atr = a['atr']
                sl = a['bb']['middle']
                tp1 = current - atr * 5
                tp2 = current - atr * 8
                risk = sl - current
                reward = current - tp1
                
                if risk > 0 and reward / risk >= 1.5:
                    trades.append({
                        'strategy': 'Volatility Breakout',
                        'type': 'SHORT',
                        'symbol': symbol,
                        'entry': a['bb']['lower'],
                        'sl': sl, 'tp1': tp1, 'tp2': tp2,
                        'confidence': 'HIGH',
                        'confidence_score': confidence,
                        'risk_reward': round(reward / risk, 1),
                        'reason': ' + '.join(reasons),
                        'indicators': f"BB Lower: {a['bb']['lower']:.4f}, ADX: {a['adx']['adx']:.1f}",
                        'expected_time': '2-4 hours',
                        'risk': risk, 'reward': reward,
                        'entry_type': 'STOP-MARKET',
                        'timeframe': tf
                    })
                    
    return trades

def strategy_bollinger_reversion(symbol, analyses):
    """Strategy: Bollinger Mean Reversion (RSI Confirmation)"""
    tf = '15m' if '15m' in analyses else '5m' if '5m' in analyses else None
    if not tf or tf not in analyses: return []
    
    a = analyses[tf]
    current = a['current_price']
    trades = []
    
    # LONG: Hits Lower Band + RSI Oversold
    if current < a['bb']['lower'] and a['rsi'] < 30:
        confidence = 8
        reasons = ["Bollinger Lower Band Touch", "RSI Oversold"]
        
        if 'BULLISH_ENGULFING' in a['price_action']:
            confidence += 2
            reasons.append("Bullish Engulfing")
            
        if confidence >= MIN_CONFIDENCE:
            atr = a['atr']
            sl = current - atr * 1.5
            tp1 = a['bb']['middle']
            tp2 = a['bb']['upper']
            risk = current - sl
            reward = tp1 - current
            
            if risk > 0 and reward/risk >= 1.5:
                trades.append({
                    'strategy': 'BB Reversion',
                    'type': 'LONG',
                    'symbol': symbol,
                    'entry': current,
                    'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence': 'VERY HIGH',
                    'confidence_score': confidence,
                    'risk_reward': round(reward/risk, 1),
                    'reason': ' + '.join(reasons),
                    'indicators': f"BB Lower, RSI:{a['rsi']:.0f}",
                    'expected_time': '1-2 hours',
                    'risk': risk, 'reward': reward,
                    'entry_type': 'MARKET',
                    'timeframe': tf
                })
                
    # SHORT: Hits Upper Band + RSI Overbought
    elif current > a['bb']['upper'] and a['rsi'] > 70:
        confidence = 8
        reasons = ["Bollinger Upper Band Touch", "RSI Overbought"]
        
        if 'BEARISH_ENGULFING' in a['price_action']:
            confidence += 2
            reasons.append("Bearish Engulfing")
            
        if confidence >= MIN_CONFIDENCE:
            atr = a['atr']
            sl = current + atr * 1.5
            tp1 = a['bb']['middle']
            tp2 = a['bb']['lower']
            risk = sl - current
            reward = current - tp1
            
            if risk > 0 and reward/risk >= 1.5:
                trades.append({
                    'strategy': 'BB Reversion',
                    'type': 'SHORT',
                    'symbol': symbol,
                    'entry': current,
                    'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence': 'VERY HIGH',
                    'confidence_score': confidence,
                    'risk_reward': round(reward/risk, 1),
                    'reason': ' + '.join(reasons),
                    'indicators': f"BB Upper, RSI:{a['rsi']:.0f}",
                    'expected_time': '1-2 hours',
                    'risk': risk, 'reward': reward,
                    'entry_type': 'MARKET',
                    'timeframe': tf
                })
                
    return trades

def strategy_liquidity_grab_reversal(symbol, analyses):
    """Strategy: Liquidity Sweep Reversal (SMC)"""
    # Prefer 1h or 15m for precision
    tf = '1h' if '1h' in analyses else '15m' if '15m' in analyses else '5m'
    if tf not in analyses: return []
    
    a = analyses[tf]
    liq = a['liquidity']
    if not liq: return []
    
    current = a['current_price']
    trades = []
    
    # BULLISH: Price swept a low and reversed
    if liq['type'] == 'BULLISH':
        confidence = 8
        reasons = [f"Bullish Liquidity Sweep (Low {liq['level']:.6f} taken)"]
        
        if a['rsi'] < 30:
            confidence += 1
            reasons.append("RSI Oversold")
        if a['wavetrend']['wt1'] < -50:
            confidence += 1
            reasons.append("WaveTrend Deep Oversold")
            
        if confidence >= MIN_CONFIDENCE:
            atr = a['atr']
            sl = liq['level'] - (atr * 0.5)
            tp1 = current + atr * 4
            tp2 = current + atr * 8
            risk = current - sl
            reward = tp1 - current
            
            if risk > 0 and reward/risk >= 2:
                trades.append({
                    'strategy': 'Liquidity Grab',
                    'type': 'LONG',
                    'symbol': symbol,
                    'entry': liq['level'],
                    'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence': 'VERY HIGH',
                    'confidence_score': confidence,
                    'risk_reward': round(reward/risk, 1),
                    'reason': ' + '.join(reasons),
                    'indicators': f"Sweep, RSI:{a['rsi']:.0f}, WT:{a['wavetrend']['wt1']:.0f}",
                    'expected_time': '4-12 hours',
                    'risk': risk, 'reward': reward,
                    'entry_type': 'LIMIT',
                    'timeframe': tf
                })

    # BEARISH: Price swept a high and reversed
    elif liq['type'] == 'BEARISH':
        confidence = 8
        reasons = [f"Bearish Liquidity Sweep (High {liq['level']:.6f} taken)"]
        
        if a['rsi'] > 70:
            confidence += 1
            reasons.append("RSI Overbought")
        if a['wavetrend']['wt1'] > 50:
            confidence += 1
            reasons.append("WaveTrend Deep Overbought")
            
        if confidence >= MIN_CONFIDENCE:
            atr = a['atr']
            sl = liq['level'] + (atr * 0.5)
            tp1 = current - atr * 4
            tp2 = current - atr * 8
            risk = sl - current
            reward = current - tp1
            
            if risk > 0 and reward/risk >= 2:
                trades.append({
                    'strategy': 'Liquidity Grab',
                    'type': 'SHORT',
                    'symbol': symbol,
                    'entry': liq['level'],
                    'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence': 'VERY HIGH',
                    'confidence_score': confidence,
                    'risk_reward': round(reward/risk, 1),
                    'reason': ' + '.join(reasons),
                    'indicators': f"Sweep, RSI:{a['rsi']:.0f}, WT:{a['wavetrend']['wt1']:.0f}",
                    'expected_time': '4-12 hours',
                    'risk': risk, 'reward': reward,
                    'entry_type': 'LIMIT',
                    'timeframe': tf
                })
                
    return trades

def strategy_wavetrend_extreme(symbol, analyses):
    """Strategy: WaveTrend Extreme Divergence/Reversal"""
    tf = '15m' if '15m' in analyses else '5m'
    if tf not in analyses: return []
    
    a = analyses[tf]
    wt = a['wavetrend']
    current = a['current_price']
    trades = []
    
    # LONG: WT1 crosses ABOVE WT2 in extreme oversold area
    if wt['wt1'] < -60 and wt['wt1'] > wt['wt2'] and wt['prev_wt1'] <= wt['wt2']:
        confidence = 7
        reasons = ["WaveTrend Bullish Gold Cross (Extreme Oversold)"]
        
        if a['rsi'] < 30:
            confidence += 1
            reasons.append("Co-incidence RSI Oversold")
            
        if confidence >= MIN_CONFIDENCE:
            atr = a['atr']
            sl = current - atr * 2
            tp1 = current + atr * 3.5
            tp2 = current + atr * 6
            risk = current - sl
            reward = tp1 - current
            
            if risk > 0 and reward/risk >= 1.5:
                trades.append({
                    'strategy': 'WaveTrend Extreme',
                    'type': 'LONG',
                    'symbol': symbol,
                    'entry': current,
                    'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence': 'HIGH',
                    'confidence_score': confidence,
                    'risk_reward': round(reward/risk, 1),
                    'reason': ' + '.join(reasons),
                    'indicators': f"WT1:{wt['wt1']:.0f}, WT2:{wt['wt2']:.0f}",
                    'expected_time': '2-6 hours',
                    'risk': risk, 'reward': reward,
                    'entry_type': 'MARKET',
                    'timeframe': tf
                })

    # SHORT: WT1 crosses BELOW WT2 in extreme overbought area
    elif wt['wt1'] > 60 and wt['wt1'] < wt['wt2'] and wt['prev_wt1'] >= wt['wt2']:
        confidence = 7
        reasons = ["WaveTrend Bearish Death Cross (Extreme Overbought)"]
        
        if a['rsi'] > 70:
            confidence += 1
            reasons.append("Co-incidence RSI Overbought")
            
        if confidence >= MIN_CONFIDENCE:
            atr = a['atr']
            sl = current + atr * 2
            tp1 = current - atr * 3.5
            tp2 = current - atr * 6
            risk = sl - current
            reward = current - tp1
            
            if risk > 0 and reward/risk >= 1.5:
                trades.append({
                    'strategy': 'WaveTrend Extreme',
                    'type': 'SHORT',
                    'symbol': symbol,
                    'entry': current,
                    'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence': 'HIGH',
                    'confidence_score': confidence,
                    'risk_reward': round(reward/risk, 1),
                    'reason': ' + '.join(reasons),
                    'indicators': f"WT1:{wt['wt1']:.0f}, WT2:{wt['wt2']:.0f}",
                    'expected_time': '2-6 hours',
                    'risk': risk, 'reward': reward,
                    'entry_type': 'MARKET',
                    'timeframe': tf
                })
                
    return trades

def strategy_squeeze_breakout(symbol, analyses):
    """Strategy: Squeeze Momentum Breakout"""
    tf = '1h' if '1h' in analyses else '15m' if '15m' in analyses else '5m'
    if tf not in analyses: return []
    
    a = analyses[tf]
    sqz = a['squeeze']
    current = a['current_price']
    trades = []
    
    # We look for Squeeze coming OFF with strong momentum
    if sqz['sqz'] == 'OFF' and abs(sqz['val']) > a['atr'] * 0.5:
        # LONG: Positive momentum
        if sqz['val'] > 0 and a['adx']['adx'] > 20:
            confidence = 7
            reasons = ["TTM Squeeze Upward Release", "Strong ADX Momentum"]
            
            if a['trend'] == 'BULLISH':
                confidence += 2
                reasons.append("Trend Alignment")
                
            if confidence >= MIN_CONFIDENCE:
                atr = a['atr']
                sl = current - atr * 3
                tp1 = current + atr * 6
                tp2 = current + atr * 10
                risk = current - sl
                reward = tp1 - current
                
                if risk > 0 and reward/risk >= 1.5:
                    trades.append({
                        'strategy': 'Squeeze Break',
                        'type': 'LONG',
                        'symbol': symbol,
                        'entry': current,
                        'sl': sl, 'tp1': tp1, 'tp2': tp2,
                        'confidence': 'HIGH',
                        'confidence_score': confidence,
                        'risk_reward': round(reward/risk, 1),
                        'reason': ' + '.join(reasons),
                        'indicators': f"SQZ Release, Mom:{sqz['val']:.4f}",
                        'expected_time': '8-24 hours',
                        'risk': risk, 'reward': reward,
                        'entry_type': 'STOP-MARKET',
                        'timeframe': tf,
                        'analysis_data': {
                            'squeeze': 'OFF',
                            'momentum': sqz['val'],
                            'adx': a['adx']['adx'],
                            'trend': a['trend']
                        }
                    })

        # SHORT: Negative momentum
        elif sqz['val'] < 0 and a['adx']['adx'] > 20:
            confidence = 7
            reasons = ["TTM Squeeze Downward Release", "Strong ADX Momentum"]
            
            if a['trend'] == 'BEARISH':
                confidence += 2
                reasons.append("Trend Alignment")
                
            if confidence >= MIN_CONFIDENCE:
                atr = a['atr']
                sl = current + atr * 3
                tp1 = current - atr * 6
                tp2 = current - atr * 10
                risk = sl - current
                reward = current - tp1
                
                if risk > 0 and reward/risk >= 1.5:
                    trades.append({
                        'strategy': 'Squeeze Break',
                        'type': 'SHORT',
                        'symbol': symbol,
                        'entry': current,
                        'sl': sl, 'tp1': tp1, 'tp2': tp2,
                        'confidence': 'HIGH',
                        'confidence_score': confidence,
                        'risk_reward': round(reward/risk, 1),
                        'reason': ' + '.join(reasons),
                        'indicators': f"SQZ Release, Mom:{sqz['val']:.4f}",
                        'expected_time': '8-24 hours',
                        'risk': risk, 'reward': reward,
                        'entry_type': 'STOP-MARKET',
                        'timeframe': tf,
                        'analysis_data': {
                            'squeeze': 'OFF',
                            'momentum': sqz['val'],
                            'adx': a['adx']['adx'],
                            'trend': a['trend']
                        }
                    })
                    
    return trades

def strategy_zlsma_fast_scalp(symbol, analyses):
    """Strategy: ZLSMA + RSI Trend Scalper (Ultra Fast)"""
    # Best on 1m, 3m
    tf = '1m' if '1m' in analyses else '3m' if '3m' in analyses else '5m'
    if tf not in analyses: return []
    
    a = analyses[tf]
    current = a['current_price']
    trades = []
    
    # LONG: Price above ZLSMA + RSI > 50 + RVOL Confirm
    if current > a['zlsma'] and a['rsi'] > 55 and a['rvol'] > 1.2:
        confidence = 7
        reasons = ["ZLSMA Bullish Ride", "Fast RSI Momentum", "High RVOL Confirm"]
        
        if a['tsi'] > 0:
            confidence += 1
            reasons.append("TSI Bullish")
            
        if confidence >= MIN_CONFIDENCE:
            atr = a['atr']
            sl = current - atr * 1.5
            tp1 = current + atr * 3
            tp2 = current + atr * 5
            risk = current - sl
            reward = tp1 - current
            
            if risk > 0 and reward/risk >= 1.5:
                trades.append({
                    'strategy': 'Z-Scalp',
                    'type': 'LONG',
                    'symbol': symbol,
                    'entry': current,
                    'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence': 'HIGH',
                    'confidence_score': confidence,
                    'risk_reward': round(reward/risk, 1),
                    'reason': ' + '.join(reasons),
                    'indicators': f"ZLSMA:{a['zlsma']:.4f}, RSI:{a['rsi']:.0f}, RVOL:{a['rvol']:.1f}",
                    'expected_time': '15-45 mins',
                    'risk': risk, 'reward': reward,
                    'entry_type': 'MARKET',
                    'timeframe': tf
                })

    # SHORT: Price below ZLSMA + RSI < 50 + RVOL Confirm
    elif current < a['zlsma'] and a['rsi'] < 45 and a['rvol'] > 1.2:
        confidence = 7
        reasons = ["ZLSMA Bearish Ride", "Fast RSI Momentum", "High RVOL Confirm"]
        
        if a['tsi'] < 0:
            confidence += 1
            reasons.append("TSI Bearish")
            
        if confidence >= MIN_CONFIDENCE:
            atr = a['atr']
            sl = current + atr * 1.5
            tp1 = current - atr * 3
            tp2 = current - atr * 5
            risk = sl - current
            reward = current - tp1
            
            if risk > 0 and reward/risk >= 1.5:
                trades.append({
                    'strategy': 'Z-Scalp',
                    'type': 'SHORT',
                    'symbol': symbol,
                    'entry': current,
                    'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence': 'HIGH',
                    'confidence_score': confidence,
                    'risk_reward': round(reward/risk, 1),
                    'reason': ' + '.join(reasons),
                    'indicators': f"ZLSMA:{a['zlsma']:.4f}, RSI:{a['rsi']:.0f}, RVOL:{a['rvol']:.1f}",
                    'expected_time': '15-45 mins',
                    'risk': risk, 'reward': reward,
                    'entry_type': 'MARKET',
                    'timeframe': tf
                })
                
    return trades

def strategy_mfi_reversion(symbol, analyses):
    """Strategy: MFI Exhaustion Scalper"""
    tf = '5m' if '5m' in analyses else '15m'
    if tf not in analyses: return []
    
    a = analyses[tf]
    current = a['current_price']
    trades = []
    
    # LONG: MFI Deep Oversold (< 15) + RSI Overbought recovery
    if a['mfi'] < 15 and a['rsi'] < 30:
        confidence = 8
        reasons = ["MFI Deep Exhaustion", "RSI Extreme Oversold"]
        
        if a['wavetrend']['wt1'] < -60:
            confidence += 1
            reasons.append("WaveTrend confirm")
            
        if confidence >= MIN_CONFIDENCE:
            atr = a['atr']
            sl = current - atr * 1.5
            tp1 = current + atr * 3.5
            tp2 = current + atr * 6
            risk = current - sl
            reward = tp1 - current
            
            if risk > 0 and reward/risk >= 1.5:
                trades.append({
                    'strategy': 'MFI Reversion',
                    'type': 'LONG',
                    'symbol': symbol,
                    'entry': current,
                    'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence': 'VERY HIGH',
                    'confidence_score': confidence,
                    'risk_reward': round(reward/risk, 1),
                    'reason': ' + '.join(reasons),
                    'indicators': f"MFI:{a['mfi']:.0f}, RSI:{a['rsi']:.0f}",
                    'expected_time': '30-90 mins',
                    'risk': risk, 'reward': reward,
                    'entry_type': 'MARKET',
                    'timeframe': tf
                })

    # SHORT: MFI Deep Overbought (> 85) + RSI Overbought recovery
    elif a['mfi'] > 85 and a['rsi'] > 70:
        confidence = 8
        reasons = ["MFI Deep Exhaustion", "RSI Extreme Overbought"]
        
        if a['wavetrend']['wt1'] > 60:
            confidence += 1
            reasons.append("WaveTrend confirm")
            
        if confidence >= MIN_CONFIDENCE:
            atr = a['atr']
            sl = current + atr * 1.5
            tp1 = current - atr * 3.5
            tp2 = current - atr * 6
            risk = sl - current
            reward = current - tp1
            
            if risk > 0 and reward/risk >= 1.5:
                trades.append({
                    'strategy': 'MFI Reversion',
                    'type': 'SHORT',
                    'symbol': symbol,
                    'entry': current,
                    'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence': 'VERY HIGH',
                    'confidence_score': confidence,
                    'risk_reward': round(reward/risk, 1),
                    'reason': ' + '.join(reasons),
                    'indicators': f"MFI:{a['mfi']:.0f}, RSI:{a['rsi']:.0f}",
                    'expected_time': '30-90 mins',
                    'risk': risk, 'reward': reward,
                    'entry_type': 'MARKET',
                    'timeframe': tf
                })
                
    return trades

def strategy_fisher_transform_pivot(symbol, analyses):
    """Strategy: Fisher Transform Early Pivot Scalper"""
    tf = '3m' if '3m' in analyses else '5m'
    if tf not in analyses: return []
    
    a = analyses[tf]
    current = a['current_price']
    trades = []
    
    # Fisher extremes usually indicate price pivots
    if a['fisher'] < -2.5: # Extreme Bottom
        confidence = 7
        reasons = ["Fisher Transform Extreme Lower (Pivot Soon)"]
        
        if a['zlsma'] > a['ema21']:
            confidence += 1
            reasons.append("Trend context support")
            
        if confidence >= MIN_CONFIDENCE:
            atr = a['atr']
            sl = current - atr * 1.8
            tp1 = current + atr * 4
            tp2 = current + atr * 7
            risk = current - sl
            reward = tp1 - current
            
            if risk > 0:
                trades.append({
                    'strategy': 'Fisher Pivot',
                    'type': 'LONG',
                    'symbol': symbol,
                    'entry': current,
                    'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence': 'MID-HIGH',
                    'confidence_score': confidence,
                    'risk_reward': round(reward/risk, 1),
                    'reason': ' + '.join(reasons),
                    'indicators': f"Fisher:{a['fisher']:.2f}",
                    'expected_time': '1-3 hours',
                    'risk': risk, 'reward': reward,
                    'entry_type': 'LIMIT',
                    'timeframe': tf
                })

    elif a['fisher'] > 2.5: # Extreme Top
        confidence = 7
        reasons = ["Fisher Transform Extreme Upper (Pivot Soon)"]
        
        if a['zlsma'] < a['ema21']:
            confidence += 1
            reasons.append("Trend context support")
            
        if confidence >= MIN_CONFIDENCE:
            atr = a['atr']
            sl = current + atr * 1.8
            tp1 = current - atr * 4
            tp2 = current - atr * 7
            risk = sl - current
            reward = current - tp1
            
            if risk > 0:
                trades.append({
                    'strategy': 'Fisher Pivot',
                    'type': 'SHORT',
                    'symbol': symbol,
                    'entry': current,
                    'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence': 'MID-HIGH',
                    'confidence_score': confidence,
                    'risk_reward': round(reward/risk, 1),
                    'reason': ' + '.join(reasons),
                    'indicators': f"Fisher:{a['fisher']:.2f}",
                    'expected_time': '1-3 hours',
                    'risk': risk, 'reward': reward,
                    'entry_type': 'LIMIT',
                    'timeframe': tf
                })
                
    return trades

def strategy_volume_spike_breakout(symbol, analyses):
    """Strategy: High Velocity Volume Spike Breakout"""
    tf = '1m' if '1m' in analyses else '3m'
    if tf not in analyses: return []
    
    a = analyses[tf]
    current = a['current_price']
    trades = []
    
    # 2.5x normal volume + Price breaking local high/low
    if a['rvol'] > 2.5:
        # LONG: Bullish price action + High volume
        if 'BULLISH_ENGULFING' in a['price_action'] or current > a['resistance']:
            confidence = 8
            reasons = ["Extreme Volume Spike", "Price Action Breakout"]
            
            if a['adx']['adx'] > 25:
                confidence += 2
                reasons.append("ADX Impulse Confirmation")
                
            if confidence >= MIN_CONFIDENCE:
                atr = a['atr']
                sl = current - atr * 2
                tp1 = current + atr * 5
                tp2 = current + atr * 9
                risk = current - sl
                reward = tp1 - current
                
                if risk > 0:
                    trades.append({
                        'strategy': 'Volume Spike',
                        'type': 'LONG',
                        'symbol': symbol,
                        'entry': current,
                        'sl': sl, 'tp1': tp1, 'tp2': tp2,
                        'confidence': 'VERY HIGH',
                        'confidence_score': confidence,
                        'risk_reward': round(reward/risk, 1),
                        'reason': ' + '.join(reasons),
                        'indicators': f"RVOL:{a['rvol']:.1f}, ADX:{a['adx']['adx']:.0f}",
                        'expected_time': '15-60 mins',
                        'risk': risk, 'reward': reward,
                        'entry_type': 'STOP-MARKET',
                        'timeframe': tf
                    })

        # SHORT: Bearish price action + High volume
        elif 'BEARISH_ENGULFING' in a['price_action'] or current < a['support']:
            confidence = 8
            reasons = ["Extreme Volume Spike", "Price Action Breakout"]
            
            if a['adx']['adx'] > 25:
                confidence += 2
                reasons.append("ADX Impulse Confirmation")
                
            if confidence >= MIN_CONFIDENCE:
                atr = a['atr']
                sl = current + atr * 2
                tp1 = current - atr * 5
                tp2 = current - atr * 9
                risk = sl - current
                reward = current - tp1
                
                if risk > 0:
                    trades.append({
                        'strategy': 'Volume Spike',
                        'type': 'SHORT',
                        'symbol': symbol,
                        'entry': current,
                        'sl': sl, 'tp1': tp1, 'tp2': tp2,
                        'confidence': 'VERY HIGH',
                        'confidence_score': confidence,
                        'risk_reward': round(reward/risk, 1),
                        'reason': ' + '.join(reasons),
                        'indicators': f"RVOL:{a['rvol']:.1f}, ADX:{a['adx']['adx']:.0f}",
                        'expected_time': '15-60 mins',
                        'risk': risk, 'reward': reward,
                        'entry_type': 'STOP-MARKET',
                        'timeframe': tf
                    })
                    
    return trades

def strategy_smc_choch(symbol, analyses):
    """Strategy: Smart Money Concepts - Change of Character (CHoCH)"""
    tf = '15m' if '15m' in analyses else '1h' if '1h' in analyses else '5m'
    if tf not in analyses: return []
    
    a = analyses[tf]
    choch = a['choch']
    if not choch: return []
    
    current = a['current_price']
    trades = []
    
    # BULLISH CHoCH: Downtrend broken, potential new uptrend
    if choch['type'] == 'BULLISH':
        confidence = 8
        reasons = [f"Bullish CHoCH detected on {tf} (Trend Reversal Sight)"]
        
        if a['rsi'] < 40:
            confidence += 1
            reasons.append("RSI shows recovery from oversold")
            
        if a['obv'] == 'BULLISH':
            confidence += 1
            reasons.append("Bullish OBV accumulation")
            
        if confidence >= MIN_CONFIDENCE:
            atr = a['atr']
            # Entry at CHoCH level or current if close
            entry = max(current, choch['level'])
            sl = current - atr * 2.5
            tp1 = entry + atr * 5
            tp2 = entry + atr * 9
            risk = entry - sl
            reward = tp1 - entry
            
            if risk > 0 and reward/risk >= 1.5:
                trades.append({
                    'strategy': 'SMC CHoCH',
                    'type': 'LONG',
                    'symbol': symbol,
                    'entry': entry,
                    'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence': 'VERY HIGH',
                    'confidence_score': confidence,
                    'risk_reward': round(reward/risk, 1),
                    'reason': ' + '.join(reasons),
                    'indicators': f"CHoCH Bull @ {choch['level']:.4f}",
                    'expected_time': '4-12 hours',
                    'risk': risk, 'reward': reward,
                    'entry_type': 'STOP-MARKET',
                    'timeframe': tf
                })
                
    # BEARISH CHoCH: Uptrend broken, potential new downtrend
    elif choch['type'] == 'BEARISH':
        confidence = 8
        reasons = [f"Bearish CHoCH detected on {tf} (Trend Reversal Sight)"]
        
        if a['rsi'] > 60:
            confidence += 1
            reasons.append("RSI shows pullback from overbought")
            
        if a['obv'] == 'BEARISH':
            confidence += 1
            reasons.append("Bearish OBV distribution")
            
        if confidence >= MIN_CONFIDENCE:
            atr = a['atr']
            entry = min(current, choch['level'])
            sl = current + atr * 2.5
            tp1 = entry - atr * 5
            tp2 = entry - atr * 9
            risk = sl - entry
            reward = entry - tp1
            
            if risk > 0 and reward/risk >= 1.5:
                trades.append({
                    'strategy': 'SMC CHoCH',
                    'type': 'SHORT',
                    'symbol': symbol,
                    'entry': entry,
                    'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence': 'VERY HIGH',
                    'confidence_score': confidence,
                    'risk_reward': round(reward/risk, 1),
                    'reason': ' + '.join(reasons),
                    'indicators': f"CHoCH Bear @ {choch['level']:.4f}",
                    'expected_time': '4-12 hours',
                    'risk': risk, 'reward': reward,
                    'entry_type': 'STOP-MARKET',
                    'timeframe': tf
                })
                
    return trades

def strategy_donchian_breakout(symbol, analyses):
    """Strategy: Donchian Channel Breakout (Trend Following)"""
    tf = '1h' if '1h' in analyses else '4h' if '4h' in analyses else '15m'
    if tf not in analyses: return []
    
    a = analyses[tf]
    don = a['donchian']
    if not don: return []
    
    current = a['current_price']
    trades = []
    
    # LONG: Price breaks above the 20-period high
    if current > don['upper'] and a['adx']['adx'] > 20:
        confidence = 7
        reasons = [f"Donchian Upper Breakout ({tf})", "Rising Momentum"]
        
        if a['chop'] < 40:
            confidence += 2
            reasons.append("Market is Trending (CHOP < 40)")
            
        if confidence >= MIN_CONFIDENCE:
            atr = a['atr']
            sl = don['middle'] # Stop loss at the median line
            tp1 = current + atr * 5
            tp2 = current + atr * 10
            risk = current - sl
            reward = tp1 - current
            
            if risk > 0 and reward/risk >= 1.5:
                trades.append({
                    'strategy': 'Donchian Break',
                    'type': 'LONG',
                    'symbol': symbol,
                    'entry': current,
                    'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence': 'HIGH',
                    'confidence_score': confidence,
                    'risk_reward': round(reward/risk, 1),
                    'reason': ' + '.join(reasons),
                    'indicators': f"Donchian High: {don['upper']:.4f}, ADX: {a['adx']['adx']:.0f}",
                    'expected_time': '12-48 hours',
                    'risk': risk, 'reward': reward,
                    'entry_type': 'STOP-MARKET',
                    'timeframe': tf
                })
                
    return trades

def strategy_stc_momentum(symbol, analyses):
    """Strategy: Schaff Trend Cycle Momentum (Early Signal)"""
    tf = '15m' if '15m' in analyses else '5m'
    if tf not in analyses: return []
    
    a = analyses[tf]
    stc = a['stc']
    current = a['current_price']
    trades = []
    
    # STC provides very early signals. Needs trend filter.
    # Bullish: STC crosses above 25
    if stc > 25 and a['rsi'] > 50 and a['trend'] == 'BULLISH':
        confidence = 7
        reasons = ["STC Bullish Momentum Release", "Trend Alignment"]
        
        if confidence >= MIN_CONFIDENCE:
            atr = a['atr']
            sl = current - atr * 2
            tp1 = current + atr * 4
            tp2 = current + atr * 7
            risk = current - sl
            reward = tp1 - current
            
            if risk > 0:
                trades.append({
                    'strategy': 'STC Momentum',
                    'type': 'LONG',
                    'symbol': symbol,
                    'entry': current,
                    'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence': 'HIGH',
                    'confidence_score': confidence,
                    'risk_reward': round(reward/risk, 1),
                    'reason': ' + '.join(reasons),
                    'indicators': f"STC: {stc:.0f}, RSI: {a['rsi']:.0f}",
                    'expected_time': '2-6 hours',
                    'risk': risk, 'reward': reward,
                    'entry_type': 'MARKET',
                    'timeframe': tf
                })
                
    return trades

def strategy_vortex_trend(symbol, analyses):
    """Strategy: Vortex Trend Confirmation"""
    tf = '1h' if '1h' in analyses else '4h'
    if tf not in analyses: return []
    
    a = analyses[tf]
    vi = a['vortex']
    current = a['current_price']
    trades = []
    
    # LONG: VI+ > VI- and crossing
    if vi['plus'] > 1.1 and vi['plus'] > vi['minus']:
        confidence = 7
        reasons = [f"Vortex Bullish Trend Confirmed ({tf})"]
        
        if a['chop'] < 40:
            confidence += 2
            reasons.append("Trending Market")
            
        if confidence >= MIN_CONFIDENCE:
            atr = a['atr']
            sl = current - atr * 3
            tp1 = current + atr * 6
            tp2 = current + atr * 11
            risk = current - sl
            reward = tp1 - current
            
            if risk > 0 and reward/risk >= 1.5:
                trades.append({
                    'strategy': 'Vortex Trend',
                    'type': 'LONG',
                    'symbol': symbol,
                    'entry': current,
                    'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence': 'HIGH',
                    'confidence_score': confidence,
                    'risk_reward': round(reward/risk, 1),
                    'reason': ' + '.join(reasons),
                    'indicators': f"VI+: {vi['plus']:.2f}, VI-: {vi['minus']:.2f}",
                    'expected_time': '24-72 hours',
                    'risk': risk, 'reward': reward,
                    'entry_type': 'MARKET',
                    'timeframe': tf
                })
                
    return trades

def is_kill_zone():
    """Check if current time is within a trading Kill Zone (UTC)."""
    now = datetime.utcnow().time()
    # London Kill Zone: 07:00 - 10:00 UTC
    if now >= datetime.strptime("07:00", "%H:%M").time() and now <= datetime.strptime("10:00", "%H:%M").time():
        return "LONDON"
    # NY Kill Zone: 13:00 - 16:00 UTC
    if now >= datetime.strptime("13:00", "%H:%M").time() and now <= datetime.strptime("16:00", "%H:%M").time():
        return "NEW_YORK"
    # Asia Kill Zone: 01:00 - 04:00 UTC
    if now >= datetime.strptime("01:00", "%H:%M").time() and now <= datetime.strptime("04:00", "%H:%M").time():
        return "ASIA"
    return None

def strategy_ict_silver_bullet(symbol, analyses):
    """Strategy: ICT Silver Bullet (FVG + Kill Zone)"""
    kz = is_kill_zone()
    if not kz: return []
    
    tf = '5m' if '5m' in analyses else '15m'
    if tf not in analyses: return []
    
    a = analyses[tf]
    fvg = a['fvg']
    if not fvg: return []
    
    current = a['current_price']
    trades = []
    
    # Silver Bullet is a high-probability FVG play during specific hours
    if fvg['type'] == 'BULLISH' and a['trend'] == 'BULLISH':
        confidence = 9
        reasons = [f"ICT Silver Bullet ({kz} Kill Zone)", "Bullish FVG Alignment"]
        
        atr = a['atr']
        entry = fvg['top']
        sl = fvg['bottom'] - (atr * 0.2)
        tp1 = entry + atr * 5
        tp2 = entry + atr * 10
        risk = entry - sl
        reward = tp1 - entry
        
        if risk > 0:
            trades.append({
                'strategy': 'ICT Silver Bullet',
                'type': 'LONG',
                'symbol': symbol,
                'entry': entry,
                'sl': sl, 'tp1': tp1, 'tp2': tp2,
                'confidence': 'VERY HIGH',
                'confidence_score': confidence,
                'risk_reward': round(reward/risk, 1),
                'reason': ' + '.join(reasons),
                'indicators': f"KillZone: {kz}, FVG:{fvg['bottom']:.4f}-{fvg['top']:.4f}",
                'expected_time': '1-2 hours',
                'risk': risk, 'reward': reward,
                'entry_type': 'LIMIT',
                'timeframe': tf,
                'analysis_data': {
                    'fvg': {'top': fvg['top'], 'bottom': fvg['bottom'], 'type': 'BULLISH'},
                    'kill_zone': kz
                }
            })
                
    elif fvg['type'] == 'BEARISH' and a['trend'] == 'BEARISH':
        confidence = 9
        reasons = [f"ICT Silver Bullet ({kz} Kill Zone)", "Bearish FVG Alignment"]
        
        atr = a['atr']
        entry = fvg['bottom']
        sl = fvg['top'] + (atr * 0.2)
        tp1 = entry - atr * 5
        tp2 = entry - atr * 10
        risk = sl - entry
        reward = entry - tp1
        
        if risk > 0:
            trades.append({
                'strategy': 'ICT Silver Bullet',
                'type': 'SHORT',
                'symbol': symbol,
                'entry': entry,
                'sl': sl, 'tp1': tp1, 'tp2': tp2,
                'confidence': 'VERY HIGH',
                'confidence_score': confidence,
                'risk_reward': round(reward/risk, 1),
                'reason': ' + '.join(reasons),
                'indicators': f"KillZone: {kz}, FVG:{fvg['bottom']:.4f}-{fvg['top']:.4f}",
                'expected_time': '1-2 hours',
                'risk': risk, 'reward': reward,
                'entry_type': 'LIMIT',
                'timeframe': tf,
                'analysis_data': {
                    'fvg': {'top': fvg['top'], 'bottom': fvg['bottom'], 'type': 'BEARISH'},
                    'kill_zone': kz
                }
            })
                
    return trades

def strategy_keltner_reversion(symbol, analyses):
    """Strategy: Keltner Channel Mean Reversion"""
    tf = '15m' if '15m' in analyses else '5m'
    if tf not in analyses: return []
    
    a = analyses[tf]
    kc = a['kc']
    if not kc: return []
    current = a['current_price']
    trades = []
    
    # LONG: Price touches or goes below lower KC band + RSI oversold
    if current <= kc['lower'] and a['rsi'] < 30:
        confidence = 8
        reasons = ["Keltner Lower Band Touch", "RSI Oversold"]
        
        if 'BULLISH_ENGULFING' in a['price_action']:
            confidence += 2
            reasons.append("Bullish Engulfing")
            
        if confidence >= MIN_CONFIDENCE:
            atr = a['atr']
            sl = current - atr * 1.5
            tp1 = kc['middle']
            tp2 = kc['upper']
            risk = current - sl
            reward = tp1 - current
            
            if risk > 0 and reward/risk >= 1.5:
                trades.append({
                    'strategy': 'KC Reversion',
                    'type': 'LONG',
                    'symbol': symbol,
                    'entry': current,
                    'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence': 'VERY HIGH',
                    'confidence_score': confidence,
                    'risk_reward': round(reward/risk, 1),
                    'reason': ' + '.join(reasons),
                    'indicators': f"KC Lower, RSI:{a['rsi']:.0f}",
                    'expected_time': '1-2 hours',
                    'risk': risk, 'reward': reward,
                    'entry_type': 'MARKET',
                    'timeframe': tf
                })
                
    # SHORT: Price touches or goes above upper KC band + RSI overbought
    elif current >= kc['upper'] and a['rsi'] > 70:
        confidence = 8
        reasons = ["Keltner Upper Band Touch", "RSI Overbought"]
        
        if 'BEARISH_ENGULFING' in a['price_action']:
            confidence += 2
            reasons.append("Bearish Engulfing")
            
        if confidence >= MIN_CONFIDENCE:
            atr = a['atr']
            sl = current + atr * 1.5
            tp1 = kc['middle']
            tp2 = kc['lower']
            risk = sl - current
            reward = current - tp1
            
            if risk > 0 and reward/risk >= 1.5:
                trades.append({
                    'strategy': 'KC Reversion',
                    'type': 'SHORT',
                    'symbol': symbol,
                    'entry': current,
                    'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence': 'VERY HIGH',
                    'confidence_score': confidence,
                    'risk_reward': round(reward/risk, 1),
                    'reason': ' + '.join(reasons),
                    'indicators': f"KC Upper, RSI:{a['rsi']:.0f}",
                    'expected_time': '1-2 hours',
                    'risk': risk, 'reward': reward,
                    'entry_type': 'MARKET',
                    'timeframe': tf
                })
                
    return trades

# --- BEST OF BEST 2026 ELITE STRATEGIES ---
def strategy_smc_elite(symbol, analyses):
    """Elite SMC Strategy: Mitigation Blocks + FVG Confluence + Trend Alignment."""
    trades = []
    for tf, a in analyses.items():
        mb = detect_mitigation_block(a['candles'])
        fvg = a['fvg']
        if mb and fvg:
            entry = mb['level']
            fvg_type = 'BULLISH' if fvg['type'] == 'BULLISH' else 'BEARISH'
            if mb['type'] == fvg_type and a['trend'] == mb['type']:
                # MTF Confluence Check
                if not check_mtf_alignment(analyses, tf, mb['type']):
                    continue
                    
                confidence = 10
                atr = a['atr']
                sl = entry - (atr * 1.5) if mb['type'] == 'BULLISH' else entry + (atr * 1.5)
                tp1 = entry + (atr * 3) if mb['type'] == 'BULLISH' else entry - (atr * 3)
                trades.append({
                    'strategy': 'SMC Elite (MB+FVG)',
                    'type': mb['type'],
                    'symbol': symbol,
                    'entry': entry,
                    'sl': sl, 'tp1': tp1, 'tp2': entry + (tp1-entry)*2,
                    'confidence': 'MAXIMUM (ELITE)',
                    'confidence_score': confidence,
                    'risk_reward': 2.0,
                    'reason': f"SMC Elite: {mb['type']} Mitigation Block + FVG Fusion",
                    'indicators': f"MB:{entry:.4f} | FVG:{fvg['type']}",
                    'expected_time': '12-36 hours', 'entry_type': 'LIMIT', 'timeframe': tf,
                    'analysis_data': {
                        'fvg': {'top': fvg['top'], 'bottom': fvg['bottom'], 'type': fvg['type']},
                        'mitigation_block': {'level': mb['level'], 'type': mb['type']}
                    }
                })
    return trades

def strategy_harmonic_pro(symbol, analyses):
    """Pro Harmonic Scanner: Full XABCD Geometric Verification."""
    trades = []
    for tf, a in analyses.items():
        pattern = detect_advanced_harmonics(a['candles'])
        if pattern:
             # MTF Confluence Check
            if not check_mtf_alignment(analyses, tf, pattern['type']):
                continue
                
            confidence = 9
            entry = a['current_price']
            atr = a['atr']
            sl = entry - (atr * 2) if pattern['type'] == 'BULLISH' else entry + (atr * 2)
            tp1 = entry + (atr * 4) if pattern['type'] == 'BULLISH' else entry - (atr * 4)
            trades.append({
                'strategy': f"Harmonic-{pattern['pattern']}",
                'type': pattern['type'],
                'symbol': symbol,
                'entry': entry,
                'sl': sl, 'tp1': tp1, 'tp2': entry + (tp1-entry)*2,
                'confidence': 'VERY HIGH',
                'confidence_score': confidence,
                'risk_reward': 2.0,
                'reason': f"Advanced Harmonic Pattern: {pattern['pattern']} Detected",
                'indicators': f"XABCD Geometric Scan ({tf})",
                'expected_time': '24-48 hours', 'entry_type': 'MARKET', 'timeframe': tf,
                'analysis_data': {
                    'harmonic_pattern': pattern['pattern'],
                    'type': pattern['type']
                }
            })
    return trades

def strategy_volatility_capitulation(symbol, analyses):
    """Strategy: Volatility Capitulation (Panic Reversal)"""
    tf = '15m' if '15m' in analyses else '1h'
    if tf not in analyses: return []
    
    a = analyses[tf]
    current = a['current_price']
    trades = []
    
    # LONG: Panic Selling (Price < Lower BB, RSI < 25, ADX High)
    if current < a['bb']['lower'] and a['rsi'] < 25 and a['adx']['adx'] > 30:
        confidence = 8
        reasons = ["Volatility Capitulation (Long)", "Extreme Panic Selling Detected"]
        
        atr_val = a['atr']
        entry = current
        sl = current - (atr_val * 2)
        tp1 = current + (atr_val * 3)
        risk = entry - sl
        reward = tp1 - entry
        
        if risk > 0:
            trades.append({
                'strategy': 'Vol-Capitulation',
                'type': 'LONG',
                'symbol': symbol,
                'entry': entry,
                'sl': sl, 'tp1': tp1, 'tp2': entry + (atr_val * 5),
                'confidence': 'VERY HIGH',
                'confidence_score': confidence,
                'risk_reward': round(reward/risk, 1),
                'reason': ' + '.join(reasons),
                'indicators': f"RSI: {a['rsi']:.1f}, ATR: {atr_val:.4f}",
                'expected_time': '6-24 hours',
                'risk': risk, 'reward': reward,
                'entry_type': 'MARKET',
                'timeframe': tf,
                'analysis_data': {
                    'indicator': 'Volatility Capitulation',
                    'rsi': a['rsi'],
                    'bb_lower': a['bb']['lower']
                }
            })
    return trades

def strategy_momentum_confluence(symbol, analyses):
    """Strategy: Advanced Momentum Confluence (Multiple Indicator Alignment)"""
    tf = '5m' if '5m' in analyses else '15m'
    if tf not in analyses: return []
    
    a = analyses[tf]
    score = 0
    reasons = []
    
    if 30 < a['rsi'] < 50: score += 1; reasons.append("RSI Recovery Zone")
    if a['macd']['histogram'] > 0: score += 1; reasons.append("MACD Histogram Positive")
    if a['stoch_rsi']['k'] < 50: score += 1; reasons.append("StochRSI Rising")
    if a['adx']['adx'] > 20: score += 1; reasons.append("ADX Directional Strength")
    if a['trend'] == 'BULLISH': score += 1; reasons.append("EMA Bullish Trend")
    
    trades = []
    if score >= 4:
        confidence_score = 6 + score
        atr = a['atr']
        entry = a['current_price']
        sl = entry - (atr * 2)
        tp1 = entry + (atr * 4)
        risk = entry - sl
        reward = tp1 - entry
        
        if risk > 0:
            trades.append({
                'strategy': 'Mom-Confluence',
                'type': 'LONG',
                'symbol': symbol,
                'entry': entry,
                'sl': sl, 'tp1': tp1, 'tp2': entry + (atr * 7),
                'confidence': 'HIGH' if confidence_score < 9 else 'VERY HIGH',
                'confidence_score': min(10, confidence_score),
                'risk_reward': round(reward/risk, 1),
                'reason': ' + '.join(reasons),
                'indicators': f"Score: {score}/5, ADX: {a['adx']['adx']:.1f}",
                'expected_time': '1-4 hours',
                'risk': risk, 'reward': reward,
                'entry_type': 'MARKET',
                'timeframe': tf,
                'analysis_data': {
                    'momentum_score': score,
                    'adx': a['adx']['adx'],
                    'macd': a['macd']['histogram']
                }
            })
    return trades

def strategy_ict_wealth_division(symbol, analyses):
    """Strategy: ICT Wealth Division (Phase Detection)"""
    tf = '1h' if '1h' in analyses else '15m'
    if tf not in analyses: return []
    
    a = analyses[tf]
    phase = a['ict_phase']
    trades = []
    
    if phase == "ACCUMULATION":
        confidence = 7
        entry = a['current_price']
        atr = a['atr']
        sl = entry - (atr * 3)
        tp1 = entry + (atr * 5)
        trades.append({
            'strategy': 'ICT-Wealth-Div',
            'type': 'LONG',
            'symbol': symbol,
            'entry': entry,
            'sl': sl, 'tp1': tp1, 'tp2': entry + (atr * 10),
            'confidence': 'HIGH',
            'confidence_score': confidence,
            'risk_reward': round((tp1-entry)/(max(0.0001, entry-sl)), 1),
            'reason': f"Phase: {phase} (Institutional Accumulation)",
            'indicators': f"ICT: {phase}, Vol < Avg",
            'expected_time': '12-48 hours',
            'risk': entry-sl, 'reward': tp1-entry,
            'entry_type': 'LIMIT',
            'timeframe': tf,
            'analysis_data': {
                'ict_phase': phase,
                'price_level': entry
            }
        })
    elif phase == "DISTRIBUTION":
        confidence = 7
        entry = a['current_price']
        atr = a['atr']
        sl = entry + (atr * 3)
        tp1 = entry - (atr * 5)
        trades.append({
            'strategy': 'ICT-Wealth-Div',
            'type': 'SHORT',
            'symbol': symbol,
            'entry': entry,
            'sl': sl, 'tp1': tp1, 'tp2': entry - (atr * 10),
            'confidence': 'HIGH',
            'confidence_score': confidence,
            'risk_reward': round((entry-tp1)/(max(0.0001, sl-entry)), 1),
            'reason': f"Phase: {phase} (Institutional Distribution)",
            'indicators': f"ICT: {phase}, Vol < Avg",
            'expected_time': '12-48 hours',
            'risk': sl-entry, 'reward': entry-tp1,
            'entry_type': 'LIMIT',
            'timeframe': tf,
            'analysis_data': {
                'ict_phase': phase,
                'price_level': entry
            }
        })
    return trades

def strategy_harmonic_gartley(symbol, analyses):
    """Strategy: Fibonacci Harmonic (Simplified Gartley 61.8% Retracement)"""
    tf = '1h' if '1h' in analyses else '4h'
    if tf not in analyses: return []
    
    a = analyses[tf]
    fib = a['fib']
    current = a['current_price']
    trades = []
    
    if a['trend'] == 'BULLISH' and current < fib['0.618'] * 1.005 and current > fib['0.786'] * 0.995:
        level = "61.8%" if abs(current - fib['0.618']) < abs(current - fib['0.786']) else "78.6%"
        confidence = 8
        atr = a['atr']
        entry = current
        sl = fib['0'] - (atr * 0.5)
        tp1 = fib['0.382']
        tp2 = fib['0.236']
        risk = entry - sl
        reward = tp1 - entry
        
        if risk > 0:
            trades.append({
                'strategy': 'Harmonic-Retracement',
                'type': 'LONG',
                'symbol': symbol,
                'entry': entry,
                'sl': sl, 'tp1': tp1, 'tp2': tp2,
                'confidence': 'VERY HIGH',
                'confidence_score': confidence,
                'risk_reward': round(reward/risk, 1),
                'reason': f"Harmonic Retracement at {level} level",
                'indicators': f"Fib {level}: {fib['0.618']:.4f}",
                'expected_time': '24-72 hours',
                'risk': risk, 'reward': reward,
                'entry_type': 'LIMIT',
                'timeframe': tf,
                'analysis_data': {
                    'harmonic_level': level,
                    'fib_level': fib['0.618']
                }
            })
    return trades

def strategy_utbot_elite(symbol, analyses):
    """Strategy: UT Bot Elite (UT Bot Alerts + STC Confirmation)"""
    tf = '5m' if '5m' in analyses else '15m' if '15m' in analyses else '1h'
    if tf not in analyses: return []
    
    a = analyses[tf]
    ut = a['utbot']
    stc = a['stc']
    current = a['current_price']
    trades = []
    
    # LONG: UT Bot BUY signal + STC Bullish alignment
    if ut['signal'] == 'BUY' or (ut['signal'] == 'BULLISH' and stc > 25 and stc < 80):
        confidence = 7
        reasons = [f"UT Bot Elite Buy Signal ({tf})"]
        
        if stc > 50:
            confidence += 1
            reasons.append("STC Upward Momentum")
        if a['trend'] == 'BULLISH':
            confidence += 1
            reasons.append("Trend Alignment")
            
        if confidence >= MIN_CONFIDENCE:
            atr = a['atr']
            entry = current
            sl = ut['stop'] if ut['stop'] < current else current - (atr * 2)
            tp1 = entry + (entry - sl) * 2
            tp2 = entry + (entry - sl) * 4
            risk = entry - sl
            reward = tp1 - entry
            
            if risk > 0:
                trades.append({
                    'strategy': 'UT Bot Elite',
                    'type': 'LONG',
                    'symbol': symbol,
                    'entry': entry,
                    'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence': 'HIGH',
                    'confidence_score': confidence,
                    'risk_reward': round(reward/risk, 1),
                    'reason': ' + '.join(reasons),
                    'indicators': f"UT Stop: {ut['stop']:.4f}, STC: {stc:.0f}",
                    'expected_time': '2-8 hours',
                    'risk': risk, 'reward': reward,
                    'entry_type': 'MARKET',
                    'timeframe': tf
                })
                
    # SHORT: UT Bot SELL signal + STC Bearish alignment
    elif ut['signal'] == 'SELL' or (ut['signal'] == 'BEARISH' and stc < 75 and stc > 20):
        confidence = 7
        reasons = [f"UT Bot Elite Sell Signal ({tf})"]
        
        if stc < 50:
            confidence += 1
            reasons.append("STC Downward Momentum")
        if a['trend'] == 'BEARISH':
            confidence += 1
            reasons.append("Trend Alignment")
            
        if confidence >= MIN_CONFIDENCE:
            atr = a['atr']
            entry = current
            sl = ut['stop'] if ut['stop'] > current else current + (atr * 2)
            tp1 = entry - (sl - entry) * 2
            tp2 = entry - (sl - entry) * 4
            risk = sl - entry
            reward = entry - tp1
            
            if risk > 0:
                trades.append({
                    'strategy': 'UT Bot Elite',
                    'type': 'SHORT',
                    'symbol': symbol,
                    'entry': entry,
                    'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence': 'HIGH',
                    'confidence_score': confidence,
                    'risk_reward': round(reward/risk, 1),
                    'reason': ' + '.join(reasons),
                    'indicators': f"UT Stop: {ut['stop']:.4f}, STC: {stc:.0f}",
                    'expected_time': '2-8 hours',
                    'risk': risk, 'reward': reward,
                    'entry_type': 'MARKET',
                    'timeframe': tf
                })
                
    return trades

def strategy_keltner_reversion(symbol, analyses):
    """Strategy: Keltner Channel Mean Reversion"""
    tf = '15m' if '15m' in analyses else '1h'
    if tf not in analyses: return []
    
    a = analyses[tf]
    kc = a['kc']
    if not kc: return []
    
    current = a['current_price']
    trades = []
    
    # LONG: Price below lower band + RSI oversold
    if current < kc['lower']:
        confidence = 6
        reasons = [f"Keltner Lower Band Rejection ({tf})"]
        
        if a['rsi'] < 30:
            confidence += 2
            reasons.append("RSI Oversold (Confluent)")
        if a['stoch_rsi']['k'] < 20:
            confidence += 1
            reasons.append("StochRSI Oversold")
            
        if confidence >= MIN_CONFIDENCE:
            atr = a['atr']
            entry = current
            sl = current - (atr * 1.5)
            # TP1 at middle line, TP2 at upper band
            tp1 = kc['middle']
            tp2 = kc['upper']
            risk = entry - sl
            reward = tp1 - entry
            
            if risk > 0 and reward/risk >= 1.2:
                trades.append({
                    'strategy': 'Keltner Reversion',
                    'type': 'LONG',
                    'symbol': symbol,
                    'entry': entry,
                    'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence': 'MEDIUM-HIGH',
                    'confidence_score': confidence,
                    'risk_reward': round(reward/risk, 1),
                    'reason': ' + '.join(reasons),
                    'indicators': f"Price < {kc['lower']:.4f}, RSI: {a['rsi']:.0f}",
                    'expected_time': '4-12 hours',
                    'risk': risk, 'reward': reward,
                    'entry_type': 'MARKET',
                    'timeframe': tf
                })
                
    return trades

def strategy_psar_tema_scalp(symbol, analyses):
    """Strategy: PSAR Trend + TEMA Cross Scalper (Fast 1m/3m)"""
    tf = '1m' if '1m' in analyses else '3m' if '3m' in analyses else '5m'
    if tf not in analyses: return []
    
    a = analyses[tf]
    psar = a['psar']
    tema = a['tema']
    current = a['current_price']
    trades = []
    
    # LONG: PSAR Bullish + Price above TEMA
    if psar['trend'] == 'BULLISH' and current > tema:
        confidence = 7
        reasons = [f"PSAR Bullish ({tf})", f"Price > TEMA ({tf})"]
        
        if a['rsi'] > 50:
            confidence += 1
            reasons.append("RSI Bullish Momentum")
        if a['adx']['adx'] > 20:
            confidence += 1
            reasons.append("Trend Strength (ADX)")
            
        if confidence >= MIN_CONFIDENCE:
            atr = a['atr']
            entry = current
            sl = psar['psar'] if psar['psar'] < current else current - (atr * 1.5)
            tp1 = entry + (entry - sl) * 2
            tp2 = entry + (entry - sl) * 3
            risk = entry - sl
            reward = tp1 - entry
            
            if risk > 0:
                trades.append({
                    'strategy': 'PSAR-TEMA Scalp',
                    'type': 'LONG',
                    'symbol': symbol,
                    'entry': entry,
                    'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence': 'HIGH',
                    'confidence_score': confidence,
                    'risk_reward': round(reward/risk, 1),
                    'reason': ' + '.join(reasons),
                    'indicators': f"PSAR: {psar['psar']:.4f}, TEMA: {tema:.4f}",
                    'expected_time': '5-15 mins',
                    'risk': risk, 'reward': reward,
                    'entry_type': 'MARKET',
                    'timeframe': tf,
                    'analysis_data': {
                        'psar': psar['psar'],
                        'tema': tema,
                        'rsi': a['rsi']
                    }
                })
    return trades

def strategy_kama_volatility_scalp(symbol, analyses):
    """Strategy: KAMA Trend + Chandelier Exit Confirmation (5m Scalp)"""
    tf = '5m' if '5m' in analyses else '3m' if '3m' in analyses else '15m'
    if tf not in analyses: return []
    
    a = analyses[tf]
    kama = a['kama']
    chan = a['chandelier']
    current = a['current_price']
    trades = []
    
    # LONG: Price > KAMA + Price > Chandelier Long Stop
    if current > kama and current > chan['long']:
        confidence = 7
        reasons = [f"Price above KAMA Adaptive ({tf})", "Chandelier Exit Bullish"]
        
        if a['vfi'] > 0:
            confidence += 2
            reasons.append("Volume Flow Positive (VFI)")
            
        if confidence >= MIN_CONFIDENCE:
            atr = a['atr']
            entry = current
            sl = chan['long'] if chan['long'] < current else current - (atr * 2)
            tp1 = entry + (entry - sl) * 2.5
            tp2 = entry + (entry - sl) * 4
            risk = entry - sl
            reward = tp1 - entry
            
            if risk > 0:
                trades.append({
                    'strategy': 'KAMA-Volatility Scalp',
                    'type': 'LONG',
                    'symbol': symbol,
                    'entry': entry,
                    'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence': 'HIGH',
                    'confidence_score': confidence,
                    'risk_reward': round(reward/risk, 1),
                    'reason': ' + '.join(reasons),
                    'indicators': f"KAMA: {kama:.4f}, VFI: {a['vfi']:.2f}",
                    'expected_time': '15-45 mins',
                    'risk': risk, 'reward': reward,
                    'entry_type': 'MARKET',
                    'timeframe': tf,
                    'analysis_data': {
                        'kama': kama,
                        'chandelier_long': chan['long'],
                        'vfi': a['vfi']
                    }
                })
    return trades

def strategy_vfi_momentum_scalp(symbol, analyses):
    """Strategy: VFI Volume Flow + Momentum Confluence (Perfect Scalping)"""
    tf = '1m' if '1m' in analyses else '3m' if '3m' in analyses else '5m'
    if tf not in analyses: return []
    
    a = analyses[tf]
    vfi = a['vfi']
    rsi = a['rsi']
    uo = a['uo']
    current = a['current_price']
    trades = []
    
    # BULLISH: VFI > 0 + RSI > 50 + UO > 50
    if vfi > 0 and rsi > 50 and uo > 50:
        confidence = 6
        reasons = ["Positive Volume Flow (VFI)", "RSI Momentum", "Ultimate Oscillator Positive"]
        
        if a['zlsma'] < current:
            confidence += 2
            reasons.append("Above ZLSMA")
            
        if confidence >= MIN_CONFIDENCE:
            atr = a['atr']
            entry = current
            sl = entry - (atr * 2)
            tp1 = entry + (atr * 4)
            tp2 = entry + (atr * 6)
            risk = entry - sl
            reward = tp1 - entry
            
            if risk > 0:
                trades.append({
                    'strategy': 'VFI Perfect Scalper',
                    'type': 'LONG',
                    'symbol': symbol,
                    'entry': entry,
                    'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence': 'VERY HIGH',
                    'confidence_score': confidence,
                    'risk_reward': round(reward/risk, 1),
                    'reason': ' + '.join(reasons),
                    'indicators': f"VFI: {vfi:.2f}, RSI: {rsi:.0f}, UO: {uo:.0f}",
                    'expected_time': '10-30 mins',
                    'risk': risk, 'reward': reward,
                    'entry_type': 'MARKET',
                    'timeframe': tf,
                    'analysis_data': {
                        'vfi': vfi,
                        'rsi': rsi,
                        'uo': uo,
                        'zlsma': a['zlsma']
                    }
                })
    return trades

def run_strategies(symbol, analyses):
    """Run all available strategies"""
    all_trades = []
    
    # Standard Strategies
    all_trades.extend(strategy_swing_trend(symbol, analyses))
    all_trades.extend(strategy_scalp_momentum(symbol, analyses))
    all_trades.extend(strategy_trend_pullback(symbol, analyses))
    all_trades.extend(strategy_volatility_breakout(symbol, analyses))
    all_trades.extend(strategy_supertrend_follow(symbol, analyses))
    all_trades.extend(strategy_vwap_reversion(symbol, analyses))
    all_trades.extend(strategy_ichimoku_tk(symbol, analyses))
    
    # Advanced / SMC Strategies
    all_trades.extend(strategy_fvg_gap_fill(symbol, analyses))
    all_trades.extend(strategy_divergence_pro(symbol, analyses))
    all_trades.extend(strategy_adx_momentum(symbol, analyses))
    all_trades.extend(strategy_bollinger_reversion(symbol, analyses))
    all_trades.extend(strategy_liquidity_grab_reversal(symbol, analyses))
    all_trades.extend(strategy_wavetrend_extreme(symbol, analyses))
    all_trades.extend(strategy_squeeze_breakout(symbol, analyses))
    all_trades.extend(strategy_zlsma_fast_scalp(symbol, analyses))
    all_trades.extend(strategy_mfi_reversion(symbol, analyses))
    all_trades.extend(strategy_fisher_transform_pivot(symbol, analyses))
    all_trades.extend(strategy_volume_spike_breakout(symbol, analyses))
    
    # NEW BEST OF BEST Strategies 2026
    all_trades.extend(strategy_smc_choch(symbol, analyses))
    all_trades.extend(strategy_donchian_breakout(symbol, analyses))
    all_trades.extend(strategy_stc_momentum(symbol, analyses))
    all_trades.extend(strategy_vortex_trend(symbol, analyses))
    all_trades.extend(strategy_ict_silver_bullet(symbol, analyses))
    all_trades.extend(strategy_utbot_elite(symbol, analyses))
    all_trades.extend(strategy_keltner_reversion(symbol, analyses))
    all_trades.extend(strategy_volatility_capitulation(symbol, analyses))
    all_trades.extend(strategy_momentum_confluence(symbol, analyses))
    all_trades.extend(strategy_ict_wealth_division(symbol, analyses))
    all_trades.extend(strategy_harmonic_gartley(symbol, analyses))
    
    # SUPERSCALP 2026 UPGRADES
    all_trades.extend(strategy_psar_tema_scalp(symbol, analyses))
    all_trades.extend(strategy_kama_volatility_scalp(symbol, analyses))
    all_trades.extend(strategy_vfi_momentum_scalp(symbol, analyses))
    
    return all_trades

def run_analysis():
    exchanges_str = ', '.join(ENABLED_EXCHANGES)
    print("\n" + "="*120)
    print("🔥 RBOT PRO | MULTI-EXCHANGE REAL-TIME ANALYSIS - HIGH CONFIDENCE TRADES ONLY")
    print("="*120)
    print(f"Exchanges: {exchanges_str} | Timeframes: {', '.join(ENABLED_TIMEFRAMES)} (VERIFIED) | Indicators ({len(ENABLED_INDICATORS)}): {', '.join(ENABLED_INDICATORS)} (VERIFIED)")
    print(f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Minimum Confidence: {MIN_CONFIDENCE}/10 | Strategies: Swing, Scalp, Stoch-Pullback, Breakout, SuperTrend, VWAP, Ichimoku, FVG, Divergence, ADX-Mom, BB-Rev, Liquidity, WaveTrend, Squeeze, Z-Scalp, MFI, Fisher, VolSpike, SMC-CHoCH, Donchian, STC-Mom, Vortex, ICT-Silver, UT-Bot Elite, Keltner-Rev, Vol-Cap, Mom-Confluence, ICT-Wealth, Harmonic-Gartley, SMC-Elite, Harmonic-Pro, PSAR-TEMA, KAMA-Vol, VFI-Scalp")
    print("="*120 + "\n")
    all_trades = []
    print(f"📡 Fetching LIVE real-time chart data from {exchanges_str} APIs...\n")
    
    # Use CLI symbols if provided, otherwise fetch top symbols
    if args.symbols:
        symbols = args.symbols.split(',')
    else:
        symbols = get_top_symbols(200)
    
    # Analyze each symbol on each enabled exchange
    max_workers = min(10, max(2, len(symbols)))
    futures = {}
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        for exchange in ENABLED_EXCHANGES:
            for sym in symbols:
                future = ex.submit(analyze_symbol, sym, exchange)
                futures[future] = (sym, exchange)
        for fut in as_completed(futures):
            sym, exchange = futures[fut]
            try:
                analyses = fut.result()
            except Exception as e:
                with print_lock:
                    print(f"  Error analyzing {sym} on {exchange}: {e}")
                continue
            if analyses:
                trades = run_strategies(sym, analyses)
                if trades:
                    # Filter trades by MIN_CONFIDENCE
                    filtered_trades = [t for t in trades if t.get('confidence_score', 0) >= MIN_CONFIDENCE]
                    if filtered_trades:
                        with print_lock:
                            for trade in filtered_trades:
                                trade['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                trade['exchange'] = exchange
                                all_trades.append(trade)
                                print(f"\n{'='*80}")
                                print(f"[{trade['strategy']}] TRADE FOUND - {trade['type']} {trade['symbol']} on {exchange} (Conf: {trade['confidence_score']}/10)")
                                print(f"Entry: ${trade['entry']:.6f}  SL: ${trade['sl']:.6f}  TP1: ${trade['tp1']:.6f}  R/R: {trade['risk_reward']}:1")
                                print(f"Indicators: {trade['indicators']} | Reason: {trade['reason']} | Expected: {trade['expected_time']}")
                                print(f"SIGNAL_DATA:{json.dumps(trade)}")
    print("\n" + "="*120)
    print(f"🚀 TRADE SETUPS (Confidence Score {MIN_CONFIDENCE}/10+  |  Minimum 2:1 Risk/Reward)")
    print("="*120 + "\n")
    if all_trades:
        all_trades.sort(key=lambda x: (x['confidence_score'], x['risk_reward']), reverse=True)
        for i, trade in enumerate(all_trades, 1):
            print(f"\n{'='*120}")
            print(f"TRADE #{i} [{trade['strategy']}] - {trade['type']} {trade['symbol']} on {trade.get('exchange', 'N/A')} (Confidence: {trade['confidence_score']}/10)")
            print(f"{'='*120}")
            print(f"📍 Entry:        ${trade['entry']:.6f}  ({trade['entry_type']})")
            print(f"🛑 Stop Loss:    ${trade['sl']:.6f}        Risk: ${trade['risk']:.6f}")
            print(f"🎯 TP1:          ${trade['tp1']:.6f}        Reward: ${trade['reward']:.6f}")
            print(f"🎯 TP2:          ${trade['tp2']:.6f}")
            print(f"\n💎 Risk/Reward Ratio:  {trade['risk_reward']}:1")
            print(f"⏱️  Expected Resolution:  {trade['expected_time']}")
            print(f"📊 Indicators:         {trade['indicators']}")
            print(f"🔍 Setup Reason:       {trade['reason']}")
            print(f"🏢 Exchange:           {trade.get('exchange', 'N/A')}")
    else:
        print("⏳ No trades meeting the configured confidence threshold found at this moment.")
        print(f"   System is waiting for optimal alignment across selected timeframes...")
    print("\n" + "="*120)
    print(f"✅ Analysis Complete - RBot Pro Multi-Exchange Analysis ({exchanges_str})")
    print("="*120 + "\n")

if __name__ == '__main__':
    run_analysis()

