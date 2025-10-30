<#
.SYNOPSIS
    Initialize the trading database schema and run migrations

.DESCRIPTION
    This script creates the trading database schema using Alembic migrations.
    It checks if the database exists, creates it if needed, and runs all pending migrations.

.PARAMETER Reset
    Drop and recreate the database (WARNING: destroys all data)

.PARAMETER DatabaseUrl
    PostgreSQL connection URL (default: from .env file)

.EXAMPLE
    .\init-database.ps1
    Initialize database with default settings

.EXAMPLE
    .\init-database.ps1 -Reset
    Reset database (development only)
#>

param(
    [switch]$Reset,
    [string]$DatabaseUrl
)

$ErrorActionPreference = "Stop"

# Add PostgreSQL to PATH if not already present
$pgPath = "C:\Program Files\PostgreSQL\17\bin"
if ((Test-Path $pgPath) -and ($env:Path -notlike "*$pgPath*")) {
    $env:Path += ";$pgPath"
}

# Colors for output
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-Error { Write-Host $args -ForegroundColor Red }

Write-Info "🗄️  Trading System - Database Initialization"
Write-Info "=" * 50

# Load environment variables from .env file
function Load-EnvFile {
    $envFile = ".env"
    if (-not (Test-Path $envFile)) {
        $envFile = ".env.local"
    }
    
    if (Test-Path $envFile) {
        Write-Info "Loading environment from: $envFile"
        Get-Content $envFile | ForEach-Object {
            if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
                $key = $matches[1].Trim()
                $value = $matches[2].Trim()
                [Environment]::SetEnvironmentVariable($key, $value, "Process")
            }
        }
    }
    else {
        Write-Warning "⚠️  No .env file found, using defaults"
    }
}

# Parse database URL
function Parse-DatabaseUrl {
    param([string]$Url)
    
    if ($Url -match 'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)') {
        return @{
            User = $matches[1]
            Password = $matches[2]
            Host = $matches[3]
            Port = $matches[4]
            Database = $matches[5]
        }
    }
    
    Write-Error "❌ Invalid DATABASE_URL format"
    Write-Info "Expected: postgresql://user:password@host:port/database"
    exit 1
}

# Check if database exists
function Test-DatabaseExists {
    param($DbConfig)
    
    try {
        $env:PGPASSWORD = $DbConfig.Password
        $result = & psql -h $DbConfig.Host -p $DbConfig.Port -U $DbConfig.User -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$($DbConfig.Database)'" 2>&1
        Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
        
        return $result -eq "1"
    }
    catch {
        Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
        return $false
    }
}

# Create database
function New-TradingDatabase {
    param($DbConfig)
    
    Write-Info "Creating database: $($DbConfig.Database)"
    
    try {
        $env:PGPASSWORD = $DbConfig.Password
        & psql -h $DbConfig.Host -p $DbConfig.Port -U $DbConfig.User -d postgres -c "CREATE DATABASE $($DbConfig.Database);" 2>&1 | Out-Null
        Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
        
        Write-Success "✅ Database created"
    }
    catch {
        Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
        Write-Error "❌ Failed to create database: $_"
        exit 1
    }
}

# Drop database
function Remove-TradingDatabase {
    param($DbConfig)
    
    Write-Warning "⚠️  Dropping database: $($DbConfig.Database)"
    
    $confirmation = Read-Host "Are you sure? This will delete ALL data! (type 'yes' to confirm)"
    if ($confirmation -ne 'yes') {
        Write-Info "Aborted"
        exit 0
    }
    
    try {
        $env:PGPASSWORD = $DbConfig.Password
        
        # Terminate existing connections
        & psql -h $DbConfig.Host -p $DbConfig.Port -U $DbConfig.User -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$($DbConfig.Database)';" 2>&1 | Out-Null
        
        # Drop database
        & psql -h $DbConfig.Host -p $DbConfig.Port -U $DbConfig.User -d postgres -c "DROP DATABASE IF EXISTS $($DbConfig.Database);" 2>&1 | Out-Null
        
        Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
        Write-Success "✅ Database dropped"
    }
    catch {
        Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
        Write-Error "❌ Failed to drop database: $_"
        exit 1
    }
}

# Run Alembic migrations
function Invoke-DatabaseMigrations {
    Write-Info "Running database migrations..."
    
    # Check if Poetry is available
    if (-not (Get-Command poetry -ErrorAction SilentlyContinue)) {
        Write-Error "❌ Poetry not found. Please install Poetry first."
        exit 1
    }
    
    try {
        # Run Alembic upgrade
        poetry run alembic upgrade head
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "✅ Migrations completed successfully"
        }
        else {
            Write-Error "❌ Migrations failed with exit code: $LASTEXITCODE"
            exit 1
        }
    }
    catch {
        Write-Error "❌ Failed to run migrations: $_"
        exit 1
    }
}

# Verify database schema
function Test-DatabaseSchema {
    param($DbConfig)
    
    Write-Info "Verifying database schema..."
    
    try {
        $env:PGPASSWORD = $DbConfig.Password
        $tables = & psql -h $DbConfig.Host -p $DbConfig.Port -U $DbConfig.User -d $DbConfig.Database -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" 2>&1
        Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
        
        if ($tables -gt 0) {
            Write-Success "✅ Database schema verified ($tables tables)"
            return $true
        }
        else {
            Write-Warning "⚠️  No tables found in database"
            return $false
        }
    }
    catch {
        Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
        Write-Warning "⚠️  Could not verify database schema"
        return $false
    }
}

# Main execution
try {
    # Load environment
    Load-EnvFile
    
    # Get database URL
    if (-not $DatabaseUrl) {
        $DatabaseUrl = $env:DATABASE_URL
    }
    
    if (-not $DatabaseUrl) {
        Write-Error "❌ DATABASE_URL not found in environment"
        Write-Info "Please set DATABASE_URL in .env file or pass -DatabaseUrl parameter"
        exit 1
    }
    
    # Parse database configuration
    $dbConfig = Parse-DatabaseUrl -Url $DatabaseUrl
    Write-Info "Database: $($dbConfig.Database) on $($dbConfig.Host):$($dbConfig.Port)"
    
    # Reset database if requested
    if ($Reset) {
        Remove-TradingDatabase -DbConfig $dbConfig
    }
    
    # Check if database exists
    $dbExists = Test-DatabaseExists -DbConfig $dbConfig
    
    if (-not $dbExists) {
        Write-Info "Database does not exist, creating..."
        New-TradingDatabase -DbConfig $dbConfig
    }
    else {
        Write-Success "✅ Database already exists"
    }
    
    # Run migrations
    Invoke-DatabaseMigrations
    
    # Verify schema
    $schemaValid = Test-DatabaseSchema -DbConfig $dbConfig
    
    # Summary
    Write-Info "`n" + ("=" * 50)
    Write-Success "🎉 Database initialization complete!"
    Write-Info "`nDatabase details:"
    Write-Info "  • Host: $($dbConfig.Host):$($dbConfig.Port)"
    Write-Info "  • Database: $($dbConfig.Database)"
    Write-Info "  • User: $($dbConfig.User)"
    
    if ($schemaValid) {
        Write-Info "`nNext steps:"
        Write-Info "  1. Run: .\scripts\start-trading-system.ps1"
    }
    else {
        Write-Warning "`n⚠️  Schema verification failed. Check migration logs."
    }
}
catch {
    Write-Error "`n❌ Database initialization failed: $_"
    Write-Info "`nTroubleshooting:"
    Write-Info "  • Check PostgreSQL is running: Get-Service postgresql*"
    Write-Info "  • Verify DATABASE_URL in .env file"
    Write-Info "  • Check PostgreSQL logs"
    exit 1
}
