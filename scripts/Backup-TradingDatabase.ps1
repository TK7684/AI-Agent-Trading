<#
.SYNOPSIS
    Backup trading database

.DESCRIPTION
    Creates a compressed backup of the trading database using pg_dump.
    Includes timestamp and optional compression.

.PARAMETER OutputPath
    Directory for backup files (default: ./backups)

.PARAMETER Compress
    Compress backup with gzip

.PARAMETER SchemaOnly
    Backup schema only (no data)

.EXAMPLE
    .\Backup-TradingDatabase.ps1
    Create full backup

.EXAMPLE
    .\Backup-TradingDatabase.ps1 -Compress
    Create compressed backup

.EXAMPLE
    .\Backup-TradingDatabase.ps1 -SchemaOnly
    Backup schema only
#>

param(
    [string]$OutputPath = "backups",
    [switch]$Compress,
    [switch]$SchemaOnly
)

$ErrorActionPreference = "Stop"

# Colors for output
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-Error { Write-Host $args -ForegroundColor Red }

Write-Info "💾 Trading System - Database Backup"
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

# Create backup
function New-DatabaseBackup {
    param(
        $DbConfig,
        [string]$BackupPath,
        [bool]$CompressBackup,
        [bool]$SchemaOnlyBackup
    )
    
    Write-Info "Creating backup of: $($DbConfig.Database)"
    
    try {
        $env:PGPASSWORD = $DbConfig.Password
        
        # Build pg_dump command
        $dumpArgs = @(
            "-h", $DbConfig.Host,
            "-p", $DbConfig.Port,
            "-U", $DbConfig.User,
            "-d", $DbConfig.Database,
            "-F", "c",  # Custom format
            "-f", $BackupPath
        )
        
        if ($SchemaOnlyBackup) {
            $dumpArgs += "-s"
            Write-Info "Backup mode: Schema only"
        }
        else {
            Write-Info "Backup mode: Full (schema + data)"
        }
        
        # Execute backup
        & pg_dump @dumpArgs
        
        Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
        
        if ($LASTEXITCODE -eq 0) {
            $fileSize = (Get-Item $BackupPath).Length / 1MB
            Write-Success "✅ Backup created: $BackupPath"
            Write-Info "   Size: $([math]::Round($fileSize, 2)) MB"
            
            # Compress if requested
            if ($CompressBackup) {
                Write-Info "Compressing backup..."
                $gzipPath = "$BackupPath.gz"
                
                # Use 7-Zip if available, otherwise skip compression
                if (Get-Command 7z -ErrorAction SilentlyContinue) {
                    & 7z a -tgzip $gzipPath $BackupPath | Out-Null
                    Remove-Item $BackupPath
                    $compressedSize = (Get-Item $gzipPath).Length / 1MB
                    Write-Success "✅ Compressed: $gzipPath"
                    Write-Info "   Size: $([math]::Round($compressedSize, 2)) MB"
                }
                else {
                    Write-Warning "⚠️  7-Zip not found, skipping compression"
                }
            }
            
            return $true
        }
        else {
            Write-Error "❌ Backup failed with exit code: $LASTEXITCODE"
            return $false
        }
    }
    catch {
        Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
        Write-Error "❌ Backup error: $_"
        return $false
    }
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
    
    # Create backup directory
    if (-not (Test-Path $OutputPath)) {
        New-Item -ItemType Directory -Path $OutputPath | Out-Null
        Write-Info "Created backup directory: $OutputPath"
    }
    
    # Generate backup filename
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupType = if ($SchemaOnly) { "schema" } else { "full" }
    $backupFile = "$($dbConfig.Database)_${backupType}_${timestamp}.backup"
    $backupPath = Join-Path $OutputPath $backupFile
    
    # Create backup
    $success = New-DatabaseBackup `
        -DbConfig $dbConfig `
        -BackupPath $backupPath `
        -CompressBackup $Compress `
        -SchemaOnlyBackup $SchemaOnly
    
    if ($success) {
        Write-Info "`n" + ("=" * 50)
        Write-Success "🎉 Database backup complete!"
        Write-Info "`nBackup location: $backupPath"
        
        # List recent backups
        Write-Info "`nRecent backups:"
        Get-ChildItem $OutputPath -Filter "*.backup*" | 
            Sort-Object LastWriteTime -Descending | 
            Select-Object -First 5 | 
            ForEach-Object {
                $size = [math]::Round($_.Length / 1MB, 2)
                Write-Info "  • $($_.Name) ($size MB) - $($_.LastWriteTime)"
            }
    }
    else {
        Write-Error "`n❌ Backup failed"
        exit 1
    }
}
catch {
    Write-Error "`n❌ Backup failed: $_"
    Write-Info "`nTroubleshooting:"
    Write-Info "  • Check PostgreSQL is running"
    Write-Info "  • Verify pg_dump is in PATH"
    Write-Info "  • Check DATABASE_URL in .env file"
    exit 1
}
