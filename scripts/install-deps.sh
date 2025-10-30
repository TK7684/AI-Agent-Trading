#!/bin/bash
# Shell script to install development dependencies on Linux/macOS

set -e

echo "Installing development dependencies for Autonomous Trading System..."

# Check if Python is installed
if command -v python3 &> /dev/null; then
    echo "Found Python: $(python3 --version)"
else
    echo "Python 3.11+ not found. Please install Python first."
    exit 1
fi

# Install Poetry
echo "Installing Poetry..."
if ! command -v poetry &> /dev/null; then
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="$HOME/.local/bin:$PATH"
    echo "Poetry installed successfully"
else
    echo "Poetry already installed: $(poetry --version)"
fi

# Install Rust
echo "Installing Rust..."
if ! command -v cargo &> /dev/null; then
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain 1.78
    source "$HOME/.cargo/env"
    echo "Rust installed successfully"
else
    echo "Rust already installed: $(rustc --version)"
fi

# Install Rust components
echo "Installing Rust components..."
rustup component add rustfmt clippy

# Install Python dependencies
echo "Installing Python dependencies..."
poetry install

# Install pre-commit hooks
echo "Installing pre-commit hooks..."
poetry run pre-commit install

echo "Installation complete!"
echo "Run 'source ~/.cargo/env' to add Rust to your PATH"
echo "Run 'poetry shell' to activate the development environment"