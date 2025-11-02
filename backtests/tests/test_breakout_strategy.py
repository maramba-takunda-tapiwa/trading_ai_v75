import pandas as pd
import numpy as np
import os
import tempfile

from breakout_strategy import BreakoutStrategy


def make_sample_df(n=100):
    # create a simple trending synthetic OHLC dataset
    rng = pd.date_range('2025-01-01', periods=n, freq='T')
    price = 1000 + np.cumsum(np.random.randn(n))
    df = pd.DataFrame({
        'time': rng,
        'open': price,
        'high': price + np.random.rand(n) * 2,
        'low': price - np.random.rand(n) * 2,
        'close': price + np.random.randn(n) * 0.5,
    })
    return df


def test_compute_signals_adds_columns():
    df = make_sample_df(200)
    # write to a temp CSV and load via the class to mimic normal flow
    td = tempfile.mkdtemp()
    path = os.path.join(td, 'sample.csv')
    df.to_csv(path, index=False)

    s = BreakoutStrategy(breakout_length=10, atr_stop_multiplier=0.5, atr_tp_multiplier=2.0, volatility_filter=True)
    s.load_data(path)
    s.compute_signals()
    assert 'ATR' in s.data.columns
    assert 'prev_high' in s.data.columns
    assert 'prev_low' in s.data.columns
    assert 'long_signal' in s.data.columns
    assert 'short_signal' in s.data.columns


def test_run_backtest_returns_dataframe():
    df = make_sample_df(500)
    td = tempfile.mkdtemp()
    path = os.path.join(td, 'sample2.csv')
    df.to_csv(path, index=False)

    s = BreakoutStrategy(breakout_length=20, atr_stop_multiplier=0.5, atr_tp_multiplier=2.0, volatility_filter=False)
    s.load_data(path)
    # ensure compute_signals is callable and then run_backtest
    s.compute_signals()
    trades = s.run_backtest(save_csv=False)
    # trades should be a DataFrame (possibly empty) with columns including entry_time
    assert hasattr(trades, 'shape')
    # if not empty, expect R column
    if not trades.empty:
        assert 'R' in trades.columns
