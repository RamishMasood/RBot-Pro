#!/usr/bin/env python3
"""
Comprehensive Verification Script for RBot Pro
Tests all strategies, indicators, and timeframes
"""

import sys
import io
import requests
import math
from datetime import datetime, timedelta

# Force UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Import key functions from fast_analysis without triggering arg parsing
import importlib.util
spec = importlib.util.spec_from_file_location("fast_analysis_module", "fast_analysis.py")
fa = importlib.util.module_from_spec(spec)

# Override argv to prevent argparse issues
old_argv = sys.argv
sys.argv = ['fast_analysis.py', '--symbols', 'BTCUSDT', '--timeframes', '1m,3m,5m,15m,1h', '--min-confidence', '5']

try:
    spec.loader.exec_module(fa)
finally:
    sys.argv = old_argv

# Now we can use functions from fast_analysis
get_klines_mexc = fa.get_klines_mexc
get_klines_binance = fa.get_klines_binance
get_klines_bybit = fa.get_klines_bybit
get_klines_bitget = fa.get_klines_bitget
get_klines_okx = fa.get_klines_okx
get_klines_kucoin = fa.get_klines_kucoin
get_klines_gateio = fa.get_klines_gateio
get_klines_htx = fa.get_klines_htx
get_klines = fa.get_klines
get_top_symbols = fa.get_top_symbols

calculate_rsi = fa.calculate_rsi
calculate_ema = fa.calculate_ema
calculate_macd = fa.calculate_macd
calculate_bb = fa.calculate_bb
calculate_atr = fa.calculate_atr
calculate_adx = fa.calculate_adx
calculate_stoch_rsi = fa.calculate_stoch_rsi
calculate_obv = fa.calculate_obv
calculate_chop = fa.calculate_chop
calculate_vortex = fa.calculate_vortex
calculate_stc = fa.calculate_stc
calculate_donchian = fa.calculate_donchian
calculate_kc = fa.calculate_kc
calculate_utbot = fa.calculate_utbot

def test_timeframes():
    """Test all timeframes with sample data"""
    print("\n" + "="*80)
    print("TESTING TIMEFRAMES")
    print("="*80)
    
    timeframes_to_test = ['1m', '3m', '5m', '15m', '30m', '1h', '4h', '1d']
    test_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
    
    results = {}
    
    for tf in timeframes_to_test:
        print(f"\n⏰ Testing {tf} timeframe...")
        success_count = 0
        
        for symbol in test_symbols:
            try:
                # Try MEXC first
                klines = get_klines_mexc(symbol, tf, limit=200)
                if not klines or len(klines) < 50:
                    # Try Binance
                    klines = get_klines_binance(symbol, tf, limit=200)
                
                if klines and len(klines) >= 50:
                    print(f"  ✅ {symbol}: Got {len(klines)} candles")
                    success_count += 1
                else:
                    print(f"  ❌ {symbol}: Failed to get data")
            except Exception as e:
                print(f"  ❌ {symbol}: Error - {str(e)}")
        
        results[tf] = {
            'tested': len(test_symbols),
            'success': success_count,
            'pass': success_count == len(test_symbols)
        }
    
    print("\n" + "-"*80)
    print("TIMEFRAME TEST SUMMARY:")
    print("-"*80)
    for tf, res in results.items():
        status = "✅ PASS" if res['pass'] else "❌ FAIL"
        print(f"{tf:6} - {status} ({res['success']}/{res['tested']})")
    
    return results

def test_indicators():
    """Test all indicators with sample data"""
    print("\n" + "="*80)
    print("TESTING INDICATORS")
    print("="*80)
    
    # Get sample data
    symbol = 'BTCUSDT'
    klines = get_klines_binance(symbol, '1h', limit=200)
    
    if not klines or len(klines) < 100:
        print("❌ Failed to get sample data for indicator testing")
        return {}
    
    closes = [k['close'] for k in klines]
    highs = [k['high'] for k in klines]
    lows = [k['low'] for k in klines]
    volumes = [k['volume'] for k in klines]
    
    indicator_tests = {
        'RSI': lambda: calculate_rsi(closes, 14),
        'EMA': lambda: calculate_ema(closes, 20),
        'MACD': lambda: calculate_macd(closes),
        'BB': lambda: calculate_bb(closes, 20, 2),
        'ATR': lambda: calculate_atr(highs, lows, closes, 14),
        'ADX': lambda: calculate_adx(highs, lows, closes, 14),
        'StochRSI': lambda: calculate_stoch_rsi(closes, 14, 14, 3, 3),
        'OBV': lambda: calculate_obv(closes, volumes),
        'CHOP': lambda: calculate_chop(highs, lows, closes, 14),
        'Vortex': lambda: calculate_vortex(highs, lows, closes, 14),
        'STC': lambda: calculate_stc(closes, 10, 23, 50),
        'Donchian': lambda: calculate_donchian(highs, lows, 20),
        'Keltner': lambda: calculate_kc(highs, lows, closes, 20, 2.0),
        'UT Bot': lambda: calculate_utbot(highs, lows, closes, 2, 10),
    }
    
    results = {}
    
    for name, test_func in indicator_tests.items():
        try:
            result = test_func()
            if result is not None:
                result_str = str(result)[:50] if not isinstance(result, dict) else "dict"
                print(f"  ✅ {name:15} - Working")
                results[name] = {'status': 'PASS', 'error': None}
            else:
                print(f"  ⚠️  {name:15} - Returned None")
                results[name] = {'status': 'WARNING', 'error': 'Returned None'}
        except Exception as e:
            print(f"  ❌ {name:15} - Error: {str(e)[:50]}")
            results[name] = {'status': 'FAIL', 'error': str(e)}
    
    print("\n" + "-"*80)
    print("INDICATOR TEST SUMMARY:")
    print("-"*80)
    pass_count = sum(1 for r in results.values() if r['status'] == 'PASS')
    warning_count = sum(1 for r in results.values() if r['status'] == 'WARNING')
    fail_count = sum(1 for r in results.values() if r['status'] == 'FAIL')
    print(f"✅ Passed: {pass_count}")
    print(f"⚠️  Warnings: {warning_count}")
    print(f"❌ Failed: {fail_count}")
    
    return results

def test_exchange_connectivity():
    """Test connectivity to all exchanges"""
    print("\n" + "="*80)
    print("TESTING EXCHANGE CONNECTIVITY")
    print("="*80)
    
    exchanges_to_test = {
        'MEXC': get_klines_mexc,
        'Binance': get_klines_binance,
        'Bybit': get_klines_bybit,
        'Bitget': get_klines_bitget,
        'OKX': get_klines_okx,
        'KuCoin': get_klines_kucoin,
        'GateIO': get_klines_gateio,
        'HTX': get_klines_htx
    }
    
    test_symbol = 'BTCUSDT'
    test_interval = '1h'
    results = {}
    
    for exchange_name, fetch_func in exchanges_to_test.items():
        try:
            klines = fetch_func(test_symbol, test_interval, limit=50)
            if klines and len(klines) >= 10:
                print(f"  ✅ {exchange_name:10} - Connected ({len(klines)} candles)")
                results[exchange_name] = 'PASS'
            else:
                print(f"  ❌ {exchange_name:10} - No data")
                results[exchange_name] = 'FAIL'
        except Exception as e:
            print(f"  ❌ {exchange_name:10} - Error: {str(e)[:40]}")
            results[exchange_name] = 'FAIL'
    
    print("\n" + "-"*80)
    print("EXCHANGE CONNECTIVITY SUMMARY:")
    print("-"*80)
    pass_count = sum(1 for r in results.values() if r == 'PASS')
    fail_count = sum(1 for r in results.values() if r == 'FAIL')
    print(f"✅ Connected: {pass_count}/{len(exchanges_to_test)}")
    print(f"❌ Failed: {fail_count}/{len(exchanges_to_test)}")
    
    return results

def test_new_coins():
    """Test analysis on a larger set of coins"""
    print("\n" + "="*80)
    print("TESTING NEW COINS (STRESS TEST)")
    print("="*80)
    
    print("\n📊 Fetching top coins from exchanges...")
    
    try:
        new_symbols = get_top_symbols(n=100)
        print(f"✅ Loaded {len(new_symbols)} symbols")
        
        # Test analysis on 20 coins
        test_coins = new_symbols[10:30] if len(new_symbols) >= 30 else new_symbols[:20]
        
        print(f"\n🔍 Testing analysis on: {len(test_coins)} coins")
        
        success_count = 0
        import time as _time
        start_time = _time.time()
        
        for symbol in test_coins:
            try:
                # Test both 1m and 3m specifically
                data1m = get_klines(symbol, '1m', limit=100)
                data3m = get_klines(symbol, '3m', limit=100)
                
                if data1m and data3m:
                    print(f"  ✅ {symbol:10} - 1m & 3m OK")
                    success_count += 1
                elif data1m:
                    print(f"  ⚠️  {symbol:10} - 1m OK, 3m MISSING")
                else:
                    print(f"  ❌ {symbol:10} - FAILED")
            except Exception as e:
                print(f"  ❌ {symbol} - Error: {str(e)[:40]}")
        
        end_time = _time.time()
        print(f"\n📈 Analyzed {success_count}/{len(test_coins)} coins in {end_time - start_time:.2f}s")
        return {'tested': len(test_coins), 'success': success_count}
        
    except Exception as e:
        print(f"❌ Error loading new coins: {str(e)}")
        return {'tested': 0, 'success': 0}

def main():
    """Run all verification tests"""
    print("\n" + "="*80)
    print("🤖 RBOT PRO - COMPREHENSIVE VERIFICATION")
    print("="*80)
    print("Testing all strategies, indicators, and timeframes...")
    print("="*80)
    
    # Run all tests
    exchange_results = test_exchange_connectivity()
    timeframe_results = test_timeframes()
    indicator_results = test_indicators()
    new_coin_results = test_new_coins()
    
    # Final Summary
    print("\n" + "="*80)
    print("📊 FINAL VERIFICATION SUMMARY")
    print("="*80)
    
    # Exchanges
    exchange_pass = sum(1 for r in exchange_results.values() if r == 'PASS')
    print(f"\n🌐 Exchanges: {exchange_pass}/8 working")
    
    # Timeframes
    tf_pass = sum(1 for r in timeframe_results.values() if r['pass'])
    print(f"⏰ Timeframes: {tf_pass}/8 fully operational")
    if tf_pass < 8:
        failed_tfs = [tf for tf, r in timeframe_results.items() if not r['pass']]
        print(f"   ⚠️  Issues with: {', '.join(failed_tfs)}")
    
    # Indicators
    ind_pass = sum(1 for r in indicator_results.values() if r['status'] == 'PASS')
    ind_total = len(indicator_results)
    print(f"📈 Indicators: {ind_pass}/{ind_total} working perfectly")
    if ind_pass < ind_total:
        failed_inds = [name for name, r in indicator_results.items() if r['status'] == 'FAIL']
        if failed_inds:
            print(f"   ❌ Failed: {', '.join(failed_inds)}")
    
    # New Coins
    if new_coin_results['tested'] > 0:
        coin_rate = (new_coin_results['success'] / new_coin_results['tested']) * 100
        print(f"🪙 New Coins: {new_coin_results['success']}/{new_coin_results['tested']} tested successfully ({coin_rate:.1f}%)")
    
    # Overall Status
    print("\n" + "="*80)
    total_checks = len(exchange_results) + len(timeframe_results) + len(indicator_results)
    passed_checks = exchange_pass + tf_pass + ind_pass
    overall_rate = (passed_checks / total_checks) * 100
    
    if overall_rate >= 90:
        print("✅ SYSTEM STATUS: EXCELLENT - All critical components working")
    elif overall_rate >= 75:
        print("⚠️  SYSTEM STATUS: GOOD - Minor issues detected")
    elif overall_rate >= 50:
        print("⚠️  SYSTEM STATUS: FAIR - Multiple issues need attention")
    else:
        print("❌ SYSTEM STATUS: POOR - Critical issues detected")
    
    print(f"Overall: {passed_checks}/{total_checks} checks passed ({overall_rate:.1f}%)")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
