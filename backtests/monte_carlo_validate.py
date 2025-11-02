"""
Monte Carlo validation of top 3 re-optimized configs.
Runs 200 sims on each and compares to baseline.
"""

import pandas as pd
import numpy as np
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from forward_test import forward_test

DATA_PATH = '../data/eurusd_candles.csv'
RESULTS_DIR = '../results/'

def run_mc_on_config(n_sims, bl, st, tp, risk, config_name="", slippage_mult=1.0):
    """Run n_sims Monte Carlo on a given config"""
    if not os.path.exists(DATA_PATH):
        print(f"Data not found: {DATA_PATH}")
        return pd.DataFrame()
    
    df = pd.read_csv(DATA_PATH)
    df = df.sort_values('time').reset_index(drop=True)
    
    from monte_carlo import block_bootstrap_prices
    
    results = []
    for i in range(n_sims):
        synth = block_bootstrap_prices(df, block_size=24)
        sim_csv = os.path.join(RESULTS_DIR, f'_tmp_val_{config_name}_{i}.csv')
        synth.to_csv(sim_csv, index=False)
        
        try:
            trades_df, signals_df, equity_df = forward_test(
                data_path=sim_csv,
                results_dir=RESULTS_DIR,
                initial_balance=10000.0,
                risk_per_trade=risk,
                commission_rate=0.0001 * slippage_mult,
                slippage_atr_frac=0.02 * slippage_mult,
                slippage_spread=0.00015 * slippage_mult,
                slippage_random_std=0.05 * slippage_mult,
                breakout_length=int(bl),
                atr_stop_multiplier=st,
                atr_tp_multiplier=tp,
                volatility_filter=True
            )
            
            if len(trades_df) == 0:
                pf, profit, max_dd, trades = 0, 0, 0, 0
            else:
                gross_profit = trades_df[trades_df['profit'] > 0]['profit'].sum()
                gross_loss = -trades_df[trades_df['profit'] < 0]['profit'].sum()
                pf = gross_profit / gross_loss if gross_loss > 0 else 0
                profit = equity_df['equity'].iloc[-1] - 10000 if len(equity_df) > 0 else 0
                max_dd = (equity_df['equity'].cummax() - equity_df['equity']).max() if len(equity_df) > 0 else 0
                trades = len(trades_df)
            
            results.append({'sim': i, 'pf': pf, 'profit': profit, 'max_dd': max_dd, 'trades': trades})
            if (i + 1) % 50 == 0:
                print(f"    Sim {i+1}/{n_sims}: PF={pf:.2f}, profit={profit:.0f}, maxDD={max_dd:.0f}")
        except Exception as e:
            print(f"    Error sim {i}: {e}")
        finally:
            if os.path.exists(sim_csv):
                os.remove(sim_csv)
    
    return pd.DataFrame(results)


def main():
    print("Monte Carlo Validation of Re-optimized Configs")
    print("="*70)
    
    # Load top 3 candidates
    candidates_path = os.path.join(RESULTS_DIR, 'reopt_top3_for_mc.csv')
    if not os.path.exists(candidates_path):
        print(f"Candidates file not found: {candidates_path}")
        print("Run reopt_fast.py first.")
        return
    
    candidates = pd.read_csv(candidates_path).head(3)
    
    # Also include baseline for comparison
    baseline = pd.DataFrame([{
        'bl': 30, 'st': 0.5, 'tp': 4.0, 'risk': 0.005
    }])
    candidates = pd.concat([baseline, candidates], ignore_index=True)
    candidates['name'] = ['BASELINE'] + [f"REOPT_{i}" for i in range(1, len(candidates))]
    
    all_results = []
    for idx, row in candidates.iterrows():
        bl, st, tp, risk = row['bl'], row['st'], row['tp'], row['risk']
        name = row['name']
        print(f"\n{name}: bl={int(bl)}, st={st:.1f}, tp={tp:.1f}, risk={risk:.3f}")
        print(f"  Running 150 sims...")
        
        mc_results = run_mc_on_config(150, bl, st, tp, risk, config_name=name)
        
        if len(mc_results) > 0:
            summary = {
                'config': name,
                'bl': int(bl), 'st': st, 'tp': tp, 'risk': risk,
                'n_sims': len(mc_results),
                'pf_mean': float(mc_results['pf'].mean()),
                'pf_median': float(mc_results['pf'].median()),
                'pf_std': float(mc_results['pf'].std()),
                'pf_gt1_pct': float((mc_results['pf'] > 1.0).mean() * 100),
                'profit_mean': float(mc_results['profit'].mean()),
                'profit_median': float(mc_results['profit'].median()),
                'profit_std': float(mc_results['profit'].std()),
                'maxdd_mean': float(mc_results['max_dd'].mean()),
                'maxdd_median': float(mc_results['max_dd'].median()),
            }
            all_results.append(summary)
            print(f"  Result: PF_mean={summary['pf_mean']:.3f}, "
                  f"PF>1: {summary['pf_gt1_pct']:.1f}%, "
                  f"profit_mean={summary['profit_mean']:.0f}, "
                  f"maxDD_mean={summary['maxdd_mean']:.0f}")
    
    # Compare
    print("\n" + "="*70)
    print("COMPARISON (150 sims each):")
    summary_df = pd.DataFrame(all_results)
    print(summary_df[['config', 'pf_mean', 'pf_gt1_pct', 'profit_mean', 'maxdd_mean']].to_string(index=False))
    
    # Save
    summary_df.to_csv(os.path.join(RESULTS_DIR, 'monte_carlo_validation.csv'), index=False)
    print(f"\nFull results saved to monte_carlo_validation.csv")


if __name__ == '__main__':
    main()
