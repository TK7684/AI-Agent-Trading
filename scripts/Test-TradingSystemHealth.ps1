<#
.SYNOPSIS
    Comprehensive health check and diagnostics for trading system

.DESCRIPTION
    Runs diagnostics on all system components including PostgreSQL, Redis,
    network connectivity, configuration, and service health.

.PARAMETER Detailed
    Show detailed diagnostic information

.PARAMETER Fix
    Attempt to fix common issues automatically

.EXAMPLE
    .\Test-TradingSystemHealth.ps1
    Run basic health checks

.EXAMPLE
    .\Test-TradingSystemHealth.ps1 -Detailed
    Run detailed diagnostics

.EXAMPLE
    .\Test-TradingSystemHealth.ps1 -Fix
    Run diagnostics and attempt fixes
#>

param(
    [switch]$Detailed,
    [switch]$Fix
)

$ErrorActionPreference = "Continue"

# Colors for output
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-Error { Write-Host $args -ForegroundColor Red }

Write-Info "🏥 Trading System - Health Check & Diagnostics"
Write-Info "=" * 60

$script:IssuesFound = @()
$script:FixesApplied = @()

function Test-Component {
    param(
        [string]$Name,
        [scriptblock]$Test,
        [scriptblock]$Fix = $null,
        [string]$FixDescription = ""
    )
    
    Write-Host "`n[$Name]" -ForegroundColor Cyan
    
    try {
        $result = & $Test
        
        if ($result.Success) {
            Write-Success "  ✓ $($result.Message)"
            if ($Detailed -and $result.Details) {
                foreach ($detail in $result.Details) {
                    Write-Info "    • $detail"
                }
            }
            return $true
        }
        else {
            Write-Error "  ✗ $($result.Message)"
            $script:IssuesFound += "$Name`: $($result.Message)"
            
            if ($result.Details) {
                foreach ($detail in $result.Details) {
                    Write-Warning "    • $detail"
                }
            }
            
            if ($Fix -and $Fix) {
                Write-Info "    Attempting fix: $FixDescription"
                try {
                    & $Fix
                    Write-Success "    ✓ Fix applied"
                    $script:FixesApplied += $Name
                }
                catch {
                    Write-Error "    ✗ Fix failed: $_"
                }
            }
            
            return $false
        }
    }
    catch {
        Write-Error "  ✗ Error: $_"
        $script:IssuesFound += "$Name`: $_"
        return $false
    }
}

# Test 1: PostgreSQL
$pgTest = {
    $service = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue
    
    if (-not $service) {
        return @{
            Success = $false
            Message = "PostgreSQL service not found"
            Details = @("Install PostgreSQL: .\scripts\install-native-services.ps1")
        }
    }
    
    if ($service.Status -ne 'Running') {
        return @{
            Success = $false
            Message = "PostgreSQL service not running"
            Details = @("Status: $($service.Status)")
        }
    }
    
    # Test connection
    $env:PGPASSWORD = "trading"
    $testResult = & psql -h localhost -U trading -d postgres -c "SELECT 1" 2>&1
    Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
    
    if ($LASTEXITCODE -eq 0) {
        return @{
            Success = $true
            Message = "PostgreSQL is healthy"
            Details = @("Service: $($service.Name)", "Status: Running", "Connection: OK")
        }
    }
    else {
        return @{
            Success = $false
            Message = "PostgreSQL connection failed"
            Details = @($testResult)
        }
    }
}

$pgFix = {
    $service = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue
    if ($service -and $service.Status -ne 'Running') {
        Start-Service $service.Name
    }
}

Test-Component -Name "PostgreSQL" -Test $pgTest -Fix $pgFix -FixDescription "Start PostgreSQL service"

# Test 2: Redis
$redisTest = {
    $service = Get-Service -Name "Redis" -ErrorAction SilentlyContinue
    
    if (-not $service) {
        return @{
            Success = $false
            Message = "Redis service not found"
            Details = @("Install Redis: .\scripts\install-native-services.ps1")
        }
    }
    
    if ($service.Status -ne 'Running') {
        return @{
            Success = $false
            Message = "Redis service not running"
            Details = @("Status: $($service.Status)")
        }
    }
    
    return @{
        Success = $true
        Message = "Redis is healthy"
        Details = @("Service: Redis", "Status: Running")
    }
}

$redisFix = {
    $service = Get-Service -Name "Redis" -ErrorAction SilentlyContinue
    if ($service -and $service.Status -ne 'Running') {
        Start-Service Redis
    }
}

Test-Component -Name "Redis" -Test $redisTest -Fix $redisFix -FixDescription "Start Redis service"

# Test 3: Environment Configuration
$envTest = {
    $envFiles = @(".env.local", ".env", ".env.native")
    $found = $null
    
    foreach ($file in $envFiles) {
        if (Test-Path $file) {
            $found = $file
            break
        }
    }
    
    if (-not $found) {
        return @{
            Success = $false
            Message = "No environment file found"
            Details = @("Create .env.local from .env.native.template")
        }
    }
    
    # Check required variables
    $content = Get-Content $found -Raw
    $required = @("DATABASE_URL", "REDIS_URL", "SECRET_KEY")
    $missing = @()
    
    foreach ($var in $required) {
        if ($content -notmatch "$var=") {
            $missing += $var
        }
    }
    
    if ($missing.Count -gt 0) {
        return @{
            Success = $false
            Message = "Missing required environment variables"
            Details = $missing
        }
    }
    
    return @{
        Success = $true
        Message = "Environment configuration is valid"
        Details = @("File: $found", "Required variables: Present")
    }
}

$envFix = {
    if (Test-Path ".env.native.template") {
        Copy-Item ".env.native.template" ".env.local"
    }
}

Test-Component -Name "Environment Configuration" -Test $envTest -Fix $envFix -FixDescription "Create .env.local from template"

# Test 4: Python Environment
$pythonTest = {
    if (-not (Get-Command poetry -ErrorAction SilentlyContinue)) {
        return @{
            Success = $false
            Message = "Poetry not found"
            Details = @("Install: https://python-poetry.org/docs/#installation")
        }
    }
    
    $version = poetry --version 2>&1
    
    # Check if dependencies are installed
    $checkResult = poetry run python -c "import fastapi" 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        return @{
            Success = $true
            Message = "Python environment is healthy"
            Details = @("Poetry: $version", "Dependencies: Installed")
        }
    }
    else {
        return @{
            Success = $false
            Message = "Python dependencies not installed"
            Details = @("Run: poetry install")
        }
    }
}

$pythonFix = {
    poetry install --no-interaction
}

Test-Component -Name "Python Environment" -Test $pythonTest -Fix $pythonFix -FixDescription "Install Python dependencies"

# Test 5: Node.js Environment
$nodeTest = {
    if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
        return @{
            Success = $false
            Message = "Node.js not found"
            Details = @("Install: https://nodejs.org/")
        }
    }
    
    $version = node --version
    
    # Check if dashboard dependencies are installed
    $nodeModules = "apps\trading-dashboard-ui-clean\node_modules"
    
    if (Test-Path $nodeModules) {
        return @{
            Success = $true
            Message = "Node.js environment is healthy"
            Details = @("Node.js: $version", "Dependencies: Installed")
        }
    }
    else {
        return @{
            Success = $false
            Message = "Node.js dependencies not installed"
            Details = @("Run: npm install in apps/trading-dashboard-ui-clean")
        }
    }
}

$nodeFix = {
    Push-Location "apps\trading-dashboard-ui-clean"
    npm install --silent
    Pop-Location
}

Test-Component -Name "Node.js Environment" -Test $nodeTest -Fix $nodeFix -FixDescription "Install Node.js dependencies"

# Test 6: Rust Build
$rustTest = {
    if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
        return @{
            Success = $false
            Message = "Rust/Cargo not found"
            Details = @("Install: https://rustup.rs/")
        }
    }
    
    $version = cargo --version
    
    if (Test-Path "target\release\execution-gateway.exe") {
        return @{
            Success = $true
            Message = "Rust execution gateway is built"
            Details = @("Cargo: $version", "Binary: target\release\execution-gateway.exe")
        }
    }
    else {
        return @{
            Success = $false
            Message = "Execution gateway not built"
            Details = @("Run: cargo build --package execution-gateway --release")
        }
    }
}

$rustFix = {
    cargo build --package execution-gateway --release
}

Test-Component -Name "Rust Build" -Test $rustTest -Fix $rustFix -FixDescription "Build execution gateway"

# Test 7: Network Connectivity
$networkTest = {
    $ports = @(
        @{ Port = 5432; Service = "PostgreSQL" },
        @{ Port = 6379; Service = "Redis" },
        @{ Port = 8000; Service = "Trading API" },
        @{ Port = 3000; Service = "Execution Gateway" },
        @{ Port = 5173; Service = "Dashboard" }
    )
    
    $listening = @()
    $notListening = @()
    
    foreach ($portInfo in $ports) {
        $connection = Test-NetConnection -ComputerName localhost -Port $portInfo.Port -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
        
        if ($connection.TcpTestSucceeded) {
            $listening += "$($portInfo.Service) (port $($portInfo.Port))"
        }
        else {
            $notListening += "$($portInfo.Service) (port $($portInfo.Port))"
        }
    }
    
    return @{
        Success = $true
        Message = "Network connectivity check complete"
        Details = @(
            "Listening: $($listening -join ', ')",
            "Not listening: $($notListening -join ', ')"
        )
    }
}

Test-Component -Name "Network Connectivity" -Test $networkTest

# Summary
Write-Host ""
Write-Info "=" * 60
Write-Host ""

if ($script:IssuesFound.Count -eq 0) {
    Write-Success "🎉 All health checks passed!"
    Write-Info "System is ready to start."
}
else {
    Write-Warning "⚠️  Found $($script:IssuesFound.Count) issue(s):"
    foreach ($issue in $script:IssuesFound) {
        Write-Warning "  • $issue"
    }
    
    if ($script:FixesApplied.Count -gt 0) {
        Write-Info "`nApplied $($script:FixesApplied.Count) fix(es):"
        foreach ($fixItem in $script:FixesApplied) {
            Write-Success "  ✓ $fixItem"
        }
        Write-Info "`nRun health check again to verify fixes."
    }
    else {
        Write-Info "`nRun with -Fix to attempt automatic fixes."
    }
}

Write-Host ""
Write-Info "Next steps:"
if ($script:IssuesFound.Count -eq 0) {
    Write-Info "  • Start system: .\scripts\start-trading-system.ps1"
}
else {
    Write-Info "  • Fix issues above"
    Write-Info "  • Run: .\scripts\Test-TradingSystemHealth.ps1 -Fix"
    Write-Info "  • Or run setup: .\scripts\Setup-NativeDevelopment.ps1"
}
Write-Host ""

exit $script:IssuesFound.Count
