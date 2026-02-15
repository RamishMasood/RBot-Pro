
import requests
import json

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36'
}

def test_exchange(name, url):
    print(f"Testing {name}...")
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()
        
        count = 0
        if name == 'MEXC':
            if data.get('success'): count = len(data.get('data', []))
        elif name == 'BINANCE':
            count = len(data)
        elif name == 'BYBIT':
            if data.get('result'): count = len(data['result'].get('list', []))
        elif name == 'BITGET':
            if data.get('data'): count = len(data['data'])
        elif name == 'OKX':
            if data.get('data'): count = len(data['data'])
        elif name == 'KUCOIN':
            if data.get('data'): count = len(data['data'].get('ticker', []))
        elif name == 'GATEIO':
            count = len(data)
        elif name == 'HTX':
            if data.get('data'): count = len(data['data'])
            
        print(f"  [OK] {name} Success: Found {count} symbols")
        return True
    except Exception as e:
        print(f"  [ERROR] {name} Failed: {e}")
        return False

exchanges = {
    'MEXC': 'https://contract.mexc.com/api/v1/contract/detail',
    'BINANCE': 'https://api.binance.com/api/v3/ticker/24hr',
    'BYBIT': 'https://api.bybit.com/v5/market/tickers?category=linear',
    'BITGET': 'https://api.bitget.com/api/v2/mix/market/tickers?productType=USDT-FUTURES',
    'OKX': 'https://www.okx.com/api/v5/market/tickers?instType=SWAP',
    'KUCOIN': 'https://api.kucoin.com/api/v1/market/allTickers',
    'GATEIO': 'https://api.gateio.ws/api/v4/futures/usdt/tickers',
    'HTX': 'https://api.huobi.pro/market/tickers'
}

for name, url in exchanges.items():
    test_exchange(name, url)
