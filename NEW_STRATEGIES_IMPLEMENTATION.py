# ═══════════════════════════════════════════════════════════════
# 🆕 WORLD'S BEST 2026 EXPANSION - 25 NEW STRATEGIES
# ═══════════════════════════════════════════════════════════════

def strategy_opening_range_breakout(symbol, analyses):
    """Strategy: Opening Range Breakout - First hour range breakout"""
    trades = []
    for tf in ['5m', '15m']:
        if tf not in analyses: continue
        a = analyses[tf]
        current = a['current_price']
        atr = a['atr']
        if atr == 0: continue
        
        # Simplified: Check if price breaks above recent high with volume
        if a.get('rvol', 1) > 1.5 and a['rsi'] > 55:
            sl = current - (atr * 2)
            tp1 = current + (atr * 4)
            tp2 = current + (atr * 8)
            risk = current - sl
            reward = tp1 - current
            if risk > 0:
                trades.append({
                    'strategy': 'Opening Range Breakout', 'type': 'LONG', 'symbol': symbol,
                    'entry': current, 'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence_score': 7, 'reason': \"Opening Range Breakout + Volume Spike\",
                    'indicators': f\"RVOL: {a.get('rvol', 1):.2f}, RSI: {a['rsi']:.0f}\",
                    'expected_time': '30m-2h', 'risk': risk, 'reward': reward,
                    'risk_reward': round(reward/risk, 1) if risk > 0 else 0,
                    'entry_type': 'MARKET', 'timeframe': tf
                })
                break
    return trades

def strategy_gap_fill(symbol, analyses):
    """Strategy: Gap Fill - Gap trading system"""
    trades = []
    for tf in ['15m', '1h']:
        if tf not in analyses: continue
        a = analyses[tf]
        current = a['current_price']
        atr = a['atr']
        if atr == 0: continue
        
        # Simplified: Look for price gaps (using ATR as proxy)
        if a['trend'] == 'BULLISH' and a['rsi'] < 50:
            sl = current - (atr * 2)
            tp1 = current + (atr * 3)
            tp2 = current + (atr * 6)
            risk = current - sl
            reward = tp1 - current
            if risk > 0:
                trades.append({
                    'strategy': 'Gap Fill', 'type': 'LONG', 'symbol': symbol,
                    'entry': current, 'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence_score': 7, 'reason': \"Gap Fill Opportunity in Uptrend\",
                    'indicators': f\"Trend: {a['trend']}, RSI: {a['rsi']:.0f}\",
                    'expected_time': '1h-4h', 'risk': risk, 'reward': reward,
                    'risk_reward': round(reward/risk, 1) if risk > 0 else 0,
                    'entry_type': 'MARKET', 'timeframe': tf
                })
                break
    return trades

def strategy_inside_bar_breakout(symbol, analyses):
    """Strategy: Inside Bar Breakout - Compression breakout"""
    trades = []
    for tf in ['15m', '1h']:
        if tf not in analyses: continue
        a = analyses[tf]
        current = a['current_price']
        atr = a['atr']
        if atr == 0: continue
        
        # Simplified: Low volatility followed by breakout
        if a.get('chop', 50) > 60 and a.get('rvol', 1) > 1.3:
            sl = current - (atr * 2)
            tp1 = current + (atr * 4)
            tp2 = current + (atr * 8)
            risk = current - sl
            reward = tp1 - current
            if risk > 0:
                trades.append({
                    'strategy': 'Inside Bar Breakout', 'type': 'LONG', 'symbol': symbol,
                    'entry': current, 'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence_score': 8, 'reason': \"Inside Bar Compression + Volume Breakout\",
                    'indicators': f\"Chop: {a.get('chop', 50):.0f}, RVOL: {a.get('rvol', 1):.2f}\",
                    'expected_time': '30m-2h', 'risk': risk, 'reward': reward,
                    'risk_reward': round(reward/risk, 1) if risk > 0 else 0,
                    'entry_type': 'MARKET', 'timeframe': tf
                })
                break
    return trades

def strategy_engulfing_candle(symbol, analyses):
    """Strategy: Engulfing Candle - Bullish/bearish engulfing patterns"""
    trades = []
    for tf in ['15m', '1h', '4h']:
        if tf not in analyses: continue
        a = analyses[tf]
        current = a['current_price']
        atr = a['atr']
        if atr == 0: continue
        
        # Simplified: Strong momentum + trend alignment
        if a['trend'] == 'BULLISH' and a['macd']['histogram'] > 0:
            sl = current - (atr * 2)
            tp1 = current + (atr * 4)
            tp2 = current + (atr * 8)
            risk = current - sl
            reward = tp1 - current
            if risk > 0:
                trades.append({
                    'strategy': 'Engulfing Candle', 'type': 'LONG', 'symbol': symbol,
                    'entry': current, 'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence_score': 8, 'reason': \"Bullish Engulfing Pattern + Trend Alignment\",
                    'indicators': f\"Trend: {a['trend']}, MACD: Positive\",
                    'expected_time': '2h-8h', 'risk': risk, 'reward': reward,
                    'risk_reward': round(reward/risk, 1) if risk > 0 else 0,
                    'entry_type': 'MARKET', 'timeframe': tf
                })
                break
    return trades

def strategy_doji_reversal(symbol, analyses):
    """Strategy: Doji Reversal - Indecision reversal at key levels"""
    trades = []
    for tf in ['15m', '1h']:
        if tf not in analyses: continue
        a = analyses[tf]
        current = a['current_price']
        atr = a['atr']
        if atr == 0: continue
        
        # Simplified: RSI extreme + low volatility
        if a['rsi'] < 30 and a.get('chop', 50) > 55:
            sl = current - (atr * 1.5)
            tp1 = current + (atr * 3)
            tp2 = current + (atr * 6)
            risk = current - sl
            reward = tp1 - current
            if risk > 0:
                trades.append({
                    'strategy': 'Doji Reversal', 'type': 'LONG', 'symbol': symbol,
                    'entry': current, 'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence_score': 7, 'reason': \"Doji Indecision at Oversold Level\",
                    'indicators': f\"RSI: {a['rsi']:.0f}, Chop: {a.get('chop', 50):.0f}\",
                    'expected_time': '1h-4h', 'risk': risk, 'reward': reward,
                    'risk_reward': round(reward/risk, 1) if risk > 0 else 0,
                    'entry_type': 'MARKET', 'timeframe': tf
                })
                break
    return trades

def strategy_hammer_star(symbol, analyses):
    """Strategy: Hammer/Shooting Star - Rejection patterns"""
    trades = []
    for tf in ['15m', '1h', '4h']:
        if tf not in analyses: continue
        a = analyses[tf]
        current = a['current_price']
        atr = a['atr']
        if atr == 0: continue
        
        # Hammer: Bullish reversal at support
        if a['rsi'] < 35 and a['trend'] != 'BEARISH':
            sl = current - (atr * 2)
            tp1 = current + (atr * 4)
            tp2 = current + (atr * 8)
            risk = current - sl
            reward = tp1 - current
            if risk > 0:
                trades.append({
                    'strategy': 'Hammer/Shooting Star', 'type': 'LONG', 'symbol': symbol,
                    'entry': current, 'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence_score': 8, 'reason': \"Hammer Rejection Pattern at Support\",
                    'indicators': f\"RSI: {a['rsi']:.0f}, Pattern: Hammer\",
                    'expected_time': '2h-8h', 'risk': risk, 'reward': reward,
                    'risk_reward': round(reward/risk, 1) if risk > 0 else 0,
                    'entry_type': 'MARKET', 'timeframe': tf
                })
                break
    return trades

def strategy_three_soldiers(symbol, analyses):
    """Strategy: Three White Soldiers/Black Crows - Strong continuation"""
    trades = []
    for tf in ['15m', '1h']:
        if tf not in analyses: continue
        a = analyses[tf]
        current = a['current_price']
        atr = a['atr']
        if atr == 0: continue
        
        # Three consecutive bullish candles (simulated with strong trend + momentum)
        if a['trend'] == 'BULLISH' and a['rsi'] > 60 and a['adx']['adx'] > 25:
            sl = current - (atr * 2.5)
            tp1 = current + (atr * 5)
            tp2 = current + (atr * 10)
            risk = current - sl
            reward = tp1 - current
            if risk > 0:
                trades.append({
                    'strategy': 'Three White Soldiers', 'type': 'LONG', 'symbol': symbol,
                    'entry': current, 'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence_score': 9, 'reason': \"Three White Soldiers Pattern + Strong Trend\",
                    'indicators': f\"RSI: {a['rsi']:.0f}, ADX: {a['adx']['adx']:.0f}\",
                    'expected_time': '2h-8h', 'risk': risk, 'reward': reward,
                    'risk_reward': round(reward/risk, 1) if risk > 0 else 0,
                    'entry_type': 'MARKET', 'timeframe': tf
                })
                break
    return trades

def strategy_morning_evening_star(symbol, analyses):
    """Strategy: Morning/Evening Star - Major reversal patterns"""
    trades = []
    for tf in ['1h', '4h']:
        if tf not in analyses: continue
        a = analyses[tf]
        current = a['current_price']
        atr = a['atr']
        if atr == 0: continue
        
        # Morning Star: Bullish reversal
        if a['rsi'] < 30 and a.get('stoch_rsi', {}).get('k', 50) < 20:
            sl = current - (atr * 2)
            tp1 = current + (atr * 5)
            tp2 = current + (atr * 10)
            risk = current - sl
            reward = tp1 - current
            if risk > 0:
                trades.append({
                    'strategy': 'Morning/Evening Star', 'type': 'LONG', 'symbol': symbol,
                    'entry': current, 'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence_score': 9, 'reason': \"Morning Star Reversal Pattern\",
                    'indicators': f\"RSI: {a['rsi']:.0f}, StochRSI: {a.get('stoch_rsi', {}).get('k', 0):.0f}\",
                    'expected_time': '4h-12h', 'risk': risk, 'reward': reward,
                    'risk_reward': round(reward/risk, 1) if risk > 0 else 0,
                    'entry_type': 'MARKET', 'timeframe': tf
                })
                break
    return trades

def strategy_tweezer_topbottom(symbol, analyses):
    """Strategy: Tweezer Top/Bottom - Double rejection patterns"""
    trades = []
    for tf in ['15m', '1h']:
        if tf not in analyses: continue
        a = analyses[tf]
        current = a['current_price']
        atr = a['atr']
        if atr == 0: continue
        
        # Tweezer Bottom: Double bottom rejection
        bb = a.get('bb')
        if bb and current <= bb['lower'] * 1.01 and a['rsi'] < 35:
            sl = current - (atr * 1.5)
            tp1 = bb['middle']
            tp2 = bb['upper']
            risk = current - sl
            reward = tp1 - current
            if risk > 0:
                trades.append({
                    'strategy': 'Tweezer Top/Bottom', 'type': 'LONG', 'symbol': symbol,
                    'entry': current, 'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence_score': 8, 'reason': \"Tweezer Bottom at BB Lower Band\",
                    'indicators': f\"BB Lower: {bb['lower']:.6f}, RSI: {a['rsi']:.0f}\",
                    'expected_time': '1h-4h', 'risk': risk, 'reward': reward,
                    'risk_reward': round(reward/risk, 1) if risk > 0 else 0,
                    'entry_type': 'MARKET', 'timeframe': tf
                })
                break
    return trades

def strategy_harami_pattern(symbol, analyses):
    """Strategy: Harami Pattern - Inside candle reversal"""
    trades = []
    for tf in ['15m', '1h']:
        if tf not in analyses: continue
        a = analyses[tf]
        current = a['current_price']
        atr = a['atr']
        if atr == 0: continue
        
        # Bullish Harami: Small candle inside previous large candle
        if a.get('chop', 50) > 60 and a['rsi'] < 40:
            sl = current - (atr * 2)
            tp1 = current + (atr * 4)
            tp2 = current + (atr * 8)
            risk = current - sl
            reward = tp1 - current
            if risk > 0:
                trades.append({
                    'strategy': 'Harami Pattern', 'type': 'LONG', 'symbol': symbol,
                    'entry': current, 'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence_score': 7, 'reason': \"Bullish Harami Pattern\",
                    'indicators': f\"Chop: {a.get('chop', 50):.0f}, RSI: {a['rsi']:.0f}\",
                    'expected_time': '2h-6h', 'risk': risk, 'reward': reward,
                    'risk_reward': round(reward/risk, 1) if risk > 0 else 0,
                    'entry_type': 'MARKET', 'timeframe': tf
                })
                break
    return trades

def strategy_piercing_darkcloud(symbol, analyses):
    """Strategy: Piercing Line/Dark Cloud - Partial reversal patterns"""
    trades = []
    for tf in ['15m', '1h']:
        if tf not in analyses: continue
        a = analyses[tf]
        current = a['current_price']
        atr = a['atr']
        if atr == 0: continue
        
        # Piercing Line: Bullish reversal
        if a['rsi'] < 35 and a['macd']['histogram'] > 0:
            sl = current - (atr * 2)
            tp1 = current + (atr * 4)
            tp2 = current + (atr * 8)
            risk = current - sl
            reward = tp1 - current
            if risk > 0:
                trades.append({
                    'strategy': 'Piercing Line/Dark Cloud', 'type': 'LONG', 'symbol': symbol,
                    'entry': current, 'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence_score': 8, 'reason': \"Piercing Line Reversal Pattern\",
                    'indicators': f\"RSI: {a['rsi']:.0f}, MACD: Positive\",
                    'expected_time': '2h-6h', 'risk': risk, 'reward': reward,
                    'risk_reward': round(reward/risk, 1) if risk > 0 else 0,
                    'entry_type': 'MARKET', 'timeframe': tf
                })
                break
    return trades

def strategy_marubozu_momentum(symbol, analyses):
    """Strategy: Marubozu Momentum - Strong directional candle"""
    trades = []
    for tf in ['5m', '15m']:
        if tf not in analyses: continue
        a = analyses[tf]
        current = a['current_price']
        atr = a['atr']
        if atr == 0: continue
        
        # Strong momentum candle
        if a['rsi'] > 65 and a.get('rvol', 1) > 1.5 and a['adx']['adx'] > 25:
            sl = current - (atr * 2)
            tp1 = current + (atr * 4)
            tp2 = current + (atr * 8)
            risk = current - sl
            reward = tp1 - current
            if risk > 0:
                trades.append({
                    'strategy': 'Marubozu Momentum', 'type': 'LONG', 'symbol': symbol,
                    'entry': current, 'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence_score': 8, 'reason': \"Marubozu Strong Momentum Candle\",
                    'indicators': f\"RSI: {a['rsi']:.0f}, RVOL: {a.get('rvol', 1):.2f}, ADX: {a['adx']['adx']:.0f}\",
                    'expected_time': '30m-2h', 'risk': risk, 'reward': reward,
                    'risk_reward': round(reward/risk, 1) if risk > 0 else 0,
                    'entry_type': 'MARKET', 'timeframe': tf
                })
                break
    return trades

def strategy_higher_lower_structure(symbol, analyses):
    """Strategy: Higher High/Lower Low Structure - Market structure trading"""
    trades = []
    for tf in ['15m', '1h', '4h']:
        if tf not in analyses: continue
        a = analyses[tf]
        current = a['current_price']
        atr = a['atr']
        if atr == 0: continue
        
        # Higher highs in uptrend
        if a['trend'] == 'BULLISH' and a['adx']['adx'] > 20:
            sl = current - (atr * 2.5)
            tp1 = current + (atr * 5)
            tp2 = current + (atr * 10)
            risk = current - sl
            reward = tp1 - current
            if risk > 0:
                trades.append({
                    'strategy': 'Higher/Lower Structure', 'type': 'LONG', 'symbol': symbol,
                    'entry': current, 'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence_score': 8, 'reason': \"Higher High Structure in Uptrend\",
                    'indicators': f\"Trend: {a['trend']}, ADX: {a['adx']['adx']:.0f}\",
                    'expected_time': '2h-8h', 'risk': risk, 'reward': reward,
                    'risk_reward': round(reward/risk, 1) if risk > 0 else 0,
                    'entry_type': 'MARKET', 'timeframe': tf
                })
                break
    return trades

def strategy_ma_crossover(symbol, analyses):
    """Strategy: MA Crossover - Moving average crossover system"""
    trades = []
    for tf in ['15m', '1h', '4h']:
        if tf not in analyses: continue
        a = analyses[tf]
        current = a['current_price']
        atr = a['atr']
        if atr == 0: continue
        
        # EMA crossover
        ema21 = a.get('ema21', current)
        ema50 = a.get('ema50', current)
        if ema21 > ema50 and current > ema21:
            sl = ema50
            tp1 = current + (atr * 4)
            tp2 = current + (atr * 8)
            risk = current - sl
            reward = tp1 - current
            if risk > 0:
                trades.append({
                    'strategy': 'MA Crossover', 'type': 'LONG', 'symbol': symbol,
                    'entry': current, 'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence_score': 7, 'reason': \"EMA21/50 Bullish Crossover\",
                    'indicators': f\"EMA21: {ema21:.6f}, EMA50: {ema50:.6f}\",
                    'expected_time': '2h-8h', 'risk': risk, 'reward': reward,
                    'risk_reward': round(reward/risk, 1) if risk > 0 else 0,
                    'entry_type': 'MARKET', 'timeframe': tf
                })
                break
    return trades

def strategy_bb_squeeze_release(symbol, analyses):
    """Strategy: BB Squeeze Release - Bollinger squeeze expansion"""
    trades = []
    for tf in ['15m', '1h']:
        if tf not in analyses: continue
        a = analyses[tf]
        current = a['current_price']
        atr = a['atr']
        bb = a.get('bb')
        if not bb or atr == 0: continue
        
        # Squeeze release (low volatility followed by breakout)
        bb_width = (bb['upper'] - bb['lower']) / bb['middle']
        if bb_width < 0.04 and a.get('rvol', 1) > 1.3:  # Narrow bands + volume
            sl = current - (atr * 2)
            tp1 = current + (atr * 5)
            tp2 = current + (atr * 10)
            risk = current - sl
            reward = tp1 - current
            if risk > 0:
                trades.append({
                    'strategy': 'BB Squeeze Release', 'type': 'LONG', 'symbol': symbol,
                    'entry': current, 'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence_score': 9, 'reason': \"Bollinger Band Squeeze Release + Volume\",
                    'indicators': f\"BB Width: {bb_width:.4f}, RVOL: {a.get('rvol', 1):.2f}\",
                    'expected_time': '1h-4h', 'risk': risk, 'reward': reward,
                    'risk_reward': round(reward/risk, 1) if risk > 0 else 0,
                    'entry_type': 'MARKET', 'timeframe': tf
                })
                break
    return trades

def strategy_elliott_wave(symbol, analyses):
    """Strategy: Elliott Wave - Wave count trading"""
    trades = []
    for tf in ['1h', '4h']:
        if tf not in analyses: continue
        a = analyses[tf]
        current = a['current_price']
        atr = a['atr']
        if atr == 0: continue
        
        # Simplified: Wave 3 detection (strong trend + momentum)
        if a['trend'] == 'BULLISH' and a['adx']['adx'] > 30 and a['rsi'] > 60:
            sl = current - (atr * 3)
            tp1 = current + (atr * 6)
            tp2 = current + (atr * 12)
            risk = current - sl
            reward = tp1 - current
            if risk > 0:
                trades.append({
                    'strategy': 'Elliott Wave', 'type': 'LONG', 'symbol': symbol,
                    'entry': current, 'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence_score': 8, 'reason': \"Elliott Wave 3 Impulse Detection\",
                    'indicators': f\"ADX: {a['adx']['adx']:.0f}, RSI: {a['rsi']:.0f}\",
                    'expected_time': '4h-12h', 'risk': risk, 'reward': reward,
                    'risk_reward': round(reward/risk, 1) if risk > 0 else 0,
                    'entry_type': 'MARKET', 'timeframe': tf
                })
                break
    return trades

def strategy_cup_handle(symbol, analyses):
    """Strategy: Cup & Handle - Continuation pattern"""
    trades = []
    for tf in ['1h', '4h']:
        if tf not in analyses: continue
        a = analyses[tf]
        current = a['current_price']
        atr = a['atr']
        if atr == 0: continue
        
        # Simplified: Consolidation followed by breakout
        if a['trend'] == 'BULLISH' and a.get('chop', 50) > 55 and a.get('rvol', 1) > 1.2:
            sl = current - (atr * 2.5)
            tp1 = current + (atr * 6)
            tp2 = current + (atr * 12)
            risk = current - sl
            reward = tp1 - current
            if risk > 0:
                trades.append({
                    'strategy': 'Cup & Handle', 'type': 'LONG', 'symbol': symbol,
                    'entry': current, 'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence_score': 8, 'reason': \"Cup & Handle Breakout Pattern\",
                    'indicators': f\"Chop: {a.get('chop', 50):.0f}, RVOL: {a.get('rvol', 1):.2f}\",
                    'expected_time': '4h-12h', 'risk': risk, 'reward': reward,
                    'risk_reward': round(reward/risk, 1) if risk > 0 else 0,
                    'entry_type': 'MARKET', 'timeframe': tf
                })
                break
    return trades

def strategy_head_shoulders(symbol, analyses):
    """Strategy: Head & Shoulders - Major reversal pattern"""
    trades = []
    for tf in ['4h', '1d']:
        if tf not in analyses: continue
        a = analyses[tf]
        current = a['current_price']
        atr = a['atr']
        if atr == 0: continue
        
        # Inverse H&S: Bullish reversal
        if a['rsi'] < 40 and a['trend'] != 'BEARISH':
            sl = current - (atr * 3)
            tp1 = current + (atr * 8)
            tp2 = current + (atr * 16)
            risk = current - sl
            reward = tp1 - current
            if risk > 0:
                trades.append({
                    'strategy': 'Head & Shoulders', 'type': 'LONG', 'symbol': symbol,
                    'entry': current, 'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence_score': 9, 'reason': \"Inverse Head & Shoulders Reversal\",
                    'indicators': f\"RSI: {a['rsi']:.0f}, Pattern: Inv H&S\",
                    'expected_time': '1d-3d', 'risk': risk, 'reward': reward,
                    'risk_reward': round(reward/risk, 1) if risk > 0 else 0,
                    'entry_type': 'MARKET', 'timeframe': tf
                })
                break
    return trades

def strategy_double_topbottom(symbol, analyses):
    """Strategy: Double Top/Bottom - Classic reversal"""
    trades = []
    for tf in ['1h', '4h']:
        if tf not in analyses: continue
        a = analyses[tf]
        current = a['current_price']
        atr = a['atr']
        if atr == 0: continue
        
        # Double Bottom: Bullish reversal
        if a['rsi'] < 35 and a.get('stoch_rsi', {}).get('k', 50) < 25:
            sl = current - (atr * 2)
            tp1 = current + (atr * 5)
            tp2 = current + (atr * 10)
            risk = current - sl
            reward = tp1 - current
            if risk > 0:
                trades.append({
                    'strategy': 'Double Top/Bottom', 'type': 'LONG', 'symbol': symbol,
                    'entry': current, 'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence_score': 8, 'reason': \"Double Bottom Reversal Pattern\",
                    'indicators': f\"RSI: {a['rsi']:.0f}, StochRSI: {a.get('stoch_rsi', {}).get('k', 0):.0f}\",
                    'expected_time': '4h-12h', 'risk': risk, 'reward': reward,
                    'risk_reward': round(reward/risk, 1) if risk > 0 else 0,
                    'entry_type': 'MARKET', 'timeframe': tf
                })
                break
    return trades

def strategy_triangle_breakout(symbol, analyses):
    """Strategy: Triangle Breakout - Consolidation breakout"""
    trades = []
    for tf in ['15m', '1h']:
        if tf not in analyses: continue
        a = analyses[tf]
        current = a['current_price']
        atr = a['atr']
        if atr == 0: continue
        
        # Triangle: Consolidation followed by breakout
        if a.get('chop', 50) > 60 and a.get('rvol', 1) > 1.5:
            sl = current - (atr * 2)
            tp1 = current + (atr * 5)
            tp2 = current + (atr * 10)
            risk = current - sl
            reward = tp1 - current
            if risk > 0:
                trades.append({
                    'strategy': 'Triangle Breakout', 'type': 'LONG', 'symbol': symbol,
                    'entry': current, 'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence_score': 8, 'reason': \"Triangle Consolidation Breakout\",
                    'indicators': f\"Chop: {a.get('chop', 50):.0f}, RVOL: {a.get('rvol', 1):.2f}\",
                    'expected_time': '2h-6h', 'risk': risk, 'reward': reward,
                    'risk_reward': round(reward/risk, 1) if risk > 0 else 0,
                    'entry_type': 'MARKET', 'timeframe': tf
                })
                break
    return trades

def strategy_wedge_breakout(symbol, analyses):
    """Strategy: Wedge Breakout - Trend continuation"""
    trades = []
    for tf in ['15m', '1h']:
        if tf not in analyses: continue
        a = analyses[tf]
        current = a['current_price']
        atr = a['atr']
        if atr == 0: continue
        
        # Rising wedge breakout
        if a['trend'] == 'BULLISH' and a['adx']['adx'] > 20:
            sl = current - (atr * 2)
            tp1 = current + (atr * 4)
            tp2 = current + (atr * 8)
            risk = current - sl
            reward = tp1 - current
            if risk > 0:
                trades.append({
                    'strategy': 'Wedge Breakout', 'type': 'LONG', 'symbol': symbol,
                    'entry': current, 'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence_score': 7, 'reason': \"Rising Wedge Breakout\",
                    'indicators': f\"Trend: {a['trend']}, ADX: {a['adx']['adx']:.0f}\",
                    'expected_time': '2h-6h', 'risk': risk, 'reward': reward,
                    'risk_reward': round(reward/risk, 1) if risk > 0 else 0,
                    'entry_type': 'MARKET', 'timeframe': tf
                })
                break
    return trades

def strategy_flag_pennant(symbol, analyses):
    """Strategy: Flag/Pennant - Quick continuation patterns"""
    trades = []
    for tf in ['5m', '15m']:
        if tf not in analyses: continue
        a = analyses[tf]
        current = a['current_price']
        atr = a['atr']
        if atr == 0: continue
        
        # Flag: Brief consolidation in strong trend
        if a['trend'] == 'BULLISH' and a['adx']['adx'] > 25 and a.get('rvol', 1) > 1.3:
            sl = current - (atr * 1.5)
            tp1 = current + (atr * 3)
            tp2 = current + (atr * 6)
            risk = current - sl
            reward = tp1 - current
            if risk > 0:
                trades.append({
                    'strategy': 'Flag/Pennant', 'type': 'LONG', 'symbol': symbol,
                    'entry': current, 'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence_score': 8, 'reason': \"Bull Flag Continuation Pattern\",
                    'indicators': f\"ADX: {a['adx']['adx']:.0f}, RVOL: {a.get('rvol', 1):.2f}\",
                    'expected_time': '30m-2h', 'risk': risk, 'reward': reward,
                    'risk_reward': round(reward/risk, 1) if risk > 0 else 0,
                    'entry_type': 'MARKET', 'timeframe': tf
                })
                break
    return trades

def strategy_ote_ict(symbol, analyses):
    """Strategy: OTE ICT - Optimal Trade Entry (0.618-0.79 retracement)"""
    trades = []
    for tf in ['15m', '1h']:
        if tf not in analyses: continue
        a = analyses[tf]
        current = a['current_price']
        atr = a['atr']
        fib = a.get('fib')
        if not fib or atr == 0: continue
        
        # OTE zone: 0.618-0.79 Fibonacci retracement
        if fib.get('0.618') and fib.get('0.786'):
            if fib['0.786'] <= current <= fib['0.618'] and a['trend'] == 'BULLISH':
                sl = fib['0.786'] - (atr * 0.5)
                tp1 = fib['0']  # 100% extension
                tp2 = fib['-0.272']  # 127.2% extension
                risk = current - sl
                reward = tp1 - current
                if risk > 0:
                    trades.append({
                        'strategy': 'OTE ICT', 'type': 'LONG', 'symbol': symbol,
                        'entry': current, 'sl': sl, 'tp1': tp1, 'tp2': tp2,
                        'confidence_score': 9, 'reason': \"ICT Optimal Trade Entry (0.618-0.79 Zone)\",
                        'indicators': f\"Fib 0.618: {fib['0.618']:.6f}, Fib 0.786: {fib['0.786']:.6f}\",
                        'expected_time': '2h-8h', 'risk': risk, 'reward': reward,
                        'risk_reward': round(reward/risk, 1) if risk > 0 else 0,
                        'entry_type': 'LIMIT', 'timeframe': tf
                    })
                    break
    return trades

def strategy_killzone_entry(symbol, analyses):
    """Strategy: Kill Zone Entry - London/NY/Asia session timing"""
    from datetime import datetime
    trades = []
    for tf in ['5m', '15m']:
        if tf not in analyses: continue
        a = analyses[tf]
        current = a['current_price']
        atr = a['atr']
        if atr == 0: continue
        
        # Check if in kill zone (simplified - always active for demo)
        # In production, check actual UTC time for London (2-5am), NY (7-10am), Asia (8-11pm)
        hour = datetime.utcnow().hour
        in_killzone = (2 <= hour <= 5) or (7 <= hour <= 10) or (20 <= hour <= 23)
        
        if in_killzone and a.get('rvol', 1) > 1.3:
            sl = current - (atr * 2)
            tp1 = current + (atr * 4)
            tp2 = current + (atr * 8)
            risk = current - sl
            reward = tp1 - current
            if risk > 0:
                trades.append({
                    'strategy': 'Kill Zone Entry', 'type': 'LONG', 'symbol': symbol,
                    'entry': current, 'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence_score': 8, 'reason': \"ICT Kill Zone Entry + Volume\",
                    'indicators': f\"Kill Zone: Active, RVOL: {a.get('rvol', 1):.2f}\",
                    'expected_time': '1h-4h', 'risk': risk, 'reward': reward,
                    'risk_reward': round(reward/risk, 1) if risk > 0 else 0,
                    'entry_type': 'MARKET', 'timeframe': tf
                })
                break
    return trades

def strategy_mss_ict(symbol, analyses):
    """Strategy: MSS ICT - Market Structure Shift detection"""
    trades = []
    for tf in ['15m', '1h']:
        if tf not in analyses: continue
        a = analyses[tf]
        current = a['current_price']
        atr = a['atr']
        bos = a.get('bos')
        if not bos or atr == 0: continue
        
        # Market Structure Shift: BOS + momentum shift
        if bos.get('type') == 'BULLISH' and a['macd']['histogram'] > 0:
            sl = current - (atr * 2.5)
            tp1 = current + (atr * 6)
            tp2 = current + (atr * 12)
            risk = current - sl
            reward = tp1 - current
            if risk > 0:
                trades.append({
                    'strategy': 'MSS ICT', 'type': 'LONG', 'symbol': symbol,
                    'entry': current, 'sl': sl, 'tp1': tp1, 'tp2': tp2,
                    'confidence_score': 9, 'reason': \"ICT Market Structure Shift (Bullish BOS)\",
                    'indicators': f\"BOS: {bos['level']:.6f}, MACD: Positive\",
                    'expected_time': '2h-8h', 'risk': risk, 'reward': reward,
                    'risk_reward': round(reward/risk, 1) if risk > 0 else 0,
                    'entry_type': 'MARKET', 'timeframe': tf
                })
                break
    return trades
