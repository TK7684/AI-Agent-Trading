<#
.SYNOPSIS
    Restart a specific trading system service

.DESCRIPTION
    Stops and restarts a specific service while maintaining dependency awareness.
    Useful for applying configuration changes or recovering from errors.

.PARAMETER ServiceName
    Name of the service to restart

.PARAMETER Force
    Force restart without graceful shutdown

.PARAMETER RestartDependents
    Also restart services that depend on this service

.EXAMPLE
    .\Restart-TradingService.ps1 -ServiceName trading-api
    Restart the trading API

.EXAMPLE
    .\Restart-TradingService.ps1 -ServiceName trading-api -RestartDependents
    Restart trading API and all dependent services

.EXAMPLE
    .\Restart-TradingService.ps1 -ServiceName orchestrator -Force
    Force restart the orchestrator
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$ServiceName,
    [switch]$Force,
    [switch]$RestartDependents
)

$ErrorActionPreference = "Stop"

# Colors for output
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-Error { Write-Host $args -ForegroundColor Red }

Write-Info "🔄 Restarting Trading Service: $ServiceName"
Write-Info "=" * 50

# Import ProcessManager module
$modulePath = Join-Path $PSScriptRoot "ProcessManager.psm1"
if (-not (Test-Path $modulePath)) {
    Write-Error "ProcessManager module not found: $modulePath"
    exit 1
}

Import-Module $modulePath -Force

try {
    # Get current status
    Write-Info "Checking current status..."
    $status = Get-TradingSystemStatus | Where-Object { $_.Name -eq $ServiceName }
    
    if (-not $status) {
        Write-Error "❌ Service not found: $ServiceName"
        Write-Info "`nAvailable services:"
        Get-TradingSystemStatus | ForEach-Object {
            Write-Info "  • $($_.Name)"
        }
        exit 1
    }
    
    Write-Info "Current status: $($status.Status)"
    
    # Determine dependent services if needed
    $servicesToRestart = @($ServiceName)
    
    if ($RestartDependents) {
        Write-Info "Finding dependent services..."
        $config = Get-ServiceConfiguration
        
        foreach ($svc in $config.services) {
            if ($svc.dependsOn -contains $ServiceName) {
                $servicesToRestart += $svc.name
                Write-Info "  • Will also restart: $($svc.name)"
            }
        }
    }
    
    # Stop services (in reverse dependency order)
    Write-Info "`nStopping service(s)..."
    foreach ($svc in $servicesToRestart | Sort-Object -Descending) {
        if ($Force) {
            Stop-TradingService -Name $svc -Graceful:$false
        }
        else {
            Stop-TradingService -Name $svc -Graceful
        }
        Write-Success "✅ Stopped: $svc"
    }
    
    # Wait a moment for cleanup
    Start-Sleep -Seconds 2
    
    # Start services (in dependency order)
    Write-Info "`nStarting service(s)..."
    foreach ($svc in $servicesToRestart) {
        Start-TradingService -Name $svc
        Write-Success "✅ Started: $svc"
        
        # Wait for health check
        Start-Sleep -Seconds 3
    }
    
    # Verify services are running
    Write-Info "`nVerifying services..."
    $allHealthy = $true
    
    foreach ($svc in $servicesToRestart) {
        $newStatus = Get-TradingSystemStatus | Where-Object { $_.Name -eq $svc }
        
        if ($newStatus.Status -eq "Running") {
            Write-Success "✅ $svc is running"
        }
        else {
            Write-Warning "⚠️  $svc status: $($newStatus.Status)"
            $allHealthy = $false
        }
    }
    
    Write-Info "`n" + ("=" * 50)
    
    if ($allHealthy) {
        Write-Success "🎉 Service restart complete!"
    }
    else {
        Write-Warning "⚠️  Some services may not be healthy"
        Write-Info "Check logs with: .\scripts\get-trading-logs.ps1 -Service $ServiceName"
    }
}
catch {
    Write-Error "`n❌ Failed to restart service: $_"
    Write-Info "`nTroubleshooting:"
    Write-Info "  • Check service logs: .\scripts\get-trading-logs.ps1 -Service $ServiceName"
    Write-Info "  • Check system status: .\scripts\get-trading-status.ps1 -Detailed"
    Write-Info "  • Try force restart: -Force"
    exit 1
}
