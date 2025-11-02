# ⚡ QUICK REFERENCE - MONDAY MORNING

## 🟢 SYSTEM STATUS: LIVE AND READY

**Dashboard**: http://localhost  
**Current Mode**: Demo (waiting for markets)  
**Trader**: Running 24/7 in Docker  
**Next Action**: Market open Monday

---

## 📊 LIVE DASHBOARD TABS

### Overview
- Deployment Status
- Current Balance
- Trader State
- System Metrics

### Trades
- All executed trades
- Entry/exit prices
- P&L per trade
- Win rate, profit factor

### Charts
- **Equity Curve**: Your balance over time (updates live)
- **Visual**: Green for profits, red for losses

### Settings
- Save Saxo credentials (already saved)
- View current config
- System info

---

## 🎯 WHAT TO WATCH ON MONDAY

**Market Opens** → Trader connects to Saxo API  
**Every Hour** → Strategy evaluates EUR/USD setup  
**Signal Detected** → Trade placed automatically  
**Real-Time Dashboard** → See P&L update live  
**Trade Closes** → Equity curve advances  

---

## 🔍 MONITORING CHECKLIST

- [ ] Dashboard loads without errors
- [ ] Trades appear in Trades tab
- [ ] Charts show equity curve changing
- [ ] Metrics update (win rate, profit factor)
- [ ] No alerts or errors

---

## 🆘 IF SOMETHING'S WRONG

**Open terminal**:
```bash
docker-compose logs --tail=50
```

**See last 50 trader output lines**

---

## 💾 IMPORTANT FILES

- **Live trades**: `results/live_trades_log_v2.csv`
- **Trader state**: `results/trader_state_v2.json`
- **Credentials**: `results/saxo_config.json`
- **Historical data**: `data/eurusd_candles.csv`

---

## 📈 EXPECTED METRICS

- **Starting Balance**: $10,000
- **Win Rate Target**: 70%+
- **Profit Factor**: 1.82+
- **Max Drawdown**: $3,000 limit
- **Daily Loss**: $600 limit

---

## 🚀 YOU'RE READY!

✅ System deployed  
✅ Credentials saved  
✅ Dashboard working  
✅ Demo trades flowing  
✅ Just wait for Monday!

Good luck! 🎯
