"""
Watchdog functionality with auto-restart capabilities for the trading system.

This module provides process monitoring, health checking, and automatic
restart capabilities to ensure system reliability.
"""

import asyncio
import logging
import os
import signal
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Optional

import psutil

from .error_handling import (
    ErrorContext,
    ErrorSeverity,
    ErrorType,
    error_recovery_system,
)

logger = logging.getLogger(__name__)


class ComponentStatus(Enum):
    """Status of a monitored component."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    STOPPED = "stopped"
    RESTARTING = "restarting"


class RestartPolicy(Enum):
    """Restart policies for components."""
    NEVER = "never"
    ON_FAILURE = "on_failure"
    ALWAYS = "always"
    UNLESS_STOPPED = "unless_stopped"


@dataclass
class HealthCheck:
    """Configuration for a health check."""
    name: str
    check_function: Callable[[], bool]
    interval: float = 30.0
    timeout: float = 10.0
    retries: int = 3
    failure_threshold: int = 3
    success_threshold: int = 1


@dataclass
class ComponentConfig:
    """Configuration for a monitored component."""
    name: str
    command: list[str]
    working_directory: Optional[str] = None
    environment: dict[str, str] = field(default_factory=dict)
    restart_policy: RestartPolicy = RestartPolicy.ON_FAILURE
    max_restarts: int = 5
    restart_delay: float = 5.0
    health_checks: list[HealthCheck] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    stop_timeout: float = 30.0
    kill_timeout: float = 10.0


@dataclass
class ComponentState:
    """Current state of a monitored component."""
    name: str
    status: ComponentStatus
    process: Optional[subprocess.Popen] = None
    pid: Optional[int] = None
    start_time: Optional[datetime] = None
    restart_count: int = 0
    last_restart: Optional[datetime] = None
    health_check_failures: dict[str, int] = field(default_factory=dict)
    health_check_successes: dict[str, int] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class HealthChecker:
    """Manages health checks for components."""

    def __init__(self):
        self.active_checks: dict[str, asyncio.Task] = {}
        self.check_results: dict[str, bool] = {}

    async def start_health_check(self, component_name: str, health_check: HealthCheck):
        """Start a health check for a component."""
        if component_name in self.active_checks:
            self.active_checks[component_name].cancel()

        self.active_checks[component_name] = asyncio.create_task(
            self._run_health_check(component_name, health_check)
        )

    async def stop_health_check(self, component_name: str):
        """Stop a health check for a component."""
        if component_name in self.active_checks:
            self.active_checks[component_name].cancel()
            del self.active_checks[component_name]

    async def _run_health_check(self, component_name: str, health_check: HealthCheck):
        """Run a health check continuously."""
        while True:
            try:
                await asyncio.sleep(health_check.interval)

                # Run health check with timeout
                try:
                    result = await asyncio.wait_for(
                        asyncio.to_thread(health_check.check_function),
                        timeout=health_check.timeout
                    )
                    self.check_results[f"{component_name}:{health_check.name}"] = result

                    if result:
                        logger.debug(f"Health check {health_check.name} for {component_name} passed")
                    else:
                        logger.warning(f"Health check {health_check.name} for {component_name} failed")

                except asyncio.TimeoutError:
                    logger.warning(f"Health check {health_check.name} for {component_name} timed out")
                    self.check_results[f"{component_name}:{health_check.name}"] = False

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check {health_check.name} for {component_name}: {e}")
                self.check_results[f"{component_name}:{health_check.name}"] = False

    def get_health_status(self, component_name: str, health_checks: list[HealthCheck]) -> bool:
        """Get overall health status for a component."""
        if not health_checks:
            return True

        for health_check in health_checks:
            check_key = f"{component_name}:{health_check.name}"
            if not self.check_results.get(check_key, True):
                return False

        return True


class ProcessManager:
    """Manages process lifecycle for components."""

    def __init__(self):
        self.processes: dict[str, subprocess.Popen] = {}

    async def start_process(self, config: ComponentConfig) -> subprocess.Popen:
        """Start a process for a component."""
        logger.info(f"Starting process for component {config.name}")

        env = os.environ.copy()
        env.update(config.environment)

        try:
            process = subprocess.Popen(
                config.command,
                cwd=config.working_directory,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid if os.name != 'nt' else None
            )

            self.processes[config.name] = process
            logger.info(f"Started process {process.pid} for component {config.name}")
            return process

        except Exception as e:
            logger.error(f"Failed to start process for component {config.name}: {e}")
            raise

    async def stop_process(self, component_name: str, stop_timeout: float = 30.0, kill_timeout: float = 10.0):
        """Stop a process gracefully."""
        if component_name not in self.processes:
            return

        process = self.processes[component_name]
        logger.info(f"Stopping process {process.pid} for component {component_name}")

        try:
            # Try graceful shutdown first
            if os.name == 'nt':
                process.terminate()
            else:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)

            # Wait for graceful shutdown
            try:
                await asyncio.wait_for(
                    asyncio.to_thread(process.wait),
                    timeout=stop_timeout
                )
                logger.info(f"Process {process.pid} for component {component_name} stopped gracefully")
            except asyncio.TimeoutError:
                # Force kill if graceful shutdown fails
                logger.warning(f"Force killing process {process.pid} for component {component_name}")
                if os.name == 'nt':
                    process.kill()
                else:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)

                await asyncio.wait_for(
                    asyncio.to_thread(process.wait),
                    timeout=kill_timeout
                )

        except Exception as e:
            logger.error(f"Error stopping process for component {component_name}: {e}")
        finally:
            if component_name in self.processes:
                del self.processes[component_name]

    def is_process_running(self, component_name: str) -> bool:
        """Check if a process is running."""
        if component_name not in self.processes:
            return False

        process = self.processes[component_name]
        return process.poll() is None

    def get_process_info(self, component_name: str) -> Optional[dict[str, Any]]:
        """Get information about a process."""
        if component_name not in self.processes:
            return None

        process = self.processes[component_name]

        try:
            psutil_process = psutil.Process(process.pid)
            return {
                "pid": process.pid,
                "status": psutil_process.status(),
                "cpu_percent": psutil_process.cpu_percent(),
                "memory_info": psutil_process.memory_info()._asdict(),
                "create_time": psutil_process.create_time(),
                "cmdline": psutil_process.cmdline()
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return {"pid": process.pid, "status": "unknown"}


class DependencyManager:
    """Manages component dependencies."""

    def __init__(self):
        self.dependency_graph: dict[str, set[str]] = {}

    def add_dependency(self, component: str, dependency: str):
        """Add a dependency relationship."""
        if component not in self.dependency_graph:
            self.dependency_graph[component] = set()
        self.dependency_graph[component].add(dependency)

    def get_start_order(self, components: list[str]) -> list[str]:
        """Get the order in which components should be started."""
        visited = set()
        temp_visited = set()
        result = []

        def visit(component: str):
            if component in temp_visited:
                raise ValueError(f"Circular dependency detected involving {component}")
            if component in visited:
                return

            temp_visited.add(component)

            # Visit dependencies first
            for dependency in self.dependency_graph.get(component, set()):
                if dependency in components:
                    visit(dependency)

            temp_visited.remove(component)
            visited.add(component)
            result.append(component)

        for component in components:
            if component not in visited:
                visit(component)

        return result

    def get_stop_order(self, components: list[str]) -> list[str]:
        """Get the order in which components should be stopped (reverse of start order)."""
        return list(reversed(self.get_start_order(components)))


class Watchdog:
    """Main watchdog class that monitors and manages components."""

    def __init__(self):
        self.components: dict[str, ComponentConfig] = {}
        self.component_states: dict[str, ComponentState] = {}
        self.process_manager = ProcessManager()
        self.health_checker = HealthChecker()
        self.dependency_manager = DependencyManager()
        self.running = False
        self.monitor_task: Optional[asyncio.Task] = None
        self.restart_locks: dict[str, asyncio.Lock] = {}

    def add_component(self, config: ComponentConfig):
        """Add a component to be monitored."""
        self.components[config.name] = config
        self.component_states[config.name] = ComponentState(
            name=config.name,
            status=ComponentStatus.STOPPED
        )
        self.restart_locks[config.name] = asyncio.Lock()

        # Add dependencies
        for dependency in config.dependencies:
            self.dependency_manager.add_dependency(config.name, dependency)

    async def start(self):
        """Start the watchdog and all components."""
        if self.running:
            return

        logger.info("Starting watchdog")
        self.running = True

        # Start components in dependency order
        start_order = self.dependency_manager.get_start_order(list(self.components.keys()))

        for component_name in start_order:
            await self.start_component(component_name)

        # Start monitoring task
        self.monitor_task = asyncio.create_task(self._monitor_components())

    async def stop(self):
        """Stop the watchdog and all components."""
        if not self.running:
            return

        logger.info("Stopping watchdog")
        self.running = False

        # Cancel monitoring task
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass

        # Stop components in reverse dependency order
        stop_order = self.dependency_manager.get_stop_order(list(self.components.keys()))

        for component_name in stop_order:
            await self.stop_component(component_name)

    async def start_component(self, component_name: str):
        """Start a specific component."""
        if component_name not in self.components:
            raise ValueError(f"Unknown component: {component_name}")

        config = self.components[component_name]
        state = self.component_states[component_name]

        if state.status in [ComponentStatus.HEALTHY, ComponentStatus.RESTARTING]:
            return

        logger.info(f"Starting component {component_name}")

        try:
            # Start the process
            process = await self.process_manager.start_process(config)

            # Update state
            state.process = process
            state.pid = process.pid
            state.start_time = datetime.now(UTC)
            state.status = ComponentStatus.HEALTHY

            # Start health checks
            for health_check in config.health_checks:
                await self.health_checker.start_health_check(component_name, health_check)

            logger.info(f"Component {component_name} started successfully")

        except Exception as e:
            logger.error(f"Failed to start component {component_name}: {e}")
            state.status = ComponentStatus.UNHEALTHY

            # Report error
            error_context = ErrorContext(
                error_type=ErrorType.SYSTEM,
                severity=ErrorSeverity.HIGH,
                message=f"Failed to start component {component_name}: {e}",
                exception=e,
                component=component_name
            )
            await error_recovery_system.handle_error(error_context)

    async def stop_component(self, component_name: str):
        """Stop a specific component."""
        if component_name not in self.components:
            raise ValueError(f"Unknown component: {component_name}")

        config = self.components[component_name]
        state = self.component_states[component_name]

        if state.status == ComponentStatus.STOPPED:
            return

        logger.info(f"Stopping component {component_name}")

        # Stop health checks
        await self.health_checker.stop_health_check(component_name)

        # Stop the process
        await self.process_manager.stop_process(
            component_name, config.stop_timeout, config.kill_timeout
        )

        # Update state
        state.process = None
        state.pid = None
        state.status = ComponentStatus.STOPPED

        logger.info(f"Component {component_name} stopped")

    async def restart_component(self, component_name: str, reason: str = "manual"):
        """Restart a specific component."""
        async with self.restart_locks[component_name]:
            config = self.components[component_name]
            state = self.component_states[component_name]

            # Check restart limits
            if state.restart_count >= config.max_restarts:
                logger.error(f"Component {component_name} has exceeded max restarts ({config.max_restarts})")
                state.status = ComponentStatus.UNHEALTHY
                return

            logger.info(f"Restarting component {component_name} (reason: {reason})")
            state.status = ComponentStatus.RESTARTING

            # Stop the component
            await self.stop_component(component_name)

            # Wait for restart delay
            await asyncio.sleep(config.restart_delay)

            # Start the component
            await self.start_component(component_name)

            # Update restart tracking
            state.restart_count += 1
            state.last_restart = datetime.now(UTC)

    async def _monitor_components(self):
        """Monitor all components continuously."""
        while self.running:
            try:
                for component_name, config in self.components.items():
                    state = self.component_states[component_name]

                    # Skip if component is stopped or restarting
                    if state.status in [ComponentStatus.STOPPED, ComponentStatus.RESTARTING]:
                        continue

                    # Check if process is still running
                    if not self.process_manager.is_process_running(component_name):
                        logger.warning(f"Component {component_name} process has died")

                        if config.restart_policy in [RestartPolicy.ALWAYS, RestartPolicy.ON_FAILURE]:
                            await self.restart_component(component_name, "process_died")
                        else:
                            state.status = ComponentStatus.STOPPED
                        continue

                    # Check health status
                    is_healthy = self.health_checker.get_health_status(component_name, config.health_checks)

                    if not is_healthy:
                        if state.status == ComponentStatus.HEALTHY:
                            state.status = ComponentStatus.DEGRADED
                            logger.warning(f"Component {component_name} is degraded")
                        elif state.status == ComponentStatus.DEGRADED:
                            state.status = ComponentStatus.UNHEALTHY
                            logger.error(f"Component {component_name} is unhealthy")

                            if config.restart_policy in [RestartPolicy.ALWAYS, RestartPolicy.ON_FAILURE]:
                                await self.restart_component(component_name, "health_check_failed")
                    else:
                        if state.status in [ComponentStatus.DEGRADED, ComponentStatus.UNHEALTHY]:
                            state.status = ComponentStatus.HEALTHY
                            logger.info(f"Component {component_name} is healthy again")

                await asyncio.sleep(10)  # Monitor every 10 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in component monitoring: {e}")
                await asyncio.sleep(5)

    def get_component_status(self, component_name: str) -> Optional[ComponentState]:
        """Get the current status of a component."""
        return self.component_states.get(component_name)

    def get_all_component_status(self) -> dict[str, ComponentState]:
        """Get the status of all components."""
        return self.component_states.copy()

    def get_system_health(self) -> dict[str, Any]:
        """Get overall system health information."""
        total_components = len(self.components)
        healthy_components = sum(
            1 for state in self.component_states.values()
            if state.status == ComponentStatus.HEALTHY
        )

        return {
            "total_components": total_components,
            "healthy_components": healthy_components,
            "health_percentage": (healthy_components / total_components * 100) if total_components > 0 else 0,
            "component_status": {
                name: state.status.value for name, state in self.component_states.items()
            },
            "uptime": time.time() - (min(
                state.start_time.timestamp() for state in self.component_states.values()
                if state.start_time
            ) if any(state.start_time for state in self.component_states.values()) else time.time())
        }


# Global watchdog instance
watchdog = Watchdog()
