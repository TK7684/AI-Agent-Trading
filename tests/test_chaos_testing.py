"""
Tests for the chaos testing framework and failure simulation.
"""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from libs.trading_models.chaos_testing import (
    ChaosConfig,
    ChaosExperiment,
    ChaosResult,
    ChaosScope,
    ChaosTestSuite,
    ChaosType,
    DataCorruptionExperiment,
    LatencyInjectionExperiment,
    NetworkFailureExperiment,
    RateLimitSpikeExperiment,
    ResourceExhaustionExperiment,
    ServiceFailureExperiment,
    chaos_context,
    run_chaos_monkey,
)


class TestChaosConfig:
    """Test ChaosConfig functionality."""

    def test_chaos_config_creation(self):
        """Test creating a chaos configuration."""
        config = ChaosConfig(
            name="test_experiment",
            chaos_type=ChaosType.NETWORK_FAILURE,
            scope=ChaosScope.SERVICE,
            target="api_service",
            duration=60.0,
            intensity=0.8
        )

        assert config.name == "test_experiment"
        assert config.chaos_type == ChaosType.NETWORK_FAILURE
        assert config.scope == ChaosScope.SERVICE
        assert config.target == "api_service"
        assert config.duration == 60.0
        assert config.intensity == 0.8
        assert config.probability == 1.0  # Default

    def test_chaos_config_with_parameters(self):
        """Test chaos configuration with custom parameters."""
        config = ChaosConfig(
            name="test_experiment",
            chaos_type=ChaosType.SERVICE_FAILURE,
            scope=ChaosScope.COMPONENT,
            target="database",
            parameters={"failure_type": "crash", "recovery_time": 30}
        )

        assert config.parameters["failure_type"] == "crash"
        assert config.parameters["recovery_time"] == 30


class TestChaosResult:
    """Test ChaosResult functionality."""

    def test_chaos_result_creation(self):
        """Test creating a chaos result."""
        config = ChaosConfig(
            name="test_experiment",
            chaos_type=ChaosType.NETWORK_FAILURE,
            scope=ChaosScope.SERVICE,
            target="api_service"
        )

        result = ChaosResult(
            experiment_id="exp_123",
            config=config,
            start_time=datetime.now(UTC)
        )

        assert result.experiment_id == "exp_123"
        assert result.config == config
        assert result.success is False  # Default
        assert result.error_count == 0
        assert len(result.logs) == 0


class MockChaosExperiment(ChaosExperiment):
    """Mock chaos experiment for testing."""

    def __init__(self, config: ChaosConfig, should_fail: bool = False):
        super().__init__(config)
        self.should_fail = should_fail
        self.chaos_injected = False
        self.chaos_restored = False

    async def inject_chaos(self):
        """Mock chaos injection."""
        if self.should_fail:
            raise Exception("Chaos injection failed")
        self.chaos_injected = True
        self.metrics["chaos_active"] = True

    async def restore_normal(self):
        """Mock chaos restoration."""
        self.chaos_restored = True
        self.metrics["chaos_active"] = False


class TestChaosExperiment:
    """Test ChaosExperiment base functionality."""

    def test_chaos_experiment_creation(self):
        """Test creating a chaos experiment."""
        config = ChaosConfig(
            name="test_experiment",
            chaos_type=ChaosType.NETWORK_FAILURE,
            scope=ChaosScope.SERVICE,
            target="api_service"
        )

        experiment = MockChaosExperiment(config)

        assert experiment.config == config
        assert experiment.active is False
        assert experiment.start_time is None

    def test_check_preconditions_all_true(self):
        """Test precondition checking when all are true."""
        config = ChaosConfig(
            name="test_experiment",
            chaos_type=ChaosType.NETWORK_FAILURE,
            scope=ChaosScope.SERVICE,
            target="api_service",
            preconditions=[lambda: True, lambda: True]
        )

        experiment = MockChaosExperiment(config)
        assert experiment.check_preconditions() is True

    def test_check_preconditions_one_false(self):
        """Test precondition checking when one is false."""
        config = ChaosConfig(
            name="test_experiment",
            chaos_type=ChaosType.NETWORK_FAILURE,
            scope=ChaosScope.SERVICE,
            target="api_service",
            preconditions=[lambda: True, lambda: False]
        )

        experiment = MockChaosExperiment(config)
        assert experiment.check_preconditions() is False

    def test_check_success_criteria_all_true(self):
        """Test success criteria checking when all are true."""
        config = ChaosConfig(
            name="test_experiment",
            chaos_type=ChaosType.NETWORK_FAILURE,
            scope=ChaosScope.SERVICE,
            target="api_service",
            success_criteria=[lambda: True, lambda: True]
        )

        experiment = MockChaosExperiment(config)
        assert experiment.check_success_criteria() is True

    def test_check_success_criteria_one_false(self):
        """Test success criteria checking when one is false."""
        config = ChaosConfig(
            name="test_experiment",
            chaos_type=ChaosType.NETWORK_FAILURE,
            scope=ChaosScope.SERVICE,
            target="api_service",
            success_criteria=[lambda: True, lambda: False]
        )

        experiment = MockChaosExperiment(config)
        assert experiment.check_success_criteria() is False

    @pytest.mark.asyncio
    async def test_run_experiment_success(self):
        """Test running a successful experiment."""
        config = ChaosConfig(
            name="test_experiment",
            chaos_type=ChaosType.NETWORK_FAILURE,
            scope=ChaosScope.SERVICE,
            target="api_service",
            duration=0.1,  # Short duration for testing
            success_criteria=[lambda: True]
        )

        experiment = MockChaosExperiment(config)
        result = await experiment.run()

        assert result.success is True
        assert experiment.chaos_injected is True
        assert experiment.chaos_restored is True
        assert result.recovery_time is not None
        assert result.end_time is not None
        assert "Chaos injected" in " ".join(result.logs)
        assert "Chaos removed" in " ".join(result.logs)

    @pytest.mark.asyncio
    async def test_run_experiment_preconditions_not_met(self):
        """Test running experiment when preconditions are not met."""
        config = ChaosConfig(
            name="test_experiment",
            chaos_type=ChaosType.NETWORK_FAILURE,
            scope=ChaosScope.SERVICE,
            target="api_service",
            preconditions=[lambda: False]
        )

        experiment = MockChaosExperiment(config)
        result = await experiment.run()

        assert result.success is False
        assert experiment.chaos_injected is False
        assert "Preconditions not met" in " ".join(result.logs)

    @pytest.mark.asyncio
    async def test_run_experiment_low_probability(self):
        """Test running experiment with low probability."""
        config = ChaosConfig(
            name="test_experiment",
            chaos_type=ChaosType.NETWORK_FAILURE,
            scope=ChaosScope.SERVICE,
            target="api_service",
            probability=0.0  # Never trigger
        )

        experiment = MockChaosExperiment(config)
        result = await experiment.run()

        assert result.success is True
        assert experiment.chaos_injected is False
        assert "not triggered due to probability" in " ".join(result.logs)

    @pytest.mark.asyncio
    async def test_run_experiment_injection_failure(self):
        """Test running experiment when chaos injection fails."""
        config = ChaosConfig(
            name="test_experiment",
            chaos_type=ChaosType.NETWORK_FAILURE,
            scope=ChaosScope.SERVICE,
            target="api_service",
            duration=0.1
        )

        experiment = MockChaosExperiment(config, should_fail=True)
        result = await experiment.run()

        assert result.success is False
        assert len(result.exceptions) > 0
        assert experiment.active is False  # Should be cleaned up

    @pytest.mark.asyncio
    async def test_run_experiment_recovery_timeout(self):
        """Test running experiment when recovery times out."""
        config = ChaosConfig(
            name="test_experiment",
            chaos_type=ChaosType.NETWORK_FAILURE,
            scope=ChaosScope.SERVICE,
            target="api_service",
            duration=0.1,
            success_criteria=[lambda: False]  # Never succeeds
        )

        experiment = MockChaosExperiment(config)

        # Just run the experiment normally - it will timeout due to success_criteria
        result = await experiment.run()

        assert result.success is False
        # The experiment should fail because success criteria never return True


class TestNetworkFailureExperiment:
    """Test NetworkFailureExperiment functionality."""

    @pytest.mark.asyncio
    async def test_network_failure_complete_outage(self):
        """Test network failure with complete outage."""
        config = ChaosConfig(
            name="network_outage",
            chaos_type=ChaosType.NETWORK_FAILURE,
            scope=ChaosScope.NETWORK,
            target="api_service",
            intensity=1.0,
            parameters={"failure_type": "complete_outage"}
        )

        experiment = NetworkFailureExperiment(config)
        await experiment.inject_chaos()

        assert experiment.metrics["network_available"] is False

        await experiment.restore_normal()
        assert experiment.metrics["network_available"] is True

    @pytest.mark.asyncio
    async def test_network_failure_high_latency(self):
        """Test network failure with high latency."""
        config = ChaosConfig(
            name="network_latency",
            chaos_type=ChaosType.NETWORK_FAILURE,
            scope=ChaosScope.NETWORK,
            target="api_service",
            intensity=0.8,
            parameters={"failure_type": "high_latency"}
        )

        experiment = NetworkFailureExperiment(config)
        await experiment.inject_chaos()

        assert experiment.metrics["network_latency_ms"] == 4000  # 0.8 * 5000

        await experiment.restore_normal()
        assert experiment.metrics["network_latency_ms"] == 50

    @pytest.mark.asyncio
    async def test_network_failure_packet_loss(self):
        """Test network failure with packet loss."""
        config = ChaosConfig(
            name="packet_loss",
            chaos_type=ChaosType.NETWORK_FAILURE,
            scope=ChaosScope.NETWORK,
            target="api_service",
            intensity=0.6,
            parameters={"failure_type": "packet_loss"}
        )

        experiment = NetworkFailureExperiment(config)
        await experiment.inject_chaos()

        assert experiment.metrics["packet_loss_rate"] == 0.3  # 0.6 * 0.5

        await experiment.restore_normal()
        assert experiment.metrics["packet_loss_rate"] == 0.0


class TestServiceFailureExperiment:
    """Test ServiceFailureExperiment functionality."""

    @pytest.mark.asyncio
    async def test_service_failure_crash(self):
        """Test service failure with crash."""
        config = ChaosConfig(
            name="service_crash",
            chaos_type=ChaosType.SERVICE_FAILURE,
            scope=ChaosScope.SERVICE,
            target="api_service",
            intensity=1.0,
            parameters={"failure_type": "crash"}
        )

        experiment = ServiceFailureExperiment(config)
        await experiment.inject_chaos()

        assert experiment.metrics["service_available"] is False

        await experiment.restore_normal()
        assert experiment.metrics["service_available"] is True

    @pytest.mark.asyncio
    async def test_service_failure_memory_leak(self):
        """Test service failure with memory leak."""
        config = ChaosConfig(
            name="memory_leak",
            chaos_type=ChaosType.SERVICE_FAILURE,
            scope=ChaosScope.SERVICE,
            target="api_service",
            intensity=0.7,
            parameters={"failure_type": "memory_leak"}
        )

        experiment = ServiceFailureExperiment(config)
        await experiment.inject_chaos()

        assert experiment.metrics["memory_usage_mb"] == 700  # 0.7 * 1000

        await experiment.restore_normal()
        assert experiment.metrics["memory_usage_mb"] == 100


class TestResourceExhaustionExperiment:
    """Test ResourceExhaustionExperiment functionality."""

    @pytest.mark.asyncio
    async def test_resource_exhaustion_memory(self):
        """Test resource exhaustion with memory."""
        config = ChaosConfig(
            name="memory_exhaustion",
            chaos_type=ChaosType.RESOURCE_EXHAUSTION,
            scope=ChaosScope.SYSTEM,
            target="system",
            intensity=0.5,
            parameters={"resource_type": "memory"}
        )

        experiment = ResourceExhaustionExperiment(config)
        await experiment.inject_chaos()

        assert experiment.metrics["memory_usage_mb"] == 4000  # 0.5 * 8000

        await experiment.restore_normal()
        assert experiment.metrics["memory_usage_mb"] == 100

    @pytest.mark.asyncio
    async def test_resource_exhaustion_cpu(self):
        """Test resource exhaustion with CPU."""
        config = ChaosConfig(
            name="cpu_exhaustion",
            chaos_type=ChaosType.RESOURCE_EXHAUSTION,
            scope=ChaosScope.SYSTEM,
            target="system",
            intensity=0.9,
            parameters={"resource_type": "cpu"}
        )

        experiment = ResourceExhaustionExperiment(config)
        await experiment.inject_chaos()

        assert experiment.metrics["cpu_usage_percent"] == 90  # 0.9 * 100

        await experiment.restore_normal()
        assert experiment.metrics["cpu_usage_percent"] == 10


class TestLatencyInjectionExperiment:
    """Test LatencyInjectionExperiment functionality."""

    @pytest.mark.asyncio
    async def test_latency_injection(self):
        """Test latency injection."""
        config = ChaosConfig(
            name="latency_injection",
            chaos_type=ChaosType.LATENCY_INJECTION,
            scope=ChaosScope.SERVICE,
            target="api_calls",
            intensity=0.6
        )

        experiment = LatencyInjectionExperiment(config)
        await experiment.inject_chaos()

        assert experiment.metrics["injected_latency_ms"] == 3000  # 0.6 * 5000

        await experiment.restore_normal()
        assert experiment.metrics["injected_latency_ms"] == 0


class TestRateLimitSpikeExperiment:
    """Test RateLimitSpikeExperiment functionality."""

    @pytest.mark.asyncio
    async def test_rate_limit_spike(self):
        """Test rate limit spike."""
        config = ChaosConfig(
            name="rate_limit_spike",
            chaos_type=ChaosType.RATE_LIMIT_SPIKE,
            scope=ChaosScope.SERVICE,
            target="api_service",
            intensity=0.8
        )

        experiment = RateLimitSpikeExperiment(config)
        await experiment.inject_chaos()

        assert experiment.metrics["rate_limit_factor"] == 8  # 0.8 * 10
        assert experiment.metrics["requests_throttled"] is True

        await experiment.restore_normal()
        assert experiment.metrics["rate_limit_factor"] == 1
        assert experiment.metrics["requests_throttled"] is False


class TestDataCorruptionExperiment:
    """Test DataCorruptionExperiment functionality."""

    @pytest.mark.asyncio
    async def test_data_corruption(self):
        """Test data corruption."""
        config = ChaosConfig(
            name="data_corruption",
            chaos_type=ChaosType.DATA_CORRUPTION,
            scope=ChaosScope.COMPONENT,
            target="database",
            intensity=0.4
        )

        experiment = DataCorruptionExperiment(config)
        await experiment.inject_chaos()

        assert abs(experiment.metrics["data_corruption_rate"] - 0.04) < 0.001  # 0.4 * 0.1
        assert experiment.metrics["data_integrity"] == 0.96  # 1.0 - 0.04

        await experiment.restore_normal()
        assert experiment.metrics["data_corruption_rate"] == 0.0
        assert experiment.metrics["data_integrity"] == 1.0


class TestChaosTestSuite:
    """Test ChaosTestSuite functionality."""

    def test_chaos_test_suite_creation(self):
        """Test creating a chaos test suite."""
        suite = ChaosTestSuite()

        assert len(suite.experiments) == 0
        assert len(suite.results) == 0
        assert len(suite.running_experiments) == 0
        assert len(suite.experiment_factories) > 0

    def test_add_experiment(self):
        """Test adding an experiment to the suite."""
        suite = ChaosTestSuite()

        config = ChaosConfig(
            name="test_experiment",
            chaos_type=ChaosType.NETWORK_FAILURE,
            scope=ChaosScope.SERVICE,
            target="api_service"
        )

        experiment_id = suite.add_experiment(config)

        assert experiment_id in suite.experiments
        assert isinstance(suite.experiments[experiment_id], NetworkFailureExperiment)

    def test_add_experiment_unknown_type(self):
        """Test adding experiment with unknown chaos type."""
        suite = ChaosTestSuite()

        # Create a config with a type not in the factory
        config = ChaosConfig(
            name="test_experiment",
            chaos_type=ChaosType.PARTIAL_FAILURE,  # Not implemented
            scope=ChaosScope.SERVICE,
            target="api_service"
        )

        with pytest.raises(ValueError, match="Unknown chaos type"):
            suite.add_experiment(config)

    @pytest.mark.asyncio
    async def test_run_experiment(self):
        """Test running a single experiment."""
        suite = ChaosTestSuite()

        config = ChaosConfig(
            name="test_experiment",
            chaos_type=ChaosType.NETWORK_FAILURE,
            scope=ChaosScope.SERVICE,
            target="api_service",
            duration=0.1,
            success_criteria=[lambda: True]
        )

        experiment_id = suite.add_experiment(config)
        result = await suite.run_experiment(experiment_id)

        assert result.experiment_id is not None
        assert result.config == config
        assert len(suite.results) == 1
        assert experiment_id not in suite.running_experiments

    @pytest.mark.asyncio
    async def test_run_experiment_not_exists(self):
        """Test running non-existent experiment."""
        suite = ChaosTestSuite()

        with pytest.raises(ValueError, match="Unknown experiment"):
            await suite.run_experiment("nonexistent")

    @pytest.mark.asyncio
    async def test_run_experiment_already_running(self):
        """Test running experiment that's already running."""
        suite = ChaosTestSuite()

        config = ChaosConfig(
            name="test_experiment",
            chaos_type=ChaosType.NETWORK_FAILURE,
            scope=ChaosScope.SERVICE,
            target="api_service"
        )

        experiment_id = suite.add_experiment(config)
        suite.running_experiments.add(experiment_id)

        with pytest.raises(ValueError, match="already running"):
            await suite.run_experiment(experiment_id)

    @pytest.mark.asyncio
    async def test_run_all_experiments_sequential(self):
        """Test running all experiments sequentially."""
        suite = ChaosTestSuite()

        # Add multiple experiments
        configs = [
            ChaosConfig(
                name="experiment1",
                chaos_type=ChaosType.NETWORK_FAILURE,
                scope=ChaosScope.SERVICE,
                target="service1",
                duration=0.1,
                success_criteria=[lambda: True]
            ),
            ChaosConfig(
                name="experiment2",
                chaos_type=ChaosType.SERVICE_FAILURE,
                scope=ChaosScope.SERVICE,
                target="service2",
                duration=0.1,
                success_criteria=[lambda: True]
            )
        ]

        for config in configs:
            suite.add_experiment(config)

        results = await suite.run_all_experiments(parallel=False)

        assert len(results) == 2
        assert len(suite.results) == 2
        assert all(isinstance(result, ChaosResult) for result in results)

    @pytest.mark.asyncio
    async def test_run_all_experiments_parallel(self):
        """Test running all experiments in parallel."""
        suite = ChaosTestSuite()

        # Add multiple experiments
        configs = [
            ChaosConfig(
                name="experiment1",
                chaos_type=ChaosType.NETWORK_FAILURE,
                scope=ChaosScope.SERVICE,
                target="service1",
                duration=0.1,
                success_criteria=[lambda: True]
            ),
            ChaosConfig(
                name="experiment2",
                chaos_type=ChaosType.SERVICE_FAILURE,
                scope=ChaosScope.SERVICE,
                target="service2",
                duration=0.1,
                success_criteria=[lambda: True]
            )
        ]

        for config in configs:
            suite.add_experiment(config)

        results = await suite.run_all_experiments(parallel=True)

        assert len(results) == 2
        assert len(suite.results) == 2

    def test_create_standard_test_suite(self):
        """Test creating a standard test suite."""
        suite = ChaosTestSuite()

        experiment_ids = suite.create_standard_test_suite()

        assert len(experiment_ids) > 0
        assert len(suite.experiments) == len(experiment_ids)

        # Check that different types of experiments were created
        chaos_types = {suite.experiments[exp_id].config.chaos_type for exp_id in experiment_ids}
        assert len(chaos_types) > 1  # Multiple types

    def test_get_success_rate_no_results(self):
        """Test getting success rate with no results."""
        suite = ChaosTestSuite()

        assert suite.get_success_rate() == 0.0

    def test_get_success_rate_with_results(self):
        """Test getting success rate with results."""
        suite = ChaosTestSuite()

        # Add mock results
        config = ChaosConfig(
            name="test",
            chaos_type=ChaosType.NETWORK_FAILURE,
            scope=ChaosScope.SERVICE,
            target="test"
        )

        suite.results = [
            ChaosResult("1", config, datetime.now(UTC), success=True),
            ChaosResult("2", config, datetime.now(UTC), success=False),
            ChaosResult("3", config, datetime.now(UTC), success=True)
        ]

        assert suite.get_success_rate() == 2/3

    def test_generate_report_no_results(self):
        """Test generating report with no results."""
        suite = ChaosTestSuite()

        report = suite.generate_report()

        assert "No experiments have been run" in report["message"]

    def test_generate_report_with_results(self):
        """Test generating report with results."""
        suite = ChaosTestSuite()

        # Add mock results
        config1 = ChaosConfig(
            name="test1",
            chaos_type=ChaosType.NETWORK_FAILURE,
            scope=ChaosScope.SERVICE,
            target="test1"
        )
        config2 = ChaosConfig(
            name="test2",
            chaos_type=ChaosType.SERVICE_FAILURE,
            scope=ChaosScope.SERVICE,
            target="test2"
        )

        suite.results = [
            ChaosResult("1", config1, datetime.now(UTC), success=True, recovery_time=10.0),
            ChaosResult("2", config2, datetime.now(UTC), success=False, recovery_time=None),
            ChaosResult("3", config1, datetime.now(UTC), success=True, recovery_time=15.0)
        ]

        report = suite.generate_report()

        assert report["summary"]["total_experiments"] == 3
        assert report["summary"]["successful_experiments"] == 2
        assert report["summary"]["success_rate"] == 2/3
        assert report["summary"]["average_recovery_time_seconds"] == 12.5

        assert "network_failure" in report["results_by_type"]
        assert "service_failure" in report["results_by_type"]

        assert len(report["detailed_results"]) == 3


@pytest.mark.asyncio
async def test_run_chaos_monkey():
    """Test running chaos monkey."""
    # Create a test suite with short-duration experiments
    suite = ChaosTestSuite()

    config = ChaosConfig(
        name="monkey_test",
        chaos_type=ChaosType.NETWORK_FAILURE,
        scope=ChaosScope.SERVICE,
        target="test_service",
        duration=0.1,
        success_criteria=[lambda: True]
    )

    suite.add_experiment(config)

    # Mock the global suite
    with patch('libs.trading_models.chaos_testing.chaos_test_suite', suite):
        # Run chaos monkey for a short duration
        await run_chaos_monkey(duration=1, interval=0.5)

        # Should have run at least one experiment
        assert len(suite.results) >= 1


@pytest.mark.asyncio
async def test_chaos_context():
    """Test chaos context manager."""
    config = ChaosConfig(
        name="context_test",
        chaos_type=ChaosType.NETWORK_FAILURE,
        scope=ChaosScope.SERVICE,
        target="test_service",
        duration=0.1,
        success_criteria=[lambda: True]
    )

    suite = ChaosTestSuite()

    with patch('libs.trading_models.chaos_testing.chaos_test_suite', suite):
        async with chaos_context(config) as result:
            assert isinstance(result, ChaosResult)
            assert result.config == config

        # Experiment should be in the suite
        assert len(suite.experiments) == 1
        assert len(suite.results) == 1


@pytest.mark.asyncio
async def test_integration_chaos_testing_flow():
    """Test complete chaos testing flow integration."""
    suite = ChaosTestSuite()

    # Create a comprehensive test scenario
    configs = [
        ChaosConfig(
            name="network_outage",
            chaos_type=ChaosType.NETWORK_FAILURE,
            scope=ChaosScope.NETWORK,
            target="market_data_api",
            duration=0.1,
            intensity=1.0,
            parameters={"failure_type": "complete_outage"},
            success_criteria=[lambda: True]
        ),
        ChaosConfig(
            name="service_crash",
            chaos_type=ChaosType.SERVICE_FAILURE,
            scope=ChaosScope.SERVICE,
            target="execution_gateway",
            duration=0.1,
            intensity=1.0,
            parameters={"failure_type": "crash"},
            success_criteria=[lambda: True]
        ),
        ChaosConfig(
            name="memory_exhaustion",
            chaos_type=ChaosType.RESOURCE_EXHAUSTION,
            scope=ChaosScope.SYSTEM,
            target="orchestrator",
            duration=0.1,
            intensity=0.8,
            parameters={"resource_type": "memory"},
            success_criteria=[lambda: True]
        )
    ]

    # Add all experiments
    experiment_ids = []
    for config in configs:
        exp_id = suite.add_experiment(config)
        experiment_ids.append(exp_id)

    # Run all experiments
    results = await suite.run_all_experiments(parallel=False)

    # Verify results
    assert len(results) == 3
    assert all(result.success for result in results)

    # Generate and verify report
    report = suite.generate_report()
    assert report["summary"]["total_experiments"] == 3
    assert report["summary"]["success_rate"] == 1.0

    # Verify different chaos types were tested
    chaos_types = {result.config.chaos_type.value for result in results}
    assert len(chaos_types) == 3
    assert "network_failure" in chaos_types
    assert "service_failure" in chaos_types
    assert "resource_exhaustion" in chaos_types
