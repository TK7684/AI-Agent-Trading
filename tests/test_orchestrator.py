"""
Integration tests for the orchestrator and main trading pipeline.

Tests the complete trading workflow from market analysis to execution,
including position lifecycle management and error handling.
"""

import asyncio
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from libs.trading_models.config_manager import ConfigManager, TradingConfig
from libs.trading_models.enums import Direction, MarketRegime, Timeframe
from libs.trading_models.orchestrator import (
    CheckInterval,
    OrchestrationConfig,
    OrchestrationState,
    Orchestrator,
    PositionLifecycle,
    create_orchestrator,
)
from libs.trading_models.signals import Signal


class TestOrchestrationConfig:
    """Test orchestration configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = OrchestrationConfig()

        assert config.symbols == ["BTCUSDT", "ETHUSDT"]
        assert config.timeframes == ["15m", "1h", "4h", "1d"]
        assert config.base_check_interval == 1800
        assert config.max_check_interval == 14400
        assert config.min_check_interval == 900
        assert config.safe_mode_cooldown == 3600
        assert config.max_concurrent_analyses == 5
        assert config.daily_drawdown_threshold == 0.08
        assert config.monthly_drawdown_threshold == 0.20

    def test_custom_config(self):
        """Test custom configuration values."""
        config = OrchestrationConfig(
            symbols=["BTCUSDT"],
            timeframes=["1h", "4h"],
            base_check_interval=3600,
            safe_mode_cooldown=7200,
        )

        assert config.symbols == ["BTCUSDT"]
        assert config.timeframes == ["1h", "4h"]
        assert config.base_check_interval == 3600
        assert config.safe_mode_cooldown == 7200


class TestPositionLifecycle:
    """Test position lifecycle management."""

    def test_position_lifecycle_creation(self):
        """Test position lifecycle creation."""
        lifecycle = PositionLifecycle(
            position_id="test_pos_1",
            symbol="BTCUSDT",
            state="open",
            entry_time=datetime.now(),
            last_check=datetime.now(),
        )

        assert lifecycle.position_id == "test_pos_1"
        assert lifecycle.symbol == "BTCUSDT"
        assert lifecycle.state == "open"
        assert lifecycle.adjustment_count == 0
        assert lifecycle.max_adjustments == 3

    def test_position_lifecycle_with_stops(self):
        """Test position lifecycle with stop loss and take profit."""
        lifecycle = PositionLifecycle(
            position_id="test_pos_2",
            symbol="ETHUSDT",
            state="monitoring",
            entry_time=datetime.now(),
            last_check=datetime.now(),
            stop_loss=1800.0,
            take_profit=2200.0,
            trailing_stop=1850.0,
        )

        assert lifecycle.stop_loss == 1800.0
        assert lifecycle.take_profit == 2200.0
        assert lifecycle.trailing_stop == 1850.0


class TestOrchestrator:
    """Test orchestrator functionality."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return OrchestrationConfig(
            symbols=["BTCUSDT"],
            timeframes=["1h"],
            base_check_interval=1800,  # 30 minutes (valid, >= min_check_interval)
            min_check_interval=900,  # 15 minutes
            max_check_interval=3600,  # 1 hour
            max_concurrent_analyses=2,
        )

    @pytest.fixture
    def orchestrator(self, config):
        """Create orchestrator instance for testing."""
        return Orchestrator(config)

    def test_orchestrator_initialization(self, orchestrator):
        """Test orchestrator initialization."""
        assert orchestrator.state == OrchestrationState.STOPPED
        assert hasattr(orchestrator, "config")
        assert hasattr(orchestrator, "analysis_cache")
        assert hasattr(orchestrator, "market_data_manager")
        assert hasattr(orchestrator, "technical_indicators")
        assert hasattr(orchestrator, "pattern_recognition")
        assert hasattr(orchestrator, "confluence_scoring")
        assert orchestrator._running is False
        assert not orchestrator._stop_event.is_set()

    def test_orchestrator_factory(self):
        """Test orchestrator factory function."""
        orchestrator = create_orchestrator()
        assert isinstance(orchestrator, Orchestrator)
        assert orchestrator.config.symbols == ["BTCUSDT", "ETHUSDT"]

        # Test with overrides
        orchestrator = create_orchestrator({"symbols": ["BTCUSDT"]})
        assert orchestrator.config.symbols == ["BTCUSDT"]

    def test_safe_mode_trigger(self, orchestrator):
        """Test safe mode triggering."""
        assert not orchestrator._is_in_safe_mode()

        orchestrator.trigger_safe_mode("Test trigger")

        assert orchestrator.state == OrchestrationState.SAFE_MODE
        assert orchestrator.safe_mode_until is not None
        assert orchestrator._is_in_safe_mode()

    def test_safe_mode_expiry(self, orchestrator):
        """Test safe mode expiry."""
        # Trigger safe mode with short cooldown
        orchestrator.config.safe_mode_cooldown = 1  # 1 second
        orchestrator.trigger_safe_mode("Test trigger")

        assert orchestrator._is_in_safe_mode()

        # Wait for expiry
        import time

        time.sleep(2)

        # Should exit safe mode
        assert not orchestrator._is_in_safe_mode()
        assert orchestrator.state == OrchestrationState.RUNNING

    def test_should_analyze_symbol(self, orchestrator):
        """Test symbol analysis timing logic."""
        symbol = "BTCUSDT"

        # Should analyze if never analyzed before
        assert orchestrator._should_analyze_symbol(symbol)

        # Mark as analyzed
        orchestrator.last_analysis[symbol] = datetime.now()

        # Should not analyze immediately
        assert not orchestrator._should_analyze_symbol(symbol)

        # Should analyze after interval
        orchestrator.last_analysis[symbol] = datetime.now() - timedelta(seconds=2000)
        assert orchestrator._should_analyze_symbol(symbol)

    @pytest.mark.asyncio
    async def test_position_lifecycle_management(self, orchestrator):
        """Test position lifecycle management."""
        # Create test position
        lifecycle = PositionLifecycle(
            position_id="test_pos",
            symbol="BTCUSDT",
            state="open",
            entry_time=datetime.now(),
            last_check=datetime.now(),
        )

        orchestrator.active_positions["test_pos"] = lifecycle

        # Mock the lifecycle management methods
        orchestrator._position_needs_adjustment = AsyncMock(return_value=False)
        orchestrator._position_should_close = AsyncMock(return_value=False)

        # Test state transition from open to monitoring
        await orchestrator._manage_position_lifecycle(lifecycle)
        assert lifecycle.state == "monitoring"

        # Test adjustment needed
        orchestrator._position_needs_adjustment.return_value = True
        orchestrator._adjust_position = AsyncMock(return_value=True)

        # First call transitions to adjusting
        await orchestrator._manage_position_lifecycle(lifecycle)
        assert lifecycle.state == "adjusting"

        # Second call performs adjustment and returns to monitoring
        orchestrator._position_needs_adjustment.return_value = (
            False  # No more adjustments needed
        )
        await orchestrator._manage_position_lifecycle(lifecycle)
        assert lifecycle.state == "monitoring"
        assert lifecycle.adjustment_count == 1

        # Test position closure
        orchestrator._position_needs_adjustment.return_value = False
        orchestrator._position_should_close.return_value = True
        orchestrator._close_position = AsyncMock(return_value=True)

        # First call transitions to closing
        await orchestrator._manage_position_lifecycle(lifecycle)
        assert lifecycle.state == "closing"

        # Second call performs closure and marks as closed
        await orchestrator._manage_position_lifecycle(lifecycle)
        assert lifecycle.state == "closed"

    @pytest.mark.asyncio
    async def test_market_volatility_calculation(self, orchestrator):
        """Test market volatility calculation."""
        volatility = await orchestrator._calculate_market_volatility()
        assert isinstance(volatility, float)
        assert volatility >= 0

    @pytest.mark.asyncio
    async def test_trading_signal_generation(self, orchestrator):
        """Test trading signal generation."""
        signal = await orchestrator._generate_trading_signal(
            "BTCUSDT", {"rsi": 30}, [], {"sentiment": "bullish"}
        )

        assert signal is not None
        assert signal.symbol == "BTCUSDT"
        assert signal.direction == Direction.LONG
        assert 0 <= signal.confidence <= 1
        assert 0 <= signal.confluence_score <= 100

    @pytest.mark.asyncio
    async def test_process_symbol_analysis(self, orchestrator):
        """Test complete symbol analysis process."""
        # Mock all the analysis methods
        orchestrator._fetch_market_data = AsyncMock(return_value={"data": "test"})
        orchestrator._compute_indicators = AsyncMock(return_value={"rsi": 50})
        orchestrator._detect_patterns = AsyncMock(return_value=[])
        orchestrator._get_llm_analysis = AsyncMock(
            return_value={"sentiment": "neutral"}
        )
        orchestrator._generate_trading_signal = AsyncMock(
            return_value=Signal(
                signal_id="test_signal_1",
                symbol="BTCUSDT",
                timestamp=datetime.now(),
                direction=Direction.LONG,
                confluence_score=80.0,
                confidence=0.8,
                market_regime=MarketRegime.SIDEWAYS,
                primary_timeframe=Timeframe.H1,
                reasoning="Test signal",
            )
        )
        orchestrator._make_trading_decision = AsyncMock(return_value={"action": "buy"})
        orchestrator._execute_trading_decision = AsyncMock()

        # Process analysis
        await orchestrator._process_symbol_analysis("BTCUSDT")

        # Verify all methods were called
        orchestrator._fetch_market_data.assert_called_once_with("BTCUSDT")
        orchestrator._compute_indicators.assert_called_once()
        orchestrator._detect_patterns.assert_called_once()
        orchestrator._get_llm_analysis.assert_called_once()
        orchestrator._generate_trading_signal.assert_called_once()
        orchestrator._make_trading_decision.assert_called_once()
        orchestrator._execute_trading_decision.assert_called_once()

        # Check that last analysis time was updated
        assert "BTCUSDT" in orchestrator.last_analysis

    @pytest.mark.asyncio
    async def test_process_symbol_analysis_low_confidence(self, orchestrator):
        """Test symbol analysis with low confidence signal."""
        # Mock methods with low confidence signal
        orchestrator._fetch_market_data = AsyncMock(return_value={"data": "test"})
        orchestrator._compute_indicators = AsyncMock(return_value={"rsi": 50})
        orchestrator._detect_patterns = AsyncMock(return_value=[])
        orchestrator._get_llm_analysis = AsyncMock(
            return_value={"sentiment": "neutral"}
        )
        orchestrator._generate_trading_signal = AsyncMock(
            return_value=Signal(
                signal_id="test_signal_2",
                symbol="BTCUSDT",
                timestamp=datetime.now(),
                direction=Direction.LONG,
                confluence_score=30.0,
                confidence=0.3,  # Low confidence
                market_regime=MarketRegime.SIDEWAYS,
                primary_timeframe=Timeframe.H1,
                reasoning="Low confidence signal",
            )
        )
        orchestrator._make_trading_decision = AsyncMock()
        orchestrator._execute_trading_decision = AsyncMock()

        # Process analysis
        await orchestrator._process_symbol_analysis("BTCUSDT")

        # Should not make trading decision due to low confidence
        orchestrator._make_trading_decision.assert_not_called()
        orchestrator._execute_trading_decision.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_symbol_analysis_no_market_data(self, orchestrator):
        """Test symbol analysis when market data is unavailable."""
        # Mock fetch_market_data to return None
        orchestrator._fetch_market_data = AsyncMock(return_value=None)
        orchestrator._compute_indicators = AsyncMock()

        # Process analysis
        await orchestrator._process_symbol_analysis("BTCUSDT")

        # Should return early without calling other methods
        orchestrator._compute_indicators.assert_not_called()

    @pytest.mark.asyncio
    async def test_emergency_position_closure(self, orchestrator):
        """Test emergency position closure."""
        # Add test positions
        pos1 = PositionLifecycle(
            "pos1", "BTCUSDT", "monitoring", datetime.now(), datetime.now()
        )
        pos2 = PositionLifecycle(
            "pos2", "ETHUSDT", "open", datetime.now(), datetime.now()
        )

        orchestrator.active_positions["pos1"] = pos1
        orchestrator.active_positions["pos2"] = pos2

        # Trigger emergency closure
        await orchestrator._emergency_position_closure()

        # All positions should be marked for closing
        assert pos1.state == "closing"
        assert pos2.state == "closing"


class TestConfigManager:
    """Test configuration manager functionality."""

    @pytest.fixture
    def temp_config_file(self):
        """Create temporary configuration file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config_content = {
                "symbols": ["BTCUSDT", "ETHUSDT"],
                "timeframes": ["1h", "4h"],
                "base_check_interval": 3600,
                "daily_drawdown_threshold": 0.05,
                "llm_models": ["gpt-4"],
                "routing_policy": "cost_aware",
                "indicator_weights": {
                    "rsi": 0.2,
                    "ema": 0.3,
                    "macd": 0.2,
                    "bollinger": 0.1,
                    "volume": 0.1,
                    "patterns": 0.1,
                    "llm": 0.0,
                },
            }
            json.dump(config_content, f, indent=2)
            f.flush()
            yield f.name

        # Cleanup
        Path(f.name).unlink(missing_ok=True)

    def test_config_manager_initialization(self):
        """Test configuration manager initialization."""
        manager = ConfigManager("nonexistent.json")
        assert manager.config_path == Path("nonexistent.json")
        assert manager._config is None
        assert manager._last_modified is None

    def test_load_config_from_file(self, temp_config_file):
        """Test loading configuration from file."""
        manager = ConfigManager(temp_config_file)
        config = manager.load_config()

        assert config.symbols == ["BTCUSDT", "ETHUSDT"]
        assert config.timeframes == ["1h", "4h"]
        assert config.base_check_interval == 3600
        assert config.daily_drawdown_threshold == 0.05
        assert config.llm_models == ["gpt-4"]
        assert config.routing_policy == "cost_aware"

    def test_load_config_nonexistent_file(self):
        """Test loading configuration when file doesn't exist."""
        manager = ConfigManager("nonexistent.json")
        config = manager.load_config()

        # Should return default configuration
        assert isinstance(config, TradingConfig)
        assert config.symbols == ["BTCUSDT", "ETHUSDT"]  # Default values

    def test_config_validation_errors(self, temp_config_file):
        """Test configuration validation with invalid values."""
        # Create invalid config
        invalid_config = {
            "symbols": [],
            "timeframes": ["invalid_tf"],
            "daily_drawdown_threshold": 1.5,
            "routing_policy": "invalid_policy",
            "indicator_weights": {"rsi": 0.5, "ema": 0.3},
        }
        with open(temp_config_file, "w") as f:
            json.dump(invalid_config, f)

        manager = ConfigManager(temp_config_file)

        # Should handle validation errors gracefully
        config = manager.load_config()
        assert isinstance(config, TradingConfig)  # Should return default config

    @patch.dict(
        "os.environ",
        {
            "TRADING_SYMBOLS": "BTCUSDT,ETHUSDT,ADAUSDT",
            "TRADING_CHECK_INTERVAL": "7200",
            "TRADING_DAILY_DD_THRESHOLD": "0.06",
        },
    )
    def test_environment_variable_overrides(self, temp_config_file):
        """Test environment variable overrides."""
        manager = ConfigManager(temp_config_file)
        config = manager.load_config()

        # Environment variables should override file values
        assert config.symbols == ["BTCUSDT", "ETHUSDT", "ADAUSDT"]
        assert config.base_check_interval == 7200
        assert config.daily_drawdown_threshold == 0.06

    def test_check_for_updates(self, temp_config_file):
        """Test configuration file update detection."""
        manager = ConfigManager(temp_config_file)
        manager.load_config()

        # No updates initially
        assert not manager.check_for_updates()

        # Modify file
        import time

        time.sleep(0.1)  # Ensure different mtime
        with open(temp_config_file) as f:
            config_data = json.load(f)
        config_data["_updated"] = True
        with open(temp_config_file, "w") as f:
            json.dump(config_data, f)

        # Should detect update
        assert manager.check_for_updates()

    def test_callback_registration(self, temp_config_file):
        """Test configuration change callback registration."""
        manager = ConfigManager(temp_config_file)
        manager.load_config()

        callback_called = False
        callback_config = None

        def test_callback(config):
            nonlocal callback_called, callback_config
            callback_called = True
            callback_config = config

        manager.register_callback(test_callback)

        # Trigger update
        import time

        time.sleep(0.1)
        with open(temp_config_file) as f:
            config_data = json.load(f)
        config_data["_callback_test"] = True
        with open(temp_config_file, "w") as f:
            json.dump(config_data, f)

        manager.check_for_updates()

        assert callback_called
        assert isinstance(callback_config, TradingConfig)

    def test_save_config(self, temp_config_file):
        """Test saving configuration to file."""
        manager = ConfigManager(temp_config_file)

        # Create modified config
        config = TradingConfig(
            symbols=["BTCUSDT"], base_check_interval=7200, daily_drawdown_threshold=0.06
        )

        # Save config
        manager.save_config(config)

        # Load and verify
        new_manager = ConfigManager(temp_config_file)
        loaded_config = new_manager.load_config()

        assert loaded_config.symbols == ["BTCUSDT"]
        assert loaded_config.base_check_interval == 7200
        assert loaded_config.daily_drawdown_threshold == 0.06

    def test_export_config_template(self):
        """Test configuration template export."""
        manager = ConfigManager()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            template_path = f.name

        try:
            manager.export_config_template(template_path)

            # Verify template was created
            assert Path(template_path).exists()

            # Verify template content
            with open(template_path) as f:
                config_data = json.load(f)
                assert "_metadata" in config_data
                assert "symbols" in config_data
                assert "timeframes" in config_data
                assert "indicator_weights" in config_data

        finally:
            Path(template_path).unlink(missing_ok=True)


class TestIntegrationWorkflow:
    """Integration tests for complete trading workflow."""

    @pytest.fixture
    def mock_orchestrator(self):
        """Create orchestrator with mocked components."""
        config = OrchestrationConfig(
            symbols=["BTCUSDT"], timeframes=["1h"], base_check_interval=60
        )
        orchestrator = Orchestrator(config)

        # Mock all external dependencies
        orchestrator.market_data = Mock()
        orchestrator.indicators = Mock()
        orchestrator.pattern_recognition = Mock()
        orchestrator.confluence_scoring = Mock()
        orchestrator.llm_router = Mock()
        orchestrator.risk_manager = Mock()
        orchestrator.memory_learning = Mock()

        return orchestrator

    @pytest.mark.asyncio
    async def test_complete_trading_pipeline(self, mock_orchestrator):
        """Test complete trading pipeline from analysis to execution."""
        orchestrator = mock_orchestrator

        # Mock the pipeline methods
        orchestrator._fetch_market_data = AsyncMock(
            return_value={
                "symbol": "BTCUSDT",
                "ohlcv": [
                    {
                        "open": 50000,
                        "high": 51000,
                        "low": 49000,
                        "close": 50500,
                        "volume": 1000,
                    }
                ],
            }
        )

        orchestrator._compute_indicators = AsyncMock(
            return_value={
                "rsi": 65.0,
                "ema_20": 50200.0,
                "macd": {"macd": 100, "signal": 80, "histogram": 20},
            }
        )

        orchestrator._detect_patterns = AsyncMock(
            return_value=[{"type": "support_break", "confidence": 0.8}]
        )

        orchestrator._get_llm_analysis = AsyncMock(
            return_value={
                "sentiment": "bullish",
                "confidence": 0.75,
                "reasoning": "Strong technical setup with RSI momentum",
            }
        )

        orchestrator._generate_trading_signal = AsyncMock(
            return_value=Signal(
                signal_id="integration_test_signal",
                symbol="BTCUSDT",
                timestamp=datetime.now(),
                direction=Direction.LONG,
                confluence_score=80.0,
                confidence=0.8,
                market_regime=MarketRegime.SIDEWAYS,
                primary_timeframe=Timeframe.H1,
                reasoning="Strong bullish confluence",
            )
        )

        orchestrator._make_trading_decision = AsyncMock(
            return_value={
                "action": "buy",
                "symbol": "BTCUSDT",
                "size": 0.01,
                "price": 50500,
                "stop_loss": 49000,
                "take_profit": 52000,
            }
        )

        orchestrator._execute_trading_decision = AsyncMock()

        # Run the complete pipeline
        await orchestrator._process_symbol_analysis("BTCUSDT")

        # Verify all steps were executed
        orchestrator._fetch_market_data.assert_called_once_with("BTCUSDT")
        orchestrator._compute_indicators.assert_called_once()
        orchestrator._detect_patterns.assert_called_once()
        orchestrator._get_llm_analysis.assert_called_once()
        orchestrator._generate_trading_signal.assert_called_once()
        orchestrator._make_trading_decision.assert_called_once()
        orchestrator._execute_trading_decision.assert_called_once()

        # Verify decision was made with correct signal
        call_args = orchestrator._make_trading_decision.call_args[0][0]
        assert call_args.symbol == "BTCUSDT"
        assert call_args.confidence == 0.8
        assert call_args.confluence_score == 80.0

    @pytest.mark.asyncio
    async def test_error_handling_in_pipeline(self, mock_orchestrator):
        """Test error handling in trading pipeline."""
        orchestrator = mock_orchestrator

        # Mock market data fetch to raise exception
        orchestrator._fetch_market_data = AsyncMock(side_effect=Exception("API Error"))
        orchestrator._compute_indicators = AsyncMock()

        # Should handle error gracefully
        await orchestrator._process_symbol_analysis("BTCUSDT")

        # Should not proceed to indicators calculation
        orchestrator._compute_indicators.assert_not_called()

    @pytest.mark.asyncio
    async def test_safe_mode_workflow(self, mock_orchestrator):
        """Test safe mode workflow and recovery."""
        orchestrator = mock_orchestrator
        orchestrator.config.safe_mode_cooldown = 1  # 1 second for testing

        # Trigger safe mode
        orchestrator.trigger_safe_mode("Test drawdown exceeded")

        assert orchestrator.state == OrchestrationState.SAFE_MODE
        assert orchestrator._is_in_safe_mode()

        # Mock position closure
        orchestrator._emergency_position_closure = AsyncMock()

        # Wait for safe mode to expire
        import time

        time.sleep(2)

        # Should exit safe mode
        assert not orchestrator._is_in_safe_mode()
        assert orchestrator.state == OrchestrationState.RUNNING

    @pytest.mark.asyncio
    async def test_concurrent_analysis_limit(self, mock_orchestrator):
        """Test concurrent analysis limit enforcement."""
        orchestrator = mock_orchestrator
        orchestrator.config.max_concurrent_analyses = 2
        orchestrator.config.symbols = ["BTCUSDT", "ETHUSDT", "ADAUSDT"]

        # Mock slow analysis
        async def slow_analysis(symbol):
            await asyncio.sleep(0.1)
            return {"symbol": symbol}

        orchestrator._process_symbol_analysis = slow_analysis

        # Start multiple analyses
        tasks = []
        for symbol in orchestrator.config.symbols:
            task = asyncio.create_task(orchestrator._process_symbol_analysis(symbol))
            tasks.append(task)

        # Should complete without error (semaphore limits concurrency)
        results = await asyncio.gather(*tasks)
        assert len(results) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
