
import ccxt
import json
import os
import time
import threading

class RealTrader:
    def __init__(self, config_file='exchange_config.json'):
        self.config_file = config_file
        self.exchanges = {}
        self.config = self.load_config()
        self.active = False
        self.risk_settings = self.config.get('risk_settings', {'type': 'percent', 'value': 1.0}) # 1% default
        self.trade_filter = self.config.get('trade_filter', ['STRONG', 'ELITE']) # Default safe
        self.auto_trade_enabled = self.config.get('auto_trade_enabled', False)
        
        # Initialize exchanges
        self.init_exchanges()

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_config(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=4)

    def update_exchange_config(self, exchange_name, api_key, secret_key):
        if 'exchanges' not in self.config:
            self.config['exchanges'] = {}
        
        self.config['exchanges'][exchange_name.upper()] = {
            'apiKey': api_key,
            'secret': secret_key,
            'enableRateLimit': True,
            'options': {'defaultType': 'future'} # Default to futures for all
        }
        self.save_config()
        self.init_exchanges() # Re-init to apply changes
        return True

    def update_settings(self, auto_enabled, risk_type, risk_value, filters):
        self.auto_trade_enabled = auto_enabled
        self.risk_settings = {'type': risk_type, 'value': float(risk_value)}
        self.trade_filter = filters
        
        self.config['auto_trade_enabled'] = auto_enabled
        self.config['risk_settings'] = self.risk_settings
        self.config['trade_filter'] = filters
        self.save_config()

    def init_exchanges(self):
        self.exchanges = {}
        if 'exchanges' not in self.config: return

        for name, conf in self.config['exchanges'].items():
            try:
                # Map common names to ccxt IDs
                ccxt_id = name.lower().replace('.', '').replace(' ', '')
                if ccxt_id == 'gateio': ccxt_id = 'gate'
                
                if hasattr(ccxt, ccxt_id):
                    exchange_class = getattr(ccxt, ccxt_id)
                    exchange = exchange_class(conf)
                    
                    # Verify Futures Support
                    if not exchange.has['createOrder']:
                        print(f"❌ {name} does not support order creation via CCXT")
                        continue
                        
                    self.exchanges[name] = exchange
                    print(f"✅ RealTrader: Connected to {name}")
                else:
                    print(f"❌ RealTrader: Exchange {name} not found in CCXT")
            except Exception as e:
                print(f"❌ RealTrader: Failed to init {name}: {e}")

    def get_balance(self, exchange_name):
        exchange = self.exchanges.get(exchange_name.upper())
        if not exchange: return None
        try:
            balance = exchange.fetch_balance()
            # Try to find USDT free balance
            msg = ""
            if 'USDT' in balance:
                return balance['USDT']['free']
            if 'total' in balance:
                 return balance['total'].get('USDT', 0)
            return 0
        except Exception as e:
            print(f"Balance error {exchange_name}: {e}")
            return None

    def execute_trade(self, trade_signal, manual_override=False):
        """
        Execute a trade based on signal.
        manual_override: If True, bypasses auto-trade toggle and filters.
        """
        if not manual_override:
            if not self.auto_trade_enabled:
                return {"status": "skipped", "msg": "Auto-Trade Disabled"}
            
            # Check Quality Filter
            quality = trade_signal.get('signal_quality', 'STANDARD')
            if quality not in self.trade_filter:
                return {"status": "skipped", "msg": f"Quality {quality} not in filter"}

        symbol = trade_signal['symbol'].replace('_', '') # CCXT usually prefers BTC/USDT or BTCUSDT
        exchange_name = trade_signal.get('exchange', 'BINANCE').upper()
        
        exchange = self.exchanges.get(exchange_name)
        if not exchange:
            return {"status": "error", "msg": f"Exchange {exchange_name} not configured"}

        # Normalize Symbol for CCXT (e.g. BTCUSDT -> BTC/USDT:USDT for futures)
        # This part is tricky and exchange specific. 
        # For now, we try standard CCXT discovery or common formats.
        market_symbol = symbol
        try:
            exchange.load_markets()
            # Try to find the market
            found = False
            for m in exchange.markets:
                if m.replace('/', '') == symbol or exchange.markets[m]['id'] == symbol:
                    market_symbol = m
                    found = True
                    break
            
            if not found:
                 # Fallback for common futures formats
                 if exchange_name == 'BINANCE': market_symbol = symbol # Binance supports BTCUSDT
                 elif exchange_name == 'BYBIT': market_symbol = symbol 
                 elif exchange_name == 'MEXC': market_symbol = symbol
        except:
             pass

        side = trade_signal['type'].lower() # 'long' or 'short' -> 'buy' or 'sell'
        if side == 'long': side = 'buy'
        elif side == 'short': side = 'sell'
        
        price = float(trade_signal['entry'])
        stop_loss = float(trade_signal['sl'])
        take_profit = float(trade_signal['tp1'])
        
        # Calculate Quantity
        risk_val = self.risk_settings['value']
        balance = self.get_balance(exchange_name) or 0
        
        if balance <= 0:
             return {"status": "error", "msg": "Insufficient Balance"}

        amount = 0
        if self.risk_settings['type'] == 'percent':
            risk_amt = balance * (risk_val / 100)
        else:
            risk_amt = risk_val

        # Position Size = Risk Amount / |Entry - SL| * Entry
        # Basic formula: Risk = Size * (Entry - SL)
        # Size = Risk / (Entry - SL)
        price_diff = abs(price - stop_loss)
        if price_diff == 0: return {"status": "error", "msg": "Invalid SL (Equal to Entry)"}
        
        position_size_in_assets = risk_amt / price_diff
        
        # Verify min limits (basic check)
        cost = position_size_in_assets * price
        if cost > balance * 50: # Sanity check for leverage (max 50x assumed implicitly if user risks too much)
             return {"status": "error", "msg": "Calculated position too large for balance"}

        try:
            # Place Order
            # Note: For simple integration, we verify if valid connection, 
            # then place MARKET order for entry with Conditional Orders for SL/TP?
            # Or simplified: Just enter. Managing SL/TP via API is complex across 8 exchanges.
            # Best approach for MVP Auto-Trader:
            # 1. Place Market Entry
            # 2. Place Stop Market (SL)
            # 3. Place Take Profit (Limit/Market)
            
            params = {}
            if exchange_name == 'BINANCE':
                params = {'positionSide': 'LONG' if side == 'buy' else 'SHORT'}

            # 1. Entry
            order = exchange.create_market_order(market_symbol, side, position_size_in_assets, params=params)
            
            # 2. Stop Loss (Essential)
            sl_side = 'sell' if side == 'buy' else 'buy'
            sl_params = params.copy()
            sl_params['stopPrice'] = stop_loss
            
            # Exchange specific SL params
            if exchange_name == 'BINANCE':
                sl_params['type'] = 'STOP_MARKET'
                sl_params['workingType'] = 'MARK_PRICE'
                exchange.create_order(market_symbol, 'STOP_MARKET', sl_side, position_size_in_assets, None, sl_params)
            else:
                 # Generic OCO or separate stop trigger if supported
                 # For MVP, we log that SL needs to be handled if not Binance
                 pass

            return {"status": "success", "msg": f"Order Placed! ID: {order['id']}", "order": order}

        except Exception as e:
            return {"status": "error", "msg": str(e)}

