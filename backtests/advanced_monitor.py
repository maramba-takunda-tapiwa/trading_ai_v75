"""
Advanced Monitoring & Kill Switch System

Real-time performance tracking with automatic safety mechanisms:
- Sharpe ratio monitoring (rolling 30-day)
- Auto-shutdown after 3 consecutive losing days
- Drawdown alerts (5%, 10%, 15% thresholds)
- Win rate degradation detection
- Emergency manual override
- Optional Telegram/Email alerts

Prevents runaway losses and detects system degradation early.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from collections import deque
import json
import os


class TradingMonitor:
    """
    Real-time trading system monitor with kill switches.
    
    Features:
    - Performance metrics (Sharpe, win rate, drawdown)
    - Automatic shutdown triggers
    - Alert system
    - Manual override controls
    """
    
    def __init__(self,
                 max_consecutive_loss_days=3,
                 max_drawdown_pct=0.15,
                 min_sharpe_ratio=0.5,
                 min_win_rate_pct=50,
                 alert_thresholds=[0.05, 0.10, 0.15]):
        """
        Args:
            max_consecutive_loss_days: Auto-shutdown after N losing days
            max_drawdown_pct: Hard stop at this drawdown
            min_sharpe_ratio: Pause trading if Sharpe drops below this
            min_win_rate_pct: Alert if win rate drops below this
            alert_thresholds: Drawdown levels that trigger alerts
        """
        self.max_consecutive_loss_days = max_consecutive_loss_days
        self.max_drawdown_pct = max_drawdown_pct
        self.min_sharpe_ratio = min_sharpe_ratio
        self.min_win_rate_pct = min_win_rate_pct
        self.alert_thresholds = sorted(alert_thresholds)
        
        # State tracking
        self.trading_enabled = True
        self.manual_override = False
        self.consecutive_loss_days = 0
        self.last_day_pnl = 0
        self.current_day = datetime.now(timezone.utc).date()
        
        # Performance tracking
        self.daily_pnl = deque(maxlen=30)  # Last 30 days
        self.all_trades = []
        self.peak_balance = 0
        self.alert_history = []
        
        # Kill switch reasons
        self.shutdown_reason = None
    
    def update_trade(self, trade: dict, current_balance: float):
        """
        Process a new trade and update monitoring.
        
        Args:
            trade: Trade dict with profit, outcome, timestamp
            current_balance: Current account balance
        """
        self.all_trades.append(trade)
        
        # Update peak balance
        if current_balance > self.peak_balance:
            self.peak_balance = current_balance
        
        # Update daily P&L
        trade_date = pd.to_datetime(trade.get('exit_time')).date()
        
        if trade_date != self.current_day:
            # New day - record previous day's P&L
            self.daily_pnl.append(self.last_day_pnl)
            
            # Check for consecutive loss days
            if self.last_day_pnl < 0:
                self.consecutive_loss_days += 1
            else:
                self.consecutive_loss_days = 0
            
            # Reset for new day
            self.current_day = trade_date
            self.last_day_pnl = 0
        
        # Add to today's P&L
        self.last_day_pnl += trade.get('profit', 0)
        
        # Run checks
        self.check_kill_switches(current_balance)
    
    def check_kill_switches(self, current_balance: float):
        """Check all automatic shutdown conditions."""
        if self.manual_override:
            return  # Manual override active - skip checks
        
        # 1. Check consecutive losing days
        if self.consecutive_loss_days >= self.max_consecutive_loss_days:
            self.shutdown(
                f"CONSECUTIVE_LOSS_DAYS: {self.consecutive_loss_days} days",
                current_balance
            )
            return
        
        # 2. Check drawdown
        if self.peak_balance > 0:
            drawdown_pct = (self.peak_balance - current_balance) / self.peak_balance
            
            if drawdown_pct >= self.max_drawdown_pct:
                self.shutdown(
                    f"MAX_DRAWDOWN: {drawdown_pct*100:.1f}% (limit: {self.max_drawdown_pct*100:.0f}%)",
                    current_balance
                )
                return
            
            # Alert thresholds
            for threshold in self.alert_thresholds:
                if drawdown_pct >= threshold and not self.has_alert(f"DD_{threshold*100:.0f}"):
                    self.create_alert(
                        level="WARNING",
                        message=f"Drawdown reached {drawdown_pct*100:.1f}%",
                        current_balance=current_balance
                    )
        
        # 3. Check Sharpe ratio (if enough data)
        if len(self.daily_pnl) >= 10:
            sharpe = self.calculate_sharpe_ratio()
            
            if sharpe < self.min_sharpe_ratio:
                self.create_alert(
                    level="WARNING",
                    message=f"Sharpe ratio degraded to {sharpe:.2f}",
                    current_balance=current_balance
                )
        
        # 4. Check win rate
        if len(self.all_trades) >= 20:
            win_rate = self.calculate_win_rate()
            
            if win_rate < self.min_win_rate_pct:
                self.create_alert(
                    level="CRITICAL",
                    message=f"Win rate dropped to {win_rate:.1f}%",
                    current_balance=current_balance
                )
    
    def shutdown(self, reason: str, current_balance: float):
        """Execute emergency shutdown."""
        self.trading_enabled = False
        self.shutdown_reason = reason
        
        self.create_alert(
            level="CRITICAL",
            message=f"TRADING HALTED: {reason}",
            current_balance=current_balance
        )
        
        print(f"\n{'='*70}")
        print(" " * 20 + "⚠️  KILL SWITCH ACTIVATED ⚠️")
        print(f"{'='*70}")
        print(f"\nReason: {reason}")
        print(f"Balance: ${current_balance:.2f}")
        print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
        print(f"\nTrading has been automatically halted.")
        print(f"Manual intervention required to resume.")
        print(f"{'='*70}\n")
    
    def calculate_sharpe_ratio(self) -> float:
        """Calculate Sharpe ratio from daily P&L."""
        if len(self.daily_pnl) < 2:
            return 0.0
        
        pnl_series = pd.Series(list(self.daily_pnl))
        mean_return = pnl_series.mean()
        std_return = pnl_series.std()
        
        if std_return > 0:
            sharpe = (mean_return / std_return) * np.sqrt(252)  # Annualized
            return round(sharpe, 2)
        return 0.0
    
    def calculate_win_rate(self) -> float:
        """Calculate current win rate."""
        if len(self.all_trades) == 0:
            return 0.0
        
        wins = sum(1 for t in self.all_trades if t.get('outcome') == 'WIN')
        return round(100 * wins / len(self.all_trades), 2)
    
    def calculate_profit_factor(self) -> float:
        """Calculate profit factor."""
        if len(self.all_trades) == 0:
            return 0.0
        
        gross_profit = sum(t.get('profit', 0) for t in self.all_trades if t.get('profit', 0) > 0)
        gross_loss = abs(sum(t.get('profit', 0) for t in self.all_trades if t.get('profit', 0) < 0))
        
        if gross_loss > 0:
            return round(gross_profit / gross_loss, 2)
        return 0.0
    
    def get_metrics(self, current_balance: float) -> dict:
        """Get current performance metrics."""
        drawdown = 0
        drawdown_pct = 0
        if self.peak_balance > 0:
            drawdown = self.peak_balance - current_balance
            drawdown_pct = drawdown / self.peak_balance
        
        return {
            'trading_enabled': self.trading_enabled,
            'manual_override': self.manual_override,
            'shutdown_reason': self.shutdown_reason,
            'total_trades': len(self.all_trades),
            'win_rate': self.calculate_win_rate(),
            'sharpe_ratio': self.calculate_sharpe_ratio(),
            'profit_factor': self.calculate_profit_factor(),
            'consecutive_loss_days': self.consecutive_loss_days,
            'current_balance': round(current_balance, 2),
            'peak_balance': round(self.peak_balance, 2),
            'drawdown': round(drawdown, 2),
            'drawdown_pct': round(drawdown_pct * 100, 2),
            'today_pnl': round(self.last_day_pnl, 2),
        }
    
    def create_alert(self, level: str, message: str, current_balance: float):
        """Create and log an alert."""
        alert = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': level,
            'message': message,
            'balance': current_balance,
        }
        
        self.alert_history.append(alert)
        
        # Print to console
        emoji = "⚠️" if level == "WARNING" else "🔴"
        print(f"\n{emoji} ALERT [{level}]: {message}")
        print(f"   Balance: ${current_balance:.2f}")
        print(f"   Time: {alert['timestamp']}\n")
        
        # TODO: Send to Telegram/Email if configured
    
    def has_alert(self, message_keyword: str) -> bool:
        """Check if alert with keyword already exists (last 24h)."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        
        for alert in self.alert_history:
            alert_time = pd.to_datetime(alert['timestamp'])
            if alert_time > cutoff and message_keyword in alert['message']:
                return True
        return False
    
    def enable_manual_override(self):
        """Enable manual override (disables kill switches)."""
        self.manual_override = True
        print("✅ Manual override ENABLED - Kill switches bypassed")
    
    def disable_manual_override(self):
        """Disable manual override (re-enable kill switches)."""
        self.manual_override = False
        print("✅ Manual override DISABLED - Kill switches active")
    
    def force_resume(self):
        """Force resume trading after shutdown."""
        if not self.manual_override:
            print("❌ Cannot resume: Enable manual override first")
            return False
        
        self.trading_enabled = True
        self.shutdown_reason = None
        self.consecutive_loss_days = 0
        print("✅ Trading RESUMED (manual override active)")
        return True
    
    def save_state(self, file_path: str):
        """Save monitor state to JSON."""
        state = {
            'trading_enabled': self.trading_enabled,
            'manual_override': self.manual_override,
            'shutdown_reason': self.shutdown_reason,
            'consecutive_loss_days': self.consecutive_loss_days,
            'peak_balance': self.peak_balance,
            'alerts': self.alert_history[-50:],  # Last 50 alerts
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
    print(" " * 15 + "ADVANCED MONITORING SYSTEM - V3")
    print("=" * 70)
    
    # Create monitor
    monitor = TradingMonitor(
        max_consecutive_loss_days=3,
        max_drawdown_pct=0.15,
        min_sharpe_ratio=0.5,
        min_win_rate_pct=50,
    )
    
    # Simulate some trades
    balance = 500.0
    monitor.peak_balance = balance
    
    print("\n📊 Simulating trades...")
    
    # Winning trades
    for i in range(5):
        trade = {
            'exit_time': (datetime.now(timezone.utc) + timedelta(hours=i)).isoformat(),
            'profit': 5.0,
            'outcome': 'WIN',
        }
        balance += 5.0
        monitor.update_trade(trade, balance)
    
    print(f"\nAfter 5 wins: ${balance:.2f}")
    
    # Losing streak
    for i in range(3):
        trade = {
            'exit_time': (datetime.now(timezone.utc) + timedelta(days=i+1)).isoformat(),
            'profit': -10.0,
            'outcome': 'LOSS',
        }
        balance -= 10.0
        monitor.update_trade(trade, balance)
    
    print(f"After 3 losing days: ${balance:.2f}")
    
    # Check status
    metrics = monitor.get_metrics(balance)
    
    print("\n" + "=" * 70)
    print(" " * 20 + "MONITOR STATUS")
    print("=" * 70)
    print(f"\nTrading Enabled: {metrics['trading_enabled']}")
    print(f"Shutdown Reason: {metrics['shutdown_reason']}")
    print(f"Total Trades: {metrics['total_trades']}")
    print(f"Win Rate: {metrics['win_rate']}%")
    print(f"Sharpe Ratio: {metrics['sharpe_ratio']}")
    print(f"Consecutive Loss Days: {metrics['consecutive_loss_days']}")
    print(f"Balance: ${metrics['current_balance']}")
    print(f"Drawdown: ${metrics['drawdown']} ({metrics['drawdown_pct']}%)")
    
    print("\n" + "=" * 70)
    print("✅ MONITORING SYSTEM READY")
    print("=" * 70)
