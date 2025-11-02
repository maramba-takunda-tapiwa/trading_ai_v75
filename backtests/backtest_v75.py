# backtest_v75.py
import math
import pandas as pd
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "v75_candles.csv"

# ---------------------------
# 1) Load & prep data
# ---------------------------
df = pd.read_csv(DATA_PATH, parse_dates=["time"])
df = df.sort_values("time").reset_index(drop=True)

# Ensure numeric
for col in ["open", "high", "low", "close"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# True Range & ATR(14) (simple moving average of TR)
df["prev_close"] = df["close"].shift(1)
tr1 = df["high"] - df["low"]
tr2 = (df["high"] - df["prev_close"]).abs()
tr3 = (df["low"] - df["prev_close"]).abs()
df["tr"] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
df["atr14"] = df["tr"].rolling(14).mean()

# Rolling 20-bar range (use *previous* 20 bars)
df["range_high_20"] = df["high"].shift(1).rolling(20).max()
df["range_low_20"]  = df["low"].shift(1).rolling(20).min()

# Drop warmup bars
df = df.dropna(subset=["atr14", "range_high_20", "range_low_20"]).reset_index(drop=True)

# ---------------------------
# 2) Backtest loop (single position engine)
# ---------------------------
trades = []  # each trade: dict with entry_time, dir, entry, sl, tp, exit_time, exit, r_mult
in_position = False
pos_dir = None          # "long" or "short"
entry_idx = None
entry_price = None
sl = None
tp = None
risk_per_trade = 1.0    # measured in "R" units; PnL will be in R

def record_trade(exit_idx, exit_price, outcome_label):
    global in_position, pos_dir, entry_idx, entry_price, sl, tp
    # R-multiple
    if pos_dir == "long":
        r = (exit_price - entry_price) / (abs(entry_price - sl) if entry_price != sl else 1e-9)
    else:  # short
        r = (entry_price - exit_price) / (abs(sl - entry_price) if entry_price != sl else 1e-9)

    trades.append({
        "entry_time": df.loc[entry_idx, "time"],
        "direction": pos_dir,
        "entry": entry_price,
        "sl": sl,
        "tp": tp,
        "exit_time": df.loc[exit_idx, "time"],
        "exit": exit_price,
        "r_mult": r,
        "outcome": outcome_label,
    })

    # reset state
    in_position = False
    pos_dir = None
    entry_idx = None
    entry_price = None
    sl = None
    tp = None

for i in range(len(df)):
    row = df.loc[i]

    if not in_position:
        # Entry logic: breakout of prior 20-bar range on CLOSE
        if row["close"] > row["range_high_20"]:
            # go long
            in_position = True
            pos_dir = "long"
            entry_idx = i
            entry_price = row["close"]
            sl = entry_price - 0.75 * row["atr14"]
            tp = entry_price + 1.5 * row["atr14"]
        elif row["close"] < row["range_low_20"]:
            # go short
            in_position = True
            pos_dir = "short"
            entry_idx = i
            entry_price = row["close"]
            sl = entry_price + 0.75 * row["atr14"]
            tp = entry_price - 1.5 * row["atr14"]
    else:
        # Manage the open position using the current bar's high/low
        high_i, low_i, close_i = row["high"], row["low"], row["close"]

        if pos_dir == "long":
            hit_sl = low_i <= sl
            hit_tp = high_i >= tp
            # Conservative: if both hit in same candle, count it as SL first
            if hit_sl:
                record_trade(i, sl, "SL")
            elif hit_tp:
                record_trade(i, tp, "TP")
            # Optional exit after N bars could be added here
        else:  # short
            hit_tp = low_i <= tp
            hit_sl = high_i >= sl
            # Conservative: SL first if both touched
            if hit_sl:
                record_trade(i, sl, "SL")
            elif hit_tp:
                record_trade(i, tp, "TP")

# If still in a trade at the end, close at last close
if in_position:
    record_trade(len(df) - 1, df.loc[len(df) - 1, "close"], "EOD")

# ---------------------------
# 3) Performance metrics
# ---------------------------
if len(trades) == 0:
    print("No trades generated. Try different params or a longer dataset.")
    raise SystemExit()

trades_df = pd.DataFrame(trades)

wins = (trades_df["r_mult"] > 0).sum()
losses = (trades_df["r_mult"] <= 0).sum()
win_rate = wins / len(trades_df) if len(trades_df) else 0.0
gross_profit = trades_df.loc[trades_df["r_mult"] > 0, "r_mult"].sum()
gross_loss = -trades_df.loc[trades_df["r_mult"] <= 0, "r_mult"].sum()
profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else math.inf
expectancy = trades_df["r_mult"].mean()

# Equity curve in R
equity = trades_df["r_mult"].cumsum()
peak = equity.cummax()
drawdown = equity - peak
max_dd = drawdown.min()  # negative number, in R
max_dd_abs = abs(max_dd)

print("\n========== Backtest Summary ==========")
print(f"Data file: {DATA_PATH.name}")
print(f"Bars tested: {len(df)}   Trades: {len(trades_df)}")
print(f"Win rate: {win_rate:.2%}  |  Profit factor: {profit_factor:.2f}")
print(f"Expectancy (R/trade): {expectancy:.3f}")
print(f"Max drawdown: {max_dd_abs:.2f} R")
print(f"Total R: {equity.iloc[-1]:.2f} R")
print("======================================\n")

print(trades_df.head(10).to_string(index=False))
trades_df.to_csv('../data/v75_trades.csv', index=False)




