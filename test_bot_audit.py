from fast_analysis import enforce_signal_safety_buffers, resolve_conflicts, TF_WEIGHTS
import unittest

class TestBotAudit(unittest.TestCase):
    def test_sl_breathing_room_fix(self):
        # Test that SL is NOT moved closer to entry (Old bug)
        # Entry: 100, SL: 95, TP1: 115 (RR = 3.0)
        # 1h timeframe (buffer 1.5x)
        atr = 1.0
        trade = {
            'symbol': 'BTCUSDT',
            'timeframe': '1h',
            'type': 'LONG',
            'entry': 100.0,
            'sl': 95.0,
            'tp1': 115.0,
            'atr': atr,
            'reason': ''
        }
        symbol_analyses_map = {'BTCUSDT': {'1h': {'support': 96.0, 'atr': atr, 'current_price': 100.0}}}
        
        trades = [trade]
        enforce_signal_safety_buffers(trades, symbol_analyses_map)
        
        # New logic should NOT move SL to 92.5 (RR 2.0) if it was already safe
        # Risk is 100 - 95 = 5.0. min_sl_distance is 1.5 * 1.0 = 1.5.
        # Since 5.0 > 1.5, SL should NOT be widened.
        self.assertEqual(trades[0]['sl'], 95.0) 
        self.assertNotIn('SL WIDENED', trades[0]['reason'])
        self.assertNotEqual(trades[0]['sl'], 92.5)

    def test_scalp_sl_floor(self):
        # Test that tight SL is widened for 1m scalps
        atr = 0.1
        entry = 100.0
        # 0.1% SL (very tight)
        trade = {
            'symbol': 'ETHUSDT',
            'timeframe': '1m',
            'type': 'LONG',
            'entry': entry,
            'sl': 99.9, 
            'tp1': 101.0,
            'atr': atr,
            'reason': ''
        }
        symbol_analyses_map = {'ETHUSDT': {'1m': {'support': 99.95, 'atr': atr, 'current_price': 100.0}}}
        
        trades = [trade]
        enforce_signal_safety_buffers(trades, symbol_analyses_map)
        
        # 1m floor is 2.5x ATR = 0.25
        # 100 - 0.25 = 99.75
        self.assertEqual(trades[0]['sl'], 99.75)
        self.assertIn('SL WIDENED', trades[0]['reason'])

    def test_conflict_resolution(self):
        # Test that only the highest confidence trade is kept
        trades = [
            {'symbol': 'SOLUSDT', 'exchange': 'MEXC', 'type': 'LONG', 'confidence_score': 7},
            {'symbol': 'SOLUSDT', 'exchange': 'MEXC', 'type': 'SHORT', 'confidence_score': 8}
        ]
        resolved, conflicts = resolve_conflicts(trades)
        print(f"\nDebug Conflict: Resolved count={len(resolved)}, Type={resolved[0]['type'] if resolved else 'N/A'}, Conflicts={conflicts}")
        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0]['type'], 'SHORT')
        self.assertEqual(conflicts, 1)

if __name__ == '__main__':
    unittest.main()
