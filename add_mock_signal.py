import json
import os
from datetime import datetime, timedelta

filepath = 'signals_history.json'
if os.path.exists(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Create a Binance ELITE signal
    # Use a symbol that exists on Binance
    new_sig = {
        "timestamp": (datetime.now() - timedelta(minutes=10)).strftime('%Y-%m-%d %H:%M:%S'),
        "symbol": "BTCUSDT",
        "type": "LONG",
        "strategy": "Triple-Confluence",
        "exchange": "BINANCE",
        "entry": 67000.0,
        "sl": 66500.0,
        "tp1": 68000.0,
        "tp2": 69000.0,
        "risk_reward": 2.0,
        "confidence_score": 10,
        "signal_quality": "ELITE",
        "timeframe": "1h",
        "reason": "MOCK SIGNAL FOR VERIFICATION"
    }
    data.append(new_sig)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    print("Added mock Binance ELITE signal")
