<#
.SYNOPSIS
    Stop the Trading System

.DESCRIPTION
    Gracefully stops all trading system services

.PARAMETER Force
    Force stop without graceful shutdown

.PARAMETER Timeout
    Timeout in seconds for graceful shutdown (default: 30)

.EXAMPLE
    .\stop-trading-system.ps1
    Gracefully stop all services

.EXAMPLE
    .\stop-trading-system.ps1 -Force
    Force stop all services immediately
#>

param(
    [switch]$Force,
    [int]$Timeout = 30
)

$ErrorActionPreference = "Stop"

# Colors for output
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-Error { Write-Host $args -ForegroundColor Red }

Write-Info "🛑 Stopping Trading System"
Write-Info "=" * 50

# Import ProcessManager module
$modulePath = Join-Path $PSScriptRoot "ProcessManager.psm1"
if (-not (Test-Path $modulePath)) {
    Write-Error "ProcessManager module not found: $modulePath"
    exit 1
}

Import-Module $modulePath -Force

# Stop services
try {
    if ($Force) {
        Write-Warning "Force stopping all services..."
        Stop-TradingSystem -Graceful:$false
    }
    else {
        Write-Info "Gracefully stopping all services (timeout: $Timeout seconds)..."
        Stop-TradingSystem -Graceful -Timeout $Timeout
    }
    
    Write-Success "`n✅ Trading System stopped successfully"
}
catch {
    Write-Error "❌ Error stopping trading system: $_"
    exit 1
}
