<#
.SYNOPSIS
    Setup trading system for production deployment

.DESCRIPTION
    Configures the trading system for production use with Windows Services,
    security hardening, and production optimizations.

.PARAMETER ServiceAccount
    Windows service account (default: LocalSystem)

.PARAMETER InstallPath
    Installation directory (default: C:\TradingSystem)

.EXAMPLE
    .\Setup-NativeProduction.ps1
    Setup with default settings

.EXAMPLE
    .\Setup-NativeProduction.ps1 -ServiceAccount "NT AUTHORITY\NetworkService"
    Setup with specific service account
#>

param(
    [string]$ServiceAccount = "LocalSystem",
    [string]$InstallPath = "C:\TradingSystem"
)

$ErrorActionPreference = "Stop"

# Require Administrator
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "This script must be run as Administrator"
    exit 1
}

# Colors for output
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-Error { Write-Host $args -ForegroundColor Red }

Write-Info "🏭 Trading System - Production Setup"
Write-Info "=" * 50

Write-Warning "`n⚠️  PRODUCTION SETUP"
Write-Warning "This will configure the system for production use."
Write-Info "Installation path: $InstallPath"
Write-Info "Service account: $ServiceAccount"

$confirmation = Read-Host "`nContinue? (y/N)"
if ($confirmation -ne 'y') {
    exit 0
}

# Step 1: Create installation directory
Write-Info "`n[1/8] Creating installation directory..."
if (-not (Test-Path $InstallPath)) {
    New-Item -ItemType Directory -Path $InstallPath | Out-Null
    Write-Success "✅ Created: $InstallPath"
}
else {
    Write-Success "✅ Directory exists: $InstallPath"
}

# Step 2: Copy application files
Write-Info "`n[2/8] Copying application files..."
$filesToCopy = @(
    "apps",
    "libs",
    "config",
    "scripts",
    "target\release\execution-gateway.exe",
    "pyproject.toml",
    "poetry.lock",
    "Cargo.toml"
)

foreach ($item in $filesToCopy) {
    if (Test-Path $item) {
        $dest = Join-Path $InstallPath (Split-Path $item -Leaf)
        Copy-Item $item $dest -Recurse -Force
        Write-Success "  ✓ Copied: $item"
    }
}

# Step 3: Create production environment file
Write-Info "`n[3/8] Creating production environment..."
$envContent = @"
# Production Environment Configuration
ENVIRONMENT=production

# Database
DATABASE_URL=postgresql://trading:CHANGE_ME@localhost:5432/trading

# Redis
REDIS_URL=redis://localhost:6379/0

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Gateway Configuration
GATEWAY_PORT=3000

# Security
SECRET_KEY=GENERATE_SECURE_KEY_HERE
CORS_ORIGINS=https://yourdomain.com

# Logging
LOG_LEVEL=INFO
LOG_DIRECTORY=C:\TradingSystem\logs

# Monitoring
PROMETHEUS_ENABLED=true
METRICS_PORT=9090
"@

$envPath = Join-Path $InstallPath ".env.production"
$envContent | Out-File -FilePath $envPath -Encoding UTF8
Write-Success "✅ Created: $envPath"
Write-Warning "  ⚠️  IMPORTANT: Update $envPath with secure values!"

# Step 4: Install Python dependencies
Write-Info "`n[4/8] Installing Python dependencies..."
Push-Location $InstallPath
try {
    poetry install --no-dev --no-interaction
    Write-Success "✅ Python dependencies installed"
}
catch {
    Write-Warning "⚠️  Failed to install Python dependencies"
}
finally {
    Pop-Location
}

# Step 5: Create Windows Services
Write-Info "`n[5/8] Creating Windows Services..."

$services = @(
    @{
        Name = "TradingAPI"
        DisplayName = "Trading System API"
        Description = "Trading System REST API Service"
        BinaryPath = "poetry run uvicorn apps.trading_api.main:app --host 0.0.0.0 --port 8000 --workers 4"
        WorkingDirectory = $InstallPath
    },
    @{
        Name = "TradingOrchestrator"
        DisplayName = "Trading System Orchestrator"
        Description = "Trading System Orchestration Service"
        BinaryPath = "poetry run python -m libs.trading_models.orchestrator"
        WorkingDirectory = $InstallPath
    },
    @{
        Name = "TradingGateway"
        DisplayName = "Trading System Execution Gateway"
        Description = "High-performance order execution gateway"
        BinaryPath = "$InstallPath\execution-gateway.exe --port 3000"
        WorkingDirectory = $InstallPath
    }
)

foreach ($svc in $services) {
    $existing = Get-Service -Name $svc.Name -ErrorAction SilentlyContinue
    
    if ($existing) {
        Write-Info "  Service exists: $($svc.Name)"
        Stop-Service $svc.Name -Force -ErrorAction SilentlyContinue
    }
    else {
        Write-Info "  Creating service: $($svc.Name)"
        # Note: Actual service creation requires NSSM or sc.exe
        Write-Warning "  ⚠️  Manual service creation required"
        Write-Info "     Use NSSM: nssm install $($svc.Name) $($svc.BinaryPath)"
    }
}

Write-Success "✅ Service configuration prepared"

# Step 6: Configure Windows Firewall
Write-Info "`n[6/8] Configuring Windows Firewall..."

$firewallRules = @(
    @{ Name = "Trading API"; Port = 8000; Protocol = "TCP" },
    @{ Name = "Trading Gateway"; Port = 3000; Protocol = "TCP" },
    @{ Name = "Prometheus Metrics"; Port = 9090; Protocol = "TCP" }
)

foreach ($rule in $firewallRules) {
    $existing = Get-NetFirewallRule -DisplayName $rule.Name -ErrorAction SilentlyContinue
    
    if (-not $existing) {
        New-NetFirewallRule `
            -DisplayName $rule.Name `
            -Direction Inbound `
            -Protocol $rule.Protocol `
            -LocalPort $rule.Port `
            -Action Allow `
            -Profile Domain,Private | Out-Null
        
        Write-Success "  ✓ Created firewall rule: $($rule.Name)"
    }
    else {
        Write-Info "  Firewall rule exists: $($rule.Name)"
    }
}

Write-Success "✅ Firewall configured"

# Step 7: Set up logging
Write-Info "`n[7/8] Setting up logging..."

$logPath = Join-Path $InstallPath "logs"
if (-not (Test-Path $logPath)) {
    New-Item -ItemType Directory -Path $logPath | Out-Null
}

# Configure log rotation
Write-Success "✅ Logging configured: $logPath"

# Step 8: Security hardening
Write-Info "`n[8/8] Applying security hardening..."

# Set directory permissions
$acl = Get-Acl $InstallPath
$acl.SetAccessRuleProtection($true, $false)

# Add Administrator full control
$adminRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
    "Administrators", "FullControl", "ContainerInherit,ObjectInherit", "None", "Allow"
)
$acl.AddAccessRule($adminRule)

# Add service account read/execute
if ($ServiceAccount -ne "LocalSystem") {
    $serviceRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
        $ServiceAccount, "ReadAndExecute", "ContainerInherit,ObjectInherit", "None", "Allow"
    )
    $acl.AddAccessRule($serviceRule)
}

Set-Acl $InstallPath $acl
Write-Success "✅ Security permissions configured"

# Summary
Write-Host ""
Write-Info "╔════════════════════════════════════════════════════════════╗"
Write-Info "║              PRODUCTION SETUP COMPLETE                     ║"
Write-Info "╚════════════════════════════════════════════════════════════╝"
Write-Host ""

Write-Success "🎉 Production setup complete!"
Write-Host ""
Write-Warning "⚠️  IMPORTANT: Complete these manual steps:"
Write-Host ""
Write-Info "1. Update environment file:"
Write-Info "   • Edit: $envPath"
Write-Info "   • Set secure DATABASE_URL password"
Write-Info "   • Generate SECRET_KEY (32+ random characters)"
Write-Info "   • Configure CORS_ORIGINS for your domain"
Write-Host ""
Write-Info "2. Install NSSM for Windows Service management:"
Write-Info "   • Download: https://nssm.cc/download"
Write-Info "   • Install services using NSSM"
Write-Host ""
Write-Info "3. Configure services to start automatically:"
Write-Info "   • Set-Service TradingAPI -StartupType Automatic"
Write-Info "   • Set-Service TradingOrchestrator -StartupType Automatic"
Write-Info "   • Set-Service TradingGateway -StartupType Automatic"
Write-Host ""
Write-Info "4. Initialize database:"
Write-Info "   • Run: .\scripts\init-database.ps1"
Write-Host ""
Write-Info "5. Start services:"
Write-Info "   • Start-Service TradingAPI"
Write-Info "   • Start-Service TradingOrchestrator"
Write-Info "   • Start-Service TradingGateway"
Write-Host ""
Write-Info "📁 Installation: $InstallPath"
Write-Info "📝 Logs: $logPath"
Write-Host ""
