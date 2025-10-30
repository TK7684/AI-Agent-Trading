"""
Tests for the error handling and self-recovery system.
"""

import asyncio
from datetime import datetime
from unittest.mock import Mock

import pytest

from libs.trading_models.error_handling import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    DataErrorHandler,
    ErrorContext,
    ErrorRecoverySystem,
    ErrorSeverity,
    ErrorType,
    ExecutionErrorHandler,
    IncidentReport,
    LLMErrorHandler,
    RecoveryAction,
    RecoveryStrategy,
    RiskErrorHandler,
    SystemErrorHandler,
    error_context,
)


class TestErrorContext:
    """Test ErrorContext functionality."""

    def test_error_context_creation(self):
        """Test creating an error context."""
        error_ctx = ErrorContext(
            error_type=ErrorType.DATA,
            severity=ErrorSeverity.HIGH,
            message="Test error",
            component="test_component"
        )

        assert error_ctx.error_type == ErrorType.DATA
        assert error_ctx.severity == ErrorSeverity.HIGH
        assert error_ctx.message == "Test error"
        assert error_ctx.component == "test_component"
        assert isinstance(error_ctx.timestamp, datetime)

    def test_error_context_with_exception(self):
        """Test error context with exception."""
        try:
            raise ValueError("Test exception")
        except ValueError as e:
            error_ctx = ErrorContext(
                error_type=ErrorType.SYSTEM,
                severity=ErrorSeverity.CRITICAL,
                message="System error",
                exception=e
            )

            assert error_ctx.exception == e
            assert error_ctx.stack_trace is not None
            assert "ValueError" in error_ctx.stack_trace


class TestCircuitBreaker:
    """Test CircuitBreaker functionality."""

    def test_circuit_breaker_creation(self):
        """Test creating a circuit breaker."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=60.0,
            success_threshold=2
        )
        cb = CircuitBreaker("test_service", config)

        assert cb.name == "test_service"
        assert cb.config == config
        assert cb.state.value == "closed"
        assert cb.failure_count == 0

    def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in closed state."""
        config = CircuitBreakerConfig(failure_threshold=3)
        cb = CircuitBreaker("test", config)

        assert cb.can_execute() is True

        # Record some failures (below threshold)
        cb.record_failure()
        cb.record_failure()
        assert cb.can_execute() is True
        assert cb.failure_count == 2

    def test_circuit_breaker_opens_on_threshold(self):
        """Test circuit breaker opens when failure threshold is reached."""
        config = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=1.0)
        cb = CircuitBreaker("test", config)

        # Reach failure threshold
        for _ in range(3):
            cb.record_failure()

        assert cb.state.value == "open"
        assert cb.can_execute() is False

    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovery after timeout."""
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=0.1)
        cb = CircuitBreaker("test", config)

        # Open the circuit breaker
        cb.record_failure()
        cb.record_failure()
        assert cb.state.value == "open"

        # Wait for recovery timeout
        await asyncio.sleep(0.2)

        # Should transition to half-open
        assert cb.can_execute() is True
        assert cb.state.value == "half_open"

    def test_circuit_breaker_half_open_success(self):
        """Test circuit breaker transitions from half-open to closed on success."""
        config = CircuitBreakerConfig(failure_threshold=2, success_threshold=2)
        cb = CircuitBreaker("test", config)

        # Open the circuit breaker
        cb.record_failure()
        cb.record_failure()

        # Manually set to half-open
        cb.state = cb.state.HALF_OPEN

        # Record successes
        cb.record_success()
        assert cb.state.value == "half_open"

        cb.record_success()
        assert cb.state.value == "closed"
        assert cb.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_execute_success(self):
        """Test successful execution through circuit breaker."""
        config = CircuitBreakerConfig()
        cb = CircuitBreaker("test", config)

        async def test_func():
            return "success"

        result = await cb.execute(test_func)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_circuit_breaker_execute_failure(self):
        """Test failed execution through circuit breaker."""
        config = CircuitBreakerConfig(failure_threshold=1)
        cb = CircuitBreaker("test", config)

        async def failing_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            await cb.execute(failing_func)

        assert cb.failure_count == 1
        assert cb.state.value == "open"

    @pytest.mark.asyncio
    async def test_circuit_breaker_execute_when_open(self):
        """Test execution when circuit breaker is open."""
        config = CircuitBreakerConfig(failure_threshold=1)
        cb = CircuitBreaker("test", config)

        # Open the circuit breaker
        cb.record_failure()

        async def test_func():
            return "success"

        with pytest.raises(CircuitBreakerOpenError):
            await cb.execute(test_func)


class TestErrorHandlers:
    """Test error handler implementations."""

    def test_data_error_handler(self):
        """Test DataErrorHandler."""
        handler = DataErrorHandler()

        # Test can_handle
        data_error = ErrorContext(ErrorType.DATA, ErrorSeverity.MEDIUM, "Data error")
        risk_error = ErrorContext(ErrorType.RISK, ErrorSeverity.HIGH, "Risk error")

        assert handler.can_handle(data_error) is True
        assert handler.can_handle(risk_error) is False

    @pytest.mark.asyncio
    async def test_data_error_handler_timeout(self):
        """Test DataErrorHandler handles timeout errors."""
        handler = DataErrorHandler()
        error_ctx = ErrorContext(ErrorType.DATA, ErrorSeverity.MEDIUM, "Connection timeout")

        action = await handler.handle(error_ctx)
        assert action == RecoveryAction.RETRY

    @pytest.mark.asyncio
    async def test_data_error_handler_invalid_data(self):
        """Test DataErrorHandler handles invalid data errors."""
        handler = DataErrorHandler()
        error_ctx = ErrorContext(ErrorType.DATA, ErrorSeverity.MEDIUM, "Invalid data format")

        action = await handler.handle(error_ctx)
        assert action == RecoveryAction.FALLBACK

    def test_risk_error_handler(self):
        """Test RiskErrorHandler."""
        handler = RiskErrorHandler()

        risk_error = ErrorContext(ErrorType.RISK, ErrorSeverity.HIGH, "Risk limit exceeded")
        assert handler.can_handle(risk_error) is True

    @pytest.mark.asyncio
    async def test_risk_error_handler_critical(self):
        """Test RiskErrorHandler handles critical errors."""
        handler = RiskErrorHandler()
        error_ctx = ErrorContext(ErrorType.RISK, ErrorSeverity.CRITICAL, "Critical risk violation")

        action = await handler.handle(error_ctx)
        assert action == RecoveryAction.SAFE_MODE

    @pytest.mark.asyncio
    async def test_risk_error_handler_limit_violation(self):
        """Test RiskErrorHandler handles limit violations."""
        handler = RiskErrorHandler()
        error_ctx = ErrorContext(ErrorType.RISK, ErrorSeverity.MEDIUM, "Position limit exceeded")

        action = await handler.handle(error_ctx)
        assert action == RecoveryAction.IGNORE

    def test_execution_error_handler(self):
        """Test ExecutionErrorHandler."""
        handler = ExecutionErrorHandler()

        exec_error = ErrorContext(ErrorType.EXECUTION, ErrorSeverity.MEDIUM, "Order failed")
        assert handler.can_handle(exec_error) is True

    @pytest.mark.asyncio
    async def test_execution_error_handler_connection(self):
        """Test ExecutionErrorHandler handles connection errors."""
        handler = ExecutionErrorHandler()
        error_ctx = ErrorContext(ErrorType.EXECUTION, ErrorSeverity.MEDIUM, "Connection lost")

        action = await handler.handle(error_ctx)
        assert action == RecoveryAction.RESET

    @pytest.mark.asyncio
    async def test_execution_error_handler_rate_limit(self):
        """Test ExecutionErrorHandler handles rate limit errors."""
        handler = ExecutionErrorHandler()
        error_ctx = ErrorContext(ErrorType.EXECUTION, ErrorSeverity.MEDIUM, "Rate limit exceeded")

        action = await handler.handle(error_ctx)
        assert action == RecoveryAction.RETRY

    def test_llm_error_handler(self):
        """Test LLMErrorHandler."""
        handler = LLMErrorHandler()

        llm_error = ErrorContext(ErrorType.LLM, ErrorSeverity.MEDIUM, "LLM timeout")
        assert handler.can_handle(llm_error) is True

    @pytest.mark.asyncio
    async def test_llm_error_handler_timeout(self):
        """Test LLMErrorHandler handles timeout errors."""
        handler = LLMErrorHandler()
        error_ctx = ErrorContext(ErrorType.LLM, ErrorSeverity.MEDIUM, "Request timeout")

        action = await handler.handle(error_ctx)
        assert action == RecoveryAction.FALLBACK

    @pytest.mark.asyncio
    async def test_llm_error_handler_rate_limit(self):
        """Test LLMErrorHandler handles rate limit errors."""
        handler = LLMErrorHandler()
        error_ctx = ErrorContext(ErrorType.LLM, ErrorSeverity.MEDIUM, "Rate limit exceeded")

        action = await handler.handle(error_ctx)
        assert action == RecoveryAction.FALLBACK

    def test_system_error_handler(self):
        """Test SystemErrorHandler."""
        handler = SystemErrorHandler()

        system_error = ErrorContext(ErrorType.SYSTEM, ErrorSeverity.HIGH, "System failure")
        assert handler.can_handle(system_error) is True

    @pytest.mark.asyncio
    async def test_system_error_handler_critical(self):
        """Test SystemErrorHandler handles critical errors."""
        handler = SystemErrorHandler()
        error_ctx = ErrorContext(ErrorType.SYSTEM, ErrorSeverity.CRITICAL, "Critical system failure")

        action = await handler.handle(error_ctx)
        assert action == RecoveryAction.RESTART


class TestErrorRecoverySystem:
    """Test ErrorRecoverySystem functionality."""

    def test_error_recovery_system_creation(self):
        """Test creating an error recovery system."""
        ers = ErrorRecoverySystem()

        assert len(ers.handlers) == 5  # All handler types
        assert len(ers.recovery_strategies) == 5  # All error types
        assert len(ers.incident_reports) == 0

    def test_add_circuit_breaker(self):
        """Test adding a circuit breaker."""
        ers = ErrorRecoverySystem()
        config = CircuitBreakerConfig()

        ers.add_circuit_breaker("test_service", config)

        cb = ers.get_circuit_breaker("test_service")
        assert cb is not None
        assert cb.name == "test_service"

    @pytest.mark.asyncio
    async def test_handle_data_error(self):
        """Test handling a data error."""
        ers = ErrorRecoverySystem()

        error_ctx = ErrorContext(
            error_type=ErrorType.DATA,
            severity=ErrorSeverity.MEDIUM,
            message="Data timeout",
            component="market_data"
        )

        incident_report = await ers.handle_error(error_ctx)

        assert incident_report.error_context == error_ctx
        assert len(incident_report.recovery_actions) > 0
        assert incident_report.resolution_time is not None
        assert len(ers.incident_reports) == 1

    @pytest.mark.asyncio
    async def test_handle_risk_error(self):
        """Test handling a risk error."""
        ers = ErrorRecoverySystem()

        error_ctx = ErrorContext(
            error_type=ErrorType.RISK,
            severity=ErrorSeverity.CRITICAL,
            message="Critical risk violation",
            component="risk_manager"
        )

        incident_report = await ers.handle_error(error_ctx)

        assert RecoveryAction.SAFE_MODE in incident_report.recovery_actions
        assert incident_report.success is True

    @pytest.mark.asyncio
    async def test_handle_unknown_error_type(self):
        """Test handling an error with no specific handler."""
        ers = ErrorRecoverySystem()

        # Create a custom error context that won't match any handler
        error_ctx = ErrorContext(
            error_type=ErrorType.NETWORK,  # Not handled by default handlers
            severity=ErrorSeverity.MEDIUM,
            message="Network error",
            component="network"
        )

        incident_report = await ers.handle_error(error_ctx)

        assert RecoveryAction.ESCALATE in incident_report.recovery_actions
        assert incident_report.success is False

    @pytest.mark.asyncio
    async def test_recovery_strategy_with_retries(self):
        """Test recovery strategy with multiple retries."""
        ers = ErrorRecoverySystem()

        # Mock a handler that fails initially then succeeds
        mock_handler = Mock()
        mock_handler.can_handle.return_value = True

        call_count = 0
        async def mock_handle(error_ctx):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return RecoveryAction.RETRY

        mock_handler.handle = mock_handle
        ers.handlers = [mock_handler]

        error_ctx = ErrorContext(ErrorType.DATA, ErrorSeverity.MEDIUM, "Test error")

        # Set a strategy with retries
        ers.recovery_strategies[ErrorType.DATA] = RecoveryStrategy(
            action=RecoveryAction.RETRY,
            max_retries=3,
            retry_delay=0.01
        )

        incident_report = await ers.handle_error(error_ctx)

        assert call_count == 3
        assert incident_report.success is True

    def test_get_incident_statistics(self):
        """Test getting incident statistics."""
        ers = ErrorRecoverySystem()

        # Add some mock incident reports
        ers.incident_reports = [
            IncidentReport(
                incident_id="1",
                error_context=ErrorContext(ErrorType.DATA, ErrorSeverity.MEDIUM, "Error 1"),
                recovery_actions=[RecoveryAction.RETRY],
                success=True
            ),
            IncidentReport(
                incident_id="2",
                error_context=ErrorContext(ErrorType.RISK, ErrorSeverity.HIGH, "Error 2"),
                recovery_actions=[RecoveryAction.SAFE_MODE],
                success=True
            ),
            IncidentReport(
                incident_id="3",
                error_context=ErrorContext(ErrorType.DATA, ErrorSeverity.LOW, "Error 3"),
                recovery_actions=[RecoveryAction.RETRY],
                success=False
            )
        ]

        stats = ers.get_incident_statistics()

        assert stats["total_incidents"] == 3
        assert stats["successful_recoveries"] == 2
        assert stats["success_rate"] == 2/3
        assert stats["error_type_distribution"]["data"] == 2
        assert stats["error_type_distribution"]["risk"] == 1
        assert stats["recovery_action_distribution"]["retry"] == 2
        assert stats["recovery_action_distribution"]["safe_mode"] == 1

    def test_get_incident_statistics_empty(self):
        """Test getting statistics with no incidents."""
        ers = ErrorRecoverySystem()

        stats = ers.get_incident_statistics()
        assert stats == {}


class TestErrorContext:
    """Test error context manager."""

    @pytest.mark.asyncio
    async def test_error_context_success(self):
        """Test error context manager with successful operation."""
        ers = ErrorRecoverySystem()

        async with error_context(ers, "test_component", ErrorType.DATA):
            # Successful operation
            pass

        # No incidents should be recorded
        assert len(ers.incident_reports) == 0

    @pytest.mark.asyncio
    async def test_error_context_with_exception(self):
        """Test error context manager with exception."""
        ers = ErrorRecoverySystem()

        with pytest.raises(ValueError):
            async with error_context(ers, "test_component", ErrorType.DATA):
                raise ValueError("Test error")

        # An incident should be recorded
        assert len(ers.incident_reports) == 1
        incident = ers.incident_reports[0]
        assert incident.error_context.component == "test_component"
        assert incident.error_context.error_type == ErrorType.DATA
        assert "Test error" in incident.error_context.message


class TestRecoveryStrategy:
    """Test RecoveryStrategy functionality."""

    def test_recovery_strategy_creation(self):
        """Test creating a recovery strategy."""
        strategy = RecoveryStrategy(
            action=RecoveryAction.RETRY,
            max_retries=5,
            retry_delay=2.0,
            backoff_multiplier=1.5
        )

        assert strategy.action == RecoveryAction.RETRY
        assert strategy.max_retries == 5
        assert strategy.retry_delay == 2.0
        assert strategy.backoff_multiplier == 1.5

    def test_recovery_strategy_with_fallback(self):
        """Test recovery strategy with fallback."""
        fallback_strategy = RecoveryStrategy(action=RecoveryAction.ESCALATE)

        strategy = RecoveryStrategy(
            action=RecoveryAction.RETRY,
            max_retries=3,
            fallback_strategy=fallback_strategy
        )

        assert strategy.fallback_strategy == fallback_strategy
        assert strategy.fallback_strategy.action == RecoveryAction.ESCALATE


@pytest.mark.asyncio
async def test_integration_error_handling_flow():
    """Test complete error handling flow integration."""
    ers = ErrorRecoverySystem()

    # Add a circuit breaker
    cb_config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=0.1)
    ers.add_circuit_breaker("test_service", cb_config)

    # Simulate a series of errors
    errors = [
        ErrorContext(ErrorType.DATA, ErrorSeverity.MEDIUM, "Data timeout", component="data_service"),
        ErrorContext(ErrorType.EXECUTION, ErrorSeverity.HIGH, "Order failed", component="execution"),
        ErrorContext(ErrorType.LLM, ErrorSeverity.MEDIUM, "LLM timeout", component="llm_router"),
        ErrorContext(ErrorType.RISK, ErrorSeverity.CRITICAL, "Risk violation", component="risk_manager")
    ]

    # Handle all errors
    for error_ctx in errors:
        incident_report = await ers.handle_error(error_ctx)
        assert incident_report.incident_id is not None
        assert len(incident_report.recovery_actions) > 0

    # Check statistics
    stats = ers.get_incident_statistics()
    assert stats["total_incidents"] == 4
    assert stats["success_rate"] > 0  # Should have some successful recoveries

    # Verify different error types were handled
    assert len(stats["error_type_distribution"]) > 1
    assert len(stats["recovery_action_distribution"]) > 1
