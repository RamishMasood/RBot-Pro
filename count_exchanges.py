import json
import os

filepath = 'signals_history.json'
if os.path.exists(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
        counts = {}
        for item in data:
            exch = item.get('exchange', 'N/A')
            counts[exch] = counts.get(exch, 0) + 1
        print(counts)
else:
    print("File not found")
