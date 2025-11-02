"""
Sensitivity sweep: Monte Carlo with varying block-size and slippage multipliers.
Compares how PF distribution changes under different resampling and fill-cost assumptions.

Usage:
    python sensitivity_sweep.py [--sims 500] [--quick]

Results saved to ../results/sensitivity_sweep_results.csv
"""

import argparse
import sys
import os
import subprocess
import pandas as pd
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sims', type=int, default=500, help='Sims per configuration')
    parser.add_argument('--quick', action='store_true', help='Quick mode: 200 sims, fewer configs')
    args = parser.parse_args()
    
    num_sims = 200 if args.quick else args.sims
    
    # configurations: (block_size, slip_mult)
    if args.quick:
        configs = [
            (24, 0.5),
            (24, 1.0),
            (24, 1.5),
        ]
    else:
        configs = [
            (24, 0.5),
            (24, 1.0),
            (24, 1.5),
            (168, 0.5),
            (168, 1.0),
            (168, 1.5),
            (720, 1.0),
        ]
    
    results = []
    root = Path(__file__).parent.parent
    results_dir = root / 'results'
    
    print(f"Starting sensitivity sweep: {len(configs)} configs x {num_sims} sims")
    print("="*70)
    
    for i, (block_size, slip_mult) in enumerate(configs, 1):
        print(f"\n[{i}/{len(configs)}] block_size={block_size}, slip_mult={slip_mult}")
        print(f"  Running {num_sims} sims...")
        
        # run monte_carlo.py with environment variable override
        env = os.environ.copy()
        env['MC_SLIPPAGE_MULT'] = str(slip_mult)
        
        cmd = [
            sys.executable,
            'monte_carlo.py',
            '--sims', str(num_sims),
            '--block-size', str(block_size),
        ]
        
        try:
            result = subprocess.run(cmd, cwd=str(Path(__file__).parent), 
                                   capture_output=True, text=True, timeout=3600, env=env)
            if result.returncode != 0:
                print(f"  ERROR: {result.stderr}")
                continue
        except subprocess.TimeoutExpired:
            print(f"  TIMEOUT after 1 hour")
            continue
        
        # read aggregated results
        mc_csv = results_dir / 'monte_carlo_results_block.csv'
        if mc_csv.exists():
            df = pd.read_csv(mc_csv)
            summary = {
                'block_size': block_size,
                'slip_mult': slip_mult,
                'n_sims': len(df),
                'pf_mean': float(df['pf'].mean()),
                'pf_median': float(df['pf'].median()),
                'pf_std': float(df['pf'].std()),
                'pf_gt_1_pct': float((df['pf'] > 1.0).mean() * 100),
                'profit_mean': float(df['profit'].mean()),
                'profit_median': float(df['profit'].median()),
                'profit_std': float(df['profit'].std()),
                'maxdd_mean': float(df['max_dd'].mean()),
                'maxdd_median': float(df['max_dd'].median()),
            }
            results.append(summary)
            print(f"  -> PF: {summary['pf_mean']:.3f} (±{summary['pf_std']:.3f}), "
                  f"{summary['pf_gt_1_pct']:.1f}% PF>1, "
                  f"profit: {summary['profit_mean']:.0f} (±{summary['profit_std']:.0f})")
        else:
            print(f"  WARNING: No results CSV found")
    
    # write summary
    if results:
        summary_df = pd.DataFrame(results)
        out_path = results_dir / 'sensitivity_sweep_results.csv'
        summary_df.to_csv(out_path, index=False)
        print(f"\n{'='*70}")
        print(f"Sensitivity sweep complete. Results saved to {out_path}")
        print(summary_df.to_string(index=False))
    else:
        print("No results collected.")

if __name__ == '__main__':
    main()
