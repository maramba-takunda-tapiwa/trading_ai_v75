"""
Enhanced Monte Carlo validation for V2 strategy.
Uses the same 1000-sim block-bootstrap approach but with V2 improvements.
"""

import argparse
import pandas as pd
import numpy as np
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from breakout_strategy_v2 import BreakoutStrategyV2

DATA_PATH = '../data/eurusd_candles.csv'
RESULTS_DIR = '../results/'
N_SIMS = 200
BLOCK_SIZE = 24

os.makedirs(RESULTS_DIR, exist_ok=True)

def block_bootstrap_prices(df, block_size=24):
    """Block bootstrap on returns to create synthetic price series."""
    closes = df['close'].values
    logret = np.log(closes[1:] / closes[:-1])
    n = len(logret)
    starts = np.arange(0, n - block_size + 1)
    blocks_needed = int(np.ceil(n / block_size))
    sampled = []
    for _ in range(blocks_needed):
        s = np.random.choice(starts)
        sampled.append(logret[s:s + block_size])
    sampled = np.concatenate(sampled)[:n]
    
    new_closes = [closes[0]]
    for r in sampled:
        new_closes.append(new_closes[-1] * np.exp(r))
    new_closes = np.array(new_closes)
    
    opens = new_closes[:-1]
    closes = new_closes[1:]
    highs = np.maximum(opens, closes) * (1 + np.abs(np.random.normal(0, 0.0005, size=len(closes))))
    lows = np.minimum(opens, closes) * (1 - np.abs(np.random.normal(0, 0.0005, size=len(closes))))
    
    times = pd.to_datetime(df['time'], utc=True).iloc[1:].reset_index(drop=True)
    
    out = pd.DataFrame({
        'time': times,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': 1
    })
    return out

def run_mc_v2(n_sims=N_SIMS, block_size=BLOCK_SIZE):
    """Run enhanced Monte Carlo with V2 strategy."""
    
    if not os.path.exists(DATA_PATH):
        print('Data not found:', DATA_PATH)
        return
    
    df = pd.read_csv(DATA_PATH)
    df = df.sort_values('time').reset_index(drop=True)
    
    print("=" * 80)
    print(f"Monte Carlo V2: {n_sims} simulations with V2 strategy")
    print("=" * 80)
    print()
    
    mc_results = []
    
    for i in range(n_sims):
        synth = block_bootstrap_prices(df, block_size=block_size)
        sim_csv = os.path.join(RESULTS_DIR, f'tmp_mc_v2_{i}.csv')
        synth.to_csv(sim_csv, index=False)
        
        # Run V2 strategy
        strategy = BreakoutStrategyV2(
            breakout_length=25,  # improved
            atr_stop_multiplier=0.3,
            atr_tp_multiplier=4.0,
            volatility_filter=True,
            trend_filter=True,  # KEY: trend filter
            dynamic_sizing=True,  # KEY: dynamic sizing
            recovery_mode=True,  # KEY: recovery mode
            equity_stop_pct=0.15  # KEY: equity stop
        )
        
        strategy.load_data(sim_csv)
        trades_df = strategy.run_backtest(initial_balance=10000.0, risk_per_trade=0.002)
        
        # Compute metrics
        if len(trades_df) == 0:
            pf = 0
            profit = 0
            max_dd = 0
            trades = 0
            win_rate = 0
        else:
            gross_profit = trades_df[trades_df['R'] > 0]['R'].sum()
            gross_loss = -trades_df[trades_df['R'] < 0]['R'].sum()
            pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            
            total_r = trades_df['R'].sum()
            profit = total_r  # in R units
            
            # Drawdown
            if len(strategy.equity_curve) > 0:
                max_dd = (np.maximum.accumulate(strategy.equity_curve) - strategy.equity_curve).max()
            else:
                max_dd = 0
            
            trades = len(trades_df)
            wins = (trades_df['R'] > 0).sum()
            win_rate = wins / trades if trades > 0 else 0
        
        mc_results.append({
            'sim': i,
            'pf': pf,
            'profit': profit,
            'max_dd': max_dd,
            'trades': trades,
            'win_rate': win_rate
        })
        
        if (i + 1) % max(1, n_sims // 10) == 0:
            print(f"Sim {i+1}/{n_sims}: PF={pf:.2f}, Profit={profit:.2f}, MaxDD={max_dd:.2f}, WR={win_rate*100:.1f}%, Trades={trades}")
    
    mc_df = pd.DataFrame(mc_results)
    
    # Save results
    output_file = os.path.join(RESULTS_DIR, 'monte_carlo_v2_results.csv')
    mc_df.to_csv(output_file, index=False)
    
    print()
    print("=" * 80)
    print("MONTE CARLO V2 SUMMARY (1000-SIM equivalent statistics)")
    print("=" * 80)
    print()
    
    print(f"Profit Factor (PF):")
    print(f"  Mean: {mc_df['pf'].mean():.3f}")
    print(f"  Median: {mc_df['pf'].median():.3f}")
    print(f"  Std: {mc_df['pf'].std():.3f}")
    print(f"  5th percentile: {mc_df['pf'].quantile(0.05):.3f}")
    print(f"  25th percentile: {mc_df['pf'].quantile(0.25):.3f}")
    print(f"  75th percentile: {mc_df['pf'].quantile(0.75):.3f}")
    print(f"  95th percentile: {mc_df['pf'].quantile(0.95):.3f}")
    print(f"  % with PF > 1.0: {(mc_df['pf'] > 1.0).sum() / len(mc_df) * 100:.1f}%")
    print()
    
    print(f"Profit (R units):")
    print(f"  Mean: {mc_df['profit'].mean():.2f}")
    print(f"  Median: {mc_df['profit'].median():.2f}")
    print(f"  Std: {mc_df['profit'].std():.2f}")
    print(f"  5th percentile: {mc_df['profit'].quantile(0.05):.2f}")
    print(f"  25th percentile: {mc_df['profit'].quantile(0.25):.2f}")
    print(f"  75th percentile: {mc_df['profit'].quantile(0.75):.2f}")
    print(f"  95th percentile: {mc_df['profit'].quantile(0.95):.2f}")
    print(f"  % with profit > 0: {(mc_df['profit'] > 0).sum() / len(mc_df) * 100:.1f}%")
    print()
    
    print(f"Max Drawdown (USD):")
    print(f"  Mean: {mc_df['max_dd'].mean():.2f}")
    print(f"  Median: {mc_df['max_dd'].median():.2f}")
    print(f"  Std: {mc_df['max_dd'].std():.2f}")
    print(f"  5th percentile: {mc_df['max_dd'].quantile(0.05):.2f}")
    print(f"  25th percentile: {mc_df['max_dd'].quantile(0.25):.2f}")
    print(f"  75th percentile: {mc_df['max_dd'].quantile(0.75):.2f}")
    print(f"  95th percentile: {mc_df['max_dd'].quantile(0.95):.2f}")
    print()
    
    print(f"Win Rate (%):")
    print(f"  Mean: {mc_df['win_rate'].mean() * 100:.1f}%")
    print(f"  Median: {mc_df['win_rate'].median() * 100:.1f}%")
    print(f"  Std: {mc_df['win_rate'].std() * 100:.1f}%")
    print()
    
    print(f"Trades per sim:")
    print(f"  Mean: {mc_df['trades'].mean():.0f}")
    print(f"  Median: {mc_df['trades'].median():.0f}")
    print()
    
    print("=" * 80)
    print()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Monte Carlo V2 runner')
    parser.add_argument('--sims', type=int, default=N_SIMS, help='Number of simulations')
    parser.add_argument('--block-size', type=int, default=BLOCK_SIZE, help='Block size in bars')
    args = parser.parse_args()
    
    run_mc_v2(n_sims=args.sims, block_size=args.block_size)
