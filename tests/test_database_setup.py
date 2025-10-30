"""
Integration tests for database setup flow.

This module tests the comprehensive database setup system including:
- DatabaseValidator class functionality
- Connection validation with various error scenarios
- Fallback mode activation and deactivation
- Schema initialization and validation
- Configuration manager database operations
"""

import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from libs.trading_models.config_manager import ConfigurationManager
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


class TestDatabaseValidator:
    """Test suite for DatabaseValidator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = DatabaseValidator()
        self.valid_connection_string = "postgresql://test:test@localhost:5432/test_db"
        self.invalid_connection_string = "invalid://connection/string"

    def test_connection_result_model_validation(self):
        """Test ConnectionResult model validation and serialization."""
        # Test successful connection result
        result = ConnectionResult(
            success=True,
            connection_time_ms=45.2,
            database_version="PostgreSQL 15.0"
        )
        assert result.success is True
        assert result.connection_time_ms == 45.2
        assert result.error_type is None

        # Test model serialization
        result_dict = result.model_dump()
        assert "success" in result_dict
        assert "connection_time_ms" in result_dict
        assert "database_version" in result_dict

        # Test failed connection result
        result = ConnectionResult(
            success=False,
            error_type="auth",
            error_message="Authentication failed",
            suggested_fix="Check password"
        )
        assert result.success is False
        assert result.error_type == "auth"
        assert result.error_message == "Authentication failed"

        # Test failed result serialization
        result_dict = result.model_dump()
        assert "success" in result_dict
        assert "error_type" in result_dict
        assert "error_message" in result_dict

    def test_schema_validation_model_validation(self):
        """Test SchemaValidation model validation and serialization."""
        validation = SchemaValidation(
            valid=True,
            tables_found=["trades", "positions"],
            tables_missing=[],
            tables_expected=["trades", "positions", "performance_metrics"],
            migration_needed=False
        )
        assert validation.valid is True
        assert len(validation.tables_found) == 2
        assert len(validation.tables_missing) == 0

        # Test model serialization
        validation_dict = validation.model_dump()
        assert "valid" in validation_dict
        assert "tables_found" in validation_dict
        assert "tables_missing" in validation_dict

    def test_service_status_model_validation(self):
        """Test ServiceStatus model validation and serialization."""
        status = ServiceStatus(
            running=True,
            service_name="postgresql-x64-17",
            pid=1234,
            status="RUNNING"
        )
        assert status.running is True
        assert status.service_name == "postgresql-x64-17"
        assert status.pid == 1234

        # Test model serialization
        status_dict = status.model_dump()
        assert "running" in status_dict
        assert "service_name" in status_dict
        assert "pid" in status_dict

    @patch('libs.trading_models.db_validator.create_engine')
    def test_connection_success(self, mock_create_engine):
        """
        Test successful database connection with proper context manager mocking.

        Verifies that:
        - Connection succeeds with valid credentials
        - Connection time is measured and positive
        - Database version is extracted correctly
        - No error type is set on success
        """
        # Mock successful connection
        mock_engine = Mock()
        mock_connection = Mock()
        mock_result = Mock()
        mock_result.fetchone.return_value = ["PostgreSQL 15.0, compiled by Visual C++"]

        # Add a small delay to simulate realistic connection time
        import time
        def mock_execute(*args, **kwargs):
            time.sleep(0.001)  # 1ms delay
            return mock_result

        mock_connection.execute.side_effect = mock_execute

        # Properly mock the context manager
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

    @patch('libs.trading_models.db_validator.create_engine')
    def test_connection_auth_failure(self, mock_create_engine):
        """Test authentication failure scenario."""
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

    @patch('libs.trading_models.db_validator.create_engine')
    def test_connection_service_failure(self, mock_create_engine):
        """Test service not running scenario."""
        from sqlalchemy.exc import OperationalError

        # Mock connection refused (service not running)
        mock_create_engine.side_effect = OperationalError(
            "connection refused", None, None
        )

        with patch.object(self.validator, 'test_service_running') as mock_service:
            mock_service.return_value = ServiceStatus(running=False, status="STOPPED")

            result = self.validator.test_connection(self.valid_connection_string)

            assert result.success is False
            assert result.error_type == "service"
            assert "service is not running" in result.error_message.lower()
            assert "Start-Service" in result.suggested_fix

    @patch('libs.trading_models.db_validator.create_engine')
    def test_connection_network_failure(self, mock_create_engine):
        """Test network connectivity failure."""
        from sqlalchemy.exc import OperationalError

        # Mock network failure with service running
        mock_create_engine.side_effect = OperationalError(
            "could not connect to server", None, None
        )

        with patch.object(self.validator, 'test_service_running') as mock_service:
            mock_service.return_value = ServiceStatus(running=True, status="RUNNING")

            result = self.validator.test_connection(self.valid_connection_string)

            assert result.success is False
            assert result.error_type == "network"
            assert "cannot connect" in result.error_message.lower()

    def test_invalid_connection_string(self):
        """Test invalid connection string format."""
        result = self.validator.test_connection(self.invalid_connection_string)

        assert result.success is False
        assert result.error_type == "config"
        assert "invalid connection string" in result.error_message.lower()

    def test_empty_connection_string(self):
        """Test empty connection string handling."""
        result = self.validator.test_connection("")

        assert result.success is False
        assert result.error_type == "config"
        assert "invalid connection string" in result.error_message.lower()

    def test_none_connection_string(self):
        """Test None connection string handling."""
        result = self.validator.test_connection(None)

        assert result.success is False
        assert result.error_type == "config"
        assert "invalid connection string" in result.error_message.lower()

    @patch('libs.trading_models.db_validator.create_engine')
    def test_unexpected_database_exception(self, mock_create_engine):
        """Test handling of unexpected database exceptions."""
        # Mock unexpected exception
        mock_create_engine.side_effect = Exception("Unexpected database error")

        result = self.validator.test_connection(self.valid_connection_string)

        assert result.success is False
        assert result.error_type == "unknown"
        assert "unexpected error" in result.error_message.lower()
        assert result.connection_time_ms is not None

    @patch('libs.trading_models.db_validator.subprocess.run')
    def test_service_status_running(self, mock_subprocess):
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

    @patch('libs.trading_models.db_validator.subprocess.run')
    def test_service_status_stopped(self, mock_subprocess):
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

    @patch('libs.trading_models.db_validator.psutil.process_iter')
    @patch('libs.trading_models.db_validator.subprocess.run')
    def test_service_status_process_detection(self, mock_subprocess, mock_process_iter):
        """Test PostgreSQL process detection when service query fails."""
        # Mock service query failure
        mock_subprocess.side_effect = Exception("Service query failed")

        # Mock process detection
        mock_process = Mock()
        mock_process.info = {'pid': 1234, 'name': 'postgres.exe', 'cmdline': ['postgres']}
        mock_process_iter.return_value = [mock_process]

        status = self.validator.test_service_running()

        assert status.running is True
        assert status.pid == 1234
        assert status.status == "PROCESS_RUNNING"

    @patch('libs.trading_models.db_validator.inspect')
    @patch('libs.trading_models.db_validator.create_engine')
    def test_schema_validation_complete(self, mock_create_engine, mock_inspect):
        """Test schema validation with all tables present."""
        # Mock database inspection
        mock_inspector = Mock()
        mock_inspector.get_table_names.return_value = [
            "trades", "positions", "performance_metrics", "audit_logs"
        ]
        mock_inspect.return_value = mock_inspector

        validation = self.validator.validate_schema(self.valid_connection_string)

        assert validation.valid is True
        assert len(validation.tables_found) == 4
        assert len(validation.tables_missing) == 0
        assert validation.migration_needed is False

    @patch('libs.trading_models.db_validator.inspect')
    @patch('libs.trading_models.db_validator.create_engine')
    def test_schema_validation_incomplete(self, mock_create_engine, mock_inspect):
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

    def test_database_error_creation(self):
        """Test DatabaseError creation and formatting."""
        connection_result = ConnectionResult(
            success=False,
            error_type="auth",
            error_message="Authentication failed",
            suggested_fix="Run Setup-Database.ps1"
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

    def test_connection_diagnostics(self):
        """Test comprehensive connection diagnostics."""
        with patch.object(self.validator, 'test_service_running') as mock_service, \
             patch.object(self.validator, 'test_connection') as mock_connection, \
             patch.object(self.validator, 'validate_schema') as mock_schema:

            # Mock all diagnostic components
            mock_service.return_value = ServiceStatus(running=True, service_name="postgresql-x64-17")
            mock_connection.return_value = ConnectionResult(success=True, connection_time_ms=25.5)
            mock_schema.return_value = SchemaValidation(valid=True, tables_found=["trades"], tables_missing=[], tables_expected=["trades"])

            diagnostics = self.validator.get_connection_diagnostics(self.valid_connection_string)

            assert "timestamp" in diagnostics
            assert "service_status" in diagnostics
            assert "connection_test" in diagnostics
            assert "schema_validation" in diagnostics
            assert "system_info" in diagnostics

            assert diagnostics["service_status"]["running"] is True
            assert diagnostics["connection_test"]["success"] is True
            assert diagnostics["schema_validation"]["valid"] is True


class TestFallbackMode:
    """Test suite for FallbackMode functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.fallback = FallbackMode()
        self.mock_generator = MockDataGenerator()

        # Ensure clean state for each test
        if self.fallback.is_enabled():
            self.fallback.disable()

    def teardown_method(self):
        """Clean up test fixtures."""
        # Reset fallback mode state after each test
        if self.fallback.is_enabled():
            self.fallback.disable()

    def test_fallback_mode_enable_disable(self):
        """Test enabling and disabling fallback mode."""
        assert self.fallback.is_enabled() is False

        self.fallback.enable("Test reason")
        assert self.fallback.is_enabled() is True

        self.fallback.disable()
        assert self.fallback.is_enabled() is False

    def test_mock_data_generation(self):
        """Test mock data generation for different types."""
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

        # Test multiple trades
        trades_data = self.fallback.get_mock_data("trades", count=5, symbol="ETHUSDT")
        assert len(trades_data) == 5
        assert all(trade["symbol"] == "ETHUSDT" for trade in trades_data)

        # Test position data
        position_data = self.fallback.get_mock_data("position", trade_id="test-123")
        assert position_data is not None
        assert position_data["trade_id"] == "test-123"
        assert "unrealized_pnl" in position_data

        # Test metrics data
        metrics_data = self.fallback.get_mock_data("metrics")
        assert isinstance(metrics_data, list)
        assert len(metrics_data) > 0
        assert all("metric_name" in metric for metric in metrics_data)

        # Test market data
        market_data = self.fallback.get_mock_data("market_data", symbol="BTCUSDT")
        assert market_data["symbol"] == "BTCUSDT"
        assert "price" in market_data
        assert market_data["mock"] is True

    def test_mock_data_when_disabled(self):
        """Test that mock data returns None when fallback mode is disabled."""
        assert self.fallback.is_enabled() is False

        trade_data = self.fallback.get_mock_data("trade")
        assert trade_data is None

    def test_warning_logging(self):
        """Test warning logging functionality."""
        self.fallback.enable("Testing")

        # Test warning logging
        self.fallback.log_warning("test_operation", {"detail": "test"})

        # Verify warning count increased
        status = self.fallback.get_status()
        assert status["warning_count"] == 1

    def test_database_availability_check(self):
        """Test database availability checking with mocked validator."""
        self.fallback.enable("Testing")

        # Test with invalid connection string (should return False)
        available = self.fallback.check_database_available("")
        assert available is False
        assert self.fallback.is_enabled() is True  # Should remain enabled

        # Test with None connection string (should return False)
        available = self.fallback.check_database_available(None)
        assert available is False
        assert self.fallback.is_enabled() is True  # Should remain enabled

    def test_fallback_status(self):
        """Test fallback mode status reporting."""
        status = self.fallback.get_status()
        assert status["enabled"] is False
        assert status["warning_count"] == 0
        assert len(status["limitations"]) == 0

        self.fallback.enable("Test reason")
        status = self.fallback.get_status()
        assert status["enabled"] is True
        assert len(status["limitations"]) > 0

    def test_user_message(self):
        """Test user-friendly status messages."""
        # Test message when disabled
        message = self.fallback.get_user_message()
        assert "✅ Database connected" in message

        # Test message when enabled
        self.fallback.enable("Test reason")
        message = self.fallback.get_user_message()
        assert "⚠️  Running in Fallback Mode" in message
        assert "limitations:" in message.lower()

    def test_global_fallback_instance(self):
        """Test global fallback mode instance."""
        global_instance = get_fallback_mode()
        assert isinstance(global_instance, FallbackMode)

        # Test that multiple calls return same instance
        another_instance = get_fallback_mode()
        assert global_instance is another_instance


@pytest.mark.skip(reason="Configuration manager needs SystemConfig refactoring")
class TestConfigurationManager:
    """Test suite for ConfigurationManager database operations."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary directory for test config files
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)

        # Create test .env.local file
        self.env_file = Path('.env.local')
        self.env_file.write_text("# Test environment file\nTEST_VAR=test_value\n")

    def teardown_method(self):
        """Clean up test fixtures."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir)

    def test_update_database_url(self):
        """Test updating database URL in .env.local file."""
        config_manager = ConfigurationManager()

        # Test updating database URL
        success = config_manager.update_database_url(
            password="test_password",
            user="test_user",
            host="test_host",
            port=5433,
            database="test_db"
        )

        assert success is True

        # Verify file was updated
        content = self.env_file.read_text()
        assert "DATABASE_URL=postgresql://test_user:test_password@test_host:5433/test_db" in content
        assert "TEST_VAR=test_value" in content  # Original content preserved

    def test_backup_and_restore_config(self):
        """Test configuration backup and restore functionality."""
        config_manager = ConfigurationManager()

        # Create backup
        backup_path = config_manager.backup_config()
        assert backup_path.exists()
        assert "backup_" in backup_path.name

        # Modify original file
        self.env_file.write_text("MODIFIED=true\n")

        # Restore from backup
        success = config_manager.restore_config(backup_path)
        assert success is True

        # Verify restoration
        content = self.env_file.read_text()
        assert "TEST_VAR=test_value" in content
        assert "MODIFIED=true" not in content

    def test_database_connection_validation(self):
        """Test database connection validation through config manager."""
        config_manager = ConfigurationManager()

        with patch('libs.trading_models.config_manager.DatabaseValidator') as mock_validator_class:
            mock_validator = Mock()
            mock_validator.test_connection.return_value = ConnectionResult(
                success=True,
                connection_time_ms=25.0
            )
            mock_validator_class.return_value = mock_validator

            # Mock get_database_config to return test config
            with patch.object(config_manager, 'get_database_config') as mock_get_config:
                mock_config = Mock()
                mock_config.connection_string = "postgresql://test:test@localhost/test"
                mock_get_config.return_value = mock_config

                result = config_manager.validate_database_connection()

                assert result["success"] is True
                assert result["connection_time_ms"] == 25.0


class TestIntegrationScenarios:
    """Integration tests for complete database setup scenarios."""

    def setup_method(self):
        """Set up integration test fixtures."""
        self.validator = DatabaseValidator()
        self.fallback = FallbackMode()

        # Reset fallback mode state
        if self.fallback.is_enabled():
            self.fallback.disable()

    @pytest.mark.asyncio
    async def test_startup_with_valid_database(self):
        """Test application startup with valid database connection."""
        with patch('libs.trading_models.db_validator.create_engine') as mock_engine, \
             patch('libs.trading_models.db_validator.inspect') as mock_inspect:

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
            mock_inspector.get_table_names.return_value = ["trades", "positions", "performance_metrics", "audit_logs"]
            mock_inspect.return_value = mock_inspector

            # Test connection
            result = self.validator.test_connection("postgresql://test:test@localhost/test")
            assert result.success is True

            # Test schema validation
            schema = self.validator.validate_schema("postgresql://test:test@localhost/test")
            assert schema.valid is True

            # Verify fallback mode is not enabled
            assert self.fallback.is_enabled() is False

    @pytest.mark.asyncio
    async def test_startup_with_database_failure(self):
        """Test application startup with database connection failure."""
        from sqlalchemy.exc import OperationalError

        with patch('libs.trading_models.db_validator.create_engine') as mock_engine:
            # Mock database connection failure
            mock_engine.side_effect = OperationalError("connection refused", None, None)

            with patch.object(self.validator, 'test_service_running') as mock_service:
                mock_service.return_value = ServiceStatus(running=False, status="STOPPED")

                # Test connection failure
                result = self.validator.test_connection("postgresql://test:test@localhost/test")
                assert result.success is False
                assert result.error_type == "service"

                # Simulate fallback mode activation
                self.fallback.enable(f"Database {result.error_type} error: {result.error_message}")
                assert self.fallback.is_enabled() is True

                # Test mock data availability
                mock_data = self.fallback.get_mock_data("trade")
                assert mock_data is not None
                assert mock_data["trade_metadata"]["mock"] is True

    @pytest.mark.asyncio
    async def test_database_recovery_scenario(self):
        """Test database recovery from failure state."""
        # Start in failure state
        self.fallback.enable("Database connection failed")
        assert self.fallback.is_enabled() is True

        # Mock database becoming available
        with patch('libs.trading_models.db_validator.DatabaseValidator') as mock_validator_class:
            mock_validator = Mock()
            mock_validator.test_connection.return_value = ConnectionResult(
                success=True,
                connection_time_ms=30.0
            )
            mock_validator_class.return_value = mock_validator

            # Test recovery
            recovered = self.fallback.check_database_available("postgresql://test:test@localhost/test")
            assert recovered is True
            assert self.fallback.is_enabled() is False

    def test_error_message_scenarios(self):
        """Test various error message scenarios."""
        test_cases = [
            {
                "error_type": "auth",
                "expected_keywords": ["authentication", "password", "Setup-Database.ps1"]
            },
            {
                "error_type": "service",
                "expected_keywords": ["service", "Start-Service", "postgresql"]
            },
            {
                "error_type": "network",
                "expected_keywords": ["network", "firewall", "telnet"]
            },
            {
                "error_type": "schema",
                "expected_keywords": ["database", "create", "Setup-Database.ps1"]
            }
        ]

        for case in test_cases:
            result = ConnectionResult(
                success=False,
                error_type=case["error_type"],
                error_message=f"Test {case['error_type']} error",
                suggested_fix="Test fix"
            )

            error = self.validator.create_database_error(result)
            user_message = error.get_user_message().lower()

            for keyword in case["expected_keywords"]:
                assert keyword.lower() in user_message, f"Keyword '{keyword}' not found in {case['error_type']} error message"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
