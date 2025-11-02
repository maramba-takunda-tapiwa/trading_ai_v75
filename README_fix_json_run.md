Purpose: helper scripts to run `backtests/json_to_csv.py` from the correct working directory so its relative paths (../data/...) resolve without changing your Python code.

Files added:
- `run_json_to_csv.ps1` - PowerShell wrapper. Run from repository root like:

    .\run_json_to_csv.ps1

- `run_json_to_csv.bat` - Windows batch wrapper. Run from repository root like:

    .\run_json_to_csv.bat

If you prefer to run directly, open a shell and:

    cd backtests; python json_to_csv.py
