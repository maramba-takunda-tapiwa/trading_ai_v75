"""
Capital Scaling & Profit Management System

Automated capital management:
- Auto-withdraw 50% of profits monthly
- Reinvest 50% for compounding
- Scale up position sizes with balance growth
- Add fresh capital only when Sharpe > 2.0 for 3 months
- Protect profits from future drawdowns

This maximizes growth while securing gains.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from collections import deque
import json
import os


class CapitalScaler:
    """
    Manages capital allocation and profit taking.
    
    Features:
    - Monthly profit withdrawals
    - Compound reinvestment
    - Position size scaling
    - Capital injection criteria
    - Drawdown protection
    """
    
    def __init__(self,
                 initial_capital: float = 500.0,
                 withdrawal_pct: float = 0.50,
                 min_sharpe_for_add: float = 2.0,
                 min_months_for_add: int = 3):
        """
        Args:
            initial_capital: Starting balance
            withdrawal_pct: % of profits to withdraw monthly
            min_sharpe_for_add: Minimum Sharpe to allow capital adds
            min_months_for_add: Months of good performance before allowing adds
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.peak_capital = initial_capital
        
        self.withdrawal_pct = withdrawal_pct
        self.min_sharpe_for_add = min_sharpe_for_add
        self.min_months_for_add = min_months_for_add
        
        # Tracking
        self.total_withdrawn = 0
        self.total_added = 0
        self.monthly_returns = deque(maxlen=12)  # Last 12 months
        self.last_withdrawal_month = None
        self.withdrawal_history = []
        self.capital_history = []
        
        # Performance tracking for capital add criteria
        self.monthly_sharpe = deque(maxlen=12)
    
    def update_month_end(self, current_balance: float, month_sharpe: float = None):
        """
        Process end-of-month capital management.
        
        Args:
            current_balance: Current account balance
            month_sharpe: Sharpe ratio for the month (optional)
        """
        month_profit = current_balance - self.current_capital
        month_return_pct = 100 * month_profit / self.current_capital if self.current_capital > 0 else 0
        
        self.monthly_returns.append(month_return_pct)
        if month_sharpe is not None:
            self.monthly_sharpe.append(month_sharpe)
        
        print(f"\n{'='*70}")
        print(" " * 20 + "MONTHLY CAPITAL MANAGEMENT")
        print(f"{'='*70}")
        print(f"\nMonth: {datetime.now(timezone.utc).strftime('%B %Y')}")
        print(f"Starting Capital: ${self.current_capital:.2f}")
        print(f"Ending Balance: ${current_balance:.2f}")
        print(f"Monthly Profit: ${month_profit:.2f} ({month_return_pct:+.2f}%)")
        
        # Handle profits
        if month_profit > 0:
            withdrawal_amount = month_profit * self.withdrawal_pct
            reinvest_amount = month_profit * (1 - self.withdrawal_pct)
            
            # Execute withdrawal
            self.total_withdrawn += withdrawal_amount
            self.current_capital = self.current_capital + reinvest_amount
            
            self.withdrawal_history.append({
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'profit': month_profit,
                'withdrawn': withdrawal_amount,
                'reinvested': reinvest_amount,
                'total_withdrawn': self.total_withdrawn,
            })
            
            print(f"\n💰 PROFIT MANAGEMENT:")
            print(f"   Withdraw ({self.withdrawal_pct*100:.0f}%):  ${withdrawal_amount:.2f}")
            print(f"   Reinvest ({(1-self.withdrawal_pct)*100:.0f}%):  ${reinvest_amount:.2f}")
            print(f"   Total Withdrawn (all time): ${self.total_withdrawn:.2f}")
        
        elif month_profit < 0:
            # Loss month - just update capital
            self.current_capital = current_balance
            print(f"\n📉 LOSS MONTH: No withdrawals, capital adjusted")
        
        # Update peak
        if self.current_capital > self.peak_capital:
            self.peak_capital = self.current_capital
        
        # Record history
        self.capital_history.append({
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'capital': self.current_capital,
            'return_pct': month_return_pct,
        })
        
        print(f"\n📊 NEW CAPITAL: ${self.current_capital:.2f}")
        print(f"{'='*70}\n")
        
        return {
            'new_capital': self.current_capital,
            'withdrawn': withdrawal_amount if month_profit > 0 else 0,
            'reinvested': reinvest_amount if month_profit > 0 else 0,
        }
    
    def check_capital_add_criteria(self) -> dict:
        """
        Check if criteria are met to add more capital.
        
        Returns:
            dict with approval status and reasons
        """
        reasons = []
        approved = True
        
        # Check 1: Minimum months of data
        if len(self.monthly_sharpe) < self.min_months_for_add:
            reasons.append(f"Need {self.min_months_for_add} months of performance (have {len(self.monthly_sharpe)})")
            approved = False
        
        # Check 2: Sharpe ratio criterion
        if len(self.monthly_sharpe) >= self.min_months_for_add:
            avg_sharpe = np.mean(list(self.monthly_sharpe)[-self.min_months_for_add:])
            
            if avg_sharpe < self.min_sharpe_for_add:
                reasons.append(f"Sharpe ratio {avg_sharpe:.2f} below {self.min_sharpe_for_add:.2f}")
                approved = False
            else:
                reasons.append(f"Sharpe ratio {avg_sharpe:.2f} meets threshold ✅")
        
        # Check 3: Recent profitability
        if len(self.monthly_returns) >= self.min_months_for_add:
            recent_returns = list(self.monthly_returns)[-self.min_months_for_add:]
            losing_months = sum(1 for r in recent_returns if r < 0)
            
            if losing_months > 1:
                reasons.append(f"{losing_months} losing months in last {self.min_months_for_add} months")
                approved = False
            else:
                reasons.append(f"Consistent profitability ({self.min_months_for_add-losing_months}/{self.min_months_for_add} winning months) ✅")
        
        # Check 4: Not in drawdown
        if self.current_capital < self.peak_capital * 0.95:
            dd_pct = 100 * (self.peak_capital - self.current_capital) / self.peak_capital
            reasons.append(f"In drawdown: {dd_pct:.1f}%")
            approved = False
        else:
            reasons.append("Not in significant drawdown ✅")
        
        return {
            'approved': approved,
            'reasons': reasons,
        }
    
    def add_capital(self, amount: float) -> bool:
        """
        Add fresh capital to the account.
        
        Args:
            amount: Amount to add
            
        Returns:
            bool: True if successful
        """
        # Check criteria
        check = self.check_capital_add_criteria()
        
        print(f"\n{'='*70}")
        print(" " * 20 + "CAPITAL ADDITION REQUEST")
        print(f"{'='*70}")
        print(f"\nRequested Amount: ${amount:.2f}")
        print(f"Current Capital: ${self.current_capital:.2f}")
        print(f"\nCriteria Check:")
        
        for reason in check['reasons']:
            print(f"  • {reason}")
        
        if not check['approved']:
            print(f"\n❌ CAPITAL ADDITION REJECTED")
            print(f"{'='*70}\n")
            return False
        
        # Approved - add capital
        self.current_capital += amount
        self.total_added += amount
        
        print(f"\n✅ CAPITAL ADDITION APPROVED")
        print(f"   New Capital: ${self.current_capital:.2f}")
        print(f"   Total Added (all time): ${self.total_added:.2f}")
        print(f"{'='*70}\n")
        
        return True
    
    def get_position_size_multiplier(self) -> float:
        """
        Calculate position size multiplier based on current capital vs initial.
        
        As account grows, position sizes scale proportionally.
        """
        if self.initial_capital > 0:
            multiplier = self.current_capital / self.initial_capital
            return round(multiplier, 2)
        return 1.0
    
    def get_summary(self) -> dict:
        """Get comprehensive capital management summary."""
        total_roi = 100 * (self.current_capital - self.initial_capital) / self.initial_capital
        
        # Calculate realized gains (withdrawn profits)
        realized_gains = self.total_withdrawn
        
        # Total value (capital + withdrawn)
        total_value = self.current_capital + self.total_withdrawn
        total_value_roi = 100 * (total_value - self.initial_capital) / self.initial_capital
        
        return {
            'initial_capital': self.initial_capital,
            'current_capital': self.current_capital,
            'peak_capital': self.peak_capital,
            'total_withdrawn': self.total_withdrawn,
            'total_added': self.total_added,
            'total_value': total_value,
            'capital_roi': round(total_roi, 2),
            'total_value_roi': round(total_value_roi, 2),
            'position_size_multiplier': self.get_position_size_multiplier(),
            'months_tracked': len(self.monthly_returns),
        }
    
    def save_state(self, file_path: str):
        """Save capital scaler state to JSON."""
        state = {
            'initial_capital': self.initial_capital,
            'current_capital': self.current_capital,
            'peak_capital': self.peak_capital,
            'total_withdrawn': self.total_withdrawn,
            'total_added': self.total_added,
            'withdrawal_history': self.withdrawal_history,
            'capital_history': self.capital_history,
            'last_update': datetime.now(timezone.utc).isoformat(),
        }
        
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as f:
            json.dump(state, f, indent=2)


# =============================================================================
# Demo Usage
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print(" " * 15 + "CAPITAL SCALING SYSTEM - V3")
    print("=" * 70)
    
    # Create scaler
    scaler = CapitalScaler(
        initial_capital=500.0,
        withdrawal_pct=0.50,
        min_sharpe_for_add=2.0,
        min_months_for_add=3,
    )
    
    print("\n📊 Simulating 6 months of trading...")
    
    # Simulate 6 profitable months
    balance = 500.0
    monthly_profits = [100, 120, 80, 150, 90, 110]  # Dollars
    monthly_sharpes = [2.3, 2.5, 1.8, 2.7, 2.1, 2.4]
    
    for i, (profit, sharpe) in enumerate(zip(monthly_profits, monthly_sharpes)):
        balance += profit
        print(f"\n--- Month {i+1} ---")
        result = scaler.update_month_end(balance, sharpe)
        balance = result['new_capital']
    
    # Try to add capital
    print("\n" + "=" * 70)
    print(" " * 15 + "ATTEMPTING CAPITAL ADDITION")
    print("=" * 70)
    
    scaler.add_capital(500.0)
    
    # Summary
    summary = scaler.get_summary()
    
    print("\n" + "=" * 70)
    print(" " * 20 + "SUMMARY")
    print("=" * 70)
    print(f"\nInitial Capital: ${summary['initial_capital']:.2f}")
    print(f"Current Capital: ${summary['current_capital']:.2f}")
    print(f"Total Withdrawn: ${summary['total_withdrawn']:.2f}")
    print(f"Total Value: ${summary['total_value']:.2f}")
    print(f"\nROI on Capital: {summary['capital_roi']:.2f}%")
    print(f"ROI on Total Value: {summary['total_value_roi']:.2f}%")
    print(f"Position Size Multiplier: {summary['position_size_multiplier']}x")
    
    print("\n" + "=" * 70)
    print("✅ CAPITAL SCALING SYSTEM READY")
    print("=" * 70)
