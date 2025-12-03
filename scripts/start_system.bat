@echo off
echo =============================================
echo    AUTOMATED TRADING SYSTEM LAUNCHER
echo =============================================
echo.

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python 3.11+ and try again
    pause
    exit /b 1
)

REM Check if in correct directory
if not exist "auto_trading_system" (
    echo ❌ Please run this script from the "AI Agent Trading" directory
    pause
    exit /b 1
)

REM Load environment variables
if exist ".env" (
    echo ✅ Loading environment variables from .env
    for /f "tokens=1,2 delims==" %%a in (.env) do (
        if not "%%a"=="" if not "%%b"=="" (
            set "%%a=%%b"
        )
    )
) else (
    echo ⚠️  No .env file found, using default settings
)

REM Check API Keys
echo 🔑 Checking API Keys...
if "%OPENAI_API_KEY%"=="" (
    echo ❌ OPENAI_API_KEY not set
    set MISSING_KEYS=1
) else (
    echo ✅ OpenAI API Key configured
)

if "%GEMINI_API_KEY%"=="" (
    echo ❌ GEMINI_API_KEY not set
    set MISSING_KEYS=1
) else (
    echo ✅ Gemini API Key configured
)

if defined MISSING_KEYS (
    echo.
    echo ⚠️  Some API keys are missing. Please set them in your .env file
    echo    OPENAI_API_KEY=your_openai_key_here
    echo    GEMINI_API_KEY=your_gemini_key_here
    echo.
    set /p CONTINUE="Continue anyway? (y/n): "
    if /i not "!CONTINUE!"=="y" exit /b 1
)

REM Choose mode
echo.
echo 🚀 Choose Trading Mode:
echo 1. Demo Mode (Simulated data, safe for testing)
echo 2. Dry Run Mode (Analysis only, no trades)
echo 3. Live Trading Mode (REAL MONEY - use with caution)
echo 4. Simulation Mode (Advanced mock data)
echo 5. Exit
echo.

set /p MODE="Select mode (1-5): "

if "%MODE%"=="1" (
    set MODE_FLAG=--demo
    set MODE_NAME=Demo Mode
) else if "%MODE%"=="2" (
    set MODE_FLAG=--dry-run
    set MODE_NAME=Dry Run Mode
) else if "%MODE%"=="3" (
    set MODE_FLAG=
    set MODE_NAME=Live Trading Mode
) else if "%MODE%"=="4" (
    set MODE_FLAG=--simulation
    set MODE_NAME=Simulation Mode
) else if "%MODE%"=="5" (
    echo 👋 Goodbye!
    exit /b 0
) else (
    echo ❌ Invalid selection
    pause
    exit /b 1
)

REM Confirmation for live trading
if "%MODE%"=="3" (
    echo.
    echo 🚨 🚨 🚨 WARNING 🚨 🚨 🚨
    echo You are about to start LIVE TRADING with REAL MONEY
    echo This will execute actual trades using your configured APIs
    echo.
    echo Please confirm:
    echo - API keys are correct
    echo - Trading limits are set appropriately
    echo - Risk management is configured
    echo - You understand the financial risks involved
    echo.
    set /p CONFIRM="Type 'LIVE' to confirm live trading: "
    if /i not "!CONFIRM!"=="LIVE" (
        echo ❌ Live trading cancelled
        pause
        exit /b 1
    )
)

REM Start the system
echo.
echo 🚀 Starting Automated Trading System...
echo Mode: %MODE_NAME%
echo.

REM Create logs directory if it doesn't exist
if not exist "logs" mkdir logs

REM Start the Python application
python auto_trading_system/start_automated_trading.py %MODE_FLAG%

REM Check exit code
if errorlevel 1 (
    echo.
    echo ❌ System exited with error
    echo Check the logs for more information
) else (
    echo.
    echo ✅ System stopped successfully
)

echo.
pause
