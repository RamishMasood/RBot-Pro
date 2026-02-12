#!/usr/bin/env python3
"""Simple test to verify 1m and 3m timeframes work"""
import requests

def test_mexc_timeframes():
    """Test 1m and 3m on MEXC"""
    print("Testing MEXC Timeframes:")
    
    timeframes = {'1m': 'Min1', '3m': 'Min3', '5m': 'Min5'}
    symbol = 'BTC_USDT'
    
    for tf_name, tf_mexc in timeframes.items():
        url = f'https://contract.mexc.com/api/v1/contract/kline/{symbol}?interval={tf_mexc}&limit=50'
        try:
            r = requests.get(url, timeout=10)
            data = r.json()
            if data.get('success') and 'data' in data and len(data['data']['time']) > 0:
                print(f"  {tf_name}: PASS - Got {len(data['data']['time'])} candles")
            else:
                print(f"  {tf_name}: FAIL - No data")
        except Exception as e:
            print(f"  {tf_name}: ERROR - {e}")

def test_binance_timeframes():
    """Test 1m and 3m on Binance"""
    print("\nTesting Binance Timeframes:")
    
    timeframes = ['1m', '3m', '5m']
    symbol = 'BTCUSDT'
    
    for tf in timeframes:
        url = f'https://api.binance.com/api/v3/klines?symbol={symbol}&interval={tf}&limit=50'
        try:
            r = requests.get(url, timeout=10)
            data = r.json()
            if data and isinstance(data, list) and len(data) > 0:
                print(f"  {tf}: PASS - Got {len(data)} candles")
            else:
                print(f"  {tf}: FAIL - No data")
        except Exception as e:
            print(f"  {tf}: ERROR - {e}")

if __name__ == "__main__":
    test_mexc_timeframes()
    test_binance_timeframes()
    print("\nConclusion: If all tests show PASS, then 1m and 3m timeframes are working correctly.")
