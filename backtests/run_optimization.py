"""
Run a full parameter grid optimization with walk-forward analysis for robustness.

Saves:
- results/optimization_results.csv (average scores across folds)
- results/validation_results.csv (best config evaluated on final OOS)
- results/best_config_trades.csv (trades from OOS run for the best config)

This script is intended to be run from the repository root with:
    py backtests\run_optimization.py

"""
import os
import time
import itertools
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit
from forward_test import forward_test


def run_grid_on_fold(df_train, df_test, grid, commission_rate=0.0001):
    """Run grid search on train, evaluate all configs on test."""
    train_csv = os.path.join(results_dir, 'tmp_train.csv')
    test_csv = os.path.join(results_dir, 'tmp_test.csv')
    df_train.to_csv(train_csv, index=False)
    df_test.to_csv(test_csv, index=False)
    
    out = []
    total = 1
    for vals in grid.values():
        total *= len(vals)
    print(f"Evaluating {total} configs on fold")
    for bl, stop_mul, tp_mul, risk, slip in itertools.product(
        grid['breakout_length'], grid['stop_mul'], grid['tp_mul'], grid['risk'], grid['slippage']
    ):
        # Train score
        trades_df, signals_df, equity_df = forward_test(
            data_path=train_csv,
            results_dir=results_dir,
            initial_balance=10000.0,
            risk_per_trade=risk,
            commission_rate=commission_rate,
            slippage_atr_frac=slip,
            breakout_length=bl,
            atr_stop_multiplier=stop_mul,
            atr_tp_multiplier=tp_mul,
            volatility_filter=True,
        )
        trades_df['profit'] = pd.to_numeric(trades_df['profit'], errors='coerce')
        wins = trades_df[trades_df['profit'] > 0]
        losses = trades_df[trades_df['profit'] < 0]
        train_pf = (wins['profit'].sum() / -losses['profit'].sum()) if len(losses) > 0 else float('inf')
        
        # Test score
        trades_df, signals_df, equity_df = forward_test(
            data_path=test_csv,
            results_dir=results_dir,
            initial_balance=10000.0,
            risk_per_trade=risk,
            commission_rate=commission_rate,
            slippage_atr_frac=slip,
            breakout_length=bl,
            atr_stop_multiplier=stop_mul,
            atr_tp_multiplier=tp_mul,
            volatility_filter=True,
        )
        trades_df['profit'] = pd.to_numeric(trades_df['profit'], errors='coerce')
        wins = trades_df[trades_df['profit'] > 0]
        losses = trades_df[trades_df['profit'] < 0]
        test_pf = (wins['profit'].sum() / -losses['profit'].sum()) if len(losses) > 0 else float('inf')
        
        out.append({
            'breakout_length': bl,
            'stop_mul': stop_mul,
            'tp_mul': tp_mul,
            'risk': risk,
            'slippage': slip,
            'train_pf': float(train_pf),
            'test_pf': float(test_pf),
        })
    return pd.DataFrame(out)


def simple_walk_forward_validate(full_csv, best_cfg, results_dir):
    # Removed, replaced with walk-forward
    pass


if __name__ == '__main__':
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    data_path = os.path.join(repo_root, 'data', 'eurusd_candles.csv')
    results_dir = os.path.join(repo_root, 'results')
    os.makedirs(results_dir, exist_ok=True)

    grid = {
        'breakout_length': [20, 30, 50, 70],
        'stop_mul': [0.5, 0.75, 1.0],
        'tp_mul': [2.0, 3.0, 4.0],
        'risk': [0.005, 0.01, 0.02],
        'slippage': [0.0, 0.02, 0.05],
    }

    # Load full data
    df = pd.read_csv(data_path, parse_dates=['time'])
    
    # Walk-forward with 3 folds
    tscv = TimeSeriesSplit(n_splits=3)
    fold_results = []
    for fold, (train_index, test_index) in enumerate(tscv.split(df)):
        print(f"Running fold {fold+1}")
        df_train = df.iloc[train_index]
        df_test = df.iloc[test_index]
        fold_df = run_grid_on_fold(df_train, df_test, grid)
        fold_df['fold'] = fold
        fold_results.append(fold_df)
    
    all_results = pd.concat(fold_results)
    # Average test_pf per config
    avg_results = all_results.groupby(['breakout_length', 'stop_mul', 'tp_mul', 'risk', 'slippage']).agg(
        avg_test_pf=('test_pf', 'mean'),
        avg_train_pf=('train_pf', 'mean')
    ).reset_index()
    avg_results['score'] = avg_results['avg_test_pf']
    
    opt_csv = os.path.join(results_dir, 'optimization_results.csv')
    avg_results.to_csv(opt_csv, index=False)
    print(f"Saved walk-forward optimization results to {opt_csv}")

    # Pick best by avg_test_pf
    best = avg_results.sort_values('avg_test_pf', ascending=False).iloc[0]
    print('Best config (walk-forward):', best.to_dict())

    # Final validation on last 20% of data
    n = len(df)
    test_start = int(n * 0.8)
    df_final_test = df.iloc[test_start:]
    test_csv = os.path.join(results_dir, 'tmp_test.csv')
    df_final_test.to_csv(test_csv, index=False)
    trades_df, signals_df, equity_df = forward_test(
        data_path=test_csv,
        results_dir=results_dir,
        initial_balance=10000.0,
        risk_per_trade=best['risk'],
        commission_rate=0.0001,
        slippage_atr_frac=best['slippage'],
        breakout_length=int(best['breakout_length']),
        atr_stop_multiplier=float(best['stop_mul']),
        atr_tp_multiplier=float(best['tp_mul']),
        volatility_filter=True,
    )
    trades_df['profit'] = pd.to_numeric(trades_df['profit'], errors='coerce')
    total_profit = float(trades_df['profit'].sum()) if not trades_df.empty else 0.0
    wins = trades_df[trades_df['profit'] > 0]
    losses = trades_df[trades_df['profit'] < 0]
    final_pf = (wins['profit'].sum() / -losses['profit'].sum()) if len(losses) > 0 else float('inf')
    try:
        equity_df['equity'] = pd.to_numeric(equity_df['equity'], errors='coerce').ffill().fillna(0.0)
        equity_df['cummax'] = equity_df['equity'].cummax()
        equity_df['dd'] = equity_df['cummax'] - equity_df['equity']
        max_dd = float(equity_df['dd'].max())
    except Exception:
        max_dd = None

    validation = {**best.to_dict(), 'final_oos_pf': final_pf, 'final_total_profit': total_profit, 'final_max_dd': max_dd}
    val_csv = os.path.join(results_dir, 'validation_results.csv')
    pd.DataFrame([validation]).to_csv(val_csv, index=False)
    trades_out = os.path.join(results_dir, 'best_config_trades.csv')
    trades_df.to_csv(trades_out, index=False)
    print('Saved final validation to', val_csv)
    print('Saved best config trades to', trades_out)
