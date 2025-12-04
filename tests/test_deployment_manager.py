"""
Tests for Deployment Manager
Validates blue/green deployment, canary releases, and rollback functionality.
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from libs.trading_models.deployment_manager import (
    DeploymentConfig,
    DeploymentManager,
    DeploymentMetrics,
    DeploymentState,
)
from libs.trading_models.e2e_integration import E2EIntegrationSystem
from libs.trading_models.monitoring import MonitoringSystem


class TestDeploymentManager:
    """Test deployment manager functionality."""

    @pytest.fixture
    def mock_e2e_system(self):
        """Create mock E2E system."""
        system = Mock(spec=E2EIntegrationSystem)
        system._trigger_safe_mode = Mock()
        return system

    @pytest.fixture
    def mock_monitoring(self):
        """Create mock monitoring system."""
        monitoring = Mock(spec=MonitoringSystem)
        monitoring.record_metric = Mock()
        monitoring.send_alert = Mock()
        return monitoring

    @pytest.fixture
    def deployment_manager(self, mock_e2e_system, mock_monitoring):
        """Create deployment manager."""
        with patch('libs.trading_models.deployment_manager.FeatureFlags') as mock_ff:
            mock_feature_flags = Mock()
            mock_ff.return_value = mock_feature_flags

            manager = DeploymentManager(mock_e2e_system, mock_monitoring)
            manager.feature_flags = mock_feature_flags
            return manager

    @pytest.fixture
    def test_deployment_config(self):
        """Create test deployment configuration."""
        return DeploymentConfig(
            version="v1.2.0-test",
            environment="staging",
            canary_percentage=10.0,
            canary_duration_minutes=1,  # Short for testing
            max_error_rate=0.05,
            max_latency_ms=1000,
            rollback_threshold_errors=3,
            health_check_interval_seconds=5,
            feature_flags={
                "new_feature": True,
                "enhanced_analysis": True
            }
        )

    @pytest.mark.asyncio
    async def test_successful_deployment(self, deployment_manager, test_deployment_config):
        """Test successful deployment flow."""
        # Mock all health checks to pass
        deployment_manager._check_market_data_health = AsyncMock(return_value=True)
        deployment_manager._check_llm_health = AsyncMock(return_value=True)
        deployment_manager._check_risk_management_health = AsyncMock(return_value=True)
        deployment_manager._check_persistence_health = AsyncMock(return_value=True)
        deployment_manager._check_monitoring_health = AsyncMock(return_value=True)

        # Mock canary monitoring to succeed
        deployment_manager._collect_canary_metrics = AsyncMock()
        deployment_manager._check_canary_safety_thresholds = AsyncMock(return_value=False)
        deployment_manager._perform_health_check = AsyncMock(return_value=True)
        deployment_manager._get_recent_trading_results = AsyncMock(return_value=[
            {"success": True, "duration_ms": 500},
            {"success": True, "duration_ms": 600}
        ])

        # Run deployment
        success = await deployment_manager.deploy_version(test_deployment_config)

        # Verify success
        assert success
        assert deployment_manager.deployment_state == DeploymentState.IDLE
        assert deployment_manager.current_deployment is not None
        assert deployment_manager.current_deployment.version == "v1.2.0-test"
        assert not deployment_manager.current_deployment.rollback_triggered

        # Verify feature flags were set
        deployment_manager.feature_flags.set_flag.assert_called()

        # Verify monitoring was called
        deployment_manager.monitoring.record_metric.assert_called()

    @pytest.mark.asyncio
    async def test_deployment_health_check_failure(self, deployment_manager, test_deployment_config):
        """Test deployment fails when health checks fail."""
        # Mock health checks to fail
        deployment_manager._check_market_data_health = AsyncMock(return_value=False)
        deployment_manager._check_llm_health = AsyncMock(return_value=True)
        deployment_manager._check_risk_management_health = AsyncMock(return_value=True)
        deployment_manager._check_persistence_health = AsyncMock(return_value=True)
        deployment_manager._check_monitoring_health = AsyncMock(return_value=True)

        # Mock rollback
        deployment_manager._rollback_deployment = AsyncMock()

        # Run deployment
        success = await deployment_manager.deploy_version(test_deployment_config)

        # Verify failure
        assert not success
        deployment_manager._rollback_deployment.assert_called()

    @pytest.mark.asyncio
    async def test_canary_failure_triggers_rollback(self, deployment_manager, test_deployment_config):
        """Test that canary failure triggers rollback."""
        # Mock health checks to pass initially
        deployment_manager._check_market_data_health = AsyncMock(return_value=True)
        deployment_manager._check_llm_health = AsyncMock(return_value=True)
        deployment_manager._check_risk_management_health = AsyncMock(return_value=True)
        deployment_manager._check_persistence_health = AsyncMock(return_value=True)
        deployment_manager._check_monitoring_health = AsyncMock(return_value=True)
        deployment_manager._perform_health_check = AsyncMock(return_value=True)

        # Mock canary to fail safety thresholds
        deployment_manager._collect_canary_metrics = AsyncMock()
        deployment_manager._check_canary_safety_thresholds = AsyncMock(return_value=True)  # Exceeds thresholds
        deployment_manager._rollback_deployment = AsyncMock()

        # Run deployment
        success = await deployment_manager.deploy_version(test_deployment_config)

        # Verify rollback was triggered
        assert not success
        deployment_manager._rollback_deployment.assert_called()

    @pytest.mark.asyncio
    async def test_canary_metrics_collection(self, deployment_manager):
        """Test canary metrics collection."""
        # Mock recent trading results
        deployment_manager._get_recent_trading_results = AsyncMock(return_value=[
            {"success": True, "duration_ms": 400},
            {"success": False, "duration_ms": 800},
            {"success": True, "duration_ms": 300}
        ])

        # Initialize canary metrics
        deployment_manager.canary_metrics = {'requests': 0, 'errors': 0, 'latencies': []}

        # Collect metrics
        await deployment_manager._collect_canary_metrics()

        # Verify metrics were updated
        assert deployment_manager.canary_metrics['requests'] == 3
        assert deployment_manager.canary_metrics['errors'] == 1
        assert len(deployment_manager.canary_metrics['latencies']) == 3
        assert 400 in deployment_manager.canary_metrics['latencies']
        assert 800 in deployment_manager.canary_metrics['latencies']
        assert 300 in deployment_manager.canary_metrics['latencies']

    @pytest.mark.asyncio
    async def test_canary_safety_threshold_checks(self, deployment_manager, test_deployment_config):
        """Test canary safety threshold checking."""
        # Test with high error rate
        deployment_manager.canary_metrics = {
            'requests': 100,
            'errors': 10,  # 10% error rate
            'latencies': [500, 600, 700]
        }

        # Should exceed error rate threshold (5%)
        exceeds = deployment_manager._check_canary_safety_thresholds(test_deployment_config)
        assert exceeds

        # Test with high latency
        deployment_manager.canary_metrics = {
            'requests': 100,
            'errors': 2,  # 2% error rate (OK)
            'latencies': [1200, 1300, 1400]  # High latencies
        }

        # Should exceed latency threshold (1000ms)
        exceeds = await deployment_manager._check_canary_safety_thresholds(test_deployment_config)
        assert exceeds

        # Test with good metrics
        deployment_manager.canary_metrics = {
            'requests': 100,
            'errors': 1,  # 1% error rate (OK)
            'latencies': [400, 500, 600]  # Good latencies
        }

        # Should not exceed thresholds
        exceeds = await deployment_manager._check_canary_safety_thresholds(test_deployment_config)
        assert not exceeds

    @pytest.mark.asyncio
    async def test_canary_safety_threshold_no_data(self, deployment_manager, test_deployment_config):
        """Test canary safety thresholds with no data."""
        # Test with no requests
        deployment_manager.canary_metrics = {
            'requests': 0,
            'errors': 0,
            'latencies': []
        }

        # Should not exceed thresholds (no data to evaluate)
        exceeds = await deployment_manager._check_canary_safety_thresholds(test_deployment_config)
        assert not exceeds

    @pytest.mark.asyncio
    async def test_rollback_deployment(self, deployment_manager):
        """Test deployment rollback functionality."""
        # Set up deployment state
        deployment_manager.deployment_state = DeploymentState.CANARY
        deployment_manager.active_environment = "green"
        deployment_manager.current_deployment = DeploymentMetrics(
            version="v1.2.0-test",
            start_time=datetime.now(),
            end_time=None,
            state=DeploymentState.CANARY,
            canary_traffic_percentage=10.0,
            success_rate=0.0,
            avg_latency_ms=0.0,
            error_count=0,
            rollback_triggered=False,
            rollback_reason=None,
            health_checks_passed=0,
            health_checks_failed=0
        )

        # Perform rollback
        await deployment_manager._rollback_deployment("Test rollback")

        # Verify rollback state
        assert deployment_manager.deployment_state == DeploymentState.FAILED
        assert deployment_manager.active_environment == "blue"  # Switched back
        assert deployment_manager.current_deployment.rollback_triggered
        assert deployment_manager.current_deployment.rollback_reason == "Test rollback"

        # Verify feature flags were disabled
        deployment_manager.feature_flags.set_flag.assert_called()

        # Verify safe mode was triggered
        deployment_manager.e2e_system._trigger_safe_mode.assert_called()

        # Verify monitoring alert was sent
        deployment_manager.monitoring.send_alert.assert_called_with(
            "DEPLOYMENT_ROLLBACK",
            {
                "reason": "Test rollback",
                "version": "v1.2.0-test",
                "timestamp": deployment_manager.current_deployment.end_time.isoformat()
            }
        )

    @pytest.mark.asyncio
    async def test_emergency_rollback(self, deployment_manager):
        """Test emergency rollback functionality."""
        # Set up some state
        deployment_manager.deployment_state = DeploymentState.FULL_DEPLOYMENT
        deployment_manager._rollback_deployment = AsyncMock()

        # Perform emergency rollback
        success = await deployment_manager.emergency_rollback()

        # Verify success
        assert success

        # Verify rollback was called
        deployment_manager._rollback_deployment.assert_called_with("Emergency rollback triggered")

        # Verify safe mode was triggered
        deployment_manager.e2e_system._trigger_safe_mode.assert_called_with("Emergency rollback")

        # Verify risky features were disabled
        deployment_manager.feature_flags.disable.assert_called()

    @pytest.mark.asyncio
    async def test_health_check_components(self, deployment_manager):
        """Test individual component health checks."""
        # Mock E2E system components
        deployment_manager.e2e_system.run_complete_trading_cycle = AsyncMock()
        deployment_manager.e2e_system.llm_router = Mock()
        deployment_manager.e2e_system.llm_router.analyze_market = AsyncMock(return_value={"test": True})
        deployment_manager.e2e_system.risk_manager = Mock()
        deployment_manager.e2e_system.persistence = Mock()
        deployment_manager.e2e_system.persistence.health_check = AsyncMock()

        # Test market data health check
        mock_result = Mock()
        mock_result.success = True
        deployment_manager.e2e_system.run_complete_trading_cycle.return_value = mock_result

        health = await deployment_manager._check_market_data_health()
        assert health

        # Test LLM health check
        health = await deployment_manager._check_llm_health()
        assert health

        # Test risk management health check
        health = await deployment_manager._check_risk_management_health()
        assert health

        # Test persistence health check
        health = await deployment_manager._check_persistence_health()
        assert health

        # Test monitoring health check
        health = await deployment_manager._check_monitoring_health()
        assert health

    @pytest.mark.asyncio
    async def test_health_check_failures(self, deployment_manager):
        """Test health check failure scenarios."""
        # Test market data health check failure
        deployment_manager.e2e_system.run_complete_trading_cycle = AsyncMock(side_effect=Exception("Connection failed"))
        health = await deployment_manager._check_market_data_health()
        assert not health

        # Test LLM health check failure
        deployment_manager.e2e_system.llm_router = Mock()
        deployment_manager.e2e_system.llm_router.analyze_market = AsyncMock(side_effect=Exception("LLM unavailable"))
        health = await deployment_manager._check_llm_health()
        assert not health

        # Test persistence health check failure
        deployment_manager.e2e_system.persistence = Mock()
        deployment_manager.e2e_system.persistence.health_check = AsyncMock(side_effect=Exception("DB connection failed"))
        health = await deployment_manager._check_persistence_health()
        assert not health

    def test_deployment_status_reporting(self, deployment_manager):
        """Test deployment status reporting."""
        # Set up deployment state
        deployment_manager.deployment_state = DeploymentState.CANARY
        deployment_manager.active_environment = "green"
        deployment_manager.current_deployment = DeploymentMetrics(
            version="v1.2.0-test",
            start_time=datetime.now(),
            end_time=None,
            state=DeploymentState.CANARY,
            canary_traffic_percentage=15.0,
            success_rate=0.95,
            avg_latency_ms=450.0,
            error_count=2,
            rollback_triggered=False,
            rollback_reason=None,
            health_checks_passed=5,
            health_checks_failed=1
        )

        # Add some deployment history
        old_deployment = DeploymentMetrics(
            version="v1.1.0",
            start_time=datetime.now(),
            end_time=datetime.now(),
            state=DeploymentState.IDLE,
            canary_traffic_percentage=0.0,
            success_rate=0.98,
            avg_latency_ms=400.0,
            error_count=1,
            rollback_triggered=False,
            rollback_reason=None,
            health_checks_passed=10,
            health_checks_failed=0
        )
        deployment_manager.deployment_history = [old_deployment]

        # Mock feature flags
        deployment_manager.feature_flags.get_all_flags = Mock(return_value={
            "canary_deployment": True,
            "new_feature": True
        })

        # Get status
        status = deployment_manager.get_deployment_status()

        # Verify status structure
        assert status['state'] == 'canary'
        assert status['active_environment'] == 'green'
        assert status['current_deployment'] is not None
        assert status['deployment_history'] is not None
        assert status['feature_flags'] is not None

        # Verify current deployment data
        current = status['current_deployment']
        assert current['version'] == 'v1.2.0-test'
        assert current['canary_traffic_percentage'] == 15.0
        assert current['success_rate'] == 0.95
        assert current['error_count'] == 2

        # Verify history is included
        assert len(status['deployment_history']) == 1
        assert status['deployment_history'][0]['version'] == 'v1.1.0'

    def test_rollback_time_limit_check(self, deployment_manager):
        """Test rollback time limit checking."""
        # Test with sufficient time limit
        can_rollback = deployment_manager.can_rollback_within_time_limit(120)  # 2 minutes
        assert can_rollback

        # Test with insufficient time limit
        can_rollback = deployment_manager.can_rollback_within_time_limit(30)   # 30 seconds
        assert not can_rollback

        # Test with exact time limit
        can_rollback = deployment_manager.can_rollback_within_time_limit(60)   # 1 minute
        assert can_rollback

    @pytest.mark.asyncio
    async def test_deployment_state_transitions(self, deployment_manager, test_deployment_config):
        """Test proper deployment state transitions."""
        # Initial state
        assert deployment_manager.deployment_state == DeploymentState.IDLE

        # Mock successful preparation
        deployment_manager._prepare_environment = AsyncMock(return_value=True)
        deployment_manager._start_canary_release = AsyncMock(return_value=True)
        deployment_manager._monitor_canary_release = AsyncMock(return_value=True)
        deployment_manager._complete_full_deployment = AsyncMock(return_value=True)
        # Set the state to IDLE in the finalize mock
        deployment_manager._finalize_deployment = AsyncMock(side_effect=lambda config: setattr(deployment_manager, 'deployment_state', DeploymentState.IDLE))

        # Start deployment
        success = await deployment_manager.deploy_version(test_deployment_config)

        # Verify final state
        assert success
        assert deployment_manager.deployment_state == DeploymentState.IDLE

        # Verify state transitions occurred
        deployment_manager._prepare_environment.assert_called_once()
        deployment_manager._start_canary_release.assert_called_once()
        deployment_manager._monitor_canary_release.assert_called_once()
        deployment_manager._complete_full_deployment.assert_called_once()
        deployment_manager._finalize_deployment.assert_called_once()

    @pytest.mark.asyncio
    async def test_concurrent_deployment_prevention(self, deployment_manager, test_deployment_config):
        """Test that concurrent deployments are prevented."""
        # Set deployment state to non-idle
        deployment_manager.deployment_state = DeploymentState.DEPLOYING

        # Try to start another deployment
        success = await deployment_manager.deploy_version(test_deployment_config)

        # Should fail
        assert not success


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
