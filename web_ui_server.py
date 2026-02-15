#!/usr/bin/env python3
"""
Advanced Web UI Server for RBot Pro Multi-Exchange Real-Time Analysis
Features: Multi-Exchange Support, Symbol/Indicator Selection, Auto-Run, Customizable Strategies
"""

import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import subprocess
import os
import sys
import io
import queue
import threading
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import json

# Fix Windows Unicode encoding issues for emojis
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
import csv
import requests

# Import News Manager
from news_manager import news_manager
# Import Real Trader
from real_trader import RealTrader

# Initialize Real Trader
real_trader = RealTrader()

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SECRET_KEY'] = 'rbot-pro-analysis-ui-secret'

# SocketIO with Institutional Stability Buffers
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='eventlet',
    ping_timeout=60,   # 60s timeout for stability
    ping_interval=20,  # 20s heartbeat to keep connection alive
    logger=False,
    engineio_logger=False
)

# --- Exchange Specific Kline Fetchers (Ported from fast_analysis.py) ---
# --- Global Request Headers ---
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36',
    'Accept': 'application/json'
}

def safe_request(url, method='GET', params=None, json_data=None, timeout=25, retries=3):
    """Fetch with retries, exponential backoff, cache-busting, and institutional headers."""
    import time
    import random
    from requests.exceptions import SSLError, ConnectionError, Timeout
    
    # 1. Institutional Cache-Busting (Suppressed for strict exchanges)
    strict_exchanges = ['binance', 'mexc', 'bybit', 'okx', 'bitget', 'kucoin', 'gate.io', 'huobi', 'gateio']
    is_strict = any(ex in url.lower() for ex in strict_exchanges)
    
    ts = str(int(time.time() * 1000))
    if params is None: params = {}
    
    # Disable _t for modern APIs that reject unknown params
    if not is_strict:
        params['_t'] = ts
    
    headers = HEADERS.copy()
    headers['X-Requested-With'] = 'XMLHttpRequest'
    
    last_err = None
    for attempt in range(retries):
        try:
            r = requests.request(method, url, params=params, json=json_data, headers=headers, timeout=timeout, verify=True)
            r.raise_for_status()
            return r.json()
        except (SSLError, ConnectionError, Timeout) as e:
            # Network/SSL errors - retry with exponential backoff
            last_err = e
            if attempt < retries - 1:
                time.sleep(1 + attempt * 1.5)
            continue
        except Exception as e:
            # Other errors (JSON decode, HTTP errors, etc.)
            last_err = e
            if attempt < retries - 1:
                time.sleep(2 + attempt * 2)
            continue
    raise last_err

# --- Exchange Specific Kline Fetchers (Enriched with Fallbacks) ---
def get_klines_mexc(symbol, interval, limit=200):
    try:
        mapping = {'1m': 'Min1', '3m': 'Min3', '5m': 'Min5', '15m': 'Min15', '30m': 'Min30', '1h': 'Min60', '4h': 'Hour4', '1d': 'Day1'}
        mexc_interval_fut = mapping.get(interval, 'Min60')
        
        # 1. Try FUTURES Endpoint first
        futures_symbol = symbol.replace('USDT', '_USDT') if 'USDT' in symbol and '_' not in symbol else symbol
        url_fut = f'https://contract.mexc.com/api/v1/contract/kline/{futures_symbol}?interval={mexc_interval_fut}&limit={limit}'
        data = safe_request(url_fut)
        if data.get('success') and 'data' in data and len(data['data'].get('time', [])) > 0:
            d = data['data']
            return [[int(d['time'][i]) * 1000, float(d['open'][i]), float(d['high'][i]), float(d['low'][i]), float(d['close'][i]), float(d['vol'][i])] for i in range(len(d['time']))]
        
        # 2. Try SPOT Fallback if Futures fails
        clean_symbol = symbol.replace('_', '').upper()
        url_spot = f'https://api.mexc.com/api/v3/klines?symbol={clean_symbol}&interval={interval}&limit={limit}'
        data = safe_request(url_spot)
        if isinstance(data, list) and len(data) > 0:
            return [[int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])] for k in data]
            
        return None
    except Exception as e: 
        print(f"  ⚠ MEXC Fetch Error ({symbol}): {e}")
        return None

def get_klines_binance(symbol, interval, limit=200):
    try:
        clean_symbol = symbol.replace('_', '').replace('-', '').upper()
        # 1. Try Futures
        url_fut = f'https://fapi.binance.com/fapi/v1/klines?symbol={clean_symbol}&interval={interval}&limit={limit}'
        data = safe_request(url_fut)
        if isinstance(data, list) and len(data) > 0:
            return [[int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])] for k in data]
        
        # 2. Try Spot Fallback
        url_spot = f'https://api.binance.com/api/v3/klines?symbol={clean_symbol}&interval={interval}&limit={limit}'
        data = safe_request(url_spot)
        if isinstance(data, list) and len(data) > 0:
            return [[int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])] for k in data]
        return None
    except: return None

def get_klines_bybit(symbol, interval, limit=200):
    try:
        mapping = {'1m': '1', '3m': '3', '5m': '5', '15m': '15', '30m': '30', '1h': '60', '4h': '240', '1d': 'D'}
        clean_symbol = symbol.replace('_', '').replace('-', '').upper()
        url = f'https://api.bybit.com/v5/market/kline?category=linear&symbol={clean_symbol}&interval={mapping.get(interval, "60")}&limit={limit}'
        data = safe_request(url)
        if data.get('result') and data['result'].get('list'):
            return [[int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])] for k in reversed(data['result']['list'])]
        return None
    except: return None

def get_klines_bitget(symbol, interval, limit=200):
    try:
        mapping = {'1m': '1m', '3m': '3m', '5m': '5m', '15m': '15m', '30m': '30m', '1h': '1H', '4h': '4H', '1d': '1D'}
        clean_symbol = symbol.replace('_', '').replace('-', '').upper()
        url = f'https://api.bitget.com/api/v2/mix/market/candles?productType=USDT-FUTURES&symbol={clean_symbol}&granularity={mapping.get(interval, "1H")}&limit={limit}'
        data = safe_request(url)
        if data.get('data'):
            candles = [[int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])] for k in data['data']]
            if candles and candles[0][0] > candles[-1][0]: candles.reverse()
            return candles
        return None
    except: return None

def get_klines_okx(symbol, interval, limit=200):
    """Get klines from OKX API with domain fallbacks"""
    try:
        mapping = {'1m': '1m', '3m': '3m', '5m': '5m', '15m': '15m', '30m': '30m', '1h': '1H', '4h': '4H', '1d': '1D'}
        okx_symbol = symbol.replace('_', '').replace('-', '')
        if 'USDT' in okx_symbol and '-' not in okx_symbol:
            okx_symbol = okx_symbol.replace('USDT', '-USDT-SWAP')
        
        domains = ['https://www.okx.com', 'https://www.okx.net', 'https://okx.com']
        for base in domains:
            try:
                url = f'{base}/api/v5/market/candles?instId={okx_symbol}&bar={mapping.get(interval, "1H")}&limit={limit}'
                data = safe_request(url)
                if data.get('data'):
                    return [[int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])] for k in reversed(data['data'])]
            except: continue
        return None
    except: return None

def get_klines_kucoin(symbol, interval, limit=200):
    try:
        mapping = {'1m': '1min', '3m': '3min', '5m': '5min', '15m': '15min', '30m': '30min', '1h': '1hour', '4h': '4hour', '1d': '1day'}
        kucoin_symbol = symbol.replace('_', '').replace('-', '')
        if 'USDT' in kucoin_symbol and '-' not in kucoin_symbol:
            kucoin_symbol = kucoin_symbol.replace('USDT', '-USDT')
        url = f'https://api.kucoin.com/api/v1/market/candles?type={mapping.get(interval, "1hour")}&symbol={kucoin_symbol}&limit={limit}'
        data = safe_request(url)
        if data.get('data'):
            return [[int(k[0]) * 1000, float(k[1]), float(k[3]), float(k[4]), float(k[2]), float(k[5])] for k in reversed(data['data'])]
        return None
    except: return None

def get_klines_gateio(symbol, interval, limit=200):
    try:
        gate_symbol = symbol.replace('USDT', '_USDT') if 'USDT' in symbol and '_' not in symbol else symbol
        url = f'https://api.gateio.ws/api/v4/futures/usdt/candlesticks?contract={gate_symbol}&interval={interval}&limit={limit}'
        data = safe_request(url)
        if isinstance(data, list):
            return [[int(k.get('t', 0)) * 1000, float(k.get('o', 0)), float(k.get('h', 0)), float(k.get('l', 0)), float(k.get('c', 0)), float(k.get('v', 0))] for k in data]
        return None
    except: return None

def get_klines_htx(symbol, interval, limit=200):
    try:
        mapping = {'1m': '1min', '3m': '3min', '5m': '5min', '15m': '15min', '30m': '30min', '1h': '60min', '4h': '4hour', '1d': '1day'}
        url = f'https://api.huobi.pro/market/history/kline?symbol={symbol.lower().replace("_","").replace("-","")}&period={mapping.get(interval, "60min")}&size={limit}'
        data = safe_request(url)
        if data.get('data'):
            return [[int(k.get('id', 0)) * 1000, float(k.get('open', 0)), float(k.get('high', 0)), float(k.get('low', 0)), float(k.get('close', 0)), float(k.get('vol', 0))] for k in reversed(data['data'])]
        return None
    except: return None

# --- Real-Time Ticker Fetchers (Highest Accuracy for Tracking) ---
# --- Optimized MEXC Cache ---
_mexc_detail_cache = {"data": None, "last_fetch": 0}

def get_ticker_mexc(symbol):
    global _mexc_detail_cache
    try:
        current_time = time.time()
        if not _mexc_detail_cache["data"] or current_time - _mexc_detail_cache["last_fetch"] > 10:
            d_data = safe_request('https://contract.mexc.com/api/v1/contract/detail')
            if d_data.get('success'):
                _mexc_detail_cache["data"] = {d['symbol']: d for d in d_data['data']}
                _mexc_detail_cache["last_fetch"] = current_time

        futures_symbol = symbol.replace('USDT', '_USDT') if 'USDT' in symbol and '_' not in symbol else symbol
        url_ticker = f'https://contract.mexc.com/api/v1/contract/ticker?symbol={futures_symbol}'
        t_data = safe_request(url_ticker)
        
        if t_data.get('success') and 'data' in t_data:
            last = float(t_data['data']['lastPrice'])
            fair = last
            if _mexc_detail_cache["data"] and futures_symbol in _mexc_detail_cache["data"]:
                fair = float(_mexc_detail_cache["data"][futures_symbol].get('fairPrice', last))
            return {'last': last, 'fair': fair, 'high': float(t_data['data']['high24h']), 'low': float(t_data['data']['low24h'])}
        
        clean_symbol = symbol.replace('_', '').upper()
        url_spot = f'https://api.mexc.com/api/v3/ticker/price?symbol={clean_symbol}'
        data = safe_request(url_spot)
        if 'price' in data:
            price = float(data['price'])
            return {'last': price, 'fair': price, 'high': price, 'low': price}
        return None
    except: return None

def get_ticker_binance(symbol):
    try:
        clean_symbol = symbol.replace('_', '').replace('-', '').upper()
        # 1. Futures Mark Price
        url = f'https://fapi.binance.com/fapi/v1/premiumIndex?symbol={clean_symbol}'
        data = safe_request(url)
        if 'markPrice' in data:
            # We also need LAST price to show in UI
            url_p = f'https://fapi.binance.com/fapi/v1/ticker/price?symbol={clean_symbol}'
            p_data = safe_request(url_p)
            last = float(p_data['price']) if 'price' in p_data else float(data['markPrice'])
            return {'last': last, 'fair': float(data['markPrice'])}
        
        url_spot = f'https://api.binance.com/api/v3/ticker/price?symbol={clean_symbol}'
        data = safe_request(url_spot)
        if 'price' in data:
            p = float(data['price'])
            return {'last': p, 'fair': p}
        return None
    except: return None

def get_ticker_bybit(symbol):
    try:
        clean_symbol = symbol.replace('_', '').replace('-', '').upper()
        url = f'https://api.bybit.com/v5/market/tickers?category=linear&symbol={clean_symbol}'
        data = safe_request(url)
        if data.get('result') and data['result'].get('list'):
            t = data['result']['list'][0]
            return {
                'last': float(t['lastPrice']),
                'fair': float(t.get('markPrice', t['lastPrice'])),
                'high': float(t['highPrice24h']),
                'low': float(t['lowPrice24h'])
            }
        return None
    except: return None

def get_ticker_okx(symbol):
    """Get ticker from OKX API with domain fallbacks"""
    try:
        okx_symbol = symbol.replace('_', '').replace('-', '')
        if 'USDT' in okx_symbol and '-' not in okx_symbol:
            okx_symbol = okx_symbol.replace('USDT', '-USDT-SWAP')
        
        domains = ['https://www.okx.com', 'https://www.okx.net', 'https://okx.com']
        for base in domains:
            try:
                url_t = f'{base}/api/v5/market/ticker?instId={okx_symbol}'
                url_m = f'{base}/api/v5/public/mark-price?instId={okx_symbol}'
                t_data = safe_request(url_t)
                m_data = safe_request(url_m)
                if t_data.get('data'):
                    t = t_data['data'][0]
                    fair = float(t['last'])
                    if m_data.get('data'):
                        fair = float(m_data['data'][0].get('markPrice', fair))
                    return {'last': float(t['last']), 'fair': fair, 'high': float(t['high24h']), 'low': float(t['low24h'])}
            except: continue
        return None
    except: return None

def get_ticker_bitget(symbol):
    try:
        clean_symbol = symbol.replace('_', '').replace('-', '').upper()
        url = f'https://api.bitget.com/api/v2/mix/market/ticker?productType=USDT-FUTURES&symbol={clean_symbol}'
        data = safe_request(url)
        if data.get('data'):
            t = data['data'][0]
            return {
                'last': float(t['lastPr']),
                'fair': float(t.get('bidPr', t['lastPr'])), # Bitget ticker lacks mark, usage of bid/ask common
                'high': float(t['high24h']),
                'low': float(t['low24h'])
            }
        return None
    except: return None

def get_ticker_kucoin(symbol):
    try:
        ku_symbol = symbol.replace('_', '').replace('-', '')
        if 'USDT' in ku_symbol and '-' not in ku_symbol:
            ku_symbol = ku_symbol.replace('USDT', '-USDT')
        url = f'https://api.kucoin.com/api/v1/market/orderbook/level1?symbol={ku_symbol}'
        data = safe_request(url)
        if data.get('data'):
            p = float(data['data']['price'])
            return {'last': p, 'fair': p}
        return None
    except: return None

def get_ticker_gateio(symbol):
    try:
        gate_symbol = symbol.replace('USDT', '_USDT') if 'USDT' in symbol and '_' not in symbol else symbol
        url = f'https://api.gateio.ws/api/v4/futures/usdt/tickers?contract={gate_symbol}'
        data = safe_request(url)
        if isinstance(data, list) and len(data) > 0:
            t = data[0]
            return {
                'last': float(t['last']),
                'fair': float(t.get('mark_price', t['last'])),
                'high': float(t['high_24h']),
                'low': float(t['low_24h'])
            }
        return None
    except: return None

def get_ticker_htx(symbol):
    try:
        url = f'https://api.huobi.pro/market/detail/merged?symbol={symbol.lower().replace("_","").replace("-","")}'
        data = safe_request(url)
        if data.get('tick'):
            p = float(data['tick']['close'])
            return {'last': p, 'fair': p, 'high': float(data['tick']['high']), 'low': float(data['tick']['low'])}
        return None
    except: return None

EXCHANGE_FETCHERS = {
    'MEXC': get_klines_mexc, 'BINANCE': get_klines_binance, 'BYBIT': get_klines_bybit,
    'BITGET': get_klines_bitget, 'OKX': get_klines_okx, 'KUCOIN': get_klines_kucoin,
    'GATEIO': get_klines_gateio, 'HTX': get_klines_htx
}

TICKER_FETCHERS = {
    'MEXC': get_ticker_mexc, 
    'BINANCE': get_ticker_binance,
    'BYBIT': get_ticker_bybit,
    'OKX': get_ticker_okx,
    'BITGET': get_ticker_bitget,
    'KUCOIN': get_ticker_kucoin,
    'GATEIO': get_ticker_gateio,
    'HTX': get_ticker_htx
}

class TradeTracker:
    def __init__(self):
        self.active_trades = []
        self.completed_trades = set() # Store (symbol, strategy, type) to prevent re-tracking
        self.lock = threading.Lock()
        self.exchange_prices = {}
        self.tracking_active = False

    def add_trade(self, trade):
        """Register a new trade for real-time tracking. Returns status: 'NEW', 'TRACKING', or 'COMPLETED'"""
        with self.lock:
            # unique_key for strict tracking (Isolated by Exchange)
            exch = str(trade.get('exchange', 'BINANCE')).upper()
            unique_key = (exch, trade['symbol'], trade['strategy'], trade['type'])
            
            # 1. Check if already completed in this session
            if unique_key in self.completed_trades:
                return 'COMPLETED'

            # 2. Check if already tracking this exact setup
            for t in self.active_trades:
                t_exch = str(t.get('exchange', 'BINANCE')).upper()
                if (t_exch, t['symbol'], t['strategy'], t['type']) == unique_key:
                    # NEW SCAN DATA RECEIVED...
                    old_sl = float(t.get('sl', 0))
                    new_sl = float(trade.get('sl', old_sl))
                    
                    # SELF-HEALING: Only resurrect if it was an SL_HIT and the new scan provides a SAFER (further) SL.
                    # CRITICAL: We NEVER resurrect a TP_HIT. Once target is hit, it's a win.
                    if t['tracking_status'] == 'SL_HIT' and abs(new_sl - old_sl) > 1e-9:
                        is_long = t['type'] == 'LONG'
                        is_safer = (new_sl < old_sl) if is_long else (new_sl > old_sl)
                        
                        if is_safer:
                            t['tracking_status'] = 'RUNNING'
                            t['is_frozen'] = False 
                            t['pnl_pct'] = 0.0 
                            if unique_key in self.completed_trades:
                                self.completed_trades.discard(unique_key)
                            print(f"🔄 RESURRECTION: {trade['symbol']} brought back to life! New Shielded SL is safer: {new_sl}")
                        else:
                            # If new SL is actually closer/worse, keep it hit.
                            pass

                    # SYNC LATEST VALUES
                    try:
                        t['sl'] = new_sl
                        t['tp1'] = float(trade.get('tp1', t['tp1']))
                        t['tp2'] = float(trade.get('tp2', t['tp2']))
                        # IMPORTANT: Do NOT overwrite entry, tracking_status, or registration_time
                    except: pass
                    return 'TRACKING', t['tracking_status']
            
            # Initial state already determined in caller or defaults here
            entry_type = str(trade.get('entry_type', 'MARKET')).upper()
            trade['entry_type'] = entry_type # Ensure it's stored for the update loop
            if 'tracking_status' not in trade:
                trade['tracking_status'] = 'RUNNING' if entry_type == 'MARKET' else 'WAITING'
            
            if 'registration_time' not in trade:
                trade['registration_time'] = time.time()

            trade['current_price'] = float(trade.get('entry', 0))
            trade['pnl_pct'] = 0.0
            trade['updated_at'] = datetime.now().strftime('%H:%M:%S')
            trade['entry_confirm_hits'] = 0 
            trade['entry_trigger_time'] = 0 # Track when it actually enters RUNNING
            trade['session_high'] = 0
            trade['session_low'] = 0
            
            self.active_trades.append(trade)
            status = trade['tracking_status']
            print(f"📡 Registered {trade['symbol']} ({entry_type}) as {status} (Entry: {trade['entry']})", flush=True)
            return 'NEW', status

    def _fetch_bulk_mexc(self):
        try:
            url = "https://contract.mexc.com/api/v1/contract/ticker"
            data = safe_request(url, timeout=5)
            if data and data.get('success'):
                prices = {}
                for t in data['data']:
                    raw_sym = t['symbol']  # e.g. BTC_USDT
                    clean_sym = raw_sym.replace('_', '')  # BTCUSDT
                    price_entry = {'last': float(t['lastPrice']), 'fair': float(t.get('fairPrice', t['lastPrice']))}
                    prices[clean_sym] = price_entry
                    prices[raw_sym] = price_entry  # Store both formats
                return prices
        except Exception as e:
            print(f"  ⚠ Bulk MEXC ticker error: {e}")
        return {}

    def _fetch_bulk_binance(self):
        try:
            # Futures prices (Mark price for SL accuracy)
            url_m = "https://fapi.binance.com/fapi/v1/premiumIndex"
            m_data = safe_request(url_m, timeout=5)
            # Spot prices (Fallback)
            url_s = "https://api.binance.com/api/v3/ticker/price"
            s_data = safe_request(url_s, timeout=5)
            
            prices = {}
            if isinstance(s_data, list):
                for p in s_data: prices[p['symbol']] = {'last': float(p['price']), 'fair': float(p['price'])}
            if isinstance(m_data, list):
                for p in m_data: 
                    sym = p['symbol']
                    fair = float(p['markPrice'])
                    last = prices.get(sym, {}).get('last', fair)
                    prices[sym] = {'last': last, 'fair': fair}
            return prices
        except Exception as e:
            print(f"  ⚠ Bulk Binance ticker error: {e}")
        return {}

    def _fetch_bulk_bybit(self):
        try:
            url = "https://api.bybit.com/v5/market/tickers?category=linear"
            data = safe_request(url, timeout=5)
            if data and data.get('result'):
                return {t['symbol']: {'last': float(t['lastPrice']), 'fair': float(t.get('markPrice', t['lastPrice']))} for t in data['result']['list']}
        except Exception as e:
            print(f"  ⚠ Bulk Bybit ticker error: {e}")
        return {}

    def _fetch_bulk_bitget(self):
        try:
            url = "https://api.bitget.com/api/v2/mix/market/ticker?productType=USDT-FUTURES"
            data = safe_request(url, timeout=5, retries=2)
            if data and data.get('data'):
                return {t['symbol']: {'last': float(t['lastPr']), 'fair': float(t.get('bidPr', t['lastPr']))} for t in data['data']}
        except Exception as e:
            # Silently handle Bitget errors - they're common due to SSL issues
            pass
        return {}

    def _fetch_bulk_okx(self):
        try:
            url = "https://www.okx.com/api/v5/market/tickers?instType=SWAP"
            data = safe_request(url, timeout=5)
            if data and data.get('data'):
                return {t['instId'].replace('-', '').replace('SWAP', ''): {'last': float(t['last']), 'fair': float(t['last'])} for t in data['data']}
        except Exception as e:
            print(f"  ⚠ Bulk OKX ticker error: {e}")
        return {}

    def _fetch_bulk_htx(self):
        try:
            url = "https://api.huobi.pro/market/tickers"
            data = safe_request(url, timeout=5)
            if data and data.get('data'):
                return {t['symbol'].upper(): {'last': float(t['close']), 'fair': float(t['close'])} for t in data['data']}
        except Exception as e:
            print(f"  ⚠ Bulk HTX ticker error: {e}")
        return {}

    def _fetch_bulk_kucoin(self):
        try:
            url = "https://api.kucoin.com/api/v1/market/allTickers"
            data = safe_request(url, timeout=5)
            if data and data.get('data') and data['data'].get('ticker'):
                return {t['symbol'].replace('-', '').upper(): {'last': float(t['last']), 'fair': float(t['last'])} for t in data['data']['ticker']}
        except Exception as e:
            print(f"  ⚠ Bulk KuCoin ticker error: {e}")
        return {}

    def _fetch_bulk_gateio(self):
        try:
            url = "https://api.gateio.ws/api/v4/futures/usdt/tickers"
            data = safe_request(url, timeout=5)
            if isinstance(data, list):
                return {t['contract'].replace('_', '').upper(): {'last': float(t['last']), 'fair': float(t.get('mark_price', t['last']))} for t in data}
        except Exception as e:
            print(f"  ⚠ Bulk Gate.io ticker error: {e}")
        return {}

    def get_price(self, exchange, symbol, bulk_cache=None):
        """Fetch real-time ticker price. Uses bulk_cache if available for unmatched performance."""
        clean_symbol = symbol.replace('_', '').replace('-', '').upper()
        exch = exchange.upper().replace(' ', '').replace('.', '')
        
        # 1. Use Global Bulk Cache if provided (with fallback key attempts)
        if bulk_cache and exch in bulk_cache:
            exch_cache = bulk_cache[exch]
            # Try multiple key formats to handle exchange-specific symbol formats
            for key_attempt in [clean_symbol, symbol, symbol.replace('USDT', '_USDT'), symbol.replace('-', '')]:
                if key_attempt in exch_cache:
                    p = exch_cache[key_attempt]
                    return {'close': p['last'], 'fair': p['fair'], 'high': p['last'], 'low': p['last'], 'is_ticker': True}

        try:
            ticker_func = TICKER_FETCHERS.get(exch)
            if ticker_func:
                ticker = ticker_func(symbol)
                if ticker:
                    return {
                        'close': ticker['last'],
                        'fair': ticker.get('fair', ticker['last']), 
                        'high': ticker['last'], # Use last price for high/low to avoid 24h extreme contamination
                        'low': ticker['last'],
                        'is_ticker': True
                    }
            # Fallback...
            fetcher = EXCHANGE_FETCHERS.get(exch)
            if not fetcher: return None
            klines = fetcher(symbol, '1m', limit=1)
            if klines and len(klines) > 0:
                k = klines[-1]
                return {
                    'close': float(k[4]),
                    'fair': float(k[4]), 
                    'high': float(k[2]),
                    'low': float(k[3]),
                    'is_ticker': False
                }
            return None
        except: return None
    def update_loop(self):
        """Background loop to update all active signals"""
        self.tracking_active = True
        print("💡 Trade Tracking Loop Started", flush=True)
        last_heartbeat = 0
        while self.tracking_active:
            eventlet.sleep(0.01) # Yield to eventlet hub
            loop_start = time.time()
            try:
                current_time = loop_start
                # 1. Snapshot of what needs updating (minimize lock time)
                with self.lock:
                    if not self.active_trades:
                        if current_time - last_heartbeat > 10:
                            print("😴 Tracking loop idle (no active trades)", flush=True)
                            last_heartbeat = current_time
                        time.sleep(2)
                        continue
                    current_trades = list(self.active_trades)

                if current_time - last_heartbeat > 10:
                    print(f"💓 Tracking heartbeat: {len(current_trades)} active trades", flush=True)
                    last_heartbeat = current_time

                # 1. Institutional Bulk Sync
                bulk_cache = {}
                active_exchanges = set(t.get('exchange', 'BINANCE').upper() for t in current_trades if t['tracking_status'] in ['WAITING', 'RUNNING'])
                
                def fetch_bulk(exch):
                    if exch == 'BINANCE': return exch, self._fetch_bulk_binance()
                    if exch == 'MEXC': return exch, self._fetch_bulk_mexc()
                    if exch == 'BYBIT': return exch, self._fetch_bulk_bybit()
                    if exch == 'BITGET': return exch, self._fetch_bulk_bitget()
                    if exch == 'OKX': return exch, self._fetch_bulk_okx()
                    if exch == 'HTX': return exch, self._fetch_bulk_htx()
                    if exch == 'KUCOIN': return exch, self._fetch_bulk_kucoin()
                    if exch == 'GATEIO': return exch, self._fetch_bulk_gateio()
                    return exch, {}

                with ThreadPoolExecutor(max_workers=max(1, len(active_exchanges))) as executor:
                    futures = [executor.submit(fetch_bulk, exch) for exch in active_exchanges]
                    for future in as_completed(futures):
                        exch, data = future.result()
                        if data: bulk_cache[exch.replace('.', '').replace(' ', '')] = data

                # 2. Map trades to pricing
                targets_map = {}
                for t in current_trades:
                    if t['tracking_status'] in ['WAITING', 'RUNNING']:
                        exch = str(t.get('exchange', 'BINANCE')).upper().replace(' ', '').replace('.', '')
                        key = (exch, t['symbol'])
                        targets_map[key] = None

                # 3. Resolve prices (Cache-first then parallel single fallback)
                with ThreadPoolExecutor(max_workers=60) as executor:
                    future_to_key = {executor.submit(self.get_price, key[0], key[1], bulk_cache): key for key in targets_map}
                    try:
                        for future in as_completed(future_to_key, timeout=4.0):
                            key = future_to_key[future]
                            targets_map[key] = future.result()
                    except: pass

                # 3. Apply updates (Brief lock)
                with self.lock:
                    for t in self.active_trades:
                        # STRICT EXCHANGE MATCH
                        exch = str(t.get('exchange', 'BINANCE')).upper()
                        price_data = targets_map.get((exch, t['symbol']))
                        if not price_data or not isinstance(price_data, dict): continue

                        price = price_data['close']
                        fair_price = price_data.get('fair', price) # Mark/Fair price for stop verification
                        
                        # --- Arbiter 2.0: Instant Recovery for False Hits ---
                        # STRICT: Only recover if price is SIGNIFICANTLY far from SL now (0.5% buffer)
                        if t['tracking_status'] == 'SL_HIT' and not t.get('resurrected'):
                            sl_p = float(t['sl'])
                            is_long = t['type'] == 'LONG'
                            recovery_margin = 0.005 # 0.5% safety zone
                            
                            recovered = False
                            if is_long and fair_price > sl_p * (1 + recovery_margin):
                                recovered = True
                            elif not is_long and fair_price < sl_p * (1 - recovery_margin):
                                recovered = True
                                
                            if recovered:
                                t['tracking_status'] = 'RUNNING'
                                t['is_frozen'] = False
                                t['sl_hit_count'] = 0
                                t['resurrected'] = True # Only allow auto-recovery once per trade
                                print(f"🪄 [RECOVERY] {t['symbol']} recovered from False SL! Current Price: {fair_price}")

                        if t.get('is_frozen'): 
                            t_exch = str(t.get('exchange', 'BINANCE')).upper()
                            unique_key = (t_exch, t['symbol'], t['strategy'], t['type'])
                            self.completed_trades.add(unique_key)
                            continue
                        
                        t['current_price'] = price
                        high = price_data['high']
                        low = price_data['low']

                        # Ensure numeric
                        try:
                            entry_price = float(t['entry'])
                            tp_price = float(t['tp1'])
                            sl_price = float(t['sl'])
                        except: continue

                        t['current_price'] = price
                        t['updated_at'] = datetime.now().strftime('%H:%M:%S')

                        # Track session extremes for accurate SL/TP checking
                        if t.get('tracking_status') == 'RUNNING':
                            if t.get('session_high', 0) == 0: t['session_high'] = price
                            if t.get('session_low', 0) == 0: t['session_low'] = price
                            t['session_high'] = max(t['session_high'], price)
                            t['session_low'] = min(t['session_low'], price)

                        # Calculate PnL
                        if t['type'] == 'LONG':
                            t['pnl_pct'] = ((price - entry_price) / entry_price) * 100
                            
                            if t['tracking_status'] == 'WAITING':
                                # Check entry immediately without delay
                                    
                                entry_type = str(t.get('entry_type', 'MARKET')).upper()
                                at_limit = False
                                
                                if entry_type == 'MARKET':
                                    at_limit = True
                                elif entry_type == 'LIMIT':
                                    if price <= entry_price * 1.0005: at_limit = True
                                elif entry_type in ['STOP-MARKET', 'STOP_LIMIT', 'STOP']:
                                    if price >= entry_price * 0.9995: at_limit = True
                                
                                if at_limit:
                                    t['entry_confirm_hits'] = t.get('entry_confirm_hits', 0) + 1
                                else:
                                    t['entry_confirm_hits'] = 0
                                    
                                if t['entry_confirm_hits'] >= 1: # Reduced to 1 hit for responsive entry
                                    t['tracking_status'] = 'RUNNING'
                                    t['entry_time'] = datetime.now().strftime('%H:%M:%S')
                                    t['entry_trigger_time'] = time.time()
                                    t['session_high'] = price
                                    t['session_low'] = price
                                    print(f"🚀 [ENTRY TRIGGERED] {t['symbol']} LONG at {price} ({entry_type} Entry: {entry_price})", flush=True)
                            
                            elif t['tracking_status'] == 'RUNNING':
                                # GRACE PERIOD: 5 seconds after ENTRY to avoid initial noise
                                base_trigger_time = t.get('entry_trigger_time', 0) or t.get('registration_time', 0)
                                if time.time() - base_trigger_time < 5:
                                    continue
                                
                                if price <= 0 or fair_price <= 0:
                                    continue

                                # SL Check: Must be below SL for X ticks (Double-Lock with fair_price)
                                noise_buffer = (t.get('atr', 0) * 0.2)
                                shielded_sl = sl_price - noise_buffer
                                trigger_price = min(price, fair_price) if price_data.get('is_ticker') else low
                                if trigger_price <= 0: continue

                                hits = t.get('sl_hit_count', 0)
                                if trigger_price <= shielded_sl:
                                    hits += 1
                                    t['sl_hit_count'] = hits
                                else:
                                    t['sl_hit_count'] = 0

                                sl_threshold = 4 if t.get('timeframe', '1h') in ['1m', '3m', '5m'] else 3
                                if hits >= sl_threshold:
                                    t['tracking_status'] = 'SL_HIT'
                                    t['is_frozen'] = True 
                                    t['pnl_pct'] = ((sl_price - entry_price) / entry_price) * 100
                                    t['reason'] = f"{t.get('reason', '')} | [🛑 SL HIT AT {trigger_price}]"
                                    exch = str(t.get('exchange', 'BINANCE')).upper()
                                    self.completed_trades.add((exch, t['symbol'], t['strategy'], t['type']))
                                    print(f"🛑 [SL HIT] {t['symbol']} LONG at {trigger_price} (Shielded SL: {shielded_sl:.6f})", flush=True)
                                
                                # TP Check using Session High / Candle High
                                elif (t.get('session_high', price) if price_data.get('is_ticker') else high) >= tp_price:
                                    t['tracking_status'] = 'TP_HIT'
                                    t['is_frozen'] = True
                                    t['pnl_pct'] = ((tp_price - entry_price) / entry_price) * 100
                                    t['reason'] = f"{t.get('reason', '')} | [💰 TP HIT AT {t.get('session_high', price)}]"
                                    exch = str(t.get('exchange', 'BINANCE')).upper()
                                    self.completed_trades.add((exch, t['symbol'], t['strategy'], t['type']))
                                    print(f"💰 [TP HIT] {t['symbol']} LONG at {tp_price}", flush=True)
                        
                        else:  # SHORT
                            t['pnl_pct'] = ((entry_price - price) / entry_price) * 100
                            
                            if t['tracking_status'] == 'WAITING':
                                # Check entry immediately without delay
                                    
                                entry_type = str(t.get('entry_type', 'MARKET')).upper()
                                at_limit = False
                                
                                if entry_type == 'MARKET':
                                    at_limit = True
                                elif entry_type == 'LIMIT':
                                    if price >= entry_price * 0.9995: at_limit = True
                                elif entry_type in ['STOP-MARKET', 'STOP_LIMIT', 'STOP']:
                                    if price <= entry_price * 1.0005: at_limit = True
                                        
                                if at_limit:
                                    t['entry_confirm_hits'] = t.get('entry_confirm_hits', 0) + 1
                                else:
                                    t['entry_confirm_hits'] = 0

                                if t['entry_confirm_hits'] >= 1: # Reduced to 1 hit for responsive entry
                                    t['tracking_status'] = 'RUNNING'
                                    t['entry_time'] = datetime.now().strftime('%H:%M:%S')
                                    t['entry_trigger_time'] = time.time()
                                    t['session_high'] = price
                                    t['session_low'] = price
                                    print(f"🚀 [ENTRY TRIGGERED] {t['symbol']} SHORT at {price} ({entry_type} Entry: {entry_price})", flush=True)

                            elif t['tracking_status'] == 'RUNNING':
                                # GRACE PERIOD: 5 seconds after ENTRY
                                base_trigger_time = t.get('entry_trigger_time', 0) or t.get('registration_time', 0)
                                if time.time() - base_trigger_time < 5:
                                    continue
                                    
                                if price <= 0 or fair_price <= 0:
                                    continue

                                # SL Check: Must be above SL for X ticks
                                noise_buffer = (t.get('atr', 0) * 0.2)
                                shielded_sl = sl_price + noise_buffer
                                trigger_price = max(price, fair_price) if price_data.get('is_ticker') else high
                                if trigger_price <= 0: continue
                                
                                hits = t.get('sl_hit_count', 0)
                                if trigger_price >= shielded_sl:
                                    hits += 1
                                    t['sl_hit_count'] = hits
                                else:
                                    t['sl_hit_count'] = 0 
                                
                                sl_threshold = 4 if t.get('timeframe', '1h') in ['1m', '3m', '5m'] else 3
                                if hits >= sl_threshold:
                                    t['tracking_status'] = 'SL_HIT'
                                    t['is_frozen'] = True
                                    t['pnl_pct'] = ((entry_price - sl_price) / entry_price) * 100
                                    t['reason'] = f"{t.get('reason', '')} | [🛑 SL HIT AT {trigger_price}]"
                                    exch = str(t.get('exchange', 'BINANCE')).upper()
                                    self.completed_trades.add((exch, t['symbol'], t['strategy'], t['type']))
                                    print(f"🛑 [SL HIT] {t['symbol']} SHORT at {trigger_price} (Shielded SL: {shielded_sl:.6f})", flush=True)
                                
                                # TP Check for SHORT (using Session Low or Candle Low)
                                elif (t.get('session_low', price) if price_data.get('is_ticker') else low) <= tp_price:
                                    t['tracking_status'] = 'TP_HIT'
                                    t['is_frozen'] = True
                                    t['pnl_pct'] = ((entry_price - tp_price) / entry_price) * 100
                                    t['reason'] = f"{t.get('reason', '')} | [💰 TP HIT AT {t.get('session_low', price)}]"
                                    exch = str(t.get('exchange', 'BINANCE')).upper()
                                    self.completed_trades.add((exch, t['symbol'], t['strategy'], t['type']))
                                    print(f"💰 [TP HIT] {t['symbol']} SHORT at {tp_price}", flush=True)

                    # Broadcast
                    socketio.emit('tracking_update', self.active_trades, namespace='/')

                # 4. Drift-Corrected Sleep to maintain 1s frequency
                elapsed = time.time() - loop_start
                sleep_time = max(0.1, 1.0 - elapsed)
                time.sleep(sleep_time)
            except Exception as e:
                print(f"Tracking error: {e}")
                time.sleep(3)

    def export_to_csv(self):
        """Save current session trades to CSV before starting next analysis"""
        with self.lock:
            if not self.active_trades:
                return
            
            filename = f"trade_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            keys = self.active_trades[0].keys()
            
            try:
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    dict_writer = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
                    dict_writer.writeheader()
                    dict_writer.writerows(self.active_trades)
                
                print(f"📊 Exported {len(self.active_trades)} trades to {filename}")
                self.active_trades = [] # Reset for next analysis
            except Exception as e:
                print(f"Failed to export CSV: {e}")

# Global instances
trade_tracker = TradeTracker()

# Session State Management
# Format: { 'sid': { 'process': subprocess.Popen, 'thread': threading.Thread, 'active': bool } }
client_sessions = {}

# Global config (still used for defaults and auto-run)
config = {
    'symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT'],
    'indicators': ['RSI', 'EMA', 'MACD', 'BB', 'ATR', 'ADX', 'OB', 'PA', 'StochRSI', 'OBV', 'ST', 'VWAP', 'HMA', 'CMF', 'ICHI', 'FVG', 'DIV', 'WT', 'SQZ', 'LIQ', 'BOS', 'MFI', 'FISH', 'ZLSMA', 'TSI', 'CHOP', 'VI', 'STC', 'DON', 'CHoCH', 'KC', 'UTBOT', 'UO', 'STDEV', 'VP', 'SUPDEM', 'FIB', 'ICT_WD', 'PSAR', 'TEMA', 'CHANDELIER', 'KAMA', 'VFI', 'REGIME', 'DELTA', 'ZSCORE', 'WYCKOFF', 'RVOL'],
    'min_confidence': 5,
    'timeframes': ['1m', '3m', '5m', '15m', '30m', '1h', '4h', '1d'],
    'exchanges': ['MEXC', 'BINANCE', 'BYBIT', 'OKX', 'BITGET', 'KUCOIN', 'GATEIO', 'HTX'],
    'strategies': ['SWING', 'SCALP', 'STOCH_PULLBACK', 'BB_BREAKOUT', 'SUPERTREND_FOLLOW', 'VWAP_REVERSION', 'ICHIMOKU_TK', 'FVG_GAP_FILL', 'DIVERGENCE_PRO', 'ADX_MOMENTUM', 'BOLLINGER_REVERSION', 'LIQUIDITY_GRAB', 'WAVETREND_EXTREME', 'SQUEEZE_BREAKOUT', 'ZLSMA_FAST_SCALP', 'MFI_REVERSION', 'FISHER_TRANSFORM', 'VOLUME_SPIKE', 'QUANTUM_CONFLUENCE', 'SMC_ELITE', 'HARMONIC_PRO', 'SMC_CHOCH', 'DONCHIAN_BREAKOUT', 'STC_MOMENTUM', 'VORTEX_TREND', 'ICT_SILVER_BULLET', 'UTBOT_ELITE', 'KELTNER_REVERSION', 'VOLATILITY_CAPITULATION', 'MOMENTUM_CONFLUENCE', 'ICT_WEALTH_DIVISION', 'HARMONIC_GARTLEY', 'PSAR_TEMA_SCALP', 'KAMA_VOLATILITY_SCALP', 'VFI_MOMENTUM_SCALP', 'REGIME_ADAPTIVE', 'WYCKOFF_SPRING', 'TRIPLE_CONFLUENCE', 'ZSCORE_REVERSION', 'MTF_TREND_RIDER', 'SMART_MONEY_TRAP', 'MOMENTUM_EXHAUSTION'],
    'auto_run': False,
    'auto_run_interval': 300,
    'risk_profile': 'moderate',
    'telegram_token': '',
    'telegram_chat_id': ''
}

def send_telegram_alert(trade):
    """Send trade alert to Telegram if configured"""
    token = config.get('telegram_token')
    chat_id = config.get('telegram_chat_id')
    if not token or not chat_id: return
    
    action = "🚀 BUY" if trade['type'] == 'LONG' else "🔻 SELL"
    msg = f"""🔥 *[RBot Pro] TRADE ALERT*
━━━━━━━━━━━━━━━━━━━━
🏢 *Exchange:* {trade.get('exchange', 'N/A')}
📈 *Signal:* {action} {trade['symbol']} ({trade['timeframe']})
📍 *Entry:* ${trade['entry']:.6f}
🛑 *SL:* ${trade['sl']:.6f}
🎯 *TP:* ${trade['tp1']:.6f}
💎 *R/R:* {trade['risk_reward']}:1
🔍 *Reason:* {trade['reason']}
━━━━━━━━━━━━━━━━━━━━
*by RBot Pro — World's Best AI Bot!* 🏆"""
    
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={
            "chat_id": chat_id,
            "text": msg,
            "parse_mode": "Markdown"
        }, timeout=5)
    except Exception as e:
        print(f"Telegram error: {e}")

def execute_auto_trade(trade, sid=None):
    """Execute trade via RealTrader and notify client"""
    try:
        # Run in a separate thread inside here if caller didn't thread it, 
        # but better to assume caller threads it.
        result = real_trader.execute_trade(trade)
        
        if result['status'] == 'success':
            msg = f"✅ [AUTO-TRADE] Executed {trade['symbol']} on {trade['exchange']} | ID: {result['order']['id']}"
            print(msg)
            # Update trade status to reflect real execution if desired
            # event = {'type': 'success', 'msg': msg}
            if sid: 
                socketio.emit('output', {'data': msg + '\n'}, room=sid, namespace='/')
            else:
                socketio.emit('output', {'data': msg + '\n'}, namespace='/')
                
        elif result['status'] == 'error':
            msg = f"❌ [AUTO-TRADE] Failed {trade['symbol']}: {result['msg']}"
            print(msg)
            if sid:
                socketio.emit('output', {'data': msg + '\n'}, room=sid, namespace='/')
            else:
                socketio.emit('output', {'data': msg + '\n'}, namespace='/')
                
        elif result['status'] == 'skipped':
            # silent skip
            pass
            
    except Exception as e:
        print(f"Auto-Trade Execution Error: {e}")

def market_monitor_loop():
    """Background thread to monitor market news and volatility"""
    last_news_time = 0
    while True:
        try:
            current_time = time.time()
            
            # check volatility every 5 seconds
            try:
                news_manager.check_btc_volatility()
            except:
                pass  # Silently handle volatility check errors
            
            # fetch news every 5 seconds
            if current_time - last_news_time >= 5:
                try:
                    news_manager.fetch_news()
                    last_news_time = current_time
                except:
                    pass  # Silently handle news fetch errors
                
            # Broadcast status to ALL clients
            try:
                status = news_manager.get_market_status()
                socketio.emit('market_status', status, namespace='/')
            except:
                pass  # Silently handle broadcast errors
            
            eventlet.sleep(2) # Green-thread friendly sleep
            
        except Exception as e:
            print(f"Market Monitor Error: {e}")
            time.sleep(10)

def run_session_analysis(sid, symbols, indicators, timeframes, min_conf, exchanges, strategies):
    """Run analysis for a specific session"""
    print(f"🚀 Starting analysis for session {sid}")
    
    try:
        cmd = [
            sys.executable, 'fast_analysis.py',
            '--symbols', ','.join(symbols),
            '--indicators', ','.join(indicators),
            '--timeframes', ','.join(timeframes),
            '--min-confidence', str(min_conf),
            '--exchanges', ','.join([e.upper() for e in exchanges]),
            '--strategies', ','.join(strategies)
        ]
        
        # Send start message to specific room (sid)
        socketio.emit('output', {'data': f"🚀 Running: {' '.join(cmd)}\n"}, room=sid, namespace='/')
        
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUNBUFFERED'] = '1'
        
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, # Merge stderr into stdout
            text=True,
            encoding='utf-8',
            bufsize=1,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            env=env
        )

        # Store process handle
        if sid in client_sessions:
            client_sessions[sid]['process'] = proc
            client_sessions[sid]['active'] = True
        
        # Stream output
        for line in iter(proc.stdout.readline, ''):
            if line:
                if line.startswith('SIGNAL_DATA:'):
                    try:
                        signal_str = line.split('SIGNAL_DATA:')[1].strip()
                        signal_data = json.loads(signal_str)
                        
                        # INJECT MARKET WARNING IF EXISTS
                        status = news_manager.get_market_status()
                        # 1. Add/Update tracker FIRST to get stable state
                        track_status, current_tracking_status = trade_tracker.add_trade(signal_data)
                        
                        # 2. Sync signal_data for emission (Must match tracker's reality)
                        signal_data['tracking_status'] = current_tracking_status
                        if 'registration_time' not in signal_data:
                            signal_data['registration_time'] = time.time()

                        # 3. Handle UI update
                        # Check if this is a post-processed signal (has agreeing_strategies_details)
                        is_final_merged = 'agreeing_strategies_details' in signal_data
                        
                        if track_status == 'NEW' or is_final_merged:
                            # Emit NEW signals immediately for quick feedback
                            # Also emit FINAL merged signals to update cards with complete details
                            socketio.emit('trade_signal', signal_data, room=sid, namespace='/')
                            
                            # Only send Telegram/Auto-trade for NEW signals (not updates)
                            if track_status == 'NEW':
                                # Forward to Telegram
                                thread = threading.Thread(target=send_telegram_alert, args=(signal_data,), daemon=True)
                                thread.start()
                                
                                # Execute Auto-Trade
                                thread_trade = threading.Thread(target=execute_auto_trade, args=(signal_data, sid), daemon=True)
                                thread_trade.start()
                        else:
                            # For existing signals without final data, don't re-emit
                            # Usually tracking_update handles the live updates
                            pass
                    except Exception as e:
                        print(f"Error processing trade signal: {e}")
                    continue
                
                # Emit standard output line to session
                socketio.emit('output', {'data': line}, room=sid, namespace='/')
                # Yield control to event loop to keep heartbeats alive
                socketio.sleep(0)
        
        # Process finished
        if sid in client_sessions and client_sessions[sid]['active']:
             socketio.emit('output', {'data': "\n✅ Analysis completed\n"}, room=sid, namespace='/')
             socketio.emit('status', {'status': 'completed'}, room=sid, namespace='/')
             client_sessions[sid]['active'] = False
             client_sessions[sid]['process'] = None

    except Exception as e:
        error_msg = str(e)
        if 'killed' not in error_msg.lower() and 'terminated' not in error_msg.lower():
            socketio.emit('output', {'data': f"❌ ERROR: {error_msg}\n"}, room=sid, namespace='/')
            socketio.emit('status', {'status': 'error'}, room=sid, namespace='/')
    finally:
        if sid in client_sessions:
            client_sessions[sid]['active'] = False


def auto_run_analysis():
    """Auto-run analysis on schedule - Runs as a background 'system' task"""
    print(f"🤖 Auto-run triggered at {datetime.now().strftime('%H:%M:%S')}")
    socketio.emit('status', {'status': 'auto_triggered'}, namespace='/')
    
    def _run_auto():
        try:
            cmd = [
                sys.executable, 'fast_analysis.py',
                '--symbols', ','.join(config['symbols']),
                '--indicators', ','.join(config['indicators']),
                '--timeframes', ','.join(config['timeframes']),
                '--min-confidence', str(config['min_confidence']),
                '--exchanges', ','.join(config.get('exchanges', ['MEXC', 'BINANCE', 'BYBIT', 'OKX', 'BITGET', 'KUCOIN', 'GATEIO', 'HTX'])),
                '--strategies', ','.join(config.get('strategies', []))
            ]
            
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            env['PYTHONUNBUFFERED'] = '1'
            
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                bufsize=1,
                cwd=os.path.dirname(os.path.abspath(__file__)),
                env=env
            )
            
            for line in iter(proc.stdout.readline, ''):
                if line and line.startswith('SIGNAL_DATA:'):
                    try:
                        signal_str = line.split('SIGNAL_DATA:')[1].strip()
                        signal_data = json.loads(signal_str)
                        
                        # INJECT MARKET WARNING IF EXISTS
                        status = news_manager.get_market_status()
                        if status.get('volatility_warning'):
                            signal_data['warning'] = status['volatility_warning']
                        if status.get('news_warning'):
                            signal_data['warning'] = f"{signal_data.get('warning', '')} {status['news_warning']}"
                        
                        # Register with GLOBAL tracker
                        track_status = trade_tracker.add_trade(signal_data)
                        
                        if track_status != 'COMPLETED':
                            # GLOBAL BROADCAST for auto-runs
                            socketio.emit('trade_signal', signal_data, namespace='/')
                        
                        # Telegram if NEW
                        if track_status == 'NEW':
                            thread = threading.Thread(target=send_telegram_alert, args=(signal_data,), daemon=True)
                            thread.start()
                            
                            # Execute Auto-Trade
                            thread_trade = threading.Thread(target=execute_auto_trade, args=(signal_data, None), daemon=True)
                            thread_trade.start()
                    except:
                        pass
                # Yield control to event loop
                socketio.sleep(0)
                        
            proc.wait()
            print("✅ Auto-run completed")
            
        except Exception as e:
            print(f"Auto-run error: {e}")

    thread = threading.Thread(target=_run_auto, daemon=True)
    thread.start() 

@app.route('/')
def index():
    """Serve main UI"""
    return render_template('ui.html')

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration"""
    return jsonify(config)

@app.route('/api/config', methods=['POST'])
def update_config():
    """Update configuration"""
    global config
    data = request.json or {}
    
    if 'symbols' in data:
        config['symbols'] = data['symbols']
    if 'indicators' in data:
        config['indicators'] = data['indicators']
    if 'timeframes' in data:
        config['timeframes'] = data['timeframes']
    if 'min_confidence' in data:
        config['min_confidence'] = data['min_confidence']
    if 'exchanges' in data:
        config['exchanges'] = data['exchanges']
    if 'strategies' in data:
        config['strategies'] = data['strategies']
    if 'auto_run' in data:
        config['auto_run'] = data['auto_run']
        update_scheduler()
        if config['auto_run']:
            # Trigger immediately for better UX
            auto_run_analysis()
        else:
            # Stop analysis for all sessions (optional, or just stop scheduler)
            pass
    if 'auto_run_interval' in data:
        config['auto_run_interval'] = data['auto_run_interval']
        update_scheduler()
    if 'risk_profile' in data:
        config['risk_profile'] = data['risk_profile']
    if 'telegram_token' in data:
        config['telegram_token'] = data['telegram_token']
    if 'telegram_chat_id' in data:
        config['telegram_chat_id'] = data['telegram_chat_id']
    
    socketio.emit('config_updated', config, namespace='/')
    return jsonify({'status': 'ok', 'config': config})

@app.route('/api/available-coins', methods=['GET'])
def get_available_coins():
    """Get top 100 coins from EACH selected exchange in parallel, then merge and deduplicate"""
    print("📡 Fetching top coins from all exchanges in parallel...")
    default_top = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT']
    all_coins_set = set(default_top)
    
    selected_exchanges = [e.upper() for e in config.get('exchanges', [])]
    if not selected_exchanges:
        selected_exchanges = ['MEXC', 'BINANCE', 'BYBIT', 'OKX', 'BITGET', 'KUCOIN', 'GATEIO', 'HTX']
    
    n = 200 # Top 200 per exchange
    coin_timeout = 8 # Tight timeout for web-speed loading

    def fetch_mexc():
        coins = set()
        try:
            data = safe_request('https://contract.mexc.com/api/v1/contract/detail', timeout=coin_timeout)
            if data.get('success') and isinstance(data.get('data'), list):
                contracts = [c for c in data['data'] if c.get('symbol', '').endswith('_USDT')]
                contracts_sorted = sorted(contracts, key=lambda x: float(x.get('last24hVol', 0)), reverse=True)
                for item in contracts_sorted[:n]:
                    sym = item.get('symbol', '')
                    coins.add(sym.replace('_', ''))
        except Exception as e: print(f"  ⚠ MEXC Coin Fetch Error: {e}")
        return 'MEXC', coins

    def fetch_binance():
        coins = set()
        try:
            data = safe_request('https://api.binance.com/api/v3/ticker/24hr', timeout=coin_timeout)
            usdt_pairs = [item for item in data if item.get('symbol', '').endswith('USDT') and not item['symbol'].endswith('UPUSDT') and not item['symbol'].endswith('DOWNUSDT')]
            binance_sorted = sorted(usdt_pairs, key=lambda x: float(x.get('quoteVolume', 0)), reverse=True)
            for item in binance_sorted[:n]:
                coins.add(item['symbol'])
        except Exception as e: print(f"  ⚠ Binance Coin Fetch Error: {e}")
        return 'BINANCE', coins

    def fetch_bybit():
        coins = set()
        try:
            data = safe_request('https://api.bybit.com/v5/market/tickers?category=linear', timeout=coin_timeout)
            if data.get('result') and data['result'].get('list'):
                usdt_pairs = [item for item in data['result']['list'] if item.get('symbol', '').endswith('USDT')]
                bybit_sorted = sorted(usdt_pairs, key=lambda x: float(x.get('turnover24h', 0)), reverse=True)
                for item in bybit_sorted[:n]:
                    coins.add(item['symbol'])
        except Exception as e: print(f"  ⚠ Bybit Coin Fetch Error: {e}")
        return 'BYBIT', coins

    def fetch_bitget():
        coins = set()
        try:
            data = safe_request('https://api.bitget.com/api/v2/mix/market/tickers?productType=USDT-FUTURES', timeout=coin_timeout)
            if data.get('data'):
                bitget_sorted = sorted(data['data'], key=lambda x: float(x.get('usdtVolume', 0)), reverse=True)
                for item in bitget_sorted[:n]:
                    sym = item.get('symbol', '')
                    if sym.endswith('USDT'):
                        coins.add(sym)
        except Exception as e: print(f"  ⚠ Bitget Coin Fetch Error: {e}")
        return 'BITGET', coins

    def fetch_okx():
        coins = set()
        try:
            domains = ['https://www.okx.com', 'https://www.okx.net']
            for base in domains:
                try:
                    data = safe_request(f'{base}/api/v5/market/tickers?instType=SWAP', timeout=coin_timeout)
                    if data.get('data'):
                        okx_sorted = sorted(data['data'], key=lambda x: float(x.get('vol24h', 0)), reverse=True)
                        for item in okx_sorted[:n]:
                            inst_id = item.get('instId', '')
                            if '-USDT-' in inst_id:
                                sym = inst_id.split('-USDT-')[0] + 'USDT'
                                coins.add(sym)
                        return 'OKX', coins
                except: continue
        except Exception as e: print(f"  ⚠ OKX Coin Fetch Error: {e}")
        return 'OKX', coins

    def fetch_kucoin():
        coins = set()
        try:
            data = safe_request('https://api.kucoin.com/api/v1/market/allTickers', timeout=coin_timeout)
            if data.get('data') and data['data'].get('ticker'):
                usdt_pairs = [item for item in data['data']['ticker'] if item.get('symbol', '').endswith('-USDT')]
                kucoin_sorted = sorted(usdt_pairs, key=lambda x: float(x.get('volValue', 0)), reverse=True)
                for item in kucoin_sorted[:n]:
                    sym = item.get('symbol', '')
                    coins.add(sym.replace('-', ''))
        except Exception as e: print(f"  ⚠ KuCoin Coin Fetch Error: {e}")
        return 'KUCOIN', coins

    def fetch_gateio():
        coins = set()
        try:
            data = safe_request('https://api.gateio.ws/api/v4/futures/usdt/tickers', timeout=coin_timeout)
            gate_sorted = sorted(data, key=lambda x: float(x.get('volume_24h_quote', 0)), reverse=True)
            for item in gate_sorted[:n]:
                sym = item.get('contract', '')
                if sym.endswith('_USDT'):
                    coins.add(sym.replace('_', ''))
        except Exception as e: print(f"  ⚠ Gate.io Coin Fetch Error: {e}")
        return 'GATEIO', coins

    def fetch_htx():
        coins = set()
        try:
            data = safe_request('https://api.huobi.pro/market/tickers', timeout=coin_timeout)
            if data.get('data'):
                usdt_pairs = [item for item in data['data'] if item.get('symbol', '').endswith('usdt')]
                htx_sorted = sorted(usdt_pairs, key=lambda x: float(x.get('vol', 0)), reverse=True)
                for item in htx_sorted[:n]:
                    sym = item.get('symbol', '').upper()
                    coins.add(sym)
        except Exception as e: print(f"  ⚠ HTX Coin Fetch Error: {e}")
        return 'HTX', coins

    fetchers = {
        'MEXC': fetch_mexc,
        'BINANCE': fetch_binance,
        'BYBIT': fetch_bybit,
        'BITGET': fetch_bitget,
        'OKX': fetch_okx,
        'KUCOIN': fetch_kucoin,
        'GATEIO': fetch_gateio,
        'HTX': fetch_htx
    }

    with ThreadPoolExecutor(max_workers=len(selected_exchanges)) as ex:
        futures = {ex.submit(fetchers[exch]): exch for exch in selected_exchanges if exch in fetchers}
        for fut in as_completed(futures):
            exch_name, coins = fut.result()
            if coins:
                all_coins_set.update(coins)
                print(f"  ✨ {exch_name}: Added {len(coins)} top coins")
    
    if not all_coins_set:
        return jsonify({'coins': default_top})
    
    final_list = sorted(list(all_coins_set))
    print(f"✅ Loaded {len(final_list)} unique coins from {len(selected_exchanges)} exchanges (Top 200 scan).")
    return jsonify({'coins': final_list})

@socketio.on('connect', namespace='/')
def handle_connect():
    """Client connected"""
    sid = request.sid
    print(f"Client connected: {sid}")
    client_sessions[sid] = {'active': False, 'process': None}
    emit('status', {'status': 'connected', 'config': config})
    emit('output', {'data': f'✓ Connected at {datetime.now().strftime("%H:%M:%S")}\n'})

@socketio.on('disconnect', namespace='/')
def handle_disconnect():
    """Client disconnected"""
    sid = request.sid
    print(f"Client disconnected: {sid}")
    
    # Optional: Kill process on disconnect to save resources
    if sid in client_sessions:
        if client_sessions[sid]['active'] and client_sessions[sid]['process']:
            try:
                 client_sessions[sid]['process'].kill()
            except: pass
        del client_sessions[sid]

@socketio.on('start_analysis', namespace='/')
def handle_start(data):
    """Start analysis for THIS session"""
    sid = request.sid
    
    # Ensure session exists
    if sid not in client_sessions:
        client_sessions[sid] = {'active': False, 'process': None}
        
    if client_sessions[sid]['active']:
        emit('output', {'data': '⚠️  Analysis already running in this tab!\n'})
        return
    
    # Use config from request or global defaults
    symbols = data.get('symbols', config['symbols'])
    indicators = data.get('indicators', config['indicators'])
    timeframes = data.get('timeframes', config['timeframes'])
    min_conf = data.get('min_confidence', config['min_confidence'])
    exchanges = data.get('exchanges', config['exchanges'])
    strategies = data.get('strategies', config['strategies'])
    
    emit('output', {'data': f'🚀 Starting analysis at {datetime.now().strftime("%H:%M:%S")}\n'})
    emit('status', {'status': 'started'})
    
    # Launch session-specific thread
    thread = threading.Thread(
        target=run_session_analysis,
        args=(sid, symbols, indicators, timeframes, min_conf, exchanges, strategies),
        daemon=True
    )
    client_sessions[sid]['thread'] = thread
    client_sessions[sid]['active'] = True
    thread.start()

@socketio.on('stop_analysis', namespace='/')
def handle_stop():
    """Stop analysis for THIS session"""
    sid = request.sid
    socketio.emit('output', {'data': '⏹️  Stop requested...\n'}, room=sid, namespace='/')
    
    if sid in client_sessions and client_sessions[sid]['process']:
        try:
            proc = client_sessions[sid]['process']
            import platform
            if platform.system() == 'Windows':
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(proc.pid)], capture_output=True)
            else:
                proc.terminate()
            
            socketio.emit('output', {'data': '⏹️  Process terminated.\n'}, room=sid, namespace='/')
        except Exception as e:
            socketio.emit('output', {'data': f'❌ Error stopping: {e}\n'}, room=sid, namespace='/')
        finally:
            client_sessions[sid]['process'] = None
            client_sessions[sid]['active'] = False
            socketio.emit('status', {'status': 'stopped'}, room=sid, namespace='/')
    else:
        socketio.emit('output', {'data': 'ℹ️  No analysis process currently running\n'}, room=sid, namespace='/')
        socketio.emit('status', {'status': 'stopped'}, room=sid, namespace='/')

@socketio.on('refresh_news', namespace='/')
def handle_refresh_news():
    """Manual trigger to refresh news (Global broadcast)"""
    try:
        # socketio.emit('output', {'data': '📰 Refreshing news...'}, namespace='/')
        news_manager.fetch_news()
        status = news_manager.get_market_status()
        emit('market_status', status, broadcast=True, namespace='/')
    except Exception as e:
        emit('output', {'data': f"Error refreshing news: {e}"}, namespace='/')

@socketio.on('clear_output', namespace='/')
def handle_clear():
    """Clear terminal (Session specific)"""
    sid = request.sid
    emit('clear', room=sid)
    emit('output', {'data': '>>> Output cleared\n'}, room=sid)

def update_scheduler():
    """Update APScheduler with new interval"""
    try:
        scheduler.remove_job('auto_analysis')
    except:
        pass
    
    if config['auto_run']:
        scheduler.add_job(
            auto_run_analysis,
            'interval',
            seconds=config['auto_run_interval'],
            id='auto_analysis'
        )
        if not scheduler.running:
            scheduler.start()


@app.route('/api/proxy/klines')
def proxy_klines():
    """Proxy kline requests to the specific exchange requested"""
    symbol = request.args.get('symbol', 'BTCUSDT').upper().replace('_', '')
    interval = request.args.get('interval', '1h')
    limit = request.args.get('limit', '200')
    exchange = request.args.get('exchange', 'BINANCE').upper().replace(' ', '').replace('.', '')
    
    fetcher = EXCHANGE_FETCHERS.get(exchange)
    if not fetcher:
        # Fallback to Binance if exchange not supported or not found
        fetcher = get_klines_binance
        
    klines = fetcher(symbol, interval, limit=int(limit))
    if klines:
        return jsonify(klines)
        
    return jsonify({'error': f'Failed to fetch klines from {exchange}'}), 500

# --- Real Trader API Routes ---
@app.route('/api/trader/config', methods=['POST'])
def save_trader_config():
    """Save exchange API keys"""
    data = request.json
    exch = data.get('exchange')
    key = data.get('apiKey')
    secret = data.get('secretKey')
    if not exch or not key or not secret:
        return jsonify({'status': 'error', 'msg': 'Missing fields'}), 400
    
    success = real_trader.update_exchange_config(exch, key, secret)
    return jsonify({'status': 'ok' if success else 'error'})

@app.route('/api/trader/settings', methods=['POST'])
def save_trader_settings():
    """Save auto-trade settings"""
    try:
        data = request.json
        print(f"Received trader settings: {data}")
        auto_enabled = data.get('auto_trade_enabled', False)
        risk_type = data.get('risk_type', 'percent')
        risk_value = data.get('risk_value', 1.0)
        filters = data.get('filters', ['STRONG', 'ELITE'])
        
        real_trader.update_settings(auto_enabled, risk_type, risk_value, filters)
        return jsonify({'status': 'ok'})
    except Exception as e:
        print(f"Error saving trader settings: {e}")
        return jsonify({'status': 'error', 'msg': str(e)}), 500

@app.route('/api/trader/status', methods=['GET'])
def get_trader_status():
    """Get current connection status and settings"""
    return jsonify({
        'connected_exchanges': list(real_trader.exchanges.keys()),
        'auto_trade_enabled': real_trader.auto_trade_enabled,
        'risk_settings': real_trader.risk_settings,
        'filters': real_trader.trade_filter
    })

@app.route('/api/trader/execute', methods=['POST'])
def manual_trade_execution():
    """Manually trigger a trade from the UI"""
    trade_data = request.json.get('trade')
    if not trade_data: return jsonify({'status': 'error', 'msg': 'No data'}), 400
    
    print(f"Manual trade request for: {trade_data['symbol']}")
    # Execute immediately, overriding checks
    result = real_trader.execute_trade(trade_data, manual_override=True)
    return jsonify(result)

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(e):
    print(f"Server error: {e}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Start Market Monitor (News + Volatility)
    eventlet.spawn(market_monitor_loop)

    # Apply initial scheduler config
    update_scheduler()

    
    print("RBot Pro Multi-Exchange Analysis UI Server")
    print("📱 Open: http://localhost:5000")
    print("✓ Using queue-based streaming for stability")
    
    # Start Trade Tracking loop
    eventlet.spawn(trade_tracker.update_loop)
    
    try:
        socketio.run(
            app,
            host='0.0.0.0',
            port=5000,
            debug=False,
            use_reloader=False,
            allow_unsafe_werkzeug=True
        )
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
