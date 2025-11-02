import pandas as pd
import os
import numpy as np

# Import the existing BreakoutStrategy class (assumed to be defined elsewhere).
from breakout_strategy import BreakoutStrategy

def forward_test(data_path: str, results_dir: str = "results/", initial_balance: float = 10000.0,
                 risk_per_trade: float = 0.01,
                 commission_rate: float = 0.0005,
                 slippage_atr_frac: float = 0.0,
                 slippage_spread: float = 0.0002,
                 slippage_random_std: float = 0.0,
                 breakout_length: int = 50,
                 atr_stop_multiplier: float = 0.75,
                 atr_tp_multiplier: float = 3.0,
                 volatility_filter: bool = True):
    """
    Perform forward testing on the BreakoutStrategy using data from data_path.
    - data_path: CSV file with historical candles (including columns like time, open, high, low, close, etc.).
    - results_dir: Directory to save output logs (will be created if not exists).
    - initial_balance: Starting capital for tracking equity.
    """
    # 1. Load historical candle data from CSV
    data = pd.read_csv(data_path)
    # (Optional) If the CSV has a time column, we can parse it as datetime:
    # data['time'] = pd.to_datetime(data['time'])
    
    # Prepare result containers
    trades_log = []    # List of completed trades (each as dict for easy DataFrame conversion)
    equity_log = []    # Equity value after each trade closure or over time
    # If detailed signal logging is needed, e.g., each candle's indicator state or entry signals:
    signal_log = []    # Could log signals or indicators per candle if needed
    
    # Ensure results directory exists
    os.makedirs(results_dir, exist_ok=True)
    
    # 2. Initialize the BreakoutStrategy instance using the same defaults as in run_strategy
    strategy = BreakoutStrategy(
        breakout_length=breakout_length,
        atr_stop_multiplier=atr_stop_multiplier,
        atr_tp_multiplier=atr_tp_multiplier,
        volatility_filter=volatility_filter
    )

    # Load the full dataset into the strategy and compute signals once.
    # This keeps the forward-test logic simple and reuses the existing implementation
    # of indicators/signals in BreakoutStrategy.
    strategy.load_data(data_path)
    strategy.compute_signals()
    df = strategy.data

    # Initialize tracking variables
    balance = initial_balance    # starting account balance (equity when no open trades)
    open_trade = None            # dict to hold the currently open trade (if any)
    trade_id = 0                 # incremental ID for each trade

    # 3. Iterate over the computed dataframe rows (no incremental on_new_candle API required)
    for timestamp, row in df.iterrows():
        open_price = row['open']
        high_price = row['high']
        low_price = row['low']
        close_price = row['close']

        # Determine entry signal from precomputed columns
        signal = None
        if 'long_signal' in row and row['long_signal']:
            signal = 'LONG'
        elif 'short_signal' in row and row['short_signal']:
            signal = 'SHORT'

        # 3a. If no trade is currently open, check for a new entry signal
        # Robust approach: require breakout to occur on the next candle and
        # use ATR-based stop/target levels consistent with the strategy.
        if open_trade is None and signal:
            # Need valid breakout level and ATR at this row
            try:
                atr = float(row.get('ATR', float('nan')))
            except Exception:
                atr = float('nan')

            # Skip if indicators not ready
            if pd.isna(atr) or pd.isna(row.get('prev_high')) or pd.isna(row.get('prev_low')):
                continue

            # determine breakout level depending on direction
            if signal == 'LONG':
                breakout_level = row['prev_high']
            else:
                breakout_level = row['prev_low']

            # find the next candle (if any) to check whether breakout was actually achieved
            pos = df.index.get_loc(timestamp)
            if pos + 1 < len(df):
                next_row = df.iloc[pos + 1]
                next_ts = df.index[pos + 1]
                # For longs: next candle must reach breakout_level (high >= level)
                # For shorts: next candle must reach breakout_level (low <= level)
                entry_taken = False
                if signal == 'LONG' and next_row['high'] >= breakout_level:
                    entry_price = breakout_level
                    entry_time = next_ts
                    entry_taken = True
                elif signal == 'SHORT' and next_row['low'] <= breakout_level:
                    entry_price = breakout_level
                    entry_time = next_ts
                    entry_taken = True
                if entry_taken:
                    trade_id += 1
                    trade_direction = signal
                    stop_loss = (entry_price - strategy.atr_stop_multiplier * atr) if trade_direction == 'LONG' else (entry_price + strategy.atr_stop_multiplier * atr)
                    take_profit = (entry_price + strategy.atr_tp_multiplier * atr) if trade_direction == 'LONG' else (entry_price - strategy.atr_tp_multiplier * atr)

                    # Position sizing: risk_per_trade is fraction of current balance to risk
                    stop_distance = abs(entry_price - stop_loss)
                    if stop_distance <= 0:
                        # defensive: skip impossible sizing
                        continue
                    risk_amount = balance * risk_per_trade
                    position_size = risk_amount / stop_distance

                    # slippage model: combine ATR-fraction slippage, spread and random noise
                    slippage_atr = slippage_atr_frac * atr
                    spread = slippage_spread
                    random_noise = np.random.normal(0, slippage_random_std * atr) if slippage_random_std > 0 else 0

                    # effective entry price including slippage and spread
                    if trade_direction == 'LONG':
                        entry_price_eff = entry_price + slippage_atr + spread/2 + random_noise
                    else:
                        entry_price_eff = entry_price - slippage_atr - spread/2 + random_noise

                    open_trade = {
                        "id": trade_id,
                        "direction": trade_direction,
                        "entry_time": entry_time,
                        "entry_price": entry_price,
                        "entry_price_eff": entry_price_eff,
                        "stop_loss": stop_loss,
                        "take_profit": take_profit,
                        "position_size": position_size,
                        "atr": atr
                    }
                    signal_log.append({
                        "time": entry_time,
                        "signal": f"ENTRY_{trade_direction}",
                        "price": entry_price_eff
                    })
                    # We moved the effective entry to the next candle; skip exit
                    # evaluation in the current iteration so monitoring begins on
                    # the candle where the trade actually exists.
                    continue
            # If no next candle or breakout not achieved, skip entry
            continue

        # 3b. If a trade is open, monitor SL/TP on the current candle
        if open_trade is not None:
            if open_trade["direction"] == 'LONG':
                sl_hit = low_price <= open_trade["stop_loss"]
                tp_hit = high_price >= open_trade["take_profit"]
            else:
                sl_hit = high_price >= open_trade["stop_loss"]
                tp_hit = low_price <= open_trade["take_profit"]

            exit_reason = None
            exit_price = None
            if sl_hit and tp_hit:
                exit_reason = "SL"
                exit_price = open_trade["stop_loss"]
            elif sl_hit:
                exit_reason = "SL"
                exit_price = open_trade["stop_loss"]
            elif tp_hit:
                exit_reason = "TP"
                exit_price = open_trade["take_profit"]

            if exit_reason:
                exit_time = timestamp
                # adjust exit price for slippage similarly to entry
                slippage_atr_exit = slippage_atr_frac * open_trade.get('atr', atr)
                random_noise_exit = np.random.normal(0, slippage_random_std * open_trade.get('atr', atr)) if slippage_random_std > 0 else 0
                if open_trade["direction"] == 'LONG':
                    exit_price_eff = exit_price - slippage_atr_exit - slippage_spread/2 + random_noise_exit
                else:
                    exit_price_eff = exit_price + slippage_atr_exit + slippage_spread/2 + random_noise_exit

                # gross profit in price points per contract
                if open_trade["direction"] == 'LONG':
                    gross_points = exit_price_eff - open_trade["entry_price_eff"]
                else:
                    gross_points = open_trade["entry_price_eff"] - exit_price_eff

                position_size = open_trade.get('position_size', 0)
                gross_profit = gross_points * position_size

                # commission charged on both entry and exit as fraction of trade value
                entry_value = open_trade["entry_price_eff"] * position_size
                exit_value = exit_price_eff * position_size
                commission = commission_rate * (abs(entry_value) + abs(exit_value))

                net_profit = gross_profit - commission

                balance += net_profit
                equity = balance
                equity_log.append({"time": exit_time, "equity": equity})

                trades_log.append({
                    "id": open_trade["id"],
                    "direction": open_trade["direction"],
                    "entry_time": open_trade["entry_time"],
                    "entry_price": open_trade["entry_price"],
                    "entry_price_eff": open_trade.get("entry_price_eff", open_trade["entry_price"]),
                    "position_size": position_size,
                    "exit_time": exit_time,
                    "exit_price": exit_price,
                    "exit_price_eff": exit_price_eff,
                    "exit_reason": exit_reason,
                    "profit": net_profit,
                    "gross_profit": gross_profit,
                    "commission": commission
                })
                signal_log.append({
                    "time": exit_time,
                    "signal": f"EXIT_{exit_reason}",
                    "price": exit_price
                })
                open_trade = None
            else:
                if open_trade["direction"] == 'LONG':
                    unrealized_pl = close_price - open_trade["entry_price"]
                else:
                    unrealized_pl = open_trade["entry_price"] - close_price
                equity = balance + unrealized_pl
                equity_log.append({"time": timestamp, "equity": equity})
    
    # End of data loop
    
    # 4. After processing all candles, save logs to CSV in the results directory
    trades_df = pd.DataFrame(trades_log)
    signals_df = pd.DataFrame(signal_log)
    equity_df  = pd.DataFrame(equity_log)
    trades_df.to_csv(os.path.join(results_dir, "trades_log.csv"), index=False)
    signals_df.to_csv(os.path.join(results_dir, "signal_log.csv"), index=False)
    equity_df.to_csv(os.path.join(results_dir, "equity_curve.csv"), index=False)
    print(f"Forward test completed. Logs saved to '{results_dir}'")
    # Optionally, return the DataFrames for further analysis
    return trades_df, signals_df, equity_df

# If the module is run directly, execute the forward test on the default data.
if __name__ == "__main__":
    # use repository-relative paths so running this module from the backtests
    # folder or from repo root both resolve the data/results locations
    forward_test(data_path="../data/v75_candles.csv", results_dir="../results/")
