import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

TRADES_PATH = Path(__file__).resolve().parents[1] / "backtests" / "backtest_v75.py"

# Instead of re-running the backtest, import the trades dataframe:
# We'll just copy the final lines from your script into a CSV
# So add this at the end of backtest_v75.py before printing summary:
# trades_df.to_csv('../data/v75_trades.csv', index=False)

# Then run this plotting script
TRADES_FILE = Path(__file__).resolve().parents[1] / "data" / "v75_trades.csv"
df = pd.read_csv(TRADES_FILE, parse_dates=["entry_time", "exit_time"])

# Compute equity curve
df["equity"] = df["r_mult"].cumsum()
df["peak"] = df["equity"].cummax()
df["drawdown"] = df["equity"] - df["peak"]

plt.figure(figsize=(12,6))
plt.subplot(2,1,1)
plt.plot(df["exit_time"], df["equity"], label="Equity (R)", linewidth=1.6)
plt.title("Equity Curve – V75 Breakout Strategy")
plt.ylabel("Cumulative R")
plt.grid(True)
plt.legend()

plt.subplot(2,1,2)
plt.plot(df["exit_time"], df["drawdown"], color="red", label="Drawdown", linewidth=1.2)
plt.fill_between(df["exit_time"], df["drawdown"], 0, color="red", alpha=0.2)
plt.ylabel("Drawdown (R)")
plt.xlabel("Time")
plt.legend()
plt.tight_layout()
plt.show()
