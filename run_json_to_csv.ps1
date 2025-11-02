try {
    Push-Location -Path (Join-Path $PSScriptRoot 'backtests')
    python .\json_to_csv.py
} finally {
    Pop-Location
}