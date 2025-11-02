"""
Monte Carlo stress test for the best config.
Runs multiple forward tests on bootstrapped (resampled) data to assess robustness.
"""
import pandas as pd
import numpy as np
import sys
sys.path.append('backtests')
from forward_test import forward_test
import os

def monte_carlo_test(data_path, results_dir, best_config, n_runs=100):
    df = pd.read_csv(data_path)
    results = []
    for i in range(n_runs):
        # Bootstrap resample
        resampled_df = df.sample(n=len(df), replace=True).sort_values('time').reset_index(drop=True)
        resampled_df['time'] = pd.to_datetime(resampled_df['time'])
        resampled_df = resampled_df.set_index('time').reset_index()  # make time column again
        temp_csv = os.path.join(results_dir, f'temp_mc_{i}.csv')
        resampled_df.to_csv(temp_csv, index=False)
        
        trades_df, _, equity_df = forward_test(
            data_path=temp_csv,
            results_dir=results_dir,
            initial_balance=10000.0,
            risk_per_trade=best_config['risk'],
            commission_rate=0.0001,
            slippage_atr_frac=0.02,  # realistic
            breakout_length=int(best_config['breakout_length']),
            atr_stop_multiplier=best_config['stop_mul'],
            atr_tp_multiplier=best_config['tp_mul'],
            volatility_filter=True,
        )
        
        trades_df['profit'] = pd.to_numeric(trades_df['profit'], errors='coerce')
        total_profit = float(trades_df['profit'].sum()) if not trades_df.empty else 0.0
        try:
            equity_df['equity'] = pd.to_numeric(equity_df['equity'], errors='coerce').ffill().fillna(0.0)
            equity_df['cummax'] = equity_df['equity'].cummax()
            equity_df['dd'] = equity_df['cummax'] - equity_df['equity']
            max_dd = float(equity_df['dd'].max())
        except:
            max_dd = 0.0
        
        results.append({'run': i, 'total_profit': total_profit, 'max_drawdown': max_dd})
        os.remove(temp_csv)  # clean up
    
    results_df = pd.DataFrame(results)
    mc_csv = os.path.join(results_dir, 'monte_carlo_results.csv')
    results_df.to_csv(mc_csv, index=False)
    
    # Summary stats
    mean_profit = results_df['total_profit'].mean()
    std_profit = results_df['total_profit'].std()
    mean_dd = results_df['max_drawdown'].mean()
    std_dd = results_df['max_drawdown'].std()
    prob_positive = (results_df['total_profit'] > 0).mean()
    
    print(f"Monte Carlo ({n_runs} runs):")
    print(f"Mean profit: {mean_profit:.2f} ± {std_profit:.2f}")
    print(f"Mean max DD: {mean_dd:.2f} ± {std_dd:.2f}")
    print(f"Prob profit > 0: {prob_positive:.2%}")
    print(f"Saved to {mc_csv}")

if __name__ == '__main__':
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    data_path = os.path.join(repo_root, 'data', 'v75_candles.csv')
    results_dir = os.path.join(repo_root, 'results')
    best_config = {'breakout_length': 30, 'stop_mul': 0.5, 'tp_mul': 2.0, 'risk': 0.02}
    monte_carlo_test(data_path, results_dir, best_config, n_runs=50)  # fewer for speed