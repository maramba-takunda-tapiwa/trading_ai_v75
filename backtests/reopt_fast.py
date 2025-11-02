"""
Fast re-optimization + validation:
1. Quick grid search on train data to find top-PF configs
2. Run 200-sim Monte Carlo on best 3 configs
3. Compare results to baseline (current config) and present findings
"""

import pandas as pd
import numpy as np
from itertools import product
import os
import sys
from pathlib import Path

# Add backtests dir to path
sys.path.insert(0, str(Path(__file__).parent))

from forward_test import forward_test

DATA_PATH = '../data/eurusd_candles.csv'
RESULTS_DIR = '../results/'
os.makedirs(RESULTS_DIR, exist_ok=True)

def evaluate_config(data_df, bl, st, tp, risk, name=""):
    """Evaluate a config on given data. Returns (pf, profit, max_dd, trades)"""
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
            breakout_length=int(bl),
            atr_stop_multiplier=st,
            atr_tp_multiplier=tp,
            volatility_filter=True
        )
        
        if len(trades_df) == 0:
            return 0, 0, 0, 0
        
        gross_profit = trades_df[trades_df['profit'] > 0]['profit'].sum()
        gross_loss = -trades_df[trades_df['profit'] < 0]['profit'].sum()
        pf = gross_profit / gross_loss if gross_loss > 0 else 0
        profit = equity_df['equity'].iloc[-1] - 10000 if len(equity_df) > 0 else 0
        max_dd = (equity_df['equity'].cummax() - equity_df['equity']).max() if len(equity_df) > 0 else 0
        trades = len(trades_df)
        
        return pf, profit, max_dd, trades
    except Exception as e:
        print(f"  Error: {e}")
        return 0, 0, 0, 0
    finally:
        if os.path.exists(temp_csv):
            os.remove(temp_csv)


def main():
    if not os.path.exists(DATA_PATH):
        print(f"Data not found: {DATA_PATH}")
        return
    
    df = pd.read_csv(DATA_PATH)
    df = df.sort_values('time').reset_index(drop=True)
    
    # split train/test
    n = len(df)
    split_idx = int(n * 0.95)  # last 5% for test
    train_df = df.iloc[:split_idx].copy()
    test_df = df.iloc[split_idx:].copy()
    
    print(f"Quick Re-Optimization with Drawdown Focus")
    print(f"Data: train={len(train_df)} bars, test={len(test_df)} bars")
    print("="*70)
    
    # Current baseline config
    baseline = {'bl': 30, 'st': 0.5, 'tp': 4.0, 'risk': 0.005}
    print(f"\nBaseline config: bl={baseline['bl']}, st={baseline['st']}, tp={baseline['tp']}, risk={baseline['risk']}")
    bl, st, tp, risk = baseline['bl'], baseline['st'], baseline['tp'], baseline['risk']
    pf, profit, maxdd, trades = evaluate_config(train_df, bl, st, tp, risk)
    print(f"  Train: PF={pf:.2f}, profit={profit:.0f}, maxDD={maxdd:.0f}, trades={trades}")
    bl, st, tp, risk = baseline['bl'], baseline['st'], baseline['tp'], baseline['risk']
    pf, profit, maxdd, trades = evaluate_config(test_df, bl, st, tp, risk)
    print(f"  Test:  PF={pf:.2f}, profit={profit:.0f}, maxDD={maxdd:.0f}, trades={trades}")
    
    # Grid search: focus on drawdown-efficient configs
    print("\nGrid search (small grid)...")
    configs = []
    for bl in [20, 25, 30, 35, 40]:
        for st in [0.3, 0.5, 0.7, 1.0]:  # higher stops might reduce whipsaws
            for tp in [2.0, 3.0, 4.0]:
                risk = 0.005  # fix risk to speed up
                pf, profit, maxdd, trades = evaluate_config(train_df, bl, st, tp, risk)
                configs.append({
                    'bl': bl, 'st': st, 'tp': tp, 'risk': risk,
                    'pf': pf, 'profit': profit, 'maxdd': maxdd, 'trades': trades,
                    'score': pf - 0.002 * (maxdd / 1000)  # score = PF with DD penalty
                })
    
    configs_df = pd.DataFrame(configs).sort_values('score', ascending=False)
    print(f"Top 5 configs by score (PF - 0.002*DD/1000):")
    print(configs_df.head(5)[['bl', 'st', 'tp', 'pf', 'maxdd', 'trades', 'score']].to_string(index=False))
    
    # Validate top 3 on test
    print("\nTest set validation:")
    top3_test = []
    for idx, row in configs_df.head(3).iterrows():
        bl, st, tp, risk = int(row['bl']), row['st'], row['tp'], row['risk']
        pf, profit, maxdd, trades = evaluate_config(test_df, bl, st, tp, risk)
        top3_test.append({'bl': bl, 'st': st, 'tp': tp, 'pf': pf, 'profit': profit, 'maxdd': maxdd})
        print(f"  [{bl}, {st:.1f}, {tp:.1f}]: PF={pf:.2f}, profit={profit:.0f}, maxDD={maxdd:.0f}")
    
    # Save candidates for Monte Carlo
    candidates = configs_df.head(3).copy()
    candidates[['bl', 'st', 'tp', 'risk']].to_csv(os.path.join(RESULTS_DIR, 'reopt_top3_for_mc.csv'), index=False)
    print(f"\nTop 3 candidates saved to reopt_top3_for_mc.csv")
    print("\nNext: Run 'py monte_carlo_validate.py' to test these configs with 200-sim Monte Carlo")


if __name__ == '__main__':
    main()
