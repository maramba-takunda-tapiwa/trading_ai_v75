"""
USD/JPY 4-Hour Trend Following Strategy

Different from breakouts - rides established trends using EMA crossovers.
Provides diversification by:
- Different timeframe (4H vs 1H)
- Different logic (trend following vs breakouts)
- Different pair characteristics (JPY vs EUR/GBP)

Logic:
- Entry: 50 EMA crosses above/below 200 EMA + ADX > 25 (trending)
- Stop: 1.5x ATR trailing stop
- Exit: Opposite crossover or stop hit
- Position sizing: Same V2 dynamic logic
"""

import pandas as pd
import numpy as np
from collections import deque


class USDJPYTrend:
    """
    Trend following strategy for USD/JPY on 4H timeframe.
    
    Uses EMA crossover + ADX filter to ride medium-term trends.
    Different logic than breakouts for portfolio diversification.
    """
    
    def __init__(self,
                 fast_ema=50,
                 slow_ema=200,
                 adx_threshold=25,
                 atr_stop_multiplier=1.5,
                 dynamic_sizing=True,
                 recovery_mode=True,
                 equity_stop_pct=0.15):
        """
        Args:
            fast_ema: Fast EMA period (50)
            slow_ema: Slow EMA period (200)
            adx_threshold: Minimum ADX to enter trend (25 = trending)
            atr_stop_multiplier: Trailing stop distance (1.5x ATR)
            dynamic_sizing: Scale position based on streak
            recovery_mode: Reduce size after losses
            equity_stop_pct: Emergency equity stop
        """
        self.fast_ema = fast_ema
        self.slow_ema = slow_ema
        self.adx_threshold = adx_threshold
        self.atr_stop_multiplier = atr_stop_multiplier
        self.dynamic_sizing = dynamic_sizing
        self.recovery_mode = recovery_mode
        self.equity_stop_pct = equity_stop_pct
        
        self.data = None
        self.trades = None
        self.equity_curve = None
        self.pair = 'USDJPY'
        
        # Tracking for dynamic sizing
        self.trade_streak = deque(maxlen=10)
        self.recovery_countdown = 0
    
    def load_data(self, file_path):
        """Load 4H OHLC data from CSV."""
        df = pd.read_csv(file_path, parse_dates=['time'])
        if 'time' in df.columns:
            df.set_index('time', inplace=True)
        self.data = df[['open', 'high', 'low', 'close']] if 'open' in df.columns else df
    
    def compute_signals(self):
        """Compute EMA crossovers, ADX, and ATR."""
        df = self.data.copy()
        
        # --- EMAs ---
        df['EMA_fast'] = df['close'].ewm(span=self.fast_ema, adjust=False).mean()
        df['EMA_slow'] = df['close'].ewm(span=self.slow_ema, adjust=False).mean()
        
        # --- ATR (14-period) ---
        prev_close = df['close'].shift(1)
        tr1 = df['high'] - df['low']
        tr2 = (df['high'] - prev_close).abs()
        tr3 = (df['low'] - prev_close).abs()
        df['TR'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df['ATR'] = df['TR'].ewm(alpha=1/14, adjust=False, min_periods=14).mean()
        
        # --- ADX (14-period) ---
        plus_dm = df['high'].diff()
        minus_dm = -df['low'].diff()
        
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        tr_smooth = df['TR'].rolling(window=14, min_periods=14).mean()
        plus_di = 100 * (plus_dm.rolling(window=14, min_periods=14).mean() / tr_smooth)
        minus_di = 100 * (minus_dm.rolling(window=14, min_periods=14).mean() / tr_smooth)
        
        dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di))
        df['ADX'] = dx.rolling(window=14, min_periods=14).mean()
        
        # --- Crossover Signals ---
        df['crossover_up'] = (df['EMA_fast'] > df['EMA_slow']) & (df['EMA_fast'].shift(1) <= df['EMA_slow'].shift(1))
        df['crossover_down'] = (df['EMA_fast'] < df['EMA_slow']) & (df['EMA_fast'].shift(1) >= df['EMA_slow'].shift(1))
        
        # --- Entry Signals (crossover + ADX filter) ---
        df['long_signal'] = df['crossover_up'] & (df['ADX'] > self.adx_threshold)
        df['short_signal'] = df['crossover_down'] & (df['ADX'] > self.adx_threshold)
        
        self.data = df
    
    def compute_position_size_multiplier(self):
        """Same dynamic sizing logic as breakout strategies."""
        if not self.dynamic_sizing:
            return 1.0
        
        if self.recovery_countdown > 0:
            self.recovery_countdown -= 1
            return 0.5
        
        if len(self.trade_streak) == 0:
            return 1.0
        
        losses = 0
        for outcome in reversed(self.trade_streak):
            if not outcome:
                losses += 1
            else:
                break
        
        if losses == 0:
            return 1.0
        elif losses == 1:
            return 0.8
        else:
            self.recovery_countdown = 5
            return 0.5
    
    def run_backtest(self, initial_balance=166.67, risk_per_trade=0.002, save_csv=False, results_path=None):
        """
        Run trend following backtest.
        
        Args:
            initial_balance: Starting capital (1/3 of portfolio)
            risk_per_trade: Risk per trade (0.2%)
            save_csv: Save trades to CSV
            results_path: CSV save path
        """
        if self.data is None:
            raise RuntimeError("Data not loaded. Call load_data() first.")
        
        self.compute_signals()
        df = self.data
        
        trades_list = []
        in_position = False
        position_type = None
        entry_price = stop_loss_price = None
        entry_time = None
        position_size_mult = 1.0
        trailing_stop = None
        
        balance = initial_balance
        peak_balance = balance
        equity_curve_list = []
        
        for idx in range(len(df)):
            row = df.iloc[idx]
            
            # Check for NaN indicators
            if pd.isna(row.get('EMA_fast')) or pd.isna(row.get('ADX')) or pd.isna(row.get('ATR')):
                continue
            
            # Equity stop check
            drawdown_pct = (peak_balance - balance) / peak_balance if peak_balance > 0 else 0
            if drawdown_pct > self.equity_stop_pct and in_position:
                # Emergency exit
                pnl = (row['close'] - entry_price) if position_type == 'Long' else (entry_price - row['close'])
                pnl_pct = 100 * pnl / entry_price
                balance += pnl
                
                trades_list.append({
                    'entry_time': entry_time,
                    'exit_time': df.index[idx],
                    'side': position_type,
                    'entry_price': entry_price,
                    'exit_price': row['close'],
                    'profit_pct': round(pnl_pct, 4),
                    'exit_reason': 'EQUITY_STOP',
                    'outcome': 'WIN' if pnl > 0 else 'LOSS',
                })
                
                self.trade_streak.append(pnl > 0)
                in_position = False
            
            if in_position:
                # Check for exit signals
                exit_triggered = False
                exit_reason = None
                exit_price = None
                
                # Opposite crossover
                if position_type == 'Long' and row.get('crossover_down', False):
                    exit_triggered = True
                    exit_reason = 'CROSSOVER'
                    exit_price = row['close']
                elif position_type == 'Short' and row.get('crossover_up', False):
                    exit_triggered = True
                    exit_reason = 'CROSSOVER'
                    exit_price = row['close']
                
                # Trailing stop
                if position_type == 'Long':
                    # Update trailing stop
                    new_stop = row['high'] - self.atr_stop_multiplier * row['ATR']
                    if trailing_stop is None or new_stop > trailing_stop:
                        trailing_stop = new_stop
                    
                    if row['low'] <= trailing_stop:
                        exit_triggered = True
                        exit_reason = 'TRAIL_STOP'
                        exit_price = trailing_stop
                
                elif position_type == 'Short':
                    # Update trailing stop
                    new_stop = row['low'] + self.atr_stop_multiplier * row['ATR']
                    if trailing_stop is None or new_stop < trailing_stop:
                        trailing_stop = new_stop
                    
                    if row['high'] >= trailing_stop:
                        exit_triggered = True
                        exit_reason = 'TRAIL_STOP'
                        exit_price = trailing_stop
                
                if exit_triggered:
                    # Calculate P&L
                    pnl = (exit_price - entry_price) if position_type == 'Long' else (entry_price - exit_price)
                    pnl_pct = 100 * pnl / entry_price
                    position_value = balance * risk_per_trade * position_size_mult
                    profit = position_value * (pnl / entry_price) * 100  # Scale to real dollars
                    
                    balance += profit
                    
                    trades_list.append({
                        'entry_time': entry_time,
                        'exit_time': df.index[idx],
                        'side': position_type,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'profit': round(profit, 2),
                        'profit_pct': round(pnl_pct, 4),
                        'exit_reason': exit_reason,
                        'size_mult': position_size_mult,
                        'outcome': 'WIN' if profit > 0 else 'LOSS',
                    })
                    
                    self.trade_streak.append(profit > 0)
                    in_position = False
                    trailing_stop = None
            
            else:
                # Check for entry signals
                if row.get('long_signal'):
                    position_size_mult = self.compute_position_size_multiplier()
                    position_type = 'Long'
                    entry_price = row['close']
                    entry_time = df.index[idx]
                    trailing_stop = entry_price - self.atr_stop_multiplier * row['ATR']
                    in_position = True
                
                elif row.get('short_signal'):
                    position_size_mult = self.compute_position_size_multiplier()
                    position_type = 'Short'
                    entry_price = row['close']
                    entry_time = df.index[idx]
                    trailing_stop = entry_price + self.atr_stop_multiplier * row['ATR']
                    in_position = True
            
            # Track equity
            if balance > peak_balance:
                peak_balance = balance
            
            equity_curve_list.append({
                'time': df.index[idx],
                'equity': balance,
            })
        
        # Store results
        self.trades = pd.DataFrame(trades_list) if trades_list else pd.DataFrame()
        self.equity_curve = pd.DataFrame(equity_curve_list)
        
        # Calculate metrics
        if len(self.trades) > 0:
            wins = (self.trades['outcome'] == 'WIN').sum()
            losses = (self.trades['outcome'] == 'LOSS').sum()
            win_rate = 100 * wins / len(self.trades)
            
            final_balance = balance
            total_return = 100 * (final_balance - initial_balance) / initial_balance
            max_dd = peak_balance - self.equity_curve['equity'].min()
            
            print(f"\n{'='*60}")
            print(f"USD/JPY TREND FOLLOWING BACKTEST RESULTS")
            print(f"{'='*60}")
            print(f"Initial Balance: ${initial_balance:,.2f}")
            print(f"Final Balance: ${final_balance:,.2f}")
            print(f"Total Return: {total_return:+.2f}%")
            print(f"Total Trades: {len(self.trades)}")
            print(f"Wins: {wins} | Losses: {losses}")
            print(f"Win Rate: {win_rate:.2f}%")
            print(f"Max Drawdown: ${max_dd:.2f}")
            print(f"{'='*60}\n")
        
        if save_csv and results_path and len(self.trades) > 0:
            self.trades.to_csv(results_path, index=False)
            print(f"Trades saved to: {results_path}")
        
        return {
            'final_balance': balance,
            'total_return': 100 * (balance - initial_balance) / initial_balance,
            'trades': len(self.trades),
            'win_rate': win_rate if len(self.trades) > 0 else 0,
        }


# =============================================================================
# Demo Usage
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("USD/JPY 4H TREND FOLLOWING STRATEGY")
    print("=" * 60)
    
    strategy = USDJPYTrend()
    
    print(f"\nPair: {strategy.pair}")
    print(f"Fast EMA: {strategy.fast_ema}")
    print(f"Slow EMA: {strategy.slow_ema}")
    print(f"ADX Threshold: {strategy.adx_threshold}")
    print(f"Trailing Stop: {strategy.atr_stop_multiplier}x ATR")
    print(f"Dynamic Sizing: {strategy.dynamic_sizing}")
    print(f"Recovery Mode: {strategy.recovery_mode}")
    
    print("\n" + "=" * 60)
    print("✅ USD/JPY TREND STRATEGY READY")
    print("=" * 60)
    print("\nNote: Requires '../data/usdjpy_4h_candles.csv' for backtesting")
    print("Different timeframe (4H) provides diversification")
