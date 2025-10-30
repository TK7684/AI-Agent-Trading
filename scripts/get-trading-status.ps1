<#
.SYNOPSIS
    Get Trading System status

.DESCRIPTION
    Displays status of all running services

.PARAMETER Detailed
    Show detailed information including health checks

.EXAMPLE
    .\get-trading-status.ps1
    Show basic status

.EXAMPLE
    .\get-trading-status.ps1 -Detailed
    Show detailed status with health checks
#>

param(
    [switch]$Detailed
)

# Import ProcessManager module
$modulePath = Join-Path $PSScriptRoot "ProcessManager.psm1"
if (Test-Path $modulePath) {
    Import-Module $modulePath -Force
    Get-TradingSystemStatus -Detailed:$Detailed
}
else {
    Write-Host "ProcessManager module not found. System may not be running." -ForegroundColor Yellow
}
