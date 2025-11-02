"""
Quick re-optimization for robustness: grid search with drawdown penalty.
Objective: PF - lambda * (maxDD / 1000)  => maximize PF while penalizing large drawdowns

Runs walk-forward style (train 6m, test 1m) and saves best configs to ../results/
"""

import pandas as pd
import numpy as np
from itertools import product
import os
from forward_test import forward_test
from pathlib import Path

DATA_PATH = '../data/eurusd_candles.csv'
RESULTS_DIR = '../results/'

def evaluate_config(data_df, bl, st, tp, risk, lambda_dd=0.005):
    """
    Run forward_test on data_df with given config, compute penalty objective.
    Returns: (objective_score, pf, profit, max_dd)
    """
    # save temp data
    temp_csv = os.path.join(RESULTS_DIR, '_temp_eval.csv')
    data_df.to_csv(temp_csv, index=False)
    
    try:
        trades_df, signals_df, equity_df = forward_test(
            data_path=temp_csv,
            results_dir=RESULTS_DIR,
            initial_balance=10000.0,
            risk_per_trade=risk,
            commission_rate=0.0001,
            slippage_atr_frac=0.02,
            slippage_spread=0.00015,
            slippage_random_std=0.05,
            breakout_length=bl,
            atr_stop_multiplier=st,
            atr_tp_multiplier=tp,
            volatility_filter=True
        )
        
        if len(trades_df) == 0:
            return -100, 0, 0, 0  # penalize no trades
        
        gross_profit = trades_df[trades_df['profit'] > 0]['profit'].sum()
        gross_loss = -trades_df[trades_df['profit'] < 0]['profit'].sum()
        pf = gross_profit / gross_loss if gross_loss > 0 else 0
        profit = equity_df['equity'].iloc[-1] - 10000 if len(equity_df) > 0 else 0
        max_dd = (equity_df['equity'].cummax() - equity_df['equity']).max() if len(equity_df) > 0 else 0
        
        # objective with drawdown penalty
        obj = pf - lambda_dd * (max_dd / 1000)
        return obj, pf, profit, max_dd
    except Exception as e:
        print(f"  Error evaluating config: {e}")
        return -100, 0, 0, 0
    finally:
        if os.path.exists(temp_csv):
            os.remove(temp_csv)


def main():
    if not os.path.exists(DATA_PATH):
        print(f"Data not found: {DATA_PATH}")
        return
    
    df = pd.read_csv(DATA_PATH)
    df = df.sort_values('time').reset_index(drop=True)
    
    # split into train and test (last month for test, rest for train)
    n = len(df)
    test_start_idx = int(n * 0.97)  # roughly last 3% as test
    train_df = df.iloc[:test_start_idx].copy()
    test_df = df.iloc[test_start_idx:].copy()
    
    print(f"Data split: train={len(train_df)}, test={len(test_df)}")
    print("="*70)
    
    # grid search on train set
    bl_range = [20, 30, 40]
    st_range = [0.3, 0.5, 0.7]
    tp_range = [2.0, 3.0, 4.0]
    risk_range = [0.003, 0.005, 0.01]
    lambda_dd = 0.005  # drawdown penalty weight
    
    best_configs = []
    total = len(bl_range) * len(st_range) * len(tp_range) * len(risk_range)
    count = 0
    
    print(f"Grid search: {total} configs")
    for bl, st, tp, risk in product(bl_range, st_range, tp_range, risk_range):
        count += 1
        if count % 10 == 0:
            print(f"  [{count}/{total}] ...", end='\r')
        
        obj, pf, profit, max_dd = evaluate_config(train_df, bl, st, tp, risk, lambda_dd)
        best_configs.append({
            'breakout_length': bl,
            'atr_stop_mult': st,
            'atr_tp_mult': tp,
            'risk_per_trade': risk,
            'train_obj': obj,
            'train_pf': pf,
            'train_profit': profit,
            'train_maxdd': max_dd,
        })
    
    # sort by objective
    best_configs_df = pd.DataFrame(best_configs).sort_values('train_obj', ascending=False)
    
    print(f"\nTop 10 configs by objective (with drawdown penalty):")
    print(best_configs_df.head(10).to_string(index=False))
    
    # validate top 5 on test set
    print("\n" + "="*70)
    print("Validating top 5 configs on test set:")
    for idx, row in best_configs_df.head(5).iterrows():
        bl, st, tp, risk = row['breakout_length'], row['atr_stop_mult'], row['atr_tp_mult'], row['risk_per_trade']
        test_obj, test_pf, test_profit, test_maxdd = evaluate_config(test_df, bl, st, tp, risk, lambda_dd)
        print(f"  [{int(bl)}, {st:.1f}, {tp:.1f}, {risk:.3f}] "
              f"train: PF={row['train_pf']:.2f}, test: PF={test_pf:.2f}, profit={test_profit:.0f}, maxDD={test_maxdd:.0f}")
    
    # save top 20
    top20 = best_configs_df.head(20)
    out_path = os.path.join(RESULTS_DIR, 'reopt_candidates.csv')
    top20.to_csv(out_path, index=False)
    print(f"\nTop 20 configs saved to {out_path}")
    print("Next: Run Monte Carlo on best 3 configs to validate out-of-sample robustness.")


if __name__ == '__main__':
    main()
