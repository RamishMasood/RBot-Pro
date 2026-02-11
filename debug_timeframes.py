
import sys
import subprocess
import threading
import time

def run_verification():
    cmd = [
        sys.executable, 'fast_analysis.py',
        '--symbols', 'BTCUSDT',
        '--indicators', 'RSI,MACD',  # Verify basic indicators work on these timeframes
        '--timeframes', '3m,1d',
        '--min-confidence', '1'
    ]
    
    # Run the command and capture output
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        print("STDOUT:", result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
            
    except Exception as e:
        print(f"Error running verification: {e}")

if __name__ == "__main__":
    run_verification()
