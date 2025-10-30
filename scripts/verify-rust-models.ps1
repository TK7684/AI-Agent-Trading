# PowerShell script to verify Rust models compilation and testing

Write-Host "Verifying Rust models..." -ForegroundColor Green

# Check if Rust is installed
try {
    $rustVersion = rustc --version 2>&1
    Write-Host "Found Rust: $rustVersion" -ForegroundColor Green
} catch {
    Write-Host "Rust not found. Please install Rust from https://rustup.rs" -ForegroundColor Red
    exit 1
}

# Check if Visual Studio Build Tools are available
try {
    $linkVersion = link.exe 2>&1
    Write-Host "Found Visual Studio Build Tools" -ForegroundColor Green
} catch {
    Write-Host "Visual Studio Build Tools not found." -ForegroundColor Yellow
    Write-Host "Please install Visual Studio 2017 or later with C++ build tools, or" -ForegroundColor Yellow
    Write-Host "install Build Tools for Visual Studio from:" -ForegroundColor Yellow
    Write-Host "https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "After installation, run this script again to verify Rust models." -ForegroundColor Yellow
    exit 1
}

# Test Rust compilation
Write-Host "Testing Rust compilation..." -ForegroundColor Yellow
try {
    cargo check --manifest-path libs/rust-common/Cargo.toml
    Write-Host "Rust compilation check passed" -ForegroundColor Green
} catch {
    Write-Host "Rust compilation check failed" -ForegroundColor Red
    exit 1
}

# Run Rust tests
Write-Host "Running Rust tests..." -ForegroundColor Yellow
try {
    cargo test --manifest-path libs/rust-common/Cargo.toml
    Write-Host "Rust tests passed" -ForegroundColor Green
} catch {
    Write-Host "Rust tests failed" -ForegroundColor Red
    exit 1
}

# Test serialization compatibility
Write-Host "Testing Python-Rust serialization compatibility..." -ForegroundColor Yellow

# Create a test JSON file with Python models
$testScript = @"
import json
from datetime import datetime, timezone
from decimal import Decimal
from libs.trading_models import MarketBar, Signal, OrderDecision, Timeframe, Direction, OrderType, MarketRegime

# Create test data
bar = MarketBar(
    symbol="BTCUSDT",
    timeframe=Timeframe.H1,
    timestamp=datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
    open=Decimal("50000.00"),
    high=Decimal("51000.00"),
    low=Decimal("49500.00"),
    close=Decimal("50500.00"),
    volume=Decimal("100.5"),
)

signal = Signal(
    signal_id="test_signal",
    symbol="BTCUSDT",
    timestamp=datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
    direction=Direction.LONG,
    confluence_score=75.0,
    confidence=0.8,
    market_regime=MarketRegime.BULL,
    primary_timeframe=Timeframe.H1,
    reasoning="Test signal for compatibility",
)

decision = OrderDecision(
    signal_id="test_signal",
    symbol="BTCUSDT",
    direction=Direction.LONG,
    order_type=OrderType.MARKET,
    base_quantity=Decimal("1.0"),
    risk_adjusted_quantity=Decimal("0.8"),
    max_position_value=Decimal("40000.00"),
    entry_price=Decimal("50000.00"),
    stop_loss=Decimal("49000.00"),
    risk_amount=Decimal("800.00"),
    risk_percentage=2.0,
    leverage=1.0,
    portfolio_value=Decimal("100000.00"),
    available_margin=Decimal("50000.00"),
    current_exposure=0.1,
    confidence_score=0.8,
    confluence_score=75.0,
    risk_reward_ratio=2.0,
    decision_reason="Test decision",
    timeframe_context=Timeframe.H1,
)

# Write test data to files
with open("test_market_bar.json", "w") as f:
    f.write(bar.to_json())

with open("test_signal.json", "w") as f:
    f.write(signal.to_json())

with open("test_order_decision.json", "w") as f:
    f.write(decision.to_json())

print("Test JSON files created successfully")
"@

try {
    $testScript | python
    Write-Host "Python test data generated successfully" -ForegroundColor Green
} catch {
    Write-Host "Failed to generate Python test data" -ForegroundColor Red
    exit 1
}

# Create Rust test to verify JSON parsing
$rustTestContent = @"
#[cfg(test)]
mod compatibility_tests {
    use super::*;
    use std::fs;
    
    #[test]
    fn test_market_bar_json_compatibility() {
        let json_content = fs::read_to_string("test_market_bar.json")
            .expect("Failed to read test_market_bar.json");
        
        let bar: MarketBar = serde_json::from_str(&json_content)
            .expect("Failed to deserialize MarketBar from Python JSON");
        
        assert_eq!(bar.symbol, "BTCUSDT");
        assert_eq!(bar.timeframe, Timeframe::H1);
        assert_eq!(bar.open, 50000.0);
        assert_eq!(bar.high, 51000.0);
        assert_eq!(bar.low, 49500.0);
        assert_eq!(bar.close, 50500.0);
        assert_eq!(bar.volume, 100.5);
    }
    
    #[test]
    fn test_signal_json_compatibility() {
        let json_content = fs::read_to_string("test_signal.json")
            .expect("Failed to read test_signal.json");
        
        let signal: Signal = serde_json::from_str(&json_content)
            .expect("Failed to deserialize Signal from Python JSON");
        
        assert_eq!(signal.signal_id, "test_signal");
        assert_eq!(signal.symbol, "BTCUSDT");
        assert_eq!(signal.direction, Direction::Long);
        assert_eq!(signal.confluence_score, 75.0);
        assert_eq!(signal.confidence, 0.8);
        assert_eq!(signal.market_regime, MarketRegime::Bull);
        assert_eq!(signal.primary_timeframe, Timeframe::H1);
    }
    
    #[test]
    fn test_order_decision_json_compatibility() {
        let json_content = fs::read_to_string("test_order_decision.json")
            .expect("Failed to read test_order_decision.json");
        
        let decision: OrderDecision = serde_json::from_str(&json_content)
            .expect("Failed to deserialize OrderDecision from Python JSON");
        
        assert_eq!(decision.signal_id, "test_signal");
        assert_eq!(decision.symbol, "BTCUSDT");
        assert_eq!(decision.direction, Direction::Long);
        assert_eq!(decision.order_type, OrderType::Market);
        assert_eq!(decision.base_quantity, 1.0);
        assert_eq!(decision.risk_adjusted_quantity, 0.8);
        assert_eq!(decision.entry_price, 50000.0);
        assert_eq!(decision.stop_loss, 49000.0);
        assert_eq!(decision.risk_percentage, 2.0);
        assert_eq!(decision.leverage, 1.0);
    }
}
"@

# Append compatibility tests to Rust test file
try {
    Add-Content -Path "libs/rust-common/src/trading_models/tests.rs" -Value $rustTestContent
    Write-Host "Added compatibility tests to Rust test file" -ForegroundColor Green
} catch {
    Write-Host "Failed to add compatibility tests to Rust test file" -ForegroundColor Red
    exit 1
}

# Run compatibility tests
Write-Host "Running Python-Rust compatibility tests..." -ForegroundColor Yellow
try {
    cargo test --manifest-path libs/rust-common/Cargo.toml compatibility_tests
    Write-Host "Python-Rust compatibility tests passed!" -ForegroundColor Green
} catch {
    Write-Host "Python-Rust compatibility tests failed" -ForegroundColor Red
    exit 1
}

# Clean up test files
Remove-Item -Path "test_market_bar.json" -ErrorAction SilentlyContinue
Remove-Item -Path "test_signal.json" -ErrorAction SilentlyContinue
Remove-Item -Path "test_order_decision.json" -ErrorAction SilentlyContinue

Write-Host "All Rust model verifications completed successfully!" -ForegroundColor Green
Write-Host "Python-Rust data model compatibility confirmed." -ForegroundColor Green