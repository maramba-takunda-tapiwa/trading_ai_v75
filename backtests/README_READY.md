This folder contains scripts for backtesting and a demo Saxo live trader.

Summary of "ready" changes applied:

- Monte Carlo:
  - `monte_carlo.py` now accepts CLI args `--sims` and `--block-size` and uses timezone-safe parsing.
  - Run with: `py monte_carlo.py --sims 1000 --block-size 24` (may take hours depending on CPU).

- Live trader (`live_trader_saxo.py`):
  - Persistent state saved to `results/trader_state.json` to resume balances and logs.
  - Global MAX_DRAWDOWN (default 30%) stops new trades and sends Slack alerts.
  - Daily loss freeze alerts and persistent state.
  - Max concurrent trades enforced and multiple open trades supported.
  - Optional Slack alerts via `SLACK_WEBHOOK` variable in the script (set your webhook URL there or set externally).
  - Streaming shim `saxo_stream.py` included — if you provide streaming credentials, extend that module to enable streaming.

Quick commands

Run a short smoke Monte Carlo (50 sims):

```powershell
cd backtests; py monte_carlo.py --sims 50 --block-size 24
```

Run a long Monte Carlo (1000 sims):

```powershell
cd backtests; py monte_carlo.py --sims 1000 --block-size 24
```

Start the demo Saxo trader (ensure credentials set in `live_trader_saxo.py` and `ACCOUNT_KEY` can be fetched):

```powershell
cd backtests; py live_trader_saxo.py
```

Notes and safety

- The live trader places market orders on the Saxo demo gateway. Keep `ACCOUNT_KEY`, `TOKEN`, and other credentials secret.
- Set `SLACK_WEBHOOK` in `live_trader_saxo.py` if you want instant alerts.
- If you want me to run more automation (e.g., set up a Windows service / scheduled job, add Slack secrets via environment variables, or extend streaming with websockets), tell me and I'll implement it next.
