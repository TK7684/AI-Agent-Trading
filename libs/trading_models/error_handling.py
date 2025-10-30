"""
Error handling and self-recovery system for the autonomous trading system.

This module provides comprehensive error classification, recovery strategies,
circuit breaker patterns, and incident detection capabilities.
"""

import asyncio
import logging
import time
import traceback
from abc import ABC, abstractmethod
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Classification of error types in the trading system."""

    DATA = "data"
    RISK = "risk"
    EXECUTION = "execution"
    LLM = "llm"
    SYSTEM = "system"
    NETWORK = "network"


class ErrorSeverity(Enum):
    """Severity levels for errors."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecoveryAction(Enum):
    """Types of recovery actions that can be taken."""

    RETRY = "retry"
    FALLBACK = "fallback"
    RESET = "reset"
    ESCALATE = "escalate"
    IGNORE = "ignore"
    SAFE_MODE = "safe_mode"
    RESTART = "restart"


@dataclass
class ErrorContext:
    """Context information for an error occurrence."""

    error_type: ErrorType
    severity: ErrorSeverity
    message: str
    exception: Optional[Exception] = None
    component: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)
    stack_trace: Optional[str] = None

    def __post_init__(self):
        if self.exception and not self.stack_trace:
            self.stack_trace = traceback.format_exc()


@dataclass
class RecoveryStrategy:
    """Defines a recovery strategy for a specific error type."""

    action: RecoveryAction
    max_retries: int = 3
    retry_delay: float = 1.0
    backoff_multiplier: float = 2.0
    timeout: float = 30.0
    fallback_strategy: Optional["RecoveryStrategy"] = None
    conditions: dict[str, Any] = field(default_factory=dict)


class CircuitBreakerState(Enum):
    """States of a circuit breaker."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""

    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    success_threshold: int = 3
    timeout: float = 30.0


class CircuitBreaker:
    """Circuit breaker implementation for external service failures."""

    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.next_attempt_time: Optional[datetime] = None

    def can_execute(self) -> bool:
        """Check if the circuit breaker allows execution."""
        now = datetime.now(UTC)

        if self.state == CircuitBreakerState.CLOSED:
            return True
        elif self.state == CircuitBreakerState.OPEN:
            if self.next_attempt_time and now >= self.next_attempt_time:
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
                return True
            return False
        elif self.state == CircuitBreakerState.HALF_OPEN:
            return True

        return False

    def record_success(self):
        """Record a successful operation."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                self.success_count = 0
        elif self.state == CircuitBreakerState.CLOSED:
            self.failure_count = max(0, self.failure_count - 1)

    def record_failure(self):
        """Record a failed operation."""
        self.failure_count += 1
        self.last_failure_time = datetime.now(UTC)

        if self.state == CircuitBreakerState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                self.state = CircuitBreakerState.OPEN
                self.next_attempt_time = datetime.now(UTC) + timedelta(
                    seconds=self.config.recovery_timeout
                )
        elif self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            self.next_attempt_time = datetime.now(UTC) + timedelta(
                seconds=self.config.recovery_timeout
            )

    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute a function with circuit breaker protection."""
        if not self.can_execute():
            raise CircuitBreakerOpenError(f"Circuit breaker {self.name} is open")

        try:
            result = await asyncio.wait_for(
                func(*args, **kwargs), timeout=self.config.timeout
            )
            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            raise e


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""

    pass


class ErrorHandler(ABC):
    """Abstract base class for error handlers."""

    @abstractmethod
    def can_handle(self, error_context: ErrorContext) -> bool:
        """Check if this handler can handle the given error."""
        pass

    @abstractmethod
    async def handle(self, error_context: ErrorContext) -> RecoveryAction:
        """Handle the error and return the recovery action taken."""
        pass


class DataErrorHandler(ErrorHandler):
    """Handler for data-related errors."""

    def can_handle(self, error_context: ErrorContext) -> bool:
        return error_context.error_type == ErrorType.DATA

    async def handle(self, error_context: ErrorContext) -> RecoveryAction:
        """Handle data errors with appropriate recovery strategies."""
        logger.warning(f"Handling data error: {error_context.message}")

        if "timeout" in error_context.message.lower():
            # Retry with exponential backoff for timeouts
            return RecoveryAction.RETRY
        elif "invalid" in error_context.message.lower():
            # Use fallback data source for invalid data
            return RecoveryAction.FALLBACK
        elif "missing" in error_context.message.lower():
            # Reset data adapter for missing data
            return RecoveryAction.RESET
        else:
            # Default to retry for other data errors
            return RecoveryAction.RETRY


class RiskErrorHandler(ErrorHandler):
    """Handler for risk management errors."""

    def can_handle(self, error_context: ErrorContext) -> bool:
        return error_context.error_type == ErrorType.RISK

    async def handle(self, error_context: ErrorContext) -> RecoveryAction:
        """Handle risk errors with safety-first approach."""
        logger.error(f"Handling risk error: {error_context.message}")

        if error_context.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            # Trigger safe mode for high severity risk errors
            return RecoveryAction.SAFE_MODE
        elif "limit" in error_context.message.lower():
            # Ignore trades that violate limits
            return RecoveryAction.IGNORE
        else:
            # Escalate other risk errors
            return RecoveryAction.ESCALATE


class ExecutionErrorHandler(ErrorHandler):
    """Handler for execution-related errors."""

    def can_handle(self, error_context: ErrorContext) -> bool:
        return error_context.error_type == ErrorType.EXECUTION

    async def handle(self, error_context: ErrorContext) -> RecoveryAction:
        """Handle execution errors with retry and fallback strategies."""
        logger.warning(f"Handling execution error: {error_context.message}")

        if "connection" in error_context.message.lower():
            # Reset connection for connection errors
            return RecoveryAction.RESET
        elif "rate limit" in error_context.message.lower():
            # Retry with delay for rate limits
            return RecoveryAction.RETRY
        elif "insufficient" in error_context.message.lower():
            # Ignore orders with insufficient funds
            return RecoveryAction.IGNORE
        else:
            # Default to retry for other execution errors
            return RecoveryAction.RETRY


class LLMErrorHandler(ErrorHandler):
    """Handler for LLM-related errors."""

    def can_handle(self, error_context: ErrorContext) -> bool:
        return error_context.error_type == ErrorType.LLM

    async def handle(self, error_context: ErrorContext) -> RecoveryAction:
        """Handle LLM errors with model switching and fallback."""
        logger.warning(f"Handling LLM error: {error_context.message}")

        if "timeout" in error_context.message.lower():
            # Switch to faster model for timeouts
            return RecoveryAction.FALLBACK
        elif "rate limit" in error_context.message.lower():
            # Switch to different model for rate limits
            return RecoveryAction.FALLBACK
        elif "invalid" in error_context.message.lower():
            # Retry with different prompt for invalid responses
            return RecoveryAction.RETRY
        else:
            # Default to fallback for other LLM errors
            return RecoveryAction.FALLBACK


class SystemErrorHandler(ErrorHandler):
    """Handler for system-level errors."""

    def can_handle(self, error_context: ErrorContext) -> bool:
        return error_context.error_type == ErrorType.SYSTEM

    async def handle(self, error_context: ErrorContext) -> RecoveryAction:
        """Handle system errors with restart and escalation."""
        logger.error(f"Handling system error: {error_context.message}")

        if error_context.severity == ErrorSeverity.CRITICAL:
            # Restart for critical system errors
            return RecoveryAction.RESTART
        else:
            # Escalate other system errors
            return RecoveryAction.ESCALATE


@dataclass
class IncidentReport:
    """Report of an incident and recovery actions taken."""

    incident_id: str
    error_context: ErrorContext
    recovery_actions: list[RecoveryAction]
    resolution_time: Optional[datetime] = None
    success: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


class ErrorRecoverySystem:
    """Main error recovery system that coordinates all error handling."""

    def __init__(self):
        self.handlers: list[ErrorHandler] = [
            DataErrorHandler(),
            RiskErrorHandler(),
            ExecutionErrorHandler(),
            LLMErrorHandler(),
            SystemErrorHandler(),
        ]
        self.circuit_breakers: dict[str, CircuitBreaker] = {}
        self.incident_reports: list[IncidentReport] = []
        self.recovery_strategies: dict[ErrorType, RecoveryStrategy] = {
            ErrorType.DATA: RecoveryStrategy(
                action=RecoveryAction.RETRY,
                max_retries=3,
                retry_delay=1.0,
                backoff_multiplier=2.0,
            ),
            ErrorType.RISK: RecoveryStrategy(
                action=RecoveryAction.SAFE_MODE, max_retries=1
            ),
            ErrorType.EXECUTION: RecoveryStrategy(
                action=RecoveryAction.RETRY,
                max_retries=5,
                retry_delay=0.5,
                backoff_multiplier=1.5,
            ),
            ErrorType.LLM: RecoveryStrategy(
                action=RecoveryAction.FALLBACK, max_retries=2, retry_delay=2.0
            ),
            ErrorType.SYSTEM: RecoveryStrategy(
                action=RecoveryAction.ESCALATE, max_retries=1
            ),
        }

    def add_circuit_breaker(self, name: str, config: CircuitBreakerConfig):
        """Add a circuit breaker for a specific service."""
        self.circuit_breakers[name] = CircuitBreaker(name, config)

    def get_circuit_breaker(self, name: str) -> Optional[CircuitBreaker]:
        """Get a circuit breaker by name."""
        return self.circuit_breakers.get(name)

    async def handle_error(self, error_context: ErrorContext) -> IncidentReport:
        """Handle an error and return an incident report."""
        incident_id = f"incident_{int(time.time() * 1000)}"
        incident_report = IncidentReport(
            incident_id=incident_id, error_context=error_context, recovery_actions=[]
        )

        logger.error(f"Handling error {incident_id}: {error_context.message}")

        try:
            # Find appropriate handler
            handler = None
            for h in self.handlers:
                if h.can_handle(error_context):
                    handler = h
                    break

            if not handler:
                logger.error(
                    f"No handler found for error type: {error_context.error_type}"
                )
                incident_report.recovery_actions.append(RecoveryAction.ESCALATE)
                return incident_report

            # Execute recovery strategy
            strategy = self.recovery_strategies.get(error_context.error_type)
            if strategy:
                success = await self._execute_recovery_strategy(
                    handler, error_context, strategy, incident_report
                )
                incident_report.success = success
            else:
                # Fallback to handler's default action
                action = await handler.handle(error_context)
                incident_report.recovery_actions.append(action)
                incident_report.success = True

            incident_report.resolution_time = datetime.now(UTC)

        except Exception as e:
            logger.error(f"Error during error handling: {e}")
            incident_report.recovery_actions.append(RecoveryAction.ESCALATE)
            incident_report.success = False

        self.incident_reports.append(incident_report)
        return incident_report

    async def _execute_recovery_strategy(
        self,
        handler: ErrorHandler,
        error_context: ErrorContext,
        strategy: RecoveryStrategy,
        incident_report: IncidentReport,
    ) -> bool:
        """Execute a recovery strategy with retries and backoff."""
        delay = strategy.retry_delay

        for attempt in range(strategy.max_retries + 1):
            try:
                action = await handler.handle(error_context)
                incident_report.recovery_actions.append(action)

                if action in [
                    RecoveryAction.IGNORE,
                    RecoveryAction.ESCALATE,
                    RecoveryAction.SAFE_MODE,
                ]:
                    # These actions don't require retries
                    return True

                # Simulate recovery action execution
                await self._execute_recovery_action(action, error_context)
                return True

            except Exception as e:
                logger.warning(f"Recovery attempt {attempt + 1} failed: {e}")
                if attempt < strategy.max_retries:
                    await asyncio.sleep(delay)
                    delay *= strategy.backoff_multiplier
                else:
                    # Try fallback strategy if available
                    if strategy.fallback_strategy:
                        return await self._execute_recovery_strategy(
                            handler,
                            error_context,
                            strategy.fallback_strategy,
                            incident_report,
                        )
                    return False

        return False

    async def _execute_recovery_action(
        self, action: RecoveryAction, error_context: ErrorContext
    ):
        """Execute a specific recovery action."""
        logger.info(f"Executing recovery action: {action}")

        if action == RecoveryAction.RETRY:
            # Simulate retry logic
            await asyncio.sleep(0.1)
        elif action == RecoveryAction.FALLBACK:
            # Simulate fallback to alternative service
            await asyncio.sleep(0.1)
        elif action == RecoveryAction.RESET:
            # Simulate component reset
            await asyncio.sleep(0.2)
        elif action == RecoveryAction.SAFE_MODE:
            # Trigger safe mode
            logger.critical("Triggering safe mode due to error")
        elif action == RecoveryAction.RESTART:
            # Simulate component restart
            logger.warning("Restarting component")
            await asyncio.sleep(0.5)
        elif action == RecoveryAction.ESCALATE:
            # Escalate to human operators
            logger.critical(f"Escalating error: {error_context.message}")

    def get_incident_statistics(self) -> dict[str, Any]:
        """Get statistics about handled incidents."""
        if not self.incident_reports:
            return {}

        total_incidents = len(self.incident_reports)
        successful_recoveries = sum(
            1 for report in self.incident_reports if report.success
        )

        error_type_counts = {}
        recovery_action_counts = {}

        for report in self.incident_reports:
            error_type = report.error_context.error_type.value
            error_type_counts[error_type] = error_type_counts.get(error_type, 0) + 1

            for action in report.recovery_actions:
                action_name = action.value
                recovery_action_counts[action_name] = (
                    recovery_action_counts.get(action_name, 0) + 1
                )

        return {
            "total_incidents": total_incidents,
            "successful_recoveries": successful_recoveries,
            "success_rate": successful_recoveries / total_incidents
            if total_incidents > 0
            else 0,
            "error_type_distribution": error_type_counts,
            "recovery_action_distribution": recovery_action_counts,
        }


# Context manager for error handling
@asynccontextmanager
async def error_context(
    error_recovery_system: ErrorRecoverySystem,
    component: str,
    error_type: ErrorType = ErrorType.SYSTEM,
):
    """Context manager for automatic error handling."""
    try:
        yield
    except Exception as e:
        error_ctx = ErrorContext(
            error_type=error_type,
            severity=ErrorSeverity.MEDIUM,
            message=str(e),
            exception=e,
            component=component,
        )
        await error_recovery_system.handle_error(error_ctx)
        raise


# Global error recovery system instance
error_recovery_system = ErrorRecoverySystem()


def safe_execute(
    func,
    error_recovery: ErrorRecoverySystem = error_recovery_system,
    component: str = "unknown",
    error_type: ErrorType = ErrorType.SYSTEM,
    default_return=None,
):
    """Decorator for safe function execution with error handling."""

    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            error_ctx = ErrorContext(
                error_type=error_type,
                severity=ErrorSeverity.MEDIUM,
                message=f"Error in {component}: {str(e)}",
                exception=e,
                component=component,
            )
            await error_recovery.handle_error(error_ctx)
            return default_return

    return wrapper


async def safe_execute_sync(
    func,
    *args,
    error_recovery: ErrorRecoverySystem = error_recovery_system,
    component: str = "unknown",
    error_type: ErrorType = ErrorType.SYSTEM,
    default_return=None,
    **kwargs,
):
    """Execute synchronous function safely with error handling."""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        error_ctx = ErrorContext(
            error_type=error_type,
            severity=ErrorSeverity.MEDIUM,
            message=f"Error in {component}: {str(e)}",
            exception=e,
            component=component,
        )
        await error_recovery.handle_error(error_ctx)
        return default_return


def log_error(
    message: str,
    error_type: ErrorType = ErrorType.SYSTEM,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    component: str = "unknown",
    exception: Optional[Exception] = None,
):
    """Utility function for consistent error logging."""
    error_ctx = ErrorContext(
        error_type=error_type,
        severity=severity,
        message=message,
        exception=exception,
        component=component,
    )
    logger.error(f"[{component}] {message}", exc_info=exception)
    return error_ctx


async def with_timeout(
    func,
    timeout_seconds: float = 30.0,
    error_recovery: ErrorRecoverySystem = error_recovery_system,
    component: str = "unknown",
):
    """Execute function with timeout and error handling."""
    try:
        return await asyncio.wait_for(func, timeout=timeout_seconds)
    except asyncio.TimeoutError as e:
        error_ctx = ErrorContext(
            error_type=ErrorType.SYSTEM,
            severity=ErrorSeverity.HIGH,
            message=f"Timeout in {component} after {timeout_seconds}s",
            exception=e,
            component=component,
        )
        await error_recovery.handle_error(error_ctx)
        raise
    except Exception as e:
        error_ctx = ErrorContext(
            error_type=ErrorType.SYSTEM,
            severity=ErrorSeverity.MEDIUM,
            message=f"Error in {component}: {str(e)}",
            exception=e,
            component=component,
        )
        await error_recovery.handle_error(error_ctx)
        raise
