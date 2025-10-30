#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Verify python-dotenv configuration and .env file loading

.DESCRIPTION
    This script verifies that python-dotenv is properly installed and configured,
    and that .env files are being loaded correctly by the configuration manager.

.EXAMPLE
    .\scripts\verify-dotenv-config.ps1
#>

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

Write-Host "=== Python-dotenv Configuration Verification ===" -ForegroundColor Cyan
Write-Host ""

# Check if Poetry is installed
Write-Host "1. Checking Poetry installation..." -ForegroundColor Yellow
try {
    $poetryVersion = poetry --version 2>&1
    Write-Host "   ✓ Poetry found: $poetryVersion" -ForegroundColor Green
} catch {
    Write-Host "   ✗ Poetry not found. Please install Poetry first." -ForegroundColor Red
    exit 1
}

# Check if python-dotenv is in dependencies
Write-Host ""
Write-Host "2. Checking python-dotenv in pyproject.toml..." -ForegroundColor Yellow
$pyprojectContent = Get-Content "pyproject.toml" -Raw
if ($pyprojectContent -match 'python-dotenv\s*=\s*"\^1\.0\.0"') {
    Write-Host "   ✓ python-dotenv ^1.0.0 found in dependencies" -ForegroundColor Green
} else {
    Write-Host "   ✗ python-dotenv not found in pyproject.toml" -ForegroundColor Red
    exit 1
}

# Check if python-dotenv is installed
Write-Host ""
Write-Host "3. Checking if python-dotenv is installed..." -ForegroundColor Yellow
try {
    $dotenvInfo = poetry show python-dotenv 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✓ python-dotenv is installed" -ForegroundColor Green
        Write-Host "     $($dotenvInfo | Select-String 'version')" -ForegroundColor Gray
    } else {
        Write-Host "   ✗ python-dotenv not installed. Run: poetry install" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "   ✗ Error checking python-dotenv installation" -ForegroundColor Red
    exit 1
}

# Check for .env files
Write-Host ""
Write-Host "4. Checking for .env files..." -ForegroundColor Yellow
$envFiles = @('.env.local', '.env', '.env.native', '.env.development', '.env.production')
$foundFiles = @()
foreach ($file in $envFiles) {
    if (Test-Path $file) {
        $foundFiles += $file
        Write-Host "   ✓ Found: $file" -ForegroundColor Green
    }
}
if ($foundFiles.Count -eq 0) {
    Write-Host "   ⚠ No .env files found. Create .env.local from template:" -ForegroundColor Yellow
    Write-Host "     copy .env.native.template .env.local" -ForegroundColor Gray
}

# Test configuration loading
Write-Host ""
Write-Host "5. Testing configuration loading..." -ForegroundColor Yellow
$testScript = @"
import sys
from pathlib import Path

# Add libs to path
sys.path.insert(0, str(Path.cwd() / 'libs'))

try:
    from trading_models.config_manager import get_config_manager
    
    manager = get_config_manager()
    config = manager.get_config()
    
    print(f"✓ Configuration loaded successfully")
    print(f"  Environment: {config.environment}")
    print(f"  Database host: {config.database.host}")
    print(f"  Redis host: {config.redis.host}")
    print(f"  Debug mode: {config.debug}")
    
    sys.exit(0)
except Exception as e:
    print(f"✗ Error loading configuration: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
"@

try {
    $testScript | poetry run python -
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✓ Configuration manager working correctly" -ForegroundColor Green
    } else {
        Write-Host "   ✗ Configuration loading failed" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "   ✗ Error testing configuration: $_" -ForegroundColor Red
    exit 1
}

# Test environment variable parsing
Write-Host ""
Write-Host "6. Testing DATABASE_URL parsing..." -ForegroundColor Yellow
$testDbUrl = @"
import sys
import os
from pathlib import Path

# Add libs to path
sys.path.insert(0, str(Path.cwd() / 'libs'))

# Set test DATABASE_URL
os.environ['DATABASE_URL'] = 'postgresql://testuser:testpass@testhost:5433/testdb'

try:
    from trading_models.config_manager import ConfigurationManager
    
    manager = ConfigurationManager()
    db_config = manager.get_database_config()
    
    assert db_config.username == 'testuser', f"Expected username 'testuser', got '{db_config.username}'"
    assert db_config.password == 'testpass', f"Expected password 'testpass', got '{db_config.password}'"
    assert db_config.host == 'testhost', f"Expected host 'testhost', got '{db_config.host}'"
    assert db_config.port == 5433, f"Expected port 5433, got {db_config.port}"
    assert db_config.database == 'testdb', f"Expected database 'testdb', got '{db_config.database}'"
    
    print(f"✓ DATABASE_URL parsing works correctly")
    print(f"  Parsed: postgresql://{db_config.username}:***@{db_config.host}:{db_config.port}/{db_config.database}")
    
    sys.exit(0)
except AssertionError as e:
    print(f"✗ DATABASE_URL parsing failed: {e}")
    sys.exit(1)
except Exception as e:
    print(f"✗ Error testing DATABASE_URL: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
"@

try {
    $testDbUrl | poetry run python -
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✓ DATABASE_URL parsing working correctly" -ForegroundColor Green
    } else {
        Write-Host "   ✗ DATABASE_URL parsing failed" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "   ✗ Error testing DATABASE_URL: $_" -ForegroundColor Red
    exit 1
}

# Summary
Write-Host ""
Write-Host "=== Verification Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "✓ All checks passed!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Create .env.local from template if you haven't:" -ForegroundColor Gray
Write-Host "     copy .env.native.template .env.local" -ForegroundColor Gray
Write-Host "  2. Edit .env.local with your configuration" -ForegroundColor Gray
Write-Host "  3. Start the trading system:" -ForegroundColor Gray
Write-Host "     .\scripts\start-trading-system.ps1" -ForegroundColor Gray
Write-Host ""
