"""
Shared test fixtures for database mocking.

This module provides reusable mock fixtures for database testing
to ensure consistency and reduce code duplication.
"""

from typing import Optional
from unittest.mock import Mock

import pytest


class DatabaseMockFactory:
    """Factory for creating consistent database mocks."""

    @staticmethod
    def create_connection_mock(
        version: str = "PostgreSQL 15.0, compiled by Visual C++",
        connection_time_delay: float = 0.001
    ) -> tuple[Mock, Mock, Mock]:
        """
        Create a properly configured database connection mock.

        Args:
            version: Database version string to return
            connection_time_delay: Simulated connection delay in seconds

        Returns:
            Tuple of (mock_engine, mock_connection, mock_context_manager)
        """
        import time

        # Create mocks
        mock_engine = Mock()
        mock_connection = Mock()
        mock_result = Mock()

        # Configure result mock
        mock_result.fetchone.return_value = [version]

        # Add realistic delay simulation
        def mock_execute(*args, **kwargs):
            time.sleep(connection_time_delay)
            return mock_result

        mock_connection.execute.side_effect = mock_execute

        # Create proper context manager mock
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_connection)
        mock_context_manager.__exit__ = Mock(return_value=None)
        mock_engine.connect.return_value = mock_context_manager

        return mock_engine, mock_connection, mock_context_manager

    @staticmethod
    def create_schema_inspector_mock(
        tables: list[str] = None
    ) -> Mock:
        """
        Create a mock database inspector for schema validation.

        Args:
            tables: List of table names to return (defaults to common tables)

        Returns:
            Mock inspector object
        """
        if tables is None:
            tables = ["trades", "positions", "performance_metrics", "audit_logs"]

        mock_inspector = Mock()
        mock_inspector.get_table_names.return_value = tables
        return mock_inspector

    @staticmethod
    def create_service_status_mock(
        running: bool = True,
        service_name: str = "postgresql-x64-17",
        pid: Optional[int] = 1234,
        status: str = "RUNNING"
    ) -> Mock:
        """
        Create a mock service status result.

        Args:
            running: Whether service is running
            service_name: Name of the PostgreSQL service
            pid: Process ID (if running)
            status: Service status string

        Returns:
            Mock subprocess result
        """
        mock_result = Mock()
        mock_result.returncode = 0

        state_code = "4" if running else "1"
        mock_result.stdout = f"SERVICE_NAME: {service_name}\nSTATE: {state_code} {status}"

        return mock_result


@pytest.fixture
def db_connection_mock():
    """Fixture providing a successful database connection mock."""
    return DatabaseMockFactory.create_connection_mock()


@pytest.fixture
def db_schema_mock():
    """Fixture providing a complete schema inspector mock."""
    return DatabaseMockFactory.create_schema_inspector_mock()


@pytest.fixture
def db_service_running_mock():
    """Fixture providing a running PostgreSQL service mock."""
    return DatabaseMockFactory.create_service_status_mock(running=True)


@pytest.fixture
def db_service_stopped_mock():
    """Fixture providing a stopped PostgreSQL service mock."""
    return DatabaseMockFactory.create_service_status_mock(
        running=False,
        status="STOPPED"
    )


@pytest.fixture
def db_auth_failure_mock():
    """Fixture providing an authentication failure mock."""
    from sqlalchemy.exc import OperationalError

    def _create_auth_error():
        return OperationalError(
            "password authentication failed for user", None, None
        )

    return _create_auth_error


@pytest.fixture
def db_service_failure_mock():
    """Fixture providing a service connection failure mock."""
    from sqlalchemy.exc import OperationalError

    def _create_service_error():
        return OperationalError("connection refused", None, None)

    return _create_service_error


class DatabaseTestMixin:
    """
    Mixin class providing common database test utilities.

    Use this mixin in test classes that need database testing utilities.
    """

    def setup_successful_connection_mock(self, mock_create_engine):
        """Set up a successful database connection mock."""
        mock_engine, mock_connection, mock_context_manager = (
            DatabaseMockFactory.create_connection_mock()
        )
        mock_create_engine.return_value = mock_engine
        return mock_engine, mock_connection, mock_context_manager

    def setup_auth_failure_mock(self, mock_create_engine):
        """Set up an authentication failure mock."""
        from sqlalchemy.exc import OperationalError
        mock_create_engine.side_effect = OperationalError(
            "password authentication failed for user", None, None
        )

    def setup_service_failure_mock(self, mock_create_engine):
        """Set up a service connection failure mock."""
        from sqlalchemy.exc import OperationalError
        mock_create_engine.side_effect = OperationalError(
            "connection refused", None, None
        )

    def assert_connection_result_success(self, result, expected_version="PostgreSQL 15.0"):
        """Assert that a connection result indicates success."""
        assert result.success is True
        assert result.connection_time_ms is not None
        assert result.connection_time_ms > 0
        assert expected_version in result.database_version
        assert result.error_type is None

    def assert_connection_result_failure(self, result, expected_error_type, expected_keywords=None):
        """Assert that a connection result indicates failure."""
        assert result.success is False
        assert result.error_type == expected_error_type
        assert result.error_message is not None
        assert result.suggested_fix is not None

        if expected_keywords:
            error_message_lower = result.error_message.lower()
            for keyword in expected_keywords:
                assert keyword.lower() in error_message_lower
