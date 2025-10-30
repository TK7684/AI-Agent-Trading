"""
Tests for the watchdog functionality and auto-restart capabilities.
"""

import asyncio
import time
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from libs.trading_models.watchdog import (
    ComponentConfig,
    ComponentState,
    ComponentStatus,
    DependencyManager,
    HealthCheck,
    HealthChecker,
    ProcessManager,
    RestartPolicy,
    Watchdog,
)


class TestHealthCheck:
    """Test HealthCheck functionality."""

    def test_health_check_creation(self):
        """Test creating a health check."""
        def check_func():
            return True

        health_check = HealthCheck(
            name="test_check",
            check_function=check_func,
            interval=30.0,
            timeout=10.0
        )

        assert health_check.name == "test_check"
        assert health_check.check_function == check_func
        assert health_check.interval == 30.0
        assert health_check.timeout == 10.0


class TestComponentConfig:
    """Test ComponentConfig functionality."""

    def test_component_config_creation(self):
        """Test creating a component configuration."""
        config = ComponentConfig(
            name="test_component",
            command=["python", "test.py"],
            restart_policy=RestartPolicy.ON_FAILURE,
            max_restarts=5
        )

        assert config.name == "test_component"
        assert config.command == ["python", "test.py"]
        assert config.restart_policy == RestartPolicy.ON_FAILURE
        assert config.max_restarts == 5

    def test_component_config_with_dependencies(self):
        """Test component configuration with dependencies."""
        config = ComponentConfig(
            name="dependent_component",
            command=["python", "dependent.py"],
            dependencies=["database", "cache"]
        )

        assert config.dependencies == ["database", "cache"]


class TestComponentState:
    """Test ComponentState functionality."""

    def test_component_state_creation(self):
        """Test creating a component state."""
        state = ComponentState(
            name="test_component",
            status=ComponentStatus.HEALTHY
        )

        assert state.name == "test_component"
        assert state.status == ComponentStatus.HEALTHY
        assert state.restart_count == 0
        assert state.process is None


class TestHealthChecker:
    """Test HealthChecker functionality."""

    def test_health_checker_creation(self):
        """Test creating a health checker."""
        checker = HealthChecker()

        assert len(checker.active_checks) == 0
        assert len(checker.check_results) == 0

    @pytest.mark.asyncio
    async def test_start_health_check(self):
        """Test starting a health check."""
        checker = HealthChecker()

        def check_func():
            return True

        health_check = HealthCheck(
            name="test_check",
            check_function=check_func,
            interval=0.1  # Short interval for testing
        )

        await checker.start_health_check("test_component", health_check)

        assert "test_component" in checker.active_checks

        # Wait for at least one check to run
        await asyncio.sleep(0.2)

        # Stop the check
        await checker.stop_health_check("test_component")

        assert "test_component" not in checker.active_checks

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test health check failure detection."""
        checker = HealthChecker()

        def failing_check():
            return False

        health_check = HealthCheck(
            name="failing_check",
            check_function=failing_check,
            interval=0.1
        )

        await checker.start_health_check("test_component", health_check)

        # Wait for check to run
        await asyncio.sleep(0.2)

        # Check result should be False
        check_key = "test_component:failing_check"
        assert checker.check_results.get(check_key) is False

        await checker.stop_health_check("test_component")

    @pytest.mark.asyncio
    async def test_health_check_timeout(self):
        """Test health check timeout handling."""
        checker = HealthChecker()

        def slow_check():
            time.sleep(1.0)  # Longer than timeout
            return True

        health_check = HealthCheck(
            name="slow_check",
            check_function=slow_check,
            interval=0.1,
            timeout=0.1  # Short timeout
        )

        await checker.start_health_check("test_component", health_check)

        # Wait for check to timeout
        await asyncio.sleep(0.3)

        # Check result should be False due to timeout
        check_key = "test_component:slow_check"
        assert checker.check_results.get(check_key) is False

        await checker.stop_health_check("test_component")

    def test_get_health_status_all_passing(self):
        """Test getting health status when all checks pass."""
        checker = HealthChecker()

        # Mock passing checks
        checker.check_results = {
            "test_component:check1": True,
            "test_component:check2": True
        }

        health_checks = [
            HealthCheck("check1", lambda: True),
            HealthCheck("check2", lambda: True)
        ]

        assert checker.get_health_status("test_component", health_checks) is True

    def test_get_health_status_one_failing(self):
        """Test getting health status when one check fails."""
        checker = HealthChecker()

        # Mock one failing check
        checker.check_results = {
            "test_component:check1": True,
            "test_component:check2": False
        }

        health_checks = [
            HealthCheck("check1", lambda: True),
            HealthCheck("check2", lambda: False)
        ]

        assert checker.get_health_status("test_component", health_checks) is False

    def test_get_health_status_no_checks(self):
        """Test getting health status with no checks."""
        checker = HealthChecker()

        assert checker.get_health_status("test_component", []) is True


class TestProcessManager:
    """Test ProcessManager functionality."""

    def test_process_manager_creation(self):
        """Test creating a process manager."""
        pm = ProcessManager()

        assert len(pm.processes) == 0

    @pytest.mark.asyncio
    @patch('subprocess.Popen')
    async def test_start_process(self, mock_popen):
        """Test starting a process."""
        pm = ProcessManager()

        # Mock process
        mock_process = Mock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        config = ComponentConfig(
            name="test_component",
            command=["python", "test.py"]
        )

        process = await pm.start_process(config)

        assert process == mock_process
        assert pm.processes["test_component"] == mock_process
        mock_popen.assert_called_once()

    @pytest.mark.asyncio
    @patch('subprocess.Popen')
    async def test_start_process_with_environment(self, mock_popen):
        """Test starting a process with custom environment."""
        pm = ProcessManager()

        mock_process = Mock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        config = ComponentConfig(
            name="test_component",
            command=["python", "test.py"],
            environment={"TEST_VAR": "test_value"}
        )

        await pm.start_process(config)

        # Check that environment was passed
        call_args = mock_popen.call_args
        env = call_args[1]['env']
        assert "TEST_VAR" in env
        assert env["TEST_VAR"] == "test_value"

    def test_is_process_running_true(self):
        """Test checking if process is running (true case)."""
        pm = ProcessManager()

        mock_process = Mock()
        mock_process.poll.return_value = None  # Process is running
        pm.processes["test_component"] = mock_process

        assert pm.is_process_running("test_component") is True

    def test_is_process_running_false(self):
        """Test checking if process is running (false case)."""
        pm = ProcessManager()

        mock_process = Mock()
        mock_process.poll.return_value = 0  # Process has exited
        pm.processes["test_component"] = mock_process

        assert pm.is_process_running("test_component") is False

    def test_is_process_running_not_exists(self):
        """Test checking if process is running when it doesn't exist."""
        pm = ProcessManager()

        assert pm.is_process_running("nonexistent") is False

    @patch('psutil.Process')
    def test_get_process_info(self, mock_psutil_process):
        """Test getting process information."""
        pm = ProcessManager()

        # Mock process
        mock_process = Mock()
        mock_process.pid = 12345
        pm.processes["test_component"] = mock_process

        # Mock psutil process
        mock_psutil_instance = Mock()
        mock_psutil_instance.status.return_value = "running"
        mock_psutil_instance.cpu_percent.return_value = 25.5
        mock_psutil_instance.memory_info.return_value = Mock()
        mock_psutil_instance.memory_info.return_value._asdict.return_value = {"rss": 1024000}
        mock_psutil_instance.create_time.return_value = 1234567890
        mock_psutil_instance.cmdline.return_value = ["python", "test.py"]
        mock_psutil_process.return_value = mock_psutil_instance

        info = pm.get_process_info("test_component")

        assert info["pid"] == 12345
        assert info["status"] == "running"
        assert info["cpu_percent"] == 25.5
        assert info["memory_info"]["rss"] == 1024000

    def test_get_process_info_not_exists(self):
        """Test getting process info when process doesn't exist."""
        pm = ProcessManager()

        info = pm.get_process_info("nonexistent")
        assert info is None


class TestDependencyManager:
    """Test DependencyManager functionality."""

    def test_dependency_manager_creation(self):
        """Test creating a dependency manager."""
        dm = DependencyManager()

        assert len(dm.dependency_graph) == 0

    def test_add_dependency(self):
        """Test adding dependencies."""
        dm = DependencyManager()

        dm.add_dependency("app", "database")
        dm.add_dependency("app", "cache")
        dm.add_dependency("api", "app")

        assert "database" in dm.dependency_graph["app"]
        assert "cache" in dm.dependency_graph["app"]
        assert "app" in dm.dependency_graph["api"]

    def test_get_start_order_simple(self):
        """Test getting start order for simple dependencies."""
        dm = DependencyManager()

        dm.add_dependency("app", "database")
        dm.add_dependency("api", "app")

        components = ["app", "database", "api"]
        start_order = dm.get_start_order(components)

        # Database should start first, then app, then api
        assert start_order.index("database") < start_order.index("app")
        assert start_order.index("app") < start_order.index("api")

    def test_get_start_order_complex(self):
        """Test getting start order for complex dependencies."""
        dm = DependencyManager()

        dm.add_dependency("app", "database")
        dm.add_dependency("app", "cache")
        dm.add_dependency("api", "app")
        dm.add_dependency("worker", "database")
        dm.add_dependency("worker", "cache")

        components = ["app", "database", "cache", "api", "worker"]
        start_order = dm.get_start_order(components)

        # Database and cache should start before app and worker
        db_index = start_order.index("database")
        cache_index = start_order.index("cache")
        app_index = start_order.index("app")
        worker_index = start_order.index("worker")
        api_index = start_order.index("api")

        assert db_index < app_index
        assert cache_index < app_index
        assert db_index < worker_index
        assert cache_index < worker_index
        assert app_index < api_index

    def test_get_start_order_circular_dependency(self):
        """Test handling circular dependencies."""
        dm = DependencyManager()

        dm.add_dependency("app", "database")
        dm.add_dependency("database", "app")  # Circular dependency

        components = ["app", "database"]

        with pytest.raises(ValueError, match="Circular dependency"):
            dm.get_start_order(components)

    def test_get_stop_order(self):
        """Test getting stop order (reverse of start order)."""
        dm = DependencyManager()

        dm.add_dependency("app", "database")
        dm.add_dependency("api", "app")

        components = ["app", "database", "api"]
        start_order = dm.get_start_order(components)
        stop_order = dm.get_stop_order(components)

        assert stop_order == list(reversed(start_order))


class TestWatchdog:
    """Test Watchdog functionality."""

    def test_watchdog_creation(self):
        """Test creating a watchdog."""
        wd = Watchdog()

        assert len(wd.components) == 0
        assert len(wd.component_states) == 0
        assert wd.running is False

    def test_add_component(self):
        """Test adding a component to watchdog."""
        wd = Watchdog()

        config = ComponentConfig(
            name="test_component",
            command=["python", "test.py"],
            dependencies=["database"]
        )

        wd.add_component(config)

        assert "test_component" in wd.components
        assert "test_component" in wd.component_states
        assert wd.component_states["test_component"].status == ComponentStatus.STOPPED
        assert "test_component" in wd.restart_locks

    @pytest.mark.asyncio
    @patch.object(ProcessManager, 'start_process')
    async def test_start_component(self, mock_start_process):
        """Test starting a component."""
        wd = Watchdog()

        # Mock process
        mock_process = Mock()
        mock_process.pid = 12345
        mock_start_process.return_value = mock_process

        config = ComponentConfig(
            name="test_component",
            command=["python", "test.py"]
        )

        wd.add_component(config)
        await wd.start_component("test_component")

        state = wd.component_states["test_component"]
        assert state.status == ComponentStatus.HEALTHY
        assert state.process == mock_process
        assert state.pid == 12345
        assert state.start_time is not None

    @pytest.mark.asyncio
    @patch.object(ProcessManager, 'start_process')
    async def test_start_component_failure(self, mock_start_process):
        """Test starting a component that fails."""
        wd = Watchdog()

        # Mock process start failure
        mock_start_process.side_effect = Exception("Failed to start")

        config = ComponentConfig(
            name="test_component",
            command=["python", "test.py"]
        )

        wd.add_component(config)
        await wd.start_component("test_component")

        state = wd.component_states["test_component"]
        assert state.status == ComponentStatus.UNHEALTHY

    @pytest.mark.asyncio
    @patch.object(ProcessManager, 'stop_process')
    @patch.object(HealthChecker, 'stop_health_check')
    async def test_stop_component(self, mock_stop_health_check, mock_stop_process):
        """Test stopping a component."""
        wd = Watchdog()

        config = ComponentConfig(
            name="test_component",
            command=["python", "test.py"]
        )

        wd.add_component(config)

        # Set component as running
        state = wd.component_states["test_component"]
        state.status = ComponentStatus.HEALTHY
        state.pid = 12345

        await wd.stop_component("test_component")

        assert state.status == ComponentStatus.STOPPED
        assert state.process is None
        assert state.pid is None
        mock_stop_health_check.assert_called_once()
        mock_stop_process.assert_called_once()

    @pytest.mark.asyncio
    @patch.object(Watchdog, 'stop_component')
    @patch.object(Watchdog, 'start_component')
    async def test_restart_component(self, mock_start_component, mock_stop_component):
        """Test restarting a component."""
        wd = Watchdog()

        config = ComponentConfig(
            name="test_component",
            command=["python", "test.py"],
            restart_delay=0.01  # Short delay for testing
        )

        wd.add_component(config)

        await wd.restart_component("test_component", "test_reason")

        state = wd.component_states["test_component"]
        assert state.restart_count == 1
        assert state.last_restart is not None

        mock_stop_component.assert_called_once()
        mock_start_component.assert_called_once()

    @pytest.mark.asyncio
    async def test_restart_component_max_restarts_exceeded(self):
        """Test restart component when max restarts exceeded."""
        wd = Watchdog()

        config = ComponentConfig(
            name="test_component",
            command=["python", "test.py"],
            max_restarts=2
        )

        wd.add_component(config)

        # Set restart count to max
        state = wd.component_states["test_component"]
        state.restart_count = 2

        await wd.restart_component("test_component")

        assert state.status == ComponentStatus.UNHEALTHY
        assert state.restart_count == 2  # Should not increment

    def test_get_component_status(self):
        """Test getting component status."""
        wd = Watchdog()

        config = ComponentConfig(
            name="test_component",
            command=["python", "test.py"]
        )

        wd.add_component(config)

        status = wd.get_component_status("test_component")
        assert status is not None
        assert status.name == "test_component"
        assert status.status == ComponentStatus.STOPPED

    def test_get_component_status_not_exists(self):
        """Test getting status of non-existent component."""
        wd = Watchdog()

        status = wd.get_component_status("nonexistent")
        assert status is None

    def test_get_all_component_status(self):
        """Test getting all component statuses."""
        wd = Watchdog()

        config1 = ComponentConfig(name="component1", command=["python", "test1.py"])
        config2 = ComponentConfig(name="component2", command=["python", "test2.py"])

        wd.add_component(config1)
        wd.add_component(config2)

        all_status = wd.get_all_component_status()

        assert len(all_status) == 2
        assert "component1" in all_status
        assert "component2" in all_status

    def test_get_system_health_all_healthy(self):
        """Test getting system health when all components are healthy."""
        wd = Watchdog()

        config1 = ComponentConfig(name="component1", command=["python", "test1.py"])
        config2 = ComponentConfig(name="component2", command=["python", "test2.py"])

        wd.add_component(config1)
        wd.add_component(config2)

        # Set components as healthy
        wd.component_states["component1"].status = ComponentStatus.HEALTHY
        wd.component_states["component1"].start_time = datetime.utcnow()
        wd.component_states["component2"].status = ComponentStatus.HEALTHY
        wd.component_states["component2"].start_time = datetime.utcnow()

        health = wd.get_system_health()

        assert health["total_components"] == 2
        assert health["healthy_components"] == 2
        assert health["health_percentage"] == 100.0
        assert health["component_status"]["component1"] == "healthy"
        assert health["component_status"]["component2"] == "healthy"

    def test_get_system_health_mixed(self):
        """Test getting system health with mixed component states."""
        wd = Watchdog()

        config1 = ComponentConfig(name="component1", command=["python", "test1.py"])
        config2 = ComponentConfig(name="component2", command=["python", "test2.py"])
        config3 = ComponentConfig(name="component3", command=["python", "test3.py"])

        wd.add_component(config1)
        wd.add_component(config2)
        wd.add_component(config3)

        # Set mixed states
        wd.component_states["component1"].status = ComponentStatus.HEALTHY
        wd.component_states["component2"].status = ComponentStatus.DEGRADED
        wd.component_states["component3"].status = ComponentStatus.UNHEALTHY

        health = wd.get_system_health()

        assert health["total_components"] == 3
        assert health["healthy_components"] == 1
        assert abs(health["health_percentage"] - (100.0 / 3)) < 0.01
        assert health["component_status"]["component1"] == "healthy"
        assert health["component_status"]["component2"] == "degraded"
        assert health["component_status"]["component3"] == "unhealthy"


@pytest.mark.asyncio
async def test_integration_watchdog_with_dependencies():
    """Test watchdog integration with component dependencies."""
    wd = Watchdog()

    # Create components with dependencies
    database_config = ComponentConfig(
        name="database",
        command=["python", "database.py"]
    )

    app_config = ComponentConfig(
        name="app",
        command=["python", "app.py"],
        dependencies=["database"]
    )

    api_config = ComponentConfig(
        name="api",
        command=["python", "api.py"],
        dependencies=["app"]
    )

    wd.add_component(database_config)
    wd.add_component(app_config)
    wd.add_component(api_config)

    # Check dependency order
    start_order = wd.dependency_manager.get_start_order(["database", "app", "api"])
    assert start_order.index("database") < start_order.index("app")
    assert start_order.index("app") < start_order.index("api")

    stop_order = wd.dependency_manager.get_stop_order(["database", "app", "api"])
    assert stop_order == list(reversed(start_order))


@pytest.mark.asyncio
@patch.object(ProcessManager, 'is_process_running')
@patch.object(HealthChecker, 'get_health_status')
async def test_watchdog_monitoring_process_died(mock_get_health_status, mock_is_process_running):
    """Test watchdog monitoring when a process dies."""
    wd = Watchdog()

    config = ComponentConfig(
        name="test_component",
        command=["python", "test.py"],
        restart_policy=RestartPolicy.ON_FAILURE
    )

    wd.add_component(config)

    # Set component as initially healthy
    state = wd.component_states["test_component"]
    state.status = ComponentStatus.HEALTHY

    # Mock process as not running (died)
    mock_is_process_running.return_value = False
    mock_get_health_status.return_value = True

    # Mock restart_component to avoid actual process operations
    with patch.object(wd, 'restart_component') as mock_restart:
        # Start monitoring (run one iteration)
        wd.running = True

        # Simulate one monitoring cycle
        for component_name, config in wd.components.items():
            state = wd.component_states[component_name]

            if state.status not in [ComponentStatus.STOPPED, ComponentStatus.RESTARTING]:
                if not wd.process_manager.is_process_running(component_name):
                    if config.restart_policy in [RestartPolicy.ALWAYS, RestartPolicy.ON_FAILURE]:
                        await wd.restart_component(component_name, "process_died")

        # Verify restart was called
        mock_restart.assert_called_once_with("test_component", "process_died")


@pytest.mark.asyncio
@patch.object(ProcessManager, 'is_process_running')
@patch.object(HealthChecker, 'get_health_status')
async def test_watchdog_monitoring_health_check_failed(mock_get_health_status, mock_is_process_running):
    """Test watchdog monitoring when health checks fail."""
    wd = Watchdog()

    config = ComponentConfig(
        name="test_component",
        command=["python", "test.py"],
        restart_policy=RestartPolicy.ON_FAILURE
    )

    wd.add_component(config)

    # Set component as initially healthy
    state = wd.component_states["test_component"]
    state.status = ComponentStatus.HEALTHY

    # Mock process as running but health check failing
    mock_is_process_running.return_value = True
    mock_get_health_status.return_value = False

    # Simulate monitoring cycles
    wd.running = True

    # First cycle - should become degraded
    for component_name, config in wd.components.items():
        state = wd.component_states[component_name]

        if state.status not in [ComponentStatus.STOPPED, ComponentStatus.RESTARTING]:
            if wd.process_manager.is_process_running(component_name):
                is_healthy = wd.health_checker.get_health_status(component_name, config.health_checks)

                if not is_healthy:
                    if state.status == ComponentStatus.HEALTHY:
                        state.status = ComponentStatus.DEGRADED

    assert state.status == ComponentStatus.DEGRADED

    # Second cycle - should become unhealthy and restart
    with patch.object(wd, 'restart_component') as mock_restart:
        for component_name, config in wd.components.items():
            state = wd.component_states[component_name]

            if state.status not in [ComponentStatus.STOPPED, ComponentStatus.RESTARTING]:
                if wd.process_manager.is_process_running(component_name):
                    is_healthy = wd.health_checker.get_health_status(component_name, config.health_checks)

                    if not is_healthy:
                        if state.status == ComponentStatus.DEGRADED:
                            state.status = ComponentStatus.UNHEALTHY

                            if config.restart_policy in [RestartPolicy.ALWAYS, RestartPolicy.ON_FAILURE]:
                                await wd.restart_component(component_name, "health_check_failed")

        mock_restart.assert_called_once_with("test_component", "health_check_failed")
