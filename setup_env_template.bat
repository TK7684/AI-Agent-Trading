@echo off
echo 🚀 AI Trading Agent - Environment Setup
echo ═════════════════════════════════════════
echo.

echo 🧠 Setting up AI/LLM API Keys...
echo.

REM AI APIs
set /p OPENAI_KEY="Enter OpenAI API Key (sk-...): "
if not "%OPENAI_KEY%"=="" (
    set OPENAI_API_KEY=%OPENAI_KEY%
    echo ✅ OpenAI API key set
) else (
    echo ⚠️  OpenAI API key skipped
)

echo.
set /p ANTHROPIC_KEY="Enter Anthropic API Key (sk-ant-...): "
if not "%ANTHROPIC_KEY%"=="" (
    set ANTHROPIC_API_KEY=%ANTHROPIC_KEY%
    echo ✅ Anthropic API key set
) else (
    echo ⚠️  Anthropic API key skipped
)

echo.
set /p GOOGLE_KEY="Enter Google Gemini API Key (AIza...): "
if not "%GOOGLE_KEY%"=="" (
    set GOOGLE_API_KEY=%GOOGLE_KEY%
    echo ✅ Google Gemini API key set
) else (
    echo ⚠️  Google Gemini API key skipped
)

echo.
echo 💹 Setting up Trading API Keys...
echo.

set /p BINANCE_API="Enter Binance API Key (optional): "
if not "%BINANCE_API%"=="" (
    set BINANCE_API_KEY=%BINANCE_API%
    echo ✅ Binance API key set
    
    set /p BINANCE_SECRET="Enter Binance Secret Key: "
    if not "%BINANCE_SECRET%"=="" (
        set BINANCE_SECRET_KEY=%BINANCE_SECRET%
        echo ✅ Binance Secret key set
    )
) else (
    echo ⚠️  Binance API keys skipped (paper trading only)
)

echo.
echo 🔐 Generating Security Keys...

REM Generate random secrets
set JWT_SECRET=jwt-trading-secret-%RANDOM%-%RANDOM%-2024
set SECRET_KEY=system-trading-secret-%RANDOM%-%RANDOM%-2024

echo ✅ JWT Secret generated
echo ✅ System Secret generated

echo.
echo 🌍 Setting Environment...
set ENVIRONMENT=development
set DEBUG=true

echo ✅ Environment set to development
echo ✅ Debug mode enabled

echo.
echo 📝 Creating .env file...

(
echo # AI Trading Agent Environment Configuration
echo # Generated on %DATE% at %TIME%
echo.
echo # AI/LLM APIs
echo OPENAI_API_KEY=%OPENAI_API_KEY%
echo ANTHROPIC_API_KEY=%ANTHROPIC_API_KEY%
echo GOOGLE_API_KEY=%GOOGLE_API_KEY%
echo.
echo # Trading APIs
echo BINANCE_API_KEY=%BINANCE_API_KEY%
echo BINANCE_SECRET_KEY=%BINANCE_SECRET_KEY%
echo.
echo # Security
echo JWT_SECRET=%JWT_SECRET%
echo SECRET_KEY=%SECRET_KEY%
echo.
echo # Environment
echo ENVIRONMENT=%ENVIRONMENT%
echo DEBUG=%DEBUG%
echo.
echo # Database ^(Local SQLite^)
echo DB_HOST=localhost
echo DB_PORT=5432
echo DB_NAME=trading_db
echo.
echo # Redis ^(Optional^)
echo REDIS_HOST=localhost
echo REDIS_PORT=6379
) > .env

echo ✅ .env file created successfully!

echo.
echo 🎊 SETUP COMPLETE!
echo ═══════════════════════════════════════════════════════════════
echo.
echo 🧠 AI Models Ready:
if not "%OPENAI_API_KEY%"=="" echo    ✅ OpenAI GPT-4 Turbo
if not "%ANTHROPIC_API_KEY%"=="" echo    ✅ Anthropic Claude
if not "%GOOGLE_API_KEY%"=="" echo    ✅ Google Gemini
echo.
echo 💹 Trading Ready:
if not "%BINANCE_API_KEY%"=="" (
    echo    ✅ Binance Live Trading
) else (
    echo    📊 Paper Trading Mode Only
)
echo.
echo 🔐 Security Configured:
echo    ✅ JWT Authentication
echo    ✅ API Key Protection
echo.
echo 🚀 Next Steps:
echo    1. Double-click LAUNCH_TRADINGVIEW_DASHBOARD.bat
echo    2. Start with Paper Trading mode
echo    3. Monitor AI analysis and signals
echo    4. Gradually move to live trading
echo.
echo 💡 Pro Tips:
echo    - Keep your API keys secure
echo    - Start with small amounts
echo    - Monitor costs and usage
echo    - Check system performance regularly
echo.
echo Your AI Trading Agent is ready to make money! 🤖💰
echo ═══════════════════════════════════════════════════════════════

pause
