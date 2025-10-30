<#
.SYNOPSIS
    One-command setup for native development environment

.DESCRIPTION
    Installs and configures the complete trading system for native development.
    Checks prerequisites, installs dependencies, builds components, and initializes database.

.PARAMETER SkipPrerequisites
    Skip prerequisite checks (not recommended)

.PARAMETER SkipDatabase
    Skip database initialization

.PARAMETER SkipBuild
    Skip building Rust components

.EXAMPLE
    .\Setup-NativeDevelopment.ps1
    Complete setup with all checks

.EXAMPLE
    .\Setup-NativeDevelopment.ps1 -SkipBuild
    Setup without building Rust components
#>

param(
    [switch]$SkipPrerequisites,
    [switch]$SkipDatabase,
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"

# Colors for output
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-Error { Write-Host $args -ForegroundColor Red }
function Write-Step { 
    param($Step, $Total, $Message)
    Write-Host "`n[$Step/$Total] " -NoNewline -ForegroundColor Magenta
    Write-Host $Message -ForegroundColor Cyan
}

# Progress tracking
$script:TotalSteps = 10
$script:CurrentStep = 0
$script:StartTime = Get-Date
$script:FailedSteps = @()

function Start-Step {
    param([string]$Message)
    $script:CurrentStep++
    Write-Step -Step $script:CurrentStep -Total $script:TotalSteps -Message $Message
}

function Complete-Step {
    param([string]$Message)
    Write-Success "✅ $Message"
}

function Fail-Step {
    param([string]$Message, [string]$Details)
    Write-Error "❌ $Message"
    if ($Details) {
        Write-Info "   $Details"
    }
    $script:FailedSteps += $Message
}

# Banner
Write-Host ""
Write-Info "╔════════════════════════════════════════════════════════════╗"
Write-Info "║                                                            ║"
Write-Info "║     🚀 TRADING SYSTEM - NATIVE DEVELOPMENT SETUP 🚀        ║"
Write-Info "║                                                            ║"
Write-Info "║          One-Command Installation & Configuration          ║"
Write-Info "║                                                            ║"
Write-Info "╚════════════════════════════════════════════════════════════╝"
Write-Host ""

# Step 1: Check Prerequisites
if (-not $SkipPrerequisites) {
    Start-Step "Checking prerequisites..."
    
    $prerequisites = @{
        "Python 3.11+" = { 
            $version = python --version 2>&1
            if ($version -match "Python (\d+)\.(\d+)") {
                $major = [int]$matches[1]
                $minor = [int]$matches[2]
                return ($major -eq 3 -and $minor -ge 11) -or ($major -gt 3)
            }
            return $false
        }
        "Poetry" = { Get-Command poetry -ErrorAction SilentlyContinue }
        "Node.js" = { Get-Command node -ErrorAction SilentlyContinue }
        "npm" = { Get-Command npm -ErrorAction SilentlyContinue }
        "Rust/Cargo" = { Get-Command cargo -ErrorAction SilentlyContinue }
        "PostgreSQL" = { Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue }
        "Redis" = { Get-Service -Name "Redis" -ErrorAction SilentlyContinue }
    }
    
    $missing = @()
    foreach ($prereq in $prerequisites.GetEnumerator()) {
        $check = & $prereq.Value
        if ($check) {
            Write-Success "  ✓ $($prereq.Key)"
        }
        else {
            Write-Warning "  ✗ $($prereq.Key) - Missing"
            $missing += $prereq.Key
        }
    }
    
    if ($missing.Count -gt 0) {
        Write-Warning "`n⚠️  Missing prerequisites: $($missing -join ', ')"
        Write-Info "`nInstallation guides:"
        Write-Info "  • Python: https://www.python.org/downloads/"
        Write-Info "  • Poetry: https://python-poetry.org/docs/#installation"
        Write-Info "  • Node.js: https://nodejs.org/"
        Write-Info "  • Rust: https://rustup.rs/"
        Write-Info "  • PostgreSQL/Redis: Run .\scripts\install-native-services.ps1"
        
        $response = Read-Host "`nContinue anyway? (y/N)"
        if ($response -ne 'y') {
            exit 1
        }
    }
    else {
        Complete-Step "All prerequisites installed"
    }
}

# Step 2: Install Native Services (PostgreSQL & Redis)
Start-Step "Checking native services..."

$pgService = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue
$redisService = Get-Service -Name "Redis" -ErrorAction SilentlyContinue

if (-not $pgService -or -not $redisService) {
    Write-Info "Installing PostgreSQL and Redis..."
    try {
        & "$PSScriptRoot\install-native-services.ps1"
        Complete-Step "Native services installed"
    }
    catch {
        Fail-Step "Failed to install native services" "Run manually: .\scripts\install-native-services.ps1"
    }
}
else {
    # Ensure services are running
    if ($pgService.Status -ne 'Running') {
        Start-Service $pgService.Name
    }
    if ($redisService.Status -ne 'Running') {
        Start-Service Redis
    }
    Complete-Step "Native services ready"
}

# Step 3: Create Environment File
Start-Step "Configuring environment..."

if (-not (Test-Path ".env.local")) {
    if (Test-Path ".env.native.template") {
        Copy-Item ".env.native.template" ".env.local"
        Write-Success "  Created .env.local from template"
        Write-Warning "  ⚠️  Please review and update .env.local with your settings"
        Write-Info "     Especially: POSTGRES_PASSWORD, SECRET_KEY, API keys"
    }
    else {
        Write-Warning "  ⚠️  No .env template found"
    }
}
else {
    Write-Success "  .env.local already exists"
}

Complete-Step "Environment configured"

# Step 4: Install Python Dependencies
Start-Step "Installing Python dependencies..."

try {
    Write-Info "  Running: poetry install"
    poetry install --no-interaction
    Complete-Step "Python dependencies installed"
}
catch {
    Fail-Step "Failed to install Python dependencies" "Run manually: poetry install"
}

# Step 5: Install Node.js Dependencies
Start-Step "Installing Node.js dependencies..."

try {
    Push-Location "apps\trading-dashboard-ui-clean"
    Write-Info "  Running: npm install"
    npm install --silent
    Pop-Location
    Complete-Step "Node.js dependencies installed"
}
catch {
    Pop-Location
    Fail-Step "Failed to install Node.js dependencies" "Run manually in apps/trading-dashboard-ui-clean: npm install"
}

# Step 6: Build Rust Components
if (-not $SkipBuild) {
    Start-Step "Building Rust execution gateway..."
    
    try {
        Write-Info "  Running: cargo build --release"
        cargo build --package execution-gateway --release
        Complete-Step "Rust components built"
    }
    catch {
        Fail-Step "Failed to build Rust components" "Run manually: cargo build --package execution-gateway --release"
    }
}
else {
    Write-Info "Skipping Rust build (--SkipBuild specified)"
}

# Step 7: Initialize Database
if (-not $SkipDatabase) {
    Start-Step "Initializing database..."
    
    try {
        & "$PSScriptRoot\init-database.ps1"
        Complete-Step "Database initialized"
    }
    catch {
        Fail-Step "Failed to initialize database" "Run manually: .\scripts\init-database.ps1"
    }
}
else {
    Write-Info "Skipping database initialization (--SkipDatabase specified)"
}

# Step 8: Verify Configuration
Start-Step "Verifying configuration..."

try {
    if (Test-Path "$PSScriptRoot\verify-dotenv-config.ps1") {
        & "$PSScriptRoot\verify-dotenv-config.ps1"
    }
    Complete-Step "Configuration verified"
}
catch {
    Write-Warning "  ⚠️  Configuration verification had warnings"
}

# Step 9: Run Health Checks
Start-Step "Running health checks..."

$healthChecks = @{
    "PostgreSQL" = {
        $pgService = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue
        return $pgService -and $pgService.Status -eq 'Running'
    }
    "Redis" = {
        $redisService = Get-Service -Name "Redis" -ErrorAction SilentlyContinue
        return $redisService -and $redisService.Status -eq 'Running'
    }
    "Python Environment" = {
        poetry run python --version 2>&1 | Out-Null
        return $LASTEXITCODE -eq 0
    }
    "Rust Build" = {
        return (Test-Path "target\release\execution-gateway.exe")
    }
}

$healthyCount = 0
foreach ($check in $healthChecks.GetEnumerator()) {
    $result = & $check.Value
    if ($result) {
        Write-Success "  ✓ $($check.Key)"
        $healthyCount++
    }
    else {
        Write-Warning "  ✗ $($check.Key)"
    }
}

if ($healthyCount -eq $healthChecks.Count) {
    Complete-Step "All health checks passed"
}
else {
    Write-Warning "  ⚠️  $healthyCount/$($healthChecks.Count) health checks passed"
}

# Step 10: Summary
Start-Step "Setup complete!"

$duration = (Get-Date) - $script:StartTime
$durationStr = "{0:mm}m {0:ss}s" -f $duration

Write-Host ""
Write-Info "╔════════════════════════════════════════════════════════════╗"
Write-Info "║                    SETUP COMPLETE                          ║"
Write-Info "╚════════════════════════════════════════════════════════════╝"
Write-Host ""

if ($script:FailedSteps.Count -eq 0) {
    Write-Success "🎉 All steps completed successfully!"
}
else {
    Write-Warning "⚠️  Setup completed with $($script:FailedSteps.Count) warning(s):"
    foreach ($failed in $script:FailedSteps) {
        Write-Warning "  • $failed"
    }
}

Write-Info "`nSetup Duration: $durationStr"
Write-Host ""
Write-Info "📋 Next Steps:"
Write-Info "  1. Review .env.local and update configuration"
Write-Info "  2. Start the system: .\scripts\start-trading-system.ps1"
Write-Info "  3. Access dashboard: http://localhost:5173"
Write-Info "  4. View API docs: http://localhost:8000/docs"
Write-Host ""
Write-Info "🔧 Useful Commands:"
Write-Info "  • Check status: .\scripts\get-trading-status.ps1"
Write-Info "  • View logs: .\scripts\get-trading-logs.ps1"
Write-Info "  • Stop system: .\scripts\stop-trading-system.ps1"
Write-Host ""

if ($script:FailedSteps.Count -gt 0) {
    Write-Info "⚠️  Please resolve the warnings above before starting the system"
    exit 1
}

Write-Success "✨ Ready to trade!"
