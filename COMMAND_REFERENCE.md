# 🛠️ COMMAND REFERENCE

## DOCKER COMMANDS

### Check System Status
```bash
docker-compose ps
```
Output: Shows if container is running and healthy

### View Live Logs
```bash
docker-compose logs --follow
```
Shows real-time trader output and API calls

### View Last N Lines
```bash
docker-compose logs --tail=100
```
Shows last 100 lines of logs

### Restart System
```bash
docker-compose down
docker-compose up -d
```
Complete restart if needed

### Rebuild (if you make code changes)
```bash
docker-compose build --no-cache
docker-compose down
docker-compose up -d
```

---

## API COMMANDS

### Check System Health
```bash
curl http://localhost/api/health
```

### Get Full Dashboard Status
```bash
curl http://localhost/api/dashboard | jq
```

### Get Current Trades
```bash
curl http://localhost/api/trades | jq
```

### Get Chart Data
```bash
curl http://localhost/api/chart-data | jq
```

### Get Trader State
```bash
curl http://localhost/api/trader-state | jq
```

### Deploy Trader
```bash
curl -X POST http://localhost/api/deploy
```

### Stop Trader
```bash
curl -X POST http://localhost/api/stop
```

---

## FILE INSPECTION

### View Live Trades CSV
```bash
cat results/live_trades_log_v2.csv
```

### View Last 10 Trades
```bash
tail -10 results/live_trades_log_v2.csv
```

### View Trader State
```bash
cat results/trader_state_v2.json | jq
```

### View Saxo Credentials
```bash
cat results/saxo_config.json
```
(Don't share these!)

### View Historical Data
```bash
head -5 data/eurusd_candles.csv
```

---

## PYTHON COMMANDS

### Run Strategy Backtest (local)
```bash
cd c:\Users\maram\trading_ai_v75\backtests
python backtest_eurusd.py
```

### Check Saxo Connection (local)
```bash
python saxo_auth.py
```

### Run Monte Carlo Analysis (local)
```bash
python monte_carlo_validate.py
```

---

## BROWSER SHORTCUTS

**Dashboard**: http://localhost

- **F5** = Refresh dashboard
- **Ctrl+Shift+J** = Open browser console (see errors)
- **F12** = Developer tools

---

## USEFUL GREP COMMANDS

### Find all trades in logs
```bash
docker-compose logs | grep "WIN\|LOSS"
```

### Find API calls
```bash
docker-compose logs | grep "POST\|GET"
```

### Find errors
```bash
docker-compose logs | grep "ERROR\|Exception"
```

### Find trader activity
```bash
docker-compose logs | grep "HEARTBEAT\|Trade"
```

---

## EMERGENCY PROCEDURES

### If Dashboard Won't Load
```bash
docker-compose restart
# Wait 10 seconds
# Refresh browser
```

### If Trader Crashed
```bash
docker-compose logs --tail=50
# Check error message
curl -X POST http://localhost/api/deploy
# Restart deployment
```

### If Container Won't Start
```bash
docker-compose down
docker ps -a  # See all containers
docker rm trading-ai-dashboard  # Remove old
docker-compose up -d  # Restart
```

### Full Reset (Nuclear Option)
```bash
docker-compose down -v
docker system prune -a
docker-compose up -d
```
(Warning: This deletes all data!)

---

## MONITORING SCRIPT

Save as `monitor.sh`:
```bash
#!/bin/bash
while true; do
  clear
  echo "=== SYSTEM STATUS ==="
  docker-compose ps
  echo ""
  echo "=== LAST TRADES ==="
  tail -3 results/live_trades_log_v2.csv
  echo ""
  echo "=== LATEST LOGS ==="
  docker-compose logs --tail=5
  sleep 5
done
```

Run with: `bash monitor.sh`

---

## PERFORMANCE TIPS

### Lighter Logs (less verbosity)
In `docker_app/app.py`, change:
```python
logging.basicConfig(level=logging.WARNING)
```

### Faster Polling
Trader polls by default every 60 seconds. To check more often:
```bash
# In deployment command, change interval
--interval 30  # 30 seconds instead of 60
```

### Reduce Storage
Old CSV files build up. Archive weekly:
```bash
cp results/live_trades_log_v2.csv results/backup_$(date +%Y%m%d).csv
rm results/live_trades_log_v2.csv
```

---

## SWITCHING FROM DEMO TO LIVE

**Step 1**: Verify credentials
```bash
cat results/saxo_config.json
```

**Step 2**: Edit trader config
```bash
# Edit: backtests/live_trader_saxo_v2_demo.py
# Change: DEMO_MODE = True → False
```

**Step 3**: Rebuild
```bash
docker-compose build --no-cache
docker-compose down
docker-compose up -d
```

**Step 4**: Deploy
```bash
curl -X POST http://localhost/api/deploy
```

---

## TROUBLESHOOTING MATRIX

| Problem | Solution |
|---------|----------|
| No trades | Check logs: `docker-compose logs --tail=50` |
| Charts empty | Refresh: `F5` in browser |
| API not responding | Restart: `docker-compose restart` |
| High CPU | Check: `docker stats` |
| File permission error | Run: `docker-compose up -d --force-recreate` |
| Can't connect to Saxo | Check internet, verify credentials |
| Trader crashes | Check logs for error details |

---

## NOTES FOR MONDAY

1. **Dashboard runs on port 80** - Use http://localhost
2. **API runs on port 5000** - For direct API calls
3. **Trades update every 1-5 seconds** - Depends on trade frequency
4. **CSV file grows** - Each trade adds one line
5. **Equity curve is your main metric** - Watch if it goes up

---

Good luck on Monday! 🚀
