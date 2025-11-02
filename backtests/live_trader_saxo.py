"""
Live Trading Automation for Optimized Breakout Strategy on Saxo Bank Demo

This script connects to Saxo's OpenAPI for real-time EUR/USD data and automated trading.
- Polls for price updates.
- Computes signals using BreakoutStrategy.
- Places demo orders (set LIVE=False for safety).

Requirements: pip install saxo-openapi. Get ClientID, ClientSecret, and Token from Saxo demo dashboard.
"""

import time
import requests
import csv
import os
from saxo_openapi import API
from datetime import datetime, timezone
import json
import traceback
try:
    from saxo_stream import configure as stream_configure, get_price_fxspot
except Exception:
    stream_configure = None
    get_price_fxspot = None
from breakout_strategy import BreakoutStrategy
import pandas as pd  # Added import for pandas

# Saxo API Credentials (from demo account)
CLIENT_ID = 'd9377c5e6a0b4b9aa6e5c81995e95032'  # App Key
CLIENT_SECRET = 'de1db69d02aa45aa8145b0734eb2077a'  # App Secret
TOKEN = 'eyJhbGciOiJFUzI1NiIsIng1dCI6IjY3NEM0MjFEMzZEMUE1OUNFNjFBRTIzMjMyOTVFRTAyRTc3MDMzNTkifQ.eyJvYWEiOiIzMzMzMCIsImlzcyI6Im9hIiwiYWlkIjoiNzM1NyIsInVpZCI6IjYxbHRiYmpHcnF4ckpuWlRuWUhEdlE9PSIsImNpZCI6IjYxbHRiYmpHcnF4ckpuWlRuWUhEdlE9PSIsImlzYSI6IkZhbHNlIiwidGlkIjoiMTIzODMiLCJzaWQiOiJiMDZlMGMxYmNiZDQ0ZjRkODMxZjc1NGYzMDRjZGExZSIsImRnaSI6Ijg0IiwiZXhwIjoiMTc2MjAwMDczMCIsIm9hbCI6IjFGIiwiaWlkIjoiMmM5OTAzZGQ1MjZiNDJjNTY5NjAwOGRlMTkwNjM1NWYifQ.4nYWhvClPvimJL4Idl51GTC4sbfJ_ZJT1WMKRsaT-jQ4LhRi6zSJtllis_0o1qHufCazU8MvAXzoZ7HW4_YTVg'  # New sim token
ACCOUNT_KEY = 'your_account_key_here'  # Still needed - check Saxo demo trading platform

# Saxo API base URL for simulation
BASE_URL = 'https://gateway.saxobank.com/sim/openapi'
HEADERS = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}

# Strategy params (re-optimized based on Monte Carlo + walk-forward)
BREAKOUT_LENGTH = 35  # improved from 30; more selective entries
ATR_STOP_MULTIPLIER = 0.3  # tighter stops (from 0.5); reduces whipsaws
ATR_TP_MULTIPLIER = 4.0
VOLATILITY_FILTER = True
RISK_PER_TRADE = 0.005
COMMISSION_RATE = 0.0001
SLIPPAGE_ATR_FRAC = 0.0  # No slippage in demo
DAILY_MAX_LOSS = 0.02  # Stop trading for the day if loss exceeds 2% of starting balance
MAX_CONCURRENT_TRADES = 2  # maximum number of simultaneous positions
SLACK_WEBHOOK = None  # set to a Slack incoming webhook URL to enable alerts
# Risk limits (from 1000-sim Monte Carlo):
MAX_DRAWDOWN_ABSOLUTE = 5414  # hard stop in absolute currency (75th percentile from MC)
DAILY_LOSS_ABSOLUTE = 1158  # daily loss freeze in absolute currency (half of 25th percentile)
STATE_FILE = '../results/trader_state.json'  # persistent state between runs

# Global state
# api removed, using requests directly
strategy = BreakoutStrategy(
    breakout_length=BREAKOUT_LENGTH,
    atr_stop_multiplier=ATR_STOP_MULTIPLIER,
    atr_tp_multiplier=ATR_TP_MULTIPLIER,
    volatility_filter=VOLATILITY_FILTER
)
data_buffer = []  # Store recent candles
balance = 10000.0  # Demo balance
max_balance = balance  # Track max for DD
day_start_balance = balance
trading_frozen_today = False
open_trades = []
trades_log = []
equity_log = []
current_day = datetime.now(timezone.utc).date()


def load_state():
    global balance, max_balance, day_start_balance, trading_frozen_today, open_trades, trades_log, equity_log
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                s = json.load(f)
            balance = s.get('balance', balance)
            max_balance = s.get('max_balance', max_balance)
            day_start_balance = s.get('day_start_balance', day_start_balance)
            trading_frozen_today = s.get('trading_frozen_today', trading_frozen_today)
            open_trades[:] = s.get('open_trades', open_trades)
            trades_log[:] = s.get('trades_log', trades_log)
            equity_log[:] = s.get('equity_log', equity_log)
            print('Loaded trader state from', STATE_FILE)
    except Exception:
        print('Failed to load trader state:', traceback.format_exc())


def save_state():
    try:
        s = {
            'balance': balance,
            'max_balance': max_balance,
            'day_start_balance': day_start_balance,
            'trading_frozen_today': trading_frozen_today,
            'open_trades': open_trades,
            'trades_log': trades_log,
            'equity_log': equity_log
        }
        with open(STATE_FILE, 'w') as f:
            json.dump(s, f, default=str)
    except Exception:
        print('Failed to save trader state:', traceback.format_exc())

def get_eurusd_price():
    """Poll current EUR/USD price from Saxo."""
    for attempt in range(3):
        try:
            response = requests.get(f'{BASE_URL}/trade/v1/infoprices?AssetType=FxSpot&Uic=21', headers=HEADERS, timeout=10)
            if response.status_code == 200:
                data = response.json()
                price = data['Quote']['Mid']
                timestamp = datetime.now()
                return {'time': timestamp, 'open': price, 'high': price, 'low': price, 'close': price, 'volume': 1}
            else:
                print(f"Price fetch failed: {response.status_code}, attempt {attempt+1}")
        except Exception as e:
            print(f"Error fetching price: {e}, attempt {attempt+1}")
        time.sleep(2)
    return None

def place_order(direction, amount, stop_loss, take_profit):
    """Place a demo order on Saxo."""
    order = {
        'AccountKey': ACCOUNT_KEY,
        'AssetType': 'FxSpot',
        'Uic': 21,  # EURUSD
        'Amount': amount,
        'BuySell': 'Buy' if direction == 'LONG' else 'Sell',
        'OrderType': 'Market',
        'StopLossPrice': stop_loss,
        'TakeProfitPrice': take_profit,
        'OrderDuration': {'DurationType': 'GoodTillCancel'}
    }
    try:
        response = requests.post(f'{BASE_URL}/trade/v2/orders', headers=HEADERS, json=order)
        print(f"Order response status: {response.status_code}")
        if response.status_code == 201:
            data = response.json()
            print(f"Order placed: {data}")
            # return a lightweight order id / data so caller can track
            return data.get('OrderId', None) or data
        else:
            print(f"Order failed: {response.text}")
            return None
    except Exception as e:
        print(f"Order error: {e}")
        return None


def send_slack_alert(text):
    """Send a simple Slack alert if webhook is configured."""
    if not SLACK_WEBHOOK:
        return
    try:
        payload = {'text': text}
        requests.post(SLACK_WEBHOOK, json=payload, timeout=5)
    except Exception as e:
        print('Failed to send slack alert:', e)

def get_account_key():
    """Fetch the demo account key."""
    try:
        response = requests.get(f'{BASE_URL}/port/v1/accounts/me', headers=HEADERS)
        if response.status_code == 200:
            data = response.json()
            if 'Data' in data and data['Data']:
                account_key = data['Data'][0]['AccountKey']
                return account_key
            else:
                print("No accounts data found.")
                return None
        else:
            print(f"Account fetch failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error fetching account: {e}")
        return None

def check_signals():
    global balance, max_balance, trading_frozen_today
    if len(data_buffer) < 60:  # Need enough data for signals
        return

    if trading_frozen_today:
        return

    df = pd.DataFrame(data_buffer[-200:])  # Last 200 ticks
    strategy.data = df
    strategy.compute_signals()

    latest = df.iloc[-1]
    long_signal = latest.get('long_signal', False)
    short_signal = latest.get('short_signal', False)

    current_dd = max_balance - balance
    if current_dd >= MAX_DRAWDOWN_ABSOLUTE:
        # global drawdown breached - freeze trading and alert
        print(f"Global max drawdown reached: {current_dd:.2f} >= {MAX_DRAWDOWN_ABSOLUTE}")
        send_slack_alert(f"ALERT: Global max drawdown reached: {current_dd:.2f} >= {MAX_DRAWDOWN_ABSOLUTE}")
        # freeze trading (stop new trades)
        return

    # daily loss freeze
    daily_loss = day_start_balance - balance
    if daily_loss >= DAILY_LOSS_ABSOLUTE:
        # set global freeze flag to avoid repeated checks
        global trading_frozen_today
        trading_frozen_today = True
        send_slack_alert(f"ALERT: Daily max loss threshold reached: {daily_loss:.2f} >= {DAILY_LOSS_ABSOLUTE}")
        return

    # enforce max concurrent trades
    if len(open_trades) >= MAX_CONCURRENT_TRADES:
        return

    if not open_trades:
        # no open trades, allow entries
        pass

    if long_signal and len(open_trades) < MAX_CONCURRENT_TRADES:
            entry_price = latest['close']
            atr = latest.get('ATR', 0.001)
            stop_loss = entry_price - ATR_STOP_MULTIPLIER * atr
            take_profit = entry_price + ATR_TP_MULTIPLIER * atr
            risk_amount = balance * RISK_PER_TRADE
            stop_distance = abs(entry_price - stop_loss)
            position_size = risk_amount / stop_distance if stop_distance > 0 else 0
            order_id = place_order('LONG', position_size, stop_loss, take_profit)
            if order_id:
                ot = {
                    'direction': 'LONG',
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'position_size': position_size,
                    'order_id': order_id
                }
                open_trades.append(ot)
                print(f"Demo LONG entry at {entry_price}")

    if short_signal and len(open_trades) < MAX_CONCURRENT_TRADES:
        entry_price = latest['close']
        atr = latest.get('ATR', 0.001)
        stop_loss = entry_price + ATR_STOP_MULTIPLIER * atr
        take_profit = entry_price - ATR_TP_MULTIPLIER * atr
        risk_amount = balance * RISK_PER_TRADE
        stop_distance = abs(entry_price - stop_loss)
        position_size = risk_amount / stop_distance if stop_distance > 0 else 0

        order_id = place_order('SHORT', position_size, stop_loss, take_profit)
        if order_id:
            ot = {
                'direction': 'SHORT',
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'position_size': position_size,
                'order_id': order_id
            }
            open_trades.append(ot)
            print(f"Demo SHORT entry at {entry_price}")

    # Check exits for any open trades (polling style)
    current_price = latest['close']
    to_remove = []
    for idx, ot in enumerate(open_trades):
        exited = False
        if (ot['direction'] == 'LONG' and (current_price <= ot['stop_loss'] or current_price >= ot['take_profit'])) or \
           (ot['direction'] == 'SHORT' and (current_price >= ot['stop_loss'] or current_price <= ot['take_profit'])):
            exit_price = current_price
            gross_profit = (exit_price - ot['entry_price']) * ot['position_size'] if ot['direction'] == 'LONG' else (ot['entry_price'] - exit_price) * ot['position_size']
            commission = COMMISSION_RATE * abs(gross_profit)
            net_profit = gross_profit - commission
            balance += net_profit
            max_balance = max(max_balance, balance)

            trades_log.append({
                'time': latest['time'],
                'direction': ot['direction'],
                'entry_price': ot['entry_price'],
                'exit_price': exit_price,
                'profit': net_profit
            })
            equity_log.append({'time': latest['time'], 'equity': balance})

            print(f"Demo exit at {exit_price}, profit: {net_profit}")
            to_remove.append(idx)
    # remove closed trades in reverse order
    for i in reversed(to_remove):
        open_trades.pop(i)

def main():
    global ACCOUNT_KEY
    print("Starting Saxo demo live trader...")
    # load persistent state if available
    load_state()
    ACCOUNT_KEY = get_account_key()
    if not ACCOUNT_KEY:
        print("Could not fetch account key. Please check credentials.")
        send_slack_alert("ERROR: Could not fetch Saxo account key on trader start.")
        return
    print(f"Using account key: {ACCOUNT_KEY}")
    poll_count = 0
    while True:
        price_data = get_eurusd_price()
        if price_data:
            # reset daily counters at UTC day boundary
            global current_day, day_start_balance, trading_frozen_today
            now_date = datetime.now(timezone.utc).date()
            if now_date != current_day:
                current_day = now_date
                day_start_balance = balance
                trading_frozen_today = False

            data_buffer.append(price_data)
            if len(data_buffer) > 1000:  # Keep buffer manageable
                data_buffer.pop(0)
            check_signals()
            poll_count += 1
            if poll_count % 20 == 0:
                print(f"Status: Price {price_data['close']:.5f}, Balance {balance:.2f}, Polls {poll_count}")
                # Save logs
                with open('../results/live_trades_log.csv', 'w', newline='') as f:
                    if trades_log:
                        writer = csv.DictWriter(f, fieldnames=trades_log[0].keys())
                        writer.writeheader()
                        writer.writerows(trades_log)
                with open('../results/live_equity_log.csv', 'w', newline='') as f:
                    if equity_log:
                        writer = csv.DictWriter(f, fieldnames=equity_log[0].keys())
                        writer.writeheader()
                        writer.writerows(equity_log)
                # heartbeat
                with open('../results/heartbeat.txt', 'w') as hf:
                    hf.write(f"time={datetime.now().isoformat()},price={price_data['close']},balance={balance},frozen={trading_frozen_today}\n")
                # persist state
                save_state()
        time.sleep(30)  # Poll every 30 seconds

if __name__ == '__main__':
    main()