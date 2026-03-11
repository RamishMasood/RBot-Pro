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
        self.risk_settings = self.config.get('risk_settings', {'type': 'percent', 'value': 1.0})
        self.trade_filter = self.config.get('trade_filter', ['STRONG', 'ELITE'])
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

    def update_exchange_config(self, exchange_name, api_key, secret_key, password=None):
        if 'exchanges' not in self.config:
            self.config['exchanges'] = {}
        
        config_entry = {
            'apiKey': api_key,
            'secret': secret_key,
            'enableRateLimit': True,
            'options': {'defaultType': 'swap'}
        }
        if password:
            config_entry['password'] = password
            
        self.config['exchanges'][exchange_name.upper()] = config_entry
        self.save_config()
        self.init_exchanges()
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
                ccxt_id = name.lower().replace('.', '').replace(' ', '')
                if ccxt_id == 'gateio': ccxt_id = 'gate'
                
                if hasattr(ccxt, ccxt_id):
                    exchange_class = getattr(ccxt, ccxt_id)
                    
                    if 'options' not in conf:
                        conf['options'] = {}
                    if 'defaultType' not in conf['options']:
                        conf['options']['defaultType'] = 'swap'
                    conf['options']['createMarketBuyOrderRequiresPrice'] = False
                    
                    exchange = exchange_class(conf)
                    
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
        """
        if not manual_override:
            if not self.auto_trade_enabled:
                return {"status": "skipped", "msg": "Auto-Trade Disabled"}
            quality = trade_signal.get('signal_quality', 'STANDARD')
            if quality not in self.trade_filter:
                return {"status": "skipped", "msg": f"Quality {quality} not in filter"}

        symbol = trade_signal['symbol'].replace('_', '')
        exchange_name = trade_signal.get('exchange', 'BINANCE').upper()
        
        exchange = self.exchanges.get(exchange_name)
        if not exchange:
            return {"status": "error", "msg": f"Exchange {exchange_name} not configured"}

        # Normalize Symbol
        market_symbol = symbol
        try:
            exchange.load_markets()
            found = False
            for m in exchange.markets:
                market = exchange.markets[m]
                if market.get('swap') or market.get('future'):
                    if m.replace('/', '').split(':')[0] == symbol or market.get('id') == symbol:
                        market_symbol = m
                        found = True
                        break
            
            if not found:
                for m in exchange.markets:
                    if m.replace('/', '') == symbol or exchange.markets[m]['id'] == symbol:
                        market_symbol = m
                        found = True
                        break
            
            if not found:
                 if exchange_name == 'BINANCE': market_symbol = symbol 
                 elif exchange_name == 'BYBIT': market_symbol = symbol 
                 elif exchange_name == 'MEXC': market_symbol = symbol
        except:
             pass

        side = trade_signal['type'].lower()
        if side == 'long': side = 'buy'
        elif side == 'short': side = 'sell'
        
        price = float(trade_signal['entry'])
        stop_loss = float(trade_signal['sl'])
        take_profit = float(trade_signal['tp1'])
        
        # Balance & Risk
        balance = self.get_balance(exchange_name) or 0
        if balance <= 0:
             return {"status": "error", "msg": "Insufficient Balance"}

        risk_val = self.risk_settings['value']
        if self.risk_settings['type'] == 'percent':
            risk_amt = balance * (risk_val / 100)
        else:
            risk_amt = risk_val

        price_diff = abs(price - stop_loss)
        if price_diff == 0: return {"status": "error", "msg": "Invalid SL"}
        
        position_size_in_assets = risk_amt / price_diff
        
        print(f"💰 Balance: {balance:.4f} USDT | Risk: {risk_amt:.4f} USDT | Calculated Size: {position_size_in_assets:.4f}")

        # Minimum Order Size Bump (6.5 USDT for safety)
        min_notional = 6.5
        entry_type = trade_signal.get('entry_type', 'MARKET').upper()
        current_price = price if entry_type == 'LIMIT' else float(trade_signal.get('price', 0)) or price
        
        current_notional = position_size_in_assets * current_price
        if current_notional < min_notional:
            print(f"⚠️ Order size bumped to {min_notional} USDT (Current: {current_notional:.2f})")
            position_size_in_assets = min_notional / current_price

        # Precision adjustments
        try:
            if exchange.markets and market_symbol in exchange.markets:
                sl_str = exchange.price_to_precision(market_symbol, stop_loss)
                tp_str = exchange.price_to_precision(market_symbol, take_profit)
                position_size_in_assets = float(exchange.amount_to_precision(market_symbol, position_size_in_assets))
            else:
                sl_str = f"{stop_loss:.8f}".rstrip('0').rstrip('.')
                tp_str = f"{take_profit:.8f}".rstrip('0').rstrip('.')
        except Exception:
            sl_str = f"{stop_loss:.8f}".rstrip('0').rstrip('.')
            tp_str = f"{take_profit:.8f}".rstrip('0').rstrip('.')

        try:
            params = {}
            if exchange_name == 'BINANCE':
                params = {'positionSide': 'LONG' if side == 'buy' else 'SHORT'}
            elif exchange_name == 'BITGET':
                # BITGET V2: Attached SL via preset (reliable, auto-cancels with position)
                params.update({
                    'presetStopLossPrice': sl_str,
                    'presetStopLossType': 'market',
                })
            elif exchange_name == 'BYBIT':
                params['stopLoss'] = sl_str
                params['takeProfit'] = tp_str
            elif exchange_name == 'OKX':
                params['slTriggerPx'] = sl_str
                params['tpTriggerPx'] = tp_str
            elif exchange_name == 'MEXC':
                params['stopLossPrice'] = sl_str
                params['takeProfitPrice'] = tp_str

            print(f"🚀 [EXEC] {exchange_name} | {side.upper()} {market_symbol} | Size: {position_size_in_assets}")
            
            if entry_type == 'LIMIT':
                order = exchange.create_limit_order(market_symbol, side, position_size_in_assets, price, params=params)
            else:
                order = exchange.create_market_order(market_symbol, side, position_size_in_assets, params=params)

            # Post-execution: Place TP as a conditional trigger order for Bitget
            if exchange_name == 'BITGET':
                threading.Thread(
                    target=self._set_bitget_tp,
                    args=(exchange, market_symbol, side, tp_str, position_size_in_assets),
                    daemon=True
                ).start()
            
            return {"status": "success", "msg": f"Order Placed ({entry_type})! ID: {order['id']}", "order": order}

        except Exception as e:
            return {"status": "error", "msg": str(e)}

    def _set_bitget_tp(self, exchange, market_symbol, side, tp_price, size):
        """
        Place TP as a conditional trigger order on Bitget.
        SL is already attached via presetStopLossPrice (auto-cancels with position).
        TP uses a trigger order with reduceOnly to close the position at profit target.
        """
        time.sleep(2.0)
        try:
            tp_side = 'sell' if side == 'buy' else 'buy'
            tp_params = {
                'triggerPrice': tp_price,
                'triggerType': 'mark_price',
                'reduceOnly': True,
            }
            exchange.create_order(market_symbol, 'market', tp_side, size, None, tp_params)
            print(f"✅ [TP] BITGET TP Trigger Placed at {tp_price} (reduceOnly)")
        except Exception as e:
            print(f"⚠️ [TP] BITGET TP Trigger Failed: {e}")
