================================================================================
TRADING AI V2 - PROFESSIONAL DOCKER DASHBOARD
================================================================================

Complete containerized solution with professional web UI for monitoring and
controlling the V2 EUR/USD breakout strategy deployment.

================================================================================
QUICK START (3 Commands)
================================================================================

1. BUILD THE DOCKER IMAGE:
   docker-compose build

2. START THE CONTAINER:
   docker-compose up -d

3. OPEN IN BROWSER:
   http://localhost

That's it! Professional dashboard is now running.

================================================================================
WHAT YOU GET
================================================================================

PROFESSIONAL WEB DASHBOARD:
- Real-time equity curve visualization
- Live trade table with all metrics
- Automated alert system (drawdown, daily loss, etc.)
- One-click deployment control
- Trade export (CSV)
- Responsive design (mobile, tablet, desktop)

BACKEND API:
- RESTful API for all operations
- Real-time data polling
- Automatic health checks
- Background task scheduling
- Data persistence via volumes

COMPLETE ISOLATION:
- Everything in Docker container
- No dependencies on your system
- Easy to start/stop/remove
- Portable across machines

================================================================================
FULL SETUP INSTRUCTIONS
================================================================================

PREREQUISITES:
- Docker Desktop installed and running
- Port 80 available (http)
- Port 5000 available (API, optional)
- ~2GB free disk space

STEP-BY-STEP:

1. NAVIGATE TO PROJECT:
   cd c:\Users\maram\trading_ai_v75

2. BUILD IMAGE (first time only, ~5 minutes):
   docker-compose build

   Output: Creates 'trading-ai-dashboard' image

3. START CONTAINER:
   docker-compose up -d

   Output: Container starts in background
   Status: Check with 'docker ps'

4. VERIFY RUNNING:
   docker ps

   Should show: trading-ai-dashboard running

5. OPEN DASHBOARD:
   Browser: http://localhost
   Or direct: http://127.0.0.1

6. STOP CONTAINER:
   docker-compose down

   (Container stops, data persists in volumes)

7. RESTART CONTAINER:
   docker-compose up -d

   (Same container, same data, automatically starts)

================================================================================
DOCKER DASHBOARD FEATURES
================================================================================

TOP METRICS (Always Visible):
✓ Deployment Status (NOT_DEPLOYED / DEPLOYED / MONITORING)
✓ Current Equity (starting: $10,000)
✓ Max Drawdown (target: < $2,500, alert: > $3,000)
✓ Win Rate (target: 12-15%)

TABS:

1. OVERVIEW TAB:
   - Key metrics summary
   - Deploy button
   - Refresh button
   - Export button

2. TRADES TAB:
   - Table of all executed trades
   - Entry price, exit price, R-multiple
   - P&L for each trade
   - Win/Loss outcome
   - Current equity per trade
   - Sortable, scrollable

3. CHARTS TAB:
   - Equity curve visualization
   - Real-time updates
   - Smooth line chart
   - Interactive tooltips

4. SETTINGS TAB:
   - Strategy configuration
   - Risk parameters
   - Read-only reference

ALERTS SYSTEM:
✓ CRITICAL: Max DD > $3,000 (RED)
✓ CRITICAL: Daily loss > $600 (RED)
✓ WARNING: Soft stop triggered < $8,500 (YELLOW)
✓ WARNING: Win rate < 10% (YELLOW)
✓ WARNING: Profit factor < 1.5 (YELLOW)

CONTROLS:
- Deploy button: Starts 48-72 hour demo
- Refresh button: Manual data refresh
- Export button: Download trades CSV
- Auto-refresh: Every 5 seconds

================================================================================
HOW TO USE THE DASHBOARD
================================================================================

INITIAL STATE (Nothing running):

1. Click "Deploy" button
2. Confirm in dialog
3. Dashboard shows "DEPLOYED"
4. Wait for first trades (usually within 1 hour)
5. Monitor equity, win rate, drawdown

MONITORING (Demo running):

1. Check "Current Equity" (should grow steady)
2. Monitor "Win Rate" (target: 12-15%)
3. Watch "Max Drawdown" (target: < $2,500)
4. Check Trades tab for detailed activity
5. Review Charts tab for equity curve

ALERTS:

Red Alerts (CRITICAL):
- Action: Investigate immediately
- Possible: System malfunction, data issue
- Next: Check trader logs, manually review

Yellow Alerts (WARNING):
- Action: Monitor closely
- Possible: Expected variance in trading
- Next: Wait 24+ more hours for more data

GREEN (No alerts):
- Action: Keep monitoring
- All metrics: Within expected ranges
- Next: Continue demo, collect more data

AFTER 48-72 HOURS:

1. Collect demo data (30+ trades minimum)
2. Review metrics vs backtest:
   - Actual win rate: 12-15% ✓
   - Actual PF: 1.8-2.2 ✓
   - Actual DD: < $2,500 ✓
3. Decision:
   - Metrics good: Deploy to LIVE
   - Metrics bad: Reoptimize
   - Unclear: Run more demo

================================================================================
TROUBLESHOOTING
================================================================================

DASHBOARD WON'T LOAD:

1. Check if container is running:
   docker ps
   (Should show: trading-ai-dashboard)

2. If not running, start it:
   docker-compose up -d

3. Wait 10 seconds for services to start

4. Try again: http://localhost

5. If still failing:
   docker-compose logs trading-ai
   (Check logs for errors)

NO TRADES APPEARING:

1. Check deployment status:
   - Should show: "DEPLOYED"
   - If not, click Deploy button

2. Wait 1+ hours for first trades
   - EUR/USD hourly
   - No trades if no valid breakouts

3. Check live_trades_log_v2.csv exists:
   docker exec trading-ai-dashboard ls /app/data/results/

4. If missing, check trader is running:
   docker exec trading-ai-dashboard ps aux | grep trader

API NOT RESPONDING:

1. Restart container:
   docker-compose down
   docker-compose up -d

2. Wait 5 seconds

3. Check health:
   curl http://localhost/api/health

4. If failing, check logs:
   docker-compose logs trading-ai

CONTAINER WON'T START:

1. Check Docker Desktop is running

2. Try rebuilding:
   docker-compose build --no-cache
   docker-compose up -d

3. Check disk space: ~2GB required

4. View detailed error:
   docker-compose logs trading-ai

DATA LOSS CONCERNS:

✓ All data persists in Docker volumes
✓ Even if container stops, data remains
✓ Volumes are backed up in ./results/ folder
✓ Can restore by bringing container back up

================================================================================
COMMAND REFERENCE
================================================================================

BUILD IMAGE:
  docker-compose build

START CONTAINER:
  docker-compose up -d

STOP CONTAINER:
  docker-compose down

VIEW LOGS:
  docker-compose logs trading-ai

FOLLOW LOGS (Real-time):
  docker-compose logs -f trading-ai

SHELL INTO CONTAINER:
  docker exec -it trading-ai-dashboard /bin/bash

CHECK RUNNING PROCESSES:
  docker ps

REMOVE EVERYTHING:
  docker-compose down -v

VIEW DATA FILES:
  docker exec trading-ai-dashboard ls -la /app/data/results/

HEALTH CHECK:
  curl http://localhost/api/health

GET STATUS:
  curl http://localhost/api/status

GET ALL TRADES:
  curl http://localhost/api/trades

================================================================================
ARCHITECTURE
================================================================================

CONTAINER STRUCTURE:

┌─────────────────────────────────────────┐
│     Docker Container: trading-ai        │
├─────────────────────────────────────────┤
│                                         │
│  ┌───────────────┐  ┌──────────────┐   │
│  │   Nginx       │  │   Flask      │   │
│  │   (Port 80)   │  │   (Port 5000)│   │
│  │   - Frontend  │  │   - API      │   │
│  │   - Routing   │  │   - Data     │   │
│  └───────────────┘  └──────────────┘   │
│          │                  │           │
│          └──────┬───────────┘           │
│                 │                       │
│          ┌──────▼──────┐                │
│          │    Files    │                │
│          ├─────────────┤                │
│          │ app.py      │                │
│          │ trades.csv  │                │
│          │ strategy.py │                │
│          └─────────────┘                │
│                                         │
└─────────────────────────────────────────┘
        │              │
        └──────┬───────┘
               │
    ┌──────────▼──────────┐
    │  Your Computer      │
    │  Port 80 → Nginx    │
    │  Port 5000 → Flask  │
    │  ./results → Data   │
    └─────────────────────┘

VOLUME MOUNTS:

./results/               ← Trade logs, status, state
./backtests/            ← Strategy code
trading-ai-data         ← Docker internal volume

DATA FLOW:

Browser (http://localhost)
   │
   ├─→ Nginx (serves React UI)
   │
   └─→ Flask API (/api/*)
       │
       ├─→ Read: live_trades_log_v2.csv
       ├─→ Read: trader_state_v2.json
       ├─→ Write: deployment_status.json
       │
       └─→ Execute: deploy_complete.py

================================================================================
PERFORMANCE & RESOURCES
================================================================================

CONTAINER RESOURCE USAGE:

Memory: ~200-500 MB (depends on trade data size)
CPU: ~5-20% (mostly idle, spikes during API calls)
Disk: ~500 MB (image) + trade data

OPTIMIZATION TIPS:

1. If slow, increase Docker resources:
   - Docker Desktop Settings
   - Resources → Memory: 2-4GB
   - CPU: 2-4 cores

2. Clear old trades periodically:
   - docker exec trading-ai-dashboard \
     rm /app/data/results/tmp_mc_*.csv

3. Monitor container:
   - docker stats trading-ai-dashboard

================================================================================
SECURITY NOTES
================================================================================

⚠️  This dashboard is for LOCAL development only.

For production deployment:
❌ Don't expose port 80 to internet
❌ Use authentication/SSL
❌ Don't put API keys in container
❌ Use environment variables for secrets

For local use (safe):
✓ Firewall blocks external access by default
✓ localhost only accessible from your PC
✓ Data never leaves your machine

================================================================================
NEXT STEPS
================================================================================

1. START CONTAINER:
   docker-compose up -d

2. OPEN BROWSER:
   http://localhost

3. CLICK "DEPLOY" BUTTON

4. MONITOR FOR 48-72 HOURS

5. ANALYZE RESULTS

6. DECIDE: LIVE or ITERATE

That's it! No CLI interactions needed. Everything through the professional UI.

================================================================================
SUPPORT
================================================================================

If something doesn't work:

1. Check logs: docker-compose logs trading-ai
2. Restart container: docker-compose restart
3. Rebuild image: docker-compose build --no-cache
4. Check Docker Desktop is running
5. Verify ports 80 and 5000 are free

Questions?
- Review MONITORING_GUIDE.txt for metrics explanation
- Check docker-compose.yml for configuration
- View docker_app/ folder for source code
