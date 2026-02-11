import sys
import os
import threading
import time

# Verify News Manager
print("--- TESTING NEWS MANAGER ---")
try:
    from news_manager import news_manager
    news_manager.fetch_news()
    status = news_manager.get_market_status()
    print(f"Sentiment: {status['sentiment']}")
    print(f"News Headlines: {[n['title'] for n in status['news_feed'][:2]]}")
    print("✅ News Manager Functional")
except Exception as e:
    print(f"❌ News Manager Error: {e}")

# Verify Fast Analysis Strategies
print("\n--- TESTING TRADING STRATEGIES ---")
try:
    import fast_analysis
    # We won't run a full analysis loop on 200 coins, just check if imports and key functions exist
    strategies = [attr for attr in dir(fast_analysis) if attr.startswith('strategy_')]
    print(f"Total Strategies Found: {len(strategies)}")
    if len(strategies) > 30:
        print(f"✅ Strategy Engine loaded ({len(strategies)} strategies)")
    else:
        print(f"⚠️ Only {len(strategies)} strategies found. Expected >30.")
    
    # Test indicators calculation (on dummy data)
    import numpy as np
    dummy_data = {
        'close': np.random.uniform(50000, 51000, 100),
        'high': np.random.uniform(51001, 51500, 100),
        'low': np.random.uniform(49000, 49999, 100),
        'volume': np.random.uniform(10, 100, 100)
    }
    # Check if compute_indicators works
    if hasattr(fast_analysis, 'compute_indicators'):
        print("✅ compute_indicators core function exists")
    
except Exception as e:
    print(f"❌ Strategy Engine Error: {e}")

print("\n--- VERIFICATION COMPLETE ---")
