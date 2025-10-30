@echo off
setlocal EnableExtensions EnableDelayedExpansion

:: ==========================================================
:: 🚀 One-Click Docker Trading Dashboard Launcher (Windows)
:: - Builds and starts the stack
:: - Ensures .env exists with POSTGRES_PASSWORD
:: - Waits for API/UI to be healthy
:: - Opens the browser automatically
:: - Optional: set ENABLE_MONITORING=1 to include Prometheus/Grafana
:: ==========================================================

:: Always run relative to this script's directory
cd /d "%~dp0"

echo.
echo ===============================================
echo 🚀 Launching Docker-based Trading Dashboard...
echo ===============================================
echo.

:: Check Docker installation
where docker >nul 2>&1
if errorlevel 1 (
  echo ❌ Docker is not installed or not in PATH.
  echo    Please install Docker Desktop and try again.
  goto :PAUSE_END
)

:: Detect Docker Compose (v2 "docker compose" preferred, fallback to "docker-compose")
set "COMPOSE_CMD="
docker compose version >nul 2>&1 && (set "COMPOSE_CMD=docker compose")
if not defined COMPOSE_CMD (
  where docker-compose >nul 2>&1
  if errorlevel 1 (
    echo ❌ Docker Compose is not available.
    echo    Update Docker Desktop or install Compose and try again.
    goto :PAUSE_END
  ) else (
    set "COMPOSE_CMD=docker-compose"
  )
)


echo ✅ Using Compose command: %COMPOSE_CMD%

echo.
echo 🔍 Checking Docker engine status...
call :WAIT_DOCKER 60
if errorlevel 1 (
  echo ⏳ Docker engine is not running. Attempting to start Docker Desktop...
  call :START_DOCKER_DESKTOP
  echo ⏳ Waiting for Docker engine to become ready...
  call :WAIT_DOCKER 240
  if errorlevel 1 (
    echo ❌ Docker engine is not available. Please start Docker Desktop and retry.
    echo 👉 Open Docker Desktop manually, wait until it says "Engine running", then re-run this launcher.
    goto :PAUSE_END
  ) else (
    echo ✅ Docker engine is running.
  )
) else (
  echo ✅ Docker engine is running.
)
echo.


:: Ensure required directories exist (used by volumes/logs)
if not exist "logs" mkdir "logs" >nul 2>&1
if not exist "logs\nginx" mkdir "logs\nginx" >nul 2>&1
if not exist "logs\nginx-proxy" mkdir "logs\nginx-proxy" >nul 2>&1

:: Ensure .env exists with a secure POSTGRES_PASSWORD
if not exist ".env" (
  echo 🔐 Creating .env with secure defaults...
  call :GENERATE_PASSWORD
  (
    echo POSTGRES_PASSWORD=!GEN_PASS!
    echo GRAFANA_PASSWORD=admin
  ) > ".env"
) else (
  :: If POSTGRES_PASSWORD is missing, append it
  findstr /B /C:"POSTGRES_PASSWORD=" ".env" >nul 2>&1
  if errorlevel 1 (
    echo 🔐 Adding POSTGRES_PASSWORD to existing .env...
    call :GENERATE_PASSWORD
    >> ".env" echo POSTGRES_PASSWORD=!GEN_PASS!
  )
)

:: Optional monitoring profile (Prometheus/Grafana)
set "PROFILE_ARG="
if /I "%ENABLE_MONITORING%"=="1" (
  set "PROFILE_ARG=--profile monitoring"
  echo 🧩 Monitoring profile enabled: Prometheus and Grafana will be started.
) else (
  echo 🧩 Monitoring profile disabled. Set ENABLE_MONITORING=1 to enable.
)
echo.

:: Build and start the stack
echo 🛠️  Building and starting containers...
%COMPOSE_CMD% -f "docker-compose.trading-dashboard.yml" up -d --build %PROFILE_ARG%
if errorlevel 1 (
  echo ❌ Failed to start containers with Docker Compose.
  goto :PAUSE_END
)

echo.
echo ⏳ Waiting for API to become healthy at http://localhost:8000/health ...
call :WAIT_HTTP "http://localhost:8000/health" 60
if errorlevel 1 (
  echo ⚠️  API did not report healthy within the expected time.
) else (
  echo ✅ API is healthy.
)

echo.
echo ⏳ Waiting for Dashboard UI to become healthy at http://localhost/health ...
call :WAIT_HTTP "http://localhost/health" 60
if errorlevel 1 (
  echo ⚠️  UI did not report healthy within the expected time.
) else (
  echo ✅ UI is healthy.
)

echo.
echo 🌐 Opening the dashboard and API docs in your default browser...
start "" "http://localhost"
start "" "http://localhost:8000/docs"

if /I "%ENABLE_MONITORING%"=="1" (
  echo 🌐 Opening Grafana (monitoring)...
  start "" "http://localhost:3001"
)

echo.
echo 🎉 All set! Your Docker-based trading dashboard is running.
echo    - UI:  http://localhost
echo    - API: http://localhost:8000/docs
if /I "%ENABLE_MONITORING%"=="1" echo    - Grafana: http://localhost:3001
echo.

goto :END



:: -----------------------------

:: Helper: Ensure Docker Desktop is running and engine ready
:START_DOCKER_DESKTOP
set "DOCKER_DESKTOP_EXE="
if exist "%ProgramFiles%\Docker\Docker\Docker Desktop.exe" set "DOCKER_DESKTOP_EXE=%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
if not defined DOCKER_DESKTOP_EXE if exist "%ProgramFiles(x86)%\Docker\Docker\Docker Desktop.exe" set "DOCKER_DESKTOP_EXE=%ProgramFiles(x86)%\Docker\Docker\Docker Desktop.exe"
if not defined DOCKER_DESKTOP_EXE if exist "%LocalAppData%\Docker\Docker Desktop.exe" set "DOCKER_DESKTOP_EXE=%LocalAppData%\Docker\Docker Desktop.exe"
if defined DOCKER_DESKTOP_EXE (
  start "" "%DOCKER_DESKTOP_EXE%"
  exit /b 0
) else (
  echo ⚠️  Could not find Docker Desktop executable automatically.
  echo    Please start Docker Desktop manually.
  exit /b 1
)

:WAIT_DOCKER
set "RETRIES=%~1"
if "%RETRIES%"=="" set "RETRIES=120"
powershell -NoProfile -Command "$limit=%RETRIES%; $ok=$false; for($i=0; $i -lt $limit; $i++){ try{ docker info ^| Out-Null; $ok=$true; break } catch{} Start-Sleep -Seconds 2 }; if($ok){ exit 0 } else { exit 1 }"
exit /b %ERRORLEVEL%

:: -----------------------------
:: Helper: Wait for HTTP endpoint

:: Usage: CALL :WAIT_HTTP "http://url" <retries>
:: Returns ERRORLEVEL 0 on success, 1 on timeout
:WAIT_HTTP
set "URL=%~1"
set "RETRIES=%~2"

powershell -NoProfile -Command "$u='%URL%'; $limit=%RETRIES%; $ok=$false; for($i=0; $i -lt $limit; $i++){ try{ $r=Invoke-WebRequest -Uri $u -UseBasicParsing; if($r.StatusCode -ge 200 -and $r.StatusCode -lt 500){ $ok=$true; break } } catch{} Start-Sleep -Seconds 2 }; if($ok){ exit 0 } else { exit 1 }"
exit /b %ERRORLEVEL%


:: -----------------------------
:: Helper: Generate a 32-char alphanumeric password (PowerShell)
:GENERATE_PASSWORD
for /f "usebackq delims=" %%A in (`powershell -NoProfile -Command "$chars='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'; -join ((1..32) ^| ForEach-Object { $chars[(Get-Random -Max $chars.Length)] })"`) do (
  set "GEN_PASS=%%A"
)
exit /b 0


:PAUSE_END
echo.
pause
goto :END

:END
endlocal
exit /b 0
