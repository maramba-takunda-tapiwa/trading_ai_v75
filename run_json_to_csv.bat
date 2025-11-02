@echo off
pushd "%~dp0backtests"
python json_to_csv.py
popd
