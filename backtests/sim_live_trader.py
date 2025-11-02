"""
Simulated Live Trading for EUR/USD using Historical Data

This script simulates live trading by feeding historical EUR/USD data tick-by-tick.
It computes signals and simulates trades in real-time speed.
"""

import pandas as pd
import time
from breakout_strategy import BreakoutStrategy

# Config
DATA_PATH = 'data/eurusd_candles.csv'
BREAKOUT_LENGTH = 50
ATR_STOP_MULTIPLIER = 0.5
ATR_TP_MULTIPLIER = 2.0
VOLATILITY_FILTER = True
RISK_PER_TRADE = 0.02
COMMISSION_RATE = 0.0001
SLIPPAGE_ATR_FRAC = 0.02

# Load data
df = pd.read_csv(DATA_PATH, parse_dates=['time'])
df = df.sort_values('time').reset_index(drop=True)

# Strategy
strategy = BreakoutStrategy(
    breakout_length=BREAKOUT_LENGTH,
    atr_stop_multiplier=ATR_STOP_MULTIPLIER,
    atr_tp_multiplier=ATR_TP_MULTIPLIER,
    volatility_filter=VOLATILITY_FILTER
)

# State
balance = 10000.0
open_trade = None
trades_log = []
equity_log = []

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

            print(f"Simulated LONG entry at {entry_price:.4f}")
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

            print(f"Simulated SHORT entry at {entry_price:.4f}")
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

                print(f"Simulated LONG exit at {exit_price:.4f}, profit: {net_profit:.2f}, balance: {balance:.2f}")
                open_trade = None

        elif open_trade['direction'] == 'SHORT':
            if current_price >= open_trade['stop_loss'] or current_price <= open_trade['take_profit']:
                exit_price = open_trade['stop_loss'] if current_price >= open_trade['stop_loss'] else open_trade['take_profit']
                gross_profit = (open_trade['entry_price'] - exit_price) * open_trade['position_size']
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

                print(f"Simulated SHORT exit at {exit_price:.4f}, profit: {net_profit:.2f}, balance: {balance:.2f}")
                open_trade = None

print("Starting simulated live trading for EUR/USD...")
for i, row in df.iterrows():
    # Update strategy with new data
    strategy.data = df.iloc[:i+1]
    strategy.compute_signals()

    # Check signals on latest
    latest = strategy.data.iloc[-1]
    check_signals(latest)

    # Simulate real-time delay (1 hour per candle)
    time.sleep(0.1)  # Fast simulation; change to 3600 for real-time

    if i % 100 == 0:
        print(f"Processed {i} candles, balance: {balance:.2f}")

# Save logs
pd.DataFrame(trades_log).to_csv('results/sim_live_trades.csv', index=False)
pd.DataFrame(equity_log).to_csv('results/sim_live_equity.csv', index=False)
print("Simulation complete. Logs saved.")