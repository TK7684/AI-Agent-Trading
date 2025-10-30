@echo off
echo 🌐 Opening Web Dashboard...
echo ==========================
echo.

:: Open UI
start "" "http://localhost"

:: Open API docs
start "" "http://localhost:8000/docs"

echo ✅ Opened:
echo    - UI: http://localhost
echo    - API docs: http://localhost:8000/docs
echo.
pause
