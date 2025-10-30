<#
.SYNOPSIS
    Enhanced database connection tester with comprehensive diagnostics

.DESCRIPTION
    Advanced database connection testing that integrates with the new database validation system.
    Provides detailed diagnostics, error analysis, and actionable recommendations.

.PARAMETER Detailed
    Show detailed diagnostic information

.PARAMETER QuickTest
    Run only a quick connection test without full diagnostics

.EXAMPLE
    .\Test-DatabaseConnection.ps1
    
.EXAMPLE
    .\Test-DatabaseConnection.ps1 -Detailed
    
.EXAMPLE
    .\Test-DatabaseConnection.ps1 -QuickTest
#>

param(
    [switch]$Detailed = $false,
    [switch]$QuickTest = $false
)

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

Write-Info "🔐 Enhanced Database Connection Tester"
Write-Info "=" * 60
Write-Host ""

# Check if .env.local exists and has DATABASE_URL
$envFile = ".env.local"
$databaseUrl = $null

if (Test-Path $envFile) {
    Write-Step "Checking existing configuration..."
    $envContent = Get-Content $envFile
    $dbUrlLine = $envContent | Where-Object { $_ -match "^DATABASE_URL=" }
    
    if ($dbUrlLine) {
        $databaseUrl = ($dbUrlLine -split "=", 2)[1]
        Write-Success "✓ Found DATABASE_URL in .env.local"
        
        if ($databaseUrl -match "YOUR_PASSWORD_HERE") {
            Write-Warning "⚠️  DATABASE_URL contains placeholder password"
            $databaseUrl = $null
        } else {
            Write-Info "   URL: $($databaseUrl -replace ':[^@]*@', ':***@')"  # Hide password
        }
    } else {
        Write-Warning "⚠️  No DATABASE_URL found in .env.local"
    }
} else {
    Write-Warning "⚠️  .env.local file not found"
}

# Test existing configuration first if available
if ($databaseUrl -and -not $QuickTest) {
    Write-Step "Testing existing configuration..."
    
    # Use Python validator for comprehensive testing
    $pythonTest = @"
import os
import sys
from libs.trading_models.db_validator import DatabaseValidator
from libs.trading_models.config_manager import ConfigurationManager

try:
    # Test with existing configuration
    config_manager = ConfigurationManager()
    database_url = config_manager.get_database_url()
    
    if not database_url:
        print('❌ No database URL in configuration')
        sys.exit(1)
    
    print('✓ Configuration loaded successfully')
    print(f'   Database URL: {database_url.split("@")[1] if "@" in database_url else "invalid"}')
    
    # Comprehensive validation
    validator = DatabaseValidator()
    
    print('✓ Testing connection...')
    result = validator.test_connection(database_url)
    
    if result.success:
        print(f'✅ Connection successful ({result.connection_time_ms:.2f}ms)')
        if result.database_version:
            print(f'   PostgreSQL: {result.database_version.split(",")[0]}')
        
        # Test schema
        print('✓ Validating schema...')
        schema = validator.validate_schema(database_url)
        
        if schema.valid:
            print(f'✅ Schema valid ({len(schema.tables_found)} tables)')
        else:
            print(f'⚠️  Schema incomplete - missing {len(schema.tables_missing)} tables')
            for table in schema.tables_missing:
                print(f'     • {table}')
        
        # Test service
        service = validator.test_service_running()
        if service.running:
            print(f'✅ PostgreSQL service running ({service.service_name or "detected"})')
        else:
            print('⚠️  PostgreSQL service status unclear')
        
        print('\n🎉 Database is fully operational!')
        sys.exit(0)
        
    else:
        print(f'❌ Connection failed: {result.error_message}')
        print(f'   Error type: {result.error_type}')
        print(f'   Suggested fix: {result.suggested_fix}')
        sys.exit(1)
        
except Exception as e:
    print(f'❌ Error during validation: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"@
    
    $tempTest = [System.IO.Path]::GetTempFileName() + ".py"
    $pythonTest | Out-File -FilePath $tempTest -Encoding UTF8
    
    try {
        $output = poetry run python $tempTest 2>&1
        $success = $LASTEXITCODE -eq 0
        
        # Display output with proper formatting
        $output | ForEach-Object { 
            if ($_ -match "^✅") { Write-Success $_ }
            elseif ($_ -match "^⚠️") { Write-Warning $_ }
            elseif ($_ -match "^❌") { Write-Error $_ }
            elseif ($_ -match "^✓") { Write-Info $_ }
            else { Write-Host "   $_" }
        }
        
        if ($success) {
            Write-Host ""
            Write-Success "🎉 All tests passed! Your database is ready."
            
            if (-not $QuickTest) {
                Write-Host ""
                Write-Info "Next steps:"
                Write-Info "• Start the trading system: .\scripts\start-trading-system.ps1"
                Write-Info "• Or start API: poetry run uvicorn apps.trading_api.main:app --port 8000"
            }
            
            if (Test-Path $tempTest) { Remove-Item $tempTest }
            return
        }
    }
    catch {
        Write-Warning "Python validation failed, falling back to manual testing..."
    }
    finally {
        if (Test-Path $tempTest) { Remove-Item $tempTest }
    }
}

# Manual connection testing (fallback or when no config exists)
Write-Step "Manual connection testing..."

if ($QuickTest) {
    Write-Info "Running quick test only..."
}

# Common passwords to try
$passwords = @("postgres", "trading", "admin", "password", "123456", "")
$found = $false
$workingPassword = ""

Write-Info "Testing common PostgreSQL passwords..."

foreach ($pwd in $passwords) {
    $displayPwd = if ($pwd -eq "") { "(empty)" } else { "'$pwd'" }
    Write-Host "  Testing password: $displayPwd" -NoNewline
    
    try {
        $env:PGPASSWORD = $pwd
        $null = psql -h localhost -U postgres -d postgres -c "SELECT 1;" 2>$null
        Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host " ✅" -ForegroundColor Green
            Write-Success "Connection successful with password: $displayPwd"
            $found = $true
            $workingPassword = $pwd
            break
        } else {
            Write-Host " ❌" -ForegroundColor Red
        }
    }
    catch {
        Write-Host " ❌" -ForegroundColor Red
        Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
    }
}

if (-not $found) {
    Write-Warning "`n⚠️  Could not connect with common passwords"
    
    if (-not $QuickTest) {
        Write-Info "`nPlease enter your PostgreSQL password:"
        $customPwd = Read-Host "PostgreSQL password" -AsSecureString
        $customPwdPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($customPwd))
        
        try {
            $env:PGPASSWORD = $customPwdPlain
            $null = psql -h localhost -U postgres -d postgres -c "SELECT 1;" 2>$null
            Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
            
            if ($LASTEXITCODE -eq 0) {
                Write-Success "✓ Connection successful with provided password!"
                $found = $true
                $workingPassword = $customPwdPlain
            } else {
                Write-Error "✗ Connection failed with provided password"
            }
        }
        catch {
            Write-Error "✗ Connection failed with provided password"
            Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
        }
    }
    
    if (-not $found) {
        Write-Error "`n❌ Unable to establish database connection"
        Write-Host ""
        Write-Info "🔧 Troubleshooting options:"
        Write-Info "1. Run the comprehensive setup wizard:"
        Write-Host "   .\scripts\Setup-Database.ps1" -ForegroundColor Cyan
        Write-Host ""
        Write-Info "2. Reset PostgreSQL password:"
        Write-Host "   .\scripts\Reset-PostgreSQL-Password.ps1" -ForegroundColor Cyan
        Write-Host ""
        Write-Info "3. Check detailed troubleshooting guide:"
        Write-Host "   See: QUICK-FIX-DATABASE.md" -ForegroundColor Cyan
        Write-Host ""
        Write-Info "4. Manual PostgreSQL service check:"
        Write-Host "   Get-Service postgresql*" -ForegroundColor Cyan
        Write-Host "   Start-Service postgresql-x64-17" -ForegroundColor Cyan
        return
    }
}

if ($found -and -not $QuickTest) {
    Write-Host ""
    Write-Step "Testing trading user and database..."
    
    # Test trading user
    try {
        $env:PGPASSWORD = $workingPassword
        $null = psql -h localhost -U trading -d trading -c "SELECT 1;" 2>$null
        Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "✓ Trading user exists and can access database"
        } else {
            Write-Warning "⚠️  Trading user or database needs setup"
            Write-Info "   Run: .\scripts\Setup-Database.ps1 to create user and database"
        }
    }
    catch {
        Write-Warning "⚠️  Error testing trading user"
        Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
    }
    
    Write-Host ""
    Write-Step "Configuration recommendations..."
    
    # Show configuration update
    $databaseUrl = "postgresql://trading:$workingPassword@localhost:5432/trading"
    Write-Info "Add this to your .env.local file:"
    Write-Host "DATABASE_URL=$databaseUrl" -ForegroundColor Green
    
    Write-Host ""
    Write-Info "🚀 Next steps:"
    Write-Info "1. Update .env.local with the DATABASE_URL above"
    Write-Info "2. Run comprehensive setup: .\scripts\Setup-Database.ps1"
    Write-Info "3. Or create tables: .\scripts\Create-DatabaseTables.ps1"
    Write-Info "4. Start the system: .\scripts\start-trading-system.ps1"
}

if ($Detailed -and $found) {
    Write-Host ""
    Write-Step "Detailed diagnostics..."
    
    # Run detailed Python diagnostics
    $detailedTest = @"
import os
from libs.trading_models.db_validator import DatabaseValidator

# Set up connection string
database_url = f"postgresql://postgres:$workingPassword@localhost:5432/postgres"

validator = DatabaseValidator()
diagnostics = validator.get_connection_diagnostics(database_url)

print('📊 Detailed Diagnostics:')
print('=' * 40)

# Service status
service = diagnostics.get('service_status', {})
print(f'Service Running: {service.get("running", "Unknown")}')
if service.get('service_name'):
    print(f'Service Name: {service["service_name"]}')

# Connection test
conn = diagnostics.get('connection_test', {})
if conn:
    print(f'Connection Success: {conn.get("success", False)}')
    if conn.get('connection_time_ms'):
        print(f'Connection Time: {conn["connection_time_ms"]:.2f}ms')
    if conn.get('database_version'):
        print(f'PostgreSQL Version: {conn["database_version"]}')

# System info
sys_info = diagnostics.get('system_info', {})
if sys_info:
    print(f'Available Memory: {sys_info.get("available_memory_gb", "Unknown")}GB')
    print(f'CPU Usage: {sys_info.get("cpu_percent", "Unknown")}%')

print('=' * 40)
"@
    
    $tempDetailed = [System.IO.Path]::GetTempFileName() + ".py"
    $detailedTest | Out-File -FilePath $tempDetailed -Encoding UTF8
    
    try {
        $detailedOutput = poetry run python $tempDetailed 2>&1
        $detailedOutput | ForEach-Object { Write-Host "   $_" }
    }
    catch {
        Write-Warning "Could not run detailed diagnostics"
    }
    finally {
        if (Test-Path $tempDetailed) { Remove-Item $tempDetailed }
    }
}

Write-Host ""