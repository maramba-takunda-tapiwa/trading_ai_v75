"""
Comparative backtest: Original vs V2 (with drawdown reduction).
Tests on the same data to show improvement metrics.
"""

import pandas as pd
import numpy as np
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from breakout_strategy import BreakoutStrategy
from breakout_strategy_v2 import BreakoutStrategyV2

DATA_PATH = '../data/eurusd_candles.csv'
RESULTS_DIR = '../results/'

os.makedirs(RESULTS_DIR, exist_ok=True)

def run_comparison():
    """Run both strategies on same data and compare."""
    
    print("=" * 80)
    print("STRATEGY COMPARISON: Original vs V2 (Drawdown-Optimized)")
    print("=" * 80)
    print()
    
    # --- Strategy 1: Original (baseline) ---
    print("1. ORIGINAL STRATEGY")
    print("-" * 80)
    
    strat1 = BreakoutStrategy(
        breakout_length=35,
        atr_stop_multiplier=0.3,
        atr_tp_multiplier=4.0,
        volatility_filter=True
    )
    strat1.load_data(DATA_PATH)
    trades1 = strat1.run_backtest(save_csv=True, results_path=os.path.join(RESULTS_DIR, 'comparison_original.csv'))
    
    print()
    
    # --- Strategy 2: V2 with all improvements ---
    print("2. V2 IMPROVED STRATEGY (Trend Filter + Dynamic Sizing + Recovery Mode)")
    print("-" * 80)
    
    strat2 = BreakoutStrategyV2(
        breakout_length=25,  # tighter
        atr_stop_multiplier=0.3,
        atr_tp_multiplier=4.0,
        volatility_filter=True,
        trend_filter=True,  # 200-bar MA
        dynamic_sizing=True,  # adaptive position sizing
        recovery_mode=True,  # loss recovery
        equity_stop_pct=0.15  # soft equity stop
    )
    strat2.load_data(DATA_PATH)
    trades2 = strat2.run_backtest(initial_balance=10000.0, risk_per_trade=0.002)
    
    print()
    
    # --- Comparison ---
    print("=" * 80)
    print("SUMMARY COMPARISON")
    print("=" * 80)
    print()
    
    def compute_metrics(trades_df, equity_curve):
        if len(trades_df) == 0:
            return {
                'trades': 0, 'wins': 0, 'losses': 0, 'win_rate': 0,
                'total_r': 0, 'expectancy': 0, 'pf': 0,
                'gross_profit': 0, 'gross_loss': 0,
                'max_dd_r': 0, 'max_dd_usd': 0
            }
        
        wins = trades_df[trades_df['R'] > 0]
        losses = trades_df[trades_df['R'] < 0]
        
        total_r = trades_df['R'].sum()
        win_rate = (len(wins) / len(trades_df) * 100) if len(trades_df) > 0 else 0
        expectancy = total_r / len(trades_df) if len(trades_df) > 0 else 0
        
        gross_profit = wins['R'].sum() if len(wins) > 0 else 0
        gross_loss = -losses['R'].sum() if len(losses) > 0 else 0
        pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Drawdown in R and USD
        if len(equity_curve) > 0:
            drawdown_r = np.maximum.accumulate(trades_df['R'].cumsum().values) - trades_df['R'].cumsum().values
            max_dd_r = drawdown_r.max() if len(drawdown_r) > 0 else 0
            
            drawdown_usd = np.maximum.accumulate(equity_curve) - equity_curve
            max_dd_usd = drawdown_usd.max() if len(drawdown_usd) > 0 else 0
        else:
            max_dd_r = 0
            max_dd_usd = 0
        
        return {
            'trades': len(trades_df),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': win_rate,
            'total_r': total_r,
            'expectancy': expectancy,
            'pf': pf,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'max_dd_r': max_dd_r,
            'max_dd_usd': max_dd_usd
        }
    
    m1 = compute_metrics(trades1, strat1.equity_curve if strat1.equity_curve is not None else np.array([]))
    m2 = compute_metrics(trades2, strat2.equity_curve)
    
    print(f"{'Metric':<30} {'Original':<20} {'V2 Improved':<20} {'Change':<15}")
    print("-" * 85)
    
    metrics_to_show = [
        ('Trades', m1['trades'], m2['trades']),
        ('Win Rate (%)', f"{m1['win_rate']:.1f}", f"{m2['win_rate']:.1f}"),
        ('Profit Factor', f"{m1['pf']:.2f}", f"{m2['pf']:.2f}"),
        ('Total R', f"{m1['total_r']:.2f}", f"{m2['total_r']:.2f}"),
        ('Expectancy (R)', f"{m1['expectancy']:.2f}", f"{m2['expectancy']:.2f}"),
        ('Max DD (R)', f"{m1['max_dd_r']:.2f}", f"{m2['max_dd_r']:.2f}"),
        ('Max DD ($)', f"{m1['max_dd_usd']:.2f}", f"{m2['max_dd_usd']:.2f}"),
    ]
    
    for metric, v1, v2 in metrics_to_show:
        try:
            if isinstance(v1, str) or isinstance(v2, str):
                v1_f = float(str(v1).strip('%'))
                v2_f = float(str(v2).strip('%'))
            else:
                v1_f = float(v1)
                v2_f = float(v2)
            
            if v1_f != 0:
                pct_change = ((v2_f - v1_f) / abs(v1_f)) * 100
                change_str = f"{pct_change:+.1f}%"
            else:
                change_str = "N/A"
        except:
            change_str = "N/A"
        
        print(f"{metric:<30} {str(v1):<20} {str(v2):<20} {change_str:<15}")
    
    print()
    print("=" * 80)
    print("KEY IMPROVEMENTS IN V2:")
    print("=" * 80)
    print()
    print("1. TREND FILTER (200-bar MA)")
    print("   - Eliminates counter-trend whipsaw trades")
    print("   - Only goes long above MA, short below MA")
    print("   - Expected: +10-15pp win rate, fewer trades")
    print()
    print("2. DYNAMIC POSITION SIZING")
    print("   - Reduces size 20-50% after losses")
    print("   - Recovery mode: stay small for 5 trades after 2+ losses")
    print("   - Expected: -30-50% max drawdown")
    print()
    print("3. EQUITY-BASED SOFT STOP")
    print("   - Freezes trading at 15% drawdown below peak")
    print("   - Allows recovery before hard stop at $5,414")
    print("   - Expected: catches drawdown spirals early")
    print()
    print("4. TIGHTER BREAKOUT THRESHOLD (25 bars vs 35)")
    print("   - More selective entries, higher quality trades")
    print("   - Combined with trend filter = fewer but better trades")
    print()
    print("=" * 80)
    print()
    
    return trades1, trades2

if __name__ == '__main__':
    trades1, trades2 = run_comparison()
    print("[OK] Comparison complete. Check results/ for CSV files.")
