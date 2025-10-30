<#
.SYNOPSIS
    Build Rust execution gateway

.DESCRIPTION
    Compiles the execution gateway with optimizations for production or development.

.PARAMETER Release
    Build in release mode with optimizations (default)

.PARAMETER Debug
    Build in debug mode for faster compilation

.PARAMETER Clean
    Clean build artifacts before building

.EXAMPLE
    .\Build-ExecutionGateway.ps1
    Build in release mode

.EXAMPLE
    .\Build-ExecutionGateway.ps1 -Debug
    Build in debug mode

.EXAMPLE
    .\Build-ExecutionGateway.ps1 -Clean
    Clean and rebuild
#>

param(
    [switch]$Release = $true,
    [switch]$Debug,
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

# Colors for output
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-Error { Write-Host $args -ForegroundColor Red }

Write-Info "🦀 Trading System - Rust Execution Gateway Build"
Write-Info "=" * 50

# Check if Rust is installed
if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Write-Error "❌ Rust/Cargo not found"
    Write-Info "Install Rust from: https://rustup.rs/"
    exit 1
}

# Show Rust version
$rustVersion = cargo --version
Write-Info "Rust version: $rustVersion"

# Clean if requested
if ($Clean) {
    Write-Info "Cleaning build artifacts..."
    cargo clean --package execution-gateway
    Write-Success "✅ Clean complete"
}

# Determine build mode
$buildMode = if ($Debug) { "debug" } else { "release" }
Write-Info "Build mode: $buildMode"

# Build command
try {
    Write-Info "Building execution gateway..."
    $startTime = Get-Date
    
    if ($Debug) {
        cargo build --package execution-gateway
    }
    else {
        cargo build --package execution-gateway --release
    }
    
    $endTime = Get-Date
    $duration = ($endTime - $startTime).TotalSeconds
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "✅ Build successful in $([math]::Round($duration, 2)) seconds"
        
        # Show binary info
        $binaryPath = if ($Debug) {
            "target\debug\execution-gateway.exe"
        } else {
            "target\release\execution-gateway.exe"
        }
        
        if (Test-Path $binaryPath) {
            $fileSize = (Get-Item $binaryPath).Length / 1MB
            Write-Info "`nBinary details:"
            Write-Info "  • Path: $binaryPath"
            Write-Info "  • Size: $([math]::Round($fileSize, 2)) MB"
            Write-Info "  • Mode: $buildMode"
            
            if (-not $Debug) {
                Write-Info "`nOptimizations enabled:"
                Write-Info "  • LTO (Link Time Optimization)"
                Write-Info "  • Code generation optimizations"
                Write-Info "  • Strip debug symbols"
            }
        }
        
        Write-Info "`nNext steps:"
        Write-Info "  1. Run: .\scripts\start-trading-system.ps1"
        Write-Info "  2. Or test directly: $binaryPath --help"
    }
    else {
        Write-Error "❌ Build failed with exit code: $LASTEXITCODE"
        exit 1
    }
}
catch {
    Write-Error "❌ Build error: $_"
    Write-Info "`nTroubleshooting:"
    Write-Info "  • Check Rust installation: rustc --version"
    Write-Info "  • Update Rust: rustup update"
    Write-Info "  • Check Cargo.toml for errors"
    exit 1
}

# Run tests if in debug mode
if ($Debug) {
    Write-Info "`nRunning tests..."
    cargo test --package execution-gateway
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "✅ Tests passed"
    }
    else {
        Write-Warning "⚠️  Some tests failed"
    }
}

Write-Info "`n" + ("=" * 50)
Write-Success "🎉 Execution gateway build complete!"
