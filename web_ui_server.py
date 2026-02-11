#!/usr/bin/env python3
"""
Advanced Web UI Server for RBot Pro Multi-Exchange Real-Time Analysis
Features: Multi-Exchange Support, Symbol/Indicator Selection, Auto-Run, Customizable Strategies
"""

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import subprocess
import threading
import sys
import os
import queue
from datetime import datetime
import json
from apscheduler.schedulers.background import BackgroundScheduler
import time

# Import News Manager
from news_manager import news_manager

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SECRET_KEY'] = 'rbot-pro-analysis-ui-secret'

# SocketIO with explicit threading for stability on Windows
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='threading',
    ping_timeout=120,
    ping_interval=30
)

# Global state
analysis_running = False
analysis_thread = None
active_process = None  # Track the running subprocess
scheduler = BackgroundScheduler()
output_queue = queue.Queue()

config = {
    'symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT'],
    'indicators': ['RSI', 'EMA', 'MACD', 'BB', 'ATR', 'ADX', 'OB', 'PA', 'StochRSI', 'OBV', 'ST', 'VWAP', 'HMA', 'CMF', 'ICHI', 'FVG', 'DIV', 'WT', 'SQZ', 'LIQ', 'BOS', 'MFI', 'FISH', 'ZLSMA', 'TSI', 'CHOP', 'VI', 'STC', 'DON', 'CHoCH', 'KC', 'UTBOT', 'UO', 'STDEV', 'VP', 'SUPDEM', 'FIB', 'ICT_WD', 'PSAR', 'TEMA', 'CHANDELIER', 'KAMA', 'VFI'],
    'min_confidence': 5,
    'timeframes': ['1m', '3m', '5m', '15m', '30m', '1h', '4h', '1d'],
    'exchanges': ['MEXC', 'Binance'],
    'auto_run': False,
    'auto_run_interval': 300,
    'risk_profile': 'moderate',
    'telegram_token': '',
    'telegram_chat_id': ''
}

def send_telegram_alert(trade):
    """Send trade alert to Telegram if configured"""
    token = config.get('telegram_token')
    chat_id = config.get('telegram_chat_id')
    if not token or not chat_id: return
    
    action = "🚀 BUY" if trade['type'] == 'LONG' else "🔻 SELL"
    msg = f"""🔥 *[RBot Pro] TRADE ALERT*
━━━━━━━━━━━━━━━━━━━━
🏢 *Exchange:* {trade.get('exchange', 'N/A')}
📈 *Signal:* {action} {trade['symbol']} ({trade['timeframe']})
📍 *Entry:* ${trade['entry']:.6f}
🛑 *SL:* ${trade['sl']:.6f}
🎯 *TP:* ${trade['tp1']:.6f}
💎 *R/R:* {trade['risk_reward']}:1
🔍 *Reason:* {trade['reason']}
━━━━━━━━━━━━━━━━━━━━
*by RBot Pro — World's Best AI Bot!* 🏆"""
    
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={
            "chat_id": chat_id,
            "text": msg,
            "parse_mode": "Markdown"
        }, timeout=5)
    except Exception as e:
        print(f"Telegram error: {e}")

def stream_output_loop():
    """Background thread that reads from queue and broadcasts to clients"""
    while True:
        try:
            line = output_queue.get(timeout=1)
            if line:
                # Parse trade data for global signals box & Telegram
                if 'SIGNAL_DATA:' in line:
                    try:
                        trade_json = line.split('SIGNAL_DATA:')[1].strip()
                        trade = json.loads(trade_json)
                        
                        # INJECT MARKET WARNING IF EXISTS
                        status = news_manager.get_market_status()
                        if status.get('volatility_warning'):
                            trade['warning'] = status['volatility_warning']
                        if status.get('news_warning'):
                            trade['warning'] = f"{trade.get('warning', '')} {status['news_warning']}"
                            
                        socketio.emit('trade', trade, namespace='/')
                        # Forward to Telegram
                        thread = threading.Thread(target=send_telegram_alert, args=(trade,), daemon=True)
                        thread.start()
                    except:
                        pass
                
                socketio.emit('output', {'data': line}, namespace='/')
        except queue.Empty:
            continue
        except Exception as e:
            print(f"Stream error: {e}")

def market_monitor_loop():
    """Background thread to monitor market news and volatility"""
    last_news_time = 0
    while True:
        try:
            current_time = time.time()
            
            # check volatility every 5 seconds
            news_manager.check_btc_volatility()
            
            # fetch news every 5 seconds
            if current_time - last_news_time >= 5:
                news_manager.fetch_news()
                last_news_time = current_time
                
            # Broadcast status
            status = news_manager.get_market_status()
            socketio.emit('market_status', status, namespace='/')
            
            # If severe warning, maybe log it
            if status.get('volatility_warning'):
                # We don't want to spam the log, so maybe just trust the UI update
                # or send a special alert event
                pass
                
            time.sleep(2)
            
        except Exception as e:
            print(f"Market Monitor Error: {e}")
            time.sleep(10)

def run_analysis_subprocess(symbols, indicators, timeframes, min_conf):
    """Run the analysis script with custom parameters"""
    global analysis_running, active_process
    analysis_running = True
    
    try:
        cmd = [
            sys.executable, 'fast_analysis.py',
            '--symbols', ','.join(symbols),
            '--indicators', ','.join(indicators),
            '--timeframes', ','.join(timeframes),
            '--min-confidence', str(min_conf),
            '--exchanges', ','.join(config.get('exchanges', ['MEXC', 'Binance']))
        ]
        
        output_queue.put(f"🚀 Running: {' '.join(cmd)}\n")
        
        # Set UTF-8 encoding environment variables
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUNBUFFERED'] = '1'
        
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            env=env
        )
        active_process = proc
        
        # Stream output to queue - read bytes and decode
        for line_bytes in iter(proc.stdout.readline, b''):
            line = line_bytes.decode('utf-8', errors='replace')
            if line:
                if line.startswith('SIGNAL_DATA:'):
                    try:
                        signal_str = line.split('SIGNAL_DATA:')[1].strip()
                        signal_data = json.loads(signal_str)
                        socketio.emit('trade_signal', signal_data, namespace='/')
                    except Exception as e:
                        print(f"Error parsing trade signal: {e}")
                    continue # Skip showing raw JSON data in the terminal
                output_queue.put(line)
        
        # Process has ended — safely get return code
        try:
            proc.wait(timeout=5)
            exit_code = proc.returncode
        except Exception:
            exit_code = -1
        
        # Only emit 'completed' if it wasn't already stopped by the stop handler
        if analysis_running:
            output_queue.put(f"\n✅ Analysis completed (exit code: {exit_code})\n")
            socketio.emit('status', {'status': 'completed', 'code': exit_code}, namespace='/')
        
    except Exception as e:
        error_msg = str(e)
        # Don't report errors from being killed/stopped
        if 'killed' not in error_msg.lower() and 'terminated' not in error_msg.lower():
            output_queue.put(f"❌ ERROR: {error_msg}\n")
            socketio.emit('status', {'status': 'error'}, namespace='/')
    finally:
        analysis_running = False
        active_process = None


def auto_run_analysis():
    """Auto-run analysis on schedule"""
    if config['auto_run'] and not analysis_running:
        output_queue.put(f"🤖 Auto-run triggered at {datetime.now().strftime('%H:%M:%S')}\n")
        socketio.emit('status', {'status': 'auto_triggered'}, namespace='/')
        thread = threading.Thread(
            target=run_analysis_subprocess,
            args=(config['symbols'], config['indicators'], config['timeframes'], config['min_confidence']),
            daemon=True
        )
        thread.start()

@app.route('/')
def index():
    """Serve main UI"""
    return render_template('ui.html')

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration"""
    return jsonify(config)

@app.route('/api/config', methods=['POST'])
def update_config():
    """Update configuration"""
    global config
    data = request.json or {}
    
    if 'symbols' in data:
        config['symbols'] = data['symbols']
    if 'indicators' in data:
        config['indicators'] = data['indicators']
    if 'timeframes' in data:
        config['timeframes'] = data['timeframes']
    if 'min_confidence' in data:
        config['min_confidence'] = data['min_confidence']
    if 'exchanges' in data:
        config['exchanges'] = data['exchanges']
    if 'auto_run' in data:
        config['auto_run'] = data['auto_run']
        update_scheduler()
        if config['auto_run']:
            # Trigger immediately for better UX
            auto_run_analysis()
        else:
            # Stop analysis immediately if turning OFF
            handle_stop()
    if 'auto_run_interval' in data:
        config['auto_run_interval'] = data['auto_run_interval']
        update_scheduler()
    if 'risk_profile' in data:
        config['risk_profile'] = data['risk_profile']
    if 'telegram_token' in data:
        config['telegram_token'] = data['telegram_token']
    if 'telegram_chat_id' in data:
        config['telegram_chat_id'] = data['telegram_chat_id']
    
    socketio.emit('config_updated', config, namespace='/')
    return jsonify({'status': 'ok', 'config': config})

@app.route('/api/available-coins', methods=['GET'])
def get_available_coins():
    """Get top 100 coins from EACH selected exchange, then merge and deduplicate"""
    default_top = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT']
    all_coins_set = set(default_top)
    import requests
    
    selected_exchanges = config.get('exchanges', ['MEXC', 'Binance'])
    n = 100 # Top 100 per exchange
    
    # Try fetching from each selected exchange
    if 'MEXC' in selected_exchanges:
        try:
            r = requests.get('https://contract.mexc.com/api/v1/contract/detail', timeout=10)
            data = r.json()
            if data.get('success') and isinstance(data.get('data'), list):
                contracts = [c for c in data['data'] if c.get('symbol', '').endswith('_USDT')]
                # Sort by volume and take top 100
                contracts_sorted = sorted(contracts, key=lambda x: float(x.get('last24hVol', 0)), reverse=True)
                for item in contracts_sorted[:n]:
                    sym = item.get('symbol', '')
                    all_coins_set.add(sym.replace('_', ''))
        except Exception as e:
            print(f"Error fetching MEXC coins: {e}")
    
    if 'Binance' in selected_exchanges:
        try:
            r = requests.get('https://api.binance.com/api/v3/ticker/24hr', timeout=10)
            data = r.json()
            # Filter for USDT pairs FIRST
            usdt_pairs = [item for item in data if item.get('symbol', '').endswith('USDT')]
            # Sort by quoteVolume (USDT volume)
            binance_sorted = sorted(usdt_pairs, key=lambda x: float(x.get('quoteVolume', 0)), reverse=True)
            for item in binance_sorted[:n]:
                all_coins_set.add(item['symbol'])
        except Exception as e:
            print(f"Error fetching Binance coins: {e}")
    
    if 'Bybit' in selected_exchanges:
        try:
            r = requests.get('https://api.bybit.com/v5/market/tickers?category=linear', timeout=10)
            data = r.json()
            if data.get('result') and data['result'].get('list'):
                # Filter USDT pairs
                usdt_pairs = [item for item in data['result']['list'] if item.get('symbol', '').endswith('USDT')]
                # Sort by turnover24h
                bybit_sorted = sorted(usdt_pairs, key=lambda x: float(x.get('turnover24h', 0)), reverse=True)
                for item in bybit_sorted[:n]:
                    all_coins_set.add(item['symbol'])
        except Exception as e:
            print(f"Error fetching Bybit coins: {e}")
    
    if 'Bitget' in selected_exchanges:
        try:
            r = requests.get('https://api.bitget.com/api/v2/mix/market/tickers?productType=USDT-FUTURES', timeout=10)
            data = r.json()
            if data.get('data'):
                # Filter USDT pairs
                usdt_pairs = [item for item in data['data'] if item.get('symbol', '').endswith('USDT')]
                for item in usdt_pairs[:n]:
                    all_coins_set.add(item['symbol'])
        except Exception as e:
            print(f"Error fetching Bitget coins: {e}")
    
    if 'OKX' in selected_exchanges:
        try:
            r = requests.get('https://www.okx.com/api/v5/market/tickers?instType=SWAP', timeout=10)
            data = r.json()
            if data.get('data'):
                # Filter USDT pairs
                usdt_pairs = [item for item in data['data'] if '-USDT-' in item.get('instId', '')]
                for item in usdt_pairs[:n]:
                    inst_id = item.get('instId', '')
                    sym = inst_id.replace('-', '').replace('SWAP', '').strip()
                    all_coins_set.add(sym)
        except Exception as e:
            print(f"Error fetching OKX coins: {e}")
    
    if 'KuCoin' in selected_exchanges:
        try:
            r = requests.get('https://api.kucoin.com/api/v1/market/allTickers', timeout=10)
            data = r.json()
            if data.get('data') and data['data'].get('ticker'):
                # Filter USDT pairs
                usdt_pairs = [item for item in data['data']['ticker'] if item.get('symbol', '').endswith('-USDT')]
                # Sort by volValue (usually USDT volume)
                kucoin_sorted = sorted(usdt_pairs, key=lambda x: float(x.get('volValue', 0)), reverse=True)
                for item in kucoin_sorted[:n]:
                    sym = item.get('symbol', '')
                    all_coins_set.add(sym.replace('-', ''))
        except Exception as e:
            print(f"Error fetching KuCoin coins: {e}")
    
    if 'GateIO' in selected_exchanges:
        try:
            r = requests.get('https://api.gateio.ws/api/v4/futures/usdt/contracts', timeout=10)
            data = r.json()
            # GateIO contracts
            for item in data[:n]:
                name = item.get('name', '')
                if name.endswith('_USDT'):
                    all_coins_set.add(name.replace('_', ''))
        except Exception as e:
            print(f"Error fetching Gate.io coins: {e}")
    
    if 'HTX' in selected_exchanges:
        try:
            r = requests.get('https://api.huobi.pro/v2/settings/common/symbols', timeout=10)
            data = r.json()
            if data.get('data'):
                for item in data['data'][:200]: # HTX symbols list is unordered, take more and filter
                    sym = item.get('sc', '')
                    if sym.endswith('usdt'):
                        all_coins_set.add(sym.upper())
                        if len(all_coins_set) > 1000: break # Safety cap
        except Exception as e:
            print(f"Error fetching HTX coins: {e}")
    
    if not all_coins_set:
        return jsonify({'coins': default_top})
    
    # Sort the final list alphabetically for the UI
    final_list = sorted(list(all_coins_set))
    return jsonify({'coins': final_list})

@socketio.on('connect', namespace='/')
def handle_connect():
    """Client connected"""
    print(f"Client connected: {request.sid}")
    emit('status', {'status': 'connected', 'config': config})
    emit('output', {'data': f'✓ Connected at {datetime.now().strftime("%H:%M:%S")}\n'})

@socketio.on('disconnect', namespace='/')
def handle_disconnect():
    """Client disconnected"""
    print(f"Client disconnected: {request.sid}")

@socketio.on('start_analysis', namespace='/')
def handle_start(data):
    """Start analysis with config"""
    global analysis_thread, analysis_running
    
    if analysis_running:
        emit('output', {'data': '⚠️  Analysis already running!\n'})
        return
    
    symbols = data.get('symbols', config['symbols'])
    indicators = data.get('indicators', config['indicators'])
    timeframes = data.get('timeframes', config['timeframes'])
    min_conf = data.get('min_confidence', config['min_confidence'])
    exchanges = data.get('exchanges', config['exchanges'])
    
    # Update current config with these values for persistence
    config['symbols'] = symbols
    config['indicators'] = indicators
    config['timeframes'] = timeframes
    config['min_confidence'] = min_conf
    config['exchanges'] = exchanges
    
    emit('output', {'data': f'🚀 Starting analysis at {datetime.now().strftime("%H:%M:%S")}\n'})
    emit('output', {'data': f'📊 Symbols: {len(symbols)} | Indicators: {len(indicators)} | Timeframes: {len(timeframes)}\n'})
    emit('status', {'status': 'started'})
    
    analysis_thread = threading.Thread(
        target=run_analysis_subprocess,
        args=(symbols, indicators, timeframes, min_conf),
        daemon=True
    )
    analysis_thread.start()

@socketio.on('stop_analysis', namespace='/')
def handle_stop():
    """Stop analysis (if running) — kills the entire process tree on Windows"""
    global active_process, analysis_running
    socketio.emit('output', {'data': '⏹️  Stop requested — terminating all processes...\n'}, namespace='/')
    
    if active_process:
        try:
            pid = active_process.pid
            print(f"Terminating analysis process tree: PID {pid}")
            # On Windows, use taskkill to kill the entire process tree
            import platform
            if platform.system() == 'Windows':
                subprocess.run(
                    ['taskkill', '/F', '/T', '/PID', str(pid)],
                    capture_output=True, timeout=10
                )
            else:
                import signal
                os.killpg(os.getpgid(pid), signal.SIGTERM)
            socketio.emit('output', {'data': '⏹️  All analysis processes terminated successfully\n'}, namespace='/')
        except Exception as e:
            socketio.emit('output', {'data': f'❌ Error stopping process: {e}\n'}, namespace='/')
            # Force kill as last resort
            try:
                active_process.kill()
            except:
                pass
        finally:
            active_process = None
            analysis_running = False
            socketio.emit('status', {'status': 'stopped'}, namespace='/')
    else:
        socketio.emit('output', {'data': 'ℹ️  No analysis process currently running\n'}, namespace='/')
        analysis_running = False
        socketio.emit('status', {'status': 'stopped'}, namespace='/')

@socketio.on('refresh_news', namespace='/')
def handle_refresh_news():
    """Manual trigger to refresh news"""
    try:
        # socketio.emit('output', {'data': '📰 Refreshing news...'}, namespace='/')
        news_manager.fetch_news()
        status = news_manager.get_market_status()
        emit('market_status', status, broadcast=True, namespace='/')
    except Exception as e:
        emit('output', {'data': f"Error refreshing news: {e}"}, namespace='/')

@socketio.on('clear_output', namespace='/')
def handle_clear():
    """Clear terminal"""
    socketio.emit('clear', {}, namespace='/')
    emit('output', {'data': '>>> Output cleared\n'})

def update_scheduler():
    """Update APScheduler with new interval"""
    try:
        scheduler.remove_job('auto_analysis')
    except:
        pass
    
    if config['auto_run']:
        scheduler.add_job(
            auto_run_analysis,
            'interval',
            seconds=config['auto_run_interval'],
            id='auto_analysis'
        )
        if not scheduler.running:
            scheduler.start()

@app.route('/api/proxy/klines')
def proxy_klines():
    """Proxy kline requests to avoid CORS"""
    symbol = request.args.get('symbol', 'BTCUSDT').upper().replace('_', '')
    interval = request.args.get('interval', '1h')
    limit = request.args.get('limit', '200')
    exchange = request.args.get('exchange', 'BINANCE').upper()
    
    import requests
    
    # Try Binance first
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            return jsonify(r.json())
    except:
        pass
        
    # Fallback to MEXC
    try:
        # MEXC uses 60m for 1h? Actually standard Binance API format is widely used.
        # But let's check basic mapping if needed. For now assume standard.
        url = f"https://api.mexc.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            return jsonify(r.json())
    except:
        pass
        
    return jsonify({'error': 'Failed to fetch klines'}), 500

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(e):
    print(f"Server error: {e}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Start background output stream reader
    reader = threading.Thread(target=stream_output_loop, daemon=True)
    reader.start()

    # Start Market Monitor (News + Volatility)
    market_thread = threading.Thread(target=market_monitor_loop, daemon=True)
    market_thread.start()
    
    print("🌐 RBot Pro Multi-Exchange Analysis UI Server")
    print("📱 Open: http://localhost:5000")
    print("✓ Using queue-based streaming for stability")
    
    try:
        socketio.run(
            app,
            host='0.0.0.0',
            port=5000,
            debug=False,
            use_reloader=False
        )
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
