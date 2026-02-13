import requests
import time

def test_fetch(exch, symbol, url):
    print(f"Testing {exch}...")
    try:
        r = requests.get(url, timeout=10)
        print(f"  Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and len(data) > 0:
                print(f"  Success: {len(data)} candles")
            elif isinstance(data, dict) and (data.get('success') or data.get('result') or data.get('data')):
                print(f"  Success: Data found")
            else:
                print(f"  Fail: {data}")
        else:
            print(f"  Fail: {r.text[:200]}")
    except Exception as e:
        print(f"  Error: {e}")

# Tests
test_fetch("BINANCE", "BTCUSDT", "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1m&limit=5")
test_fetch("BYBIT", "BTCUSDT", "https://api.bybit.com/v5/market/kline?category=linear&symbol=BTCUSDT&interval=1&limit=5")
test_fetch("BITGET", "BTCUSDT", "https://api.bitget.com/api/v2/mix/market/candles?productType=USDT-FUTURES&symbol=BTCUSDT&granularity=1m&limit=5")
test_fetch("OKX", "BTC-USDT-SWAP", "https://www.okx.com/api/v5/market/candles?instId=BTC-USDT-SWAP&bar=1m&limit=5")
test_fetch("KUCOIN", "BTC-USDT", "https://api.kucoin.com/api/v1/market/candles?type=1min&symbol=BTC-USDT&limit=5")
test_fetch("GATEIO", "BTC_USDT", "https://api.gateio.ws/api/v4/futures/usdt/candlesticks?contract=BTC_USDT&interval=1m&limit=5")
test_fetch("HTX", "btcusdt", "https://api.huobi.pro/market/history/kline?symbol=btcusdt&period=1min&size=5")
