"""
Database validation and connection testing module.

This module provides comprehensive database connection validation,
service status checking, and schema validation with detailed error reporting.
"""

import subprocess
import time
from datetime import UTC, datetime
from typing import Any, Optional

import psutil
import structlog
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError

from .base import BaseModel as TradingBaseModel

logger = structlog.get_logger(__name__)


class ConnectionResult(TradingBaseModel):
    """Result of database connection test."""
    success: bool
    error_type: Optional[str] = None  # "auth", "service", "network", "schema", "permission"
    error_message: Optional[str] = None
    suggested_fix: Optional[str] = None
    connection_time_ms: Optional[float] = None
    database_version: Optional[str] = None


class SchemaValidation(TradingBaseModel):
    """Result of database schema validation."""
    valid: bool
    tables_found: list[str]
    tables_missing: list[str]
    tables_expected: list[str]
    schema_version: Optional[str] = None
    migration_needed: bool = False


class ServiceStatus(TradingBaseModel):
    """PostgreSQL service status information."""
    running: bool
    service_name: Optional[str] = None
    pid: Optional[int] = None
    status: Optional[str] = None
    error_message: Optional[str] = None


class DatabaseError(Exception):
    """Custom database error with structured information."""

    def __init__(self, error_type: str, message: str, suggested_fix: str, recovery_steps: list[str] = None):
        self.error_type = error_type
        self.message = message
        self.suggested_fix = suggested_fix
        self.recovery_steps = recovery_steps or []
        super().__init__(message)

    def get_user_message(self) -> str:
        """Returns formatted message for user display."""
        # Map error types to user-friendly names
        error_type_names = {
            "auth": "authentication",
            "service": "service",
            "network": "network",
            "schema": "database schema",
            "permission": "permission"
        }

        display_error_type = error_type_names.get(self.error_type, self.error_type)

        return f"""❌ Database {display_error_type} error

{self.message}

Suggested fix:
{self.suggested_fix}

Recovery steps:
""" + "\n".join(f"{i+1}. {step}" for i, step in enumerate(self.recovery_steps))

    def get_diagnostic_info(self) -> dict[str, Any]:
        """Returns detailed diagnostic information."""
        return {
            "error_type": self.error_type,
            "message": self.message,
            "suggested_fix": self.suggested_fix,
            "recovery_steps": self.recovery_steps,
            "timestamp": datetime.now(UTC).isoformat()
        }


class DatabaseValidator:
    """Validates database connections and provides diagnostics."""

    # Expected table names from the trading system
    EXPECTED_TABLES = {
        "trades", "positions", "performance_metrics", "audit_logs"
    }

    # Common PostgreSQL service names on Windows
    POSTGRES_SERVICE_NAMES = [
        "postgresql-x64-17", "postgresql-x64-16", "postgresql-x64-15",
        "postgresql-x64-14", "postgresql-x64-13", "postgresql",
        "PostgreSQL"
    ]

    def __init__(self):
        self.logger = logger.bind(component="DatabaseValidator")

    def test_connection(self, connection_string: str) -> ConnectionResult:
        """
        Test database connection with detailed error analysis.

        Args:
            connection_string: PostgreSQL connection string

        Returns:
            ConnectionResult with success status and diagnostic information
        """
        start_time = time.time()

        try:
            # Validate connection string
            if not connection_string or not isinstance(connection_string, str):
                return ConnectionResult(
                    success=False,
                    error_type="config",
                    error_message="Invalid connection string format",
                    suggested_fix="Use format: postgresql://user:password@host:port/database"
                )

            # Parse connection string to extract components
            if not connection_string.startswith(('postgresql://', 'postgres://')):
                return ConnectionResult(
                    success=False,
                    error_type="config",
                    error_message="Invalid connection string format",
                    suggested_fix="Use format: postgresql://user:password@host:port/database"
                )

            # Test basic connection
            engine = create_engine(connection_string, pool_pre_ping=True)

            with engine.connect() as conn:
                # Test basic query
                result = conn.execute(text("SELECT version()"))
                version_info = result.fetchone()[0]

                connection_time = (time.time() - start_time) * 1000

                self.logger.info("Database connection successful",
                               connection_time_ms=connection_time,
                               database_version=version_info)

                return ConnectionResult(
                    success=True,
                    connection_time_ms=connection_time,
                    database_version=version_info
                )

        except OperationalError as e:
            error_str = str(e).lower()
            connection_time = (time.time() - start_time) * 1000

            # Analyze specific error types
            if "authentication failed" in error_str or "password authentication failed" in error_str:
                return ConnectionResult(
                    success=False,
                    error_type="auth",
                    error_message="Database authentication failed - incorrect password or user",
                    suggested_fix="Run: .\\scripts\\Setup-Database.ps1 to configure password",
                    connection_time_ms=connection_time
                )

            elif "connection refused" in error_str or "could not connect" in error_str:
                service_status = self.test_service_running()
                if not service_status.running:
                    return ConnectionResult(
                        success=False,
                        error_type="service",
                        error_message="PostgreSQL service is not running",
                        suggested_fix="Start PostgreSQL service: Start-Service postgresql-x64-17",
                        connection_time_ms=connection_time
                    )
                else:
                    return ConnectionResult(
                        success=False,
                        error_type="network",
                        error_message="Cannot connect to database - check host and port",
                        suggested_fix="Verify PostgreSQL is running and accessible on specified host:port",
                        connection_time_ms=connection_time
                    )

            elif "database" in error_str and "does not exist" in error_str:
                return ConnectionResult(
                    success=False,
                    error_type="schema",
                    error_message="Database does not exist",
                    suggested_fix="Run: .\\scripts\\Setup-Database.ps1 to create database",
                    connection_time_ms=connection_time
                )

            elif "permission denied" in error_str or "insufficient privilege" in error_str:
                return ConnectionResult(
                    success=False,
                    error_type="permission",
                    error_message="Insufficient database permissions",
                    suggested_fix="Grant required permissions or run: .\\scripts\\Setup-Database.ps1",
                    connection_time_ms=connection_time
                )

            else:
                return ConnectionResult(
                    success=False,
                    error_type="unknown",
                    error_message=f"Database connection failed: {str(e)}",
                    suggested_fix="Check connection string and run: .\\scripts\\Setup-Database.ps1",
                    connection_time_ms=connection_time
                )

        except Exception as e:
            connection_time = (time.time() - start_time) * 1000
            self.logger.error("Unexpected database connection error", error=str(e))

            return ConnectionResult(
                success=False,
                error_type="unknown",
                error_message=f"Unexpected error: {str(e)}",
                suggested_fix="Check logs and run: .\\scripts\\Setup-Database.ps1",
                connection_time_ms=connection_time
            )

    def test_service_running(self) -> ServiceStatus:
        """
        Test if PostgreSQL service is running.

        Returns:
            ServiceStatus with service information
        """
        try:
            # Check Windows services
            for service_name in self.POSTGRES_SERVICE_NAMES:
                try:
                    result = subprocess.run(
                        ["sc", "query", service_name],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )

                    if result.returncode == 0 and "RUNNING" in result.stdout:
                        return ServiceStatus(
                            running=True,
                            service_name=service_name,
                            status="RUNNING"
                        )
                    elif result.returncode == 0:
                        return ServiceStatus(
                            running=False,
                            service_name=service_name,
                            status="STOPPED"
                        )

                except subprocess.TimeoutExpired:
                    continue
                except Exception:
                    continue

            # Check for PostgreSQL processes
            postgres_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] and 'postgres' in proc.info['name'].lower():
                        postgres_processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if postgres_processes:
                return ServiceStatus(
                    running=True,
                    pid=postgres_processes[0]['pid'],
                    status="PROCESS_RUNNING"
                )

            return ServiceStatus(
                running=False,
                status="NOT_FOUND",
                error_message="PostgreSQL service not found"
            )

        except Exception as e:
            self.logger.error("Error checking PostgreSQL service status", error=str(e))
            return ServiceStatus(
                running=False,
                error_message=f"Error checking service: {str(e)}"
            )

    def validate_schema(self, connection_string: str) -> SchemaValidation:
        """
        Validate database schema against expected tables.

        Args:
            connection_string: PostgreSQL connection string

        Returns:
            SchemaValidation with schema status
        """
        try:
            engine = create_engine(connection_string)
            inspector = inspect(engine)

            # Get existing tables
            existing_tables = set(inspector.get_table_names())
            expected_tables = self.EXPECTED_TABLES

            tables_missing = list(expected_tables - existing_tables)
            tables_found = list(expected_tables & existing_tables)

            is_valid = len(tables_missing) == 0
            migration_needed = len(tables_missing) > 0

            self.logger.info("Schema validation completed",
                           tables_found=len(tables_found),
                           tables_missing=len(tables_missing),
                           valid=is_valid)

            return SchemaValidation(
                valid=is_valid,
                tables_found=tables_found,
                tables_missing=tables_missing,
                tables_expected=list(expected_tables),
                migration_needed=migration_needed
            )

        except Exception as e:
            self.logger.error("Schema validation failed", error=str(e))
            return SchemaValidation(
                valid=False,
                tables_found=[],
                tables_missing=list(self.EXPECTED_TABLES),
                tables_expected=list(self.EXPECTED_TABLES),
                migration_needed=True
            )

    def get_connection_diagnostics(self, connection_string: str = None) -> dict[str, Any]:
        """
        Get comprehensive connection diagnostics.

        Args:
            connection_string: Optional connection string to test

        Returns:
            Dictionary with diagnostic information
        """
        diagnostics = {
            "timestamp": datetime.now(UTC).isoformat(),
            "service_status": self.test_service_running().model_dump(),
        }

        if connection_string:
            diagnostics["connection_test"] = self.test_connection(connection_string).model_dump()
            diagnostics["schema_validation"] = self.validate_schema(connection_string).model_dump()

        # Add system information
        try:
            diagnostics["system_info"] = {
                "platform": "Windows",
                "python_version": f"{__import__('sys').version_info.major}.{__import__('sys').version_info.minor}",
                "available_memory_gb": round(psutil.virtual_memory().available / (1024**3), 2),
                "cpu_percent": psutil.cpu_percent(interval=1)
            }
        except Exception as e:
            diagnostics["system_info"] = {"error": str(e)}

        return diagnostics

    def create_database_error(self, connection_result: ConnectionResult) -> DatabaseError:
        """
        Create a structured DatabaseError from connection result.

        Args:
            connection_result: Failed connection result

        Returns:
            DatabaseError with detailed information
        """
        error_type = connection_result.error_type or "unknown"
        message = connection_result.error_message or "Unknown database error"
        suggested_fix = connection_result.suggested_fix or "Run database setup wizard"

        # Define recovery steps based on error type
        recovery_steps = {
            "auth": [
                "Run: .\\scripts\\Setup-Database.ps1",
                "Or manually update .env.local with correct password",
                "Or reset password: .\\scripts\\Reset-PostgreSQL-Password.ps1"
            ],
            "service": [
                "Start PostgreSQL service: Start-Service postgresql-x64-17",
                "Or use Services.msc to start PostgreSQL service",
                "Check Windows Event Logs for service errors"
            ],
            "network": [
                "Verify PostgreSQL is running on correct host and port",
                "Check firewall settings",
                "Test with: telnet localhost 5432"
            ],
            "schema": [
                "Run: .\\scripts\\Setup-Database.ps1 to create database",
                "Or manually create database in pgAdmin",
                "Verify database name in connection string"
            ],
            "permission": [
                "Grant database permissions to trading user",
                "Run: .\\scripts\\Setup-Database.ps1 to recreate user",
                "Check PostgreSQL logs for permission errors"
            ]
        }.get(error_type, [
            "Run: .\\scripts\\Setup-Database.ps1",
            "Check TROUBLESHOOTING.md for detailed help",
            "Review PostgreSQL logs for more information"
        ])

        return DatabaseError(
            error_type=error_type,
            message=message,
            suggested_fix=suggested_fix,
            recovery_steps=recovery_steps
        )
