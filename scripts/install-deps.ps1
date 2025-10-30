# PowerShell script to install development dependencies on Windows

Write-Host "Installing development dependencies for Autonomous Trading System..." -ForegroundColor Green

# Check if Python is installed
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Found Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "Python not found. Please install Python 3.11+ from https://python.org" -ForegroundColor Red
    exit 1
}

# Install Poetry
Write-Host "Installing Poetry..." -ForegroundColor Yellow
try {
    Invoke-RestMethod -Uri https://install.python-poetry.org | python -
    Write-Host "Poetry installed successfully" -ForegroundColor Green
} catch {
    Write-Host "Failed to install Poetry. Please install manually from https://python-poetry.org" -ForegroundColor Red
}

# Install Rust
Write-Host "Installing Rust..." -ForegroundColor Yellow
try {
    Invoke-RestMethod -Uri https://win.rustup.rs/ -OutFile rustup-init.exe
    .\rustup-init.exe -y --default-toolchain 1.78
    Remove-Item rustup-init.exe
    
    # Add Rust to PATH for current session
    $env:PATH += ";$env:USERPROFILE\.cargo\bin"
    
    Write-Host "Rust installed successfully" -ForegroundColor Green
} catch {
    Write-Host "Failed to install Rust. Please install manually from https://rustup.rs" -ForegroundColor Red
}

# Install Rust components
Write-Host "Installing Rust components..." -ForegroundColor Yellow
try {
    rustup component add rustfmt clippy
    Write-Host "Rust components installed successfully" -ForegroundColor Green
} catch {
    Write-Host "Failed to install Rust components" -ForegroundColor Red
}

# Install Python dependencies
Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
try {
    poetry install
    Write-Host "Python dependencies installed successfully" -ForegroundColor Green
} catch {
    Write-Host "Failed to install Python dependencies" -ForegroundColor Red
}

# Install pre-commit hooks
Write-Host "Installing pre-commit hooks..." -ForegroundColor Yellow
try {
    poetry run pre-commit install
    Write-Host "Pre-commit hooks installed successfully" -ForegroundColor Green
} catch {
    Write-Host "Failed to install pre-commit hooks" -ForegroundColor Red
}

Write-Host "Installation complete! Please restart your terminal to ensure PATH changes take effect." -ForegroundColor Green
Write-Host "Run 'make dev-setup' or 'poetry shell' to activate the development environment." -ForegroundColor Cyan