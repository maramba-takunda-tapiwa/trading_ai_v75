"""
Live Trading Automation for Optimized Breakout Strategy on Deriv Synthetic Indices

This script connects to Deriv's WebSocket API for real-time data on synthetic indices (e.g., Volatility 10 Index).
- Subscribes to tick data.
- Computes signals using BreakoutStrategy.
- Simulates trades (set SIMULATION=True for safety).

Requirements: Install websockets (pip install websockets).
Get Deriv API token from https://app.deriv.com/account/api-token.
"""

import asyncio
import json
import pandas as pd
import websockets
from datetime import datetime
from breakout_strategy import BreakoutStrategy

# Configuration
# Never hardcode tokens; read from environment or a local config file excluded by .gitignore
import os
API_TOKEN = os.getenv('DERIV_API_TOKEN', '')  # Set in environment
APP_ID = 1089  # Deriv app ID
SYMBOL = 'frxEURUSD'  # EUR/USD forex pair
SIMULATION = True  # Simulate trades; set to False for real (use demo account first!)

# Strategy params (optimized)
BREAKOUT_LENGTH = 50
ATR_STOP_MULTIPLIER = 0.5
ATR_TP_MULTIPLIER = 2.0
VOLATILITY_FILTER = True
RISK_PER_TRADE = 0.02
COMMISSION_RATE = 0.0001
SLIPPAGE_ATR_FRAC = 0.02

# Global state
strategy = BreakoutStrategy(
    breakout_length=BREAKOUT_LENGTH,
    atr_stop_multiplier=ATR_STOP_MULTIPLIER,
    atr_tp_multiplier=ATR_TP_MULTIPLIER,
    volatility_filter=VOLATILITY_FILTER
)
data_buffer = []  # Store recent ticks
balance = 10000.0
open_trade = None
trades_log = []
equity_log = []

async def deriv_ws_handler():
    uri = f"wss://ws.derivws.com/websockets/v3?app_id={APP_ID}"
    async with websockets.connect(uri) as websocket:
        # Authorize
        await websocket.send(json.dumps({
            "authorize": API_TOKEN
        }))
        response = await websocket.recv()
        print("Authorized:", json.loads(response))

        # Subscribe to ticks
        await websocket.send(json.dumps({
            "ticks": SYMBOL,
            "subscribe": 1
        }))

        while True:
            try:
                message = await websocket.recv()
                data = json.loads(message)

                if 'tick' in data:
                    tick = data['tick']
                    timestamp = datetime.fromtimestamp(tick['epoch'])
                    price = tick['quote']

                    # Add to buffer (simulate OHLC if needed, but for simplicity use tick price)
                    data_buffer.append({
                        'time': timestamp,
                        'open': price,
                        'high': price,
                        'low': price,
                        'close': price,
                        'volume': 1
                    })

                    # Keep last 200 ticks for signals
                    if len(data_buffer) > 200:
                        data_buffer.pop(0)

                    # Update strategy
                    df = pd.DataFrame(data_buffer)
                    strategy.data = df
                    strategy.compute_signals()

                    # Check signals
                    check_signals(df.iloc[-1])

                await asyncio.sleep(1)  # Throttle

            except Exception as e:
                print(f"Error: {e}")
                await asyncio.sleep(5)

def check_signals(latest):
    global open_trade, balance
    long_signal = latest.get('long_signal', False)
    short_signal = latest.get('short_signal', False)

    if open_trade is None:
        if long_signal:
            entry_price = latest['close']
            atr = latest.get('atr', 1.0)
            stop_loss = entry_price - ATR_STOP_MULTIPLIER * atr
            take_profit = entry_price + ATR_TP_MULTIPLIER * atr
            risk_amount = balance * RISK_PER_TRADE
            stop_distance = abs(entry_price - stop_loss)
            position_size = risk_amount / stop_distance if stop_distance > 0 else 0

            if SIMULATION:
                print(f"Simulated LONG entry at {entry_price}")
            else:
                # Send buy order via WS
                pass

            open_trade = {
                'direction': 'LONG',
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'position_size': position_size,
                'atr': atr
            }

        elif short_signal:
            entry_price = latest['close']
            atr = latest.get('atr', 1.0)
            stop_loss = entry_price + ATR_STOP_MULTIPLIER * atr
            take_profit = entry_price - ATR_TP_MULTIPLIER * atr
            risk_amount = balance * RISK_PER_TRADE
            stop_distance = abs(entry_price - stop_loss)
            position_size = risk_amount / stop_distance if stop_distance > 0 else 0

            if SIMULATION:
                print(f"Simulated SHORT entry at {entry_price}")
            else:
                pass

            open_trade = {
                'direction': 'SHORT',
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'position_size': position_size,
                'atr': atr
            }

    else:
        current_price = latest['close']
        if open_trade['direction'] == 'LONG':
            if current_price <= open_trade['stop_loss'] or current_price >= open_trade['take_profit']:
                exit_price = open_trade['stop_loss'] if current_price <= open_trade['stop_loss'] else open_trade['take_profit']
                gross_profit = (exit_price - open_trade['entry_price']) * open_trade['position_size']
                commission = COMMISSION_RATE * abs(gross_profit)
                net_profit = gross_profit - commission
                balance += net_profit

                trades_log.append({
                    'time': latest['time'],
                    'direction': open_trade['direction'],
                    'entry_price': open_trade['entry_price'],
                    'exit_price': exit_price,
                    'profit': net_profit
                })
                equity_log.append({'time': latest['time'], 'equity': balance})

                if SIMULATION:
                    print(f"Simulated LONG exit at {exit_price}, profit: {net_profit}")
                else:
                    pass

                open_trade = None

        # Similar for SHORT

async def main():
    print("Starting Deriv synthetic indices live trader...")
    await deriv_ws_handler()

if __name__ == '__main__':
    asyncio.run(main())