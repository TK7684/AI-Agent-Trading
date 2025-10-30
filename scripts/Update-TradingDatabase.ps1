<#
.SYNOPSIS
    Update trading database schema with pending migrations

.DESCRIPTION
    Runs pending Alembic migrations and provides rollback support.
    Checks current schema version and applies migrations safely.

.PARAMETER Rollback
    Rollback to previous migration version

.PARAMETER Version
    Target migration version (for upgrade or downgrade)

.PARAMETER ShowHistory
    Display migration history

.EXAMPLE
    .\Update-TradingDatabase.ps1
    Apply all pending migrations

.EXAMPLE
    .\Update-TradingDatabase.ps1 -Rollback
    Rollback last migration

.EXAMPLE
    .\Update-TradingDatabase.ps1 -Version abc123
    Migrate to specific version
#>

param(
    [switch]$Rollback,
    [string]$Version,
    [switch]$ShowHistory
)

$ErrorActionPreference = "Stop"

# Colors for output
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-Error { Write-Host $args -ForegroundColor Red }

Write-Info "🔄 Trading System - Database Migration Manager"
Write-Info "=" * 50

# Check Poetry
if (-not (Get-Command poetry -ErrorAction SilentlyContinue)) {
    Write-Error "❌ Poetry not found. Please install Poetry first."
    exit 1
}

# Show migration history
if ($ShowHistory) {
    Write-Info "Migration History:"
    poetry run alembic history --verbose
    exit 0
}

# Get current version
function Get-CurrentVersion {
    Write-Info "Checking current schema version..."
    try {
        $output = poetry run alembic current 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Success "✅ Current version retrieved"
            Write-Host $output
            return $true
        }
        else {
            Write-Warning "⚠️  Could not determine current version"
            return $false
        }
    }
    catch {
        Write-Warning "⚠️  Error checking version: $_"
        return $false
    }
}

# Apply migrations
function Invoke-Upgrade {
    param([string]$TargetVersion = "head")
    
    Write-Info "Applying migrations to: $TargetVersion"
    
    try {
        poetry run alembic upgrade $TargetVersion
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "✅ Migrations applied successfully"
            return $true
        }
        else {
            Write-Error "❌ Migration failed with exit code: $LASTEXITCODE"
            return $false
        }
    }
    catch {
        Write-Error "❌ Migration error: $_"
        return $false
    }
}

# Rollback migrations
function Invoke-Downgrade {
    param([string]$TargetVersion = "-1")
    
    Write-Warning "⚠️  Rolling back to: $TargetVersion"
    
    $confirmation = Read-Host "Are you sure you want to rollback? (type 'yes' to confirm)"
    if ($confirmation -ne 'yes') {
        Write-Info "Rollback cancelled"
        return $false
    }
    
    try {
        poetry run alembic downgrade $TargetVersion
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "✅ Rollback completed successfully"
            return $true
        }
        else {
            Write-Error "❌ Rollback failed with exit code: $LASTEXITCODE"
            return $false
        }
    }
    catch {
        Write-Error "❌ Rollback error: $_"
        return $false
    }
}

# Main execution
try {
    # Show current version
    Get-CurrentVersion
    
    # Execute requested operation
    if ($Rollback) {
        $target = if ($Version) { $Version } else { "-1" }
        $success = Invoke-Downgrade -TargetVersion $target
    }
    elseif ($Version) {
        $success = Invoke-Upgrade -TargetVersion $Version
    }
    else {
        $success = Invoke-Upgrade
    }
    
    if ($success) {
        Write-Info "`n" + ("=" * 50)
        Write-Success "🎉 Database migration complete!"
        
        # Show new version
        Write-Info "`nNew schema version:"
        Get-CurrentVersion | Out-Null
    }
    else {
        Write-Error "`n❌ Migration operation failed"
        Write-Info "`nTroubleshooting:"
        Write-Info "  • Check migration files in alembic/versions/"
        Write-Info "  • Review database logs"
        Write-Info "  • Verify database connectivity"
        exit 1
    }
}
catch {
    Write-Error "`n❌ Migration failed: $_"
    exit 1
}
