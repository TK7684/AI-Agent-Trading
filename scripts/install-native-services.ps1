#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Install PostgreSQL and Redis natively on Windows for the Trading System

.DESCRIPTION
    This script installs PostgreSQL 15 and Redis 7 as native Windows services
    using Chocolatey package manager. It configures both services for optimal
    trading system performance.

.PARAMETER SkipPostgres
    Skip PostgreSQL installation

.PARAMETER SkipRedis
    Skip Redis installation

.PARAMETER PostgresPassword
    Password for PostgreSQL trading user (default: auto-generated)

.EXAMPLE
    .\install-native-services.ps1
    Install both PostgreSQL and Redis with default settings

.EXAMPLE
    .\install-native-services.ps1 -SkipRedis
    Install only PostgreSQL
#>

param(
    [switch]$SkipPostgres,
    [switch]$SkipRedis,
    [string]$PostgresPassword
)

$ErrorActionPreference = "Stop"

# Colors for output
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-Error { Write-Host $args -ForegroundColor Red }

Write-Info "🚀 Trading System - Native Services Installer"
Write-Info "=" * 50

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Error "❌ This script must be run as Administrator"
    Write-Info "Right-click PowerShell and select 'Run as Administrator'"
    exit 1
}

# Install Chocolatey if not present
function Install-Chocolatey {
    if (Get-Command choco -ErrorAction SilentlyContinue) {
        Write-Success "✅ Chocolatey is already installed"
        return
    }
    
    Write-Info "📦 Installing Chocolatey package manager..."
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    
    try {
        Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
        Write-Success "✅ Chocolatey installed successfully"
        
        # Refresh environment variables
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    }
    catch {
        Write-Error "❌ Failed to install Chocolatey: $_"
        exit 1
    }
}


# Install PostgreSQL
function Install-PostgreSQL {
    param([string]$Password)
    
    Write-Info "`n🐘 Installing PostgreSQL 15..."
    
    # Check if already installed
    $pgService = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue
    if ($pgService) {
        Write-Warning "⚠️  PostgreSQL service already exists: $($pgService.Name)"
        $response = Read-Host "Do you want to reinstall? (y/N)"
        if ($response -ne 'y') {
            Write-Info "Skipping PostgreSQL installation"
            return
        }
    }
    
    # Install via Chocolatey
    try {
        choco install postgresql15 --params '/Password:postgres /Port:5432' -y
        Write-Success "✅ PostgreSQL 15 installed"
    }
    catch {
        Write-Error "❌ Failed to install PostgreSQL: $_"
        exit 1
    }
    
    # Wait for service to start
    Write-Info "Waiting for PostgreSQL service to start..."
    Start-Sleep -Seconds 10
    
    # Verify installation
    $pgService = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue
    if ($pgService -and $pgService.Status -eq 'Running') {
        Write-Success "✅ PostgreSQL service is running"
    }
    else {
        Write-Error "❌ PostgreSQL service is not running"
        Write-Info "Try starting it manually: net start postgresql-x64-15"
        exit 1
    }
    
    # Configure PostgreSQL
    Write-Info "Configuring PostgreSQL for trading system..."
    
    # Add PostgreSQL to PATH if not already there
    $pgPath = "C:\Program Files\PostgreSQL\15\bin"
    if (Test-Path $pgPath) {
        $currentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
        if ($currentPath -notlike "*$pgPath*") {
            [Environment]::SetEnvironmentVariable("Path", "$currentPath;$pgPath", "Machine")
            $env:Path += ";$pgPath"
            Write-Success "✅ Added PostgreSQL to PATH"
        }
    }
    
    # Create trading database and user
    Write-Info "Creating trading database and user..."
    
    if (-not $Password) {
        # Generate secure random password
        $Password = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 16 | ForEach-Object {[char]$_})
        Write-Info "Generated password for trading user: $Password"
        Write-Warning "⚠️  Save this password! You'll need it for .env configuration"
    }
    
    # Create SQL script
    $sqlScript = @"
-- Create trading user
CREATE USER trading WITH PASSWORD '$Password';

-- Create trading database
CREATE DATABASE trading OWNER trading;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE trading TO trading;
"@
    
    $sqlFile = "$env:TEMP\setup_trading_db.sql"
    $sqlScript | Out-File -FilePath $sqlFile -Encoding UTF8
    
    # Execute SQL script
    try {
        $env:PGPASSWORD = "postgres"
        & psql -U postgres -f $sqlFile 2>&1 | Out-Null
        Write-Success "✅ Trading database and user created"
        
        # Save password to file for reference
        $Password | Out-File -FilePath ".\postgres_password.txt" -Encoding UTF8
        Write-Info "Password saved to: postgres_password.txt"
    }
    catch {
        Write-Warning "⚠️  Database creation may have failed. You may need to create it manually."
        Write-Info "Run: psql -U postgres -c `"CREATE DATABASE trading;`""
    }
    finally {
        Remove-Item $sqlFile -ErrorAction SilentlyContinue
        Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
    }
    
    # Update pg_hba.conf for local connections
    $pgDataDir = "C:\Program Files\PostgreSQL\15\data"
    $pgHbaFile = Join-Path $pgDataDir "pg_hba.conf"
    
    if (Test-Path $pgHbaFile) {
        Write-Info "Configuring PostgreSQL authentication..."
        $hbaContent = Get-Content $pgHbaFile
        
        # Ensure local connections are allowed
        if ($hbaContent -notmatch "host\s+all\s+all\s+127.0.0.1/32\s+scram-sha-256") {
            Add-Content $pgHbaFile "`nhost    all             all             127.0.0.1/32            scram-sha-256"
            Write-Success "✅ Updated pg_hba.conf"
            
            # Restart PostgreSQL to apply changes
            Restart-Service postgresql-x64-15
            Start-Sleep -Seconds 5
        }
    }
    
    Write-Success "✅ PostgreSQL configuration complete"
}


# Install Redis
function Install-Redis {
    Write-Info "`n🔴 Installing Redis 7..."
    
    # Check if already installed
    $redisService = Get-Service -Name "Redis" -ErrorAction SilentlyContinue
    if ($redisService) {
        Write-Warning "⚠️  Redis service already exists"
        $response = Read-Host "Do you want to reinstall? (y/N)"
        if ($response -ne 'y') {
            Write-Info "Skipping Redis installation"
            return
        }
    }
    
    # Install via Chocolatey
    try {
        choco install redis-64 -y
        Write-Success "✅ Redis installed"
    }
    catch {
        Write-Error "❌ Failed to install Redis: $_"
        Write-Info "You can install manually from: https://github.com/microsoftarchive/redis/releases"
        exit 1
    }
    
    # Wait for service to start
    Write-Info "Waiting for Redis service to start..."
    Start-Sleep -Seconds 5
    
    # Verify installation
    $redisService = Get-Service -Name "Redis" -ErrorAction SilentlyContinue
    if ($redisService -and $redisService.Status -eq 'Running') {
        Write-Success "✅ Redis service is running"
    }
    else {
        Write-Warning "⚠️  Redis service is not running, attempting to start..."
        try {
            Start-Service Redis
            Start-Sleep -Seconds 3
            Write-Success "✅ Redis service started"
        }
        catch {
            Write-Error "❌ Failed to start Redis service: $_"
            exit 1
        }
    }
    
    # Configure Redis
    Write-Info "Configuring Redis for trading system..."
    
    $redisConfigPath = "C:\Program Files\Redis\redis.windows-service.conf"
    if (Test-Path $redisConfigPath) {
        # Backup original config
        Copy-Item $redisConfigPath "$redisConfigPath.backup" -Force
        
        # Update configuration
        $config = Get-Content $redisConfigPath
        
        # Set maxmemory to 1GB
        if ($config -notmatch "^maxmemory") {
            Add-Content $redisConfigPath "`nmaxmemory 1gb"
        }
        
        # Set maxmemory-policy
        if ($config -notmatch "^maxmemory-policy") {
            Add-Content $redisConfigPath "`nmaxmemory-policy allkeys-lru"
        }
        
        # Enable AOF persistence
        if ($config -notmatch "^appendonly yes") {
            Add-Content $redisConfigPath "`nappendonly yes"
        }
        
        Write-Success "✅ Redis configuration updated"
        
        # Restart Redis to apply changes
        Restart-Service Redis
        Start-Sleep -Seconds 3
    }
    
    Write-Success "✅ Redis configuration complete"
}

# Test database connections
function Test-DatabaseConnections {
    Write-Info "`n🔍 Testing database connections..."
    
    # Test PostgreSQL
    if (-not $SkipPostgres) {
        Write-Info "Testing PostgreSQL connection..."
        try {
            $env:PGPASSWORD = "postgres"
            $result = & psql -U postgres -c "SELECT version();" 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Success "✅ PostgreSQL connection successful"
            }
            else {
                Write-Warning "⚠️  PostgreSQL connection test failed"
            }
        }
        catch {
            Write-Warning "⚠️  Could not test PostgreSQL connection"
        }
        finally {
            Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
        }
    }
    
    # Test Redis
    if (-not $SkipRedis) {
        Write-Info "Testing Redis connection..."
        try {
            $redisCliPath = "C:\Program Files\Redis\redis-cli.exe"
            if (Test-Path $redisCliPath) {
                $result = & $redisCliPath PING
                if ($result -eq "PONG") {
                    Write-Success "✅ Redis connection successful"
                }
                else {
                    Write-Warning "⚠️  Redis connection test failed"
                }
            }
            else {
                Write-Warning "⚠️  redis-cli not found, skipping test"
            }
        }
        catch {
            Write-Warning "⚠️  Could not test Redis connection"
        }
    }
}

# Main execution
try {
    # Install Chocolatey
    Install-Chocolatey
    
    # Install PostgreSQL
    if (-not $SkipPostgres) {
        Install-PostgreSQL -Password $PostgresPassword
    }
    else {
        Write-Info "Skipping PostgreSQL installation"
    }
    
    # Install Redis
    if (-not $SkipRedis) {
        Install-Redis
    }
    else {
        Write-Info "Skipping Redis installation"
    }
    
    # Test connections
    Test-DatabaseConnections
    
    # Summary
    Write-Info "`n" + ("=" * 50)
    Write-Success "🎉 Native services installation complete!"
    Write-Info "`nInstalled services:"
    if (-not $SkipPostgres) {
        Write-Info "  • PostgreSQL 15 (Port 5432)"
        Write-Info "    - Database: trading"
        Write-Info "    - User: trading"
        Write-Info "    - Password: See postgres_password.txt"
    }
    if (-not $SkipRedis) {
        Write-Info "  • Redis 7 (Port 6379)"
    }
    
    Write-Info "`nNext steps:"
    Write-Info "  1. Update .env file with database credentials"
    Write-Info "  2. Run: .\scripts\init-database.ps1"
    Write-Info "  3. Run: .\scripts\start-trading-system.ps1"
    
}
catch {
    Write-Error "`n❌ Installation failed: $_"
    Write-Info "`nFor troubleshooting, check:"
    Write-Info "  • Windows Event Viewer"
    Write-Info "  • Chocolatey logs: C:\ProgramData\chocolatey\logs"
    exit 1
}
