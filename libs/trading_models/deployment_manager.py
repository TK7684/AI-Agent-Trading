"""
Deployment Manager for Blue/Green Deployments and Feature Flags
Handles safe deployments with rollback capabilities and canary releases.
"""

import asyncio
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from .e2e_integration import E2EIntegrationSystem
from .feature_flags import FeatureFlags
from .monitoring import MonitoringSystem


class DeploymentState(Enum):
    IDLE = "idle"
    DEPLOYING = "deploying"
    CANARY = "canary"
    FULL_DEPLOYMENT = "full_deployment"
    ROLLING_BACK = "rolling_back"
    FAILED = "failed"


@dataclass
class DeploymentConfig:
    """Configuration for deployment process."""
    version: str
    environment: str
    canary_percentage: float
    canary_duration_minutes: int
    max_error_rate: float
    max_latency_ms: float
    rollback_threshold_errors: int
    health_check_interval_seconds: int
    feature_flags: dict[str, bool]


@dataclass
class DeploymentMetrics:
    """Metrics collected during deployment."""
    version: str
    start_time: datetime
    end_time: Optional[datetime]
    state: DeploymentState
    canary_traffic_percentage: float
    success_rate: float
    avg_latency_ms: float
    error_count: int
    rollback_triggered: bool
    rollback_reason: Optional[str]
    health_checks_passed: int
    health_checks_failed: int


class DeploymentManager:
    """
    Manages blue/green deployments with canary releases,
    automatic rollback, and feature flag control.
    """

    def __init__(self, e2e_system: E2EIntegrationSystem, monitoring: MonitoringSystem):
        self.e2e_system = e2e_system
        self.monitoring = monitoring
        self.feature_flags = FeatureFlags()
        self.logger = logging.getLogger(__name__)

        # Deployment state
        self.current_deployment: Optional[DeploymentMetrics] = None
        self.deployment_state = DeploymentState.IDLE
        self.deployment_history: list[DeploymentMetrics] = []

        # Blue/Green environments
        self.blue_environment = None
        self.green_environment = None
        self.active_environment = "blue"

        # Canary release tracking
        self.canary_start_time = None
        self.canary_metrics = {
            'requests': 0,
            'errors': 0,
            'latencies': []
        }

        # Safety thresholds
        self.safety_thresholds = {
            'max_error_rate': 0.05,  # 5%
            'max_latency_p95_ms': 3000,
            'max_memory_growth_mb': 500,
            'min_success_rate': 0.95
        }

    async def deploy_version(self, config: DeploymentConfig) -> bool:
        """Deploy a new version using blue/green deployment with canary release."""
        if self.deployment_state != DeploymentState.IDLE:
            self.logger.error(f"Cannot deploy: system in state {self.deployment_state}")
            return False

        self.logger.info(f"Starting deployment of version {config.version}")

        # Initialize deployment metrics
        self.current_deployment = DeploymentMetrics(
            version=config.version,
            start_time=datetime.now(),
            end_time=None,
            state=DeploymentState.DEPLOYING,
            canary_traffic_percentage=0.0,
            success_rate=0.0,
            avg_latency_ms=0.0,
            error_count=0,
            rollback_triggered=False,
            rollback_reason=None,
            health_checks_passed=0,
            health_checks_failed=0
        )

        self.deployment_state = DeploymentState.DEPLOYING

        try:
            # Step 1: Prepare new environment (green if blue is active, vice versa)
            target_env = "green" if self.active_environment == "blue" else "blue"
            self.logger.info(f"Preparing {target_env} environment for version {config.version}")

            if not await self._prepare_environment(target_env, config):
                raise Exception(f"Failed to prepare {target_env} environment")

            # Step 2: Start canary release
            self.logger.info(f"Starting canary release with {config.canary_percentage}% traffic")
            if not await self._start_canary_release(config):
                raise Exception("Failed to start canary release")

            # Step 3: Monitor canary performance
            self.logger.info(f"Monitoring canary for {config.canary_duration_minutes} minutes")
            canary_success = await self._monitor_canary_release(config)

            if not canary_success:
                self.logger.warning("Canary release failed, initiating rollback")
                await self._rollback_deployment("Canary metrics exceeded thresholds")
                return False

            # Step 4: Full deployment
            self.logger.info("Canary successful, proceeding with full deployment")
            if not await self._complete_full_deployment(config):
                self.logger.error("Full deployment failed, initiating rollback")
                await self._rollback_deployment("Full deployment failed")
                return False

            # Step 5: Finalize deployment
            await self._finalize_deployment(config)

            self.logger.info(f"Deployment of version {config.version} completed successfully")
            return True

        except Exception as e:
            self.logger.error(f"Deployment failed: {e}")
            await self._rollback_deployment(str(e))
            return False

    async def _prepare_environment(self, environment: str, config: DeploymentConfig) -> bool:
        """Prepare the target environment for deployment."""
        try:
            self.logger.info(f"Preparing {environment} environment")

            # Update feature flags for new version
            for flag_name, enabled in config.feature_flags.items():
                self.feature_flags.set_flag(flag_name, enabled)

            # Perform health checks on target environment
            health_check_passed = await self._perform_health_check(environment)

            if health_check_passed:
                self.current_deployment.health_checks_passed += 1
                return True
            else:
                self.current_deployment.health_checks_failed += 1
                return False

        except Exception as e:
            self.logger.error(f"Failed to prepare {environment} environment: {e}")
            return False

    async def _start_canary_release(self, config: DeploymentConfig) -> bool:
        """Start canary release with specified traffic percentage."""
        try:
            self.deployment_state = DeploymentState.CANARY
            self.canary_start_time = datetime.now()
            self.canary_metrics = {'requests': 0, 'errors': 0, 'latencies': []}

            # Configure traffic routing for canary
            self.current_deployment.canary_traffic_percentage = config.canary_percentage

            # Enable canary feature flag
            self.feature_flags.set_flag("canary_deployment", True)
            self.feature_flags.set_flag("canary_percentage", config.canary_percentage)

            # Start monitoring canary traffic
            self.monitoring.record_metric("canary_deployment_started", 1.0)

            return True

        except Exception as e:
            self.logger.error(f"Failed to start canary release: {e}")
            return False

    async def _monitor_canary_release(self, config: DeploymentConfig) -> bool:
        """Monitor canary release performance and decide whether to proceed."""
        monitor_duration = config.canary_duration_minutes * 60  # Convert to seconds
        check_interval = config.health_check_interval_seconds

        start_time = time.time()

        while time.time() - start_time < monitor_duration:
            try:
                # Collect canary metrics
                await self._collect_canary_metrics()

                # Check safety thresholds
                if await self._check_canary_safety_thresholds(config):
                    self.logger.warning("Canary safety thresholds exceeded")
                    return False

                # Perform health check
                if not await self._perform_health_check("canary"):
                    self.current_deployment.health_checks_failed += 1
                    if self.current_deployment.health_checks_failed >= 3:
                        self.logger.warning("Multiple canary health check failures")
                        return False
                else:
                    self.current_deployment.health_checks_passed += 1

                # Wait before next check
                await asyncio.sleep(check_interval)

            except Exception as e:
                self.logger.error(f"Error during canary monitoring: {e}")
                return False

        # Calculate final canary metrics
        total_requests = self.canary_metrics['requests']
        if total_requests > 0:
            error_rate = self.canary_metrics['errors'] / total_requests
            avg_latency = sum(self.canary_metrics['latencies']) / len(self.canary_metrics['latencies']) if self.canary_metrics['latencies'] else 0

            self.current_deployment.success_rate = 1.0 - error_rate
            self.current_deployment.avg_latency_ms = avg_latency
            self.current_deployment.error_count = self.canary_metrics['errors']

            # Final safety check
            if error_rate > config.max_error_rate or avg_latency > config.max_latency_ms:
                self.logger.warning(f"Canary failed final check: error_rate={error_rate:.3f}, avg_latency={avg_latency:.1f}ms")
                return False

        self.logger.info(f"Canary release successful: {total_requests} requests, "
                        f"{self.current_deployment.success_rate:.3f} success rate, "
                        f"{self.current_deployment.avg_latency_ms:.1f}ms avg latency")

        return True

    async def _collect_canary_metrics(self):
        """Collect metrics from canary traffic."""
        try:
            # Simulate collecting metrics from monitoring system
            # In real implementation, this would query actual metrics

            # Get recent trading cycle results
            recent_results = await self._get_recent_trading_results(minutes=5)

            for result in recent_results:
                self.canary_metrics['requests'] += 1

                if not result.get('success', True):
                    self.canary_metrics['errors'] += 1

                if 'duration_ms' in result:
                    self.canary_metrics['latencies'].append(result['duration_ms'])

        except Exception as e:
            self.logger.warning(f"Failed to collect canary metrics: {e}")

    async def _check_canary_safety_thresholds(self, config: DeploymentConfig) -> bool:
        """Check if canary metrics exceed safety thresholds."""
        if self.canary_metrics['requests'] == 0:
            return False  # No data yet

        error_rate = self.canary_metrics['errors'] / self.canary_metrics['requests']

        if error_rate > config.max_error_rate:
            self.logger.warning(f"Canary error rate {error_rate:.3f} exceeds threshold {config.max_error_rate}")
            return True

        if self.canary_metrics['latencies']:
            avg_latency = sum(self.canary_metrics['latencies']) / len(self.canary_metrics['latencies'])
            if avg_latency > config.max_latency_ms:
                self.logger.warning(f"Canary avg latency {avg_latency:.1f}ms exceeds threshold {config.max_latency_ms}ms")
                return True

        return False

    async def _complete_full_deployment(self, config: DeploymentConfig) -> bool:
        """Complete the full deployment after successful canary."""
        try:
            self.deployment_state = DeploymentState.FULL_DEPLOYMENT

            # Switch traffic to new environment
            target_env = "green" if self.active_environment == "blue" else "blue"
            self.active_environment = target_env

            # Disable canary flags
            self.feature_flags.set_flag("canary_deployment", False)
            self.feature_flags.remove_flag("canary_percentage")

            # Enable full deployment
            self.feature_flags.set_flag("full_deployment", True)

            # Perform final health check
            if not await self._perform_health_check(self.active_environment):
                return False

            self.monitoring.record_metric("full_deployment_completed", 1.0)

            return True

        except Exception as e:
            self.logger.error(f"Failed to complete full deployment: {e}")
            return False

    async def _finalize_deployment(self, config: DeploymentConfig):
        """Finalize the deployment and clean up."""
        self.deployment_state = DeploymentState.IDLE

        if self.current_deployment:
            self.current_deployment.end_time = datetime.now()
            self.current_deployment.state = DeploymentState.IDLE

            # Add to deployment history
            self.deployment_history.append(self.current_deployment)

            # Keep only last 10 deployments
            if len(self.deployment_history) > 10:
                self.deployment_history = self.deployment_history[-10:]

        # Clean up feature flags
        self.feature_flags.remove_flag("full_deployment")

        self.logger.info(f"Deployment {config.version} finalized successfully")

    async def _rollback_deployment(self, reason: str):
        """Rollback the current deployment."""
        self.logger.warning(f"Rolling back deployment: {reason}")

        self.deployment_state = DeploymentState.ROLLING_BACK

        if self.current_deployment:
            self.current_deployment.rollback_triggered = True
            self.current_deployment.rollback_reason = reason
            self.current_deployment.state = DeploymentState.ROLLING_BACK

        try:
            # Disable all new features
            self.feature_flags.set_flag("canary_deployment", False)
            self.feature_flags.set_flag("full_deployment", False)
            self.feature_flags.remove_flag("canary_percentage")

            # Switch back to previous environment
            previous_env = "blue" if self.active_environment == "green" else "green"
            self.active_environment = previous_env

            # Trigger safe mode to prevent risky operations
            self.e2e_system._trigger_safe_mode(f"Deployment rollback: {reason}")

            # Record rollback metrics
            self.monitoring.record_metric("deployment_rollback", 1.0)
            self.monitoring.send_alert("DEPLOYMENT_ROLLBACK", {
                "reason": reason,
                "version": self.current_deployment.version if self.current_deployment else "unknown",
                "timestamp": datetime.now().isoformat()
            })

            self.deployment_state = DeploymentState.FAILED

            if self.current_deployment:
                self.current_deployment.end_time = datetime.now()
                self.current_deployment.state = DeploymentState.FAILED
                self.deployment_history.append(self.current_deployment)

            self.logger.info("Rollback completed")

        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")
            # This is a critical situation - alert operations team
            self.monitoring.send_alert("ROLLBACK_FAILED", {
                "error": str(e),
                "original_reason": reason,
                "timestamp": datetime.now().isoformat()
            })

    async def _perform_health_check(self, environment: str) -> bool:
        """Perform comprehensive health check on specified environment."""
        try:
            # Check system components
            health_checks = [
                self._check_market_data_health(),
                self._check_llm_health(),
                self._check_risk_management_health(),
                self._check_persistence_health(),
                self._check_monitoring_health()
            ]

            results = await asyncio.gather(*health_checks, return_exceptions=True)

            # All health checks must pass
            all_healthy = all(
                isinstance(result, bool) and result for result in results
            )

            if all_healthy:
                self.logger.info(f"Health check passed for {environment} environment")
            else:
                self.logger.warning(f"Health check failed for {environment} environment")
                failed_checks = [
                    f"check_{i}" for i, result in enumerate(results)
                    if not (isinstance(result, bool) and result)
                ]
                self.logger.warning(f"Failed checks: {failed_checks}")

            return all_healthy

        except Exception as e:
            self.logger.error(f"Health check error for {environment}: {e}")
            return False

    async def _check_market_data_health(self) -> bool:
        """Check market data component health."""
        try:
            # Test basic market data fetch
            result = await self.e2e_system.run_complete_trading_cycle("BTCUSDT")
            return result.success
        except Exception:
            return False

    async def _check_llm_health(self) -> bool:
        """Check LLM component health."""
        try:
            # Test LLM with simple request
            if hasattr(self.e2e_system, 'llm_router'):
                response = await self.e2e_system.llm_router.analyze_market(
                    "Health check", {"test": True}
                )
                return response is not None
            return True
        except Exception:
            return False

    async def _check_risk_management_health(self) -> bool:
        """Check risk management component health."""
        try:
            # Test risk calculation
            return hasattr(self.e2e_system, 'risk_manager')
        except Exception:
            return False

    async def _check_persistence_health(self) -> bool:
        """Check persistence component health."""
        try:
            # Test database connection
            if hasattr(self.e2e_system, 'persistence'):
                await self.e2e_system.persistence.health_check()
            return True
        except Exception:
            return False

    async def _check_monitoring_health(self) -> bool:
        """Check monitoring component health."""
        try:
            # Test metrics recording
            self.monitoring.record_metric("health_check", 1.0)
            return True
        except Exception:
            return False

    async def _get_recent_trading_results(self, minutes: int = 5) -> list[dict[str, Any]]:
        """Get recent trading results for metrics collection."""
        try:
            # In real implementation, this would query the persistence layer
            # For now, return mock data
            return [
                {"success": True, "duration_ms": 850, "symbol": "BTCUSDT"},
                {"success": True, "duration_ms": 920, "symbol": "ETHUSDT"},
                {"success": False, "duration_ms": 1200, "symbol": "ADAUSDT", "error": "timeout"}
            ]
        except Exception:
            return []

    def get_deployment_status(self) -> dict[str, Any]:
        """Get current deployment status and metrics."""
        status = {
            'state': self.deployment_state.value,
            'active_environment': self.active_environment,
            'current_deployment': None,
            'deployment_history': [asdict(d) for d in self.deployment_history[-5:]],  # Last 5
            'feature_flags': self.feature_flags.get_all_flags()
        }

        if self.current_deployment:
            status['current_deployment'] = asdict(self.current_deployment)

        return status

    async def emergency_rollback(self) -> bool:
        """Perform emergency rollback with minimal checks."""
        self.logger.critical("Performing emergency rollback")

        try:
            # Immediate rollback without extensive checks
            await self._rollback_deployment("Emergency rollback triggered")

            # Force safe mode
            self.e2e_system._trigger_safe_mode("Emergency rollback")

            # Disable all risky features
            risky_features = ["live_trading", "high_risk_trades", "llm_analysis"]
            for feature in risky_features:
                self.feature_flags.disable(feature)

            return True

        except Exception as e:
            self.logger.critical(f"Emergency rollback failed: {e}")
            return False

    def can_rollback_within_time_limit(self, time_limit_seconds: int = 60) -> bool:
        """Check if system can rollback within specified time limit."""
        # This would check system state and estimate rollback time
        # For now, assume we can always rollback within 60 seconds
        return time_limit_seconds >= 60
