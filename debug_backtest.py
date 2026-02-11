
import requests
import datetime
import json

def get_utc_timestamp(dt_str):
    dt = datetime.datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
    return int(dt.timestamp() * 1000)

def test_fetch_mexc(symbol, ts_str):
    print(f"--- Testing MEXC for {symbol} at {ts_str} ---")
    start_ms = get_utc_timestamp(ts_str)
    
    if 'USDT' in symbol and '_' not in symbol:
        mexc_symbol = symbol.replace('USDT', '_USDT')
    else:
        mexc_symbol = symbol
        
    start_sec = start_ms // 1000
    end_sec = start_sec + (60 * 60) # 1 hour
    
    url = f"https://contract.mexc.com/api/v1/contract/kline/{mexc_symbol}?interval=Min1&start={start_sec}&end={end_sec}"
    print(f"URL: {url}")
    
    try:
        r = requests.get(url, timeout=10)
        print(f"Status: {r.status_code}")
        data = r.json()
        if data.get('success'):
            candles = data.get('data', {}).get('close', [])
            times = data.get('data', {}).get('time', [])
            print(f"Success: True. Candle count: {len(candles)}")
            if times:
                print(f"First candle time: {times[0]}")
                print(f"Requested start: {start_sec}")
        else:
            print(f"Success: False. Response: {data}")
    except Exception as e:
        print(f"Error: {e}")

def test_fetch_binance(symbol, ts_str):
    print(f"--- Testing Binance for {symbol} at {ts_str} ---")
    start_ms = get_utc_timestamp(ts_str)
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&startTime={start_ms}&limit=10"
    print(f"URL: {url}")
    try:
        r = requests.get(url, timeout=10)
        print(f"Status: {r.status_code}")
        data = r.json()
        if isinstance(data, list):
             print(f"Candle count: {len(data)}")
             if data:
                 print(f"First candle time: {data[0][0]}")
                 print(f"Requested start: {start_ms}")
        else:
            print(f"Response: {data}")
    except Exception as e:
        print(f"Error: {e}")

import sys

class Logger:
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "w", encoding='utf-8')

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()

    def flush(self):
        self.terminal.flush()
        self.log.flush()

sys.stdout = Logger("debug_log.txt")

def test_fetch_mexc_spot(symbol, ts_str):
    print(f"--- Testing MEXC Spot for {symbol} at {ts_str} ---")
    start_ms = get_utc_timestamp(ts_str)
    start_sec = start_ms // 1000
    end_sec = start_sec + (60 * 60) # 1 hour
    
    url = f"https://api.mexc.com/api/v3/klines?symbol={symbol}&interval=1m&startTime={start_ms}&limit=60"
    print(f"URL: {url}")
    
    try:
        r = requests.get(url, timeout=10)
        print(f"Status: {r.status_code}")
        data = r.json()
        if isinstance(data, list):
            print(f"Success: True. Candle count: {len(data)}")
            if data:
                print(f"First candle time: {data[0][0]}")
                print(f"Requested start: {start_ms}")
        else:
            print(f"Success: False. Response: {data}")
    except Exception as e:
        print(f"Error: {e}")

# Test Cases based on user logs
# WIN/LOSS/PENDING case
test_fetch_mexc("ATOMUSDT", "2026-02-11 21:12:59") 
# NO_DATA case
test_fetch_mexc("BTCUSDT", "2026-02-11 22:34:20")
test_fetch_mexc("ASTERUSDT", "2026-02-11 22:34:05")
# Aligned Timestamp Test (Simulating Fix)
test_fetch_mexc("ASTERUSDT", "2026-02-11 22:34:00")

# Spot Test
test_fetch_mexc_spot("ASTERUSDT", "2026-02-11 22:34:05")

