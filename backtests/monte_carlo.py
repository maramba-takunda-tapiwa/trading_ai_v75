"""
Monte Carlo robustness test using block bootstrap on returns.
- Reads historical OHLC data
- Creates synthetic price series by block-bootstrapping returns
- Reconstructs OHLC (open/high/low/close) simplistically from returns
- Runs `forward_test` on each synthetic series and aggregates metrics

Run: py monte_carlo.py [--sims N] [--block-size B]
Environment: MC_SLIPPAGE_MULT (default 1.0) to scale slippage/commission
"""
import argparse
import pandas as pd
import numpy as np
import os
from forward_test import forward_test

DATA_PATH = '../data/eurusd_candles.csv'
RESULTS_DIR = '../results/'
N_SIMS = 200
BLOCK_SIZE = 24  # blocks of 24 bars (~1 day for hourly data)
SLIPPAGE_MULT = float(os.environ.get('MC_SLIPPAGE_MULT', '1.0'))  # multiplier for slippage/commission

os.makedirs(RESULTS_DIR, exist_ok=True)


def block_bootstrap_prices(df, block_size=24):
    # Use log returns on close
    closes = df['close'].values
    logret = np.log(closes[1:] / closes[:-1])
    n = len(logret)
    # indices of possible block starts
    starts = np.arange(0, n - block_size + 1)
    # number of blocks needed
    blocks_needed = int(np.ceil(n / block_size))
    sampled = []
    for _ in range(blocks_needed):
        s = np.random.choice(starts)
        sampled.append(logret[s:s + block_size])
    sampled = np.concatenate(sampled)[:n]
    # rebuild closes from initial price
    new_closes = [closes[0]]
    for r in sampled:
        new_closes.append(new_closes[-1] * np.exp(r))
    new_closes = np.array(new_closes)
    # Build OHLC: set open = prev close, close as computed, high/low add small noise
    opens = new_closes[:-1]
    closes = new_closes[1:]
    highs = np.maximum(opens, closes) * (1 + np.abs(np.random.normal(0, 0.0005, size=len(closes))))
    lows = np.minimum(opens, closes) * (1 - np.abs(np.random.normal(0, 0.0005, size=len(closes))))
    # ensure timezone-safe parsing
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


def run_mc(n_sims=N_SIMS, block_size=BLOCK_SIZE):
    if not os.path.exists(DATA_PATH):
        print('Data not found:', DATA_PATH)
        return
    df = pd.read_csv(DATA_PATH)
    df = df.sort_values('time').reset_index(drop=True)

    mc_results = []
    for i in range(n_sims):
        synth = block_bootstrap_prices(df, block_size=block_size)
        sim_csv = os.path.join(RESULTS_DIR, f'tmp_mc_{i}.csv')
        synth.to_csv(sim_csv, index=False)
        trades_df, signals_df, equity_df = forward_test(
            data_path=sim_csv,
            results_dir=RESULTS_DIR,
            initial_balance=10000.0,
            risk_per_trade=0.005,
            commission_rate=0.0001 * SLIPPAGE_MULT,
            slippage_atr_frac=0.02 * SLIPPAGE_MULT,
            slippage_spread=0.00015 * SLIPPAGE_MULT,
            slippage_random_std=0.05 * SLIPPAGE_MULT,
            breakout_length=30,
            atr_stop_multiplier=0.5,
            atr_tp_multiplier=4.0,
            volatility_filter=True
        )
        # compute PF and metrics
        if len(trades_df) == 0:
            pf = 0
            profit = 0
            max_dd = 0
            trades = 0
        else:
            gross_profit = trades_df[trades_df['profit'] > 0]['profit'].sum()
            gross_loss = -trades_df[trades_df['profit'] < 0]['profit'].sum()
            pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            profit = equity_df['equity'].iloc[-1] - 10000 if len(equity_df) > 0 else 0
            max_dd = (equity_df['equity'].cummax() - equity_df['equity']).max() if len(equity_df) > 0 else 0
            trades = len(trades_df)
        mc_results.append({'sim': i, 'pf': pf, 'profit': profit, 'max_dd': max_dd, 'trades': trades})
        print(f"Sim {i+1}/{n_sims}: PF={pf:.2f}, Profit={profit:.2f}, MaxDD={max_dd:.2f}, Trades={trades}")

    mc_df = pd.DataFrame(mc_results)
    mc_df.to_csv(os.path.join(RESULTS_DIR, 'monte_carlo_results_block.csv'), index=False)
    print('Monte Carlo complete. Results saved to', os.path.join(RESULTS_DIR, 'monte_carlo_results_block.csv'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Monte Carlo block-bootstrap runner')
    parser.add_argument('--sims', type=int, default=N_SIMS, help='Number of Monte Carlo simulations')
    parser.add_argument('--block-size', type=int, default=BLOCK_SIZE, help='Block size in bars for bootstrap')
    args = parser.parse_args()
    run_mc(n_sims=args.sims, block_size=args.block_size)
