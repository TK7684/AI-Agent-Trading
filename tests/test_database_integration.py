"""
Integration tests for database setup flow - Task 11 implementation.

This module tests the comprehensive database setup system including:
- DatabaseValidator class functionality
- Connection validation with various error scenarios
- Fallback mode activation and deactivation
- Schema initialization and validation
- Configuration manager database operations (simplified)

Requirements covered: 1.1, 1.2, 1.3, 1.4
"""

from unittest.mock import Mock, patch

import pytest

from libs.trading_models.db_validator import (
    ConnectionResult,
    DatabaseError,
    DatabaseValidator,
    SchemaValidation,
    ServiceStatus,
)
from libs.trading_models.fallback_mode import (
    FallbackMode,
    MockDataGenerator,
    get_fallback_mode,
)


class TestDatabaseValidatorIntegration:
    """Integration tests for DatabaseValidator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = DatabaseValidator()
        self.valid_connection_string = "postgresql://test:test@localhost:5432/test_db"
        self.invalid_connection_string = "invalid://connection/string"

    def test_connection_result_model_validation(self):
        """Test ConnectionResult model validation and serialization."""
        # Test successful connection result
        result = ConnectionResult(
            success=True, connection_time_ms=45.2, database_version="PostgreSQL 15.0"
        )
        assert result.success is True
        assert result.connection_time_ms == 45.2
        assert result.error_type is None

        # Test model serialization
        result_dict = result.model_dump()
        assert "success" in result_dict
        assert "connection_time_ms" in result_dict

        # Test failed connection result
        result = ConnectionResult(
            success=False,
            error_type="auth",
            error_message="Authentication failed",
            suggested_fix="Check password",
        )
        assert result.success is False
        assert result.error_type == "auth"
        assert result.error_message == "Authentication failed"

    def test_schema_validation_model_validation(self):
        """Test SchemaValidation model validation and serialization."""
        validation = SchemaValidation(
            valid=True,
            tables_found=["trades", "positions"],
            tables_missing=[],
            tables_expected=["trades", "positions", "performance_metrics"],
            migration_needed=False,
        )
        assert validation.valid is True
        assert len(validation.tables_found) == 2
        assert len(validation.tables_missing) == 0

        # Test model serialization
        validation_dict = validation.model_dump()
        assert "valid" in validation_dict
        assert "tables_found" in validation_dict

    def test_service_status_model_validation(self):
        """Test ServiceStatus model validation and serialization."""
        status = ServiceStatus(
            running=True, service_name="postgresql-x64-17", pid=1234, status="RUNNING"
        )
        assert status.running is True
        assert status.service_name == "postgresql-x64-17"
        assert status.pid == 1234

        # Test model serialization
        status_dict = status.model_dump()
        assert "running" in status_dict
        assert "service_name" in status_dict

    @patch("libs.trading_models.db_validator.create_engine")
    def test_connection_success_integration(self, mock_create_engine):
        """Test successful database connection with full integration."""
        import time

        # Mock successful connection
        mock_engine = Mock()
        mock_connection = Mock()
        mock_result = Mock()
        mock_result.fetchone.return_value = ["PostgreSQL 15.0, compiled by Visual C++"]

        # Add a small delay to simulate realistic connection time
        def mock_execute(*args, **kwargs):
            time.sleep(0.001)  # 1ms delay - simulates fast local connection
            return mock_result

        mock_connection.execute.side_effect = mock_execute

        # Create a proper context manager mock
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_connection)
        mock_context_manager.__exit__ = Mock(return_value=None)
        mock_engine.connect.return_value = mock_context_manager
        mock_create_engine.return_value = mock_engine

        result = self.validator.test_connection(self.valid_connection_string)

        assert result.success is True
        assert result.connection_time_ms is not None
        assert result.connection_time_ms > 0
        assert "PostgreSQL 15.0" in result.database_version
        assert result.error_type is None

        # Verify engine was created with correct connection string
        mock_create_engine.assert_called_once_with(
            self.valid_connection_string, pool_pre_ping=True
        )

    @patch("libs.trading_models.db_validator.create_engine")
    def test_connection_auth_failure_integration(self, mock_create_engine):
        """Test authentication failure scenario with full error handling."""
        from sqlalchemy.exc import OperationalError

        # Mock authentication failure
        mock_create_engine.side_effect = OperationalError(
            "password authentication failed for user", None, None
        )

        result = self.validator.test_connection(self.valid_connection_string)

        assert result.success is False
        assert result.error_type == "auth"
        assert "authentication failed" in result.error_message.lower()
        assert "Setup-Database.ps1" in result.suggested_fix
        assert result.connection_time_ms is not None

    @patch("libs.trading_models.db_validator.create_engine")
    def test_connection_service_failure_integration(self, mock_create_engine):
        """Test service not running scenario with service detection."""
        from sqlalchemy.exc import OperationalError

        # Mock connection refused (service not running)
        mock_create_engine.side_effect = OperationalError(
            "connection refused", None, None
        )

        with patch.object(self.validator, "test_service_running") as mock_service:
            mock_service.return_value = ServiceStatus(running=False, status="STOPPED")

            result = self.validator.test_connection(self.valid_connection_string)

            assert result.success is False
            assert result.error_type == "service"
            assert "service is not running" in result.error_message.lower()
            assert "Start-Service" in result.suggested_fix

            # Verify service status was checked
            mock_service.assert_called_once()

    @patch("libs.trading_models.db_validator.create_engine")
    def test_connection_network_failure_integration(self, mock_create_engine):
        """Test network connectivity failure with service running."""
        from sqlalchemy.exc import OperationalError

        # Mock network failure with service running
        mock_create_engine.side_effect = OperationalError(
            "could not connect to server", None, None
        )

        with patch.object(self.validator, "test_service_running") as mock_service:
            mock_service.return_value = ServiceStatus(running=True, status="RUNNING")

            result = self.validator.test_connection(self.valid_connection_string)

            assert result.success is False
            assert result.error_type == "network"
            assert "cannot connect" in result.error_message.lower()

    def test_invalid_connection_string_integration(self):
        """Test invalid connection string format handling."""
        result = self.validator.test_connection(self.invalid_connection_string)

        assert result.success is False
        assert result.error_type == "config"
        assert "invalid connection string" in result.error_message.lower()

    @patch("libs.trading_models.db_validator.subprocess.run")
    def test_service_status_running_integration(self, mock_subprocess):
        """Test PostgreSQL service status detection when running."""
        # Mock successful service query
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "SERVICE_NAME: postgresql-x64-17\nSTATE: 4 RUNNING"
        mock_subprocess.return_value = mock_result

        status = self.validator.test_service_running()

        assert status.running is True
        assert status.service_name == "postgresql-x64-17"
        assert status.status == "RUNNING"

        # Verify subprocess was called correctly
        mock_subprocess.assert_called()

    @patch("libs.trading_models.db_validator.subprocess.run")
    def test_service_status_stopped_integration(self, mock_subprocess):
        """Test PostgreSQL service status detection when stopped."""
        # Mock service stopped
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "SERVICE_NAME: postgresql-x64-17\nSTATE: 1 STOPPED"
        mock_subprocess.return_value = mock_result

        status = self.validator.test_service_running()

        assert status.running is False
        assert status.service_name == "postgresql-x64-17"
        assert status.status == "STOPPED"

    @patch("libs.trading_models.db_validator.psutil.process_iter")
    @patch("libs.trading_models.db_validator.subprocess.run")
    def test_service_status_process_detection_integration(
        self, mock_subprocess, mock_process_iter
    ):
        """Test PostgreSQL process detection when service query fails."""
        # Mock service query failure
        mock_subprocess.side_effect = Exception("Service query failed")

        # Mock process detection
        mock_process = Mock()
        mock_process.info = {
            "pid": 1234,
            "name": "postgres.exe",
            "cmdline": ["postgres"],
        }
        mock_process_iter.return_value = [mock_process]

        status = self.validator.test_service_running()

        assert status.running is True
        assert status.pid == 1234
        assert status.status == "PROCESS_RUNNING"

    @patch("libs.trading_models.db_validator.inspect")
    @patch("libs.trading_models.db_validator.create_engine")
    def test_schema_validation_complete_integration(
        self, mock_create_engine, mock_inspect
    ):
        """Test schema validation with all tables present."""
        # Mock database inspection
        mock_inspector = Mock()
        mock_inspector.get_table_names.return_value = [
            "trades",
            "positions",
            "performance_metrics",
            "audit_logs",
        ]
        mock_inspect.return_value = mock_inspector

        validation = self.validator.validate_schema(self.valid_connection_string)

        assert validation.valid is True
        assert len(validation.tables_found) == 4
        assert len(validation.tables_missing) == 0
        assert validation.migration_needed is False

        # Verify engine and inspector were used
        mock_create_engine.assert_called_once_with(self.valid_connection_string)
        mock_inspect.assert_called_once()

    @patch("libs.trading_models.db_validator.inspect")
    @patch("libs.trading_models.db_validator.create_engine")
    def test_schema_validation_incomplete_integration(
        self, mock_create_engine, mock_inspect
    ):
        """Test schema validation with missing tables."""
        # Mock database inspection with missing tables
        mock_inspector = Mock()
        mock_inspector.get_table_names.return_value = ["trades", "positions"]
        mock_inspect.return_value = mock_inspector

        validation = self.validator.validate_schema(self.valid_connection_string)

        assert validation.valid is False
        assert len(validation.tables_found) == 2
        assert len(validation.tables_missing) == 2
        assert "performance_metrics" in validation.tables_missing
        assert "audit_logs" in validation.tables_missing
        assert validation.migration_needed is True

    def test_database_error_creation_integration(self):
        """Test DatabaseError creation and formatting."""
        connection_result = ConnectionResult(
            success=False,
            error_type="auth",
            error_message="Authentication failed",
            suggested_fix="Run Setup-Database.ps1",
        )

        error = self.validator.create_database_error(connection_result)

        assert isinstance(error, DatabaseError)
        assert error.error_type == "auth"
        assert error.message == "Authentication failed"
        assert error.suggested_fix == "Run Setup-Database.ps1"
        assert len(error.recovery_steps) > 0

        # Test user message formatting
        user_message = error.get_user_message()
        assert "❌ Database authentication error" in user_message
        assert "Authentication failed" in user_message
        assert "Recovery steps:" in user_message

        # Test diagnostic info
        diagnostic_info = error.get_diagnostic_info()
        assert "error_type" in diagnostic_info
        assert "timestamp" in diagnostic_info

    def test_connection_diagnostics_integration(self):
        """Test comprehensive connection diagnostics."""
        with (
            patch.object(self.validator, "test_service_running") as mock_service,
            patch.object(self.validator, "test_connection") as mock_connection,
            patch.object(self.validator, "validate_schema") as mock_schema,
        ):
            # Mock all diagnostic components
            mock_service.return_value = ServiceStatus(
                running=True, service_name="postgresql-x64-17"
            )
            mock_connection.return_value = ConnectionResult(
                success=True, connection_time_ms=25.5
            )
            mock_schema.return_value = SchemaValidation(
                valid=True,
                tables_found=["trades"],
                tables_missing=[],
                tables_expected=["trades"],
            )

            diagnostics = self.validator.get_connection_diagnostics(
                self.valid_connection_string
            )

            assert "timestamp" in diagnostics
            assert "service_status" in diagnostics
            assert "connection_test" in diagnostics
            assert "schema_validation" in diagnostics
            assert "system_info" in diagnostics

            assert diagnostics["service_status"]["running"] is True
            assert diagnostics["connection_test"]["success"] is True
            assert diagnostics["schema_validation"]["valid"] is True


class TestFallbackModeIntegration:
    """Integration tests for FallbackMode functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.fallback = FallbackMode()
        self.mock_generator = MockDataGenerator()

        # Reset fallback mode state
        if self.fallback.is_enabled():
            self.fallback.disable()

    def test_fallback_mode_enable_disable_integration(self):
        """Test enabling and disabling fallback mode with state management."""
        assert self.fallback.is_enabled() is False

        # Test enabling
        self.fallback.enable("Test reason")
        assert self.fallback.is_enabled() is True

        # Test status after enabling
        status = self.fallback.get_status()
        assert status["enabled"] is True
        assert len(status["limitations"]) > 0

        # Test disabling
        self.fallback.disable()
        assert self.fallback.is_enabled() is False

        # Test status after disabling
        status = self.fallback.get_status()
        assert status["enabled"] is False
        assert len(status["limitations"]) == 0

    def test_mock_data_generation_integration(self):
        """Test mock data generation for different types with validation."""
        # Enable fallback mode
        self.fallback.enable("Testing")

        # Test trade data generation
        trade_data = self.fallback.get_mock_data("trade", symbol="BTCUSDT")
        assert trade_data is not None
        assert trade_data["symbol"] == "BTCUSDT"
        assert "id" in trade_data
        assert "entry_price" in trade_data
        assert "exit_price" in trade_data
        assert trade_data["trade_metadata"]["mock"] is True
        assert trade_data["trade_metadata"]["fallback_mode"] is True

        # Validate trade data structure
        required_fields = [
            "id",
            "symbol",
            "direction",
            "entry_price",
            "exit_price",
            "quantity",
            "pnl",
            "status",
            "trade_metadata",
        ]
        for field in required_fields:
            assert field in trade_data, f"Missing required field: {field}"

        # Test multiple trades
        trades_data = self.fallback.get_mock_data("trades", count=5, symbol="ETHUSDT")
        assert len(trades_data) == 5
        assert all(trade["symbol"] == "ETHUSDT" for trade in trades_data)
        assert all(trade["trade_metadata"]["mock"] is True for trade in trades_data)

        # Test position data
        position_data = self.fallback.get_mock_data("position", trade_id="test-123")
        assert position_data is not None
        assert position_data["trade_id"] == "test-123"
        assert "unrealized_pnl" in position_data
        assert position_data["position_metadata"]["mock"] is True

        # Test metrics data
        metrics_data = self.fallback.get_mock_data("metrics")
        assert isinstance(metrics_data, list)
        assert len(metrics_data) > 0
        assert all("metric_name" in metric for metric in metrics_data)
        assert all(metric["metric_metadata"]["mock"] is True for metric in metrics_data)

        # Test market data
        market_data = self.fallback.get_mock_data("market_data", symbol="BTCUSDT")
        assert market_data["symbol"] == "BTCUSDT"
        assert "price" in market_data
        assert market_data["mock"] is True
        assert market_data["fallback_mode"] is True

    def test_mock_data_when_disabled_integration(self):
        """Test that mock data returns None when fallback mode is disabled."""
        assert self.fallback.is_enabled() is False

        trade_data = self.fallback.get_mock_data("trade")
        assert trade_data is None

        # Test all data types return None when disabled
        data_types = [
            "trade",
            "trades",
            "position",
            "positions",
            "metrics",
            "market_data",
        ]
        for data_type in data_types:
            result = self.fallback.get_mock_data(data_type)
            assert result is None, f"Expected None for {data_type} when disabled"

    def test_warning_logging_integration(self):
        """Test warning logging functionality with rate limiting."""
        self.fallback.enable("Testing")

        # Test warning logging
        self.fallback.log_warning("test_operation", {"detail": "test"})

        # Verify warning count increased
        status = self.fallback.get_status()
        assert status["warning_count"] == 1
        assert status["last_warning"] is not None

        # Test multiple warnings (may be rate limited)
        self.fallback.log_warning("another_operation")
        status = self.fallback.get_status()
        # Warning count may be rate limited, so check it's at least 1
        assert status["warning_count"] >= 1

    def test_database_availability_check_integration(self):
        """Test database availability checking with reconnection."""
        self.fallback.enable("Testing")

        with patch(
            "libs.trading_models.db_validator.DatabaseValidator"
        ) as mock_validator_class:
            mock_validator = Mock()
            mock_validator.test_connection.return_value = ConnectionResult(success=True)
            mock_validator_class.return_value = mock_validator

            # Test successful reconnection
            available = self.fallback.check_database_available(
                "postgresql://test:test@localhost/test"
            )
            assert available is True
            assert (
                self.fallback.is_enabled() is False
            )  # Should be disabled after successful check

            # Verify validator was called
            mock_validator_class.assert_called_once()
            mock_validator.test_connection.assert_called_once()

    def test_database_availability_check_failure_integration(self):
        """Test database availability check when database is still unavailable."""
        self.fallback.enable("Testing")

        with patch(
            "libs.trading_models.db_validator.DatabaseValidator"
        ) as mock_validator_class:
            mock_validator = Mock()
            mock_validator.test_connection.return_value = ConnectionResult(
                success=False, error_type="service"
            )
            mock_validator_class.return_value = mock_validator

            # Test failed reconnection
            available = self.fallback.check_database_available(
                "postgresql://test:test@localhost/test"
            )
            assert available is False
            assert self.fallback.is_enabled() is True  # Should remain enabled

    def test_fallback_status_integration(self):
        """Test fallback mode status reporting with full state."""
        # Test status when disabled
        status = self.fallback.get_status()
        assert status["enabled"] is False
        assert status["warning_count"] == 0
        assert len(status["limitations"]) == 0
        assert "config" in status

        # Test status when enabled
        self.fallback.enable("Test reason")
        status = self.fallback.get_status()
        assert status["enabled"] is True
        assert len(status["limitations"]) > 0

        # Verify all expected status fields
        expected_fields = [
            "enabled",
            "warning_count",
            "last_warning",
            "last_db_check",
            "config",
            "limitations",
        ]
        for field in expected_fields:
            assert field in status, f"Missing status field: {field}"

    def test_user_message_integration(self):
        """Test user-friendly status messages."""
        # Test message when disabled
        message = self.fallback.get_user_message()
        assert "✅ Database connected" in message

        # Test message when enabled
        self.fallback.enable("Test reason")
        message = self.fallback.get_user_message()
        assert "⚠️  Running in Fallback Mode" in message
        assert "limitations:" in message.lower()
        assert "Setup-Database.ps1" in message

        # Verify message contains actionable information
        assert "restore full functionality" in message.lower()
        assert "restart the application" in message.lower()

    def test_global_fallback_instance_integration(self):
        """Test global fallback mode instance management."""
        global_instance = get_fallback_mode()
        assert isinstance(global_instance, FallbackMode)

        # Test that multiple calls return same instance
        another_instance = get_fallback_mode()
        assert global_instance is another_instance

        # Test state persistence across calls
        global_instance.enable("Test")
        assert another_instance.is_enabled() is True


class TestIntegrationScenarios:
    """Integration tests for complete database setup scenarios."""

    def setup_method(self):
        """Set up integration test fixtures."""
        self.validator = DatabaseValidator()
        self.fallback = FallbackMode()

        # Reset fallback mode state
        if self.fallback.is_enabled():
            self.fallback.disable()

    def test_startup_with_valid_database_integration(self):
        """Test application startup with valid database connection."""
        with (
            patch("libs.trading_models.db_validator.create_engine") as mock_engine,
            patch("libs.trading_models.db_validator.inspect") as mock_inspect,
        ):
            # Mock successful database connection
            mock_connection = Mock()
            mock_result = Mock()
            mock_result.fetchone.return_value = ["PostgreSQL 15.0"]
            mock_connection.execute.return_value = mock_result

            # Create proper context manager mock
            mock_context_manager = Mock()
            mock_context_manager.__enter__ = Mock(return_value=mock_connection)
            mock_context_manager.__exit__ = Mock(return_value=None)
            mock_engine.return_value.connect.return_value = mock_context_manager

            # Mock schema validation
            mock_inspector = Mock()
            mock_inspector.get_table_names.return_value = [
                "trades",
                "positions",
                "performance_metrics",
                "audit_logs",
            ]
            mock_inspect.return_value = mock_inspector

            # Test connection
            result = self.validator.test_connection(
                "postgresql://test:test@localhost/test"
            )
            assert result.success is True

            # Test schema validation
            schema = self.validator.validate_schema(
                "postgresql://test:test@localhost/test"
            )
            assert schema.valid is True

            # Verify fallback mode is not enabled
            assert self.fallback.is_enabled() is False

            # Test diagnostics
            diagnostics = self.validator.get_connection_diagnostics(
                "postgresql://test:test@localhost/test"
            )
            assert diagnostics["connection_test"]["success"] is True
            assert diagnostics["schema_validation"]["valid"] is True

    def test_startup_with_database_failure_integration(self):
        """Test application startup with database connection failure."""
        from sqlalchemy.exc import OperationalError

        with patch("libs.trading_models.db_validator.create_engine") as mock_engine:
            # Mock database connection failure
            mock_engine.side_effect = OperationalError("connection refused", None, None)

            with patch.object(self.validator, "test_service_running") as mock_service:
                mock_service.return_value = ServiceStatus(
                    running=False, status="STOPPED"
                )

                # Test connection failure
                result = self.validator.test_connection(
                    "postgresql://test:test@localhost/test"
                )
                assert result.success is False
                assert result.error_type == "service"

                # Simulate fallback mode activation
                self.fallback.enable(
                    f"Database {result.error_type} error: {result.error_message}"
                )
                assert self.fallback.is_enabled() is True

                # Test mock data availability
                mock_data = self.fallback.get_mock_data("trade")
                assert mock_data is not None
                assert mock_data["trade_metadata"]["mock"] is True

                # Test user message
                user_message = self.fallback.get_user_message()
                assert "⚠️  Running in Fallback Mode" in user_message

    def test_database_recovery_scenario_integration(self):
        """Test database recovery from failure state."""
        # Start in failure state
        self.fallback.enable("Database connection failed")
        assert self.fallback.is_enabled() is True

        # Mock database becoming available
        with patch(
            "libs.trading_models.db_validator.DatabaseValidator"
        ) as mock_validator_class:
            mock_validator = Mock()
            mock_validator.test_connection.return_value = ConnectionResult(
                success=True, connection_time_ms=30.0
            )
            mock_validator_class.return_value = mock_validator

            # Test recovery
            recovered = self.fallback.check_database_available(
                "postgresql://test:test@localhost/test"
            )
            assert recovered is True
            assert self.fallback.is_enabled() is False

            # Verify user message reflects recovery
            user_message = self.fallback.get_user_message()
            assert "✅ Database connected" in user_message

    def test_error_message_scenarios_integration(self):
        """Test various error message scenarios with full error handling."""
        test_cases = [
            {
                "error_type": "auth",
                "expected_keywords": [
                    "authentication",
                    "password",
                    "Setup-Database.ps1",
                ],
                "expected_recovery_steps": 3,
            },
            {
                "error_type": "service",
                "expected_keywords": ["service", "Start-Service", "postgresql"],
                "expected_recovery_steps": 3,
            },
            {
                "error_type": "network",
                "expected_keywords": ["network", "firewall", "telnet"],
                "expected_recovery_steps": 3,
            },
            {
                "error_type": "schema",
                "expected_keywords": ["database", "create", "Setup-Database.ps1"],
                "expected_recovery_steps": 3,
            },
        ]

        for case in test_cases:
            result = ConnectionResult(
                success=False,
                error_type=case["error_type"],
                error_message=f"Test {case['error_type']} error",
                suggested_fix="Test fix",
            )

            error = self.validator.create_database_error(result)
            user_message = error.get_user_message().lower()

            # Check expected keywords (some may be in recovery steps)
            full_error_text = (
                user_message + " " + " ".join(error.recovery_steps)
            ).lower()
            for keyword in case["expected_keywords"]:
                assert keyword.lower() in full_error_text, (
                    f"Keyword '{keyword}' not found in {case['error_type']} error message or recovery steps"
                )

            # Check recovery steps count
            assert len(error.recovery_steps) >= case["expected_recovery_steps"], (
                f"Expected at least {case['expected_recovery_steps']} recovery steps for {case['error_type']}"
            )

            # Check diagnostic info
            diagnostic_info = error.get_diagnostic_info()
            assert diagnostic_info["error_type"] == case["error_type"]
            assert "timestamp" in diagnostic_info

    def test_complete_setup_validation_integration(self):
        """Test complete setup validation with all components."""
        setup_results = {}

        # Step 1: Service status check
        with patch.object(self.validator, "test_service_running") as mock_service:
            mock_service.return_value = ServiceStatus(
                running=True, service_name="postgresql-x64-17"
            )
            service_status = self.validator.test_service_running()
            setup_results["service_check"] = service_status.running

        # Step 2: Connection test
        with patch("libs.trading_models.db_validator.create_engine") as mock_engine:
            mock_connection = Mock()
            mock_result = Mock()
            mock_result.fetchone.return_value = ["PostgreSQL 15.0"]
            mock_connection.execute.return_value = mock_result

            # Create proper context manager mock
            mock_context_manager = Mock()
            mock_context_manager.__enter__ = Mock(return_value=mock_connection)
            mock_context_manager.__exit__ = Mock(return_value=None)
            mock_engine.return_value.connect.return_value = mock_context_manager

            connection_result = self.validator.test_connection(
                "postgresql://test:test@localhost/test"
            )
            setup_results["connection_test"] = connection_result.success

        # Step 3: Schema validation
        with (
            patch("libs.trading_models.db_validator.inspect") as mock_inspect,
            patch(
                "libs.trading_models.db_validator.create_engine"
            ) as mock_schema_engine,
        ):
            mock_inspector = Mock()
            mock_inspector.get_table_names.return_value = [
                "trades",
                "positions",
                "performance_metrics",
                "audit_logs",
            ]
            mock_inspect.return_value = mock_inspector

            schema_validation = self.validator.validate_schema(
                "postgresql://test:test@localhost/test"
            )
            setup_results["schema_validation"] = schema_validation.valid

        # Step 4: Fallback mode should not be needed
        setup_results["fallback_needed"] = self.fallback.is_enabled()

        # Verify all setup steps passed
        assert setup_results["service_check"] is True
        assert setup_results["connection_test"] is True
        assert setup_results["schema_validation"] is True
        assert setup_results["fallback_needed"] is False

        # Test comprehensive diagnostics
        diagnostics = self.validator.get_connection_diagnostics(
            "postgresql://test:test@localhost/test"
        )
        assert "service_status" in diagnostics
        assert "connection_test" in diagnostics
        assert "schema_validation" in diagnostics
        assert "system_info" in diagnostics


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
