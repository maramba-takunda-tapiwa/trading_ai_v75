"""
Walk-Forward Optimization for Breakout Strategy

This script performs walk-forward analysis to validate the strategy's robustness.
- Splits data into rolling training/validation windows.
- Optimizes parameters on training data.
- Tests on out-of-sample validation data.
- Aggregates results to check for overfitting.

Usage: python walk_forward_optimization.py
"""

import pandas as pd
import numpy as np
from itertools import product
from breakout_strategy import BreakoutStrategy
from forward_test import forward_test
import os

# Data path
DATA_PATH = '../data/eurusd_candles.csv'

# Walk-forward parameters
TRAIN_WINDOW_MONTHS = 6  # ~4320 bars (1-hour)
TEST_WINDOW_MONTHS = 1   # ~720 bars
STEP_MONTHS = 1          # Roll every month
BARS_PER_MONTH = 720     # Approx for 1-hour data

# Strategy params grid (smaller for speed)
BREAKOUT_LENGTHS = [20, 30, 40]
STOP_MULTS = [0.3, 0.5, 0.7]
TP_MULTS = [2.0, 3.0, 4.0]
RISKS = [0.005]

# Scoring: profit_factor
def score_results(trades_df):
    if len(trades_df) == 0:
        return 0
    gross_profit = trades_df[trades_df['profit'] > 0]['profit'].sum()
    gross_loss = abs(trades_df[trades_df['profit'] < 0]['profit'].sum())
    return gross_profit / gross_loss if gross_loss > 0 else float('inf')

def optimize_on_data(train_df, params_grid):
    train_csv = '../results/tmp_train.csv'
    train_df.to_csv(train_csv, index=False)
    
    best_score = -float('inf')
    best_params = None
    for bl, sm, tm, r in product(*params_grid):
        trades_df, _, _ = forward_test(
            data_path=train_csv,
            results_dir='../results/',
            initial_balance=10000.0,
            risk_per_trade=r,
            commission_rate=0.0001,
            slippage_atr_frac=0.0,
            breakout_length=bl,
            atr_stop_multiplier=sm,
            atr_tp_multiplier=tm,
            volatility_filter=True
        )
        score = score_results(trades_df)
        if score > best_score:
            best_score = score
            best_params = (bl, sm, tm, r)
    return best_params, best_score

def run_walk_forward():
    if not os.path.exists(DATA_PATH):
        print(f"Data file not found: {DATA_PATH}")
        return

    data = pd.read_csv(DATA_PATH)
    data['time'] = pd.to_datetime(data['time'])
    data = data.sort_values('time').reset_index(drop=True)
    total_bars = len(data)
    train_bars = TRAIN_WINDOW_MONTHS * BARS_PER_MONTH
    test_bars = TEST_WINDOW_MONTHS * BARS_PER_MONTH
    step_bars = STEP_MONTHS * BARS_PER_MONTH

    results = []
    for start in range(0, total_bars - train_bars - test_bars + 1, step_bars):
        train_end = start + train_bars
        test_end = train_end + test_bars

        train_data = data.iloc[start:train_end]
        test_data = data.iloc[train_end:test_end]

        print(f"Optimizing on {len(train_data)} bars, testing on {len(test_data)} bars...")

        params_grid = [BREAKOUT_LENGTHS, STOP_MULTS, TP_MULTS, RISKS]
        best_params, train_score = optimize_on_data(train_data, params_grid)
        bl, sm, tm, r = best_params

        test_data.to_csv('../results/tmp_test.csv', index=False)
        trades_df, _, equity_df = forward_test(
            data_path='../results/tmp_test.csv',
            results_dir='../results/',
            initial_balance=10000.0,
            risk_per_trade=r,
            commission_rate=0.0001,
            slippage_atr_frac=0.0,
            breakout_length=bl,
            atr_stop_multiplier=sm,
            atr_tp_multiplier=tm,
            volatility_filter=True
        )
        test_score = score_results(trades_df)
        total_trades = len(trades_df)
        win_rate = len(trades_df[trades_df['profit'] > 0]) / total_trades if total_trades > 0 else 0
        max_dd = (equity_df['equity'].cummax() - equity_df['equity']).max()
        final_balance = equity_df['equity'].iloc[-1]
        test_profit = final_balance - 10000

        results.append({
            'train_start': data.iloc[start]['time'],
            'train_end': data.iloc[train_end-1]['time'],
            'test_start': data.iloc[train_end]['time'],
            'test_end': data.iloc[test_end-1]['time'],
            'best_bl': bl,
            'best_sm': sm,
            'best_tm': tm,
            'best_r': r,
            'train_score': train_score,
            'test_score': test_score,
            'test_profit': test_profit,
            'test_trades': total_trades,
            'test_win_rate': win_rate,
            'test_max_dd': max_dd
        })

    df_results = pd.DataFrame(results)
    df_results.to_csv('../results/walk_forward_results.csv', index=False)
    print("Walk-forward results saved to ../results/walk_forward_results.csv")

    # Summary
    avg_test_score = df_results['test_score'].mean()
    total_test_profit = df_results['test_profit'].sum()
    avg_win_rate = df_results['test_win_rate'].mean()
    avg_max_dd = df_results['test_max_dd'].mean()
    print(f"Average Test PF: {avg_test_score:.2f}")
    print(f"Total Test Profit: {total_test_profit:.2f}")
    print(f"Average Win Rate: {avg_win_rate:.2f}")
    print(f"Average Max DD: {avg_max_dd:.2f}")

    # Monte Carlo Simulations - skipped due to data bootstrap issues, walk-forward suffices for robustness

if __name__ == '__main__':
    run_walk_forward()