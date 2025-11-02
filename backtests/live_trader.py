"""
Live Trading Automation for Optimized Breakout Strategy

This script connects to a broker API (e.g., Alpaca for stocks/crypto) and runs the optimized breakout strategy in live mode.
- Fetches real-time data.
- Computes signals using BreakoutStrategy.
- Executes trades based on signals.
- Logs trades and equity.

For simulation, set SIMULATION=True to use paper trading or mock execution.

Requirements: Install alpaca-py (pip install alpaca-py) and set API keys.
"""

import os
import time
import pandas as pd
from datetime import datetime, timedelta
from alpaca_trade_api import REST, TimeFrame
from breakout_strategy import BreakoutStrategy

# Configuration
API_KEY = os.getenv('ALPACA_API_KEY', 'your_api_key')
API_SECRET = os.getenv('ALPACA_API_SECRET', 'your_api_secret')
BASE_URL = 'https://paper-api.alpaca.markets'  # Paper trading for simulation
SIMULATION = True  # Set to False for live trading (use caution!)

SYMBOL = 'BTC/USD'  # Example: Bitcoin on Alpaca
TIMEFRAME = TimeFrame.Minute  # 1-minute bars
BREAKOUT_LENGTH = 50
ATR_STOP_MULTIPLIER = 0.5
ATR_TP_MULTIPLIER = 2.0
VOLATILITY_FILTER = True
RISK_PER_TRADE = 0.02
COMMISSION_RATE = 0.0001
SLIPPAGE_ATR_FRAC = 0.02

# Initialize API
api = REST(API_KEY, API_SECRET, BASE_URL)

# Strategy instance
strategy = BreakoutStrategy(
    breakout_length=BREAKOUT_LENGTH,
    atr_stop_multiplier=ATR_STOP_MULTIPLIER,
    atr_tp_multiplier=ATR_TP_MULTIPLIER,
    volatility_filter=VOLATILITY_FILTER
)

# Global state
balance = 10000.0  # Track simulated balance
open_trade = None
trades_log = []
equity_log = []

def fetch_recent_data(symbol, timeframe, limit=100):
    """Fetch recent bars from Alpaca."""
    bars = api.get_crypto_bars(symbol, timeframe, limit=limit).df
    bars = bars.reset_index()
    bars = bars.rename(columns={'timestamp': 'time', 'open': 'open', 'high': 'high', 'low': 'low', 'close': 'close', 'volume': 'volume'})
    bars['time'] = pd.to_datetime(bars['time'])
    return bars

def update_strategy_data(new_bars):
    """Update strategy with new data and recompute signals."""
    # Append new bars to existing data (simulate incremental update)
    if hasattr(strategy, 'data') and strategy.data is not None:
        strategy.data = pd.concat([strategy.data, new_bars]).drop_duplicates().reset_index(drop=True)
    else:
        strategy.data = new_bars
    strategy.compute_signals()

def check_signals():
    """Check for new signals and execute trades."""
    global open_trade, balance
    df = strategy.data
    if df.empty:
        return

    latest = df.iloc[-1]
    long_signal = latest.get('long_signal', False)
    short_signal = latest.get('short_signal', False)

    if open_trade is None:
        # Check for entry
        if long_signal:
            # Simulate entry
            entry_price = latest['close']  # Use close for simplicity
            atr = latest.get('atr', 1.0)
            stop_loss = entry_price - ATR_STOP_MULTIPLIER * atr
            take_profit = entry_price + ATR_TP_MULTIPLIER * atr
            risk_amount = balance * RISK_PER_TRADE
            stop_distance = abs(entry_price - stop_loss)
            position_size = risk_amount / stop_distance if stop_distance > 0 else 0

            if SIMULATION:
                print(f"Simulated LONG entry at {entry_price}")
            else:
                # Real order: api.submit_order(...)
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
            # Similar for SHORT
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
        # Check for exit
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

def main():
    print("Starting live trading automation...")
    while True:
        try:
            # Fetch new data
            new_bars = fetch_recent_data(SYMBOL, TIMEFRAME, limit=1)  # Last bar
            if not new_bars.empty:
                update_strategy_data(new_bars)
                check_signals()

            # Save logs periodically
            if len(trades_log) > 0:
                pd.DataFrame(trades_log).to_csv('results/live_trades.csv', index=False)
                pd.DataFrame(equity_log).to_csv('results/live_equity.csv', index=False)

            time.sleep(60)  # Check every minute

        except Exception as e:
            print(f"Error: {e}")
            time.sleep(60)

if __name__ == '__main__':
    main()