"""
Generate demo V3 data for dashboard testing

Creates sample multi-strategy trades, monitor state, and capital state
to test the V3 dashboard integration.
"""

import pandas as pd
import json
from datetime import datetime, timedelta, timezone
import random
import os

# Output directory
RESULTS_DIR = '../results'
os.makedirs(RESULTS_DIR, exist_ok=True)

# =============================================================================
# Generate V3 Trades
# =============================================================================

print("=" * 70)
print(" " * 15 + "GENERATING V3 DEMO DATA")
print("=" * 70)

strategies = ['EUR/USD Breakout', 'GBP/USD Breakout', 'USD/JPY Trend']
pairs = ['EURUSD', 'GBPUSD', 'USDJPY']

trades = []
balance = 500.0
base_time = datetime.now(timezone.utc) - timedelta(days=30)

for i in range(50):
    strategy_idx = random.randint(0, 2)
    strategy = strategies[strategy_idx]
    pair = pairs[strategy_idx]
    
    # Generate trade
    win = random.random() < 0.755  # 75.5% win rate
    
    if win:
        R = random.uniform(2.5, 5.0)
        profit = random.uniform(8, 20)
        outcome = 'WIN'
    else:
        R = -1.0
        profit = random.uniform(-10, -5)
        outcome = 'LOSS'
    
    balance += profit
    
    entry_time = base_time + timedelta(hours=i * 12)
    exit_time = entry_time + timedelta(hours=random.randint(1, 6))
    
    trades.append({
        'entry_time': entry_time.isoformat(),
        'exit_time': exit_time.isoformat(),
        'strategy': strategy,
        'pair': pair,
        'side': random.choice(['LONG', 'SHORT']),
        'entry_price': round(random.uniform(1.05, 1.10), 5),
        'exit_price': round(random.uniform(1.05, 1.10), 5),
        'profit': round(profit, 2),
        'R': round(R, 2),
        'outcome': outcome,
        'balance': round(balance, 2),
        'regime': random.choice(['TRENDING', 'RANGING']),
    })

# Save trades
df_trades = pd.DataFrame(trades)
trades_file = os.path.join(RESULTS_DIR, 'live_trades_v3_multi.csv')
df_trades.to_csv(trades_file, index=False)

print(f"\n✅ Generated {len(trades)} trades")
print(f"   Saved to: {trades_file}")
print(f"   Win Rate: {100 * (df_trades['outcome'] == 'WIN').sum() / len(df_trades):.1f}%")
print(f"   Final Balance: ${balance:.2f}")

# =============================================================================
# Generate V3 Monitor State
# =============================================================================

monitor_state = {
    'trading_enabled': True,
    'shutdown_reason': None,
    'total_trades': len(trades),
    'win_rate': 100 * (df_trades['outcome'] == 'WIN').sum() / len(df_trades),
    'sharpe_ratio': 2.35,
    'consecutive_loss_days': 0,
    'current_balance': balance,
    'peak_balance': balance,
    'current_drawdown': 0.0,
    'recent_alerts': [
        {
            'timestamp': (datetime.now(timezone.utc) - timedelta(days=5)).isoformat(),
            'level': 'WARNING',
            'message': 'Drawdown reached 5.2%',
        },
        {
            'timestamp': (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
            'level': 'INFO',
            'message': 'Win rate recovered to 75%',
        },
    ],
    'last_update': datetime.now(timezone.utc).isoformat(),
}

monitor_file = os.path.join(RESULTS_DIR, 'v3_monitor_state.json')
with open(monitor_file, 'w') as f:
    json.dump(monitor_state, f, indent=2)

print(f"\n✅ Generated monitor state")
print(f"   Saved to: {monitor_file}")
print(f"   Sharpe Ratio: {monitor_state['sharpe_ratio']}")
print(f"   Trading Enabled: {monitor_state['trading_enabled']}")

# =============================================================================
# Generate V3 Capital State
# =============================================================================

capital_state = {
    'initial_capital': 500.0,
    'current_capital': balance,
    'peak_capital': balance,
    'total_withdrawn': 150.0,
    'total_added': 0.0,
    'latest_sharpe': 2.35,
    'withdrawal_history': [
        {
            'timestamp': (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
            'profit': 50.0,
            'withdrawn': 25.0,
            'reinvested': 25.0,
            'total_withdrawn': 25.0,
        },
        {
            'timestamp': (datetime.now(timezone.utc) - timedelta(days=60)).isoformat(),
            'profit': 80.0,
            'withdrawn': 40.0,
            'reinvested': 40.0,
            'total_withdrawn': 65.0,
        },
        {
            'timestamp': (datetime.now(timezone.utc) - timedelta(days=90)).isoformat(),
            'profit': 170.0,
            'withdrawn': 85.0,
            'reinvested': 85.0,
            'total_withdrawn': 150.0,
        },
    ],
    'capital_history': [],
    'last_update': datetime.now(timezone.utc).isoformat(),
}

capital_file = os.path.join(RESULTS_DIR, 'v3_capital_state.json')
with open(capital_file, 'w') as f:
    json.dump(capital_state, f, indent=2)

print(f"\n✅ Generated capital state")
print(f"   Saved to: {capital_file}")
print(f"   Current Capital: ${capital_state['current_capital']:.2f}")
print(f"   Total Withdrawn: ${capital_state['total_withdrawn']:.2f}")
print(f"   Total Value: ${capital_state['current_capital'] + capital_state['total_withdrawn']:.2f}")

# =============================================================================
# Summary
# =============================================================================

print("\n" + "=" * 70)
print(" " * 15 + "V3 DEMO DATA GENERATION COMPLETE")
print("=" * 70)

print(f"\n📊 Summary:")
print(f"   Trades: {len(trades)}")
print(f"   Strategies: {len(strategies)}")
print(f"   Win Rate: {100 * (df_trades['outcome'] == 'WIN').sum() / len(df_trades):.1f}%")
print(f"   Final Balance: ${balance:.2f}")
print(f"   Total Value: ${balance + capital_state['total_withdrawn']:.2f}")
print(f"   ROI: {100 * (balance + capital_state['total_withdrawn'] - 500) / 500:.1f}%")

print(f"\n✅ Dashboard should now show V3 data!")
print(f"   Run the Flask app to test: py docker_app/app.py")
print(f"   Open: http://localhost:5000")

print("\n" + "=" * 70)
