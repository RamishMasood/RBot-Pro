
import sys
import subprocess

cmd = [
    sys.executable, 'fast_analysis.py',
    '--symbols', 'BTCUSDT',
    '--indicators', 'PSAR,TEMA,CHANDELIER,KAMA,VFI',
    '--timeframes', '1m',
    '--min-confidence', '1'
]

with open('debug_output.txt', 'w', encoding='utf-8') as f:
    result = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, text=True)
