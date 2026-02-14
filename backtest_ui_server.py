#!/usr/bin/env python3
"""
Backtest UI Server for RBot Pro

Provides a separate, professional web UI for backtesting signals stored in
`signals_history.json` with:
- Exchange selector
- Strategy selector
- Timeframe selector
- Custom initial capital and risk % per trade
- Per-trade and aggregate PnL (price % and account currency)

This runs independently from `web_ui_server.py` so you can keep analysis
and backtesting separate.
"""

import os
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from flask import Flask, jsonify, render_template, request

# Reuse the candle fetching and timestamp logic from backtest_signals
from backtest_signals import get_utc_timestamp, fetch_candles, MIN_AGE_MINUTES, SIGNALS_FILE


app = Flask(__name__, template_folder='templates', static_folder='static')

# Canonical list of exchanges used by RBot Pro (for UI selectors)
ALL_EXCHANGES = [
    'MEXC',
    'BINANCE',
    'BYBIT',
    'OKX',
    'BITGET',
    'KUCOIN',
    'GATEIO',
    'HTX',
]

# Canonical list of strategy names as emitted by fast_analysis.py
# (kept in sync with `'strategy': '<Name>'` fields to ensure UI always
# exposes every available strategy, even if some haven't fired yet).
ALL_STRATEGIES = sorted({
    'Swing Trend',
    'Scalp Momentum',
    'StochRSI Pullback',
    'SuperTrend Rebound',
    'SuperTrend Rejection',
    'VWAP Reversion',
    'Ichimoku Master',
    'FVG Imbalance',
    'Divergence Pro',
    'ADX Momentum',
    'Volatility Breakout',
    'BB Reversion',
    'Liquidity Grab',
    'WaveTrend Extreme',
    'Squeeze Break',
    'Z-Scalp',
    'MFI Reversion',
    'Fisher Pivot',
    'Volume Spike',
    'SMC CHoCH',
    'Donchian Break',
    'STC Momentum',
    'Vortex Trend',
    'ICT Silver Bullet',
    'KC Reversion',
    'Quantum Elite 2026',
    'SMC Elite (X-Confluence)',
    'Vol-Capitulation',
    'Mom-Confluence',
    'ICT-Wealth-Div',
    'Harmonic-Retracement',
    'UT Bot Elite',
    'Keltner Reversion',
    'PSAR-TEMA Scalp',
    'KAMA-Volatility Scalp',
    'VFI Perfect Scalper',
    'Regime-Adaptive',
    'Wyckoff-Spring',
    'Wyckoff-Upthrust',
    'Triple-Confluence',
    'Z-Reversion',
    'MTF-TrendRider',
    'SmartMoney-Trap',
    'Mom-Exhaustion',
})


def load_signals():
    """Load signals_history.json as a list. Returns [] on error."""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base_dir, SIGNALS_FILE)
        if not os.path.exists(path):
            return []
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def build_options(signals):
    """Derive available exchanges and timeframes from signals, and expose all known strategies."""
    exchanges = set()
    strategies = set()
    timeframes = set()

    for s in signals:
        exch = str(s.get('exchange', 'BINANCE')).upper()
        strategy = s.get('strategy', 'UNKNOWN')
        tf = s.get('timeframe', 'N/A')
        if exch:
            exchanges.add(exch)
        if strategy:
            strategies.add(strategy)
        if tf:
            timeframes.add(tf)

    # Always expose all supported exchanges in the selector, even if
    # history currently only contains a subset.
    exchanges.update(ALL_EXCHANGES)

    # Strategies come from canonical list + any custom names observed in history
    strategies.update(ALL_STRATEGIES)

    return {
        'exchanges': sorted(exchanges),
        'strategies': sorted(strategies),
        'timeframes': sorted(timeframes),
    }


def _filter_signals(signals, selected_exchanges, selected_strategies,
                    selected_timeframes, min_age_minutes, only_elite=True):
    """Apply all filters and basic validation to raw signals."""
    now = datetime.now()
    backtestable = []

    for sig in signals:
        try:
            # 1) Optional conflict filter - by default we skip those
            if sig.get('conflict_warning'):
                continue

            # 2) Optional quality filter - ELITE only by default
            if only_elite:
                quality = str(sig.get('signal_quality', '')).upper()
                if quality != 'ELITE':
                    continue

            exchange = str(sig.get('exchange', 'BINANCE')).upper()
            strategy = sig.get('strategy', 'UNKNOWN')
            tf = sig.get('timeframe', 'N/A')

            if selected_exchanges and exchange not in selected_exchanges:
                continue
            if selected_strategies and strategy not in selected_strategies:
                continue
            if selected_timeframes and tf not in selected_timeframes:
                continue

            ts_str = sig.get('timestamp')
            if not ts_str:
                continue

            sig_dt = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S')
            age = now - sig_dt
            if age.total_seconds() < (min_age_minutes * 60):
                # Too fresh, skip for backtesting
                continue

            sig['_dt'] = sig_dt
            sig['_age_str'] = str(age).split('.')[0]
            backtestable.append(sig)
        except Exception:
            continue

    return backtestable


def _evaluate_signal(sig):
    """
    Evaluate ONE signal using the same candle logic as `backtest_signals.py`.
    Returns dict with outcome & price-based pnl%.
    """
    symbol = sig['symbol']
    direction = sig['type']
    exchange = sig.get('exchange', 'Binance')
    entry = float(sig['entry'])
    tp1 = float(sig['tp1'])
    sl = float(sig['sl'])

    start_ms = get_utc_timestamp(sig['timestamp'])
    candles = fetch_candles(symbol, start_ms, exchange)

    outcome = "PENDING"
    pnl_pct = 0.0
    reason = ""
    entry_type = str(sig.get('entry_type', 'MARKET')).upper()
    state = "WAITING" if entry_type != 'MARKET' else "RUNNING"

    if candles:
        last_close = float(candles[-1][4])
        for c in candles:
            c_high = float(c[2])
            c_low = float(c[3])
            
            if state == "WAITING":
                # Entry Trigger logic
                if direction == 'LONG':
                    if entry_type == 'LIMIT':
                        if c_low <= entry: state = "RUNNING"
                    elif entry_type in ['STOP-MARKET', 'STOP_LIMIT', 'STOP']:
                        if c_high >= entry: state = "RUNNING"
                else: # SHORT
                    if entry_type == 'LIMIT':
                        if c_high >= entry: state = "RUNNING"
                    elif entry_type in ['STOP-MARKET', 'STOP_LIMIT', 'STOP']:
                        if c_low <= entry: state = "RUNNING"
                
                if state == "WAITING": continue
                
            if state == "RUNNING":
                if direction == 'LONG':
                    if c_low <= sl:
                        outcome = "LOSS"
                        pnl_pct = (sl - entry) / entry * 100
                        reason = f"Hit SL at {sl:.2f}"
                        break
                    if c_high >= tp1:
                        outcome = "WIN"
                        pnl_pct = (tp1 - entry) / entry * 100
                        reason = f"Hit TP1 at {tp1:.2f}"
                        break
                elif direction == 'SHORT':
                    if c_high >= sl:
                        outcome = "LOSS"
                        pnl_pct = (entry - sl) / entry * 100
                        reason = f"Hit SL at {sl:.2f}"
                        break
                    if c_low <= tp1:
                        outcome = "WIN"
                        pnl_pct = (entry - tp1) / entry * 100
                        reason = f"Hit TP1 at {tp1:.2f}"
                        break

        if outcome == 'PENDING':
            if state == "WAITING":
                outcome = "WAITING"
                reason = f"Waiting for {entry_type} entry at {entry:.2f}"
            else:
                if direction == 'LONG':
                    pnl_pct = (last_close - entry) / entry * 100
                else:
                    pnl_pct = (entry - last_close) / entry * 100
                reason = f"Trade Active (Last: {last_close:.2f})"
    else:
        outcome = "NO_DATA"
        reason = "Market data unavailable for this period"

    return {
        'sig': sig,
        'outcome': outcome,
        'pnl_pct': pnl_pct,
        'reason': reason,
        'exchange': exchange,
    }


def _compute_capital_path(results, initial_capital, risk_percent):
    """
    Walk through signals chronologically and simulate account equity using
    risk% per trade and R:R from each signal's SL/TP.
    """
    # Sort results by signal timestamp
    ordered = sorted(results, key=lambda r: r['sig']['timestamp'])

    capital = float(initial_capital)
    risk_pct = float(risk_percent)
    trades_out = []

    for res in ordered:
        sig = res['sig']
        outcome = res['outcome']
        pnl_price_pct = res['pnl_pct']
        reason = res.get('reason', '')

        # Extract price levels
        try:
            entry = float(sig['entry'])
            sl = float(sig['sl'])
            tp1 = float(sig['tp1'])
        except Exception:
            # If any field is missing, keep capital unchanged
            trades_out.append({
                'signal': sig,
                'outcome': outcome,
                'reason': reason,
                'pnl_price_pct': pnl_price_pct,
                'capital_before': capital,
                'risk_amount': 0.0,
                'pnl_amount': 0.0,
                'capital_after': capital,
            })
            continue

        # Compute per-trade risk & R:R from price structure
        if entry == sl:
            # Invalid SL
            risk_amount = 0.0
            pnl_amount = 0.0
            trades_out.append({
                'signal': sig,
                'outcome': outcome,
                'reason': reason,
                'pnl_price_pct': pnl_price_pct,
                'capital_before': capital,
                'risk_amount': risk_amount,
                'pnl_amount': pnl_amount,
                'capital_after': capital,
            })
            continue

        if sig['type'] == 'LONG':
            risk_dist = max(0.0, entry - sl)
            reward_dist = max(0.0, tp1 - entry)
        else:  # SHORT
            risk_dist = max(0.0, sl - entry)
            reward_dist = max(0.0, entry - tp1)

        if risk_dist <= 0.0 or reward_dist <= 0.0:
            rr = 0.0
        else:
            rr = reward_dist / risk_dist

        capital_before = capital
        risk_amount = capital * (risk_pct / 100.0)
        pnl_amount = 0.0

        if outcome == 'WIN':
            pnl_amount = risk_amount * rr
            capital += pnl_amount
        elif outcome == 'LOSS':
            pnl_amount = -risk_amount
            capital += pnl_amount
        else:
            # PENDING / NO_DATA → treat as unrealized; capital unchanged
            pnl_amount = 0.0

        trades_out.append({
            'signal': sig,
            'outcome': outcome,
            'reason': reason,
            'pnl_price_pct': pnl_price_pct,
            'capital_before': round(capital_before, 2),
            'risk_amount': round(risk_amount, 2),
            'pnl_amount': round(pnl_amount, 2),
            'capital_after': round(capital, 2),
            'rr': round(rr, 2) if rr else 0.0,
        })

    return trades_out, capital


@app.route('/')
def index():
    """Serve the backtest UI."""
    return render_template('backtest_ui.html')


@app.route('/api/backtest/options', methods=['GET'])
def api_options():
    """Return dynamic options derived from signals_history.json."""
    signals = load_signals()
    opts = build_options(signals)
    # Provide some sensible defaults for the UI
    opts.update({
        'defaults': {
            'initial_capital': 10000.0,
            'risk_percent': 1.0,
            'min_age_minutes': MIN_AGE_MINUTES,
            'only_elite': True,
        }
    })
    return jsonify(opts)


@app.route('/api/backtest/run', methods=['POST'])
def api_run_backtest():
    """
    Run a customizable backtest over signals_history.json.

    Expected JSON body:
    {
      "exchanges": ["MEXC", "BINANCE"],
      "strategies": ["PSAR-TEMA Scalp"],
      "timeframes": ["1m","3m","5m"],
      "initial_capital": 10000,
      "risk_percent": 1.0,
      "min_age_minutes": 5,
      "only_elite": true
    }
    """
    payload = request.json or {}

    # Parse filters
    selected_exchanges = [str(e).upper() for e in payload.get('exchanges', []) if e]
    selected_strategies = [str(s) for s in payload.get('strategies', []) if s]
    selected_timeframes = [str(tf) for tf in payload.get('timeframes', []) if tf]

    initial_capital = float(payload.get('initial_capital', 10000.0))
    risk_percent = float(payload.get('risk_percent', 1.0))
    min_age_minutes = int(payload.get('min_age_minutes', MIN_AGE_MINUTES))
    only_elite = bool(payload.get('only_elite', True))

    signals = load_signals()
    if not signals:
        return jsonify({'error': 'No signals found in signals_history.json'}), 400

    filtered = _filter_signals(
        signals,
        selected_exchanges=selected_exchanges,
        selected_strategies=selected_strategies,
        selected_timeframes=selected_timeframes,
        min_age_minutes=min_age_minutes,
        only_elite=only_elite,
    )

    if not filtered:
        return jsonify({
            'error': 'No signals match the selected filters (age/quality/exchange/strategy/timeframe).'
        }), 400

    # Evaluate all signals (price-only outcome + pnl%)
    results = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(_evaluate_signal, sig) for sig in filtered]
        for fut in as_completed(futures):
            try:
                results.append(fut.result())
            except Exception:
                continue

    if not results:
        return jsonify({'error': 'Failed to evaluate any signals (API issues or invalid data).'}), 500

    # Aggregate basic stats
    agg = {
        'total': 0,
        'wins': 0,
        'losses': 0,
        'pending': 0,
        'no_data': 0,
        'total_pnl_price_pct': 0.0,
    }

    # Strategy/TF Performance Tracking
    combo_stats = {}

    for res in results:
        agg['total'] += 1
        outcome = res['outcome']
        pnl_pct = res['pnl_pct']
        sig = res['sig']
        
        strategy = sig.get('strategy', 'UNKNOWN')
        tf = sig.get('timeframe', 'N/A')
        key = f"{strategy}|{tf}"
        
        if key not in combo_stats:
            combo_stats[key] = {
                'strategy': strategy,
                'timeframe': tf,
                'total': 0, 
                'wins': 0, 
                'losses': 0, 
                'pending': 0,
                'pnl': 0.0
            }
        
        stats = combo_stats[key]
        stats['total'] += 1

        if outcome == 'WIN':
            agg['wins'] += 1
            agg['total_pnl_price_pct'] += pnl_pct
            stats['wins'] += 1
            stats['pnl'] += pnl_pct
        elif outcome == 'LOSS':
            agg['losses'] += 1
            agg['total_pnl_price_pct'] += pnl_pct
            stats['losses'] += 1
            stats['pnl'] += pnl_pct
        elif outcome == 'PENDING':
            agg['pending'] += 1
            stats['pending'] += 1
        else:
            agg['no_data'] += 1

    # Calculate Best Performer PER TIMEFRAME
    tf_best = {}
    for key, s in combo_stats.items():
        total_closed = s['wins'] + s['losses']
        if total_closed > 0 and s['pnl'] > 0:
            win_rate = (s['wins'] / total_closed) * 100
            score = s['pnl'] * (total_closed ** 0.5)
            tf = s['timeframe']
            
            perf = {
                'strategy': s['strategy'],
                'timeframe': tf,
                'win_rate': round(win_rate, 2),
                'total_trades': s['total'],
                'closed_trades': total_closed,
                'wins': s['wins'],
                'losses': s['losses'],
                'pending_trades': s['pending'],
                'pnl_pct': round(s['pnl'], 2),
                'score': score
            }
            
            if tf not in tf_best or score > tf_best[tf]['score']:
                tf_best[tf] = perf
    
    # Sort performers by timeframe (optional: or by score)
    best_performers = sorted(tf_best.values(), key=lambda x: x['timeframe'])

    # Simulate capital path with risk% logic
    trades_with_capital, final_capital = _compute_capital_path(results, initial_capital, risk_percent)

    closed_trades = [t for t in trades_with_capital if t['outcome'] in ('WIN', 'LOSS')]
    realized_pnl_amount = round(final_capital - initial_capital, 2)
    realized_pnl_pct = round((realized_pnl_amount / initial_capital) * 100.0, 2) if initial_capital > 0 else 0.0

    win_rate = 0.0
    if agg['wins'] + agg['losses'] > 0:
        win_rate = round(agg['wins'] / (agg['wins'] + agg['losses']) * 100.0, 2)

    response = {
        'filters': {
            'exchanges': selected_exchanges,
            'strategies': selected_strategies,
            'timeframes': selected_timeframes,
            'min_age_minutes': min_age_minutes,
            'only_elite': only_elite,
            'initial_capital': initial_capital,
            'risk_percent': risk_percent,
        },
        'summary': {
            'total_signals': agg['total'],
            'wins': agg['wins'],
            'losses': agg['losses'],
            'pending': agg['pending'],
            'no_data': agg['no_data'],
            'win_rate_percent': win_rate,
            'final_capital': round(final_capital, 2),
            'initial_capital': round(initial_capital, 2),
            'realized_pnl_amount': realized_pnl_amount,
            'realized_pnl_percent': realized_pnl_pct,
        },
        'best_performers': best_performers,
        # Price-based aggregation (sum of individual price PnLs) – mostly diagnostic
        'price_pnl': {
            'total_pnl_percent_sum': round(agg['total_pnl_price_pct'], 2),
        },
        # Detailed trade list for UI (can be sliced client-side)
        'trades': trades_with_capital,
        'closed_trades': closed_trades,
    }

    return jsonify(response)


if __name__ == '__main__':
    print("🌐 RBot Pro Backtest UI Server")
    print("📱 Open: http://localhost:5100")
    app.run(host='0.0.0.0', port=5100, debug=False)

