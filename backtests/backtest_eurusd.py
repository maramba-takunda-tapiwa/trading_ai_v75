import yfinance as yf
import pandas as pd
from forward_test import forward_test

# Fetch EUR/USD historical data (1-hour bars for last 2 years)
ticker = yf.Ticker("EURUSD=X")
df = ticker.history(period="2y", interval="1h")
df.reset_index(inplace=True)
df = df.rename(columns={
    'Datetime': 'time',
    'Open': 'open',
    'High': 'high',
    'Low': 'low',
    'Close': 'close',
    'Volume': 'volume'
})
df['time'] = pd.to_datetime(df['time'])
df = df[['time', 'open', 'high', 'low', 'close', 'volume']]

# Save to CSV
df.to_csv('data/eurusd_candles.csv', index=False)
print(f"Fetched {len(df)} EUR/USD candles. Saved to data/eurusd_candles.csv")

# Run backtest with optimized config
trades_df, signals_df, equity_df = forward_test(
    data_path='data/eurusd_candles.csv',
    results_dir='results',
    initial_balance=10000.0,
    risk_per_trade=0.02,
    commission_rate=0.0001,
    slippage_atr_frac=0.02,
    breakout_length=50,
    atr_stop_multiplier=0.5,
    atr_tp_multiplier=2.0,
    volatility_filter=True,
)

# Calculate metrics
trades_df['profit'] = pd.to_numeric(trades_df['profit'], errors='coerce')
total_profit = float(trades_df['profit'].sum())
wins = trades_df[trades_df['profit'] > 0]
losses = trades_df[trades_df['profit'] < 0]
pf = (wins['profit'].sum() / -losses['profit'].sum()) if len(losses) > 0 else float('inf')
expectancy = float(trades_df['profit'].mean())
max_dd = float(equity_df['equity'].min() - 10000)  # Approximate

print(f"EUR/USD Backtest Results:")
print(f"Trades: {len(trades_df)}")
print(f"Total Profit: {total_profit:.2f}")
print(f"Profit Factor: {pf:.3f}")
print(f"Expectancy: {expectancy:.2f}")
print(f"Max Drawdown: {max_dd:.2f}")
print(f"Profit/DD Ratio: {total_profit / abs(max_dd):.2f}")