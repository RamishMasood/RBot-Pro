import json
import os
from datetime import datetime, timedelta

filepath = 'signals_history.json'
if os.path.exists(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    exchanges = ['BYBIT', 'OKX', 'BITGET', 'KUCOIN', 'GATEIO', 'HTX']
    for ex in exchanges:
        new_sig = {
            "timestamp": (datetime.now() - timedelta(minutes=15)).strftime('%Y-%m-%d %H:%M:%S'),
            "symbol": "BTCUSDT",
            "type": "LONG",
            "strategy": "Triple-Confluence",
            "exchange": ex,
            "entry": 67000.0,
            "sl": 66000.0,
            "tp1": 68000.0,
            "tp2": 69000.0,
            "risk_reward": 1.0,
            "confidence_score": 10,
            "signal_quality": "ELITE",
            "timeframe": "1h",
            "reason": f"MOCK {ex} SIGNAL"
        }
        data.append(new_sig)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    print("Added mock signals for all exchanges")
