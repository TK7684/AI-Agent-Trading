<#
.SYNOPSIS
    Start the Trading System with all services

.DESCRIPTION
    Main entry point to start all trading system services natively without Docker.
    This script uses the ProcessManager module to orchestrate service startup.

.PARAMETER Services
    Specific services to start (default: all services)

.PARAMETER SkipHealthCheck
    Skip health check validation

.PARAMETER ConfigPath
    Path to services configuration file

.EXAMPLE
    .\start-trading-system.ps1
    Start all services with health checks

.EXAMPLE
    .\start-trading-system.ps1 -Services trading-api,trading-dashboard
    Start only specific services

.EXAMPLE
    .\start-trading-system.ps1 -SkipHealthCheck
    Start all services without waiting for health checks
#>

param(
    [string[]]$Services,
    [switch]$SkipHealthCheck,
    [string]$ConfigPath = "config/services.json"
)

$ErrorActionPreference = "Stop"

# Colors for output
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-Error { Write-Host $args -ForegroundColor Red }

# Banner
Write-Host ""
Write-Info "╔════════════════════════════════════════════════════════════╗"
Write-Info "║                                                            ║"
Write-Info "║        🚀 AUTONOMOUS TRADING SYSTEM - NATIVE MODE 🚀       ║"
Write-Info "║                                                            ║"
Write-Info "║              Docker-Free • High Performance                ║"
Write-Info "║                                                            ║"
Write-Info "╚════════════════════════════════════════════════════════════╝"
Write-Host ""

# Import ProcessManager module
$modulePath = Join-Path $PSScriptRoot "ProcessManager.psm1"
if (-not (Test-Path $modulePath)) {
    Write-Error "ProcessManager module not found: $modulePath"
    exit 1
}

Import-Module $modulePath -Force

# Pre-flight checks
Write-Info "🔍 Running pre-flight checks..."

# Check if .env file exists
$envFiles = @(".env.local", ".env", ".env.native")
$envFound = $false
foreach ($envFile in $envFiles) {
    if (Test-Path $envFile) {
        Write-Success "✅ Found environment file: $envFile"
        $envFound = $true
        break
    }
}

if (-not $envFound) {
    Write-Warning "⚠️  No .env file found!"
    Write-Info "Creating .env.local from template..."
    
    if (Test-Path ".env.native.template") {
        Copy-Item ".env.native.template" ".env.local"
        Write-Warning "⚠️  Please edit .env.local with your configuration"
        Write-Info "Especially update:"
        Write-Info "  • POSTGRES_PASSWORD"
        Write-Info "  • SECRET_KEY"
        Write-Info ""
        $response = Read-Host "Continue anyway? (y/N)"
        if ($response -ne 'y') {
            exit 0
        }
    }
    else {
        Write-Error "❌ No .env template found. Cannot continue."
        exit 1
    }
}

# Check if services.json exists
if (-not (Test-Path $ConfigPath)) {
    Write-Error "❌ Services configuration not found: $ConfigPath"
    exit 1
}

# Check PostgreSQL service
Write-Info "Checking PostgreSQL service..."
$pgService = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue
if ($pgService -and $pgService.Status -eq 'Running') {
    Write-Success "✅ PostgreSQL is running"
}
else {
    Write-Warning "⚠️  PostgreSQL service not running"
    Write-Info "Attempting to start PostgreSQL..."
    
    try {
        Start-Service $pgService.Name
        Start-Sleep -Seconds 5
        Write-Success "✅ PostgreSQL started"
    }
    catch {
        Write-Error "❌ Failed to start PostgreSQL: $_"
        Write-Info "Please run: .\scripts\install-native-services.ps1"
        exit 1
    }
}

# Check Redis service
Write-Info "Checking Redis service..."
$redisService = Get-Service -Name "Redis" -ErrorAction SilentlyContinue
if ($redisService -and $redisService.Status -eq 'Running') {
    Write-Success "✅ Redis is running"
}
else {
    Write-Warning "⚠️  Redis service not running"
    Write-Info "Attempting to start Redis..."
    
    try {
        Start-Service Redis
        Start-Sleep -Seconds 3
        Write-Success "✅ Redis started"
    }
    catch {
        Write-Error "❌ Failed to start Redis: $_"
        Write-Info "Please run: .\scripts\install-native-services.ps1"
        exit 1
    }
}

# Check if Poetry is installed
if (-not (Get-Command poetry -ErrorAction SilentlyContinue)) {
    Write-Error "❌ Poetry not found. Please install Poetry first."
    Write-Info "Visit: https://python-poetry.org/docs/#installation"
    exit 1
}

# Check if Node.js is installed
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Error "❌ Node.js not found. Please install Node.js first."
    Write-Info "Visit: https://nodejs.org/"
    exit 1
}

# Check if Rust execution gateway is built
if (-not (Test-Path "target/release/execution-gateway.exe")) {
    Write-Warning "⚠️  Execution gateway not built"
    Write-Info "Building execution gateway..."
    
    try {
        cargo build --package execution-gateway --release
        Write-Success "✅ Execution gateway built"
    }
    catch {
        Write-Warning "⚠️  Failed to build execution gateway, will skip it"
    }
}

Write-Success "`n✅ Pre-flight checks complete"
Write-Host ""

# Start services
try {
    $params = @{
        ConfigPath = $ConfigPath
    }
    
    if ($Services) {
        $params.Services = $Services
    }
    
    if ($SkipHealthCheck) {
        $params.SkipHealthCheck = $true
    }
    
    Start-TradingSystem @params
    
    # Display helpful information
    Write-Host ""
    Write-Info "╔════════════════════════════════════════════════════════════╗"
    Write-Info "║                    SYSTEM READY                            ║"
    Write-Info "╚════════════════════════════════════════════════════════════╝"
    Write-Host ""
    Write-Info "📊 Access Points:"
    Write-Info "  • Trading Dashboard: http://localhost:5173"
    Write-Info "  • Trading API: http://localhost:8000"
    Write-Info "  • API Documentation: http://localhost:8000/docs"
    Write-Info "  • Execution Gateway: http://localhost:3000"
    Write-Host ""
    Write-Info "🔧 Management Commands:"
    Write-Info "  • View Status: Get-TradingSystemStatus"
    Write-Info "  • View Logs: Get-TradingSystemLogs"
    Write-Info "  • Stop System: Stop-TradingSystem"
    Write-Info "  • Restart Service: Restart-TradingService -Name <service>"
    Write-Host ""
    Write-Info "📝 Log Files: ./logs/"
    Write-Host ""
    Write-Success "🎉 Trading System is running!"
    Write-Info "Press Ctrl+C to stop (or run Stop-TradingSystem in another terminal)"
    Write-Host ""
    
    # Keep script running
    Write-Info "Monitoring services... (Ctrl+C to exit)"
    while ($true) {
        Start-Sleep -Seconds 10
        
        # Check if any service has crashed
        $status = Get-TradingSystemStatus
        $crashed = $status | Where-Object { $_.Status -eq "Stopped" }
        
        if ($crashed) {
            Write-Warning "`n⚠️  Detected crashed services: $($crashed.Name -join ', ')"
            Write-Info "Check logs with: Get-TradingSystemLogs -Service <name>"
        }
    }
}
catch {
    Write-Error "`n❌ Failed to start trading system: $_"
    Write-Info "`nTroubleshooting:"
    Write-Info "  • Check logs in ./logs/ directory"
    Write-Info "  • Verify .env configuration"
    Write-Info "  • Ensure PostgreSQL and Redis are running"
    Write-Info "  • Run: Get-TradingSystemStatus"
    
    # Cleanup
    Write-Info "`nCleaning up..."
    Stop-TradingSystem -Force
    
    exit 1
}
