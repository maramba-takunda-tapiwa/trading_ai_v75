"""
GBP/USD Hourly Breakout Strategy (V2 Logic)

Identical logic to EUR/USD but on GBP/USD pair:
- 25-bar breakouts (tightened from 30)
- 0.3x ATR stop loss (tightened from 0.5x)
- 4.0x ATR take profit
- 200-bar MA trend filter
- Dynamic position sizing
- Recovery mode after losses
- 15% equity soft stop

This provides diversification while using proven logic.
GBP/USD typically moves 10-20% different from EUR/USD,
reducing correlation risk in the portfolio.
"""

from breakout_strategy_v2 import BreakoutStrategyV2


class GBPUSDBreakout(BreakoutStrategyV2):
    """
    GBP/USD specific breakout strategy.
    
    Inherits all V2 logic from EUR/USD strategy but operates on GBP/USD data.
    Parameters optimized for cable volatility (slightly higher than EUR/USD).
    """
    
    def __init__(self):
        """Initialize with V2 optimized parameters for GBP/USD."""
        super().__init__(
            breakout_length=25,      # Slightly tighter for GBP volatility
            atr_stop_multiplier=0.3, # Tight stops for fast moves
            atr_tp_multiplier=4.0,   # Asymmetric 1:13+ R:R
            volatility_filter=True,   # Filter low volatility periods
            trend_filter=True,        # Only trade with 200MA trend
            dynamic_sizing=True,      # Scale down after losses
            recovery_mode=True,       # 50% size after 2 losses
            equity_stop_pct=0.15,    # Emergency stop at 15% DD
        )
        
        self.pair = 'GBPUSD'
    
    def run_backtest(self, initial_balance=166.67, risk_per_trade=0.002, save_csv=False, results_path=None):
        """
        Run backtest with GBP/USD specific capital (1/3 of total portfolio).
        
        Args:
            initial_balance: Starting capital for this strategy (~1/3 of $500)
            risk_per_trade: Risk per trade (0.2% of allocated capital)
            save_csv: Whether to save trades to CSV
            results_path: Path to save CSV if save_csv=True
        """
        return super().run_backtest(
            initial_balance=initial_balance,
            risk_per_trade=risk_per_trade,
            save_csv=save_csv,
            results_path=results_path
        )


# =============================================================================
# Demo Usage
# =============================================================================

if __name__ == "__main__":
    import pandas as pd
    
    print("=" * 60)
    print("GBP/USD HOURLY BREAKOUT STRATEGY (V2)")
    print("=" * 60)
    
    # Create strategy
    strategy = GBPUSDBreakout()
    
    print(f"\nPair: {strategy.pair}")
    print(f"Breakout Length: {strategy.breakout_length} bars")
    print(f"Stop Loss: {strategy.atr_stop_multiplier}x ATR")
    print(f"Take Profit: {strategy.atr_tp_multiplier}x ATR")
    print(f"Trend Filter: {strategy.trend_filter}")
    print(f"Dynamic Sizing: {strategy.dynamic_sizing}")
    print(f"Recovery Mode: {strategy.recovery_mode}")
    
    # Note: To run full backtest, you need GBP/USD historical data
    # strategy.load_data('../data/gbpusd_candles.csv')
    # results = strategy.run_backtest(initial_balance=166.67)
    
    print("\n" + "=" * 60)
    print("✅ GBP/USD STRATEGY READY")
    print("=" * 60)
    print("\nNote: Requires '../data/gbpusd_candles.csv' for backtesting")
    print("Download from: https://www.histdata.com/download-free-forex-historical-data/")
