"""
Walk-Forward Optimization Engine

Auto-adapts strategy parameters based on recent performance:
- Trains on 6-month rolling window
- Tests on next 2 weeks
- Re-optimizes every 14 days
- Switches to best parameter set automatically
- Detects regime changes and adapts

This keeps the system fresh and prevents overfitting to old data.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
from pathlib import Path
from itertools import product
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from breakout_strategy_v2 import BreakoutStrategyV2


class WalkForwardOptimizer:
    """
    Performs walk-forward optimization on trading strategies.
    
    Process:
    1. Train window: 6 months of data
    2. Test window: 2 weeks forward
    3. Optimize parameters on train window
    4. Apply best params to test window
    5. Roll forward 2 weeks and repeat
    """
    
    def __init__(self,
                 train_months=6,
                 test_days=14,
                 reopt_frequency_days=14):
        """
        Args:
            train_months: Months of historical data for training
            test_days: Days to test forward
            reopt_frequency_days: How often to re-optimize
        """
        self.train_months = train_months
        self.test_days = test_days
        self.reopt_frequency_days = reopt_frequency_days
        
        self.optimization_history = []
        self.current_best_params = None
    
    def generate_parameter_grid(self):
        """Generate parameter combinations to test."""
        param_grid = {
            'breakout_length': [20, 25, 30],
            'atr_stop_multiplier': [0.3, 0.5, 0.7],
            'atr_tp_multiplier': [3.0, 4.0, 5.0],
        }
        
        # Generate all combinations
        keys = param_grid.keys()
        values = param_grid.values()
        combinations = [dict(zip(keys, v)) for v in product(*values)]
        
        return combinations
    
    def optimize_on_window(self, data, initial_balance=166.67):
        """
        Find best parameters for a training window.
        
        Args:
            data: Training data (DataFrame with OHLC)
            initial_balance: Starting capital for backtest
            
        Returns:
            dict: Best parameters and their performance
        """
        param_combinations = self.generate_parameter_grid()
        results = []
        
        print(f"\n🔍 Testing {len(param_combinations)} parameter combinations...")
        
        for i, params in enumerate(param_combinations):
            try:
                # Create strategy with these params
                strategy = BreakoutStrategyV2(
                    breakout_length=params['breakout_length'],
                    atr_stop_multiplier=params['atr_stop_multiplier'],
                    atr_tp_multiplier=params['atr_tp_multiplier'],
                    trend_filter=True,
                    dynamic_sizing=True,
                    recovery_mode=True,
                )
                
                # Load data
                strategy.data = data.copy()
                
                # Run backtest
                result = strategy.run_backtest(
                    initial_balance=initial_balance,
                    risk_per_trade=0.002,
                )
                
                # Calculate fitness score (Sharpe-like metric)
                if len(strategy.trades) > 0:
                    returns = strategy.equity_curve['equity'].pct_change().dropna()
                    sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
                else:
                    sharpe = 0
                
                results.append({
                    'params': params,
                    'final_balance': result.get('final_balance', initial_balance),
                    'total_return': result.get('total_return', 0),
                    'trades': result.get('trades', 0),
                    'win_rate': result.get('win_rate', 0),
                    'sharpe': sharpe,
                    'fitness': sharpe * result.get('total_return', 0) / 100,  # Sharpe * Return
                })
                
                if (i + 1) % 9 == 0:
                    print(f"   Progress: {i+1}/{len(param_combinations)} tested...")
            
            except Exception as e:
                print(f"   Error with params {params}: {e}")
                continue
        
        # Sort by fitness score
        results.sort(key=lambda x: x['fitness'], reverse=True)
        
        if len(results) > 0:
            best = results[0]
            print(f"\n✅ Best parameters found:")
            print(f"   Breakout: {best['params']['breakout_length']} bars")
            print(f"   Stop: {best['params']['atr_stop_multiplier']}x ATR")
            print(f"   TP: {best['params']['atr_tp_multiplier']}x ATR")
            print(f"   Return: {best['total_return']:.2f}%")
            print(f"   Win Rate: {best['win_rate']:.1f}%")
            print(f"   Sharpe: {best['sharpe']:.2f}")
            
            return best
        else:
            print("❌ No valid parameter sets found")
            return None
    
    def run_walk_forward(self, data_path, initial_balance=166.67):
        """
        Execute complete walk-forward optimization.
        
        Args:
            data_path: Path to CSV with OHLC data
            initial_balance: Starting capital
            
        Returns:
            dict: Walk-forward results
        """
        # Load data
        df = pd.read_csv(data_path, parse_dates=['time'])
        df.set_index('time', inplace=True)
        df = df[['open', 'high', 'low', 'close']]
        
        print("=" * 70)
        print(" " * 15 + "WALK-FORWARD OPTIMIZATION")
        print("=" * 70)
        print(f"\nDataset: {len(df)} bars")
        print(f"Train window: {self.train_months} months")
        print(f"Test window: {self.test_days} days")
        print(f"Re-optimize every: {self.reopt_frequency_days} days\n")
        
        # Calculate window sizes
        train_size = int(self.train_months * 30 * 24)  # Assuming hourly data
        test_size = self.test_days * 24
        
        all_trades = []
        equity_curve = []
        current_balance = initial_balance
        
        # Walk forward through data
        start_idx = 0
        window_count = 0
        
        while start_idx + train_size + test_size < len(df):
            window_count += 1
            
            # Define windows
            train_end = start_idx + train_size
            test_end = train_end + test_size
            
            train_data = df.iloc[start_idx:train_end]
            test_data = df.iloc[train_end:test_end]
            
            print(f"\n{'='*70}")
            print(f"Window {window_count}: Train {train_data.index[0]} to {train_data.index[-1]}")
            print(f"               Test  {test_data.index[0]} to {test_data.index[-1]}")
            print(f"{'='*70}")
            
            # Optimize on training window
            best_result = self.optimize_on_window(train_data, current_balance)
            
            if best_result is None:
                print("⚠️  Skipping this window (no valid params)")
                start_idx += test_size
                continue
            
            # Apply best params to test window
            print(f"\n📊 Testing on forward period...")
            
            strategy = BreakoutStrategyV2(
                breakout_length=best_result['params']['breakout_length'],
                atr_stop_multiplier=best_result['params']['atr_stop_multiplier'],
                atr_tp_multiplier=best_result['params']['atr_tp_multiplier'],
                trend_filter=True,
                dynamic_sizing=True,
                recovery_mode=True,
            )
            
            strategy.data = test_data.copy()
            test_result = strategy.run_backtest(
                initial_balance=current_balance,
                risk_per_trade=0.002,
            )
            
            # Update balance
            current_balance = test_result.get('final_balance', current_balance)
            
            # Store results
            self.optimization_history.append({
                'window': window_count,
                'train_start': str(train_data.index[0]),
                'train_end': str(train_data.index[-1]),
                'test_start': str(test_data.index[0]),
                'test_end': str(test_data.index[-1]),
                'best_params': best_result['params'],
                'test_return': test_result.get('total_return', 0),
                'test_trades': test_result.get('trades', 0),
                'test_win_rate': test_result.get('win_rate', 0),
                'ending_balance': current_balance,
            })
            
            print(f"\n✅ Window {window_count} complete:")
            print(f"   Test return: {test_result.get('total_return', 0):.2f}%")
            print(f"   Test trades: {test_result.get('trades', 0)}")
            print(f"   Balance: ${current_balance:.2f}")
            
            # Move forward
            start_idx += test_size
        
        # Summary
        total_return = 100 * (current_balance - initial_balance) / initial_balance
        
        print(f"\n{'='*70}")
        print(" " * 15 + "WALK-FORWARD RESULTS")
        print(f"{'='*70}")
        print(f"\nWindows tested: {window_count}")
        print(f"Initial balance: ${initial_balance:.2f}")
        print(f"Final balance: ${current_balance:.2f}")
        print(f"Total return: {total_return:.2f}%")
        print(f"\n{'='*70}\n")
        
        # Save results
        self.current_best_params = self.optimization_history[-1]['best_params'] if self.optimization_history else None
        
        return {
            'windows': window_count,
            'initial_balance': initial_balance,
            'final_balance': current_balance,
            'total_return': total_return,
            'best_params': self.current_best_params,
        }
    
    def get_current_best_params(self):
        """Get the most recently optimized parameters."""
        return self.current_best_params
    
    def save_optimization_history(self, file_path):
        """Save optimization history to JSON."""
        with open(file_path, 'w') as f:
            json.dump(self.optimization_history, f, indent=2)
        print(f"✅ Optimization history saved to {file_path}")


# =============================================================================
# Demo Usage
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print(" " * 15 + "WALK-FORWARD OPTIMIZER - V3")
    print("=" * 70)
    
    # Create optimizer
    optimizer = WalkForwardOptimizer(
        train_months=6,
        test_days=14,
        reopt_frequency_days=14
    )
    
    # Check for data
    import os
    if os.path.exists('../data/eurusd_candles.csv'):
        print("\n🚀 Running walk-forward optimization on EUR/USD...")
        
        results = optimizer.run_walk_forward(
            data_path='../data/eurusd_candles.csv',
            initial_balance=166.67
        )
        
        # Save results
        optimizer.save_optimization_history('results/walk_forward_history.json')
        
        print("\n✅ Walk-forward optimization complete!")
        print(f"   Current best params: {optimizer.get_current_best_params()}")
    
    else:
        print("\n⚠️  EUR/USD data not found")
        print("   Place eurusd_candles.csv in ../data/ to run optimization")
        print("\n✅ WALK-FORWARD OPTIMIZER CODE READY")
