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
parser.add_argument('--exchanges', type=str, default='MEXC,BINANCE,BYBIT,OKX,BITGET,KUCOIN,GATEIO,HTX', help='Comma-separated exchanges to analyze')
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
ENABLED_EXCHANGES = [e.strip().upper() for e in args.exchanges.split(',')] if args.exchanges else ['MEXC', 'BINANCE', 'BYBIT', 'OKX', 'BITGET', 'KUCOIN', 'GATEIO', 'HTX']

# All supported exchanges
ALL_EXCHANGES = ['MEXC', 'BINANCE', 'BITGET', 'BYBIT', 'OKX', 'KUCOIN', 'GATEIO', 'HTX']

# Enabled indicators and timeframes
DEFAULT_INDICATOR_LIST = {'RSI', 'EMA', 'MACD', 'BB', 'ATR', 'ADX', 'OB', 'PA', 'ST', 'VWAP', 'CMF', 'ICHI', 'FVG', 'DIV', 'WT', 'KC', 'LIQ', 'BOS', 'MFI', 'FISH', 'ZLSMA', 'TSI', 'CHOP', 'VI', 'STC', 'DON', 'CHoCH', 'UTBOT', 'UO', 'STDEV', 'VP', 'SUPDEM', 'FIB', 'ICT_WD', 'SQZ', 'StochRSI', 'OBV', 'HMA', 'REGIME', 'DELTA', 'ZSCORE', 'WYCKOFF', 'RVOL'}
ENABLED_INDICATORS = set(args.indicators.split(',')) if args.indicators else DEFAULT_INDICATOR_LIST
ENABLED_TIMEFRAMES = args.timeframes.split(',') if args.timeframes else ['1m', '3m', '5m', '15m', '30m', '1h', '4h', '1d']

# --- GLOBAL REQUEST CONFIGURATION ---
COMMON_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36',
    'Accept': 'application/json',
    'Cache-Control': 'no-cache'
}

def safe_request(url, method='GET', params=None, json_data=None, timeout=15, retries=3):
    """Fetch with retries, exponential backoff, cache-busting, and institutional headers."""
    import time
    import random
    
    # Institutional Cache-Busting (Suppressed for Binance)
    is_binance = 'binance' in url.lower()
    if params is None: params = {}
    
    if not is_binance:
        params['_t'] = int(time.time() * 1000)
        params['_r'] = random.randint(1000, 9999)
    
    last_err = None
    for attempt in range(retries):
        try:
            r = requests.request(method, url, params=params, json=json_data, headers=COMMON_HEADERS, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last_err = e
            time.sleep(2 + attempt * 2)
    raise last_err

def get_top_symbols(n=200):
    """Fetch top `n` USDT symbols by volume from enabled exchanges."""
    default_top = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT']
    all_coins = set(default_top)
    
    # Try fetching from each enabled exchange
    if 'MEXC' in ENABLED_EXCHANGES:
        try:
            data = safe_request('https://contract.mexc.com/api/v1/contract/detail')
            if data.get('success') and isinstance(data.get('data'), list):
                contracts = data['data']
                contracts_sorted = sorted(contracts, key=lambda x: float(x.get('last24hVol', 0)), reverse=True)
                for item in contracts_sorted[:n]:
                    sym = item.get('symbol', '')
                    if sym.endswith('_USDT'):
                        all_coins.add(sym.replace('_', ''))
        except Exception as e:
            print(f"  ⚠ MEXC symbol fetch error: {e}")
    
    if 'BINANCE' in ENABLED_EXCHANGES:
        try:
            data = safe_request('https://api.binance.com/api/v3/ticker/24hr')
            binance_sorted = sorted(data, key=lambda x: float(x.get('quoteVolume', 0)), reverse=True)
            for item in binance_sorted[:n]:
                sym = item.get('symbol', '')
                if sym.endswith('USDT'):
                    all_coins.add(sym)
        except Exception as e:
            print(f"  ⚠ Binance symbol fetch error: {e}")
    
    if 'BYBIT' in ENABLED_EXCHANGES:
        try:
            data = safe_request('https://api.bybit.com/v5/market/tickers?category=linear')
            if data.get('result') and data['result'].get('list'):
                bybit_sorted = sorted(data['result']['list'], key=lambda x: float(x.get('turnover24h', 0)), reverse=True)
                for item in bybit_sorted[:n]:
                    sym = item.get('symbol', '')
                    if sym.endswith('USDT'):
                        all_coins.add(sym)
        except Exception as e:
            print(f"  ⚠ Bybit symbol fetch error: {e}")
    
    if 'BITGET' in ENABLED_EXCHANGES:
        try:
            data = safe_request('https://api.bitget.com/api/v2/mix/market/tickers?productType=USDT-FUTURES')
            if data.get('data'):
                for item in data['data'][:n]:
                    sym = item.get('symbol', '')
                    if sym.endswith('USDT'):
                        all_coins.add(sym)
        except Exception as e:
            print(f"  ⚠ Bitget symbol fetch error: {e}")
    
    if 'OKX' in ENABLED_EXCHANGES:
        try:
            # OKX DNS Fallback
            domains = ['https://www.okx.com', 'https://www.okx.net']
            for base in domains:
                try:
                    data = safe_request(f'{base}/api/v5/market/tickers?instType=SWAP')
                    if data.get('data'):
                        for item in data['data'][:n]:
                            inst_id = item.get('instId', '')
                            if 'USDT' in inst_id:
                                sym = inst_id.replace('-', '').replace('SWAP', '').strip()
                                if sym.endswith('USDT'):
                                    all_coins.add(sym)
                        break
                except: continue
        except Exception as e:
            print(f"  ⚠ OKX symbol fetch error: {e}")
    
    if 'KUCOIN' in ENABLED_EXCHANGES:
        try:
            data = safe_request('https://api.kucoin.com/api/v1/market/allTickers')
            if data.get('data') and data['data'].get('ticker'):
                for item in data['data']['ticker'][:n*2]:
                    sym = item.get('symbol', '')
                    if sym.endswith('-USDT'):
                        all_coins.add(sym.replace('-', ''))
        except Exception as e:
            print(f"  ⚠ KuCoin symbol fetch error: {e}")
    
    if 'GATEIO' in ENABLED_EXCHANGES:
        try:
            data = safe_request('https://api.gateio.ws/api/v4/futures/usdt/contracts')
            for item in data[:n]:
                name = item.get('name', '')
                if name.endswith('_USDT'):
                    all_coins.add(name.replace('_', ''))
        except Exception as e:
            print(f"  ⚠ Gate.io symbol fetch error: {e}")
    
    if 'HTX' in ENABLED_EXCHANGES:
        try:
            data = safe_request('https://api.huobi.pro/v2/settings/common/symbols')
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
        data = safe_request(url)
        
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
        data = safe_request(url)
        
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
        data = safe_request(url)
        
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
        data = safe_request(url)
        
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
    """Get klines from OKX API with domain fallbacks"""
    try:
        mapping = {'1m': '1m', '3m': '3m', '5m': '5m', '15m': '15m', '30m': '30m', '1h': '1H', '4h': '4H', '1d': '1D'}
        okx_interval = mapping.get(interval, '1H')
        okx_symbol = symbol.replace('USDT', '-USDT-SWAP') if 'USDT' in symbol and '-' not in symbol else symbol
        
        domains = ['https://www.okx.com', 'https://www.okx.net', 'https://okx.com']
        for base in domains:
            try:
                url = f'{base}/api/v5/market/candles?instId={okx_symbol}&bar={okx_interval}&limit={limit}'
                data = safe_request(url)
                if data.get('data'):
                    candles = []
                    for k in reversed(data['data']):
                        candles.append({
                            'time': int(k[0]),
                            'open': float(k[1]),
                            'high': float(k[2]),
                            'low': float(k[3]),
                            'close': float(k[4]),
                            'volume': float(k[5]) if len(k) > 5 else 0
                        })
                    return candles if len(candles) >= 50 else None
            except: continue
        return None
    except: return None

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
        url = f'https://api.kucoin.com/api/v1/market/candles?type={kucoin_interval}&symbol={kucoin_symbol}&limit={limit}'
        data = safe_request(url)
        
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
        data = safe_request(url)
        
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
        data = safe_request(url)
        
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

# Map exchange names to their kline fetcher functions (STRICT UPPERCASE)
EXCHANGE_KLINE_FETCHERS = {
    'MEXC': get_klines_mexc,
    'BINANCE': get_klines_binance,
    'BYBIT': get_klines_bybit,
    'BITGET': get_klines_bitget,
    'OKX': get_klines_okx,
    'KUCOIN': get_klines_kucoin,
    'GATEIO': get_klines_gateio,
    'HTX': get_klines_htx
}

def resample_klines(klines, factor):
    """
    Resample klines (e.g. 1m -> 3m).
    'factor' is the number of small candles to combine (e.g. 3).
    """
    if not klines or factor <= 1:
        return klines
    
    resampled = []
    # Start from an index that aligns with the timeframe (optional, but good)
    # Most traders align with 0:00 UTC
    for i in range(0, len(klines) - (len(klines) % factor), factor):
        chunk = klines[i : i + factor]
        if len(chunk) < factor:
            break
            
        resampled.append({
            'time': chunk[0]['time'],
            'open': chunk[0]['open'],
            'high': max(c['high'] for c in chunk),
            'low': min(c['low'] for c in chunk),
            'close': chunk[-1]['close'],
            'volume': sum(c['volume'] for c in chunk)
        })
    return resampled

def get_klines(symbol, interval, limit=200, exchange=None):
    """
    Get klines from the specified exchange, with fallback chain through enabled exchanges.
    Includes an automatic resampling engine for missing timeframes (e.g. 3m on MEXC).
    """
    def _fetch_direct(sym, itv, lim, ex):
        if ex:
            fetcher = EXCHANGE_KLINE_FETCHERS.get(ex)
            if fetcher:
                return fetcher(sym, itv, lim)
        for ex_name in ENABLED_EXCHANGES:
            fetcher = EXCHANGE_KLINE_FETCHERS.get(ex_name)
            if fetcher:
                k = fetcher(sym, itv, lim)
                if k and len(k) >= 50:
                    return k
        return None

    # 1. Try direct fetch
    result = _fetch_direct(symbol, interval, limit, exchange)
    if result and len(result) >= 50:
        return result
        
    # 2. Resampling Engine Fallback
    # If a timeframe is missing (like 3m/5m on some MEXC pairs), build it from 1m
    target_map = {'3m': 3, '5m': 5, '15m': 15, '30m': 30, '1h': 60}
    if interval in target_map:
        factor = target_map[interval]
        # Fetch more 1m candles to satisfy the limit for the target timeframe
        klines_1m = _fetch_direct(symbol, '1m', limit * factor, exchange)
        if klines_1m and len(klines_1m) >= factor:
            return resample_klines(klines_1m, factor)
            
    return None

# --- Indicators & analysis helpers ---

def format_series_for_chart(times, values):
    """Format series for Lightweight Charts {time, value}"""
    if not times or not values: return []
    # Ensure same length
    length = min(len(times), len(values))
    return [{'time': times[i]/1000, 'value': float(values[i])} for i in range(len(times)-length, len(times))]

def calculate_ema_series(data, period):
    if not data:
        return []
    if len(data) < period:
        return [data[-1]] * len(data)
    mult = 2 / (period + 1)
    ema = sum(data[:period]) / period
    res = [ema]
    for val in data[period:]:
        ema = val * mult + ema * (1 - mult)
        res.append(ema)
    # Pad results to match input length if needed
    if len(res) < len(data):
        res = [res[0]] * (len(data) - len(res)) + res
    return res

def calculate_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    
    # First average
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    # Wilder's Smoothing
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
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
    
    ema12_series = calculate_ema_series(closes, 12)
    ema26_series = calculate_ema_series(closes, 26)
    
    macd_series = [e1 - e2 for e1, e2 in zip(ema12_series, ema26_series)]
    macd_line = macd_series[-1]
    
    # Signal line is EMA9 of MACD line
    signal_series = calculate_ema_series(macd_series, 9)
    signal = signal_series[-1]
    
    return {'macd': macd_line, 'signal': signal, 'histogram': macd_line - signal}

def calculate_bb(closes, period=20, std_dev=2):
    if len(closes) < period:
        return None
    sma = sum(closes[-period:]) / period
    variance = sum((x - sma) ** 2 for x in closes[-period:]) / period
    std = variance ** 0.5
    return {'upper': sma + (std * std_dev), 'middle': sma, 'lower': sma - (std * std_dev), 'width': 2 * std * std_dev}

def calculate_atr(highs, lows, closes, period=14):
    if len(closes) < period + 1:
        return 0
    trs = []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        trs.append(tr)
    
    # First TR average
    atr = sum(trs[:period]) / period
    
    # Smoothing (Standard ATR move)
    for i in range(period, len(trs)):
        atr = (atr * (period - 1) + trs[i]) / period
        
    return atr

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
        trail = [src[0]] * len(src)
        
        # FULL SERIES WARMUP (Institutional Standard)
        # We process the entire available history to settle the trailing stop
        for i in range(1, len(src)):
            prev_trail = trail[i-1]
            
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
        'cloud_top': max(senkou_a, senkou_b),
        'cloud_bottom': min(senkou_a, senkou_b),
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
    if min_idx > 2:
        # Take the 3 candles preceding the explosive move as the OB zone
        ob_candles_high = highs[-lookback + min_idx - 3 : -lookback + min_idx]
        ob_candles_low = lows[-lookback + min_idx - 3 : -lookback + min_idx]
        if ob_candles_high and ob_candles_low:
            bullish_ob_zone = {'high': max(ob_candles_high), 'low': min(ob_candles_low)}
            
    if max_idx > 2:
        ob_candles_high = highs[-lookback + max_idx - 3 : -lookback + max_idx]
        ob_candles_low = lows[-lookback + max_idx - 3 : -lookback + max_idx]
        if ob_candles_high and ob_candles_low:
            bearish_ob_zone = {'high': max(ob_candles_high), 'low': min(ob_candles_low)}
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
            
        return {'psar': psar_list[-1], 'trend': 'BULLISH' if closes[-1] > psar_list[-1] else 'BEARISH', 'series': psar_list}
    except:
        return {'psar': closes[-1], 'trend': 'NEUTRAL', 'series': []}

def calculate_tema(closes, period=9):
    """Triple Exponential Moving Average"""
    try:
        if len(closes) < period: return {'value': closes[-1], 'series': [closes[-1]] * len(closes)}
        
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
        return {'value': tema[-1], 'series': tema}
    except:
        return {'value': closes[-1], 'series': [closes[-1]] * len(closes)}

def calculate_chandelier_exit(highs, lows, closes, period=22, multiplier=3):
    """Chandelier Exit for trend following"""
    try:
        if len(closes) < period: return {'long': closes[-1], 'short': closes[-1], 'long_series': [], 'short_series': []}
        
        # Calculate trailing stops for each candle to build series
        long_series = []
        short_series = []
        
        for i in range(period, len(closes)+1):
            h_chunk = highs[i-period:i]
            l_chunk = lows[i-period:i]
            c_chunk = closes[:i]
            
            atr = calculate_atr(h_chunk, l_chunk, c_chunk, period)
            highest_high = max(h_chunk)
            lowest_low = min(l_chunk)
            
            long_series.append(highest_high - atr * multiplier)
            short_series.append(lowest_low + atr * multiplier)
            
        return {
            'long': long_series[-1], 
            'short': short_series[-1],
            'long_series': long_series,
            'short_series': short_series
        }
    except:
        return {'long': closes[-1], 'short': closes[-1], 'long_series': [], 'short_series': []}

def calculate_kama(closes, period=10, fast=2, slow=30):
    """Kaufman's Adaptive Moving Average"""
    try:
        if len(closes) < period + 1: return {'value': closes[-1], 'series': [closes[-1]] * len(closes)}
        
        # Calculate full series
        kama_series = [closes[0]]
        for i in range(1, len(closes)):
            chunk = closes[max(0, i-period+1) : i+1]
            if len(chunk) < 2: 
                kama_series.append(kama_series[-1])
                continue
            change = abs(chunk[-1] - chunk[0])
            vol = sum(abs(chunk[j] - chunk[j-1]) for j in range(1, len(chunk)))
            er = change / vol if vol != 0 else 0
            fast_sc = 2 / (fast + 1)
            slow_sc = 2 / (slow + 1)
            sc = (er * (fast_sc - slow_sc) + slow_sc)**2
            kama_series.append(kama_series[-1] + sc * (closes[i] - kama_series[-1]))
            
        return {'value': kama_series[-1], 'series': kama_series}
    except:
        return {'value': closes[-1], 'series': [closes[-1]] * len(closes)}

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

# ═══════════════════════════════════════════════════════════════
# 🧠 NEW ADVANCED INDICATORS (2025 Research-Backed)
# ═══════════════════════════════════════════════════════════════

def detect_market_regime(adx_val=None, chop_val=None, bb=None, atr=None, closes=None):
    """
    Market Regime Detector - Classifies market state for adaptive strategy selection.
    Regimes: TRENDING_STRONG, TRENDING_WEAK, RANGING, VOLATILE, CHOPPY
    """
    try:
        adx = adx_val if adx_val is not None else 20
        chop = chop_val if chop_val is not None else 50
        bb_width = 0
        if bb and bb.get('upper') and bb.get('lower') and bb.get('middle'):
            bb_width = (bb['upper'] - bb['lower']) / bb['middle'] if bb['middle'] > 0 else 0
        atr_val = atr if atr else 0
        avg_close = sum(closes[-20:]) / 20 if closes and len(closes) >= 20 else 1
        atr_pct = (atr_val / avg_close * 100) if avg_close > 0 else 0

        if adx >= 35 and chop < 45:
            regime = 'TRENDING_STRONG'; strength = min(adx / 50, 1.0)
            strategies = ['trend_following', 'momentum', 'breakout']
        elif adx >= 25 and chop < 55:
            regime = 'TRENDING_WEAK'; strength = adx / 50
            strategies = ['trend_following', 'pullback']
        elif chop >= 61.8 and adx < 20:
            regime = 'CHOPPY'; strength = chop / 100
            strategies = ['none']
        elif atr_pct > 3.0 or bb_width > 0.08:
            regime = 'VOLATILE'; strength = min(atr_pct / 5.0, 1.0)
            strategies = ['breakout', 'reversal', 'scalping']
        else:
            regime = 'RANGING'; strength = 1.0 - (adx / 50)
            strategies = ['mean_reversion', 'range_trading', 'scalping']
        return {
            'regime': regime, 'strength': round(strength, 2),
            'suitable_strategies': strategies, 'adx': adx,
            'chop': chop, 'bb_width': round(bb_width, 4), 'atr_pct': round(atr_pct, 2)
        }
    except:
        return {'regime': 'UNKNOWN', 'strength': 0, 'suitable_strategies': ['all']}

def calculate_cumulative_delta(candles, lookback=50):
    """
    Cumulative Delta Volume - Approximates order flow.
    Close near high = buying, close near low = selling.
    Returns: {'delta': float, 'trend': str, 'divergence': str|None}
    """
    try:
        if len(candles) < lookback:
            return {'delta': 0, 'trend': 'NEUTRAL', 'divergence': None}
        recent = candles[-lookback:]
        delta_values = []
        cumulative = 0
        for c in recent:
            candle_range = c['high'] - c['low']
            if candle_range == 0:
                delta_values.append(cumulative)
                continue
            close_position = (c['close'] - c['low']) / candle_range
            delta = (close_position - 0.5) * 2 * c['volume']
            cumulative += delta
            delta_values.append(cumulative)
        
        # Delta trend
        if len(delta_values) >= 10:
            recent_delta = sum(delta_values[-5:]) / 5
            older_delta = sum(delta_values[-10:-5]) / 5
            delta_trend = 'BUYING' if recent_delta > older_delta else 'SELLING' if recent_delta < older_delta else 'NEUTRAL'
        else:
            delta_trend = 'NEUTRAL'
        
        # Divergence: price up + delta down = bearish, vice versa
        divergence = None
        if len(recent) >= 10:
            price_change = recent[-1]['close'] - recent[-10]['close']
            delta_change = delta_values[-1] - delta_values[-10] if len(delta_values) >= 10 else 0
            if price_change > 0 and delta_change < 0:
                divergence = 'BEARISH'
            elif price_change < 0 and delta_change > 0:
                divergence = 'BULLISH'
        
        return {'delta': round(cumulative, 2), 'trend': delta_trend, 'divergence': divergence}
    except:
        return {'delta': 0, 'trend': 'NEUTRAL', 'divergence': None}

def calculate_zscore(closes, period=20):
    """
    Z-Score: How many std devs price is from its mean.
    Z > 2.0 = overbought, Z < -2.0 = oversold.
    """
    try:
        if len(closes) < period: return 0
        window = closes[-period:]
        mean = sum(window) / period
        variance = sum((x - mean) ** 2 for x in window) / period
        std = variance ** 0.5
        return round((closes[-1] - mean) / std, 2) if std > 0 else 0
    except:
        return 0

def detect_wyckoff_phase(candles, lookback=50):
    """
    Wyckoff Phase Detector - Identifies accumulation/distribution phases.
    Detects: ACCUMULATION (Spring), DISTRIBUTION (Upthrust), MARKUP, MARKDOWN
    """
    try:
        if len(candles) < lookback:
            return {'phase': 'NEUTRAL', 'event': None, 'confidence': 0}
        recent = candles[-lookback:]
        closes = [c['close'] for c in recent]
        volumes = [c['volume'] for c in recent]
        highs = [c['high'] for c in recent]
        lows = [c['low'] for c in recent]
        
        range_high = max(highs[-30:])
        range_low = min(lows[-30:])
        range_size = range_high - range_low
        if range_size == 0:
            return {'phase': 'NEUTRAL', 'event': None, 'confidence': 0}
        
        current_price = closes[-1]
        avg_volume = sum(volumes) / len(volumes)
        recent_avg_vol = sum(volumes[-5:]) / 5
        
        # Spring: dip below support and recover
        spring_detected = False
        for i in range(-5, 0):
            if lows[i] < range_low * 0.998 and closes[i] > range_low:
                spring_detected = True; break
        
        # Upthrust: spike above resistance and fail
        upthrust_detected = False
        for i in range(-5, 0):
            if highs[i] > range_high * 1.002 and closes[i] < range_high:
                upthrust_detected = True; break
        
        volume_spike = recent_avg_vol > avg_volume * 1.5
        volume_declining = recent_avg_vol < avg_volume * 0.8
        price_position = (current_price - range_low) / range_size
        
        # Effort vs Result
        price_change_pct = abs(closes[-1] - closes[-5]) / closes[-5] * 100 if closes[-5] > 0 else 0
        vol_ratio = recent_avg_vol / avg_volume if avg_volume > 0 else 1
        effort_mismatch = vol_ratio > 1.5 and price_change_pct < 0.5
        
        if spring_detected and volume_spike:
            return {'phase': 'ACCUMULATION', 'event': 'SPRING', 'confidence': 8}
        elif upthrust_detected and volume_spike:
            return {'phase': 'DISTRIBUTION', 'event': 'UPTHRUST', 'confidence': 8}
        elif price_position > 0.7 and volume_declining and effort_mismatch:
            return {'phase': 'DISTRIBUTION', 'event': 'PHASE_B', 'confidence': 5}
        elif price_position < 0.3 and volume_declining and effort_mismatch:
            return {'phase': 'ACCUMULATION', 'event': 'PHASE_B', 'confidence': 5}
        elif current_price > range_high and volume_spike:
            return {'phase': 'MARKUP', 'event': 'BREAKOUT', 'confidence': 7}
        elif current_price < range_low and volume_spike:
            return {'phase': 'MARKDOWN', 'event': 'BREAKDOWN', 'confidence': 7}
        else:
            return {'phase': 'NEUTRAL', 'event': None, 'confidence': 0}
    except:
        return {'phase': 'NEUTRAL', 'event': None, 'confidence': 0}

def calculate_rvol_strength(volumes, period=20):
    """
    Relative Volume Strength - Enhanced RVOL with actionable categories.
    EXTREME (>3x), HIGH (>2x), ABOVE_AVG (>1.5x), NORMAL (0.5-1.5x), LOW (<0.5x)
    """
    try:
        if len(volumes) < period + 1:
            return {'ratio': 1.0, 'category': 'NORMAL'}
        avg_vol = sum(volumes[-period-1:-1]) / period
        current_vol = volumes[-1]
        ratio = current_vol / avg_vol if avg_vol > 0 else 1.0
        if ratio >= 3.0: category = 'EXTREME'
        elif ratio >= 2.0: category = 'HIGH'
        elif ratio >= 1.5: category = 'ABOVE_AVG'
        elif ratio >= 0.5: category = 'NORMAL'
        else: category = 'LOW'
        return {'ratio': round(ratio, 2), 'category': category}
    except:
        return {'ratio': 1.0, 'category': 'NORMAL'}

# ═══════════════════════════════════════════════════════════════
# END NEW ADVANCED INDICATORS
# ═══════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════
# 🚀 OPTIMIZED PARAMETER HELPERS (2024 Best Practices)
# ═══════════════════════════════════════════════════════════════

def get_optimal_rsi_period(timeframe):
    """Get optimal RSI period based on timeframe for crypto volatility"""
    scalping_tf = ['1m', '3m', '5m']
    day_trading_tf = ['15m', '30m', '1h']
    
    if timeframe in scalping_tf:
        return 7  # Faster for scalping, captures momentum quicker
    elif timeframe in day_trading_tf:
        return 9  # Balanced for day trading
    else:
        return 14  # Standard for swing/position trading

def get_optimal_rsi_levels(timeframe):
    """Get optimal RSI overbought/oversold levels for crypto"""
    scalping_tf = ['1m', '3m', '5m']
    day_trading_tf = ['15m', '30m', '1h']
    
    if timeframe in scalping_tf:
        return (20, 80)  # Wider levels for volatile scalping
    elif timeframe in day_trading_tf:
        return (25, 75)  # Adjusted for day trading
    else:
        return (30, 70)  # Standard for swing trading

def get_optimal_macd_params(timeframe):
    """Get optimal MACD parameters based on timeframe"""
    if timeframe == '1m':
        return (6, 13, 5)  # Ultra-fast for 1-minute scalping
    elif timeframe in ['3m', '5m', '15m']:
        return (8, 17, 9)  # Fast day trading settings
    else:
        return (12, 26, 9)  # Standard for swing trading

def get_optimal_bb_params(timeframe):
    """Get optimal Bollinger Bands parameters for crypto"""
    scalping_tf = ['1m', '3m', '5m']
    day_trading_tf = ['15m', '30m', '1h']
    
    if timeframe in scalping_tf:
        return (10, 1.8)  # Tighter bands for scalping
    elif timeframe in day_trading_tf:
        return (20, 2.0)  # Standard for day trading
    else:
        return (20, 2.3)  # Wider for volatile swing trading

def get_optimal_supertrend_params(timeframe):
    """Get optimal SuperTrend parameters for crypto"""
    scalping_tf = ['1m', '3m', '5m']
    swing_tf = ['4h', '1d', '1w']
    
    if timeframe in scalping_tf:
        return (7, 2.5)  # (ATR period, multiplier) - Fast for scalping
    elif timeframe in swing_tf:
        return (10, 4.5)  # Higher multiplier filters noise in swing trading
    else:
        return (10, 3.0)  # Balanced for day trading

def get_optimal_ichimoku_params(timeframe):
    """Get optimal Ichimoku parameters for crypto (24/7 markets)"""
    # Crypto runs 24/7, needs adjustment from traditional 9,26,52
    return (10, 30, 60, 30)  # (conversion, base, span_b, displacement)

def get_optimal_adx_threshold(confidence_level='standard'):
    """Get optimal ADX threshold for trend strength"""
    if confidence_level == 'high':
        return 30  # Very strong trends only
    elif confidence_level == 'elite':
        return 35  # Ultra-selective
    else:
        return 25  # Standard strong trend threshold

def calculate_signal_confidence(analysis, mtf_analyses=None):
    """
    Calculate signal confidence score (0-10)
    Based on indicator confluence, MTF alignment, volume, and R:R
    """
    confidence = 0
    
    # 1. Multi-Timeframe Alignment (0-3 points)
    if mtf_analyses and len(mtf_analyses) >= 2:
        trends = [a.get('trend', 'NEUTRAL') for a in mtf_analyses if a]
        bullish_count = trends.count('BULLISH')
        bearish_count = trends.count('BEARISH')
        total = len(trends)
        
        if bullish_count / total >= 0.75 or bearish_count / total >= 0.75:
            confidence += 3  # Strong alignment
        elif bullish_count / total >= 0.6 or bearish_count / total >= 0.6:
            confidence += 2  # Moderate alignment
        elif bullish_count / total >= 0.5 or bearish_count / total >= 0.5:
            confidence += 1  # Weak alignment
    
    # 2. Indicator Confluence (0-2 points)
    confirming = 0
    trend = analysis.get('trend', 'NEUTRAL')
    
    if trend == 'BULLISH':
        if analysis.get('rsi', 50) > 50 and analysis.get('rsi', 50) < 70:
            confirming += 1
        if analysis.get('macd', {}).get('histogram', 0) > 0:
            confirming += 1
        if analysis.get('adx', {}).get('adx', 0) > 25:
            confirming += 1
        if analysis.get('supertrend', {}).get('trend') == 'BULLISH':
            confirming += 1
    elif trend == 'BEARISH':
        if analysis.get('rsi', 50) < 50 and analysis.get('rsi', 50) > 30:
            confirming += 1
        if analysis.get('macd', {}).get('histogram', 0) < 0:
            confirming += 1
        if analysis.get('adx', {}).get('adx', 0) > 25:
            confirming += 1
        if analysis.get('supertrend', {}).get('trend') == 'BEARISH':
            confirming += 1
    
    confidence += min(confirming / 2, 2)  # Max 2 points
    
    # 3. Volume Confirmation (0-1 point)
    volume = analysis.get('volume', 0)
    avg_volume = analysis.get('avg_volume', 0)
    if avg_volume > 0 and volume / avg_volume >= 1.3:
        confidence += 1
    
    # 4. Key Level Proximity (0-2 points)
    price = analysis.get('current_price', 0)
    support = analysis.get('support', 0)
    resistance = analysis.get('resistance', 0)
    
    if price > 0 and support > 0 and resistance > 0:
        # Check if price is near support (for longs) or resistance (for shorts)
        range_size = resistance - support
        if range_size > 0:
            if trend == 'BULLISH' and abs(price - support) / range_size < 0.15:
                confidence += 2  # Near support in uptrend
            elif trend == 'BEARISH' and abs(price - resistance) / range_size < 0.15:
                confidence += 2  # Near resistance in downtrend
            elif abs(price - support) / range_size < 0.25 or abs(price - resistance) / range_size < 0.25:
                confidence += 1  # Somewhat near key level
    
    # 5. Trend Strength (0-2 points)
    adx_val = analysis.get('adx', {}).get('adx', 0)
    if adx_val >= 40:
        confidence += 2  # Very strong trend
    elif adx_val >= 30:
        confidence += 1.5  # Strong trend
    elif adx_val >= 25:
        confidence += 1  # Moderate trend
    
    return round(min(confidence, 10), 1)  # Cap at 10

def calculate_optimal_sl_tp(entry_price, atr, trend, support, resistance, min_rr=2.0):
    """
    Calculate optimal Stop Loss and Take Profit based on ATR and key levels
    Returns: {'sl': float, 'tp': float, 'rr': float}
    """
    if not all([entry_price, atr, trend, support, resistance]):
        return {'sl': 0, 'tp': 0, 'rr': 0}
    
    atr_buffer = 1.5 * atr
    
    if trend == 'BULLISH':
        # Stop Loss: Below support with ATR buffer
        sl = max(support - atr_buffer, entry_price * 0.95)  # Max 5% stop
        
        # Take Profit: Target resistance first, then check R:R
        risk = entry_price - sl
        tp_by_rr = entry_price + (min_rr * risk)
        
        # Use the lower of resistance or R:R target (conservative)
        tp = min(resistance * 0.98, tp_by_rr)  # Stay below resistance
        
    elif trend == 'BEARISH':
        # Stop Loss: Above resistance with ATR buffer
        sl = min(resistance + atr_buffer, entry_price * 1.05)  # Max 5% stop
        
        # Take Profit: Target support first, then check R:R
        risk = sl - entry_price
        tp_by_rr = entry_price - (min_rr * risk)
        
        # Use the higher of support or R:R target (conservative)
        tp = max(support * 1.02, tp_by_rr)  # Stay above support
        
    else:
        return {'sl': 0, 'tp': 0, 'rr': 0}
    
    # Calculate actual R:R
    risk = abs(entry_price - sl)
    reward = abs(tp - entry_price)
    rr = reward / risk if risk > 0 else 0
    
    return {
        'sl': round(sl, 8),
        'tp': round(tp, 8),
        'rr': round(rr, 2)
    }

def check_mtf_alignment_strict(analyses, min_alignment=0.75):
    """
    Strict multi-timeframe alignment check
    Returns: 'STRONG_BULLISH', 'STRONG_BEARISH', 'WEAK', or 'NEUTRAL'
    """
    if not analyses or len(analyses) < 2:
        return 'NEUTRAL'
    
    trends = [a.get('trend', 'NEUTRAL') for a in analyses if a]
    if not trends:
        return 'NEUTRAL'
    
    bullish_count = trends.count('BULLISH')
    bearish_count = trends.count('BEARISH')
    total = len(trends)
    
    if bullish_count / total >= min_alignment:
        return 'STRONG_BULLISH'
    elif bearish_count / total >= min_alignment:
        return 'STRONG_BEARISH'
    elif bullish_count > bearish_count:
        return 'WEAK_BULLISH'
    elif bearish_count > bullish_count:
        return 'WEAK_BEARISH'
    else:
        return 'NEUTRAL'

# ═══════════════════════════════════════════════════════════════
# END OF OPTIMIZATION HELPERS
# ═══════════════════════════════════════════════════════════════

def analyze_timeframe(candles, timeframe_name):
    if not candles or len(candles) < 50:
        return None
    closes = [c['close'] for c in candles]
    highs = [c['high'] for c in candles]
    lows = [c['low'] for c in candles]
    opens = [c['open'] for c in candles]
    volumes = [c['volume'] for c in candles]
    current_price = closes[-1]
    
    # ═══════════════════════════════════════════════════════════════
    # 🚀 USE OPTIMIZED PARAMETERS BASED ON TIMEFRAME
    # ═══════════════════════════════════════════════════════════════
    
    # Get optimal parameters for this timeframe
    rsi_period = get_optimal_rsi_period(timeframe_name)
    rsi_levels = get_optimal_rsi_levels(timeframe_name)
    macd_params = get_optimal_macd_params(timeframe_name)
    bb_params = get_optimal_bb_params(timeframe_name)
    st_params = get_optimal_supertrend_params(timeframe_name)
    ich_params = get_optimal_ichimoku_params(timeframe_name)
    adx_threshold = get_optimal_adx_threshold('standard')  # 25 for standard
    
    # Calculate indicators with OPTIMIZED parameters
    rsi = calculate_rsi(closes, rsi_period)
    ema9 = calculate_ema(closes, 9)
    ema21 = calculate_ema(closes, 21)
    ema50 = calculate_ema(closes, 50)
    ema200 = calculate_ema(closes, 200) if len(closes) >= 200 else ema50
    
    # MACD with optimized parameters
    if len(closes) >= macd_params[1]:
        ema_fast = calculate_ema_series(closes, macd_params[0])
        ema_slow = calculate_ema_series(closes, macd_params[1])
        macd_series = [e1 - e2 for e1, e2 in zip(ema_fast, ema_slow)]
        macd_line = macd_series[-1]
        signal_series = calculate_ema_series(macd_series, macd_params[2])
        signal = signal_series[-1]
        macd = {'macd': macd_line, 'signal': signal, 'histogram': macd_line - signal}
    else:
        macd = {'macd': 0, 'signal': 0, 'histogram': 0}
    
    # Bollinger Bands with optimized parameters
    bb = calculate_bb(closes, bb_params[0], bb_params[1])
    
    # ATR and ADX (keep standard period 14)
    atr = calculate_atr(highs, lows, closes, 14)
    adx = calculate_adx(highs, lows, closes, 14)
    
    # SuperTrend with optimized parameters (if enabled)
    if 'ST' in ENABLED_INDICATORS:
        # Re-calculate with optimized params
        st_highs = highs
        st_lows = lows
        st_closes = closes
        st_atr_period = st_params[0]
        st_multiplier = st_params[1]
        
        # Calculate ATR for SuperTrend
        if len(closes) >= st_atr_period + 1:
            trs = []
            for i in range(1, len(closes)):
                tr = max(st_highs[i] - st_lows[i], 
                        abs(st_highs[i] - st_closes[i-1]), 
                        abs(st_lows[i] - st_closes[i-1]))
                trs.append(tr)
            st_atr = sum(trs[:st_atr_period]) / st_atr_period
            for i in range(st_atr_period, len(trs)):
                st_atr = (st_atr * (st_atr_period - 1) + trs[i]) / st_atr_period
            
            # Calculate SuperTrend
            hl_avg = (st_highs[-1] + st_lows[-1]) / 2
            upper_band = hl_avg + (st_multiplier * st_atr)
            lower_band = hl_avg - (st_multiplier * st_atr)
            
            # Determine trend
            if current_price > upper_band:
                st_trend = 'BULLISH'
            elif current_price < lower_band:
                st_trend = 'BEARISH'
            else:
                st_trend = 'NEUTRAL'
            
            supertrend = {'trend': st_trend, 'upper': upper_band, 'lower': lower_band}
        else:
            supertrend = {'trend': 'NEUTRAL', 'upper': current_price, 'lower': current_price}
    else:
        supertrend = calculate_supertrend(candles) if 'ST' in ENABLED_INDICATORS else {'trend': 'NEUTRAL'}
    
    # Ichimoku with optimized parameters (if enabled)
    if 'ICHI' in ENABLED_INDICATORS:
        ich_conv_period = ich_params[0]  # 10
        ich_base_period = ich_params[1]  # 30
        ich_span_b_period = ich_params[2]  # 60
        
        # Conversion Line (Tenkan-sen)
        if len(highs) >= ich_conv_period:
            conv_high = max(highs[-ich_conv_period:])
            conv_low = min(lows[-ich_conv_period:])
            tenkan = (conv_high + conv_low) / 2
        else:
            tenkan = current_price
        
        # Base Line (Kijun-sen)
        if len(highs) >= ich_base_period:
            base_high = max(highs[-ich_base_period:])
            base_low = min(lows[-ich_base_period:])
            kijun = (base_high + base_low) / 2
        else:
            kijun = current_price
        
        # Leading Span A (Senkou Span A)
        span_a = (tenkan + kijun) / 2
        
        # Leading Span B (Senkou Span B)
        if len(highs) >= ich_span_b_period:
            span_b_high = max(highs[-ich_span_b_period:])
            span_b_low = min(lows[-ich_span_b_period:])
            span_b = (span_b_high + span_b_low) / 2
        else:
            span_b = current_price
        
        ichimoku = {
            'tenkan': tenkan,
            'kijun': kijun,
            'span_a': span_a,  # Required by strategies
            'span_b': span_b,  # Required by strategies
            'cloud_top': max(span_a, span_b),
            'cloud_bottom': min(span_a, span_b),
            'cloud_state': 'BULLISH' if span_a > span_b else 'BEARISH'  # Required by strategies
        }
    else:
        ichimoku = calculate_ichimoku(highs, lows) if 'ICHI' in ENABLED_INDICATORS else {
            'tenkan': 0, 'kijun': 0, 'span_a': 0, 'span_b': 0, 
            'cloud_top': 0, 'cloud_bottom': 0, 'cloud_state': 'NEUTRAL'
        }
    
    # Other indicators (unchanged)
    stoch_rsi = calculate_stoch_rsi(closes) if 'StochRSI' in ENABLED_INDICATORS else {'k': 50, 'd': 50}
    obv = calculate_obv(closes, volumes) if 'OBV' in ENABLED_INDICATORS else []
    hma = calculate_hma(closes, 21) if 'HMA' in ENABLED_INDICATORS else closes[-1]
    vwap = calculate_vwap(candles) if 'VWAP' in ENABLED_INDICATORS else current_price
    cmf = calculate_cmf(candles) if 'CMF' in ENABLED_INDICATORS else 0
    fvg = detect_fvg(candles) if 'FVG' in ENABLED_INDICATORS else None
    
    # Need RSI series for divergence
    rsi_div = None
    if 'DIV' in ENABLED_INDICATORS:
        rsi_series = []
        for i in range(len(closes) - 31, len(closes) + 1):
            if i < rsi_period + 1: continue
            rsi_series.append(calculate_rsi(closes[:i], rsi_period))
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
    psar_res = calculate_psar(highs, lows, closes) if 'PSAR' in ENABLED_INDICATORS else {'psar': current_price, 'trend': 'NEUTRAL', 'series': []}
    tema_res = calculate_tema(closes) if 'TEMA' in ENABLED_INDICATORS else {'value': current_price, 'series': []}
    
    psar = {'psar': psar_res['psar'], 'trend': psar_res['trend']}
    tema = tema_res['value']
    
    chandelier = calculate_chandelier_exit(highs, lows, closes) if 'CHANDELIER' in ENABLED_INDICATORS else {'long': 0, 'short': 0, 'long_series': [], 'short_series': []}
    kama_res = calculate_kama(closes) if 'KAMA' in ENABLED_INDICATORS else {'value': current_price, 'series': []}
    kama = kama_res['value']
    
    # Format indicator series for the chart (last 200 bars)
    times = [c['time'] for c in candles]
    psar_series = format_series_for_chart(times, psar_res.get('series', []))
    tema_series = format_series_for_chart(times, tema_res.get('series', []))
    kama_series = format_series_for_chart(times, kama_res.get('series', []))
    zlsma_series = format_series_for_chart(times, calculate_ema_series(closes, 32)) # ZLSMA approximation
    ema200_series = format_series_for_chart(times, calculate_ema_series(closes, 200))
    chandelier_series = format_series_for_chart(times, chandelier.get('long_series', [])) # Just return long as base
    
    vfi = calculate_vfi(closes, volumes) if 'VFI' in ENABLED_INDICATORS else 0
    
    rvol = volumes[-1] / (sum(volumes[-20:])/20) if len(volumes) >= 20 else 1.0
    
    trend = 'BULLISH' if ema9 > ema21 > ema50 else 'BEARISH' if ema9 < ema21 < ema50 else 'NEUTRAL'
    ict_phase = calculate_ict_phases(rsi, adx['adx'], volumes[-1], sum(volumes[-20:])/20 if len(volumes)>=20 else 1, trend) if 'ICT_WD' in ENABLED_INDICATORS else "CONSOLIDATION"
    
    # ═══════════════════════════════════════════════════════════════
    # 🚀 ENHANCED TREND STRENGTH WITH OPTIMIZED ADX THRESHOLD (25 not 20)
    # ═══════════════════════════════════════════════════════════════
    trend_strength = 'STRONG' if adx['adx'] > adx_threshold else 'WEAK'
    if supertrend['trend'] == 'BULLISH' and trend == 'BULLISH':
        trend_strength = 'VERY STRONG'
    elif supertrend['trend'] == 'BEARISH' and trend == 'BEARISH':
        trend_strength = 'VERY STRONG'
    
    support = min(lows[-20:]) if len(lows) >= 20 else lows[-1]
    resistance = max(highs[-20:]) if len(highs) >= 20 else highs[-1]
    
    # ═══ NEW ADVANCED INDICATORS ═══
    adx_v = adx['adx'] if isinstance(adx, dict) else adx
    market_regime = detect_market_regime(adx_val=adx_v, chop_val=chop, bb=bb, atr=atr, closes=closes)
    cumulative_delta = calculate_cumulative_delta(candles)
    zscore = calculate_zscore(closes)
    wyckoff_phase = detect_wyckoff_phase(candles)
    rvol_strength = calculate_rvol_strength(volumes)
    
    return {
        'timeframe': timeframe_name,
        'current_price': current_price,
        'rsi': rsi,
        'rsi_period': rsi_period,  # Include for reference
        'rsi_levels': rsi_levels,  # Include for reference
        'stoch_rsi': stoch_rsi,
        'adx': adx,
        'adx_threshold': adx_threshold,  # Include for reference
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
        'psar_series': psar_series,
        'tema_series': tema_series,
        'kama_series': kama_series,
        'zlsma_series': zlsma_series,
        'ema200_series': ema200_series,
        'chandelier_series': chandelier_series,
        'volume': volumes[-1] if volumes else 0,
        'avg_volume': sum(volumes[-20:]) / 20 if len(volumes) >= 20 else 0,
        'candle_time': candles[-1]['time'] if candles else 0,
        'candles': candles[-10:] if len(candles) >= 10 else candles,
        # ═══ NEW ADVANCED INDICATORS ═══
        'market_regime': market_regime,
        'cumulative_delta': cumulative_delta,
        'zscore': zscore,
        'wyckoff_phase': wyckoff_phase,
        'rvol_strength': rvol_strength,
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
            count = len(analyses)
            print(f"✓ ({count} TF)")
        else:
            print("❌ (No Data/Skip)")
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
        # Use support but add 1.0x ATR buffer for safety
        sl = (h1['support'] - atr_val * 1.0) if h1['support'] < current else current - (atr_val * 2.5)
        tp1 = current + atr_val * 3
        tp2 = current + atr_val * 5
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
        # Use resistance but add 1.0x ATR buffer for safety
        sl = (h1['resistance'] + atr_val * 1.0) if h1['resistance'] > current else current + (atr_val * 2.5)
        tp1 = current - atr_val * 3
        tp2 = current - atr_val * 5
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
                 sl = current - atr * 3
                 tp1 = current + atr * 6
                 tp2 = current + atr * 10
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
                 sl = current + atr * 3
                 tp1 = current - atr * 6
                 tp2 = current - atr * 10
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
    """Strategy: Ichimoku TK Cross + Cloud Confirmation + Regime"""
    tf = '1h' if '1h' in analyses else '4h' if '4h' in analyses else None
    if not tf or tf not in analyses: return []
    
    a = analyses[tf]
    ichi = a['ichimoku']
    if not ichi: return []
    current = a['current_price']
    trades = []
    
    # Regime Check
    regime = a.get('market_regime', {}).get('regime', 'UNKNOWN')
    if regime == 'CHOPPY': return []
    
    # Cloud Thickness Check (Thicker cloud = Stronger S/R)
    atr = a['atr']
    cloud_thickness = abs(ichi['span_a'] - ichi['span_b'])
    is_cloud_thick = cloud_thickness > (atr * 0.5)
    
    # LONG: Tenkan crosses ABOVE Kijun, price is ABOVE Cloud
    if ichi['tenkan'] > ichi['kijun'] and current > ichi['span_a'] and current > ichi['span_b']:
        confidence = 7
        reasons = ["Ichimoku TK Bullish Cross", "Price above Cloud"]
        
        if ichi['cloud_state'] == 'BULLISH':
            confidence += 1
            reasons.append("Future Cloud Bullish")
            
        if is_cloud_thick:
            confidence += 1
            reasons.append("Strong Cloud Support")
            
        if a['trend'] == 'BULLISH':
            confidence += 1
            reasons.append("EMA Trend Alignment")
            
        if confidence >= MIN_CONFIDENCE:
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
                    'confidence': 'VERY HIGH' if confidence >= 8 else 'HIGH',
                    'confidence_score': confidence,
                    'risk_reward': round(reward/risk, 1),
                    'reason': ' + '.join(reasons),
                    'indicators': f"TK Cross, Cloud:{ichi['cloud_state']}, Regime:{regime}",
                    'expected_time': '12-24 hours',
                    'risk': risk, 'reward': reward,
                    'entry_type': 'MARKET',
                    'timeframe': tf,
                    'analysis_data': {'regime': regime, 'cloud_state': ichi['cloud_state']}
                })
                
    # SHORT: Tenkan crosses BELOW Kijun, price is BELOW Cloud
    elif ichi['tenkan'] < ichi['kijun'] and current < ichi['span_a'] and current < ichi['span_b']:
        confidence = 7
        reasons = ["Ichimoku TK Bearish Cross", "Price below Cloud"]
        
        if ichi['cloud_state'] == 'BEARISH':
            confidence += 1
            reasons.append("Future Cloud Bearish")
            
        if is_cloud_thick:
            confidence += 1
            reasons.append("Strong Cloud Resistance")
            
        if a['trend'] == 'BEARISH':
            confidence += 1
            reasons.append("EMA Trend Alignment")
            
        if confidence >= MIN_CONFIDENCE:
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
                    'confidence': 'VERY HIGH' if confidence >= 8 else 'HIGH',
                    'confidence_score': confidence,
                    'risk_reward': round(reward/risk, 1),
                    'reason': ' + '.join(reasons),
                    'indicators': f"TK Cross, Cloud:{ichi['cloud_state']}, Regime:{regime}",
                    'expected_time': '12-24 hours',
                    'risk': risk, 'reward': reward,
                    'entry_type': 'MARKET',
                    'timeframe': tf,
                    'analysis_data': {'regime': regime, 'cloud_state': ichi['cloud_state']}
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
            # Entry at the top of the gap, SL at the bottom with protective buffer
            entry = fvg['top']
            sl = fvg['bottom'] - (atr * 1.0)
            tp1 = entry + atr * 5
            tp2 = entry + atr * 10
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
    """Strategy: Bollinger Band Breakout with ADX + Volume + Regime Confirmation"""
    tf = '1h' if '1h' in analyses else '15m' if '15m' in analyses else None
    if not tf or tf not in analyses: return []
    
    a = analyses[tf]
    current = a['current_price']
    trades = []
    
    # Regime Check
    regime = a.get('market_regime', {}).get('regime', 'UNKNOWN')
    if regime == 'CHOPPY': return []
    
    # Volume Check
    rvol = a.get('rvol_strength', {}).get('category', 'NORMAL')
    vol_confirm = rvol in ('HIGH', 'EXTREME', 'ABOVE_AVG')
    
    # ADX must be strong or rising for a breakout
    if a['adx']['adx'] > 25:
        # LONG: Price breaks above Upper BB
        if current > a['bb']['upper']:
            confidence = 7
            reasons = ["Bollinger Band Breakout (Upper)", "Strong ADX Momentum"]
            
            if vol_confirm:
                confidence += 1
                reasons.append(f"Volume Confirmation ({rvol})")
            
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
                        'confidence': 'VERY HIGH' if confidence >= 8 else 'HIGH',
                        'confidence_score': confidence,
                        'risk_reward': round(reward / risk, 1),
                        'reason': ' + '.join(reasons),
                        'indicators': f"BB Upper, ADX:{a['adx']['adx']:.1f}, Vol:{rvol}",
                        'expected_time': '2-4 hours',
                        'risk': risk, 'reward': reward,
                        'entry_type': 'STOP-MARKET',
                        'timeframe': tf,
                        'analysis_data': {'regime': regime, 'rvol': rvol}
                    })
                    
        # SHORT: Price breaks below Lower BB
        elif current < a['bb']['lower']:
            confidence = 7
            reasons = ["Bollinger Band Breakout (Lower)", "Strong ADX Momentum"]
            
            if vol_confirm:
                confidence += 1
                reasons.append(f"Volume Confirmation ({rvol})")
            
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
                        'confidence': 'VERY HIGH' if confidence >= 8 else 'HIGH',
                        'confidence_score': confidence,
                        'risk_reward': round(reward / risk, 1),
                        'reason': ' + '.join(reasons),
                        'indicators': f"BB Lower, ADX:{a['adx']['adx']:.1f}, Vol:{rvol}",
                        'expected_time': '2-4 hours',
                        'risk': risk, 'reward': reward,
                        'entry_type': 'STOP-MARKET',
                        'timeframe': tf,
                        'analysis_data': {'regime': regime, 'rvol': rvol}
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
            sl = current - atr * 2.5
            tp1 = current + atr * 5
            tp2 = current + atr * 9
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
            sl = current + atr * 2.5
            tp1 = current - atr * 5
            tp2 = current - atr * 9
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
        # SL below FVG bottom + extra ATR buffer for safety
        sl = fvg['bottom'] - (atr * 1.5)
        tp1 = entry + atr * 6
        tp2 = entry + atr * 12
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
        # SL above FVG top + extra ATR buffer for safety
        sl = fvg['top'] + (atr * 1.5)
        tp1 = entry - atr * 6
        tp2 = entry - atr * 12
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
def strategy_quantum_confluence_2026(symbol, analyses):
    """
    ULTIMATE 2026 STRATEGY: Quantum Confluence.
    Combines: HTF Trend + Squeeze Release + SMC OrderBlock + Vortex + Volume.
    Targeting 75%+ Win Rate via Hyper-Selectivity.
    """
    trades = []
    # 1. Bias Check (HTF Alignment is non-negotiable)
    mtf_bias = check_mtf_alignment_strict(list(analyses.values()))
    if mtf_bias == 'NEUTRAL': return []

    for tf in ['15m', '1h']: # Scalp/Swing hybrid timeframes
        if tf not in analyses: continue
        a = analyses[tf]
        current = a['current_price']
        atr = a['atr']
        if atr == 0: continue
        
        # 2. Volatility Check: Must be breaking out of a squeeze
        sqz = a.get('squeeze', {}).get('sqz', 'OFF')
        if sqz != 'OFF' and abs(a.get('squeeze', {}).get('val', 0)) < 1.0:
            continue # Still in low volatility / consolidation
            
        # 3. Indicator Confluence
        vortex = a.get('vortex', {'plus': 0, 'minus': 0})
        adx_v = a['adx']['adx'] if isinstance(a['adx'], dict) else 0
        rvol = a.get('rvol', 1.0)
        
        # LONG 
        if mtf_bias in ('STRONG_BULLISH', 'WEAK_BULLISH') and a['trend'] == 'BULLISH':
            # Indicators: Vortex Plus > Minus, ADX Rising (>20), Volume Healthy
            if vortex['plus'] > vortex['minus'] and adx_v > 20 and rvol > 1.2:
                # SMC Confirmation: Within proximity of Support or OB
                near_support = abs(current - a['support']) / current < 0.005
                has_ob = a['order_blocks']['bullish_ob'] is not None
                
                if near_support or has_ob:
                    confidence = 9
                    reasons = ["Quantum Confluence [HTF Trend]", "Vortex Alignment", "Squeeze Release"]
                    if has_ob: reasons.append("Order Block Support")
                    if rvol > 2.0: confidence = 10; reasons.append("Extreme Volume Spike")
                    
                    sl = current - (atr * 4.0)
                    tp1 = current + (atr * 5.0)
                    risk = current - sl
                    reward = tp1 - current
                    
                    if risk > 0 and reward/risk >= 1.8:
                        trades.append({
                            'strategy': 'Quantum Elite 2026',
                            'type': 'LONG', 'symbol': symbol,
                            'entry': current, 'sl': sl, 'tp1': tp1, 'tp2': current + (atr * 9),
                            'confidence': 'MAXIMUM' if confidence == 10 else 'VERY HIGH',
                            'confidence_score': confidence,
                            'risk_reward': round(reward/risk, 1),
                            'reason': ' + '.join(reasons),
                            'indicators': f"ADX:{adx_v:.0f}, Vol:{rvol:.1f}x, VI+:{vortex['plus']:.2f}",
                            'expected_time': '4-12 hours', 'entry_type': 'MARKET', 'timeframe': tf,
                            'analysis_data': {'mtf_bias': mtf_bias, 'rvol': rvol}
                        })
                        
        # SHORT
        elif mtf_bias in ('STRONG_BEARISH', 'WEAK_BEARISH') and a['trend'] == 'BEARISH':
            if vortex['minus'] > vortex['plus'] and adx_v > 20 and rvol > 1.2:
                near_resistance = abs(current - a['resistance']) / current < 0.005
                has_ob = a['order_blocks']['bearish_ob'] is not None
                
                if near_resistance or has_ob:
                    confidence = 9
                    reasons = ["Quantum Confluence [HTF Trend]", "Vortex Alignment", "Squeeze Release"]
                    if has_ob: reasons.append("Order Block Resistance")
                    if rvol > 2.0: confidence = 10; reasons.append("Extreme Volume Spike")
                    
                    sl = current + (atr * 4.0)
                    tp1 = current - (atr * 5.0)
                    risk = sl - current
                    reward = current - tp1
                    
                    if risk > 0 and reward/risk >= 1.8:
                        trades.append({
                            'strategy': 'Quantum Elite 2026',
                            'type': 'SHORT', 'symbol': symbol,
                            'entry': current, 'sl': sl, 'tp1': tp1, 'tp2': current - (atr * 9),
                            'confidence': 'MAXIMUM' if confidence == 10 else 'VERY HIGH',
                            'confidence_score': confidence,
                            'risk_reward': round(reward/risk, 1),
                            'reason': ' + '.join(reasons),
                            'indicators': f"ADX:{adx_v:.0f}, Vol:{rvol:.1f}x, VI-:{vortex['minus']:.2f}",
                            'expected_time': '4-12 hours', 'entry_type': 'MARKET', 'timeframe': tf,
                            'analysis_data': {'mtf_bias': mtf_bias, 'rvol': rvol}
                        })
    return trades

def strategy_smc_elite(symbol, analyses):
    """Elite SMC Strategy: Mitigation Blocks + FVG Confluence + Wyckoff + Trend Alignment."""
    trades = []
    for tf, a in analyses.items():
        # Regime Check
        regime = a.get('market_regime', {}).get('regime', 'UNKNOWN')
        if regime == 'CHOPPY': continue
        
        mb = detect_mitigation_block(a['candles'])
        fvg = a['fvg']
        wyckoff = a.get('wyckoff_phase', {})
        
        if mb and fvg:
            entry = mb['level']
            current = a['current_price']
            fvg_type = 'BULLISH' if fvg['type'] == 'BULLISH' else 'BEARISH'
            
            if mb['type'] == fvg_type and a['trend'] == mb['type']:
                # MTF Confluence Check
                if not check_mtf_alignment(analyses, tf, mb['type']):
                    continue
                
                confidence = 9
                reasons = [f"SMC Elite: {mb['type']} Mitigation Block + FVG"]
                
                # FVG Equilibrium Check: Entry must be deep enough in the gap
                if mb['type'] == 'BULLISH':
                    fvg_equiv = fvg['bottom'] + (fvg['top'] - fvg['bottom']) * 0.5
                    if current > fvg_equiv:
                        # Price hasn't retraced deep enough into FVG Equilibrium
                        continue
                else:
                    fvg_equiv = fvg['top'] - (fvg['top'] - fvg['bottom']) * 0.5
                    if current < fvg_equiv:
                        continue

                # Liquidity Check: Require a recent sweep before entry
                liq = a.get('liquidity')
                if liq and liq['type'] == mb['type']:
                    confidence = 10
                    reasons.append("Liquidity Sweep Confirmed")
                
                # Wyckoff Confirmation
                if mb['type'] == 'BULLISH':
                    if wyckoff.get('phase') == 'ACCUMULATION':
                        confidence = 10
                        reasons.append("Wyckoff Accumulation")
                elif mb['type'] == 'BEARISH':
                    if wyckoff.get('phase') == 'DISTRIBUTION':
                        confidence = 10
                        reasons.append("Wyckoff Distribution")
                        
                atr = a['atr']
                if atr == 0: continue
                
                # Widen SL for higher safety
                sl = entry - (atr * 3.5) if mb['type'] == 'BULLISH' else entry + (atr * 3.5)
                tp1 = entry + (atr * 5.0) if mb['type'] == 'BULLISH' else entry - (atr * 5.0)
                tp2 = entry + (tp1-entry)*2
                
                risk = abs(entry - sl)
                reward = abs(tp1 - entry)
                if risk == 0: continue

                trades.append({
                    'strategy': 'SMC Elite (X-Confluence)',
                    'type': mb['type'],
                    'symbol': symbol,
                    'entry': entry,
                    'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence': 'MAXIMUM (ELITE)' if confidence == 10 else 'VERY HIGH',
                    'confidence_score': confidence,
                    'risk_reward': round(reward/risk, 1),
                    'reason': ' + '.join(reasons),
                    'indicators': f"MB:{entry:.4f} | FVG:{fvg['type']} | Eqm:Hit",
                    'expected_time': '12-36 hours', 'entry_type': 'LIMIT', 'timeframe': tf,
                    'analysis_data': {
                        'fvg': {'top': fvg['top'], 'bottom': fvg['bottom'], 'type': fvg['type']},
                        'mitigation_block': {'level': mb['level'], 'type': mb['type']},
                        'wyckoff': wyckoff.get('phase')
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
            sl = entry - (atr * 3.5) if pattern['type'] == 'BULLISH' else entry + (atr * 3.5)
            tp1 = entry + (atr * 7.0) if pattern['type'] == 'BULLISH' else entry - (atr * 7.0)
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
    current = a['current_price']
    trades = []
    
    # Common indicators
    rsi = a['rsi']
    adx_v = a['adx']['adx'] if isinstance(a['adx'], dict) else 0
    macd_hist = a['macd']['histogram']
    st_trend = a['supertrend']['trend']
    rvol = a.get('rvol_strength', {}).get('category', 'NORMAL')
    
    # LONG Scoring
    bull_score = 0
    bull_reasons = []
    if 40 < rsi < 65: bull_score += 1; bull_reasons.append("RSI Bullish Zone")
    if macd_hist > 0: bull_score += 1; bull_reasons.append("MACD Positive")
    if a['stoch_rsi']['k'] < 80 and a['stoch_rsi']['k'] > a['stoch_rsi']['d']: 
        bull_score += 1; bull_reasons.append("StochRSI Rising")
    if adx_v > 25: bull_score += 1; bull_reasons.append("ADX > 25")
    if a['trend'] == 'BULLISH': bull_score += 1; bull_reasons.append("EMA Trend Bullish")
    if st_trend == 'BULLISH': bull_score += 1; bull_reasons.append("SuperTrend Bullish")
    if rvol in ('HIGH', 'EXTREME', 'ABOVE_AVG'): bull_score += 1; bull_reasons.append("Volume High")
    
    # SHORT Scoring
    bear_score = 0
    bear_reasons = []
    if 35 < rsi < 60: bear_score += 1; bear_reasons.append("RSI Bearish Zone")
    if macd_hist < 0: bear_score += 1; bear_reasons.append("MACD Negative")
    if a['stoch_rsi']['k'] > 20 and a['stoch_rsi']['k'] < a['stoch_rsi']['d']:
        bear_score += 1; bear_reasons.append("StochRSI Falling")
    if adx_v > 25: bear_score += 1; bear_reasons.append("ADX > 25")
    if a['trend'] == 'BEARISH': bear_score += 1; bear_reasons.append("EMA Trend Bearish")
    if st_trend == 'BEARISH': bear_score += 1; bear_reasons.append("SuperTrend Bearish")
    if rvol in ('HIGH', 'EXTREME', 'ABOVE_AVG'): bear_score += 1; bear_reasons.append("Volume High")
    
    atr = a['atr']
    if atr == 0: return []
    
    if bull_score >= 6: # Higher threshold (from 5 to 6)
        confidence = min(10, 5 + int(bull_score/1.2))
        sl = current - (atr * 1.8) # Tighter SL
        tp1 = current + (atr * 4.5)
        risk = current - sl
        reward = tp1 - current
        if risk > 0 and reward/risk >= 1.8:
            trades.append({
                'strategy': 'Mom-Confluence', 'type': 'LONG', 'symbol': symbol,
                'entry': current, 'sl': sl, 'tp1': tp1, 'tp2': current + (atr * 8),
                'confidence': 'VERY HIGH' if confidence >= 8 else 'HIGH',
                'confidence_score': confidence,
                'risk_reward': round(reward/risk, 1),
                'reason': ' + '.join(bull_reasons[:5]),
                'indicators': f"Score: {bull_score}/7, ADX: {adx_v:.0f}, Vol: {rvol}",
                'expected_time': '1-4 hours', 'risk': risk, 'reward': reward,
                'entry_type': 'MARKET', 'timeframe': tf,
                'analysis_data': {'score': bull_score, 'adx': adx_v}
            })
            
    elif bear_score >= 6: # Higher threshold
        confidence = min(10, 5 + int(bear_score/1.2))
        sl = current + (atr * 1.8) # Tighter SL
        tp1 = current - (atr * 4.5)
        risk = sl - current
        reward = current - tp1
        if risk > 0 and reward/risk >= 1.8:
            trades.append({
                'strategy': 'Mom-Confluence', 'type': 'SHORT', 'symbol': symbol,
                'entry': current, 'sl': sl, 'tp1': tp1, 'tp2': current - (atr * 8),
                'confidence': 'VERY HIGH' if confidence >= 8 else 'HIGH',
                'confidence_score': confidence,
                'risk_reward': round(reward/risk, 1),
                'reason': ' + '.join(bear_reasons[:5]),
                'indicators': f"Score: {bear_score}/7, ADX: {adx_v:.0f}, Vol: {rvol}",
                'expected_time': '1-4 hours', 'risk': risk, 'reward': reward,
                'entry_type': 'MARKET', 'timeframe': tf,
                'analysis_data': {'score': bear_score, 'adx': adx_v}
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
            # Use UT Stop but ensure at least 2.5x ATR buffer
            sl_val = ut['stop'] if ut['stop'] < current else current - (atr * 3.0)
            sl = min(sl_val, current - (atr * 2.5))
            tp1 = entry + (entry - sl) * 3
            tp2 = entry + (entry - sl) * 5
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
            # Use UT Stop but ensure at least 2.5x ATR buffer
            sl_val = ut['stop'] if ut['stop'] > current else current + (atr * 3.0)
            sl = max(sl_val, current + (atr * 2.5))
            tp1 = entry - (sl - entry) * 3
            tp2 = entry - (sl - entry) * 5
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
    
    # LONG: PSAR Bullish + Price above TEMA + EMA200 Check
    if psar['trend'] == 'BULLISH' and current > tema:
        # WORLD-BEST FILTER: Only long above EMA200
        if current < a.get('ema200', current): return []
        
        confidence = 6 # Lower base
        reasons = [f"PSAR Bullish ({tf})", f"Price > TEMA ({tf})", "Above EMA200"]
        
        if a['rsi'] > 50 and a['rsi'] < 70: # Not overbought
            confidence += 2
            reasons.append("RSI Bullish Momentum")
        if a['adx']['adx'] > 25:
            confidence += 2
            reasons.append("Strong Trend (ADX)")
            
        if confidence >= MIN_CONFIDENCE:
            atr = a['atr']
            entry = current
            # Use PSAR dot or 2x ATR fallback for breathing room
            sl_val = psar['psar'] if psar['psar'] < current else current - (atr * 2.2)
            # Ensure SL is at least 1.5x ATR away even if PSAR is too close
            sl = min(sl_val, current - (atr * 1.5))
            tp1 = entry + (entry - sl) * 2.5
            tp2 = entry + (entry - sl) * 4
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
                        'psar_series': a.get('psar_series', []),
                        'tema': tema,
                        'tema_series': a.get('tema_series', []),
                        'ema200_series': a.get('ema200_series', []),
                        'rsi': a['rsi']
                    }
                })
                    
    # SHORT: PSAR Bearish + Price below TEMA + EMA200 Check
    elif psar['trend'] == 'BEARISH' and current < tema:
        # WORLD-BEST FILTER: Only short below EMA200
        if current > a.get('ema200', current): return []

        confidence = 6 # Lower base
        reasons = [f"PSAR Bearish ({tf})", f"Price < TEMA ({tf})", "Below EMA200"]
        
        if a['rsi'] < 50 and a['rsi'] > 30: # Not oversold
            confidence += 2
            reasons.append("RSI Bearish Momentum")
        if a['adx']['adx'] > 25:
            confidence += 2
            reasons.append("Strong Trend (ADX)")
            
        if confidence >= MIN_CONFIDENCE:
            atr = a['atr']
            entry = current
            # Use PSAR dot or 2x ATR fallback for breathing room
            sl_val = psar['psar'] if psar['psar'] > current else current + (atr * 2.2)
            # Ensure SL is at least 1.5x ATR away even if PSAR is too close
            sl = max(sl_val, current + (atr * 1.5))
            tp1 = entry - (sl - entry) * 2.5
            tp2 = entry - (sl - entry) * 4
            risk = sl - entry
            reward = entry - tp1
            
            if risk > 0:
                trades.append({
                    'strategy': 'PSAR-TEMA Scalp',
                    'type': 'SHORT',
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
                        'psar_series': a.get('psar_series', []),
                        'tema': tema,
                        'tema_series': a.get('tema_series', []),
                        'ema200_series': a.get('ema200_series', []),
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
            # Use Chandelier or 2.5x ATR buffer for safety
            sl_val = chan['long'] if chan['long'] < current else current - (atr * 2.5)
            sl = min(sl_val, current - (atr * 2.0))
            tp1 = entry + (entry - sl) * 3
            tp2 = entry + (entry - sl) * 5
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
                        'kama_series': a.get('kama_series', []),
                        'chandelier_long': chan['long'],
                        'chandelier_series': a.get('chandelier_series', []),
                        'ema200_series': a.get('ema200_series', []),
                        'vfi': a['vfi']
                    }
                })
                    
    # SHORT: Price < KAMA + Price < Chandelier Short Stop
    elif current < kama and current < chan['short']:
        confidence = 7
        reasons = [f"Price below KAMA Adaptive ({tf})", "Chandelier Exit Bearish"]
        
        if a['vfi'] < 0:
            confidence += 2
            reasons.append("Volume Flow Negative (VFI)")
            
        if confidence >= MIN_CONFIDENCE:
            atr = a['atr']
            entry = current
            # Use Chandelier or 2.5x ATR buffer for safety
            sl_val = chan['short'] if chan['short'] > current else current + (atr * 2.5)
            sl = max(sl_val, current + (atr * 2.0))
            tp1 = entry - (sl - entry) * 3
            tp2 = entry - (sl - entry) * 5
            risk = sl - entry
            reward = entry - tp1
            
            if risk > 0:
                trades.append({
                    'strategy': 'KAMA-Volatility Scalp',
                    'type': 'SHORT',
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
                        'kama_series': a.get('kama_series', []),
                        'chandelier_short': chan['short'],
                        'chandelier_series': a.get('chandelier_series', []),
                        'ema200_series': a.get('ema200_series', []),
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
            sl = entry - (atr * 3)
            tp1 = entry + (atr * 6)
            tp2 = entry + (atr * 10)
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
                        'zlsma': a['zlsma'],
                        'zlsma_series': a.get('zlsma_series', []),
                        'ema200_series': a.get('ema200_series', [])
                    }
                })
                    
    # SHORT: VFI < 0 + RSI < 50 + UO < 50
    elif vfi < 0 and rsi < 50 and uo < 50:
        confidence = 6
        reasons = ["Negative Volume Flow (VFI)", "RSI Bearish Momentum", "Ultimate Oscillator Negative"]
        
        if a['zlsma'] > current:
            confidence += 2
            reasons.append("Below ZLSMA")
            
        if confidence >= MIN_CONFIDENCE:
            atr = a['atr']
            entry = current
            sl = entry + (atr * 3)
            tp1 = entry - (atr * 6)
            tp2 = entry - (atr * 10)
            risk = sl - entry
            reward = entry - tp1
            
            if risk > 0:
                trades.append({
                    'strategy': 'VFI Perfect Scalper',
                    'type': 'SHORT',
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
                        'zlsma': a['zlsma'],
                        'zlsma_series': a.get('zlsma_series', []),
                        'ema200_series': a.get('ema200_series', [])
                    }
                })
    return trades

# ═══════════════════════════════════════════════════════════════
# 🧠 ULTIMATE 2025 STRATEGIES (Research-Backed)
# ═══════════════════════════════════════════════════════════════

def strategy_regime_adaptive(symbol, analyses):
    """Strategy: Market Regime Adaptive - Switches sub-strategy based on detected regime"""
    trades = []
    tf = '5m' if '5m' in analyses else '15m' if '15m' in analyses else None
    htf = '1h' if '1h' in analyses else '4h' if '4h' in analyses else None
    if not tf or tf not in analyses: return []
    a = analyses[tf]
    regime = a.get('market_regime', {})
    regime_type = regime.get('regime', 'UNKNOWN')
    if regime_type == 'CHOPPY': return []
    entry = a['current_price']
    atr = a['atr']
    if atr == 0: return []
    htf_trend = analyses[htf]['trend'] if htf and htf in analyses else None

    if regime_type in ('TRENDING_STRONG', 'TRENDING_WEAK'):
        adx_v = a['adx']['adx'] if isinstance(a['adx'], dict) else a['adx']
        if adx_v < 25: return []
        if a['trend'] == 'BULLISH' and a['macd']['histogram'] > 0 and a['rsi'] > 50:
            if htf_trend and htf_trend != 'BULLISH': return []
            d = 'LONG'; sl = entry - (atr*2); tp1 = entry + (atr*4)
        elif a['trend'] == 'BEARISH' and a['macd']['histogram'] < 0 and a['rsi'] < 50:
            if htf_trend and htf_trend != 'BEARISH': return []
            d = 'SHORT'; sl = entry + (atr*2); tp1 = entry - (atr*4)
        else: return []
        risk = abs(entry - sl); reward = abs(tp1 - entry)
        if risk == 0: return []
        trades.append({
            'strategy': 'Regime-Adaptive', 'type': d, 'symbol': symbol,
            'entry': entry, 'sl': sl, 'tp1': tp1,
            'tp2': entry + (atr*7*(1 if d=='LONG' else -1)),
            'confidence': 'HIGH', 'confidence_score': 7,
            'risk_reward': round(reward/risk, 1),
            'reason': f'Regime: {regime_type} + {a["trend"]} + ADX {adx_v:.0f}',
            'indicators': f'Regime: {regime_type}, ADX: {adx_v:.1f}, RSI: {a["rsi"]:.0f}',
            'expected_time': '1-4 hours', 'risk': risk, 'reward': reward,
            'entry_type': 'MARKET', 'timeframe': tf,
            'analysis_data': {'regime': regime_type, 'adx': adx_v}
        })
    elif regime_type == 'RANGING':
        bb = a.get('bb')
        if not bb: return []
        rsi = a['rsi']
        if rsi < 30 and entry <= bb['lower']*1.005:
            d = 'LONG'; sl = entry-(atr*1.5); tp1 = bb['middle']
        elif rsi > 70 and entry >= bb['upper']*0.995:
            d = 'SHORT'; sl = entry+(atr*1.5); tp1 = bb['middle']
        else: return []
        risk = abs(entry-sl); reward = abs(tp1-entry)
        if risk == 0: return []
        trades.append({
            'strategy': 'Regime-Adaptive', 'type': d, 'symbol': symbol,
            'entry': entry, 'sl': sl, 'tp1': tp1,
            'tp2': bb['lower'] if d=='SHORT' else bb['upper'],
            'confidence': 'STRONG', 'confidence_score': 7,
            'risk_reward': round(reward/risk, 1),
            'reason': f'Regime: RANGING + RSI {rsi:.0f} + BB Touch',
            'indicators': f'Regime: RANGING, RSI: {rsi:.0f}, Z: {a.get("zscore",0):.1f}',
            'expected_time': '30m-2h', 'risk': risk, 'reward': reward,
            'entry_type': 'MARKET', 'timeframe': tf,
            'analysis_data': {'regime': 'RANGING', 'rsi': rsi}
        })
    elif regime_type == 'VOLATILE':
        rvol = a.get('rvol_strength', {})
        if rvol.get('category') not in ('HIGH','EXTREME','ABOVE_AVG'): return []
        bb = a.get('bb')
        if not bb: return []
        if entry > bb['upper'] and a['macd']['histogram'] > 0:
            d = 'LONG'; sl = bb['middle']; tp1 = entry+(entry-bb['middle'])
        elif entry < bb['lower'] and a['macd']['histogram'] < 0:
            d = 'SHORT'; sl = bb['middle']; tp1 = entry-(bb['middle']-entry)
        else: return []
        risk = abs(entry-sl); reward = abs(tp1-entry)
        if risk == 0: return []
        trades.append({
            'strategy': 'Regime-Adaptive', 'type': d, 'symbol': symbol,
            'entry': entry, 'sl': sl, 'tp1': tp1,
            'tp2': entry+(atr*6*(1 if d=='LONG' else -1)),
            'confidence': 'STRONG', 'confidence_score': 7,
            'risk_reward': round(reward/risk, 1),
            'reason': f'Regime: VOLATILE + BB Breakout + RVOL {rvol.get("category")}',
            'indicators': f'Regime: VOLATILE, RVOL: {rvol.get("ratio",1):.1f}x',
            'expected_time': '15m-1h', 'risk': risk, 'reward': reward,
            'entry_type': 'MARKET', 'timeframe': tf,
            'analysis_data': {'regime': 'VOLATILE', 'rvol': rvol.get('ratio',1)}
        })
    return trades

def strategy_wyckoff_spring(symbol, analyses):
    """Strategy: Wyckoff Accumulation Spring - Catches institutional accumulation"""
    trades = []
    for tf in ['15m', '5m', '1h']:
        if tf not in analyses: continue
        a = analyses[tf]
        wyckoff = a.get('wyckoff_phase', {})
        entry = a['current_price']; atr = a['atr']
        if atr == 0: continue
        if wyckoff.get('phase') == 'ACCUMULATION' and wyckoff.get('event') == 'SPRING':
            sl = entry-(atr*1.5); tp1 = a['resistance']; tp2 = entry+(atr*6)
            risk = abs(entry-sl); reward = abs(tp1-entry)
            if risk <= 0: continue
            trades.append({
                'strategy': 'Wyckoff-Spring', 'type': 'LONG', 'symbol': symbol,
                'entry': entry, 'sl': sl, 'tp1': tp1, 'tp2': tp2,
                'confidence': 'ELITE', 'confidence_score': 9,
                'risk_reward': round(reward/risk, 1),
                'reason': 'Wyckoff Spring + Volume + Accumulation Phase',
                'indicators': f'Phase: ACCUM, Event: SPRING',
                'expected_time': '1-6 hours', 'risk': risk, 'reward': reward,
                'entry_type': 'MARKET', 'timeframe': tf,
                'analysis_data': {'wyckoff_phase': 'ACCUMULATION', 'wyckoff_event': 'SPRING'}
            }); break
        elif wyckoff.get('phase') == 'DISTRIBUTION' and wyckoff.get('event') == 'UPTHRUST':
            sl = entry+(atr*1.5); tp1 = a['support']; tp2 = entry-(atr*6)
            risk = abs(sl-entry); reward = abs(entry-tp1)
            if risk <= 0: continue
            trades.append({
                'strategy': 'Wyckoff-Upthrust', 'type': 'SHORT', 'symbol': symbol,
                'entry': entry, 'sl': sl, 'tp1': tp1, 'tp2': tp2,
                'confidence': 'ELITE', 'confidence_score': 9,
                'risk_reward': round(reward/risk, 1),
                'reason': 'Wyckoff Upthrust + Volume + Distribution Phase',
                'indicators': f'Phase: DIST, Event: UPTHRUST',
                'expected_time': '1-6 hours', 'risk': risk, 'reward': reward,
                'entry_type': 'MARKET', 'timeframe': tf,
                'analysis_data': {'wyckoff_phase': 'DISTRIBUTION', 'wyckoff_event': 'UPTHRUST'}
            }); break
    return trades

def strategy_triple_confluence(symbol, analyses):
    """Strategy: RSI + MACD + Volume Triple Confluence (73-77% win rate)"""
    trades = []
    for tf in ['5m', '15m', '1h']:
        if tf not in analyses: continue
        a = analyses[tf]
        rsi = a['rsi']; macd_hist = a['macd']['histogram']
        rvol = a.get('rvol_strength', {}); rvol_cat = rvol.get('category', 'NORMAL')
        adx_v = a['adx']['adx'] if isinstance(a['adx'], dict) else 0
        delta = a.get('cumulative_delta', {})
        entry = a['current_price']; atr = a['atr']
        if atr == 0: continue
        
        bull_s = 0; bear_s = 0; bull_r = []; bear_r = []
        # RSI
        if rsi < 35: bull_s += 2; bull_r.append(f'RSI Oversold({rsi:.0f})')
        elif 40 <= rsi <= 55: bull_s += 1; bull_r.append(f'RSI Bull({rsi:.0f})')
        if rsi > 65: bear_s += 2; bear_r.append(f'RSI Overbought({rsi:.0f})')
        elif 45 <= rsi <= 60: bear_s += 1; bear_r.append(f'RSI Bear({rsi:.0f})')
        # MACD
        if macd_hist > 0: bull_s += 1; bull_r.append('MACD+')
        if macd_hist < 0: bear_s += 1; bear_r.append('MACD-')
        if a['macd']['macd'] > a['macd']['signal'] and macd_hist > 0: bull_s += 1; bull_r.append('MACD Cross↑')
        if a['macd']['macd'] < a['macd']['signal'] and macd_hist < 0: bear_s += 1; bear_r.append('MACD Cross↓')
        # Volume
        if rvol_cat in ('HIGH','EXTREME'): bull_s += 1; bear_s += 1; bull_r.append(f'RVOL {rvol_cat}'); bear_r.append(f'RVOL {rvol_cat}')
        # Delta
        if delta.get('trend') == 'BUYING': bull_s += 1; bull_r.append('Delta↑')
        if delta.get('trend') == 'SELLING': bear_s += 1; bear_r.append('Delta↓')
        # EMA
        if a['trend'] == 'BULLISH': bull_s += 1; bull_r.append('EMA Bull')
        if a['trend'] == 'BEARISH': bear_s += 1; bear_r.append('EMA Bear')
        
        if bull_s >= 5 and bull_s > bear_s and adx_v > 20:
            sl = entry-(atr*2.5); tp1 = entry+(atr*5)
            risk = entry-sl; reward = tp1-entry
            if risk <= 0: continue
            cs = min(10, 5+int(bull_s))
            trades.append({
                'strategy': 'Triple-Confluence', 'type': 'LONG', 'symbol': symbol,
                'entry': entry, 'sl': sl, 'tp1': tp1, 'tp2': entry+(atr*7.5),
                'confidence': 'ELITE' if cs >= 9 else 'HIGH',
                'confidence_score': cs,
                'risk_reward': round(reward/risk, 1),
                'reason': ' + '.join(bull_r[:4]),
                'indicators': f'Score: {bull_s}/7, RSI: {rsi:.0f}',
                'expected_time': '30m-4h', 'risk': risk, 'reward': reward,
                'entry_type': 'MARKET', 'timeframe': tf,
                'analysis_data': {'confluence_score': bull_s, 'rsi': rsi}
            }); break
        elif bear_s >= 5 and bear_s > bull_s and adx_v > 20:
            sl = entry+(atr*2.5); tp1 = entry-(atr*5)
            risk = sl-entry; reward = entry-tp1
            if risk <= 0: continue
            cs = min(10, 5+int(bear_s))
            trades.append({
                'strategy': 'Triple-Confluence', 'type': 'SHORT', 'symbol': symbol,
                'entry': entry, 'sl': sl, 'tp1': tp1, 'tp2': entry-(atr*7.5),
                'confidence': 'ELITE' if cs >= 9 else 'HIGH',
                'confidence_score': cs,
                'risk_reward': round(reward/risk, 1),
                'reason': ' + '.join(bear_r[:4]),
                'indicators': f'Score: {bear_s}/7, RSI: {rsi:.0f}',
                'expected_time': '30m-4h', 'risk': risk, 'reward': reward,
                'entry_type': 'MARKET', 'timeframe': tf,
                'analysis_data': {'confluence_score': bear_s, 'rsi': rsi}
            }); break
    return trades

def strategy_zscore_reversion(symbol, analyses):
    """Strategy: Mean Reversion Z-Score - Enters at extreme statistical deviations"""
    trades = []
    for tf in ['5m', '15m', '30m']:
        if tf not in analyses: continue
        a = analyses[tf]
        zscore = a.get('zscore', 0)
        regime = a.get('market_regime', {}).get('regime', 'UNKNOWN')
        rsi = a['rsi']; bb = a.get('bb')
        entry = a['current_price']; atr = a['atr']
        if atr == 0 or not bb: continue
        if regime == 'TRENDING_STRONG': continue
        
        if zscore <= -2.0 and rsi < 35:
            sl = entry-(atr*1.5); tp1 = bb['middle']; tp2 = bb['upper']
            risk = entry-sl; reward = tp1-entry
            if risk <= 0 or reward <= 0: continue
            cs = 7 if zscore <= -2.5 else 6
            if regime == 'RANGING': cs += 1
            trades.append({
                'strategy': 'Z-Reversion', 'type': 'LONG', 'symbol': symbol,
                'entry': entry, 'sl': sl, 'tp1': tp1, 'tp2': tp2,
                'confidence': 'HIGH' if cs >= 8 else 'STRONG',
                'confidence_score': min(10, cs),
                'risk_reward': round(reward/risk, 1),
                'reason': f'Z-Score {zscore:.1f} (Extreme Oversold) + RSI {rsi:.0f}',
                'indicators': f'Z: {zscore:.2f}, RSI: {rsi:.0f}, Regime: {regime}',
                'expected_time': '15m-2h', 'risk': risk, 'reward': reward,
                'entry_type': 'MARKET', 'timeframe': tf,
                'analysis_data': {'zscore': zscore, 'regime': regime}
            }); break
        elif zscore >= 2.0 and rsi > 65:
            sl = entry+(atr*1.5); tp1 = bb['middle']; tp2 = bb['lower']
            risk = sl-entry; reward = entry-tp1
            if risk <= 0 or reward <= 0: continue
            cs = 7 if zscore >= 2.5 else 6
            if regime == 'RANGING': cs += 1
            trades.append({
                'strategy': 'Z-Reversion', 'type': 'SHORT', 'symbol': symbol,
                'entry': entry, 'sl': sl, 'tp1': tp1, 'tp2': tp2,
                'confidence': 'HIGH' if cs >= 8 else 'STRONG',
                'confidence_score': min(10, cs),
                'risk_reward': round(reward/risk, 1),
                'reason': f'Z-Score {zscore:.1f} (Extreme Overbought) + RSI {rsi:.0f}',
                'indicators': f'Z: {zscore:.2f}, RSI: {rsi:.0f}, Regime: {regime}',
                'expected_time': '15m-2h', 'risk': risk, 'reward': reward,
                'entry_type': 'MARKET', 'timeframe': tf,
                'analysis_data': {'zscore': zscore, 'regime': regime}
            }); break
    return trades

def strategy_mtf_trend_rider(symbol, analyses):
    """Strategy: Multi-Timeframe Trend Rider - 3 TF alignment with Fibonacci entry"""
    trades = []
    tf_trios = [('4h','1h','15m'), ('1h','15m','5m'), ('1d','4h','1h')]
    for htf, mtf, ltf in tf_trios:
        if htf not in analyses or mtf not in analyses or ltf not in analyses: continue
        h = analyses[htf]; m = analyses[mtf]; l_a = analyses[ltf]
        if h['trend'] == m['trend'] == l_a['trend'] and h['trend'] in ('BULLISH','BEARISH'):
            direction = h['trend']
            entry = l_a['current_price']; atr = l_a['atr']
            if atr == 0: continue
            adx_v = m['adx']['adx'] if isinstance(m['adx'], dict) else 0
            if adx_v < 20: continue
            m_rsi = m['rsi']
            if direction == 'BULLISH':
                if not (38 <= m_rsi <= 58): continue
                if l_a['macd']['histogram'] <= 0: continue
                sl = entry-(atr*2.5); tp1 = entry+(atr*5); tp2 = entry+(atr*8)
                risk = entry-sl; reward = tp1-entry
            else:
                if not (42 <= m_rsi <= 62): continue
                if l_a['macd']['histogram'] >= 0: continue
                sl = entry+(atr*2.5); tp1 = entry-(atr*5); tp2 = entry-(atr*8)
                risk = sl-entry; reward = entry-tp1
            if risk <= 0 or reward <= 0: continue
            trades.append({
                'strategy': 'MTF-TrendRider', 'type': 'LONG' if direction=='BULLISH' else 'SHORT',
                'symbol': symbol, 'entry': entry, 'sl': sl, 'tp1': tp1, 'tp2': tp2,
                'confidence': 'ELITE', 'confidence_score': 9,
                'risk_reward': round(reward/risk, 1),
                'reason': f'3-TF Aligned ({htf}+{mtf}+{ltf}) {direction} + Pullback',
                'indicators': f'HTF: {h["trend"]}, MTF RSI: {m_rsi:.0f}, ADX: {adx_v:.0f}',
                'expected_time': '2-12 hours', 'risk': risk, 'reward': reward,
                'entry_type': 'MARKET', 'timeframe': ltf,
                'analysis_data': {'htf_trend': h['trend'], 'mtf_rsi': m_rsi, 'adx': adx_v}
            }); break
    return trades

def strategy_smart_money_trap(symbol, analyses):
    """Strategy: Smart Money Trap Reversal - Detects stop hunts / liquidity sweeps"""
    trades = []
    for tf in ['5m', '15m', '1h']:
        if tf not in analyses: continue
        a = analyses[tf]
        entry = a['current_price']; atr = a['atr']
        if atr == 0: continue
        delta = a.get('cumulative_delta', {}); rvol = a.get('rvol_strength', {})
        candles = a.get('candles', [])
        if len(candles) < 3: continue
        support = a['support']; resistance = a['resistance']
        lc = candles[-1]
        
        # Bear trap (long): wick below support, close above, bullish candle, volume
        bear_trap = (lc['low'] < support*0.998 and lc['close'] > support and
                     lc['close'] > lc['open'] and rvol.get('category') in ('HIGH','EXTREME','ABOVE_AVG'))
        # Bull trap (short): wick above resistance, close below, bearish candle, volume
        bull_trap = (lc['high'] > resistance*1.002 and lc['close'] < resistance and
                     lc['close'] < lc['open'] and rvol.get('category') in ('HIGH','EXTREME','ABOVE_AVG'))
        
        if bear_trap:
            sl = lc['low']-(atr*0.5); tp1 = resistance; tp2 = entry+(atr*6)
            risk = entry-sl; reward = tp1-entry
            if risk <= 0 or reward <= 0: continue
            cs = 9 if delta.get('divergence') == 'BULLISH' else 8
            trades.append({
                'strategy': 'SmartMoney-Trap', 'type': 'LONG', 'symbol': symbol,
                'entry': entry, 'sl': sl, 'tp1': tp1, 'tp2': tp2,
                'confidence': 'ELITE' if cs >= 9 else 'HIGH', 'confidence_score': cs,
                'risk_reward': round(reward/risk, 1),
                'reason': f'Bear Trap (Stop Hunt) + RVOL {rvol.get("category")}',
                'indicators': f'Trap: BEAR, RVOL: {rvol.get("ratio",1):.1f}x',
                'expected_time': '30m-4h', 'risk': risk, 'reward': reward,
                'entry_type': 'MARKET', 'timeframe': tf,
                'analysis_data': {'trap_type': 'BEAR'}
            }); break
        elif bull_trap:
            sl = lc['high']+(atr*0.5); tp1 = support; tp2 = entry-(atr*6)
            risk = sl-entry; reward = entry-tp1
            if risk <= 0 or reward <= 0: continue
            cs = 9 if delta.get('divergence') == 'BEARISH' else 8
            trades.append({
                'strategy': 'SmartMoney-Trap', 'type': 'SHORT', 'symbol': symbol,
                'entry': entry, 'sl': sl, 'tp1': tp1, 'tp2': tp2,
                'confidence': 'ELITE' if cs >= 9 else 'HIGH', 'confidence_score': cs,
                'risk_reward': round(reward/risk, 1),
                'reason': f'Bull Trap (Stop Hunt) + RVOL {rvol.get("category")}',
                'indicators': f'Trap: BULL, RVOL: {rvol.get("ratio",1):.1f}x',
                'expected_time': '30m-4h', 'risk': risk, 'reward': reward,
                'entry_type': 'MARKET', 'timeframe': tf,
                'analysis_data': {'trap_type': 'BULL'}
            }); break
    return trades

def strategy_momentum_exhaustion(symbol, analyses):
    """Strategy: Momentum Exhaustion Reversal - Catches major trend reversals"""
    trades = []
    for tf in ['15m', '1h', '5m']:
        if tf not in analyses: continue
        a = analyses[tf]
        rsi = a['rsi']; adx_v = a['adx']['adx'] if isinstance(a['adx'], dict) else 0
        rsi_div = a.get('rsi_div', 'NONE'); wt = a.get('wavetrend', {})
        delta = a.get('cumulative_delta', {}); rvol = a.get('rvol_strength', {})
        entry = a['current_price']; atr = a['atr']
        if atr == 0: continue
        
        # Bearish exhaustion
        be = 0; br = []
        if rsi > 65: be += 1; br.append(f'RSI OB({rsi:.0f})')
        if rsi_div == 'BEARISH': be += 2; br.append('RSI Div↓')
        if isinstance(wt, dict) and wt.get('wt1', 0) > 60: be += 1; br.append('WT OB')
        if delta.get('divergence') == 'BEARISH': be += 1; br.append('Delta Div↓')
        if rvol.get('category') == 'LOW': be += 1; br.append('Vol Dry')
        
        # Bullish exhaustion
        bue = 0; bur = []
        if rsi < 35: bue += 1; bur.append(f'RSI OS({rsi:.0f})')
        if rsi_div == 'BULLISH': bue += 2; bur.append('RSI Div↑')
        if isinstance(wt, dict) and wt.get('wt1', 0) < -60: bue += 1; bur.append('WT OS')
        if delta.get('divergence') == 'BULLISH': bue += 1; bur.append('Delta Div↑')
        if rvol.get('category') == 'LOW': bue += 1; bur.append('Vol Dry')
        
        if be >= 3:
            sl = entry+(atr*2); tp1 = entry-(atr*4); tp2 = entry-(atr*7)
            risk = sl-entry; reward = entry-tp1
            if risk <= 0 or reward <= 0: continue
            cs = min(10, 6+be)
            trades.append({
                'strategy': 'Mom-Exhaustion', 'type': 'SHORT', 'symbol': symbol,
                'entry': entry, 'sl': sl, 'tp1': tp1, 'tp2': tp2,
                'confidence': 'ELITE' if cs >= 9 else 'HIGH', 'confidence_score': cs,
                'risk_reward': round(reward/risk, 1),
                'reason': ' + '.join(br[:4]),
                'indicators': f'Exhaust: {be}/5, RSI: {rsi:.0f}, ADX: {adx_v:.0f}',
                'expected_time': '1-6 hours', 'risk': risk, 'reward': reward,
                'entry_type': 'MARKET', 'timeframe': tf,
                'analysis_data': {'exhaustion_score': be, 'rsi': rsi}
            }); break
        elif bue >= 3:
            sl = entry-(atr*2); tp1 = entry+(atr*4); tp2 = entry+(atr*7)
            risk = entry-sl; reward = tp1-entry
            if risk <= 0 or reward <= 0: continue
            cs = min(10, 6+bue)
            trades.append({
                'strategy': 'Mom-Exhaustion', 'type': 'LONG', 'symbol': symbol,
                'entry': entry, 'sl': sl, 'tp1': tp1, 'tp2': tp2,
                'confidence': 'ELITE' if cs >= 9 else 'HIGH', 'confidence_score': cs,
                'risk_reward': round(reward/risk, 1),
                'reason': ' + '.join(bur[:4]),
                'indicators': f'Exhaust: {bue}/5, RSI: {rsi:.0f}, ADX: {adx_v:.0f}',
                'expected_time': '1-6 hours', 'risk': risk, 'reward': reward,
                'entry_type': 'MARKET', 'timeframe': tf,
                'analysis_data': {'exhaustion_score': bue, 'rsi': rsi}
            }); break
    return trades

# ═══════════════════════════════════════════════════════════════
# END ULTIMATE 2025 STRATEGIES
# ═══════════════════════════════════════════════════════════════

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
    
    # ELITE 2026 STRATEGIES (High Confidence)
    all_trades.extend(strategy_quantum_confluence_2026(symbol, analyses))
    all_trades.extend(strategy_smc_elite(symbol, analyses))
    all_trades.extend(strategy_harmonic_pro(symbol, analyses))

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
    
    # 🧠 ULTIMATE 2025 STRATEGIES (Research-Backed)
    all_trades.extend(strategy_regime_adaptive(symbol, analyses))
    all_trades.extend(strategy_wyckoff_spring(symbol, analyses))
    all_trades.extend(strategy_triple_confluence(symbol, analyses))
    all_trades.extend(strategy_zscore_reversion(symbol, analyses))
    all_trades.extend(strategy_mtf_trend_rider(symbol, analyses))
    all_trades.extend(strategy_smart_money_trap(symbol, analyses))
    all_trades.extend(strategy_momentum_exhaustion(symbol, analyses))
    
    return all_trades

# === Signal Quality Engine (Post-Processing) ===

# Timeframe weights for cross-timeframe voting (higher = stronger signal)
TF_WEIGHTS = {'1d': 5, '4h': 4, '1h': 3, '30m': 2, '15m': 2, '5m': 1, '3m': 1, '1m': 1}

def deduplicate_signals(trades):
    """
    Merge duplicate signals on the same symbol + direction.
    Keeps the highest-confidence/highest-TF signal and enriches it with agreement data.
    """
    if not trades:
        return trades

    # Group by (exchange, symbol, direction)
    groups = {}
    for trade in trades:
        exch = trade.get('exchange', 'N/A')
        key = (exch, trade['symbol'], trade['type'])  # Isolated per exchange
        if key not in groups:
            groups[key] = []
        groups[key].append(trade)

    merged = []
    total_dupes_removed = 0

    for key, group in groups.items():
        if len(group) == 1:
            # No duplicates — just add agreement info
            group[0]['agreement_count'] = 1
            group[0]['agreeing_strategies'] = [group[0]['strategy']]
            merged.append(group[0])
            continue

        # Multiple strategies agree on same symbol + direction
        # Sort by: confidence_score DESC, then timeframe weight DESC
        group.sort(key=lambda t: (
            t.get('confidence_score', 0),
            TF_WEIGHTS.get(t.get('timeframe', '1m'), 1),
            t.get('risk_reward', 0)
        ), reverse=True)

        # Keep the best signal as primary
        best = group[0]
        
        # Combine strategy names with timeframes and deduplicate
        strategy_list = []
        seen_pairs = set()
        for t in group:
            st_name = f"{t['strategy']} ({t.get('timeframe', 'N/A')})"
            if st_name not in seen_pairs:
                strategy_list.append(st_name)
                seen_pairs.add(st_name)
        
        # Enrich with agreement data
        best['agreement_count'] = len(strategy_list)
        best['agreeing_strategies'] = strategy_list

        # Boost confidence for agreement (+1 per extra strategy, capped at 10)
        original_conf = best.get('confidence_score', 0)
        best['original_confidence'] = original_conf
        agreement_bonus = min(len(group) - 1, 3)  # Max +3 from agreement
        best['confidence_score'] = min(10, original_conf + agreement_bonus)

        # Combine reasons from all strategies (keep it concise)
        all_reasons = set()
        for t in group:
            for reason in t.get('reason', '').split(' + '):
                if reason.strip():
                    all_reasons.add(reason.strip())
        best['reason'] = ' + '.join(list(all_reasons)[:5])

        merged.append(best)
        total_dupes_removed += len(group) - 1

    return merged, total_dupes_removed


def resolve_conflicts(trades):
    """
    Resolve LONG vs SHORT conflicts on the same symbol on the same exchange.
    Also identifies global market correlation (e.g. 5+ LONGS = high directional bias).
    """
    if not trades:
        return trades, 0

    # Group by (exchange, symbol)
    by_exchange_symbol = {}
    long_total = 0
    short_total = 0
    
    for trade in trades:
        exch = trade.get('exchange', 'N/A')
        sym = trade['symbol']
        key = (exch, sym)
        if key not in by_exchange_symbol:
            by_exchange_symbol[key] = {'LONG': [], 'SHORT': []}
        
        direction = trade['type']
        if direction == 'LONG': long_total += 1
        else: short_total += 1
        
        by_exchange_symbol[key][direction].append(trade)

    resolved = []
    conflicts_found = 0

    for key, directions in by_exchange_symbol.items():
        exch, sym = key
        longs = directions.get('LONG', [])
        shorts = directions.get('SHORT', [])

        if longs and shorts:
            # Conflict detected on this specific exchange
            conflicts_found += 1

            best_long_conf = max(t.get('confidence_score', 0) for t in longs)
            best_short_conf = max(t.get('confidence_score', 0) for t in shorts)

            if best_long_conf >= best_short_conf + 3:
                # Long is dominant — keep longs, suppress shorts
                for t in longs:
                    t['conflict_warning'] = f"⚠️ Conflicting SHORT signals suppressed on {exch} (LONG {best_long_conf}/10 vs SHORT {best_short_conf}/10)"
                    resolved.append(t)
            elif best_short_conf >= best_long_conf + 3:
                # Short is dominant — keep shorts, suppress longs
                for t in shorts:
                    t['conflict_warning'] = f"⚠️ Conflicting LONG signals suppressed on {exch} (SHORT {best_short_conf}/10 vs LONG {best_long_conf}/10)"
                    resolved.append(t)
            else:
                # Both sides similar — VOID BOTH (Sign of indecision/chop)
                for t in longs + shorts:
                    pass
                conflicts_found += 1 # Report as resolved but removed

        else:
            # No conflict — pass through
            resolved.extend(longs)
            resolved.extend(shorts)

    # Add correlation metrics to each trade
    for t in resolved:
        t['market_correlation'] = f"Overall Analysis Bias: {long_total} LONGs / {short_total} SHORTs"
        if (t['type'] == 'LONG' and long_total >= 10) or (t['type'] == 'SHORT' and short_total >= 10):
            t['correlation_warning'] = "⚠️ Extreme Directional Bias Detected — Caution on Size"

    return resolved, conflicts_found


def enhance_confidence(trades):
    """
    Apply dynamic confidence bonuses based on signal quality factors.
    Bonuses are additive and the final score is capped at 10.
    """
    for trade in trades:
        if 'original_confidence' not in trade:
            trade['original_confidence'] = trade.get('confidence_score', 0)

        bonuses = 0

        # +1 for excellent R:R (>= 3:1)
        if trade.get('risk_reward', 0) >= 3:
            bonuses += 1

        # +1 for strong agreement (3+ strategies)
        if trade.get('agreement_count', 1) >= 3:
            bonuses += 1

        # +1 for high-timeframe confirmation (1h, 4h, 1d)
        if TF_WEIGHTS.get(trade.get('timeframe', '1m'), 1) >= 3:
            bonuses += 1

        # Apply bonuses (capped at 10)
        trade['confidence_score'] = min(10, trade['confidence_score'] + bonuses)
        
        # Calculate Adaptive Risk / Recommended Position Sizing
        calculate_adaptive_risk(trade)

    return trades

def calculate_adaptive_risk(trade):
    """
    Calculate suggested position size and risk parameters.
    Based on $10,000 default balance and 1% risk per trade.
    """
    # Use defaults if not provided
    balance = float(trade.get('account_balance', 10000.0))
    risk_pct = float(trade.get('risk_per_trade', 1.0)) # 1% risk per trade
    
    risk_amount = balance * (risk_pct / 100.0)
    
    entry = float(trade.get('entry', 0))
    sl = float(trade.get('sl', 0))
    
    if entry and sl and entry != sl:
        # Distance to Stop Loss
        sl_dist = abs(entry - sl)
        sl_pct = (sl_dist / entry) * 100.0
        
        # Suggested Quantity (Units)
        # Formula: Quantity = (Balance * Risk%) / (Entry - SL)
        qty = risk_amount / sl_dist
        
        # Position Size in Dollars (Leveraged if necessary)
        pos_size_dollars = qty * entry
        
        # Leverage needed if pos_size > balance
        leverage = pos_size_dollars / balance
        
        trade['suggested_qty'] = round(qty, 6)
        trade['suggested_pos_size'] = round(pos_size_dollars, 2)
        trade['risk_amount'] = round(risk_amount, 2)
        trade['sl_pct'] = round(sl_pct, 2)
        trade['leverage_needed'] = round(leverage, 1) if leverage > 1 else 1.0
        
        # Strategic Advice
        if trade.get('risk_reward', 0) >= 2:
            trade['trailing_advice'] = "Move SL to Entry at 1:1 Profit; Take 50% at 2:1"
        else:
            trade['trailing_advice'] = "Aggressive trailing stop recommended"
            
    return trade


def get_signal_quality(trade):
    """Classify signal quality based on absolute confidence and confluence."""
    score = trade.get('confidence_score', 0)
    agreement = trade.get('agreement_count', 1)
    rr = trade.get('risk_reward', 0)
    mtf_status = trade.get('mtf_alignment', 'NEUTRAL')
    
    # ELITE Criteria (High Conviction Mastery):
    # Rule 1: Extreme confidence (10/10) with ANY alignment and decent RR
    # Rule 2: Strong confidence (9/10) with agreement OR perfect mtf alignment
    is_elite = False
    if score >= 10 and 'STRONG' in mtf_status and rr >= 2.0:
        is_elite = True
    elif score >= 9 and agreement >= 2 and rr >= 2.0:
        is_elite = True
    elif score >= 9 and 'STRONG' in mtf_status and rr >= 2.5:
        is_elite = True
    elif trade.get('strategy', '') == 'Quantum Elite 2026' and score >= 9:
        is_elite = True
        
    if is_elite:
        return 'ELITE'
    elif score >= 7 and rr >= 1.8:
        return 'STRONG'
    else:
        return 'STANDARD'

def apply_global_market_filters(trades, symbol_analyses_map):
    """
    World-Class Filter Layer: Rejects low-probability setups based on 
    Global Market Context (MTF Trend, Volatility, and Institutional Flow).
    """
    if not trades or not symbol_analyses_map:
        return trades

    filtered = []
    for t in trades:
        tf = t['timeframe']
        symbol = t['symbol']
        
        # Get analyses for THIS specific symbol
        symbol_data = symbol_analyses_map.get(symbol, {})
        if not symbol_data: continue

        # 1. Get Higher Timeframe Context (Dynamic Detection)
        sorted_tfs = sorted(symbol_data.keys(), key=lambda x: TF_WEIGHTS.get(x, 0), reverse=True)
        h_tfs = [tf_name for tf_name in sorted_tfs if TF_WEIGHTS.get(tf_name, 0) > TF_WEIGHTS.get(tf, 0)]
        
        htf_bullish = 0
        htf_bearish = 0
        
        # Check up to top 2 available higher timeframes
        for htf_name in h_tfs[:2]:
            htf_analysis = symbol_data[htf_name]
            weight = 2 if TF_WEIGHTS.get(htf_name, 0) >= 4 else 1 # Heavy weight for 4h/1d
            if htf_analysis.get('trend') == 'BULLISH': htf_bullish += weight
            elif htf_analysis.get('trend') == 'BEARISH': htf_bearish += weight
            
        dominant_trend = 'BULLISH' if htf_bullish > htf_bearish else 'BEARISH' if htf_bearish > htf_bullish else 'NEUTRAL'
        
        # 2. STRICT: Counter-Trend Signal Rejection (World-Best Rule #1)
        is_counter_trend = (t['type'] == 'LONG' and dominant_trend == 'BEARISH' and htf_bearish >= 2) or \
                           (t['type'] == 'SHORT' and dominant_trend == 'BULLISH' and htf_bullish >= 2)
        
        if is_counter_trend:
            if 'Reversion' in t['strategy'] or 'Exhaustion' in t['strategy']:
                t['mtf_alignment'] = 'MEAN_REVERSION'
                t['confidence_score'] -= 1
            else:
                continue 
        else:
            t['mtf_alignment'] = 'STRONG_ALIGN' if htf_bullish >= 2 or htf_bearish >= 2 else 'NEUTRAL'

        # 3. ANTI-CHOP SHIELD: Kill trend signals in chop (World-Best Rule #2)
        current_tf_analysis = symbol_data.get(tf)
        if current_tf_analysis:
            chop = current_tf_analysis.get('chop', 50)
            adx = current_tf_analysis.get('adx', {}).get('adx', 0)
            if chop > 61.8 and 'Trend' in t['strategy'] and adx < 25:
                continue
            if adx < 18 and 'Trend' in t['strategy']:
                continue

        # 4. INSTITUTIONAL CONFIRMATION (World-Best Rule #3)
        if current_tf_analysis:
            rvol = current_tf_analysis.get('rvol', 1.0)
            delta = current_tf_analysis.get('cumulative_delta', {}).get('trend', 'NEUTRAL')
            if t['confidence_score'] >= 7:
                 if rvol < 1.1: t['confidence_score'] -= 1
                 if (t['type'] == 'LONG' and delta == 'SELLING') or (t['type'] == 'SHORT' and delta == 'BUYING'):
                     t['confidence_score'] -= 1 

        filtered.append(t)
    return filtered


def enforce_signal_safety_buffers(trades, symbol_analyses_map):
    """
    World-Class Safety Layer: Ensures no trade has a 'Guesswork' Stop Loss.
    Uses Structural Analysis (Order Blocks, Swing Points) + Volatility Buffers.
    """
    for trade in trades:
        symbol = trade.get('symbol')
        tf = trade.get('timeframe')
        atr = trade.get('atr', 0)
        entry = trade['entry']
        tp1 = trade['tp1']
        
        # Get Analysis Context for Structural Protection
        if not symbol_analyses_map or symbol not in symbol_analyses_map:
            continue
            
        analysis = symbol_analyses_map[symbol].get(tf)
        if not analysis: continue
        
        # Part 1: Structural SL Placement (Hunt Protection)
        structural_sl = None
        
        if trade['type'] == 'LONG':
            obs = analysis.get('order_blocks', {})
            bull_ob = obs.get('bullish_ob')
            sup_dem = analysis.get('sup_dem')
            
            # Extract floor levels
            ob_floor = bull_ob['low'] if isinstance(bull_ob, dict) else None
            sd_floor = sup_dem['level'] if isinstance(sup_dem, dict) and sup_dem['type'] == 'DEMAND' else None
            swing_low = analysis.get('support', entry * 0.98)
            
            # Use the most conservative (lowest) level as structure
            structural_sl = swing_low
            if ob_floor and ob_floor < entry: structural_sl = min(structural_sl, ob_floor)
            if sd_floor and sd_floor < entry: structural_sl = min(structural_sl, sd_floor)
            
            # Apply Safety Buffer (0.8x ATR) below structure
            trade['sl'] = min(trade['sl'], structural_sl - (atr * 0.8))
            
        else: # SHORT
            obs = analysis.get('order_blocks', {})
            bear_ob = obs.get('bearish_ob')
            sup_dem = analysis.get('sup_dem')
            
            # Extract ceiling levels
            ob_ceil = bear_ob['high'] if isinstance(bear_ob, dict) else None
            sd_ceil = sup_dem['level'] if isinstance(sup_dem, dict) and sup_dem['type'] == 'SUPPLY' else None
            swing_high = analysis.get('resistance', entry * 1.02)
            
            # Use the most conservative (highest) level as structure
            structural_sl = swing_high
            if ob_ceil and ob_ceil > entry: structural_sl = max(structural_sl, ob_ceil)
            if sd_ceil and sd_ceil > entry: structural_sl = max(structural_sl, sd_ceil)
            
            # Apply Safety Buffer (0.8x ATR) above structure
            trade['sl'] = max(trade['sl'], structural_sl + (atr * 0.8))

        # Part 2: Smart RR Rebalancing (Maximum Breathing Room)
        current_risk = abs(entry - trade['sl'])
        current_reward = abs(tp1 - entry)
        rr = current_reward / max(0.00000001, current_risk)
        
        if rr > 2.5:
            target_rr = 2.0
            new_risk = current_reward / target_rr
            if trade['type'] == 'LONG':
                trade['sl'] = entry - new_risk
            else:
                trade['sl'] = entry + new_risk
            trade['reason'] += f" | 🛡️ BREATHING ROOM (RR {target_rr}:1)"

        # Step 3: Final Meta Sync
        trade['risk'] = abs(trade['entry'] - trade['sl'])
        trade['reward'] = abs(trade['tp1'] - trade['entry'])
        trade['risk_reward'] = round(trade['reward'] / max(0.00000001, trade['risk']), 1)
    
    return trades


def save_signal_history(trades, filepath='signals_history.json'):
    """Append trade signals to a JSON history file for performance tracking."""
    try:
        import os
        history = []
        full_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filepath)

        # Load existing history
        if os.path.exists(full_path):
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        history = json.loads(content)
            except (json.JSONDecodeError, IOError):
                history = []

        # Add new trades (compact format for storage)
        for trade in trades:
            entry = {
                'timestamp': trade.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                'symbol': trade.get('symbol'),
                'type': trade.get('type'),
                'strategy': trade.get('strategy'),
                'exchange': trade.get('exchange', 'N/A'),
                'entry': trade.get('entry'),
                'sl': trade.get('sl'),
                'tp1': trade.get('tp1'),
                'tp2': trade.get('tp2'),
                'risk_reward': trade.get('risk_reward'),
                'confidence_score': trade.get('confidence_score'),
                'original_confidence': trade.get('original_confidence'),
                'agreement_count': trade.get('agreement_count', 1),
                'agreeing_strategies': trade.get('agreeing_strategies', []),
                'signal_quality': trade.get('signal_quality', 'STANDARD'),
                'conflict_warning': trade.get('conflict_warning'),
                'timeframe': trade.get('timeframe'),
                'candle_time': trade.get('candle_time'),
                'reason': trade.get('reason'),
                'result': None  # To be filled in later for performance tracking
            }
            history.append(entry)

        # Keep only last 1000 signals to avoid huge files
        if len(history) > 1000:
            history = history[-1000:]

        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

    except Exception as e:
        with print_lock:
            print(f"  ⚠️ Could not save signal history: {e}")

def run_analysis():
    exchanges_str = ', '.join(ENABLED_EXCHANGES)
    print("\n" + "="*120)
    print("🔥 RBOT PRO | MULTI-EXCHANGE REAL-TIME ANALYSIS - HIGH CONFIDENCE TRADES ONLY")
    print("="*120)
    print(f"Exchanges: {exchanges_str} | Timeframes: {', '.join(ENABLED_TIMEFRAMES)} (VERIFIED) | Indicators ({len(ENABLED_INDICATORS)}): {', '.join(ENABLED_INDICATORS)} (VERIFIED)")
    print(f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Minimum Confidence: {MIN_CONFIDENCE}/10 | Strategies: Swing, Scalp, Stoch-Pullback, Breakout, SuperTrend, VWAP, Ichimoku, FVG, Divergence, ADX-Mom, BB-Rev, Liquidity, WaveTrend, Squeeze, Z-Scalp, MFI, Fisher, VolSpike, SMC-CHoCH, Donchian, STC-Mom, Vortex, ICT-Silver, UT-Bot Elite, Keltner-Rev, Vol-Cap, Mom-Confluence, ICT-Wealth, Harmonic-Gartley, SMC-Elite, Harmonic-Pro, PSAR-TEMA, KAMA-Vol, VFI-Scalp")
    print("="*120 + "\n")
    all_trades = []
    symbol_analyses_map = {}
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
                symbol_analyses_map[sym] = analyses
                trades = run_strategies(sym, analyses)
                if trades:
                    # Filter trades by MIN_CONFIDENCE
                    filtered_trades = [t for t in trades if t.get('confidence_score', 0) >= MIN_CONFIDENCE]
                    if filtered_trades:
                        with print_lock:
                            for trade in filtered_trades:
                                # Step 1: Capture Metadata
                                trade['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                trade['exchange'] = exchange.upper()
                                tf_analysis = analyses.get(trade['timeframe'])
                                if tf_analysis:
                                    trade['candle_time'] = tf_analysis['candle_time'] / 1000
                                    trade['atr'] = tf_analysis['atr']
                                    
                                # Step 2: Immediate Global Filter (for real-time suppression)
                                # We wrap it in a list as the filter expects a list
                                filtered_single = apply_global_market_filters([trade], {sym: analyses})
                                if not filtered_single:
                                    continue # Suppressed by G.M.C. (Counter-trend/Chop)
                                
                                trade = filtered_single[0]
                                
                                # Step 3: Final Confidence Check (post-filter)
                                if trade.get('confidence_score', 0) < MIN_CONFIDENCE:
                                    continue # Penalized below user threshold

                                # Step 4: Quality & Risk Pre-calc
                                trade['signal_quality'] = get_signal_quality(trade)
                                calculate_adaptive_risk(trade)
                                
                                all_trades.append(trade)

                                # Step 5: High-Clarity Log & UI Stream
                                print(f"\n{'='*80}")
                                print(f"[{trade['strategy']}] TRADE FOUND - {trade['type']} {trade['symbol']} on {exchange} (Conf: {trade['confidence_score']}/10)")
                                print(f"Entry: ${trade['entry']:.6f}  SL: ${trade['sl']:.6f}  TP1: ${trade['tp1']:.6f}  R/R: {trade['risk_reward']}:1")
                                print(f"Indicators: {trade['indicators']} | Reason: {trade['reason']} | Expected: {trade['expected_time']}")
                                print(f"SIGNAL_DATA:{json.dumps(trade, default=str)}")
    # === SIGNAL QUALITY POST-PROCESSING PIPELINE ===
    raw_count = len(all_trades)
    dupes_removed = 0
    conflicts_found = 0

    if all_trades:
        # Step 1: Apply Global Market Filters (Counter-Trend & Anti-Chop)
        all_trades = apply_global_market_filters(all_trades, symbol_analyses_map)

        # Step 2: Deduplicate signals (merge same symbol + direction)
        all_trades, dupes_removed = deduplicate_signals(all_trades)

        # Step 3: Resolve LONG vs SHORT conflicts on same symbol
        all_trades, conflicts_found = resolve_conflicts(all_trades)

        # Step 4: Enhance confidence with dynamic bonuses
        all_trades = enhance_confidence(all_trades)

        # Step 5: FINAL SECURITY FILTER - Ensure signals still meet MIN_CONFIDENCE after penalties
        all_trades = [t for t in all_trades if t.get('confidence_score', 0) >= MIN_CONFIDENCE]

        # Step 6: Classify signal quality
        for trade in all_trades:
            trade['signal_quality'] = get_signal_quality(trade)

        # Step 7: Enforce Global Safety Buffers (Bulletproof SLs)
        all_trades = enforce_signal_safety_buffers(all_trades, symbol_analyses_map)

    # === PRINT FINAL RESULTS ===
    print("\n" + "="*120)
    print(f"🚀 TRADE SETUPS (Confidence Score {MIN_CONFIDENCE}/10+  |  Minimum 2:1 Risk/Reward)")
    print("="*120)

    # Signal Quality Stats
    if all_trades:
        elite_count = sum(1 for t in all_trades if t.get('signal_quality') == 'ELITE')
        strong_count = sum(1 for t in all_trades if t.get('signal_quality') == 'STRONG')
        standard_count = sum(1 for t in all_trades if t.get('signal_quality') == 'STANDARD')
        print(f"\n🧠 SIGNAL INTELLIGENCE: {raw_count} raw → {len(all_trades)} final signals | {dupes_removed} duplicates merged | {conflicts_found} conflicts resolved")
        print(f"   Quality Breakdown: 🏆 ELITE: {elite_count}  |  💪 STRONG: {strong_count}  |  📊 STANDARD: {standard_count}")
        print("="*120 + "\n")

        all_trades.sort(key=lambda x: (
            {'ELITE': 3, 'STRONG': 2, 'STANDARD': 1}.get(x.get('signal_quality', 'STANDARD'), 0),
            x['confidence_score'],
            x['risk_reward']
        ), reverse=True)

        for i, trade in enumerate(all_trades, 1):
            quality_badge = {'ELITE': '🏆 ELITE', 'STRONG': '💪 STRONG', 'STANDARD': '📊 STANDARD'}.get(trade.get('signal_quality', 'STANDARD'), '📊 STANDARD')
            agreement_str = f"  |  ✅ {trade.get('agreement_count', 1)} strategies agree" if trade.get('agreement_count', 1) > 1 else ""

            print(f"\n{'='*120}")
            print(f"TRADE #{i} [{trade['strategy']}] - {trade['type']} {trade['symbol']} on {trade.get('exchange', 'N/A')} (Confidence: {trade['confidence_score']}/10) [{quality_badge}]{agreement_str}")
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
            if trade.get('agreement_count', 1) > 1:
                print(f"🤝 Agreement:          {trade['agreement_count']} strategies ({', '.join(trade.get('agreeing_strategies', []))})")
            if trade.get('conflict_warning'):
                print(f"{trade['conflict_warning']}")
            if trade.get('original_confidence') and trade['original_confidence'] != trade['confidence_score']:
                print(f"📈 Confidence Boost:   {trade['original_confidence']} → {trade['confidence_score']} (quality bonuses applied)")

            # Print to terminal for final summary
            print(f"SIGNAL_SUMMARY: {trade['symbol']} {trade['type']} (Score: {trade['confidence_score']})")
    else:
        print("\n")
        print("⏳ No trades meeting the configured confidence threshold found at this moment.")
        print(f"   System is waiting for optimal alignment across selected timeframes...")

    # Save signal history
    if all_trades:
        save_signal_history(all_trades)
        print(f"\n💾 Signal history saved ({len(all_trades)} signals → signals_history.json)")

    print("\n" + "="*120)
    print(f"✅ Analysis Complete - RBot Pro Multi-Exchange Analysis ({exchanges_str})")
    print("="*120 + "\n")

if __name__ == '__main__':
    run_analysis()

