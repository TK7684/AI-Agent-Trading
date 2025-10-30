<#
.SYNOPSIS
    Interactive database setup wizard for the trading system

.DESCRIPTION
    Comprehensive wizard that guides users through database configuration:
    - Tests PostgreSQL service status
    - Automatically tests common passwords
    - Creates trading user if needed
    - Updates .env.local configuration
    - Initializes database schema
    - Validates complete setup

.EXAMPLE
    .\Setup-Database.ps1
    
.EXAMPLE
    .\Setup-Database.ps1 -AutoMode
    Run in automatic mode with minimal prompts
#>

param(
    [switch]$AutoMode = $false,
    [string]$Password = "",
    [switch]$SkipServiceCheck = $false,
    [switch]$Verbose = $false
)

$ErrorActionPreference = "Stop"

# Add PostgreSQL to PATH if needed
$pgPath = "C:\Program Files\PostgreSQL\17\bin"
if ((Test-Path $pgPath) -and ($env:Path -notlike "*$pgPath*")) {
    $env:Path += ";$pgPath"
}

# Color functions for better UX
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-Error { Write-Host $args -ForegroundColor Red }
function Write-Step { Write-Host "🔧 $args" -ForegroundColor Magenta }

# Progress tracking
$script:StepCount = 0
$script:TotalSteps = 8

function Write-Progress {
    param([string]$Activity)
    $script:StepCount++
    Write-Host "`n[$script:StepCount/$script:TotalSteps] $Activity" -ForegroundColor Blue -BackgroundColor White
}

# Configuration
$CommonPasswords = @("postgres", "trading", "admin", "password", "123456", "")
$PostgresServiceNames = @(
    "postgresql-x64-17", "postgresql-x64-16", "postgresql-x64-15",
    "postgresql-x64-14", "postgresql-x64-13", "postgresql", "PostgreSQL"
)

# Results tracking
$script:Results = @{
    ServiceRunning = $false
    ServiceName = ""
    PasswordFound = $false
    Password = ""
    TradingUserExists = $false
    DatabaseExists = $false
    ConfigUpdated = $false
    SchemaInitialized = $false
    ValidationPassed = $false
}

Write-Info "🚀 Trading System Database Setup Wizard"
Write-Info "=" * 60
Write-Host ""

if ($AutoMode) {
    Write-Info "Running in automatic mode with minimal prompts"
} else {
    Write-Info "This wizard will help you configure the database for the trading system."
    Write-Info "It will:"
    Write-Info "  • Check PostgreSQL service status"
    Write-Info "  • Test database connection with common passwords"
    Write-Info "  • Create trading user and database if needed"
    Write-Info "  • Update .env.local configuration"
    Write-Info "  • Initialize database schema"
    Write-Info "  • Validate the complete setup"
    Write-Host ""
    
    if (-not $AutoMode) {
        $continue = Read-Host "Continue? (Y/n)"
        if ($continue -eq "n" -or $continue -eq "N") {
            Write-Info "Setup cancelled by user"
            exit 0
        }
    }
}

# Step 1: Check PostgreSQL Service
Write-Progress "Checking PostgreSQL Service Status"

if (-not $SkipServiceCheck) {
    $serviceFound = $false
    $runningService = $null
    
    foreach ($serviceName in $PostgresServiceNames) {
        try {
            $service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
            if ($service) {
                $serviceFound = $true
                Write-Info "Found PostgreSQL service: $serviceName"
                
                if ($service.Status -eq "Running") {
                    Write-Success "✓ PostgreSQL service is running"
                    $script:Results.ServiceRunning = $true
                    $script:Results.ServiceName = $serviceName
                    $runningService = $service
                    break
                } else {
                    Write-Warning "⚠️  PostgreSQL service '$serviceName' is $($service.Status)"
                    
                    if (-not $AutoMode) {
                        $startService = Read-Host "Would you like to start the service? (Y/n)"
                        if ($startService -ne "n" -and $startService -ne "N") {
                            try {
                                Write-Info "Starting PostgreSQL service..."
                                Start-Service -Name $serviceName
                                Start-Sleep -Seconds 3
                                
                                $service = Get-Service -Name $serviceName
                                if ($service.Status -eq "Running") {
                                    Write-Success "✓ PostgreSQL service started successfully"
                                    $script:Results.ServiceRunning = $true
                                    $script:Results.ServiceName = $serviceName
                                    $runningService = $service
                                    break
                                }
                            }
                            catch {
                                Write-Error "Failed to start service: $($_.Exception.Message)"
                            }
                        }
                    }
                }
            }
        }
        catch {
            # Service doesn't exist, continue
        }
    }
    
    if (-not $serviceFound) {
        Write-Error "❌ No PostgreSQL service found"
        Write-Info "Please install PostgreSQL and try again"
        Write-Info "Download from: https://www.postgresql.org/download/windows/"
        exit 1
    }
    
    if (-not $script:Results.ServiceRunning) {
        Write-Error "❌ PostgreSQL service is not running"
        Write-Info "Please start the PostgreSQL service manually:"
        Write-Info "  1. Open Services (services.msc)"
        Write-Info "  2. Find PostgreSQL service"
        Write-Info "  3. Right-click and select 'Start'"
        Write-Info "Or run: Start-Service $($PostgresServiceNames[0])"
        exit 1
    }
} else {
    Write-Info "Skipping service check (--SkipServiceCheck specified)"
    $script:Results.ServiceRunning = $true
}

# Step 2: Test Database Connection
Write-Progress "Testing Database Connection"

$foundPassword = ""
$connectionSuccessful = $false

if ($Password) {
    Write-Info "Using provided password..."
    $testPasswords = @($Password)
} else {
    Write-Info "Testing common passwords..."
    $testPasswords = $CommonPasswords
}

foreach ($pwd in $testPasswords) {
    $displayPwd = if ($pwd -eq "") { "(empty)" } else { "'$pwd'" }
    Write-Host "  Testing password: $displayPwd" -NoNewline
    
    try {
        $env:PGPASSWORD = $pwd
        $null = psql -h localhost -U postgres -d postgres -c "SELECT 1;" 2>$null
        Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host " ✓" -ForegroundColor Green
            Write-Success "Connection successful with password: $displayPwd"
            $foundPassword = $pwd
            $connectionSuccessful = $true
            $script:Results.PasswordFound = $true
            $script:Results.Password = $pwd
            break
        } else {
            Write-Host " ✗" -ForegroundColor Red
        }
    }
    catch {
        Write-Host " ✗" -ForegroundColor Red
        Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
    }
}

if (-not $connectionSuccessful) {
    Write-Warning "`n⚠️  Could not connect with common passwords"
    
    if (-not $AutoMode) {
        Write-Info "`nPlease enter your PostgreSQL password:"
        $customPwd = Read-Host "PostgreSQL password" -AsSecureString
        $customPwdPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($customPwd))
        
        try {
            $env:PGPASSWORD = $customPwdPlain
            $null = psql -h localhost -U postgres -d postgres -c "SELECT 1;" 2>$null
            Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
            
            if ($LASTEXITCODE -eq 0) {
                Write-Success "✓ Connection successful!"
                $foundPassword = $customPwdPlain
                $connectionSuccessful = $true
                $script:Results.PasswordFound = $true
                $script:Results.Password = $customPwdPlain
            } else {
                Write-Error "✗ Connection failed with provided password"
            }
        }
        catch {
            Write-Error "✗ Connection failed with provided password"
            Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
        }
    }
    
    if (-not $connectionSuccessful) {
        Write-Error "`n❌ Unable to connect to PostgreSQL"
        Write-Info "`nTroubleshooting steps:"
        Write-Info "1. Reset PostgreSQL password:"
        Write-Info "   .\scripts\Reset-PostgreSQL-Password.ps1"
        Write-Info "2. Check PostgreSQL installation"
        Write-Info "3. Verify service is running"
        Write-Info "4. See QUICK-FIX-DATABASE.md for detailed help"
        exit 1
    }
}

# Step 3: Check/Create Trading Database
Write-Progress "Checking Trading Database"

try {
    $env:PGPASSWORD = $foundPassword
    $null = psql -h localhost -U postgres -d trading -c "SELECT 1;" 2>$null
    Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "✓ Trading database exists"
        $script:Results.DatabaseExists = $true
    } else {
        Write-Info "Creating trading database..."
        $env:PGPASSWORD = $foundPassword
        $null = psql -h localhost -U postgres -c "CREATE DATABASE trading;" 2>$null
        Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "✓ Trading database created"
            $script:Results.DatabaseExists = $true
        } else {
            Write-Warning "⚠️  Could not create trading database (may already exist)"
            $script:Results.DatabaseExists = $true  # Assume it exists
        }
    }
}
catch {
    Write-Warning "⚠️  Error checking trading database: $($_.Exception.Message)"
    Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
}

# Step 4: Check/Create Trading User
Write-Progress "Checking Trading User"

try {
    $env:PGPASSWORD = $foundPassword
    $null = psql -h localhost -U trading -d trading -c "SELECT 1;" 2>$null
    Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "✓ Trading user exists and can access database"
        $script:Results.TradingUserExists = $true
    } else {
        Write-Info "Creating trading user..."
        $env:PGPASSWORD = $foundPassword
        $createUserCmd = "CREATE USER trading WITH PASSWORD '$foundPassword'; GRANT ALL PRIVILEGES ON DATABASE trading TO trading; ALTER USER trading CREATEDB;"
        $null = psql -h localhost -U postgres -d postgres -c $createUserCmd 2>$null
        Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "✓ Trading user created with full privileges"
            $script:Results.TradingUserExists = $true
        } else {
            Write-Warning "⚠️  Could not create trading user (may already exist)"
            # Try to grant privileges anyway
            $env:PGPASSWORD = $foundPassword
            $grantCmd = "GRANT ALL PRIVILEGES ON DATABASE trading TO trading; ALTER USER trading CREATEDB;"
            $null = psql -h localhost -U postgres -d postgres -c $grantCmd 2>$null
            Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
            $script:Results.TradingUserExists = $true
        }
    }
}
catch {
    Write-Warning "⚠️  Error with trading user: $($_.Exception.Message)"
    Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
}

# Step 5: Update .env.local Configuration
Write-Progress "Updating Configuration"

try {
    $envFile = ".env.local"
    
    # Backup existing file
    if (Test-Path $envFile) {
        $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
        $backupFile = ".env.local.backup_$timestamp"
        Copy-Item $envFile $backupFile
        Write-Info "✓ Backed up existing .env.local to $backupFile"
    }
    
    # Read existing content
    $lines = @()
    if (Test-Path $envFile) {
        $lines = Get-Content $envFile
    }
    
    # Update DATABASE_URL
    $databaseUrl = "postgresql://trading:$foundPassword@localhost:5432/trading"
    $urlLine = "DATABASE_URL=$databaseUrl"
    
    # Find and replace DATABASE_URL line
    $found = $false
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match "^DATABASE_URL=") {
            $lines[$i] = $urlLine
            $found = $true
            break
        }
    }
    
    # Add if not found
    if (-not $found) {
        $lines += $urlLine
    }
    
    # Also update individual database variables
    $dbVars = @{
        "POSTGRES_HOST" = "localhost"
        "POSTGRES_PORT" = "5432"
        "POSTGRES_DB" = "trading"
        "POSTGRES_USER" = "trading"
        "POSTGRES_PASSWORD" = $foundPassword
    }
    
    foreach ($varName in $dbVars.Keys) {
        $varLine = "$varName=$($dbVars[$varName])"
        $found = $false
        
        for ($i = 0; $i -lt $lines.Count; $i++) {
            if ($lines[$i] -match "^$varName=") {
                $lines[$i] = $varLine
                $found = $true
                break
            }
        }
        
        if (-not $found) {
            $lines += $varLine
        }
    }
    
    # Write back to file
    $lines | Out-File -FilePath $envFile -Encoding UTF8
    
    Write-Success "✓ Updated .env.local with database configuration"
    $script:Results.ConfigUpdated = $true
}
catch {
    Write-Error "❌ Error updating .env.local: $($_.Exception.Message)"
}

# Step 6: Initialize Database Schema
Write-Progress "Initializing Database Schema"

try {
    Write-Info "Creating database tables..."
    
    # Create Python script to initialize schema
    $pythonScript = @"
import sys
import os
from libs.trading_models.persistence import DatabaseManager
from libs.trading_models.db_validator import DatabaseValidator

# Load environment
from dotenv import load_dotenv
load_dotenv('.env.local')

# Get database URL
database_url = os.getenv('DATABASE_URL')
if not database_url:
    print('❌ DATABASE_URL not found in environment')
    sys.exit(1)

print('✓ Validating database connection...')

# Validate connection first
validator = DatabaseValidator()
result = validator.test_connection(database_url)

if not result.success:
    print(f'❌ Database connection failed: {result.error_message}')
    print(f'Suggested fix: {result.suggested_fix}')
    sys.exit(1)

print(f'✓ Connected successfully ({result.connection_time_ms:.2f}ms)')

try:
    # Create database manager
    db_manager = DatabaseManager(database_url)
    
    # Initialize schema with detailed reporting
    print('✓ Initializing database schema...')
    init_result = db_manager.initialize_schema()
    
    if init_result.success:
        print(f'✅ Schema initialization successful!')
        print(f'   Duration: {init_result.duration_ms:.2f}ms')
        
        if init_result.tables_created:
            print(f'   Created {len(init_result.tables_created)} new tables:')
            for table in init_result.tables_created:
                print(f'     • {table}')
        
        if init_result.tables_skipped:
            print(f'   Skipped {len(init_result.tables_skipped)} existing tables:')
            for table in init_result.tables_skipped:
                print(f'     • {table}')
        
        # Validate schema
        print('✓ Validating schema...')
        schema_validation = validator.validate_schema(database_url)
        
        if schema_validation.valid:
            print(f'✅ Schema validation passed - all {len(schema_validation.tables_found)} tables present')
        else:
            print(f'⚠️  Schema validation warning - missing {len(schema_validation.tables_missing)} tables:')
            for table in schema_validation.tables_missing:
                print(f'     • {table}')
        
        sys.exit(0)
    else:
        print('❌ Schema initialization failed')
        for error in init_result.errors:
            print(f'   Error: {error}')
        sys.exit(1)
    
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"@
    
    # Write Python script to temp file
    $tempScript = [System.IO.Path]::GetTempFileName() + ".py"
    $pythonScript | Out-File -FilePath $tempScript -Encoding UTF8
    
    # Run schema initialization
    $output = poetry run python $tempScript 2>&1
    $success = $LASTEXITCODE -eq 0
    
    # Display output
    $output | ForEach-Object { Write-Host "  $_" }
    
    if ($success) {
        Write-Success "✓ Database schema initialized successfully"
        $script:Results.SchemaInitialized = $true
    } else {
        Write-Error "❌ Schema initialization failed"
        Write-Info "Check the error messages above for details"
    }
    
    # Cleanup temp file
    if (Test-Path $tempScript) {
        Remove-Item $tempScript
    }
}
catch {
    Write-Error "❌ Error initializing schema: $($_.Exception.Message)"
}

# Step 7: Final Validation
Write-Progress "Final Validation"

try {
    Write-Info "Running comprehensive validation..."
    
    # Test full connection chain
    $env:PGPASSWORD = $foundPassword
    $testResult = psql -h localhost -U trading -d trading -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>$null
    Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "✓ Full database connection chain validated"
        $script:Results.ValidationPassed = $true
    } else {
        Write-Warning "⚠️  Validation warning - connection may have issues"
    }
    
    # Test Python connection
    $pythonTest = @"
import os
from dotenv import load_dotenv
load_dotenv('.env.local')
from libs.trading_models.db_validator import DatabaseValidator

database_url = os.getenv('DATABASE_URL')
validator = DatabaseValidator()
result = validator.test_connection(database_url)

if result.success:
    print('✓ Python connection test passed')
    exit(0)
else:
    print(f'✗ Python connection test failed: {result.error_message}')
    exit(1)
"@
    
    $tempTest = [System.IO.Path]::GetTempFileName() + ".py"
    $pythonTest | Out-File -FilePath $tempTest -Encoding UTF8
    
    $testOutput = poetry run python $tempTest 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "✓ Python database connection validated"
    } else {
        Write-Warning "⚠️  Python connection test failed: $testOutput"
    }
    
    if (Test-Path $tempTest) {
        Remove-Item $tempTest
    }
}
catch {
    Write-Warning "⚠️  Validation error: $($_.Exception.Message)"
}

# Step 8: Summary and Next Steps
Write-Progress "Setup Complete"

Write-Host "`n" + "=" * 60 -ForegroundColor Green
Write-Host "🎉 DATABASE SETUP SUMMARY" -ForegroundColor Green -BackgroundColor Black
Write-Host "=" * 60 -ForegroundColor Green

$allSuccessful = $true

# Display results
$results = @(
    @{ Name = "PostgreSQL Service"; Status = $script:Results.ServiceRunning; Details = $script:Results.ServiceName }
    @{ Name = "Database Connection"; Status = $script:Results.PasswordFound; Details = "Password: $(if($script:Results.Password -eq '') {'(empty)'} else {'***'})" }
    @{ Name = "Trading Database"; Status = $script:Results.DatabaseExists; Details = "Database: trading" }
    @{ Name = "Trading User"; Status = $script:Results.TradingUserExists; Details = "User: trading" }
    @{ Name = "Configuration Update"; Status = $script:Results.ConfigUpdated; Details = "File: .env.local" }
    @{ Name = "Schema Initialization"; Status = $script:Results.SchemaInitialized; Details = "Tables created" }
    @{ Name = "Final Validation"; Status = $script:Results.ValidationPassed; Details = "Connection verified" }
)

foreach ($result in $results) {
    $status = if ($result.Status) { "✅ SUCCESS" } else { "❌ FAILED"; $allSuccessful = $false }
    $color = if ($result.Status) { "Green" } else { "Red" }
    
    Write-Host "  $($result.Name.PadRight(25)): " -NoNewline
    Write-Host $status -ForegroundColor $color -NoNewline
    if ($result.Details) {
        Write-Host " ($($result.Details))" -ForegroundColor Gray
    } else {
        Write-Host ""
    }
}

Write-Host "`n" + "=" * 60 -ForegroundColor Green

if ($allSuccessful) {
    Write-Success "`n🎉 SETUP COMPLETED SUCCESSFULLY!"
    Write-Host ""
    Write-Info "Your trading system database is now ready!"
    Write-Host ""
    Write-Info "Next steps:"
    Write-Info "1. Start the trading system:"
    Write-Host "   .\scripts\start-trading-system.ps1" -ForegroundColor Cyan
    Write-Host ""
    Write-Info "2. Or start individual components:"
    Write-Host "   # API Server:" -ForegroundColor Gray
    Write-Host "   poetry run uvicorn apps.trading_api.main:app --host 0.0.0.0 --port 8000" -ForegroundColor Cyan
    Write-Host "   # Dashboard:" -ForegroundColor Gray
    Write-Host "   cd apps\trading-dashboard-ui-clean && npm run dev" -ForegroundColor Cyan
    Write-Host ""
    Write-Info "3. Access the system:"
    Write-Info "   • Dashboard: http://localhost:5173"
    Write-Info "   • API Docs:  http://localhost:8000/docs"
    Write-Host ""
    Write-Success "🚀 Happy Trading!"
} else {
    Write-Error "`n❌ SETUP COMPLETED WITH ISSUES"
    Write-Host ""
    Write-Info "Some components failed to set up properly."
    Write-Info "You can still try to start the system, but you may encounter issues."
    Write-Host ""
    Write-Info "For troubleshooting:"
    Write-Info "• Check TROUBLESHOOTING.md"
    Write-Info "• Review error messages above"
    Write-Info "• Run this wizard again: .\scripts\Setup-Database.ps1"
    Write-Info "• Get help: QUICK-FIX-DATABASE.md"
}

Write-Host ""