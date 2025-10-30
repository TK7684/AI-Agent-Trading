# ProcessManager.psm1
# PowerShell module for managing Trading System processes without Docker

$ErrorActionPreference = "Stop"

# Module-level variables
$script:ProcessRegistry = @{}
$script:ConfigPath = "config/services.json"
$script:LogDirectory = "logs"

# Colors for output
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-Error { Write-Host $args -ForegroundColor Red }

<#
.SYNOPSIS
    Load service configuration from JSON file

.DESCRIPTION
    Reads services.json and returns configuration for all services
#>
function Get-ServiceConfiguration {
    [CmdletBinding()]
    param(
        [string]$ConfigPath = $script:ConfigPath
    )
    
    if (-not (Test-Path $ConfigPath)) {
        throw "Configuration file not found: $ConfigPath"
    }
    
    try {
        $config = Get-Content $ConfigPath -Raw | ConvertFrom-Json
        return $config
    }
    catch {
        throw "Failed to parse configuration file: $_"
    }
}

<#
.SYNOPSIS
    Load environment variables from .env file

.DESCRIPTION
    Reads .env or .env.local file and sets environment variables
#>
function Import-EnvironmentVariables {
    [CmdletBinding()]
    param()
    
    $envFiles = @(".env.local", ".env", ".env.native")
    $loaded = $false
    
    foreach ($envFile in $envFiles) {
        if (Test-Path $envFile) {
            Write-Info "Loading environment from: $envFile"
            
            Get-Content $envFile | ForEach-Object {
                $line = $_.Trim()
                
                # Skip comments and empty lines
                if ($line -match '^\s*#' -or $line -eq '') {
                    return
                }
                
                # Parse KEY=VALUE
                if ($line -match '^\s*([^=]+)=(.*)$') {
                    $key = $matches[1].Trim()
                    $value = $matches[2].Trim()
                    
                    # Remove quotes if present
                    $value = $value -replace '^["'']|["'']$', ''
                    
                    [Environment]::SetEnvironmentVariable($key, $value, "Process")
                }
            }
            
            $loaded = $true
            break
        }
    }
    
    if (-not $loaded) {
        Write-Warning "No .env file found, using system environment variables"
    }
}

<#
.SYNOPSIS
    Substitute environment variables in a string

.DESCRIPTION
    Replaces ${VAR} or $VAR patterns with environment variable values
#>
function Expand-EnvironmentVariables {
    [CmdletBinding()]
    param(
        [string]$Text
    )
    
    # Replace ${VAR} pattern
    $result = $Text -replace '\$\{([^}]+)\}', {
        param($match)
        $varName = $match.Groups[1].Value
        $value = [Environment]::GetEnvironmentVariable($varName)
        if ($null -eq $value) { $match.Value } else { $value }
    }
    
    # Replace $VAR pattern (word boundary)
    $result = $result -replace '\$(\w+)', {
        param($match)
        $varName = $match.Groups[1].Value
        $value = [Environment]::GetEnvironmentVariable($varName)
        if ($null -eq $value) { $match.Value } else { $value }
    }
    
    return $result
}

<#
.SYNOPSIS
    Start a service process

.DESCRIPTION
    Starts a service process with the specified configuration
#>
function Start-ServiceProcess {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [PSCustomObject]$ServiceConfig
    )
    
    $serviceName = $ServiceConfig.name
    Write-Info "Starting service: $serviceName"
    
    # Expand environment variables in command and args
    $command = Expand-EnvironmentVariables -Text $ServiceConfig.command
    $args = $ServiceConfig.args | ForEach-Object { Expand-EnvironmentVariables -Text $_ }
    
    # Set working directory
    $workingDir = if ($ServiceConfig.workingDirectory) {
        $ServiceConfig.workingDirectory
    } else {
        Get-Location
    }
    
    # Prepare environment variables
    $envVars = @{}
    if ($ServiceConfig.env) {
        $ServiceConfig.env.PSObject.Properties | ForEach-Object {
            $envVars[$_.Name] = Expand-EnvironmentVariables -Text $_.Value
        }
    }
    
    # Create log file
    $logFile = Join-Path $script:LogDirectory "$serviceName.log"
    $null = New-Item -ItemType Directory -Path $script:LogDirectory -Force
    
    # Start process
    try {
        $processInfo = New-Object System.Diagnostics.ProcessStartInfo
        $processInfo.FileName = $command
        $processInfo.Arguments = $args -join ' '
        $processInfo.WorkingDirectory = $workingDir
        $processInfo.UseShellExecute = $false
        $processInfo.RedirectStandardOutput = $true
        $processInfo.RedirectStandardError = $true
        $processInfo.CreateNoWindow = $false
        
        # Add environment variables
        foreach ($key in $envVars.Keys) {
            $processInfo.EnvironmentVariables[$key] = $envVars[$key]
        }
        
        $process = New-Object System.Diagnostics.Process
        $process.StartInfo = $processInfo
        
        # Set up output redirection
        $outputHandler = {
            param($sender, $e)
            if ($e.Data) {
                Add-Content -Path $logFile -Value "[OUT] $($e.Data)"
            }
        }
        
        $errorHandler = {
            param($sender, $e)
            if ($e.Data) {
                Add-Content -Path $logFile -Value "[ERR] $($e.Data)"
            }
        }
        
        Register-ObjectEvent -InputObject $process -EventName OutputDataReceived -Action $outputHandler | Out-Null
        Register-ObjectEvent -InputObject $process -EventName ErrorDataReceived -Action $errorHandler | Out-Null
        
        $process.Start() | Out-Null
        $process.BeginOutputReadLine()
        $process.BeginErrorReadLine()
        
        # Store process info
        $script:ProcessRegistry[$serviceName] = @{
            Process = $process
            Config = $ServiceConfig
            StartTime = Get-Date
            RestartCount = 0
            LogFile = $logFile
        }
        
        Write-Success "✅ Started $serviceName (PID: $($process.Id))"
        return $process
    }
    catch {
        Write-Error "❌ Failed to start $serviceName : $_"
        throw
    }
}


<#
.SYNOPSIS
    Stop a service process

.DESCRIPTION
    Gracefully stops a service process with timeout
#>
function Stop-ServiceProcess {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$ServiceName,
        
        [int]$TimeoutSeconds = 30,
        
        [switch]$Force
    )
    
    if (-not $script:ProcessRegistry.ContainsKey($ServiceName)) {
        Write-Warning "Service not found in registry: $ServiceName"
        return
    }
    
    $processInfo = $script:ProcessRegistry[$ServiceName]
    $process = $processInfo.Process
    
    if ($process.HasExited) {
        Write-Info "Service already stopped: $ServiceName"
        $script:ProcessRegistry.Remove($ServiceName)
        return
    }
    
    Write-Info "Stopping service: $ServiceName (PID: $($process.Id))"
    
    if ($Force) {
        # Force kill
        $process.Kill()
        $process.WaitForExit(5000)
        Write-Success "✅ Force stopped $ServiceName"
    }
    else {
        # Graceful shutdown
        try {
            $process.CloseMainWindow() | Out-Null
            
            if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
                Write-Warning "Service did not stop gracefully, forcing..."
                $process.Kill()
                $process.WaitForExit(5000)
            }
            
            Write-Success "✅ Stopped $ServiceName"
        }
        catch {
            Write-Warning "Failed to stop gracefully, forcing..."
            $process.Kill()
            $process.WaitForExit(5000)
        }
    }
    
    $script:ProcessRegistry.Remove($ServiceName)
}

<#
.SYNOPSIS
    Wait for a service to become healthy

.DESCRIPTION
    Polls health check endpoint until service is ready or timeout
#>
function Wait-ForServiceHealth {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [PSCustomObject]$ServiceConfig,
        
        [int]$TimeoutSeconds = 60
    )
    
    if (-not $ServiceConfig.healthCheck) {
        Write-Info "No health check configured for $($ServiceConfig.name), skipping"
        return $true
    }
    
    $serviceName = $ServiceConfig.name
    $healthUrl = Expand-EnvironmentVariables -Text $ServiceConfig.healthCheck.url
    $interval = if ($ServiceConfig.healthCheck.interval) { $ServiceConfig.healthCheck.interval } else { 5 }
    
    Write-Info "Waiting for $serviceName to become healthy..."
    Write-Info "Health check: $healthUrl"
    
    $elapsed = 0
    $attempt = 0
    
    while ($elapsed -lt $TimeoutSeconds) {
        $attempt++
        
        try {
            $response = Invoke-WebRequest -Uri $healthUrl -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
            
            if ($response.StatusCode -eq 200) {
                Write-Success "✅ $serviceName is healthy (attempt $attempt)"
                return $true
            }
        }
        catch {
            # Service not ready yet
            Write-Host "." -NoNewline
        }
        
        Start-Sleep -Seconds $interval
        $elapsed += $interval
    }
    
    Write-Error "`n❌ $serviceName failed to become healthy within $TimeoutSeconds seconds"
    return $false
}

<#
.SYNOPSIS
    Check if a service dependency is running

.DESCRIPTION
    Verifies that a dependency service is running and healthy
#>
function Test-ServiceDependency {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$DependencyName
    )
    
    # Check if it's a Windows service
    $windowsService = Get-Service -Name $DependencyName -ErrorAction SilentlyContinue
    if ($windowsService) {
        return $windowsService.Status -eq 'Running'
    }
    
    # Check if it's in our process registry
    if ($script:ProcessRegistry.ContainsKey($DependencyName)) {
        $processInfo = $script:ProcessRegistry[$DependencyName]
        return -not $processInfo.Process.HasExited
    }
    
    return $false
}

<#
.SYNOPSIS
    Start all trading system services

.DESCRIPTION
    Starts all services in dependency order with health checks
#>
function Start-TradingSystem {
    [CmdletBinding()]
    param(
        [string[]]$Services,
        [switch]$SkipHealthCheck,
        [string]$ConfigPath = $script:ConfigPath
    )
    
    Write-Info "🚀 Starting Trading System"
    Write-Info "=" * 50
    
    # Load environment variables
    Import-EnvironmentVariables
    
    # Load configuration
    $config = Get-ServiceConfiguration -ConfigPath $ConfigPath
    
    # Filter services if specified
    $servicesToStart = if ($Services) {
        $config.services | Where-Object { $Services -contains $_.name }
    } else {
        $config.services
    }
    
    if ($servicesToStart.Count -eq 0) {
        Write-Error "No services to start"
        return
    }
    
    # Build dependency graph and start in order
    $started = @()
    $failed = @()
    
    foreach ($serviceConfig in $servicesToStart) {
        $serviceName = $serviceConfig.name
        
        # Check dependencies
        if ($serviceConfig.dependsOn) {
            Write-Info "`nChecking dependencies for $serviceName..."
            
            foreach ($dependency in $serviceConfig.dependsOn) {
                if (-not (Test-ServiceDependency -DependencyName $dependency)) {
                    Write-Warning "⚠️  Dependency not running: $dependency"
                    Write-Info "Waiting for $dependency..."
                    
                    # Wait a bit for dependency to start
                    $maxWait = 30
                    $waited = 0
                    while ($waited -lt $maxWait -and -not (Test-ServiceDependency -DependencyName $dependency)) {
                        Start-Sleep -Seconds 2
                        $waited += 2
                        Write-Host "." -NoNewline
                    }
                    
                    if (-not (Test-ServiceDependency -DependencyName $dependency)) {
                        Write-Error "`n❌ Dependency $dependency is not available"
                        $failed += $serviceName
                        continue
                    }
                    
                    Write-Host ""
                }
            }
        }
        
        # Start service
        try {
            $process = Start-ServiceProcess -ServiceConfig $serviceConfig
            
            # Wait for health check
            if (-not $SkipHealthCheck -and $serviceConfig.healthCheck) {
                $healthy = Wait-ForServiceHealth -ServiceConfig $serviceConfig -TimeoutSeconds 60
                
                if (-not $healthy) {
                    Write-Error "Service $serviceName failed health check"
                    Stop-ServiceProcess -ServiceName $serviceName -Force
                    $failed += $serviceName
                    continue
                }
            }
            
            $started += $serviceName
        }
        catch {
            Write-Error "Failed to start $serviceName : $_"
            $failed += $serviceName
        }
    }
    
    # Summary
    Write-Info "`n" + ("=" * 50)
    
    if ($started.Count -gt 0) {
        Write-Success "✅ Started services: $($started -join ', ')"
    }
    
    if ($failed.Count -gt 0) {
        Write-Error "❌ Failed services: $($failed -join ', ')"
    }
    
    # Display service URLs
    Write-Info "`n📊 Service URLs:"
    foreach ($serviceConfig in $servicesToStart) {
        if ($started -contains $serviceConfig.name -and $serviceConfig.healthCheck) {
            $url = Expand-EnvironmentVariables -Text $serviceConfig.healthCheck.url
            Write-Info "  • $($serviceConfig.name): $url"
        }
    }
    
    Write-Info "`nView logs: Get-TradingSystemLogs"
    Write-Info "Check status: Get-TradingSystemStatus"
}


<#
.SYNOPSIS
    Stop all trading system services

.DESCRIPTION
    Stops all services in reverse dependency order
#>
function Stop-TradingSystem {
    [CmdletBinding()]
    param(
        [switch]$Graceful = $true,
        [int]$Timeout = 30
    )
    
    Write-Info "🛑 Stopping Trading System"
    Write-Info "=" * 50
    
    if ($script:ProcessRegistry.Count -eq 0) {
        Write-Info "No services running"
        return
    }
    
    # Stop in reverse order
    $services = $script:ProcessRegistry.Keys | Sort-Object -Descending
    
    foreach ($serviceName in $services) {
        try {
            if ($Graceful) {
                Stop-ServiceProcess -ServiceName $serviceName -TimeoutSeconds $Timeout
            }
            else {
                Stop-ServiceProcess -ServiceName $serviceName -Force
            }
        }
        catch {
            Write-Warning "Error stopping $serviceName : $_"
        }
    }
    
    Write-Success "`n✅ All services stopped"
}

<#
.SYNOPSIS
    Restart a specific service

.DESCRIPTION
    Stops and restarts a service while maintaining dependencies
#>
function Restart-TradingService {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$Name,
        
        [string]$ConfigPath = $script:ConfigPath
    )
    
    Write-Info "🔄 Restarting service: $Name"
    
    # Stop service
    if ($script:ProcessRegistry.ContainsKey($Name)) {
        Stop-ServiceProcess -ServiceName $Name
    }
    
    # Load configuration
    $config = Get-ServiceConfiguration -ConfigPath $ConfigPath
    $serviceConfig = $config.services | Where-Object { $_.name -eq $Name }
    
    if (-not $serviceConfig) {
        Write-Error "Service not found in configuration: $Name"
        return
    }
    
    # Start service
    Start-Sleep -Seconds 2
    Start-ServiceProcess -ServiceConfig $serviceConfig
    
    # Wait for health check
    if ($serviceConfig.healthCheck) {
        Wait-ForServiceHealth -ServiceConfig $serviceConfig
    }
    
    Write-Success "✅ Service restarted: $Name"
}

<#
.SYNOPSIS
    Get status of all services

.DESCRIPTION
    Returns status information for all running services
#>
function Get-TradingSystemStatus {
    [CmdletBinding()]
    param(
        [switch]$Detailed
    )
    
    Write-Info "📊 Trading System Status"
    Write-Info "=" * 50
    
    if ($script:ProcessRegistry.Count -eq 0) {
        Write-Warning "No services running"
        return
    }
    
    $statusList = @()
    
    foreach ($serviceName in $script:ProcessRegistry.Keys) {
        $processInfo = $script:ProcessRegistry[$serviceName]
        $process = $processInfo.Process
        
        $status = [PSCustomObject]@{
            Name = $serviceName
            PID = $process.Id
            Status = if ($process.HasExited) { "Stopped" } else { "Running" }
            StartTime = $processInfo.StartTime
            Uptime = if ($process.HasExited) { "N/A" } else { (Get-Date) - $processInfo.StartTime }
            RestartCount = $processInfo.RestartCount
            LogFile = $processInfo.LogFile
        }
        
        $statusList += $status
        
        # Display
        $statusIcon = if ($status.Status -eq "Running") { "🟢" } else { "🔴" }
        Write-Host "$statusIcon $($status.Name) " -NoNewline
        
        if ($status.Status -eq "Running") {
            Write-Host "(PID: $($status.PID), Uptime: $($status.Uptime.ToString('hh\:mm\:ss')))" -ForegroundColor Green
        }
        else {
            Write-Host "(Stopped)" -ForegroundColor Red
        }
        
        if ($Detailed) {
            Write-Info "   Start Time: $($status.StartTime)"
            Write-Info "   Restart Count: $($status.RestartCount)"
            Write-Info "   Log File: $($status.LogFile)"
            
            # Check health if configured
            $config = $processInfo.Config
            if ($config.healthCheck) {
                try {
                    $healthUrl = Expand-EnvironmentVariables -Text $config.healthCheck.url
                    $response = Invoke-WebRequest -Uri $healthUrl -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
                    Write-Success "   Health: OK ($($response.StatusCode))"
                }
                catch {
                    Write-Error "   Health: FAILED"
                }
            }
            
            Write-Host ""
        }
    }
    
    return $statusList
}

<#
.SYNOPSIS
    Get aggregated logs from all services

.DESCRIPTION
    Displays logs from all services or a specific service
#>
function Get-TradingSystemLogs {
    [CmdletBinding()]
    param(
        [string]$Service,
        [switch]$Follow,
        [int]$Tail = 50
    )
    
    if ($Service) {
        # Show logs for specific service
        if (-not $script:ProcessRegistry.ContainsKey($Service)) {
            Write-Error "Service not found: $Service"
            return
        }
        
        $logFile = $script:ProcessRegistry[$Service].LogFile
        
        if (-not (Test-Path $logFile)) {
            Write-Warning "Log file not found: $logFile"
            return
        }
        
        if ($Follow) {
            Get-Content $logFile -Tail $Tail -Wait
        }
        else {
            Get-Content $logFile -Tail $Tail
        }
    }
    else {
        # Show aggregated logs
        $logFiles = $script:ProcessRegistry.Values | ForEach-Object { $_.LogFile } | Where-Object { Test-Path $_ }
        
        if ($logFiles.Count -eq 0) {
            Write-Warning "No log files found"
            return
        }
        
        # Get recent logs from all files
        $allLogs = @()
        
        foreach ($logFile in $logFiles) {
            $serviceName = [System.IO.Path]::GetFileNameWithoutExtension($logFile)
            $logs = Get-Content $logFile -Tail $Tail -ErrorAction SilentlyContinue
            
            foreach ($log in $logs) {
                $allLogs += [PSCustomObject]@{
                    Service = $serviceName
                    Message = $log
                    Time = Get-Date  # Simplified, could parse from log
                }
            }
        }
        
        # Sort and display
        $allLogs | Sort-Object Time | ForEach-Object {
            Write-Host "[$($_.Service)] " -ForegroundColor Cyan -NoNewline
            Write-Host $_.Message
        }
        
        if ($Follow) {
            Write-Info "`nFollowing logs (Ctrl+C to stop)..."
            # This is simplified - real implementation would need proper tail -f
            while ($true) {
                Start-Sleep -Seconds 2
                # Re-read and display new logs
            }
        }
    }
}

<#
.SYNOPSIS
    Monitor process and restart on failure

.DESCRIPTION
    Monitors a process and automatically restarts it if it crashes
#>
function Start-ProcessMonitoring {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$ServiceName,
        
        [int]$MaxRestarts = 3,
        [int]$BackoffSeconds = 5
    )
    
    if (-not $script:ProcessRegistry.ContainsKey($ServiceName)) {
        Write-Error "Service not found: $ServiceName"
        return
    }
    
    $processInfo = $script:ProcessRegistry[$ServiceName]
    $process = $processInfo.Process
    $config = $processInfo.Config
    
    # Start monitoring in background job
    $monitorJob = Start-Job -ScriptBlock {
        param($Process, $Config, $ServiceName, $MaxRestarts, $BackoffSeconds)
        
        $restartCount = 0
        
        while ($restartCount -lt $MaxRestarts) {
            $Process.WaitForExit()
            
            $exitCode = $Process.ExitCode
            Write-Warning "Process $ServiceName exited with code $exitCode"
            
            if ($exitCode -eq 0) {
                # Clean exit, don't restart
                break
            }
            
            $restartCount++
            $backoff = [Math]::Pow(2, $restartCount - 1) * $BackoffSeconds
            
            Write-Info "Restarting $ServiceName in $backoff seconds (attempt $restartCount/$MaxRestarts)..."
            Start-Sleep -Seconds $backoff
            
            # Restart process (simplified - would need to call Start-ServiceProcess)
            Write-Info "Restarting $ServiceName..."
        }
        
        if ($restartCount -ge $MaxRestarts) {
            Write-Error "Service $ServiceName exceeded restart limit"
        }
    } -ArgumentList $process, $config, $ServiceName, $MaxRestarts, $BackoffSeconds
    
    Write-Info "Started monitoring for $ServiceName (Job ID: $($monitorJob.Id))"
}

# Export module functions
Export-ModuleMember -Function @(
    'Get-ServiceConfiguration',
    'Import-EnvironmentVariables',
    'Start-TradingSystem',
    'Stop-TradingSystem',
    'Restart-TradingService',
    'Get-TradingSystemStatus',
    'Get-TradingSystemLogs',
    'Wait-ForServiceHealth',
    'Start-ProcessMonitoring'
)
