<#
.SYNOPSIS
    PostgreSQL password reset helper with step-by-step guidance

.DESCRIPTION
    Comprehensive PostgreSQL password reset utility that provides both automated
    and manual password reset options. Includes detailed instructions and
    integrates with the database setup system.

.PARAMETER NewPassword
    Specify the new password to set (optional)

.PARAMETER AutoMode
    Run in automatic mode with minimal prompts

.PARAMETER ManualOnly
    Show manual instructions only without attempting automated reset

.EXAMPLE
    .\Reset-PostgreSQL-Password.ps1
    
.EXAMPLE
    .\Reset-PostgreSQL-Password.ps1 -NewPassword "mypassword123"
    
.EXAMPLE
    .\Reset-PostgreSQL-Password.ps1 -ManualOnly
#>

param(
    [string]$NewPassword = "",
    [switch]$AutoMode = $false,
    [switch]$ManualOnly = $false
)

# Require Administrator privileges for service operations
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "❌ This script requires Administrator privileges for service operations" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please run PowerShell as Administrator and try again:" -ForegroundColor Yellow
    Write-Host "1. Right-click PowerShell" -ForegroundColor Cyan
    Write-Host "2. Select 'Run as Administrator'" -ForegroundColor Cyan
    Write-Host "3. Navigate to this directory and run the script again" -ForegroundColor Cyan
    exit 1
}

# Add PostgreSQL to PATH
$pgPath = "C:\Program Files\PostgreSQL\17\bin"
if ((Test-Path $pgPath) -and ($env:Path -notlike "*$pgPath*")) {
    $env:Path += ";$pgPath"
}

function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-Error { Write-Host $args -ForegroundColor Red }
function Write-Step { Write-Host "🔧 $args" -ForegroundColor Magenta }

Write-Info "🔐 PostgreSQL Password Reset Helper"
Write-Info "=" * 60
Write-Host ""

if ($ManualOnly) {
    Write-Info "Showing manual reset instructions only..."
} elseif ($AutoMode) {
    Write-Info "Running in automatic mode..."
} else {
    Write-Info "This tool will help you reset your PostgreSQL password."
    Write-Info "Choose from automated reset or detailed manual instructions."
}

# PostgreSQL service names to check
$PostgresServiceNames = @(
    "postgresql-x64-17", "postgresql-x64-16", "postgresql-x64-15",
    "postgresql-x64-14", "postgresql-x64-13", "postgresql", "PostgreSQL"
)

# Step 1: Find PostgreSQL installation
Write-Step "Detecting PostgreSQL installation..."

$pgInstallPath = ""
$pgDataPath = ""
$pgVersion = ""
$serviceName = ""

# Common installation paths
$commonPaths = @(
    "C:\Program Files\PostgreSQL\17",
    "C:\Program Files\PostgreSQL\16", 
    "C:\Program Files\PostgreSQL\15",
    "C:\Program Files\PostgreSQL\14",
    "C:\Program Files\PostgreSQL\13",
    "C:\Program Files (x86)\PostgreSQL\17",
    "C:\Program Files (x86)\PostgreSQL\16"
)

foreach ($path in $commonPaths) {
    if (Test-Path "$path\bin\postgres.exe") {
        $pgInstallPath = $path
        $pgVersion = Split-Path $path -Leaf
        $pgDataPath = "$path\data"
        Write-Success "✓ Found PostgreSQL $pgVersion at: $path"
        break
    }
}

if (-not $pgInstallPath) {
    Write-Error "❌ PostgreSQL installation not found in common locations"
    Write-Host ""
    Write-Info "Manual detection required:"
    Write-Info "1. Find your PostgreSQL installation directory"
    Write-Info "2. Look for the 'data' subdirectory"
    Write-Info "3. Note the path for manual configuration below"
    Write-Host ""
}

# Step 2: Find running service
Write-Step "Checking PostgreSQL service status..."

$runningService = $null
foreach ($svcName in $PostgresServiceNames) {
    try {
        $service = Get-Service -Name $svcName -ErrorAction SilentlyContinue
        if ($service) {
            $serviceName = $svcName
            $runningService = $service
            Write-Info "Found service: $svcName (Status: $($service.Status))"
            break
        }
    }
    catch {
        # Service doesn't exist, continue
    }
}

if (-not $runningService) {
    Write-Warning "⚠️  No PostgreSQL service found"
    Write-Info "You may need to install PostgreSQL or check service names manually"
} else {
    Write-Success "✓ PostgreSQL service: $serviceName"
}

# Manual instructions
if ($ManualOnly -or -not $pgInstallPath -or -not $runningService) {
    Write-Host ""
    Write-Step "Manual Password Reset Instructions"
    Write-Host ""
    
    Write-Info "📋 Method 1: Using pg_hba.conf (Recommended)"
    Write-Host ""
    Write-Info "1. Stop PostgreSQL service:"
    Write-Host "   Stop-Service $($serviceName -or 'postgresql-x64-17')" -ForegroundColor Cyan
    Write-Host ""
    
    Write-Info "2. Edit pg_hba.conf file:"
    if ($pgDataPath) {
        Write-Host "   File location: $pgDataPath\pg_hba.conf" -ForegroundColor Cyan
    } else {
        Write-Host "   File location: C:\Program Files\PostgreSQL\[VERSION]\data\pg_hba.conf" -ForegroundColor Cyan
    }
    Write-Host ""
    Write-Info "   Find lines like:"
    Write-Host "   # IPv4 local connections:" -ForegroundColor Gray
    Write-Host "   host    all             all             127.0.0.1/32            md5" -ForegroundColor Gray
    Write-Host ""
    Write-Info "   Change 'md5' to 'trust':"
    Write-Host "   host    all             all             127.0.0.1/32            trust" -ForegroundColor Green
    Write-Host ""
    
    Write-Info "3. Start PostgreSQL service:"
    Write-Host "   Start-Service $($serviceName -or 'postgresql-x64-17')" -ForegroundColor Cyan
    Write-Host ""
    
    Write-Info "4. Connect without password and reset:"
    Write-Host "   psql -U postgres" -ForegroundColor Cyan
    Write-Host "   ALTER USER postgres WITH PASSWORD 'your_new_password';" -ForegroundColor Cyan
    Write-Host "   CREATE USER trading WITH PASSWORD 'your_new_password';" -ForegroundColor Cyan
    Write-Host "   GRANT ALL PRIVILEGES ON DATABASE trading TO trading;" -ForegroundColor Cyan
    Write-Host "   \q" -ForegroundColor Cyan
    Write-Host ""
    
    Write-Info "5. Restore pg_hba.conf:"
    Write-Host "   Change 'trust' back to 'md5'" -ForegroundColor Cyan
    Write-Host ""
    
    Write-Info "6. Restart PostgreSQL service:"
    Write-Host "   Restart-Service $($serviceName -or 'postgresql-x64-17')" -ForegroundColor Cyan
    Write-Host ""
    
    Write-Info "7. Update your .env.local file:"
    Write-Host "   DATABASE_URL=postgresql://trading:your_new_password@localhost:5432/trading" -ForegroundColor Green
    Write-Host ""
    
    Write-Host "=" * 60
    Write-Host ""
    
    Write-Info "📋 Method 2: Reinstall PostgreSQL (If Method 1 fails)"
    Write-Host ""
    Write-Info "1. Uninstall PostgreSQL from Control Panel"
    Write-Info "2. Download latest PostgreSQL from: https://www.postgresql.org/download/windows/"
    Write-Info "3. During installation, set a memorable password"
    Write-Info "4. Run: .\scripts\Setup-Database.ps1"
    Write-Host ""
    
    if ($ManualOnly) {
        return
    }
}

# Automated reset attempt
if (-not $ManualOnly -and $pgInstallPath -and $runningService) {
    Write-Host ""
    Write-Step "Attempting automated password reset..."
    
    if (-not $NewPassword) {
        if (-not $AutoMode) {
            Write-Info "Enter new PostgreSQL password (or press Enter for 'postgres'):"
            $securePassword = Read-Host "New password" -AsSecureString
            $NewPassword = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword))
            
            if (-not $NewPassword) {
                $NewPassword = "postgres"
                Write-Info "Using default password: 'postgres'"
            }
        } else {
            $NewPassword = "postgres"
            Write-Info "Auto mode: Using default password 'postgres'"
        }
    }
    
    try {
        # Step 1: Stop PostgreSQL service
        Write-Info "1. Stopping PostgreSQL service..."
        Stop-Service -Name $serviceName -Force
        Start-Sleep -Seconds 3
        Write-Success "✓ Service stopped"
        
        # Step 2: Backup pg_hba.conf
        $pgHbaPath = "$pgDataPath\pg_hba.conf"
        $backupPath = "$pgDataPath\pg_hba.conf.backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
        
        if (Test-Path $pgHbaPath) {
            Write-Info "2. Backing up pg_hba.conf..."
            Copy-Item $pgHbaPath $backupPath
            Write-Success "✓ Backup created: $backupPath"
            
            # Step 3: Modify pg_hba.conf
            Write-Info "3. Modifying pg_hba.conf for trust authentication..."
            $content = Get-Content $pgHbaPath
            $newContent = $content | ForEach-Object {
                if ($_ -match "^host\s+all\s+all\s+127\.0\.0\.1/32\s+md5") {
                    $_ -replace "md5", "trust"
                } elseif ($_ -match "^host\s+all\s+all\s+::1/128\s+md5") {
                    $_ -replace "md5", "trust"
                } else {
                    $_
                }
            }
            $newContent | Out-File -FilePath $pgHbaPath -Encoding UTF8
            Write-Success "✓ pg_hba.conf modified for trust authentication"
        } else {
            Write-Warning "⚠️  pg_hba.conf not found at expected location: $pgHbaPath"
            throw "Cannot find pg_hba.conf file"
        }
        
        # Step 4: Start PostgreSQL service
        Write-Info "4. Starting PostgreSQL service..."
        Start-Service -Name $serviceName
        Start-Sleep -Seconds 5
        Write-Success "✓ Service started"
        
        # Step 5: Reset password
        Write-Info "5. Resetting PostgreSQL password..."
        
        $sqlCommands = @"
ALTER USER postgres WITH PASSWORD '$NewPassword';
CREATE DATABASE IF NOT EXISTS trading;
DO `$`$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'trading') THEN
        CREATE USER trading WITH PASSWORD '$NewPassword';
    END IF;
END
`$`$;
ALTER USER trading WITH PASSWORD '$NewPassword';
GRANT ALL PRIVILEGES ON DATABASE trading TO trading;
ALTER USER trading CREATEDB;
"@
        
        $tempSqlFile = [System.IO.Path]::GetTempFileName() + ".sql"
        $sqlCommands | Out-File -FilePath $tempSqlFile -Encoding UTF8
        
        try {
            $result = psql -U postgres -d postgres -f $tempSqlFile 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Success "✓ Password reset successful"
                Write-Success "✓ Trading user created/updated"
            } else {
                Write-Warning "⚠️  Password reset may have failed: $result"
            }
        }
        finally {
            if (Test-Path $tempSqlFile) { Remove-Item $tempSqlFile }
        }
        
        # Step 6: Restore pg_hba.conf
        Write-Info "6. Restoring pg_hba.conf..."
        Copy-Item $backupPath $pgHbaPath
        Write-Success "✓ pg_hba.conf restored"
        
        # Step 7: Restart service
        Write-Info "7. Restarting PostgreSQL service..."
        Restart-Service -Name $serviceName
        Start-Sleep -Seconds 5
        Write-Success "✓ Service restarted"
        
        # Step 8: Test new password
        Write-Info "8. Testing new password..."
        $env:PGPASSWORD = $NewPassword
        $testResult = psql -U postgres -d postgres -c "SELECT version();" 2>&1
        Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "✅ Password reset completed successfully!"
            Write-Host ""
            Write-Info "New password set to: '$NewPassword'"
            Write-Host ""
            Write-Info "📋 Next steps:"
            Write-Info "1. Update your .env.local file:"
            Write-Host "   DATABASE_URL=postgresql://trading:$NewPassword@localhost:5432/trading" -ForegroundColor Green
            Write-Host ""
            Write-Info "2. Run the setup wizard to complete configuration:"
            Write-Host "   .\scripts\Setup-Database.ps1" -ForegroundColor Cyan
            Write-Host ""
            Write-Info "3. Or test the connection:"
            Write-Host "   .\scripts\Test-DatabaseConnection.ps1" -ForegroundColor Cyan
        } else {
            Write-Warning "⚠️  Password test failed, but reset may have succeeded"
            Write-Info "Try connecting manually with password: '$NewPassword'"
        }
        
    }
    catch {
        Write-Error "❌ Automated reset failed: $($_.Exception.Message)"
        Write-Host ""
        Write-Info "🔧 Fallback options:"
        Write-Info "1. Try manual reset instructions above"
        Write-Info "2. Run with -ManualOnly flag for detailed steps"
        Write-Info "3. Consider reinstalling PostgreSQL"
        Write-Host ""
        
        # Try to restore service if it was stopped
        try {
            if ($runningService.Status -eq "Stopped") {
                Start-Service -Name $serviceName -ErrorAction SilentlyContinue
            }
        }
        catch {
            Write-Warning "⚠️  Could not restart PostgreSQL service"
        }
        
        exit 1
    }
}

Write-Host ""
Write-Info "🔐 Password reset process completed"
Write-Host ""

if (-not $ManualOnly) {
    Write-Info "💡 Tips for the future:"
    Write-Info "• Use a password manager to store your PostgreSQL password"
    Write-Info "• Consider using environment variables for sensitive data"
    Write-Info "• Regular backups can prevent data loss during resets"
    Write-Info "• Document your password in a secure location"
}

Write-Host ""