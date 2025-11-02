# trading_ai_v75 — how to run

Basic steps to reproduce experiments and optimization in this repository.

Prereqs
- Python 3.8+ with pandas, numpy, matplotlib

Quick commands (PowerShell)

Convert JSON candles to CSV (if needed):
```powershell
py .\backtests\json_to_csv.py
```

Run a single forward test (uses defaults but accepts params):
```powershell
py .\backtests\forward_test.py
```

Run full optimization + simple walk-forward validation (saves results in `results/`):
```powershell
py .\backtests\run_optimization.py
```

Run tests (pytest):
```powershell
py -m pytest
```

Outputs
- `results/optimization_results.csv` — grid results
- `results/validation_results.csv` — OOS validation for best config
- `results/best_config_trades.csv` — trades log for best config OOS

Notes
- The forward test assumes CSV with columns `time,open,high,low,close` in `data/`.
- The optimization script may take a few minutes depending on grid size.
