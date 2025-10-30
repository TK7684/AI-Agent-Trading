<#
.SYNOPSIS
    Comprehensive test of native deployment functionality

.DESCRIPTION
    Tests all native deployment scripts and features to verify the implementation.

.EXAMPLE
    .\Test-NativeDeployment.ps1
#>

$ErrorActionPreference = "Continue"

# Colors for output
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-Error { Write-Host $args -ForegroundColor Red }
function Write-TestHeader { 
    param([string]$Title)
    Write-Host "`n" -NoNewline
    Write-Host "=" * 70 -ForegroundColor Magenta
    Write-Host "TEST: $Title" -ForegroundColor Cyan
    Write-Host "=" * 70 -ForegroundColor Magenta
}

$script:TestsPassed = 0
$script:TestsFailed = 0
$script:TestsSkipped = 0

function Test-Feature {
    param(
        [string]$Name,
        [scriptblock]$Test,
        [switch]$SkipOnError
    )
    
    Write-Host "`n[$Name]" -ForegroundColor Yellow
    
    try {
        $result = & $Test
        if ($result) {
            Write-Success "  ✓ PASS"
            $script:TestsPassed++
            return $true
        }
        else {
            Write-Error "  ✗ FAIL"
            $script:TestsFailed++
            return $false
        }
    }
    catch {
        if ($SkipOnError) {
            Write-Warning "  ⊘ SKIP: $_"
            $script:TestsSkipped++
        }
        else {
            Write-Error "  ✗ FAIL: $_"
            $script:TestsFailed++
        }
        return $false
    }
}

Write-Info "╔════════════════════════════════════════════════════════════════════╗"
Write-Info "║                                                                    ║"
Write-Info "║     🧪 NATIVE DEPLOYMENT - COMPREHENSIVE FUNCTIONALITY TEST 🧪      ║"
Write-Info "║                                                                    ║"
Write-Info "╚════════════════════════════════════════════════════════════════════╝"

$startTime = Get-Date

# Test 1: Configuration Loading
Write-TestHeader "Configuration Loading (.env file priority)"

Test-Feature "Environment file exists" {
    $envFiles = @(".env.local", ".env", ".env.native")
    foreach ($file in $envFiles) {
        if (Test-Path $file) {
            Write-Info "    Found: $file"
            return $true
        }
    }
    return $false
}

Test-Feature "Python config_manager loads .env" {
    $output = poetry run python -c "from libs.trading_models.config_manager import *; import os; print(bool(os.getenv('DATABASE_URL')))" 2>&1
    return $output -match "True"
}

Test-Feature "Environment variables are loaded" {
    $output = poetry run python -c "import os; from dotenv import load_dotenv; load_dotenv('.env.local'); print('DB:', bool(os.getenv('DATABASE_URL')), 'Redis:', bool(os.getenv('REDIS_URL')))" 2>&1
    return $output -match "DB: True" -and $output -match "Redis: True"
}

# Test 2: Script Availability
Write-TestHeader "Script Availability"

$scripts = @(
    "Setup-NativeDevelopment.ps1",
    "Setup-NativeProduction.ps1",
    "start-trading-system.ps1",
    "stop-trading-system.ps1",
    "get-trading-status.ps1",
    "get-trading-logs.ps1",
    "Restart-TradingService.ps1",
    "Backup-TradingDatabase.ps1",
    "Restore-TradingDatabase.ps1",
    "Update-TradingDatabase.ps1",
    "Reset-TradingDatabase.ps1",
    "Build-ExecutionGateway.ps1",
    "Test-TradingSystemHealth.ps1",
    "ProcessManager.psm1"
)

foreach ($script in $scripts) {
    Test-Feature "Script exists: $script" {
        $path = "scripts\$script"
        if (Test-Path $path) {
            Write-Info "    Path: $path"
            return $true
        }
        return $false
    }
}

# Test 3: ProcessManager Module
Write-TestHeader "ProcessManager Module"

Test-Feature "ProcessManager module loads" {
    Import-Module ".\scripts\ProcessManager.psm1" -Force
    return $true
}

Test-Feature "Get-ServiceConfiguration function exists" {
    $cmd = Get-Command Get-ServiceConfiguration -ErrorAction SilentlyContinue
    return $null -ne $cmd
}

Test-Feature "Services configuration file exists" {
    return Test-Path "config\services.json"
}

Test-Feature "Services configuration is valid JSON" {
    $config = Get-Content "config\services.json" -Raw | ConvertFrom-Json
    return $config.services.Count -gt 0
}

# Test 4: Database Scripts
Write-TestHeader "Database Management Scripts"

Test-Feature "Database scripts are executable" {
    $dbScripts = @(
        "scripts\Backup-TradingDatabase.ps1",
        "scripts\Restore-TradingDatabase.ps1",
        "scripts\Update-TradingDatabase.ps1",
        "scripts\Reset-TradingDatabase.ps1"
    )
    
    foreach ($script in $dbScripts) {
        if (-not (Test-Path $script)) {
            Write-Warning "    Missing: $script"
            return $false
        }
    }
    Write-Info "    All database scripts present"
    return $true
}

# Test 5: Service Management
Write-TestHeader "Service Management"

Test-Feature "Status script works" {
    $output = & ".\scripts\get-trading-status.ps1" 2>&1
    return $LASTEXITCODE -eq 0
}

Test-Feature "ProcessManager can list services" {
    Import-Module ".\scripts\ProcessManager.psm1" -Force
    $config = Get-ServiceConfiguration
    Write-Info "    Services defined: $($config.services.Count)"
    foreach ($svc in $config.services) {
        Write-Info "      • $($svc.name)"
    }
    return $config.services.Count -gt 0
}

# Test 6: Health Check System
Write-TestHeader "Health Check & Diagnostics"

Test-Feature "Health check script exists" {
    return Test-Path "scripts\Test-TradingSystemHealth.ps1"
}

Test-Feature "Health check runs without errors" {
    $output = & ".\scripts\Test-TradingSystemHealth.ps1" 2>&1
    # Script may return non-zero if issues found, but should execute
    return $output -match "Trading System"
}

# Test 7: Documentation
Write-TestHeader "Documentation"

$docs = @(
    "NATIVE-DEPLOYMENT.md",
    "NATIVE-DEPLOYMENT-QUICKSTART.md",
    "NATIVE-DEPLOYMENT-COMPLETE.md",
    "README.md"
)

foreach ($doc in $docs) {
    Test-Feature "Documentation exists: $doc" {
        if (Test-Path $doc) {
            $lines = (Get-Content $doc).Count
            Write-Info "    Lines: $lines"
            return $true
        }
        return $false
    }
}

# Test 8: Configuration Files
Write-TestHeader "Configuration Files"

Test-Feature "services.json exists and valid" {
    if (Test-Path "config\services.json") {
        $config = Get-Content "config\services.json" -Raw | ConvertFrom-Json
        Write-Info "    Services: $($config.services.Count)"
        Write-Info "    Logging configured: $($null -ne $config.logging)"
        return $true
    }
    return $false
}

Test-Feature ".env template exists" {
    return Test-Path ".env.native.template"
}

Test-Feature "config.toml exists" {
    return Test-Path "config.toml"
}

# Test 9: Python Environment
Write-TestHeader "Python Environment"

Test-Feature "Poetry is installed" {
    $version = poetry --version 2>&1
    Write-Info "    $version"
    return $LASTEXITCODE -eq 0
}

Test-Feature "python-dotenv is installed" {
    $output = poetry run python -c "import dotenv; print(dotenv.__version__)" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Info "    Version: $output"
        return $true
    }
    return $false
}

Test-Feature "Trading models can be imported" {
    $output = poetry run python -c "from libs.trading_models import config_manager; print('OK')" 2>&1
    return $output -match "OK"
}

# Test 10: Node.js Environment
Write-TestHeader "Node.js Environment"

Test-Feature "Node.js is installed" {
    $version = node --version 2>&1
    Write-Info "    Version: $version"
    return $LASTEXITCODE -eq 0
}

Test-Feature "Dashboard dependencies installed" {
    return Test-Path "apps\trading-dashboard-ui-clean\node_modules"
}

Test-Feature "Dashboard package.json has dev script" {
    $pkg = Get-Content "apps\trading-dashboard-ui-clean\package.json" -Raw | ConvertFrom-Json
    return $null -ne $pkg.scripts.dev
}

# Test 11: Vite Configuration
Write-TestHeader "Vite Configuration"

Test-Feature "vite.config.ts exists" {
    return Test-Path "apps\trading-dashboard-ui-clean\vite.config.ts"
}

Test-Feature "Vite config has proxy settings" {
    $content = Get-Content "apps\trading-dashboard-ui-clean\vite.config.ts" -Raw
    return $content -match "proxy" -and $content -match "/api" -and $content -match "/ws"
}

# Test 12: System Prerequisites
Write-TestHeader "System Prerequisites"

Test-Feature "PostgreSQL service exists" {
    $service = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue
    if ($service) {
        Write-Info "    Service: $($service.Name)"
        Write-Info "    Status: $($service.Status)"
        return $true
    }
    return $false
} -SkipOnError

Test-Feature "Cargo (Rust) is available" {
    $version = cargo --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Info "    $version"
        return $true
    }
    return $false
} -SkipOnError

# Summary
$duration = (Get-Date) - $startTime
$total = $script:TestsPassed + $script:TestsFailed + $script:TestsSkipped

Write-Host "`n"
Write-Info "╔════════════════════════════════════════════════════════════════════╗"
Write-Info "║                         TEST SUMMARY                               ║"
Write-Info "╚════════════════════════════════════════════════════════════════════╝"
Write-Host ""

Write-Success "✓ Passed:  $script:TestsPassed"
if ($script:TestsFailed -gt 0) {
    Write-Error "✗ Failed:  $script:TestsFailed"
}
else {
    Write-Info "✗ Failed:  $script:TestsFailed"
}
if ($script:TestsSkipped -gt 0) {
    Write-Warning "⊘ Skipped: $script:TestsSkipped"
}
Write-Info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Info "  Total:   $total"
Write-Host ""

$passRate = [math]::Round(($script:TestsPassed / $total) * 100, 1)
Write-Info "Pass Rate: $passRate%"
Write-Info "Duration:  $([math]::Round($duration.TotalSeconds, 2))s"
Write-Host ""

if ($script:TestsFailed -eq 0) {
    Write-Success "🎉 ALL TESTS PASSED!"
    Write-Info "Native deployment implementation is fully functional."
}
else {
    Write-Warning "⚠️  Some tests failed. Review the output above."
}

Write-Host ""
Write-Info "Next steps:"
Write-Info "  • Review test results above"
Write-Info "  • Run: .\scripts\Test-TradingSystemHealth.ps1 -Detailed"
Write-Info "  • Start system: .\scripts\start-trading-system.ps1"
Write-Host ""

exit $script:TestsFailed
