# optimize_v75.py
import pandas as pd
import itertools
from pathlib import Path
import math

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "v75_candles.csv"

# -------------------------------------------------------------------
# 1) Load & prep the candle data
# -------------------------------------------------------------------
df_master = pd.read_csv(DATA_PATH, parse_dates=["time"])
df_master = df_master.sort_values("time").reset_index(drop=True)

for col in ["open", "high", "low", "close"]:
    df_master[col] = pd.to_numeric(df_master[col], errors="coerce")

# -------------------------------------------------------------------
# 2) Helper function: backtest with given parameters
# -------------------------------------------------------------------
def backtest(breakout_len=20, atr_sl_mult=0.75, atr_tp_mult=1.5):
    df = df_master.copy()
    df["prev_close"] = df["close"].shift(1)
    tr1 = df["high"] - df["low"]
    tr2 = (df["high"] - df["prev_close"]).abs()
    tr3 = (df["low"] - df["prev_close"]).abs()
    df["tr"] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df["atr14"] = df["tr"].rolling(14).mean()
    df["range_high"] = df["high"].shift(1).rolling(breakout_len).max()
    df["range_low"]  = df["low"].shift(1).rolling(breakout_len).min()
    df = df.dropna().reset_index(drop=True)

    trades = []
    in_pos, dirn, entry, sl, tp = False, None, None, None, None

    def close_trade(i, price, label):
        nonlocal in_pos, dirn, entry, sl, tp
        r = (price - entry) / abs(entry - sl) if dirn == "long" else (entry - price) / abs(sl - entry)
        trades.append(r)
        in_pos = False

    for i, row in df.iterrows():
        if not in_pos:
            if row["close"] > row["range_high"]:
                in_pos = True; dirn="long"
                entry=row["close"]; sl=entry-atr_sl_mult*row["atr14"]; tp=entry+atr_tp_mult*row["atr14"]
            elif row["close"] < row["range_low"]:
                in_pos = True; dirn="short"
                entry=row["close"]; sl=entry+atr_sl_mult*row["atr14"]; tp=entry-atr_tp_mult*row["atr14"]
        else:
            hi, lo = row["high"], row["low"]
            hit_sl = lo<=sl if dirn=="long" else hi>=sl
            hit_tp = hi>=tp if dirn=="long" else lo<=tp
            if hit_sl: close_trade(i, sl, "SL")
            elif hit_tp: close_trade(i, tp, "TP")
    if in_pos:  # close final
        close_trade(len(df)-1, df.iloc[-1]["close"], "EOD")

    if len(trades)==0: return (breakout_len, atr_sl_mult, atr_tp_mult, 0,0,0,0)
    trades = pd.Series(trades)
    wins = (trades>0).sum()
    losses = (trades<=0).sum()
    win_rate = wins/len(trades)
    gross_profit = trades[trades>0].sum()
    gross_loss = -trades[trades<=0].sum()
    profit_factor = (gross_profit/gross_loss) if gross_loss>0 else math.inf
    expectancy = trades.mean()
    total_r = trades.sum()
    return (breakout_len, atr_sl_mult, atr_tp_mult, win_rate, profit_factor, expectancy, total_r)

# -------------------------------------------------------------------
# 3) Run the grid search
# -------------------------------------------------------------------
breakouts = [10, 20, 30, 40, 50]
sl_mults = [0.5, 0.75, 1.0]
tp_mults = [1.0, 1.5, 2.0, 3.0]

results = []
for b, s, t in itertools.product(breakouts, sl_mults, tp_mults):
    print(f"Testing breakout={b}, SLx={s}, TPx={t}")
    res = backtest(b, s, t)
    results.append(res)

cols = ["breakout_len", "atr_sl_mult", "atr_tp_mult", "win_rate", "profit_factor", "expectancy", "total_r"]
df_res = pd.DataFrame(results, columns=cols)
df_res = df_res.sort_values("profit_factor", ascending=False).reset_index(drop=True)

# -------------------------------------------------------------------
# 4) Save & show top results
# -------------------------------------------------------------------
out_file = Path(__file__).resolve().parents[1] / "data" / "optimization_results.csv"
df_res.to_csv(out_file, index=False)

print("\nTop parameter sets:")
print(df_res.head(10).to_string(index=False))
print(f"\n✅ Saved all {len(df_res)} results to {out_file}")
