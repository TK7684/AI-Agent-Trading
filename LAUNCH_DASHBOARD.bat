@echo off
cd /d "%~dp0"

echo 🚀 Starting Desktop Trading Dashboard...
echo.

:: Try Poetry first (preferred)
poetry run python trading_dashboard.py
if %ERRORLEVEL% EQU 0 goto :END

:: Fallback to python -m if Poetry fails
python -m trading_dashboard.py

:END
pause
```
