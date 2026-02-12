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
import csv
import requests

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

# --- Exchange Specific Kline Fetchers (Ported from fast_analysis.py) ---
def get_klines_mexc(symbol, interval, limit=200):
    try:
        mapping = {'1m': 'Min1', '3m': 'Min3', '5m': 'Min5', '15m': 'Min15', '30m': 'Min30', '1h': 'Min60', '4h': 'Hour4', '1d': 'Day1'}
        mexc_interval = mapping.get(interval, 'Min60')
        futures_symbol = symbol.replace('USDT', '_USDT') if 'USDT' in symbol and '_' not in symbol else symbol
        url = f'https://contract.mexc.com/api/v1/contract/kline/{futures_symbol}?interval={mexc_interval}&limit={limit}'
        r = requests.get(url, timeout=5)
        data = r.json()
        if data.get('success') and 'data' in data:
            d = data['data']
            candles = []
            for i in range(len(d['time'])):
                candles.append([int(d['time'][i]) * 1000, float(d['open'][i]), float(d['high'][i]), float(d['low'][i]), float(d['close'][i]), float(d['vol'][i])])
            return candles
        return None
    except: return None

def get_klines_binance(symbol, interval, limit=200):
    try:
        url = f'https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}'
        r = requests.get(url, timeout=5)
        return r.json()
    except: return None

def get_klines_bybit(symbol, interval, limit=200):
    try:
        mapping = {'1m': '1', '3m': '3', '5m': '5', '15m': '15', '30m': '30', '1h': '60', '4h': '240', '1d': 'D'}
        url = f'https://api.bybit.com/v5/market/kline?category=linear&symbol={symbol}&interval={mapping.get(interval, "60")}&limit={limit}'
        r = requests.get(url, timeout=5)
        data = r.json()
        if data.get('result') and data['result'].get('list'):
            return [[int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])] for k in reversed(data['result']['list'])]
        return None
    except: return None

def get_klines_bitget(symbol, interval, limit=200):
    try:
        mapping = {'1m': '1m', '3m': '3m', '5m': '5m', '15m': '15m', '30m': '30m', '1h': '1H', '4h': '4H', '1d': '1D'}
        url = f'https://api.bitget.com/api/v2/mix/market/candles?productType=USDT-FUTURES&symbol={symbol}&granularity={mapping.get(interval, "1H")}&limit={limit}'
        r = requests.get(url, timeout=5)
        data = r.json()
        if data.get('data'):
            candles = [[int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])] for k in data['data']]
            if candles and candles[0][0] > candles[-1][0]: candles.reverse()
            return candles
        return None
    except: return None

def get_klines_okx(symbol, interval, limit=200):
    try:
        mapping = {'1m': '1m', '3m': '3m', '5m': '5m', '15m': '15m', '30m': '30m', '1h': '1H', '4h': '4H', '1d': '1D'}
        okx_symbol = symbol.replace('USDT', '-USDT-SWAP') if 'USDT' in symbol and '-' not in symbol else symbol
        url = f'https://www.okx.com/api/v5/market/candles?instId={okx_symbol}&bar={mapping.get(interval, "1H")}&limit={limit}'
        r = requests.get(url, timeout=5)
        data = r.json()
        if data.get('data'):
            return [[int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])] for k in reversed(data['data'])]
        return None
    except: return None

def get_klines_kucoin(symbol, interval, limit=200):
    try:
        mapping = {'1m': '1min', '3m': '3min', '5m': '5min', '15m': '15min', '30m': '30min', '1h': '1hour', '4h': '4hour', '1d': '1day'}
        kucoin_symbol = symbol.replace('USDT', '-USDT') if 'USDT' in symbol and '-' not in symbol else symbol
        url = f'https://api.kucoin.com/api/v1/market/candles?type={mapping.get(interval, "1hour")}&symbol={kucoin_symbol}&limit={limit}'
        r = requests.get(url, timeout=5)
        data = r.json()
        if data.get('data'):
            return [[int(k[0]) * 1000, float(k[1]), float(k[3]), float(k[4]), float(k[2]), float(k[5])] for k in reversed(data['data'])]
        return None
    except: return None

def get_klines_gateio(symbol, interval, limit=200):
    try:
        gate_symbol = symbol.replace('USDT', '_USDT') if 'USDT' in symbol and '_' not in symbol else symbol
        url = f'https://api.gateio.ws/api/v4/futures/usdt/candlesticks?contract={gate_symbol}&interval={interval}&limit={limit}'
        r = requests.get(url, timeout=5)
        data = r.json()
        if isinstance(data, list):
            return [[int(k.get('t', 0)) * 1000, float(k.get('o', 0)), float(k.get('h', 0)), float(k.get('l', 0)), float(k.get('c', 0)), float(k.get('v', 0))] for k in data]
        return None
    except: return None

def get_klines_htx(symbol, interval, limit=200):
    try:
        mapping = {'1m': '1min', '3m': '3min', '5m': '5min', '15m': '15min', '30m': '30min', '1h': '60min', '4h': '4hour', '1d': '1day'}
        url = f'https://api.huobi.pro/market/history/kline?symbol={symbol.lower()}&period={mapping.get(interval, "60min")}&size={limit}'
        r = requests.get(url, timeout=5)
        data = r.json()
        if data.get('data'):
            return [[int(k.get('id', 0)) * 1000, float(k.get('open', 0)), float(k.get('high', 0)), float(k.get('low', 0)), float(k.get('close', 0)), float(k.get('vol', 0))] for k in reversed(data['data'])]
        return None
    except: return None

EXCHANGE_FETCHERS = {
    'MEXC': get_klines_mexc, 'BINANCE': get_klines_binance, 'BYBIT': get_klines_bybit,
    'BITGET': get_klines_bitget, 'OKX': get_klines_okx, 'KUCOIN': get_klines_kucoin,
    'GATEIO': get_klines_gateio, 'HTX': get_klines_htx
}

class TradeTracker:
    def __init__(self):
        self.active_trades = []
        self.lock = threading.Lock()
        self.exchange_prices = {}
        self.tracking_active = False

    def add_trade(self, trade):
        """Register a new trade for real-time tracking"""
        with self.lock:
            # Check if already tracking this exact setup
            for t in self.active_trades:
                if t['symbol'] == trade['symbol'] and t['strategy'] == trade['strategy'] and t['type'] == trade['type']:
                    print(f"⚠️  {trade['symbol']} already being tracked. Skipping.")
                    return
            
            # Auto-set status for MARKET entries
            entry_type = str(trade.get('entry_type', 'LIMIT')).upper()
            if entry_type == 'MARKET':
                trade['tracking_status'] = 'RUNNING'
                print(f"📡 Registered {trade['symbol']} (MARKET) - Started RUNNING immediately.", flush=True)
            else:
                trade['tracking_status'] = 'WAITING'
                print(f"📡 Registered {trade['symbol']} ({entry_type}) for tracking.", flush=True)

            trade['current_price'] = trade['entry']
            trade['pnl_pct'] = 0.0
            trade['updated_at'] = datetime.now().strftime('%H:%M:%S')
            self.active_trades.append(trade)
            print(f"📈 Total active trades being tracked: {len(self.active_trades)}", flush=True)

    def get_price(self, exchange, symbol):
        """Fetch live price for a symbol using exchange-specific fetchers with fallback to Binance"""
        try:
            # Try primary exchange
            exch = exchange.upper().replace(' ', '').replace('.', '')
            fetcher = EXCHANGE_FETCHERS.get(exch)
            
            price = None
            if fetcher:
                klines = fetcher(symbol, '1m', limit=1)
                if klines and len(klines) > 0:
                    price = float(klines[-1][4])

            # Fallback to Binance if primary fails or is not supported
            if not price and exch != 'BINANCE':
                klines = get_klines_binance(symbol, '1m', limit=1)
                if klines and len(klines) > 0:
                    price = float(klines[-1][4])
            
            # if price:
            #     print(f"DEBUG: Price for {symbol} on {exchange}: {price}")
            return price
        except Exception as e:
            print(f"Price fetch error for {symbol} on {exchange}: {e}")
            return None

    def update_loop(self):
        """Background loop to update all active signals"""
        self.tracking_active = True
        print("💡 Trade Tracking Loop Started", flush=True)
        last_heartbeat = 0
        while self.tracking_active:
            try:
                current_time = time.time()
                # 1. Snapshot of what needs updating (minimize lock time)
                with self.lock:
                    if not self.active_trades:
                        if current_time - last_heartbeat > 10:
                            print("😴 Tracking loop idle (no active trades)", flush=True)
                            last_heartbeat = current_time
                        time.sleep(2)
                        continue
                    current_trades = list(self.active_trades)

                if current_time - last_heartbeat > 10:
                    print(f"💓 Tracking heartbeat: {len(current_trades)} active trades", flush=True)
                    last_heartbeat = current_time

                # Group targets
                targets_map = {}
                for t in current_trades:
                    if t['tracking_status'] in ['WAITING', 'RUNNING']:
                        key = (t.get('exchange', 'Binance'), t['symbol'])
                        targets_map[key] = None

                # 2. Fetch prices (Slow, NO lock held)
                for key in targets_map:
                    targets_map[key] = self.get_price(key[0], key[1])

                # 3. Apply updates (Brief lock)
                with self.lock:
                    for t in self.active_trades:
                        if t['tracking_status'] in ['TP_HIT', 'SL_HIT']:
                            continue

                        price = targets_map.get((t.get('exchange', 'Binance'), t['symbol']))
                        if not price: continue

                        # Ensure numeric
                        try:
                            entry_price = float(t['entry'])
                            tp_price = float(t['tp1'])
                            sl_price = float(t['sl'])
                        except: continue

                        t['current_price'] = price
                        t['updated_at'] = datetime.now().strftime('%H:%M:%S')

                        # Calculate PnL
                        if t['type'] == 'LONG':
                            t['pnl_pct'] = ((price - entry_price) / entry_price) * 100
                            if t['tracking_status'] == 'WAITING':
                                if price >= entry_price * 0.999: # 0.1% buffer below entry
                                    t['tracking_status'] = 'RUNNING'
                                    print(f"✅ [RUNNING] {t['symbol']} LONG at {price}", flush=True)
                            
                            if price >= tp_price:
                                t['tracking_status'] = 'TP_HIT'
                                t['pnl_pct'] = ((tp_price - entry_price) / entry_price) * 100
                                print(f"💰 [TP HIT] {t['symbol']} LONG at {price}", flush=True)
                            elif price <= sl_price:
                                t['tracking_status'] = 'SL_HIT'
                                t['pnl_pct'] = ((sl_price - entry_price) / entry_price) * 100
                                print(f"🛑 [SL HIT] {t['symbol']} LONG at {price}", flush=True)
                        else:  # SHORT
                            t['pnl_pct'] = ((entry_price - price) / entry_price) * 100
                            if t['tracking_status'] == 'WAITING':
                                if price <= entry_price * 1.001: # 0.1% buffer above entry
                                    t['tracking_status'] = 'RUNNING'
                                    print(f"✅ [RUNNING] {t['symbol']} SHORT at {price}", flush=True)

                            if price <= tp_price:
                                t['tracking_status'] = 'TP_HIT'
                                t['pnl_pct'] = ((entry_price - tp_price) / entry_price) * 100
                                print(f"💰 [TP HIT] {t['symbol']} SHORT at {price}", flush=True)
                            elif price >= sl_price:
                                t['tracking_status'] = 'SL_HIT'
                                t['pnl_pct'] = ((entry_price - sl_price) / entry_price) * 100
                                print(f"🛑 [SL HIT] {t['symbol']} SHORT at {price}", flush=True)

                    # Broadcast
                    socketio.emit('tracking_update', self.active_trades, namespace='/')

                time.sleep(1)
            except Exception as e:
                print(f"Tracking error: {e}")
                time.sleep(3)

    def export_to_csv(self):
        """Save current session trades to CSV before starting next analysis"""
        with self.lock:
            if not self.active_trades:
                return
            
            filename = f"trade_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            keys = self.active_trades[0].keys()
            
            try:
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    dict_writer = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
                    dict_writer.writeheader()
                    dict_writer.writerows(self.active_trades)
                
                print(f"📊 Exported {len(self.active_trades)} trades to {filename}")
                self.active_trades = [] # Reset for next analysis
            except Exception as e:
                print(f"Failed to export CSV: {e}")

# Global instances
trade_tracker = TradeTracker()

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
                        # Register with tracker
                        trade_tracker.add_trade(trade)
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
            text=True,
            encoding='utf-8',
            bufsize=1,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            env=env
        )
        active_process = proc
        
        # Stream output to queue
        for line in iter(proc.stdout.readline, ''):
            if line:
                if line.startswith('SIGNAL_DATA:'):
                    try:
                        signal_str = line.split('SIGNAL_DATA:')[1].strip()
                        signal_data = json.loads(signal_str)
                        
                        # Register with tracker for real-time price updates
                        trade_tracker.add_trade(signal_data)
                        
                        # Emit to UI
                        socketio.emit('trade_signal', signal_data, namespace='/')
                        
                        # Forward to Telegram in background
                        thread = threading.Thread(target=send_telegram_alert, args=(signal_data,), daemon=True)
                        thread.start()
                    except Exception as e:
                        print(f"Error processing trade signal: {e}")
                    continue # Skip showing raw JSON data in terminal
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
    
    # Export previous session data to CSV before starting new analysis
    trade_tracker.export_to_csv()
    
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
    """Proxy kline requests to the specific exchange requested"""
    symbol = request.args.get('symbol', 'BTCUSDT').upper().replace('_', '')
    interval = request.args.get('interval', '1h')
    limit = request.args.get('limit', '200')
    exchange = request.args.get('exchange', 'BINANCE').upper().replace(' ', '').replace('.', '')
    
    fetcher = EXCHANGE_FETCHERS.get(exchange)
    if not fetcher:
        # Fallback to Binance if exchange not supported or not found
        fetcher = get_klines_binance
        
    klines = fetcher(symbol, interval, limit=int(limit))
    if klines:
        return jsonify(klines)
        
    return jsonify({'error': f'Failed to fetch klines from {exchange}'}), 500

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
    
    # Start Trade Tracking loop
    tracker_thread = threading.Thread(target=trade_tracker.update_loop, daemon=True)
    tracker_thread.start()
    
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
