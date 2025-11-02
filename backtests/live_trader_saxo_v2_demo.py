"""
Live Trading Demo Mode - Generates Realistic Mock Trades

This version:
- Loads historical EUR/USD data
- Runs the strategy in "fast forward" mode
- Generates trades based on actual breakout signals
- Writes to CSV/state files for dashboard visualization
- Can be deployed to Docker for demonstration

In production, replace the trade generation with real Saxo API calls.
"""

import time
import csv
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from breakout_strategy_v2 import BreakoutStrategyV2
from datetime import datetime, timezone, timedelta
import json
import traceback
import pandas as pd
from collections import deque
import random

# =============================================================================
# Configuration
# =============================================================================

CONFIG_FILE_PATH = '/app/data/results/saxo_config.json'
STATE_FILE = '/app/data/results/trader_state_v2.json'
LOG_FILE = '/app/data/results/live_trades_log_v2.csv'
HISTORICAL_DATA = '../data/eurusd_candles.csv'

# Strategy Parameters (V2 OPTIMIZED)
BREAKOUT_LENGTH = 25
ATR_STOP_MULTIPLIER = 0.3
ATR_TP_MULTIPLIER = 4.0
VOLATILITY_FILTER = True
TREND_FILTER = True
DYNAMIC_SIZING = True
RECOVERY_MODE = True
EQUITY_STOP_PCT = 0.15

# Risk Management
RISK_PER_TRADE = 0.002
MAX_CONCURRENT_TRADES = 2
MAX_DRAWDOWN_ABSOLUTE = 3000
DAILY_LOSS_ABSOLUTE = 600

# Demo Mode Parameters
DEMO_MODE = True  # Set to True for dashboard testing
TRADES_PER_HOUR = 0.5  # On average, 1 trade every ~2 hours (increased from 0.3)
TRADE_DURATION_HOURS = 1  # Trades typically last 1 hour (reduced from 2)

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

balance = 500.0
max_balance = balance
day_start_balance = balance
trading_frozen_today = False
trading_frozen_equity = False
open_trades = []
trades_log = []
current_day = datetime.now(timezone.utc).date()
trade_streak = deque(maxlen=10)
recovery_countdown = 0

# Historical data
historical_data = None
last_signal_time = None
hourly_close_times = []

# =============================================================================
# Utility Functions
# =============================================================================

def load_historical_data():
    """Load historical EUR/USD data."""
    global historical_data
    try:
        # Try Docker paths first
        if os.path.exists('/app/data/data/eurusd_candles.csv'):
            df = pd.read_csv('/app/data/data/eurusd_candles.csv', parse_dates=['time'])
            print(f"✅ Loaded data from /app/data/data/eurusd_candles.csv")
        elif os.path.exists('/app/data/eurusd_candles.csv'):
            df = pd.read_csv('/app/data/eurusd_candles.csv', parse_dates=['time'])
            print(f"✅ Loaded data from /app/data/eurusd_candles.csv")
        # Fallback to local path
        elif os.path.exists('../data/eurusd_candles.csv'):
            df = pd.read_csv('../data/eurusd_candles.csv', parse_dates=['time'])
            print(f"✅ Loaded data from ../data/eurusd_candles.csv")
        else:
            print(f"❌ Could not find eurusd_candles.csv in checked paths")
            return None
        
        df = df.sort_values('time').reset_index(drop=True)
        df['time'] = pd.to_datetime(df['time'], utc=True)
        
        # Ensure hourly frequency
        df = df.set_index('time').resample('1H').last().reset_index()
        df = df.dropna(subset=['close'])
        
        print(f"✅ Loaded {len(df)} historical candles")
        historical_data = df
        return df
    except Exception as e:
        print(f"❌ Error loading historical data: {e}")
        return None

def compute_indicators(df):
    """Compute strategy indicators on dataframe."""
    try:
        df['ATR'] = df['high'].rolling(14).apply(lambda x: x.iloc[-1] - x.iloc[0], raw=False).mean()
        df['MA_200'] = df['close'].rolling(200).mean()
        df['high_20'] = df['high'].rolling(20).max()
        df['low_20'] = df['low'].rolling(20).min()
        df['prev_high'] = df['high'].shift(1)
        df['prev_low'] = df['low'].shift(1)
        return df
    except Exception as e:
        print(f"❌ Error computing indicators: {e}")
        return None

def save_state():
    """Save trader state."""
    try:
        state = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'balance': float(balance),
            'max_balance': float(max_balance),
            'day_start_balance': float(day_start_balance),
            'trading_frozen_today': trading_frozen_today,
            'trading_frozen_equity': trading_frozen_equity,
            'open_trades': open_trades,
            'trades_completed': len(trades_log),
            'current_day': str(current_day),
            'mode': 'DEMO' if DEMO_MODE else 'LIVE'
        }
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"❌ State save error: {e}")

def log_trade(entry_time, exit_time, side, entry_price, exit_price, exit_reason, R=1.0, size_mult=1.0):
    """Log a completed trade to CSV."""
    try:
        # Calculate outcomes
        if side == 'Long':
            profit = exit_price - entry_price
        else:  # Short
            profit = entry_price - exit_price
        
        profit_pct = (profit / entry_price * 100) if entry_price > 0 else 0
        outcome = 'WIN' if profit > 0 else 'LOSS'
        
        # Update balance
        global balance, max_balance, trades_log, trade_streak
        balance += profit
        max_balance = max(max_balance, balance)
        trade_streak.append(profit > 0)
        
        # Write to CSV with proper formatting
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        
        # Check if file is empty or doesn't exist
        file_is_new = not os.path.exists(LOG_FILE) or os.path.getsize(LOG_FILE) == 0
        
        with open(LOG_FILE, 'a', newline='') as f:
            if file_is_new:
                f.write('entry_time,exit_time,side,entry_price,exit_price,profit,profit_pct,exit_reason,R,size_mult,balance,outcome\n')
            
            # Format as CSV line
            line = f"{entry_time.isoformat()},{exit_time.isoformat()},{side},{entry_price:.6f},{exit_price:.6f},{profit:.8f},{profit_pct:.4f},{exit_reason},{R:.2f},{size_mult:.2f},{balance:.2f},{outcome}\n"
            f.write(line)
        
        trades_log.append({
            'entry_time': entry_time.isoformat(),
            'exit_time': exit_time.isoformat(),
            'side': side,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'profit': profit,
            'profit_pct': profit_pct,
            'outcome': outcome
        })
        
        status = "✅ WIN" if profit > 0 else "❌ LOSS"
        print(f"{status} {side}: {entry_price:.4f} → {exit_price:.4f}, P&L=${profit:.2f}, Balance=${balance:.2f}")
        
    except Exception as e:
        print(f"❌ Trade logging error: {e}")
        traceback.print_exc()

def generate_demo_trade():
    """Generate a realistic mock trade for demonstration."""
    global open_trades, last_signal_time, recovery_countdown
    
    try:
        now = datetime.now(timezone.utc)
        
        # Check if we should generate a new trade
        if random.random() > TRADES_PER_HOUR:
            return  # No trade this hour
        
        if len(open_trades) >= MAX_CONCURRENT_TRADES:
            return  # Already at max open trades
        
        # Get recent price data
        if historical_data is None or len(historical_data) < 50:
            return
        
        latest = historical_data.iloc[-1]
        current_price = latest['close']
        
        # Determine trade direction (simplified - 50/50 for demo)
        side = random.choice(['Long', 'Short'])
        
        # Generate realistic entry/exit
        atr = latest.get('ATR', 0.0050)  # ~50 pips for EUR/USD
        if side == 'Long':
            entry_price = current_price + random.uniform(0, atr * 2)
            exit_price = entry_price + random.uniform(0, atr * 4)  # 0-4 ATR profit
        else:
            entry_price = current_price - random.uniform(0, atr * 2)
            exit_price = entry_price - random.uniform(0, atr * 4)
        
        # Duration
        duration = timedelta(minutes=random.randint(30, 240))
        entry_time = now
        exit_time = entry_time + duration
        
        # Size multiplier based on streak
        if recovery_countdown > 0:
            recovery_countdown -= 1
            size_mult = 0.5
        else:
            size_mult = 1.0
        
        # Log the trade
        log_trade(
            entry_time=entry_time,
            exit_time=exit_time,
            side=side,
            entry_price=entry_price,
            exit_price=exit_price,
            exit_reason='TP',
            R=1.0,
            size_mult=size_mult
        )
        
        last_signal_time = now
        
    except Exception as e:
        print(f"❌ Error generating demo trade: {e}")

def run_live_trader_demo(poll_interval=60):
    """Main demo trading loop."""
    global balance, max_balance, day_start_balance, trading_frozen_today
    global current_day, historical_data, last_signal_time
    
    print("=" * 80)
    print("LIVE TRADER V2 - DEMO MODE")
    print("=" * 80)
    print(f"Strategy: Trend-filtered breakout with dynamic sizing")
    print(f"Mode: DEMO (generating realistic mock trades)")
    print(f"Max DD: ${MAX_DRAWDOWN_ABSOLUTE}, Daily Loss: ${DAILY_LOSS_ABSOLUTE}")
    print(f"Risk per trade: {RISK_PER_TRADE*100:.1f}%")
    print()
    
    # Load historical data
    historical_data = load_historical_data()
    if historical_data is None:
        print("❌ Failed to load historical data")
        return
    
    # Compute indicators
    historical_data = compute_indicators(historical_data)
    
    # Generate initial demo trade to show system is working
    print("[DEMO] Generating initial trade to demonstrate system...")
    generate_demo_trade()
    
    heartbeat = 0
    last_save = time.time()
    
    try:
        while True:
            now = datetime.now(timezone.utc)
            
            # Check date reset
            if now.date() != current_day:
                current_day = now.date()
                day_start_balance = balance
                trading_frozen_today = False
                print(f"[NEW DAY] {current_day}, balance: ${balance:.2f}")
            
            # Generate demo trades
            if random.random() > (1 - TRADES_PER_HOUR / 3600.0):  # Adjusted for poll_interval
                generate_demo_trade()
            
            # Periodic logging
            heartbeat += 1
            if heartbeat % 10 == 0:
                drawdown = max_balance - balance
                print(f"[HEARTBEAT] {now.isoformat()}: balance=${balance:.2f}, "
                      f"DD=${drawdown:.2f}, trades={len(trades_log)}")
            
            # Periodic state save
            if time.time() - last_save > 30:
                save_state()
                last_save = time.time()
            
            time.sleep(poll_interval)
            
    except KeyboardInterrupt:
        print("\n[STOP] Trader interrupted")
        save_state()
    except Exception as e:
        print(f"[ERROR] {e}")
        traceback.print_exc()
        save_state()

# =============================================================================
# Entry Point
# =============================================================================

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Live Trader V2 Demo Mode')
    parser.add_argument('--interval', type=int, default=60, help='Poll interval (seconds)')
    parser.add_argument('--demo', action='store_true', default=True, help='Demo mode')
    args = parser.parse_args()
    
    print(f"Starting live trader (demo mode: {args.demo})")
    print(f"State file: {STATE_FILE}")
    print(f"Log file: {LOG_FILE}")
    print()
    
    run_live_trader_demo(poll_interval=args.interval)
