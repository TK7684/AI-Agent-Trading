"""
Health check system for all trading system components.
Provides fast health status checks with <200ms response times.
"""

import asyncio
import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Optional

import psutil
import requests

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check"""
    component: str
    status: HealthStatus
    message: str
    response_time_ms: float
    timestamp: datetime
    details: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'component': self.component,
            'status': self.status.value,
            'message': self.message,
            'response_time_ms': self.response_time_ms,
            'timestamp': self.timestamp.isoformat(),
            'details': self.details or {}
        }


class HealthCheck:
    """Base class for health checks"""

    def __init__(self, name: str, timeout_ms: int = 200):
        self.name = name
        self.timeout_ms = timeout_ms

    async def check(self) -> HealthCheckResult:
        """Perform health check"""
        start_time = time.time()
        try:
            status, message, details = await self._perform_check()
            response_time = (time.time() - start_time) * 1000

            return HealthCheckResult(
                component=self.name,
                status=status,
                message=message,
                response_time_ms=response_time,
                timestamp=datetime.now(UTC),
                details=details
            )
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                response_time_ms=response_time,
                timestamp=datetime.now(UTC)
            )

    async def _perform_check(self) -> tuple[HealthStatus, str, Optional[dict[str, Any]]]:
        """Override this method to implement specific health check logic"""
        raise NotImplementedError


class DatabaseHealthCheck(HealthCheck):
    """Health check for database connectivity"""

    def __init__(self, db_connection_func: Callable):
        super().__init__("database")
        self.db_connection_func = db_connection_func

    async def _perform_check(self) -> tuple[HealthStatus, str, Optional[dict[str, Any]]]:
        """Check database connectivity"""
        try:
            # Test database connection with a simple query
            conn = self.db_connection_func()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            conn.close()

            if result:
                return HealthStatus.HEALTHY, "Database connection successful", {"query_result": result[0]}
            else:
                return HealthStatus.UNHEALTHY, "Database query returned no results", None

        except Exception as e:
            return HealthStatus.UNHEALTHY, f"Database connection failed: {str(e)}", None


class MarketDataHealthCheck(HealthCheck):
    """Health check for market data feeds"""

    def __init__(self, data_source_url: str, api_key: Optional[str] = None):
        super().__init__("market_data")
        self.data_source_url = data_source_url
        self.api_key = api_key

    async def _perform_check(self) -> tuple[HealthStatus, str, Optional[dict[str, Any]]]:
        """Check market data feed connectivity"""
        try:
            headers = {}
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'

            # Test with a simple market data request
            response = requests.get(
                f"{self.data_source_url}/health",
                headers=headers,
                timeout=self.timeout_ms / 1000
            )

            if response.status_code == 200:
                return HealthStatus.HEALTHY, "Market data feed accessible", {
                    "status_code": response.status_code,
                    "response_size": len(response.content)
                }
            else:
                return HealthStatus.DEGRADED, f"Market data feed returned status {response.status_code}", {
                    "status_code": response.status_code
                }

        except requests.exceptions.Timeout:
            return HealthStatus.UNHEALTHY, "Market data feed timeout", None
        except Exception as e:
            return HealthStatus.UNHEALTHY, f"Market data feed error: {str(e)}", None


class ExecutionGatewayHealthCheck(HealthCheck):
    """Health check for execution gateway"""

    def __init__(self, gateway_url: str):
        super().__init__("execution_gateway")
        self.gateway_url = gateway_url

    async def _perform_check(self) -> tuple[HealthStatus, str, Optional[dict[str, Any]]]:
        """Check execution gateway health"""
        try:
            response = requests.get(
                f"{self.gateway_url}/health",
                timeout=self.timeout_ms / 1000
            )

            if response.status_code == 200:
                data = response.json()
                return HealthStatus.HEALTHY, "Execution gateway healthy", data
            else:
                return HealthStatus.UNHEALTHY, f"Execution gateway returned status {response.status_code}", {
                    "status_code": response.status_code
                }

        except requests.exceptions.Timeout:
            return HealthStatus.UNHEALTHY, "Execution gateway timeout", None
        except Exception as e:
            return HealthStatus.UNHEALTHY, f"Execution gateway error: {str(e)}", None


class LLMHealthCheck(HealthCheck):
    """Health check for LLM services"""

    def __init__(self, llm_router):
        super().__init__("llm_services")
        self.llm_router = llm_router

    async def _perform_check(self) -> tuple[HealthStatus, str, Optional[dict[str, Any]]]:
        """Check LLM service availability"""
        try:
            # Test with a simple prompt
            test_prompt = "Health check: respond with 'OK'"
            response = await asyncio.wait_for(
                self.llm_router.route_request(test_prompt, {"test": True}),
                timeout=self.timeout_ms / 1000
            )

            if response and "OK" in response.content:
                return HealthStatus.HEALTHY, "LLM services responding", {
                    "model_used": response.model_id,
                    "latency_ms": response.latency_ms
                }
            else:
                return HealthStatus.DEGRADED, "LLM services responding but unexpected output", {
                    "response": response.content if response else None
                }

        except asyncio.TimeoutError:
            return HealthStatus.UNHEALTHY, "LLM services timeout", None
        except Exception as e:
            return HealthStatus.UNHEALTHY, f"LLM services error: {str(e)}", None


class SystemResourceHealthCheck(HealthCheck):
    """Health check for system resources (CPU, Memory, Disk)"""

    def __init__(self, cpu_threshold: float = 90.0, memory_threshold: float = 90.0, disk_threshold: float = 90.0):
        super().__init__("system_resources")
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.disk_threshold = disk_threshold

    async def _perform_check(self) -> tuple[HealthStatus, str, Optional[dict[str, Any]]]:
        """Check system resource usage"""
        try:
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            details = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "disk_percent": (disk.used / disk.total) * 100,
                "disk_free_gb": disk.free / (1024**3)
            }

            # Check thresholds
            issues = []
            if cpu_percent > self.cpu_threshold:
                issues.append(f"CPU usage {cpu_percent:.1f}% > {self.cpu_threshold}%")
            if memory.percent > self.memory_threshold:
                issues.append(f"Memory usage {memory.percent:.1f}% > {self.memory_threshold}%")
            if (disk.used / disk.total) * 100 > self.disk_threshold:
                issues.append(f"Disk usage {(disk.used / disk.total) * 100:.1f}% > {self.disk_threshold}%")

            if issues:
                return HealthStatus.DEGRADED, f"Resource issues: {'; '.join(issues)}", details
            else:
                return HealthStatus.HEALTHY, "System resources within normal limits", details

        except Exception as e:
            return HealthStatus.UNHEALTHY, f"System resource check failed: {str(e)}", None


class RiskManagerHealthCheck(HealthCheck):
    """Health check for risk management system"""

    def __init__(self, risk_manager):
        super().__init__("risk_manager")
        self.risk_manager = risk_manager

    async def _perform_check(self) -> tuple[HealthStatus, str, Optional[dict[str, Any]]]:
        """Check risk manager functionality"""
        try:
            # Test risk calculation with dummy data
            from ..signals import Direction, TradingSignal

            test_signal = TradingSignal(
                symbol="BTCUSD",
                direction=Direction.LONG,
                confidence=0.7,
                confluence_score=75.0,
                reasoning="Health check test",
                timeframe_analysis={}
            )

            # Test position size calculation
            position_size = self.risk_manager.calculate_position_size(test_signal, None)

            if position_size > 0:
                return HealthStatus.HEALTHY, "Risk manager functioning normally", {
                    "test_position_size": position_size,
                    "safe_mode": getattr(self.risk_manager, 'safe_mode', False)
                }
            else:
                return HealthStatus.DEGRADED, "Risk manager returned zero position size", None

        except Exception as e:
            return HealthStatus.UNHEALTHY, f"Risk manager check failed: {str(e)}", None


class HealthCheckManager:
    """Manages all health checks and provides aggregated health status"""

    def __init__(self):
        self.health_checks: list[HealthCheck] = []
        self.last_results: dict[str, HealthCheckResult] = {}
        self._lock = threading.RLock()

    def register_health_check(self, health_check: HealthCheck):
        """Register a health check"""
        with self._lock:
            self.health_checks.append(health_check)

    async def check_all(self, timeout_ms: int = 5000) -> dict[str, HealthCheckResult]:
        """Run all health checks concurrently"""
        results = {}

        try:
            # Run all health checks concurrently with timeout
            tasks = [check.check() for check in self.health_checks]
            completed_results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=timeout_ms / 1000
            )

            for i, result in enumerate(completed_results):
                if isinstance(result, Exception):
                    # Handle exceptions from individual health checks
                    check_name = self.health_checks[i].name
                    results[check_name] = HealthCheckResult(
                        component=check_name,
                        status=HealthStatus.UNHEALTHY,
                        message=f"Health check exception: {str(result)}",
                        response_time_ms=0.0,
                        timestamp=datetime.now(UTC)
                    )
                else:
                    results[result.component] = result

        except asyncio.TimeoutError:
            # Handle overall timeout
            for check in self.health_checks:
                if check.name not in results:
                    results[check.name] = HealthCheckResult(
                        component=check.name,
                        status=HealthStatus.UNKNOWN,
                        message="Health check timed out",
                        response_time_ms=timeout_ms,
                        timestamp=datetime.now(UTC)
                    )

        with self._lock:
            self.last_results = results

        return results

    def get_overall_status(self) -> HealthStatus:
        """Get overall system health status"""
        with self._lock:
            if not self.last_results:
                return HealthStatus.UNKNOWN

            statuses = [result.status for result in self.last_results.values()]

            if any(status == HealthStatus.UNHEALTHY for status in statuses):
                return HealthStatus.UNHEALTHY
            elif any(status == HealthStatus.DEGRADED for status in statuses):
                return HealthStatus.DEGRADED
            elif all(status == HealthStatus.HEALTHY for status in statuses):
                return HealthStatus.HEALTHY
            else:
                return HealthStatus.UNKNOWN

    def get_health_summary(self) -> dict[str, Any]:
        """Get comprehensive health summary"""
        with self._lock:
            overall_status = self.get_overall_status()

            component_statuses = {}
            total_response_time = 0.0

            for name, result in self.last_results.items():
                component_statuses[name] = {
                    'status': result.status.value,
                    'message': result.message,
                    'response_time_ms': result.response_time_ms
                }
                total_response_time += result.response_time_ms

            return {
                'overall_status': overall_status.value,
                'timestamp': datetime.now(UTC).isoformat(),
                'total_response_time_ms': total_response_time,
                'component_count': len(self.last_results),
                'components': component_statuses
            }

    def get_health_endpoint_response(self) -> tuple[dict[str, Any], int]:
        """Get health check response suitable for HTTP endpoint"""
        summary = self.get_health_summary()

        # Determine HTTP status code based on overall health
        status_code_map = {
            HealthStatus.HEALTHY: 200,
            HealthStatus.DEGRADED: 200,  # Still operational
            HealthStatus.UNHEALTHY: 503,  # Service unavailable
            HealthStatus.UNKNOWN: 503
        }

        overall_status = HealthStatus(summary['overall_status'])
        status_code = status_code_map[overall_status]

        return summary, status_code


# Global health check manager
_health_manager: Optional[HealthCheckManager] = None


def get_health_manager() -> HealthCheckManager:
    """Get global health check manager instance"""
    global _health_manager
    if _health_manager is None:
        _health_manager = HealthCheckManager()
    return _health_manager


def setup_default_health_checks(
    db_connection_func: Optional[Callable] = None,
    market_data_url: Optional[str] = None,
    execution_gateway_url: Optional[str] = None,
    llm_router = None,
    risk_manager = None
):
    """Setup default health checks for the trading system"""
    manager = get_health_manager()

    # System resources (always available)
    manager.register_health_check(SystemResourceHealthCheck())

    # Database health check
    if db_connection_func:
        manager.register_health_check(DatabaseHealthCheck(db_connection_func))

    # Market data health check
    if market_data_url:
        manager.register_health_check(MarketDataHealthCheck(market_data_url))

    # Execution gateway health check
    if execution_gateway_url:
        manager.register_health_check(ExecutionGatewayHealthCheck(execution_gateway_url))

    # LLM health check
    if llm_router:
        manager.register_health_check(LLMHealthCheck(llm_router))

    # Risk manager health check
    if risk_manager:
        manager.register_health_check(RiskManagerHealthCheck(risk_manager))

    logger.info(f"Registered {len(manager.health_checks)} health checks")


async def run_health_checks() -> dict[str, Any]:
    """Run all health checks and return summary"""
    manager = get_health_manager()
    await manager.check_all()
    return manager.get_health_summary()


# Utility function for timezone handling
def ensure_utc_timezone(dt: datetime) -> datetime:
    """Ensure datetime has UTC timezone for consistent comparisons"""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)
