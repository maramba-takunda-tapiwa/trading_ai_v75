"""
Multi-Strategy Portfolio Manager - Trading AI V3

Coordinates multiple trading strategies running in parallel:
- Manages capital allocation across strategies
- Tracks positions and P&L per strategy
- Aggregates performance metrics
- Enforces portfolio-level risk limits

Strategies:
1. EUR/USD Hourly Breakout (V2 optimized)
2. GBP/USD Hourly Breakout (same logic, different pair)
3. USD/JPY 4H Trend Following (different timeframe + logic)

Each strategy gets equal capital allocation (1/3 of total).
Portfolio max risk: 20% of total capital at any time.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timezone
from typing import Dict, List, Optional
import json
from pathlib import Path


class StrategyManager:
    """
    Manages multiple trading strategies as a unified portfolio.
    
    Features:
    - Capital allocation (equal or custom weights)
    - Position tracking across strategies
    - Aggregated P&L and metrics
    - Portfolio-level risk management
    - Trade logging and state persistence
    """
    
    def __init__(self, 
                 total_capital: float = 500.0,
                 allocation_weights: Optional[Dict[str, float]] = None,
                 max_portfolio_risk_pct: float = 0.20,
                 max_correlation_exposure: float = 0.50):
        """
        Args:
            total_capital: Total account balance
            allocation_weights: Dict of strategy_name -> weight (must sum to 1.0)
                               If None, defaults to equal weighting
            max_portfolio_risk_pct: Max % of capital at risk across all strategies
            max_correlation_exposure: Max % exposure to correlated assets (e.g., EUR pairs)
        """
        self.total_capital = total_capital
        self.initial_capital = total_capital
        self.peak_capital = total_capital
        
        # Default to equal weighting if not specified
        if allocation_weights is None:
            self.allocation_weights = {
                'eurusd_breakout': 1/3,
                'gbpusd_breakout': 1/3,
                'usdjpy_trend': 1/3,
            }
        else:
            self.allocation_weights = allocation_weights
            
        self.max_portfolio_risk_pct = max_portfolio_risk_pct
        self.max_correlation_exposure = max_correlation_exposure
        
        # Strategy tracking
        self.strategies: Dict[str, dict] = {}
        self.initialize_strategies()
        
        # Position tracking
        self.open_positions: Dict[str, List[dict]] = {
            'eurusd_breakout': [],
            'gbpusd_breakout': [],
            'usdjpy_trend': [],
        }
        
        # Trade history
        self.all_trades: List[dict] = []
        
        # Portfolio metrics
        self.portfolio_metrics = {
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0.0,
            'total_profit': 0.0,
            'max_drawdown': 0.0,
            'current_drawdown': 0.0,
            'sharpe_ratio': 0.0,
            'profit_factor': 0.0,
        }
        
    def initialize_strategies(self):
        """Initialize capital allocation for each strategy."""
        for strategy_name, weight in self.allocation_weights.items():
            self.strategies[strategy_name] = {
                'allocated_capital': self.total_capital * weight,
                'current_balance': self.total_capital * weight,
                'peak_balance': self.total_capital * weight,
                'total_trades': 0,
                'wins': 0,
                'losses': 0,
                'profit': 0.0,
                'drawdown': 0.0,
                'active': True,  # Can be toggled on/off
            }
    
    def get_strategy_allocation(self, strategy_name: str) -> float:
        """Get current capital allocation for a strategy."""
        if strategy_name not in self.strategies:
            raise ValueError(f"Unknown strategy: {strategy_name}")
        return self.strategies[strategy_name]['current_balance']
    
    def check_portfolio_risk(self) -> dict:
        """
        Calculate current portfolio risk exposure.
        
        Returns:
            dict with risk metrics and whether new trades are allowed
        """
        total_risk = 0.0
        eur_exposure = 0.0
        usd_exposure = 0.0
        
        for strategy_name, positions in self.open_positions.items():
            for pos in positions:
                # Calculate risk (stop loss distance * position size)
                if 'risk_amount' in pos:
                    total_risk += pos['risk_amount']
                
                # Track currency exposure
                if 'eurusd' in strategy_name.lower():
                    eur_exposure += pos.get('position_value', 0)
                if 'gbpusd' in strategy_name.lower():
                    eur_exposure += pos.get('position_value', 0) * 0.7  # Correlated
                
        total_risk_pct = total_risk / self.total_capital if self.total_capital > 0 else 0
        eur_exposure_pct = eur_exposure / self.total_capital if self.total_capital > 0 else 0
        
        return {
            'total_risk_pct': total_risk_pct,
            'total_risk_amount': total_risk,
            'eur_exposure_pct': eur_exposure_pct,
            'allow_new_trades': total_risk_pct < self.max_portfolio_risk_pct,
            'allow_eur_trades': eur_exposure_pct < self.max_correlation_exposure,
        }
    
    def can_open_position(self, strategy_name: str, pair: str, risk_amount: float) -> bool:
        """
        Check if a new position can be opened based on portfolio risk limits.
        
        Args:
            strategy_name: Name of strategy requesting position
            pair: Currency pair (e.g., 'EURUSD')
            risk_amount: Dollar risk of new position
            
        Returns:
            True if position is allowed, False otherwise
        """
        # Check if strategy is active
        if not self.strategies.get(strategy_name, {}).get('active', False):
            return False
        
        # Get current portfolio risk
        risk_check = self.check_portfolio_risk()
        
        # Check total portfolio risk
        new_total_risk = risk_check['total_risk_amount'] + risk_amount
        if new_total_risk / self.total_capital > self.max_portfolio_risk_pct:
            return False
        
        # Check correlation exposure (EUR pairs)
        if 'EUR' in pair.upper() or 'GBP' in pair.upper():
            if not risk_check['allow_eur_trades']:
                return False
        
        return True
    
    def log_trade(self, strategy_name: str, trade: dict):
        """
        Log a completed trade and update strategy metrics.
        
        Args:
            strategy_name: Strategy that executed the trade
            trade: Trade details dict with keys:
                - entry_time, exit_time, side, entry_price, exit_price
                - profit, outcome, exit_reason, etc.
        """
        if strategy_name not in self.strategies:
            raise ValueError(f"Unknown strategy: {strategy_name}")
        
        # Add strategy identifier
        trade['strategy'] = strategy_name
        
        # Update strategy metrics
        strat = self.strategies[strategy_name]
        strat['total_trades'] += 1
        strat['profit'] += trade.get('profit', 0)
        strat['current_balance'] += trade.get('profit', 0)
        
        if trade.get('outcome') == 'WIN':
            strat['wins'] += 1
        elif trade.get('outcome') == 'LOSS':
            strat['losses'] += 1
        
        # Update peak and drawdown
        if strat['current_balance'] > strat['peak_balance']:
            strat['peak_balance'] = strat['current_balance']
        
        strat['drawdown'] = strat['peak_balance'] - strat['current_balance']
        
        # Add to portfolio trade history
        self.all_trades.append(trade)
        
        # Update total capital
        self.total_capital += trade.get('profit', 0)
        if self.total_capital > self.peak_capital:
            self.peak_capital = self.total_capital
        
        # Update portfolio metrics
        self.update_portfolio_metrics()
    
    def update_portfolio_metrics(self):
        """Recalculate aggregated portfolio metrics."""
        if len(self.all_trades) == 0:
            return
        
        total_profit = sum(t.get('profit', 0) for t in self.all_trades)
        wins = sum(1 for t in self.all_trades if t.get('outcome') == 'WIN')
        losses = sum(1 for t in self.all_trades if t.get('outcome') == 'LOSS')
        total_trades = len(self.all_trades)
        
        win_rate = 100 * wins / total_trades if total_trades > 0 else 0
        
        # Calculate profit factor
        gross_profit = sum(t.get('profit', 0) for t in self.all_trades if t.get('profit', 0) > 0)
        gross_loss = abs(sum(t.get('profit', 0) for t in self.all_trades if t.get('profit', 0) < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Drawdown
        current_drawdown = self.peak_capital - self.total_capital
        max_drawdown = max(current_drawdown, self.portfolio_metrics.get('max_drawdown', 0))
        
        self.portfolio_metrics = {
            'total_trades': total_trades,
            'wins': wins,
            'losses': losses,
            'win_rate': round(win_rate, 2),
            'total_profit': round(total_profit, 2),
            'current_balance': round(self.total_capital, 2),
            'max_drawdown': round(max_drawdown, 2),
            'current_drawdown': round(current_drawdown, 2),
            'profit_factor': round(profit_factor, 3),
            'return_pct': round(100 * total_profit / self.initial_capital, 2),
        }
    
    def get_portfolio_summary(self) -> dict:
        """Get comprehensive portfolio status."""
        return {
            'total_capital': round(self.total_capital, 2),
            'initial_capital': round(self.initial_capital, 2),
            'peak_capital': round(self.peak_capital, 2),
            'metrics': self.portfolio_metrics,
            'strategies': {
                name: {
                    'balance': round(data['current_balance'], 2),
                    'allocated': round(data['allocated_capital'], 2),
                    'profit': round(data['profit'], 2),
                    'trades': data['total_trades'],
                    'wins': data['wins'],
                    'losses': data['losses'],
                    'win_rate': round(100 * data['wins'] / data['total_trades'], 2) if data['total_trades'] > 0 else 0,
                    'drawdown': round(data['drawdown'], 2),
                    'active': data['active'],
                }
                for name, data in self.strategies.items()
            },
            'risk_status': self.check_portfolio_risk(),
        }
    
    def save_state(self, file_path: str):
        """Save portfolio state to JSON file."""
        state = {
            'total_capital': self.total_capital,
            'initial_capital': self.initial_capital,
            'peak_capital': self.peak_capital,
            'strategies': self.strategies,
            'portfolio_metrics': self.portfolio_metrics,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }
        
        with open(file_path, 'w') as f:
            json.dump(state, f, indent=2)
    
    def load_state(self, file_path: str):
        """Load portfolio state from JSON file."""
        with open(file_path, 'r') as f:
            state = json.load(f)
        
        self.total_capital = state['total_capital']
        self.initial_capital = state['initial_capital']
        self.peak_capital = state['peak_capital']
        self.strategies = state['strategies']
        self.portfolio_metrics = state['portfolio_metrics']


# =============================================================================
# Demo Usage
# =============================================================================

if __name__ == "__main__":
    # Create portfolio manager
    manager = StrategyManager(total_capital=500.0)
    
    print("=" * 60)
    print("MULTI-STRATEGY PORTFOLIO MANAGER - V3")
    print("=" * 60)
    
    # Show initial allocation
    summary = manager.get_portfolio_summary()
    print(f"\nTotal Capital: ${summary['total_capital']}")
    print(f"\nStrategy Allocations:")
    for name, data in summary['strategies'].items():
        print(f"  {name}: ${data['allocated']} ({data['win_rate']}% WR, {data['trades']} trades)")
    
    # Simulate some trades
    print("\n" + "=" * 60)
    print("SIMULATING TRADES...")
    print("=" * 60)
    
    # EUR/USD win
    manager.log_trade('eurusd_breakout', {
        'entry_time': '2025-11-02 10:00',
        'exit_time': '2025-11-02 12:00',
        'side': 'Long',
        'entry_price': 1.0850,
        'exit_price': 1.0865,
        'profit': 3.25,
        'outcome': 'WIN',
        'exit_reason': 'TP',
    })
    
    # GBP/USD win
    manager.log_trade('gbpusd_breakout', {
        'entry_time': '2025-11-02 11:00',
        'exit_time': '2025-11-02 13:00',
        'side': 'Short',
        'entry_price': 1.2750,
        'exit_price': 1.2735,
        'profit': 2.80,
        'outcome': 'WIN',
        'exit_reason': 'TP',
    })
    
    # USD/JPY loss
    manager.log_trade('usdjpy_trend', {
        'entry_time': '2025-11-02 12:00',
        'exit_time': '2025-11-02 14:00',
        'side': 'Long',
        'entry_price': 149.50,
        'exit_price': 149.35,
        'profit': -1.50,
        'outcome': 'LOSS',
        'exit_reason': 'SL',
    })
    
    # Show updated summary
    summary = manager.get_portfolio_summary()
    print(f"\nPortfolio Balance: ${summary['total_capital']}")
    print(f"Total Profit: ${summary['metrics']['total_profit']}")
    print(f"Win Rate: {summary['metrics']['win_rate']}%")
    print(f"\nStrategy Performance:")
    for name, data in summary['strategies'].items():
        print(f"  {name}: ${data['balance']} (P&L: ${data['profit']})")
    
    print(f"\nRisk Status:")
    risk = summary['risk_status']
    print(f"  Total Risk: {risk['total_risk_pct']*100:.1f}% of capital")
    print(f"  EUR Exposure: {risk['eur_exposure_pct']*100:.1f}% of capital")
    print(f"  New Trades Allowed: {risk['allow_new_trades']}")
    
    print("\n" + "=" * 60)
    print("✅ PORTFOLIO MANAGER READY")
    print("=" * 60)
