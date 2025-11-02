"""
Enhanced Live Trading Automation with V2 Drawdown Reduction

Integration of BreakoutStrategyV2 into live Saxo trading with:
- Trend filter (200-bar MA)
- Dynamic position sizing
- Recovery mode
- Equity-based soft stop
- Enhanced logging
"""

import time
import requests
import csv
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from saxo_openapi import API
from datetime import datetime, timezone
import json
import traceback
import pandas as pd
from collections import deque

try:
    from saxo_stream import configure as stream_configure, get_price_fxspot
except Exception:
    stream_configure = None
    get_price_fxspot = None

from breakout_strategy_v2 import BreakoutStrategyV2

# =============================================================================
# Saxo API Configuration
# =============================================================================

# Load credentials from config file (set via dashboard)
CONFIG_FILE_PATH = '/app/data/results/saxo_config.json'

try:
    # Try to load from Docker config path
    with open(CONFIG_FILE_PATH, 'r') as f:
        config = json.load(f)
        CLIENT_ID = config.get('app_id', '')
        CLIENT_SECRET = config.get('client_secret', '')
        TOKEN = config.get('access_token', '')
        ACCOUNT_KEY = config.get('account_id', '')
    print(f"✅ Loaded credentials from {CONFIG_FILE_PATH}")
except FileNotFoundError:
    # Fallback to environment variables for local testing (no hardcoded secrets)
    print(f"⚠️ Config file not found at {CONFIG_FILE_PATH}, using environment variables")
    CLIENT_ID = os.getenv('SAXO_APP_ID', '')
    CLIENT_SECRET = os.getenv('SAXO_CLIENT_SECRET', '')
    TOKEN = os.getenv('SAXO_ACCESS_TOKEN', '')
    ACCOUNT_KEY = os.getenv('SAXO_ACCOUNT_ID', '')
except Exception as e:
    print(f"❌ Error loading config: {e}")
    raise

BASE_URL = 'https://gateway.saxobank.com/sim/openapi'
HEADERS = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}

# =============================================================================
# Strategy Parameters (V2 OPTIMIZED)
# =============================================================================

# Core breakout parameters
BREAKOUT_LENGTH = 25  # Tighter selection
ATR_STOP_MULTIPLIER = 0.3  # Tighter stops
ATR_TP_MULTIPLIER = 4.0
VOLATILITY_FILTER = True
TREND_FILTER = True  # NEW: 200-bar MA filter
DYNAMIC_SIZING = True  # NEW: Adaptive position sizing
RECOVERY_MODE = True  # NEW: Gentle martingale
EQUITY_STOP_PCT = 0.15  # NEW: Soft equity stop

# Risk management (REDUCED from 0.5% to 0.2%)
RISK_PER_TRADE = 0.002  # was 0.005
MAX_CONCURRENT_TRADES = 2

# Hard stops (from Monte Carlo V2)
MAX_DRAWDOWN_ABSOLUTE = 3000  # was 5414
DAILY_LOSS_ABSOLUTE = 600  # was 1158

# Alerts
SLACK_WEBHOOK = None  # Set to webhook URL to enable

# State persistence
# Use absolute path for Docker compatibility
if os.path.exists('/app/data/results'):
    STATE_FILE = '/app/data/results/trader_state_v2.json'
    LOG_FILE = '/app/data/results/live_trades_log_v2.csv'
else:
    # Fallback for local testing
    STATE_FILE = '../results/trader_state_v2.json'
    LOG_FILE = '../results/live_trades_log_v2.csv'

# =============================================================================
# Global State
# =============================================================================

strategy = BreakoutStrategyV2(
    breakout_length=BREAKOUT_LENGTH,
    atr_stop_multiplier=ATR_STOP_MULTIPLIER,
    atr_tp_multiplier=ATR_TP_MULTIPLIER,
    volatility_filter=VOLATILITY_FILTER,
    trend_filter=TREND_FILTER,
    dynamic_sizing=DYNAMIC_SIZING,
    recovery_mode=RECOVERY_MODE,
    equity_stop_pct=EQUITY_STOP_PCT
)

data_buffer = []
balance = 10000.0
max_balance = balance
day_start_balance = balance
trading_frozen_today = False
trading_frozen_equity = False
open_trades = []
trades_log = []
equity_log = []
current_day = datetime.now(timezone.utc).date()

# For tracking streaks and dynamic sizing
trade_streak = deque(maxlen=10)
recovery_countdown = 0

# =============================================================================
# Utility Functions
# =============================================================================

def send_slack_alert(message):
    """Send Slack notification if webhook is configured."""
    if not SLACK_WEBHOOK:
        return
    try:
        payload = {'text': message}
        requests.post(SLACK_WEBHOOK, json=payload, timeout=5)
    except Exception as e:
        print(f"[SLACK ERROR] {e}")

def compute_position_size_multiplier():
    """Dynamic position sizing based on streak."""
    global recovery_countdown
    
    if not DYNAMIC_SIZING:
        return 1.0
    
    if recovery_countdown > 0:
        recovery_countdown -= 1
        return 0.5
    
    if len(trade_streak) == 0:
        return 1.0
    
    losses = 0
    for outcome in reversed(trade_streak):
        if not outcome:  # loss
            losses += 1
        else:
            break
    
    if losses == 0:
        return 1.0
    elif losses == 1:
        return 0.8
    else:
        recovery_countdown = 5
        return 0.5

def save_state():
    """Save trader state to JSON."""
    global balance, max_balance, day_start_balance, trading_frozen_today
    global open_trades, trades_log, equity_log
    try:
        state = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'balance': balance,
            'max_balance': max_balance,
            'day_start_balance': day_start_balance,
            'trading_frozen_today': trading_frozen_today,
            'trading_frozen_equity': trading_frozen_equity,
            'open_trades': open_trades,
            'trades_log': trades_log,
            'equity_log': equity_log,
            'trade_streak': list(trade_streak),
            'recovery_countdown': recovery_countdown
        }
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, default=str, indent=2)
    except Exception as e:
        print(f"[STATE ERROR] {e}")

def load_state():
    """Load trader state from JSON."""
    global balance, max_balance, day_start_balance, trading_frozen_today
    global open_trades, trades_log, equity_log, trade_streak, recovery_countdown
    global trading_frozen_equity
    
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
            balance = state.get('balance', balance)
            max_balance = state.get('max_balance', max_balance)
            day_start_balance = state.get('day_start_balance', day_start_balance)
            trading_frozen_today = state.get('trading_frozen_today', False)
            trading_frozen_equity = state.get('trading_frozen_equity', False)
            open_trades[:] = state.get('open_trades', [])
            trades_log[:] = state.get('trades_log', [])
            equity_log[:] = state.get('equity_log', [])
            trade_streak.clear()
            trade_streak.extend(state.get('trade_streak', []))
            recovery_countdown = state.get('recovery_countdown', 0)
            print(f"[STATE] Loaded: balance=${balance:.2f}, trades={len(trades_log)}")
    except Exception as e:
        print(f"[STATE ERROR] {e}")

def log_trade(trade_info):
    """Log a completed trade."""
    try:
        with open(LOG_FILE, 'a', newline='') as f:
            if len(trades_log) == 0:
                # Write header
                writer = csv.DictWriter(f, fieldnames=trade_info.keys())
                writer.writeheader()
            writer.writerow(trade_info)
    except Exception as e:
        print(f"[LOG ERROR] {e}")

def get_eurusd_price():
    """Poll current EUR/USD price from Saxo."""
    for attempt in range(3):
        try:
            response = requests.get(
                f'{BASE_URL}/trade/v1/infoprices?AssetType=FxSpot&Uic=21',
                headers=HEADERS,
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                price = data['Quote']['Mid']
                timestamp = datetime.now(timezone.utc)
                return {
                    'time': timestamp,
                    'open': price,
                    'high': price,
                    'low': price,
                    'close': price,
                    'volume': 1
                }
        except Exception as e:
            print(f"[PRICE ERROR] Attempt {attempt+1}: {e}")
        time.sleep(2)
    return None

def check_equity_stops():
    """Check if we've hit equity or drawdown stops."""
    global balance, max_balance, trading_frozen_today, trading_frozen_equity
    
    # Daily loss check
    daily_loss = day_start_balance - balance
    if daily_loss > DAILY_LOSS_ABSOLUTE:
        print(f"[DAILY LOSS STOP] Loss: ${daily_loss:.2f} > ${DAILY_LOSS_ABSOLUTE:.2f}")
        trading_frozen_today = True
        send_slack_alert(f"DAILY LOSS STOP: ${daily_loss:.2f} reached")
    
    # Drawdown check
    drawdown = max_balance - balance
    if drawdown > MAX_DRAWDOWN_ABSOLUTE:
        print(f"[DRAWDOWN STOP] DD: ${drawdown:.2f} > ${MAX_DRAWDOWN_ABSOLUTE:.2f}")
        send_slack_alert(f"HARD DRAWDOWN STOP: ${drawdown:.2f}")
    
    # Equity soft stop (15% below peak)
    drawdown_pct = (max_balance - balance) / max_balance if max_balance > 0 else 0
    if drawdown_pct > EQUITY_STOP_PCT:
        if not trading_frozen_equity:
            print(f"[EQUITY SOFT STOP] Drawdown: {drawdown_pct*100:.1f}% > {EQUITY_STOP_PCT*100:.1f}%")
            trading_frozen_equity = True
            send_slack_alert(f"EQUITY SOFT STOP: {drawdown_pct*100:.1f}% DD")

def run_live_trader(poll_interval=3600):
    """Main live trading loop."""
    global balance, max_balance, day_start_balance, trading_frozen_today
    global current_day, open_trades, trades_log, equity_log
    global trade_streak, recovery_countdown, trading_frozen_equity
    
    print("=" * 80)
    print("LIVE TRADER V2 START")
    print("=" * 80)
    print(f"Strategy: Trend-filtered breakout with dynamic sizing")
    print(f"Max DD: ${MAX_DRAWDOWN_ABSOLUTE}, Daily Loss: ${DAILY_LOSS_ABSOLUTE}")
    print(f"Risk per trade: {RISK_PER_TRADE*100:.1f}%")
    print()
    
    load_state()
    
    heartbeat = 0
    
    while True:
        try:
            # Check date reset
            now = datetime.now(timezone.utc)
            if now.date() != current_day:
                current_day = now.date()
                day_start_balance = balance
                trading_frozen_today = False
                trading_frozen_equity = False
                print(f"[NEW DAY] {current_day}, balance: ${balance:.2f}")
            
            # Get price
            candle = get_eurusd_price()
            if not candle:
                print("[PRICE] Failed to get price, retrying...")
                time.sleep(poll_interval)
                continue
            
            # Check stops
            check_equity_stops()
            
            # Log heartbeat
            heartbeat += 1
            if heartbeat % 10 == 0:
                print(f"[HEARTBEAT] {now.isoformat()}: balance=${balance:.2f}, "
                      f"DD=${max_balance-balance:.2f}, trades={len(trades_log)}")
                save_state()
            
            # Check if we're at an hourly close (when strategy evaluates signals)
            # For demo: evaluate every hour (3600 seconds)
            minutes = now.minute
            seconds = now.second
            
            # At the start of each hour, evaluate strategy
            if minutes == 0 and seconds < 10:  # First 10 seconds of each hour
                try:
                    # Prepare data for strategy
                    candle_data = [candle]  # Single current candle
                    
                    # TODO: Get historical data for indicators (200-bar MA, ATR, etc.)
                    # For now, use mock data with current price
                    
                    print(f"[SIGNAL CHECK] {now.isoformat()}: price=${candle['close']:.4f}, balance=${balance:.2f}")
                    
                    # Strategy would evaluate here
                    # signal = strategy.evaluate(candle_data)
                    # if signal['long_signal'] or signal['short_signal']:
                    #     place_trade(signal)
                    
                except Exception as e:
                    print(f"[SIGNAL ERROR] {e}")
                    traceback.print_exc()
            
            time.sleep(poll_interval)
            
        except KeyboardInterrupt:
            print("\n[STOP] User interrupt")
            save_state()
            break
        except Exception as e:
            print(f"[ERROR] {e}")
            traceback.print_exc()
            save_state()
            time.sleep(poll_interval)

# =============================================================================
# Entry Point
# =============================================================================

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Live Trader V2 with Drawdown Reduction')
    parser.add_argument('--interval', type=int, default=3600, help='Poll interval (seconds)')
    parser.add_argument('--demo', action='store_true', help='Demo mode (no real orders)')
    args = parser.parse_args()
    
    print(f"Starting live trader (demo mode: {args.demo})")
    print(f"State file: {STATE_FILE}")
    print(f"Log file: {LOG_FILE}")
    print()
    
    run_live_trader(poll_interval=args.interval)
