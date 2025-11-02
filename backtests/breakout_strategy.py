import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

class BreakoutStrategy:
    def __init__(self, breakout_length, atr_stop_multiplier, atr_tp_multiplier, volatility_filter):
        self.breakout_length = breakout_length
        self.atr_stop_multiplier = atr_stop_multiplier
        self.atr_tp_multiplier = atr_tp_multiplier
        self.volatility_filter = volatility_filter
        self.data = None
        self.trades = None
        self.equity_curve = None

    def load_data(self, file_path):
        df = pd.read_csv(file_path, parse_dates=['time'])
        if 'time' in df.columns:
            df.set_index('time', inplace=True)
        self.data = df[['open', 'high', 'low', 'close']] if 'open' in df.columns else df

    def compute_signals(self):
        df = self.data.copy()
        prev_close = df['close'].shift(1)
        tr1 = df['high'] - df['low']
        tr2 = (df['high'] - prev_close).abs()
        tr3 = (df['low'] - prev_close).abs()
        df['TR'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr_period = 14
        df['ATR'] = df['TR'].ewm(alpha=1/atr_period, adjust=False, min_periods=atr_period).mean()
        N = self.breakout_length
        df['prev_high'] = df['high'].shift(1).rolling(window=N, min_periods=N).max()
        df['prev_low'] = df['low'].shift(1).rolling(window=N, min_periods=N).min()
        breakout_up = df['high'] > df['prev_high']
        breakout_down = df['low'] < df['prev_low']
        if self.volatility_filter:
            df['ATR_slow'] = df['ATR'].rolling(window=14, min_periods=14).mean()
            vol_cond = df['ATR'] > df['ATR_slow']
        else:
            vol_cond = pd.Series(True, index=df.index)
        df['long_signal'] = breakout_up & vol_cond
        df['short_signal'] = breakout_down & vol_cond
        self.data = df

    def run_backtest(self, save_csv=False, results_path=None):
        if self.data is None:
            raise RuntimeError("Data not loaded. Please call load_data() first.")
        self.compute_signals()
        df = self.data
        trades_list = []
        in_position = False
        position_type = None
        entry_price = stop_loss_price = target_price = None
        entry_time = None

        for idx in range(len(df)):
            if np.isnan(df['prev_high'].iloc[idx]) or np.isnan(df['prev_low'].iloc[idx]) or np.isnan(df['ATR'].iloc[idx]):
                continue
            if not in_position:
                if df['long_signal'].iloc[idx]:
                    position_type = 'long'
                    entry_price = df['prev_high'].iloc[idx]
                    stop_loss_price = entry_price - self.atr_stop_multiplier * df['ATR'].iloc[idx]
                    target_price = entry_price + self.atr_tp_multiplier * df['ATR'].iloc[idx]
                    entry_time = df.index[idx]
                    in_position = True
                elif df['short_signal'].iloc[idx]:
                    position_type = 'short'
                    entry_price = df['prev_low'].iloc[idx]
                    stop_loss_price = entry_price + self.atr_stop_multiplier * df['ATR'].iloc[idx]
                    target_price = entry_price - self.atr_tp_multiplier * df['ATR'].iloc[idx]
                    entry_time = df.index[idx]
                    in_position = True
            else:
                if position_type == 'long':
                    stop_hit = df['low'].iloc[idx] <= stop_loss_price
                    target_hit = df['high'].iloc[idx] >= target_price
                    if stop_hit and target_hit:
                        dist_to_stop = abs(entry_price - stop_loss_price)
                        dist_to_target = abs(target_price - entry_price)
                        exit_price = target_price if dist_to_target <= dist_to_stop else stop_loss_price
                        exit_reason = 'TP' if dist_to_target <= dist_to_stop else 'SL'
                    elif stop_hit:
                        exit_price = stop_loss_price
                        exit_reason = 'SL'
                    elif target_hit:
                        exit_price = target_price
                        exit_reason = 'TP'
                    else:
                        continue
                    exit_time = df.index[idx]
                    profit = exit_price - entry_price
                    risk = entry_price - stop_loss_price
                    R = profit / risk
                    trades_list.append({
                        'entry_time': entry_time, 'exit_time': exit_time, 'side': 'Long',
                        'entry_price': entry_price, 'exit_price': exit_price,
                        'R': R, 'exit_reason': exit_reason
                    })
                    in_position = False
                    position_type = None
                elif position_type == 'short':
                    stop_hit = df['high'].iloc[idx] >= stop_loss_price
                    target_hit = df['low'].iloc[idx] <= target_price
                    if stop_hit and target_hit:
                        dist_to_stop = abs(stop_loss_price - entry_price)
                        dist_to_target = abs(entry_price - target_price)
                        exit_price = target_price if dist_to_target <= dist_to_stop else stop_loss_price
                        exit_reason = 'TP' if dist_to_target <= dist_to_stop else 'SL'
                    elif stop_hit:
                        exit_price = stop_loss_price
                        exit_reason = 'SL'
                    elif target_hit:
                        exit_price = target_price
                        exit_reason = 'TP'
                    else:
                        continue
                    exit_time = df.index[idx]
                    profit = entry_price - exit_price
                    risk = stop_loss_price - entry_price
                    R = profit / risk
                    trades_list.append({
                        'entry_time': entry_time, 'exit_time': exit_time, 'side': 'Short',
                        'entry_price': entry_price, 'exit_price': exit_price,
                        'R': R, 'exit_reason': exit_reason
                    })
                    in_position = False
                    position_type = None

        if in_position:
            exit_time = df.index[-1]
            last_close = df['close'].iloc[-1]
            if position_type == 'long':
                exit_price = last_close
                exit_reason = 'EOD'
                profit = exit_price - entry_price
                risk = entry_price - stop_loss_price
                R = profit / risk
                side_label = 'Long'
            else:
                exit_price = last_close
                exit_reason = 'EOD'
                profit = entry_price - exit_price
                risk = stop_loss_price - entry_price
                R = profit / risk
                side_label = 'Short'
            trades_list.append({
                'entry_time': entry_time, 'exit_time': exit_time, 'side': side_label,
                'entry_price': entry_price, 'exit_price': exit_price,
                'R': R, 'exit_reason': exit_reason
            })

        trades_df = pd.DataFrame(trades_list)
        total_R = trades_df['R'].sum() if not trades_df.empty else 0.0
        wins = trades_df[trades_df['R'] > 0]
        losses = trades_df[trades_df['R'] < 0]
        win_rate = (len(wins) / len(trades_df) * 100) if len(trades_df) > 0 else 0.0
        expectancy = (total_R / len(trades_df)) if len(trades_df) > 0 else 0.0
        profit_factor = (wins['R'].sum() / -losses['R'].sum()) if len(losses) > 0 else float('inf')
        equity = pd.Series(0.0, index=df.index)
        cum_R = 0.0
        trade_idx = 0
        for t, current_time in enumerate(df.index):
            if not trades_df.empty and trade_idx < len(trades_df) and current_time == trades_df.loc[trade_idx, 'exit_time']:
                cum_R += trades_df.loc[trade_idx, 'R']
                trade_idx += 1
            equity.iloc[t] = cum_R
        drawdown = equity.cummax() - equity
        max_drawdown = drawdown.max() if len(drawdown) > 0 else 0.0
        self.trades = trades_df
        self.equity_curve = equity
        if save_csv and results_path:
            trades_df.to_csv(results_path, index=False)
        print(f"Total R: {total_R:.2f}")
        print(f"Win rate: {win_rate:.2f}%")
        print(f"Expectancy (Avg R): {expectancy:.2f}")
        print(f"Profit factor: {profit_factor:.2f}")
        print(f"Max drawdown (R): {max_drawdown:.2f}")
        return trades_df

    def plot_equity_curve(self, save_path=None):
        if self.equity_curve is None:
            raise RuntimeError("No results to plot. Please run run_backtest() first.")
        equity = self.equity_curve
        cum_max = equity.cummax()
        drawdown = cum_max - equity
        fig, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
        axes[0].plot(equity.index, equity.values, color='blue', label='Equity (R)')
        axes[0].set_title("Equity Curve")
        axes[0].set_ylabel("Cumulative R")
        axes[0].legend(loc='best')
        axes[1].plot(drawdown.index, -drawdown.values, color='red', label='Drawdown')
        axes[1].axhline(0, color='black', linewidth=1)
        axes[1].set_title("Drawdown")
        axes[1].set_ylabel("Drawdown (R)")
        axes[1].legend(loc='best')
        plt.xlabel("Time")
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path)
            plt.close()
        else:
            plt.show()