<#
.SYNOPSIS
    Reset trading database for development

.DESCRIPTION
    Drops and recreates the trading database, then runs all migrations.
    FOR DEVELOPMENT USE ONLY - destroys all data!

.PARAMETER Force
    Skip confirmation prompt

.EXAMPLE
    .\Reset-TradingDatabase.ps1
    Reset database with confirmation

.EXAMPLE
    .\Reset-TradingDatabase.ps1 -Force
    Reset database without confirmation
#>

param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"

# Colors for output
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-Error { Write-Host $args -ForegroundColor Red }

Write-Warning "⚠️  Trading System - Database Reset (DEVELOPMENT ONLY)"
Write-Info "=" * 50

# Safety check
if (-not $Force) {
    Write-Warning "`n⚠️  WARNING: This will DELETE ALL DATA in the database!"
    Write-Warning "This operation is intended for DEVELOPMENT ONLY."
    $confirmation = Read-Host "`nType 'RESET' to confirm"
    
    if ($confirmation -ne 'RESET') {
        Write-Info "Reset cancelled"
        exit 0
    }
}

# Load environment variables
function Load-EnvFile {
    $envFiles = @(".env.local", ".env", ".env.native")
    
    foreach ($envFile in $envFiles) {
        if (Test-Path $envFile) {
            Write-Info "Loading environment from: $envFile"
            Get-Content $envFile | ForEach-Object {
                if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
                    $key = $matches[1].Trim()
                    $value = $matches[2].Trim()
                    [Environment]::SetEnvironmentVariable($key, $value, "Process")
                }
            }
            break
        }
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
    exit 1
}

# Main execution
try {
    # Load environment
    Load-EnvFile
    
    # Get database URL
    $databaseUrl = $env:DATABASE_URL
    if (-not $databaseUrl) {
        Write-Error "❌ DATABASE_URL not found in environment"
        exit 1
    }
    
    # Parse database configuration
    $dbConfig = Parse-DatabaseUrl -Url $databaseUrl
    Write-Info "Database: $($dbConfig.Database) on $($dbConfig.Host):$($dbConfig.Port)"
    
    # Drop database
    Write-Info "`nDropping database..."
    try {
        $env:PGPASSWORD = $dbConfig.Password
        
        # Terminate existing connections
        & psql -h $dbConfig.Host -p $dbConfig.Port -U $dbConfig.User -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$($DbConfig.Database)' AND pid <> pg_backend_pid();" 2>&1 | Out-Null
        
        # Drop database
        & psql -h $dbConfig.Host -p $dbConfig.Port -U $dbConfig.User -d postgres -c "DROP DATABASE IF EXISTS $($dbConfig.Database);" 2>&1 | Out-Null
        
        Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
        Write-Success "✅ Database dropped"
    }
    catch {
        Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
        Write-Error "❌ Failed to drop database: $_"
        exit 1
    }
    
    # Create database
    Write-Info "Creating fresh database..."
    try {
        $env:PGPASSWORD = $dbConfig.Password
        & psql -h $dbConfig.Host -p $dbConfig.Port -U $dbConfig.User -d postgres -c "CREATE DATABASE $($dbConfig.Database);" 2>&1 | Out-Null
        Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
        Write-Success "✅ Database created"
    }
    catch {
        Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
        Write-Error "❌ Failed to create database: $_"
        exit 1
    }
    
    # Run migrations
    Write-Info "Running migrations..."
    if (-not (Get-Command poetry -ErrorAction SilentlyContinue)) {
        Write-Error "❌ Poetry not found"
        exit 1
    }
    
    poetry run alembic upgrade head
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "✅ Migrations completed"
    }
    else {
        Write-Error "❌ Migrations failed"
        exit 1
    }
    
    # Verify schema
    Write-Info "Verifying schema..."
    try {
        $env:PGPASSWORD = $dbConfig.Password
        $tables = & psql -h $dbConfig.Host -p $dbConfig.Port -U $dbConfig.User -d $dbConfig.Database -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" 2>&1
        Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
        
        if ($tables -gt 0) {
            Write-Success "✅ Schema verified ($tables tables)"
        }
        else {
            Write-Warning "⚠️  No tables found"
        }
    }
    catch {
        Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
        Write-Warning "⚠️  Could not verify schema"
    }
    
    # Summary
    Write-Info "`n" + ("=" * 50)
    Write-Success "🎉 Database reset complete!"
    Write-Info "`nDatabase is now in a clean state with latest schema."
    Write-Info "`nNext steps:"
    Write-Info "  1. Run: .\scripts\start-trading-system.ps1"
    Write-Info "  2. System will start with empty database"
}
catch {
    Write-Error "`n❌ Database reset failed: $_"
    Write-Info "`nTroubleshooting:"
    Write-Info "  • Check PostgreSQL is running"
    Write-Info "  • Verify DATABASE_URL in .env file"
    Write-Info "  • Check PostgreSQL logs"
    exit 1
}
