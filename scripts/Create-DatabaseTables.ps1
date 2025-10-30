<#
.SYNOPSIS
    Enhanced database table creation with validation and error handling

.DESCRIPTION
    Creates the required database tables using SQLAlchemy models with comprehensive
    validation, error handling, and detailed reporting. Integrates with the new
    database validation system for robust table creation.

.PARAMETER Force
    Force recreation of tables (drops existing tables first)

.PARAMETER Validate
    Only validate existing schema without creating tables

.PARAMETER Verbose
    Show detailed output during table creation

.EXAMPLE
    .\Create-DatabaseTables.ps1
    
.EXAMPLE
    .\Create-DatabaseTables.ps1 -Validate
    
.EXAMPLE
    .\Create-DatabaseTables.ps1 -Force -Verbose
#>

param(
    [switch]$Force = $false,
    [switch]$Validate = $false,
    [switch]$Verbose = $false
)

$ErrorActionPreference = "Stop"

# Add PostgreSQL to PATH if needed
$pgPath = "C:\Program Files\PostgreSQL\17\bin"
if ((Test-Path $pgPath) -and ($env:Path -notlike "*$pgPath*")) {
    $env:Path += ";$pgPath"
}

function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-Error { Write-Host $args -ForegroundColor Red }
function Write-Step { Write-Host "🔧 $args" -ForegroundColor Magenta }

Write-Info "📊 Enhanced Database Table Manager"
Write-Info "=" * 60
Write-Host ""

if ($Validate) {
    Write-Info "Running in validation mode - no tables will be created"
} elseif ($Force) {
    Write-Warning "Force mode enabled - existing tables will be dropped!"
}

# Step 1: Validate database connection
Write-Step "Validating database connection..."

$pythonValidation = @"
import sys
import os
from libs.trading_models.db_validator import DatabaseValidator
from libs.trading_models.config_manager import ConfigurationManager

try:
    # Load configuration
    config_manager = ConfigurationManager()
    database_url = config_manager.get_database_url()
    
    if not database_url:
        print('❌ DATABASE_URL not configured')
        print('   Run: .\\scripts\\Setup-Database.ps1')
        sys.exit(1)
    
    print('✓ Configuration loaded')
    
    # Validate connection
    validator = DatabaseValidator()
    result = validator.test_connection(database_url)
    
    if not result.success:
        print(f'❌ Database connection failed: {result.error_message}')
        print(f'   Error type: {result.error_type}')
        print(f'   Suggested fix: {result.suggested_fix}')
        sys.exit(1)
    
    print(f'✅ Database connection successful ({result.connection_time_ms:.2f}ms)')
    
    # Check service status
    service = validator.test_service_running()
    if service.running:
        print(f'✅ PostgreSQL service running ({service.service_name or "detected"})')
    
    # Output database URL for the main script
    print(f'DATABASE_URL_VALIDATED:{database_url}')
    sys.exit(0)
    
except Exception as e:
    print(f'❌ Validation error: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"@

$tempValidation = [System.IO.Path]::GetTempFileName() + ".py"
$pythonValidation | Out-File -FilePath $tempValidation -Encoding UTF8

try {
    $validationOutput = poetry run python $tempValidation 2>&1
    $validationSuccess = $LASTEXITCODE -eq 0
    
    # Parse output
    $databaseUrl = ""
    $validationOutput | ForEach-Object {
        if ($_ -match "^DATABASE_URL_VALIDATED:(.+)$") {
            $databaseUrl = $matches[1]
        } elseif ($_ -match "^✅|^✓") {
            Write-Success $_
        } elseif ($_ -match "^❌") {
            Write-Error $_
        } elseif ($_ -match "^⚠️") {
            Write-Warning $_
        } else {
            if ($Verbose) { Write-Host "   $_" }
        }
    }
    
    if (-not $validationSuccess) {
        Write-Error "Database validation failed. Cannot proceed with table creation."
        exit 1
    }
}
finally {
    if (Test-Path $tempValidation) { Remove-Item $tempValidation }
}

# Step 2: Schema validation or creation
if ($Validate) {
    Write-Step "Validating existing schema..."
} else {
    Write-Step "Creating/updating database schema..."
}

$pythonScript = @"
import sys
import os
from libs.trading_models.persistence import DatabaseManager
from libs.trading_models.db_validator import DatabaseValidator

# Configuration
database_url = '$databaseUrl'
force_recreate = $($Force.ToString().ToLower())
validate_only = $($Validate.ToString().ToLower())
verbose = $($Verbose.ToString().ToLower())

try:
    print('✓ Initializing database manager...')
    db_manager = DatabaseManager(database_url)
    
    if validate_only:
        print('✓ Validating existing schema...')
        
        # Use validator for schema checking
        validator = DatabaseValidator()
        schema_validation = validator.validate_schema(database_url)
        
        print(f'Schema Validation Results:')
        print(f'  Valid: {schema_validation.valid}')
        print(f'  Tables Expected: {len(schema_validation.tables_expected)}')
        print(f'  Tables Found: {len(schema_validation.tables_found)}')
        print(f'  Tables Missing: {len(schema_validation.tables_missing)}')
        
        if schema_validation.tables_found:
            print(f'  ✅ Existing tables:')
            for table in schema_validation.tables_found:
                print(f'     • {table}')
        
        if schema_validation.tables_missing:
            print(f'  ❌ Missing tables:')
            for table in schema_validation.tables_missing:
                print(f'     • {table}')
            print(f'  Run without -Validate flag to create missing tables')
        
        if schema_validation.valid:
            print('✅ Schema validation passed - all tables present')
        else:
            print('⚠️  Schema validation incomplete - missing tables detected')
            sys.exit(1)
        
        sys.exit(0)
    
    # Test connection before proceeding
    if not db_manager.test_connection():
        print('❌ Database connection test failed')
        sys.exit(1)
    
    print('✅ Database connection verified')
    
    if force_recreate:
        print('⚠️  Force mode: Dropping existing tables...')
        try:
            from libs.trading_models.persistence import Base
            Base.metadata.drop_all(bind=db_manager.engine)
            print('✓ Existing tables dropped')
        except Exception as e:
            print(f'⚠️  Warning dropping tables: {e}')
    
    # Initialize schema with detailed reporting
    print('✓ Initializing database schema...')
    result = db_manager.initialize_schema()
    
    if result.success:
        print(f'✅ Schema initialization successful!')
        print(f'   Duration: {result.duration_ms:.2f}ms')
        
        if result.tables_created:
            print(f'   ✅ Created {len(result.tables_created)} new tables:')
            for table in result.tables_created:
                print(f'      • {table}')
        
        if result.tables_skipped:
            print(f'   ℹ️  Skipped {len(result.tables_skipped)} existing tables:')
            for table in result.tables_skipped:
                print(f'      • {table}')
        
        # Final validation
        print('✓ Performing final validation...')
        validator = DatabaseValidator()
        final_validation = validator.validate_schema(database_url)
        
        if final_validation.valid:
            print(f'✅ Final validation passed - all {len(final_validation.tables_found)} tables verified')
            
            # Test basic operations
            print('✓ Testing basic database operations...')
            with db_manager.get_session() as session:
                # Test a simple query
                session.execute('SELECT 1')
                print('✅ Basic operations test passed')
            
        else:
            print(f'⚠️  Final validation issues:')
            for table in final_validation.tables_missing:
                print(f'     • Missing: {table}')
        
        print('\n🎉 Database schema setup completed successfully!')
        
        # Show next steps
        print('\n📋 Next Steps:')
        print('   1. Start the trading system: .\\scripts\\start-trading-system.ps1')
        print('   2. Or start API server: poetry run uvicorn apps.trading_api.main:app --port 8000')
        print('   3. Test connection: .\\scripts\\Test-DatabaseConnection.ps1')
        
        sys.exit(0)
    else:
        print('❌ Schema initialization failed')
        if result.errors:
            print('   Errors encountered:')
            for error in result.errors:
                print(f'     • {error}')
        sys.exit(1)
    
except Exception as e:
    print(f'❌ Error during schema operations: {e}')
    if verbose:
        import traceback
        traceback.print_exc()
    sys.exit(1)
finally:
    try:
        db_manager.close()
    except:
        pass
"@

# Write and execute the main script
$tempScript = [System.IO.Path]::GetTempFileName() + ".py"
$pythonScript | Out-File -FilePath $tempScript -Encoding UTF8

try {
    if ($Verbose) {
        Write-Info "Running schema operations with verbose output..."
    } else {
        Write-Info "Running schema operations..."
    }
    
    $output = poetry run python $tempScript 2>&1
    $success = $LASTEXITCODE -eq 0
    
    # Display output with proper formatting
    $output | ForEach-Object {
        if ($_ -match "^✅") { Write-Success $_ }
        elseif ($_ -match "^⚠️") { Write-Warning $_ }
        elseif ($_ -match "^❌") { Write-Error $_ }
        elseif ($_ -match "^✓|^ℹ️") { Write-Info $_ }
        elseif ($_ -match "^📋|^🎉") { Write-Host $_ -ForegroundColor Magenta }
        else { 
            if ($Verbose -or $_ -match "^\s+•|^\s+Duration:|^\s+Created|^\s+Skipped") {
                Write-Host $_
            }
        }
    }
    
    if ($success) {
        Write-Host ""
        if ($Validate) {
            Write-Success "✅ Schema validation completed successfully!"
        } else {
            Write-Success "✅ Database table creation completed successfully!"
        }
    } else {
        Write-Host ""
        Write-Error "❌ Operation failed - see errors above"
        
        Write-Host ""
        Write-Info "🔧 Troubleshooting:"
        Write-Info "• Check database connection: .\scripts\Test-DatabaseConnection.ps1"
        Write-Info "• Run setup wizard: .\scripts\Setup-Database.ps1"
        Write-Info "• Check logs for detailed error information"
        Write-Info "• See: TROUBLESHOOTING.md for more help"
        
        exit 1
    }
}
finally {
    # Cleanup temp file
    if (Test-Path $tempScript) {
        Remove-Item $tempScript
    }
}

Write-Host ""