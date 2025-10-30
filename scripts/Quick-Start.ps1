<#
.SYNOPSIS
    Quick start trading system (development mode)

.DESCRIPTION
    Starts the trading system services that don't require database initialization.
    Useful for testing the native deployment setup.

.EXAMPLE
    .\Quick-Start.ps1
#>

$ErrorActionPreference = "Stop"

function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }

Write-Info "╔════════════════════════════════════════════════════════════╗"
Write-Info "║                                                            ║"
Write-Info "║        🚀 TRADING SYSTEM - QUICK START (DEV MODE) 🚀       ║"
Write-Info "║                                                            ║"
Write-Info "╚════════════════════════════════════════════════════════════╝"
Write-Host ""

Write-Info "This will start the trading dashboard and API in development mode."
Write-Info "Database services will be skipped for now."
Write-Host ""

# Check prerequisites
Write-Info "Checking prerequisites..."

if (-not (Get-Command poetry -ErrorAction SilentlyContinue)) {
    Write-Warning "Poetry not found. Please install Poetry first."
    exit 1
}

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Warning "Node.js not found. Please install Node.js first."
    exit 1
}

Write-Success "✓ Prerequisites OK"
Write-Host ""

# Start API in background
Write-Info "Starting Trading API..."
$apiJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    poetry run uvicorn apps.trading_api.main:app --host 0.0.0.0 --port 8000 --reload
}

Write-Success "✓ API starting (Job ID: $($apiJob.Id))"
Start-Sleep -Seconds 5

# Check if API is responding
Write-Info "Waiting for API to be ready..."
$maxAttempts = 10
$attempt = 0
$apiReady = $false

while ($attempt -lt $maxAttempts -and -not $apiReady) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            $apiReady = $true
            Write-Success "✓ API is ready!"
        }
    }
    catch {
        $attempt++
        Write-Host "." -NoNewline
        Start-Sleep -Seconds 2
    }
}

if (-not $apiReady) {
    Write-Warning "`n⚠ API may still be starting. Check logs if needed."
}

Write-Host ""

# Start Dashboard in background
Write-Info "Starting Trading Dashboard..."
$dashboardJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    Set-Location "apps\trading-dashboard-ui-clean"
    npm run dev
}

Write-Success "✓ Dashboard starting (Job ID: $($dashboardJob.Id))"
Start-Sleep -Seconds 5

Write-Host ""
Write-Info "╔════════════════════════════════════════════════════════════╗"
Write-Info "║                    SYSTEM STARTED                          ║"
Write-Info "╚════════════════════════════════════════════════════════════╝"
Write-Host ""

Write-Info "📊 Access Points:"
Write-Info "  • Trading Dashboard: http://localhost:5173"
Write-Info "  • Trading API: http://localhost:8000"
Write-Info "  • API Documentation: http://localhost:8000/docs"
Write-Host ""

Write-Info "🔧 Management:"
Write-Info "  • View API logs: Receive-Job $($apiJob.Id)"
Write-Info "  • View Dashboard logs: Receive-Job $($dashboardJob.Id)"
Write-Info "  • Stop API: Stop-Job $($apiJob.Id); Remove-Job $($apiJob.Id)"
Write-Info "  • Stop Dashboard: Stop-Job $($dashboardJob.Id); Remove-Job $($dashboardJob.Id)"
Write-Info "  • Stop All: Get-Job | Stop-Job; Get-Job | Remove-Job"
Write-Host ""

Write-Success "✨ System is running in development mode!"
Write-Info "Press Ctrl+C to stop monitoring (services will continue in background)"
Write-Host ""

# Monitor jobs
Write-Info "Monitoring services... (Ctrl+C to exit)"
Write-Host ""

try {
    while ($true) {
        Start-Sleep -Seconds 10
        
        $apiStatus = Get-Job -Id $apiJob.Id
        $dashStatus = Get-Job -Id $dashboardJob.Id
        
        if ($apiStatus.State -ne "Running") {
            Write-Warning "⚠ API job stopped: $($apiStatus.State)"
            Write-Info "View logs: Receive-Job $($apiJob.Id)"
        }
        
        if ($dashStatus.State -ne "Running") {
            Write-Warning "⚠ Dashboard job stopped: $($dashStatus.State)"
            Write-Info "View logs: Receive-Job $($dashboardJob.Id)"
        }
        
        if ($apiStatus.State -ne "Running" -and $dashStatus.State -ne "Running") {
            Write-Warning "All services stopped. Exiting."
            break
        }
    }
}
catch {
    Write-Info "`nMonitoring stopped. Services are still running in background."
    Write-Info "To stop services: Get-Job | Stop-Job; Get-Job | Remove-Job"
}
