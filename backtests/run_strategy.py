from breakout_strategy import BreakoutStrategy

# Configure strategy parameters
strategy = BreakoutStrategy(
    breakout_length=50,
    atr_stop_multiplier=0.75,
    atr_tp_multiplier=3.0,
    volatility_filter=True
)

# Load price data (make sure your file path is correct)
strategy.load_data("../data/v75_candles.csv")

# Run backtest and save results
strategy.run_backtest(
    save_csv=True,
    results_path="../results/v75_breakout_trades.csv"
)

# Plot and save equity curve
strategy.plot_equity_curve(save_path="../results/v75_equity_curve.png")
