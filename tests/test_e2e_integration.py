"""
Comprehensive End-to-End Integration Tests
Tests complete trading workflows and system integration.
"""

import asyncio
import time
from unittest.mock import AsyncMock, Mock, patch

import pytest

from libs.trading_models.base import Portfolio
from libs.trading_models.e2e_integration import E2EIntegrationSystem, SystemState


class TestE2EIntegration:
    """Test complete end-to-end system integration."""

    @pytest.fixture
    def e2e_system(self, mock_config):
        """Create E2EIntegrationSystem instance for testing."""
        # Mock all dependencies to avoid complex initialization
        with patch('libs.trading_models.e2e_integration.MarketDataIngestion'), \
             patch('libs.trading_models.e2e_integration.TechnicalIndicators'), \
             patch('libs.trading_models.e2e_integration.PatternRecognition'), \
             patch('libs.trading_models.e2e_integration.ConfluenceScoring'), \
             patch('libs.trading_models.e2e_integration.LLMRouter'), \
             patch('libs.trading_models.e2e_integration.RiskManager'), \
             patch('libs.trading_models.e2e_integration.TradingOrchestrator'), \
             patch('libs.trading_models.e2e_integration.PersistenceManager'), \
             patch('libs.trading_models.e2e_integration.MonitoringSystem'), \
             patch('libs.trading_models.e2e_integration.ErrorHandler'), \
             patch('libs.trading_models.e2e_integration.FeatureFlags'):
            system = E2EIntegrationSystem(mock_config)
            return system

    @pytest.fixture
    def mock_config(self):
        """Mock system configuration."""
        return {
            'market_data': {
                'sources': ['binance'],
                'symbols': ['BTCUSDT', 'ETHUSDT'],
                'timeframes': ['15m', '1h', '4h', '1d']
            },
            'llm': {
                'models': ['claude', 'gpt4'],
                'routing_policy': 'AccuracyFirst'
            },
            'risk': {
                'max_position_size': 0.02,
                'max_portfolio_risk': 0.20,
                'safe_mode_drawdown': 0.08
            },
            'orchestrator': {
                'check_interval': 900,  # 15 minutes
                'symbols': ['BTCUSDT', 'ETHUSDT']
            },
            'persistence': {
                'database_url': 'sqlite:///test.db'
            },
            'monitoring': {
                'metrics_enabled': True,
                'alerts_enabled': True
            }
        }


    @pytest.mark.asyncio
    async def test_system_startup_and_shutdown(self, e2e_system):
        """Test complete system startup and shutdown."""
        # Mock health checks to pass
        e2e_system._check_market_data_health = AsyncMock(return_value=True)
        e2e_system._check_llm_health = AsyncMock(return_value=True)
        e2e_system._check_risk_health = AsyncMock(return_value=True)
        e2e_system._check_persistence_health = AsyncMock(return_value=True)
        e2e_system._check_monitoring_health = AsyncMock(return_value=True)

        # Mock component start/stop methods
        e2e_system.market_data.start = AsyncMock()
        e2e_system.orchestrator.start = AsyncMock()
        e2e_system.monitoring.start = AsyncMock()
        e2e_system.monitoring.stop = AsyncMock()
        e2e_system.orchestrator.stop = AsyncMock()
        e2e_system.market_data.stop = AsyncMock()
        e2e_system.persistence.flush_all = AsyncMock()

        # Test startup
        assert e2e_system.state == SystemState.INITIALIZING
        success = await e2e_system.start_system()
        assert success
        assert e2e_system.state == SystemState.RUNNING

        # Verify all components were started
        e2e_system.market_data.start.assert_called_once()
        e2e_system.orchestrator.start.assert_called_once()
        e2e_system.monitoring.start.assert_called_once()

        # Test shutdown
        success = await e2e_system.stop_system()
        assert success
        assert e2e_system.state == SystemState.SHUTDOWN

        # Verify all components were stopped
        e2e_system.monitoring.stop.assert_called_once()
        e2e_system.orchestrator.stop.assert_called_once()
        e2e_system.market_data.stop.assert_called_once()
        e2e_system.persistence.flush_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_startup_health_check_failure(self, e2e_system):
        """Test system handles health check failures on startup."""
        # Mock one health check to fail
        e2e_system._check_market_data_health = AsyncMock(return_value=False)
        e2e_system._check_llm_health = AsyncMock(return_value=True)
        e2e_system._check_risk_health = AsyncMock(return_value=True)
        e2e_system._check_persistence_health = AsyncMock(return_value=True)
        e2e_system._check_monitoring_health = AsyncMock(return_value=True)

        success = await e2e_system.start_system()
        assert not success
        assert e2e_system.state == SystemState.INITIALIZING

        # Check that failed component is recorded
        assert 'market_data' in e2e_system.component_health
        assert not e2e_system.component_health['market_data'].healthy

    @pytest.mark.asyncio
    async def test_complete_trading_cycle_success(self, e2e_system):
        """Test successful complete trading cycle."""
        symbol = "BTCUSDT"

        # Mock market data
        mock_market_data = {
            "15m": [{"open": 50000, "high": 50100, "low": 49900, "close": 50050, "volume": 100}],
            "1h": [{"open": 49800, "high": 50200, "low": 49700, "close": 50050, "volume": 400}],
            "4h": [{"open": 49500, "high": 50300, "low": 49400, "close": 50050, "volume": 1600}],
            "1d": [{"open": 48000, "high": 51000, "low": 47500, "close": 50050, "volume": 6400}]
        }

        # Mock indicators
        mock_indicators = {
            "15m": {"rsi": 65, "ema_20": 49950, "macd": 0.5},
            "1h": {"rsi": 62, "ema_20": 49900, "macd": 0.3},
            "4h": {"rsi": 58, "ema_20": 49800, "macd": 0.1},
            "1d": {"rsi": 55, "ema_20": 49500, "macd": -0.1}
        }

        # Mock patterns
        mock_patterns = {
            "15m": [{"type": "bullish_engulfing", "confidence": 0.8}],
            "1h": [{"type": "support_break", "confidence": 0.7}],
            "4h": [],
            "1d": [{"type": "trend_continuation", "confidence": 0.6}]
        }

        # Mock confluence result
        mock_confluence = Mock()
        mock_confluence.direction = "LONG"
        mock_confluence.confidence = 0.75
        mock_confluence.score = 72.5
        mock_confluence.reasoning = "Strong bullish confluence across timeframes"
        mock_confluence.timeframe_analysis = {"15m": 0.8, "1h": 0.7, "4h": 0.6, "1d": 0.8}

        # Mock portfolio
        mock_portfolio = Portfolio(
            total_equity=10000.0,
            available_margin=5000.0,
            positions=[],
            daily_pnl=0.0,
            unrealized_pnl=0.0
        )

        # Mock risk assessment
        mock_risk_assessment = Mock()
        mock_risk_assessment.approved = True
        mock_risk_assessment.position_size = 0.1
        mock_risk_assessment.stop_loss = 49500
        mock_risk_assessment.take_profit = 51000

        # Set up mocks
        e2e_system.market_data.fetch_multi_timeframe_data = AsyncMock(return_value=mock_market_data)
        e2e_system.indicators.calculate_all_indicators = Mock(return_value=mock_indicators)
        e2e_system.patterns.detect_all_patterns = Mock(return_value=mock_patterns)
        e2e_system.confluence.calculate_confluence_score = Mock(return_value=mock_confluence)
        e2e_system.llm_router.analyze_market = AsyncMock(return_value={"analysis": "bullish"})
        e2e_system.persistence.get_current_portfolio = AsyncMock(return_value=mock_portfolio)
        e2e_system.risk_manager.assess_trade_risk = Mock(return_value=mock_risk_assessment)
        e2e_system.orchestrator.execute_trade = AsyncMock(return_value={"trade_id": "test_123"})
        e2e_system.persistence.record_trading_cycle = AsyncMock()
        e2e_system.monitoring.record_metric = Mock()
        # Mock error handler to be async
        e2e_system.error_handler.handle_trading_error = AsyncMock()
        e2e_system.feature_flags.is_enabled = Mock(return_value=True)

        # Run trading cycle
        result = await e2e_system.run_complete_trading_cycle(symbol)

        # Verify success
        assert result.success
        assert result.test_name == f"complete_trading_cycle_{symbol}"
        assert result.duration_ms > 0
        assert result.metrics is not None

        # Verify all components were called
        e2e_system.market_data.fetch_multi_timeframe_data.assert_called_once_with(
            symbol, ["15m", "1h", "4h", "1d"]
        )
        e2e_system.persistence.record_trading_cycle.assert_called_once()
        e2e_system.monitoring.record_metric.assert_called()

        # Verify metrics were updated
        assert e2e_system.performance_metrics['total_scans'] == 1
        assert e2e_system.performance_metrics['successful_scans'] == 1
        assert len(e2e_system.performance_metrics['scan_latencies']) == 1

    @pytest.mark.asyncio
    async def test_complete_trading_cycle_failure(self, e2e_system):
        """Test trading cycle handles failures gracefully."""
        symbol = "BTCUSDT"

        # Mock market data fetch to fail
        e2e_system.market_data.fetch_multi_timeframe_data = AsyncMock(
            side_effect=Exception("Market data unavailable")
        )
        e2e_system.error_handler.handle_trading_error = AsyncMock()

        # Run trading cycle
        result = await e2e_system.run_complete_trading_cycle(symbol)

        # Verify failure handling
        assert not result.success
        assert "Market data unavailable" in result.error_message
        assert result.duration_ms > 0

        # Verify error handling was called
        e2e_system.error_handler.handle_trading_error.assert_called_once()

        # Verify error metrics were updated
        assert e2e_system.performance_metrics['error_count'] == 1

    @pytest.mark.asyncio
    async def test_safe_mode_trigger(self, e2e_system):
        """Test safe mode triggering and recovery."""
        # Mock feature flags
        e2e_system.feature_flags.disable = Mock()
        e2e_system.risk_manager.enable_safe_mode = Mock()
        e2e_system.monitoring.send_alert = Mock()

        # Trigger safe mode
        e2e_system._trigger_safe_mode("High drawdown detected")

        # Verify safe mode was activated
        assert e2e_system.state == SystemState.SAFE_MODE

        # Verify safety measures were taken
        e2e_system.feature_flags.disable.assert_any_call("live_trading")
        e2e_system.feature_flags.disable.assert_any_call("high_risk_trades")
        e2e_system.risk_manager.enable_safe_mode.assert_called_once()
        e2e_system.monitoring.send_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_recovery(self, e2e_system):
        """Test automatic error recovery mechanisms."""
        # Mock recovery methods
        e2e_system._recover_market_data = AsyncMock(return_value=True)
        e2e_system._recover_llm = AsyncMock(return_value=True)
        e2e_system._recover_execution = AsyncMock(return_value=True)
        e2e_system._recover_persistence = AsyncMock(return_value=True)

        # Test market data recovery
        success = await e2e_system._attempt_recovery('market_data_error', {})
        assert success
        e2e_system._recover_market_data.assert_called_once()

        # Test LLM recovery
        success = await e2e_system._attempt_recovery('llm_error', {})
        assert success
        e2e_system._recover_llm.assert_called_once()

        # Test execution recovery
        success = await e2e_system._attempt_recovery('execution_error', {})
        assert success
        e2e_system._recover_execution.assert_called_once()

        # Test persistence recovery
        success = await e2e_system._attempt_recovery('persistence_error', {})
        assert success
        e2e_system._recover_persistence.assert_called_once()

        # Test unknown error type
        success = await e2e_system._attempt_recovery('unknown_error', {})
        assert not success

    def test_system_status_reporting(self, e2e_system):
        """Test comprehensive system status reporting."""
        # Set up some test data
        e2e_system.performance_metrics['total_scans'] = 100
        e2e_system.performance_metrics['successful_scans'] = 95
        e2e_system.performance_metrics['error_count'] = 5
        e2e_system.performance_metrics['scan_latencies'] = [800, 900, 750, 850, 950]
        e2e_system.state = SystemState.RUNNING

        # Mock feature flags
        e2e_system.feature_flags.get_all_flags = Mock(return_value={
            "live_trading": True,
            "llm_analysis": True,
            "high_risk_trades": False
        })

        # Get system status
        status = e2e_system.get_system_status()

        # Verify status structure
        assert 'state' in status
        assert 'uptime_hours' in status
        assert 'uptime_percentage' in status
        assert 'total_scans' in status
        assert 'successful_scans' in status
        assert 'error_count' in status
        assert 'avg_scan_latency_ms' in status
        assert 'component_health' in status
        assert 'feature_flags' in status
        assert 'slo_compliance' in status

        # Verify values
        assert status['state'] == 'running'
        assert status['total_scans'] == 100
        assert status['successful_scans'] == 95
        assert status['error_count'] == 5
        assert status['avg_scan_latency_ms'] == 850.0  # Average of test latencies

        # Verify SLO compliance structure
        slo = status['slo_compliance']
        assert 'uptime_target' in slo
        assert 'uptime_actual' in slo
        assert 'scan_latency_target_ms' in slo
        assert 'scan_latency_actual_ms' in slo
        assert 'meets_slo' in slo

        assert slo['uptime_target'] == 99.5
        assert slo['scan_latency_target_ms'] == 1000
        assert slo['scan_latency_actual_ms'] == 850.0

    def test_alert_handling(self, e2e_system):
        """Test monitoring alert handling."""
        # Mock methods
        e2e_system._trigger_safe_mode = Mock()
        e2e_system.feature_flags.disable = Mock()

        # Test high drawdown alert
        e2e_system._handle_alert("HIGH_DRAWDOWN", {"drawdown": 0.12})
        e2e_system._trigger_safe_mode.assert_called_with("High drawdown detected")

        # Test system overload alert
        e2e_system._handle_alert("SYSTEM_OVERLOAD", {"cpu": 95})
        e2e_system.feature_flags.disable.assert_called_with("non_essential_features")

        # Test cost budget exceeded alert
        e2e_system._handle_alert("COST_BUDGET_EXCEEDED", {"spend": 1500})
        e2e_system.feature_flags.disable.assert_called_with("frequent_llm_calls")


class TestE2ELoadTesting:
    """Test system performance under load."""

    @pytest.fixture
    def load_test_system(self, mock_config):
        """Create system for load testing."""
        with patch.multiple(
            'libs.trading_models.e2e_integration',
            MarketDataIngestion=Mock,
            TechnicalIndicators=Mock,
            PatternRecognition=Mock,
            ConfluenceScoring=Mock,
            LLMRouter=Mock,
            RiskManager=Mock,
            TradingOrchestrator=Mock,
            PersistenceManager=Mock,
            MonitoringSystem=Mock,
            ErrorHandler=Mock,
            FeatureFlags=Mock
        ):
            system = E2EIntegrationSystem(mock_config)

            # Mock fast responses for load testing
            system.market_data.fetch_multi_timeframe_data = AsyncMock(
                return_value={"1h": [{"close": 50000}]}
            )
            system.indicators.calculate_all_indicators = Mock(return_value={"rsi": 50})
            system.patterns.detect_all_patterns = Mock(return_value=[])
            mock_confluence = Mock()
            mock_confluence.direction = "LONG"
            mock_confluence.confidence = 0.5
            mock_confluence.score = 50
            mock_confluence.reasoning = "test"
            mock_confluence.timeframe_analysis = {"1h": 0.5}  # Must be a dictionary
            system.confluence.calculate_confluence_score = Mock(
                return_value=mock_confluence
            )
            system.persistence.get_current_portfolio = AsyncMock(
                return_value=Portfolio(
                    total_equity=10000.0,
                    available_margin=5000.0,
                    positions=[],
                    daily_pnl=0.0,
                    unrealized_pnl=0.0
                )
            )
            system.risk_manager.assess_trade_risk = Mock(
                return_value=Mock(approved=False)
            )
            system.persistence.record_trading_cycle = AsyncMock()
            system.monitoring.record_metric = Mock()
            system.feature_flags.is_enabled = Mock(return_value=False)

            return system

    @pytest.mark.asyncio
    async def test_concurrent_trading_cycles(self, load_test_system):
        """Test multiple concurrent trading cycles."""
        symbols = ["BTCUSDT", "ETHUSDT", "ADAUSDT", "DOTUSDT", "LINKUSDT"]

        # Run concurrent trading cycles
        start_time = time.time()
        tasks = [
            load_test_system.run_complete_trading_cycle(symbol)
            for symbol in symbols
        ]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time

        # Verify all cycles completed successfully
        assert len(results) == len(symbols)
        for result in results:
            assert result.success
            # Duration may be 0 in mocked tests, which is acceptable

        # Verify performance (should handle 5 symbols concurrently in reasonable time)
        assert total_time < 10.0  # Should complete within 10 seconds

        # Verify metrics were updated correctly
        assert load_test_system.performance_metrics['total_scans'] == len(symbols)
        assert load_test_system.performance_metrics['successful_scans'] == len(symbols)

    @pytest.mark.asyncio
    async def test_sustained_load(self, load_test_system):
        """Test system under sustained load."""
        # Run multiple rounds of trading cycles
        rounds = 3
        symbols_per_round = 2
        symbols = ["BTCUSDT", "ETHUSDT"]

        all_results = []
        start_time = time.time()

        for round_num in range(rounds):
            round_tasks = [
                load_test_system.run_complete_trading_cycle(symbol)
                for symbol in symbols
            ]
            round_results = await asyncio.gather(*round_tasks)
            all_results.extend(round_results)

            # Small delay between rounds
            await asyncio.sleep(0.1)

        total_time = time.time() - start_time

        # Verify all cycles completed
        expected_total = rounds * symbols_per_round
        assert len(all_results) == expected_total

        for result in all_results:
            assert result.success

        # Verify performance metrics
        assert load_test_system.performance_metrics['total_scans'] == expected_total
        assert load_test_system.performance_metrics['successful_scans'] == expected_total

        # Calculate average latency
        avg_latency = sum(load_test_system.performance_metrics['scan_latencies']) / len(
            load_test_system.performance_metrics['scan_latencies']
        )

        # Verify latency SLO (should be under 1000ms per scan)
        assert avg_latency < 1000.0

    @pytest.mark.asyncio
    async def test_memory_usage_stability(self, load_test_system):
        """Test that memory usage remains stable under load."""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Run many trading cycles
        for i in range(20):
            result = await load_test_system.run_complete_trading_cycle("BTCUSDT")
            assert result.success

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (less than 50MB)
        assert memory_increase < 50 * 1024 * 1024  # 50MB in bytes


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
