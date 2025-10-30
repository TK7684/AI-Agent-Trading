<#
.SYNOPSIS
    Restore trading database from backup

.DESCRIPTION
    Restores a trading database from a pg_dump backup file.
    Supports both compressed and uncompressed backups.

.PARAMETER BackupFile
    Path to backup file to restore

.PARAMETER Force
    Skip confirmation prompt

.EXAMPLE
    .\Restore-TradingDatabase.ps1 -BackupFile backups/trading_full_20241007.backup

.EXAMPLE
    .\Restore-TradingDatabase.ps1 -BackupFile backups/trading_full_20241007.backup.gz -Force
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$BackupFile,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

# Colors for output
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-Error { Write-Host $args -ForegroundColor Red }

Write-Info "♻️  Trading System - Database Restore"
Write-Info "=" * 50

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

# Restore database
function Restore-Database {
    param(
        $DbConfig,
        [string]$BackupPath
    )
    
    Write-Warning "⚠️  This will REPLACE all data in: $($DbConfig.Database)"
    
    if (-not $Force) {
        $confirmation = Read-Host "Are you sure? Type 'yes' to confirm"
        if ($confirmation -ne 'yes') {
            Write-Info "Restore cancelled"
            exit 0
        }
    }
    
    Write-Info "Restoring from: $BackupPath"
    
    try {
        $env:PGPASSWORD = $DbConfig.Password
        
        # Terminate existing connections
        Write-Info "Terminating existing connections..."
        & psql -h $DbConfig.Host -p $DbConfig.Port -U $DbConfig.User -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$($DbConfig.Database)' AND pid <> pg_backend_pid();" 2>&1 | Out-Null
        
        # Drop and recreate database
        Write-Info "Recreating database..."
        & psql -h $DbConfig.Host -p $DbConfig.Port -U $DbConfig.User -d postgres -c "DROP DATABASE IF EXISTS $($DbConfig.Database);" 2>&1 | Out-Null
        & psql -h $DbConfig.Host -p $DbConfig.Port -U $DbConfig.User -d postgres -c "CREATE DATABASE $($DbConfig.Database);" 2>&1 | Out-Null
        
        # Restore backup
        Write-Info "Restoring data..."
        & pg_restore -h $DbConfig.Host -p $DbConfig.Port -U $DbConfig.User -d $DbConfig.Database -v $BackupPath
        
        Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "✅ Database restored successfully"
            return $true
        }
        else {
            Write-Warning "⚠️  Restore completed with warnings (exit code: $LASTEXITCODE)"
            return $true
        }
    }
    catch {
        Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
        Write-Error "❌ Restore error: $_"
        return $false
    }
}

# Main execution
try {
    # Check backup file exists
    if (-not (Test-Path $BackupFile)) {
        Write-Error "❌ Backup file not found: $BackupFile"
        exit 1
    }
    
    # Decompress if needed
    $restoreFile = $BackupFile
    if ($BackupFile -match '\.gz$') {
        Write-Info "Decompressing backup..."
        $restoreFile = $BackupFile -replace '\.gz$', ''
        
        if (Get-Command 7z -ErrorAction SilentlyContinue) {
            & 7z x -y $BackupFile -o"$(Split-Path $restoreFile)" | Out-Null
        }
        else {
            Write-Error "❌ 7-Zip not found. Cannot decompress .gz file"
            exit 1
        }
    }
    
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
    
    # Restore database
    $success = Restore-Database -DbConfig $dbConfig -BackupPath $restoreFile
    
    # Cleanup decompressed file if we created it
    if ($BackupFile -match '\.gz$' -and (Test-Path $restoreFile)) {
        Remove-Item $restoreFile
    }
    
    if ($success) {
        Write-Info "`n" + ("=" * 50)
        Write-Success "🎉 Database restore complete!"
        Write-Info "`nDatabase: $($dbConfig.Database)"
        Write-Info "Restored from: $BackupFile"
        
        Write-Info "`nNext steps:"
        Write-Info "  1. Verify data integrity"
        Write-Info "  2. Run: .\scripts\start-trading-system.ps1"
    }
    else {
        Write-Error "`n❌ Restore failed"
        exit 1
    }
}
catch {
    Write-Error "`n❌ Restore failed: $_"
    Write-Info "`nTroubleshooting:"
    Write-Info "  • Check PostgreSQL is running"
    Write-Info "  • Verify pg_restore is in PATH"
    Write-Info "  • Check backup file integrity"
    exit 1
}
