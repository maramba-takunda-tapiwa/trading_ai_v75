# Trading AI V2 - System Integration & Deployment Plan

## Current Status ✅

### What's Working
- ✅ Docker container running (trading-ai-dashboard)
- ✅ Flask API backend alive (http://localhost:5000)
- ✅ Nginx web server active
- ✅ React frontend available (http://localhost)
- ✅ /api/health returning 200 OK
- ✅ All 12 API endpoints defined
- ✅ Professional Material-UI dashboard ready

### What Needs to Happen
The system is now a **full-stack web application**, but it needs to be **connected to the live trader**. Currently:
- Dashboard shows placeholders (no real trades yet)
- Deploy button doesn't actually start the trader
- No integration with `live_trader_saxo_v2.py`

---

## Phase 1: API Integration (IMMEDIATE - Next 1-2 hours)

### Goal
Make the `/api/deploy` endpoint actually start `live_trader_saxo_v2.py` and feed real trades to the dashboard.

### Step 1.1: Update Flask App to Launch Trader

**File:** `docker_app/app.py`

**Change Required:** The `/api/deploy` POST endpoint needs to:

```python
@app.route('/api/deploy', methods=['POST'])
def deploy():
    """Start live trader deployment"""
    try:
        status = get_status()
        
        if status.get('deployment_status') == 'DEPLOYED':
            return jsonify({'error': 'Already deployed'}), 400
        
        # Start live_trader_saxo_v2.py in background thread
        def run_trader():
            try:
                # Run the trader script
                result = subprocess.run([
                    'python',
                    '/app/data/backtests/live_trader_saxo_v2.py'
                ], capture_output=True, text=True)
                logger.info(f"Trader completed: {result.stdout}")
            except Exception as e:
                logger.error(f"Trader error: {e}")
        
        thread = threading.Thread(target=run_trader, daemon=True)
        thread.start()
        
        # Update status
        status_update = {
            'deployment_status': 'DEPLOYED',
            'phase': 'MONITORING',
            'deployment_time': datetime.now(timezone.utc).isoformat(),
            'expected_completion': (datetime.now(timezone.utc) + timedelta(hours=72)).isoformat(),
            'tasks_completed': {'trader_started': True},
        }
        
        with open(STATUS_FILE, 'w') as f:
            json.dump(status_update, f)
        
        return jsonify({'status': 'DEPLOYED', 'message': 'Trader started'}), 200
    except Exception as e:
        logger.error(f"Deploy error: {e}")
        return jsonify({'error': str(e)}), 500
```

**Key Logic:**
- Thread off the trader so Flask doesn't block
- Update deployment status file
- Dashboard polls this file every 5 seconds

---

### Step 1.2: Verify live_trader_saxo_v2.py Writes Correct CSV

**File:** `backtests/live_trader_saxo_v2.py`

**Check:** This file must write to `/app/data/results/live_trades_log_v2.csv` with:
- Column: `trade_time` (timestamp)
- Column: `entry_price` 
- Column: `exit_price`
- Column: `pnl` (profit/loss)
- Column: `outcome` (win/loss)
- Column: `r_multiple` (risk/reward)
- Column: `equity` (account balance after trade)

**Why:** Flask reads this CSV and sends to dashboard every 5 seconds.

**Action:**
1. Check what columns live_trader_saxo_v2.py currently writes
2. Add missing columns if needed
3. Ensure it writes to correct path inside container

---

### Step 1.3: Set Up Saxo Credentials

**Problem:** Saxo demo trading needs credentials (app_id, access_token, account_id)

**Solution Options:**

**Option A: Environment Variables (Recommended)**
```bash
docker-compose down
# Edit docker-compose.yml to add environment:
environment:
  - SAXO_APP_ID=your_app_id
  - SAXO_ACCESS_TOKEN=your_token
  - SAXO_ACCOUNT_ID=your_account_id
docker-compose up -d
```

**Option B: Config File (More Secure)**
- Create `/app/data/saxo_config.json`
- Mount as volume in docker-compose.yml
- Read in live_trader_saxo_v2.py

**Option C: Flask Endpoint**
- `/api/configure` POST endpoint to set credentials
- Store in environment or file
- Use by trader

**Recommendation:** Use **Option C** (API endpoint) so you can:
1. Start container
2. Go to dashboard
3. Add credentials via Settings tab
4. Click Deploy
5. Trading starts automatically

---

## Phase 2: Real-Time Updates (2-3 hours)

### Goal
Dashboard shows live metrics that update every 5 seconds as trades happen.

### Step 2.1: Implement Trade Polling

Flask API already has:
- `/api/trades` - Returns all trades + metrics
- `/api/dashboard` - Returns everything combined

Dashboard (React) already polls every 5 seconds.

**Test:** 
```bash
curl http://localhost/api/trades
```

Should return JSON with trades array and metrics.

### Step 2.2: Real-Time Equity Curve

The `/api/chart-data` endpoint must return:
```json
{
  "times": ["2025-11-01 10:00", "2025-11-01 11:00", ...],
  "equities": [10000, 10050, 9980, ...]
}
```

This is already implemented in Flask app. Just needs data from CSV.

---

## Phase 3: Safety Features (1-2 hours)

### Goal
Add automatic stopping on risks, prevent account disaster.

### Step 3.1: Create `/api/stop` Endpoint

```python
@app.route('/api/stop', methods=['POST'])
def stop_deployment():
    """Emergency stop the trader"""
    try:
        # Kill trader process
        # Write stop signal to state file
        # Return status
        return jsonify({'status': 'STOPPED'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

### Step 3.2: Implement Max Drawdown Check

```python
def check_drawdown():
    """Check if max drawdown exceeded"""
    df = pd.read_csv(LOG_FILE)
    if len(df) > 0:
        max_dd = (df['equity'].max() - df['equity'].min())
        if max_dd > 3000:  # Hard limit
            stop_deployment()
            create_alert('CRITICAL', f'Max DD ${max_dd} exceeded limit')
```

---

## Phase 4: Deployment Workflow (1 hour)

### The Complete User Flow

1. **Open Dashboard**
   ```
   Browser: http://localhost
   ```

2. **Configure (if first time)**
   - Click "Settings" tab
   - Enter Saxo credentials
   - Click "Save Configuration"

3. **Deploy**
   - Click "Deploy" button (big green button)
   - Confirm dialog
   - Status changes to "DEPLOYED"
   - Dashboard starts showing live metrics

4. **Monitor**
   - Watch equity line update
   - View trades as they happen
   - Check alerts for warnings
   - Review win rate, drawdown, profit factor

5. **Stop (if needed)**
   - Click "Stop" button (red button)
   - Trader halts
   - Trades stop

6. **Export Results**
   - After 48-72 hours
   - Click "Export" button
   - Download trades CSV
   - Analyze in Excel/Python

---

## Phase 5: Packaging for Daily Use (2 hours)

### Goal
Make it so easy that you just click one icon and dashboard opens.

### Step 5.1: Windows Startup Script

**File:** `START_DASHBOARD.bat`
```batch
@echo off
cd c:\Users\maram\trading_ai_v75
docker-compose up -d
timeout /t 5
start http://localhost
```

**Location:** Desktop or Start Menu

### Step 5.2: Stop Script

**File:** `STOP_DASHBOARD.bat`
```batch
@echo off
docker-compose down
echo Dashboard stopped
pause
```

### Step 5.3: Auto-Backup

**File:** `BACKUP_RESULTS.bat`
```batch
@echo off
REM Copy results daily
xcopy results c:\Users\maram\trading_ai_backups\%date:~-10% /e /y
echo Backup complete
```

---

## Implementation Roadmap

### TODAY (Next 3-4 hours)

1. **Update Flask `/api/deploy` endpoint** ← START HERE
   - Make it launch live_trader_saxo_v2.py
   - Update status file
   - Return success/error

2. **Test with mock trader**
   - Create dummy trader that writes fake CSV
   - Verify dashboard displays it
   - Test real-time updates

3. **Create Settings API**
   - `/api/configure` endpoint
   - Store Saxo credentials
   - Make them available to trader

### TOMORROW (Next 3-4 hours)

4. **Integrate real Saxo trader**
   - Pass credentials to live_trader_saxo_v2.py
   - Test with small position
   - Monitor for 1 hour

5. **Add safety features**
   - Max drawdown kill switch
   - Daily loss limit
   - Email alerts

6. **Full end-to-end test**
   - Deploy via dashboard
   - Watch one trade execute
   - Verify all metrics update
   - Stop cleanly

### SUNDAY (Final polish - 2 hours)

7. **Create startup scripts**
   - Windows batch files
   - Auto-backup setup
   - README for daily use

8. **Documentation**
   - How to add credentials
   - How to deploy
   - How to read dashboard
   - Emergency procedures

---

## Technical Checklist

### Before Live Trading
- [ ] `/api/deploy` endpoint launches trader
- [ ] live_trader_saxo_v2.py writes correct CSV format
- [ ] Dashboard reads CSV and displays metrics
- [ ] Real-time polling works (every 5 seconds)
- [ ] Equity chart updates live
- [ ] Trade table shows new trades
- [ ] Alerts trigger on drawdown
- [ ] `/api/stop` kills trader cleanly
- [ ] Credentials stored securely
- [ ] Test with $1 risk per trade (minimal)

### User Experience Checklist
- [ ] Dashboard loads in <2 seconds
- [ ] Deploy button is obvious
- [ ] Status updates in real-time
- [ ] No error messages for normal operation
- [ ] Export works
- [ ] Startup/stop scripts are one-click

---

## Key Files to Modify

| File | Change | Priority | Effort |
|------|--------|----------|--------|
| `docker_app/app.py` | `/api/deploy` endpoint logic | CRITICAL | 30 min |
| `backtests/live_trader_saxo_v2.py` | Write to correct CSV path | CRITICAL | 15 min |
| `docker_app/app.py` | `/api/configure` for credentials | HIGH | 20 min |
| `docker_app/app.py` | Safety check functions | HIGH | 20 min |
| `Dockerfile` | Add environment variables | MEDIUM | 10 min |
| `docker-compose.yml` | Volume mounts for credentials | MEDIUM | 10 min |
| `START_DASHBOARD.bat` | Create startup script | LOW | 5 min |
| `DEPLOYMENT_WORKFLOW.md` | User guide | LOW | 15 min |

---

## Success Criteria

✅ **Phase 1 Complete:** Dashboard can launch trader via Deploy button
✅ **Phase 2 Complete:** Live trades appear on dashboard in real-time
✅ **Phase 3 Complete:** Safety features prevent catastrophic loss
✅ **Phase 4 Complete:** User can deploy, monitor, export in <5 clicks
✅ **Phase 5 Complete:** Desktop shortcuts make it one-click easy

---

## Next Action

**I recommend we start with Step 1.1 NOW:**

Update the Flask `/api/deploy` endpoint to actually launch the trader. This is the critical connection point that makes everything else work.

Once that's done:
- Test it manually: click "Deploy" button
- Watch for "DEPLOYED" status
- Check that trader starts

Then move to real credentials and safety features.

**Ready to start? 🚀**
