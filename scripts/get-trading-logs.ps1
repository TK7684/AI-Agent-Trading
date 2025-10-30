<#
.SYNOPSIS
    View Trading System logs

.DESCRIPTION
    Displays logs from all services or a specific service

.PARAMETER Service
    Specific service to view logs for

.PARAMETER Follow
    Follow log output (like tail -f)

.PARAMETER Tail
    Number of lines to show (default: 50)

.EXAMPLE
    .\get-trading-logs.ps1
    Show recent logs from all services

.EXAMPLE
    .\get-trading-logs.ps1 -Service trading-api
    Show logs for trading API only

.EXAMPLE
    .\get-trading-logs.ps1 -Service trading-api -Follow
    Follow trading API logs in real-time
#>

param(
    [string]$Service,
    [switch]$Follow,
    [int]$Tail = 50
)

# Import ProcessManager module
$modulePath = Join-Path $PSScriptRoot "ProcessManager.psm1"
if (Test-Path $modulePath) {
    Import-Module $modulePath -Force
    
    $params = @{
        Tail = $Tail
    }
    
    if ($Service) {
        $params.Service = $Service
    }
    
    if ($Follow) {
        $params.Follow = $true
    }
    
    Get-TradingSystemLogs @params
}
else {
    Write-Host "ProcessManager module not found." -ForegroundColor Yellow
    Write-Host "Checking log directory..." -ForegroundColor Cyan
    
    if (Test-Path "logs") {
        $logFiles = Get-ChildItem "logs" -Filter "*.log"
        
        if ($logFiles.Count -gt 0) {
            Write-Host "`nAvailable log files:" -ForegroundColor Cyan
            foreach ($file in $logFiles) {
                Write-Host "  • $($file.Name)" -ForegroundColor Green
            }
            
            if ($Service) {
                $logFile = "logs\$Service.log"
                if (Test-Path $logFile) {
                    Write-Host "`nShowing logs for: $Service" -ForegroundColor Cyan
                    Get-Content $logFile -Tail $Tail
                }
                else {
                    Write-Host "Log file not found: $logFile" -ForegroundColor Red
                }
            }
        }
        else {
            Write-Host "No log files found" -ForegroundColor Yellow
        }
    }
    else {
        Write-Host "Logs directory not found" -ForegroundColor Yellow
    }
}
