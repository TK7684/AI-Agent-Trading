"""Pytest configuration and fixtures."""

from dataclasses import dataclass

import pytest

from libs.trading_models.orchestrator import OrchestrationConfig


@pytest.fixture
def sample_market_data() -> dict:
    """Sample market data for testing."""
    return {
        "symbol": "BTCUSD",
        "timeframe": "1h",
        "ohlcv": [
            {"open": 50000, "high": 51000, "low": 49500, "close": 50500, "volume": 1000},
            {"open": 50500, "high": 51500, "low": 50000, "close": 51000, "volume": 1200},
        ]
    }


@pytest.fixture
def mock_config() -> dict:
    """Mock configuration for testing."""
    return {
        "risk": {
            "max_position_size": 0.02,
            "max_portfolio_exposure": 0.20,
            "stop_loss_pct": 0.02,
        },
        "trading": {
            "timeframes": ["15m", "1h", "4h", "1d"],
            "symbols": ["BTCUSD", "ETHUSD"],
        }
    }


@dataclass
class TestSystemConfig:
    """Test configuration for SystemConfig with proper defaults."""
    database_url: str = "sqlite:///:memory:"
    redis_url: str = "redis://localhost:6379/1"
    log_level: str = "INFO"
    environment: str = "test"
    api_key: str = "test_api_key"
    secret_key: str = "test_secret_key"
    base_url: str = "https://api.test.com"
    timeout: int = 30
    max_retries: int = 3
    enable_logging: bool = True
    debug_mode: bool = True
    cache_enabled: bool = False
    rate_limit: int = 100


class TestConfigBuilder:
    """Builder class for creating test configurations."""

    @staticmethod
    def create_test_system_config(**overrides) -> TestSystemConfig:
        """Create a TestSystemConfig with optional overrides."""
        config_dict = {
            "database_url": "sqlite:///:memory:",
            "redis_url": "redis://localhost:6379/1",
            "log_level": "INFO",
            "environment": "test",
            "api_key": "test_api_key",
            "secret_key": "test_secret_key",
            "base_url": "https://api.test.com",
            "timeout": 30,
            "max_retries": 3,
            "enable_logging": True,
            "debug_mode": True,
            "cache_enabled": False,
            "rate_limit": 100
        }
        config_dict.update(overrides)
        return TestSystemConfig(**config_dict)

    @staticmethod
    def create_test_orchestrator_config(**overrides) -> OrchestrationConfig:
        """Create an OrchestrationConfig with test-friendly defaults."""
        config_dict = {
            "symbols": ["BTCUSDT"],
            "timeframes": ["1h"],
            "base_check_interval": 1,  # Fast for tests
            "max_check_interval": 10,
            "min_check_interval": 1,
            "safe_mode_cooldown": 1,  # Short for tests
            "max_concurrent_analyses": 2,
            "enable_hot_reload": False,  # Disabled for tests
            "config_file_path": "test_config.toml",
            "daily_drawdown_threshold": 0.05,
            "monthly_drawdown_threshold": 0.15,
            "volatility_threshold_high": 0.05,
            "volatility_threshold_low": 0.02,
            "enable_caching": False,  # Disabled for tests
            "cache_ttl_seconds": 60,
            "max_cache_size": 100,
            "enable_compression": False
        }
        config_dict.update(overrides)
        return OrchestrationConfig(**config_dict)


@pytest.fixture
def test_orchestrator_config() -> OrchestrationConfig:
    """Fixture providing a test orchestrator configuration."""
    return TestConfigBuilder.create_test_orchestrator_config()


@pytest.fixture
def test_system_config() -> TestSystemConfig:
    """Fixture providing a test system configuration."""
    return TestConfigBuilder.create_test_system_config()
