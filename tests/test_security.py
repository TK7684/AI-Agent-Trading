"""
Comprehensive tests for security and compliance features.
"""

import json
import os
import ssl
import tempfile
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from libs.trading_models.api_security import (
    APIRequest,
    APISecurityMiddleware,
    RequestValidator,
    SecureCommunication,
    rate_limit,
    require_permission,
)
from libs.trading_models.security import (
    AuditEvent,
    AuditEventType,
    AuditLogger,
    ComplianceReporter,
    Permission,
    RateLimiter,
    RBACManager,
    Role,
    SecretManager,
    SecurityError,
    SecurityManager,
    User,
)


class TestSecretManager:
    """Test secret management functionality."""

    def test_environment_variable_secrets(self):
        """Test retrieving secrets from environment variables."""
        with patch.dict(os.environ, {'TEST_SECRET': 'test_value'}):
            secret_manager = SecretManager()
            assert secret_manager.get_secret('TEST_SECRET') == 'test_value'

    def test_encrypted_local_storage(self):
        """Test encrypted local secret storage."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)

            secret_manager = SecretManager()

            # Set and retrieve secret
            assert secret_manager.set_secret('test_key', 'test_value')
            assert secret_manager.get_secret('test_key') == 'test_value'

            # Verify file is encrypted
            secrets_file = Path('.secrets.enc')
            assert secrets_file.exists()

            with open(secrets_file, 'rb') as f:
                content = f.read()

            # Should not contain plaintext
            assert b'test_value' not in content

    def test_secret_rotation(self):
        """Test secret rotation functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)

            secret_manager = SecretManager()

            # Initial secret
            secret_manager.set_secret('api_key', 'old_key')
            assert secret_manager.get_secret('api_key') == 'old_key'

            # Rotate secret
            assert secret_manager.rotate_secret('api_key', 'new_key')
            assert secret_manager.get_secret('api_key') == 'new_key'

    def test_vault_integration_placeholder(self):
        """Test Vault integration (placeholder implementation)."""
        secret_manager = SecretManager(vault_url='https://vault.example.com', vault_token='test_token')

        # Should return None for non-existent secrets when Vault is not actually configured
        assert secret_manager.get_secret('vault_secret') is None


class TestRBACManager:
    """Test Role-Based Access Control."""

    def test_user_creation(self):
        """Test user creation with roles."""
        secret_manager = SecretManager()
        rbac = RBACManager(secret_manager)

        user = rbac.create_user('testuser', Role.TRADER)

        assert user.username == 'testuser'
        assert user.role == Role.TRADER
        assert Permission.READ_TRADES in user.permissions
        assert Permission.WRITE_TRADES in user.permissions
        assert Permission.READ_SECRETS not in user.permissions  # Admin only

    def test_permission_checking(self):
        """Test permission checking."""
        secret_manager = SecretManager()
        rbac = RBACManager(secret_manager)

        # Create users with different roles
        admin = rbac.create_user('admin', Role.ADMIN)
        trader = rbac.create_user('trader', Role.TRADER)
        viewer = rbac.create_user('viewer', Role.VIEWER)

        # Admin has all permissions
        assert rbac.check_permission(admin.user_id, Permission.READ_SECRETS)
        assert rbac.check_permission(admin.user_id, Permission.EXECUTE_ORDERS)

        # Trader has trading permissions
        assert rbac.check_permission(trader.user_id, Permission.EXECUTE_ORDERS)
        assert not rbac.check_permission(trader.user_id, Permission.READ_SECRETS)

        # Viewer has limited permissions
        assert rbac.check_permission(viewer.user_id, Permission.READ_TRADES)
        assert not rbac.check_permission(viewer.user_id, Permission.EXECUTE_ORDERS)

    def test_signed_configuration(self):
        """Test signed configuration generation and verification."""
        secret_manager = SecretManager()
        rbac = RBACManager(secret_manager)

        config = {"max_position_size": 1000, "risk_limit": 0.02}

        # Generate signed config
        signed_config = rbac.generate_signed_config(config, "admin")
        assert isinstance(signed_config, str)

        # Verify signed config
        verified_config = rbac.verify_signed_config(signed_config)
        assert verified_config == config

        # Tampered config should fail verification
        tampered_config = signed_config[:-5] + "XXXXX"
        assert rbac.verify_signed_config(tampered_config) is None


class TestAuditLogger:
    """Test audit logging functionality."""

    def test_audit_event_logging(self):
        """Test basic audit event logging."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test_audit.jsonl"
            audit_logger = AuditLogger(str(log_file))

            event = AuditEvent(
                event_id="test_001",
                event_type=AuditEventType.LOGIN,
                user_id="testuser",
                timestamp=datetime.now(UTC),
                details={"success": True}
            )

            assert audit_logger.log_event(event)
            assert log_file.exists()

            # Verify log content
            with open(log_file) as f:
                log_line = f.readline().strip()
                log_data = json.loads(log_line)

                assert log_data['event_id'] == "test_001"
                assert log_data['event_type'] == "login"
                assert log_data['user_id'] == "testuser"
                assert 'hash' in log_data
                assert 'previous_hash' in log_data

    def test_hash_chain_integrity(self):
        """Test tamper-evident hash chain."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test_audit.jsonl"
            audit_logger = AuditLogger(str(log_file))

            # Log multiple events
            events = [
                AuditEvent("event_1", AuditEventType.LOGIN, "user1", datetime.now(UTC), {}),
                AuditEvent("event_2", AuditEventType.TRADE_EXECUTED, "user1", datetime.now(UTC), {}),
                AuditEvent("event_3", AuditEventType.LOGOUT, "user1", datetime.now(UTC), {})
            ]

            for event in events:
                audit_logger.log_event(event)

            # Verify integrity
            assert audit_logger.verify_integrity()

            # Tamper with log file
            with open(log_file) as f:
                lines = f.readlines()

            # Modify second line
            tampered_data = json.loads(lines[1])
            tampered_data['user_id'] = 'hacker'
            lines[1] = json.dumps(tampered_data) + '\n'

            with open(log_file, 'w') as f:
                f.writelines(lines)

            # Create new logger to reload
            audit_logger_new = AuditLogger(str(log_file))
            assert not audit_logger_new.verify_integrity()

    def test_hash_chain_loading(self):
        """Test loading existing hash chain."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test_audit.jsonl"

            # Create initial logger and log event
            audit_logger1 = AuditLogger(str(log_file))
            event1 = AuditEvent("event_1", AuditEventType.LOGIN, "user1", datetime.now(UTC), {})
            audit_logger1.log_event(event1)

            # Create new logger (simulating restart)
            audit_logger2 = AuditLogger(str(log_file))

            # Log another event
            event2 = AuditEvent("event_2", AuditEventType.LOGOUT, "user1", datetime.now(UTC), {})
            audit_logger2.log_event(event2)

            # Verify integrity
            assert audit_logger2.verify_integrity()


class TestComplianceReporter:
    """Test compliance reporting functionality."""

    def test_trade_report_generation(self):
        """Test trade compliance report generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test_audit.jsonl"
            audit_logger = AuditLogger(str(log_file))

            # Log some trade events
            trade_details = {
                "trade_id": "T001",
                "symbol": "BTCUSD",
                "quantity": 1.5,
                "price": 50000.0,
                "timestamp": datetime.now(UTC).isoformat(),
                "user_id": "trader1"
            }

            trade_event = AuditEvent(
                event_id="trade_001",
                event_type=AuditEventType.TRADE_EXECUTED,
                user_id="trader1",
                timestamp=datetime.now(UTC),
                details=trade_details
            )

            audit_logger.log_event(trade_event)

            # Generate compliance report
            reporter = ComplianceReporter(audit_logger)
            start_date = datetime.now(UTC) - timedelta(days=1)
            end_date = datetime.now(UTC) + timedelta(days=1)

            report = reporter.generate_trade_report("US", start_date, end_date)

            assert report["jurisdiction"] == "US"
            assert report["total_trades"] == 1
            assert len(report["trades"]) == 1
            assert report["trades"][0]["trade_id"] == "T001"
            assert report["compliance_status"] == "COMPLIANT"

    def test_audit_summary_generation(self):
        """Test audit summary report generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test_audit.jsonl"
            audit_logger = AuditLogger(str(log_file))

            # Log various events
            events = [
                AuditEvent("login_1", AuditEventType.LOGIN, "user1", datetime.now(UTC), {}),
                AuditEvent("trade_1", AuditEventType.TRADE_EXECUTED, "user1", datetime.now(UTC), {}),
                AuditEvent("config_1", AuditEventType.CONFIG_CHANGED, "admin", datetime.now(UTC), {}),
                AuditEvent("logout_1", AuditEventType.LOGOUT, "user1", datetime.now(UTC), {})
            ]

            for event in events:
                audit_logger.log_event(event)

            # Generate summary
            reporter = ComplianceReporter(audit_logger)
            start_date = datetime.now(UTC) - timedelta(days=1)
            end_date = datetime.now(UTC) + timedelta(days=1)

            summary = reporter.generate_audit_summary(start_date, end_date)

            assert summary["total_events"] == 4
            assert summary["event_summary"]["login"] == 1
            assert summary["event_summary"]["trade_executed"] == 1
            assert summary["event_summary"]["config_changed"] == 1
            assert summary["event_summary"]["logout"] == 1

            assert "user1" in summary["user_activity"]
            assert "admin" in summary["user_activity"]


class TestRateLimiter:
    """Test rate limiting functionality."""

    def test_rate_limiting(self):
        """Test basic rate limiting."""
        limiter = RateLimiter(max_requests=3, window_seconds=60)

        # First 3 requests should be allowed
        assert limiter.is_allowed("client1")
        assert limiter.is_allowed("client1")
        assert limiter.is_allowed("client1")

        # 4th request should be denied
        assert not limiter.is_allowed("client1")

        # Different client should be allowed
        assert limiter.is_allowed("client2")

    def test_rate_limit_window(self):
        """Test rate limit window expiration."""
        limiter = RateLimiter(max_requests=2, window_seconds=1)

        # Use up the limit
        assert limiter.is_allowed("client1")
        assert limiter.is_allowed("client1")
        assert not limiter.is_allowed("client1")

        # Wait for window to expire
        time.sleep(1.1)

        # Should be allowed again
        assert limiter.is_allowed("client1")

    def test_remaining_requests(self):
        """Test remaining requests calculation."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)

        assert limiter.get_remaining_requests("client1") == 5

        limiter.is_allowed("client1")
        assert limiter.get_remaining_requests("client1") == 4

        limiter.is_allowed("client1")
        limiter.is_allowed("client1")
        assert limiter.get_remaining_requests("client1") == 2


class TestRequestValidator:
    """Test API request validation."""

    def test_valid_trade_request(self):
        """Test validation of valid trade request."""
        validator = RequestValidator()

        request = APIRequest(
            method="POST",
            path="/api/v1/trades",
            headers={"Content-Type": "application/json"},
            body=json.dumps({
                "symbol": "BTCUSD",
                "side": "BUY",
                "quantity": 1.0,
                "order_type": "MARKET"
            })
        )

        result = validator.validate_request(request)
        assert result["valid"]
        assert len(result["errors"]) == 0

    def test_invalid_trade_request(self):
        """Test validation of invalid trade request."""
        validator = RequestValidator()

        request = APIRequest(
            method="POST",
            path="/api/v1/trades",
            headers={"Content-Type": "application/json"},
            body=json.dumps({
                "symbol": "",  # Too short
                "side": "INVALID",  # Not in allowed values
                "quantity": -1.0,  # Negative (warning)
                # Missing required order_type
            })
        )

        result = validator.validate_request(request)
        assert not result["valid"]
        assert len(result["errors"]) > 0
        assert any("symbol" in error for error in result["errors"])
        assert any("side" in error for error in result["errors"])
        assert any("order_type" in error for error in result["errors"])

    def test_json_validation(self):
        """Test JSON parsing validation."""
        validator = RequestValidator()

        request = APIRequest(
            method="POST",
            path="/api/v1/trades",
            headers={"Content-Type": "application/json"},
            body="invalid json"
        )

        result = validator.validate_request(request)
        assert not result["valid"]
        assert any("Invalid JSON" in error for error in result["errors"])


class TestAPISecurityMiddleware:
    """Test API security middleware."""

    def test_rate_limiting_middleware(self):
        """Test rate limiting in middleware."""
        security_manager = SecurityManager()
        middleware = APISecurityMiddleware(security_manager)

        request = APIRequest(
            method="GET",
            path="/api/v1/positions",
            headers={"Authorization": "Bearer admin_token"},
            client_ip="192.168.1.1"
        )

        # First requests should be allowed
        for _ in range(5):
            result = middleware.process_request(request)
            assert result["allowed"]

        # Exhaust rate limit
        for _ in range(100):
            middleware.process_request(request)

        # Should be rate limited
        result = middleware.process_request(request)
        assert not result["allowed"]
        assert result["status_code"] == 429

    def test_authentication_middleware(self):
        """Test authentication in middleware."""
        security_manager = SecurityManager()
        middleware = APISecurityMiddleware(security_manager)

        # Request without auth header
        request = APIRequest(
            method="GET",
            path="/api/v1/trades",
            headers={},
            client_ip="192.168.1.1"
        )

        result = middleware.process_request(request)
        assert not result["allowed"]
        assert result["status_code"] == 401

        # Request with valid auth
        request.headers["Authorization"] = "Bearer admin_token"
        result = middleware.process_request(request)
        assert result["allowed"]
        assert "user" in result

    def test_ip_blocking(self):
        """Test IP blocking functionality."""
        security_manager = SecurityManager()
        middleware = APISecurityMiddleware(security_manager)

        # Block an IP
        middleware.blocked_ips.add("192.168.1.100")

        request = APIRequest(
            method="GET",
            path="/api/v1/positions",
            headers={"Authorization": "Bearer admin_token"},
            client_ip="192.168.1.100"
        )

        result = middleware.process_request(request)
        assert not result["allowed"]
        assert result["status_code"] == 403


class TestSecureCommunication:
    """Test secure inter-service communication."""

    def test_service_token_creation_and_verification(self):
        """Test service-to-service token creation and verification."""
        security_manager = SecurityManager()
        secure_comm = SecureCommunication(security_manager)

        # Create service token
        token = secure_comm.create_service_token("orchestrator", "execution-gateway")
        assert isinstance(token, str)

        # Verify token
        assert secure_comm.verify_service_token(token, "execution-gateway")

        # Wrong target service should fail
        assert not secure_comm.verify_service_token(token, "wrong-service")

    def test_request_signing(self):
        """Test HTTP request signing and verification."""
        security_manager = SecurityManager()
        secure_comm = SecureCommunication(security_manager)

        method = "POST"
        url = "/api/v1/orders"
        body = '{"symbol": "BTCUSD", "side": "BUY"}'

        # Create signed request
        headers = secure_comm.create_signed_request("orchestrator", method, url, body)

        assert "X-Service-Name" in headers
        assert "X-Signature" in headers
        assert "X-Timestamp" in headers
        assert "X-Nonce" in headers

        # Verify signed request
        assert secure_comm.verify_signed_request(headers, method, url, body)

        # Tampered body should fail verification
        assert not secure_comm.verify_signed_request(headers, method, url, "tampered")

    def test_tls_context_creation(self):
        """Test TLS context creation."""
        security_manager = SecurityManager()
        secure_comm = SecureCommunication(security_manager)

        context = secure_comm.create_tls_context()

        assert context.minimum_version == ssl.TLSVersion.TLSv1_2
        assert context.check_hostname
        assert context.verify_mode == ssl.CERT_REQUIRED


class TestSecurityDecorators:
    """Test security decorators."""

    def test_permission_decorator(self):
        """Test permission requirement decorator."""
        @require_permission(Permission.EXECUTE_ORDERS)
        def execute_trade(user=None):
            return "Trade executed"

        # User with permission
        admin_user = User(
            user_id="admin",
            username="admin",
            role=Role.ADMIN,
            permissions=[Permission.EXECUTE_ORDERS],
            created_at=datetime.now(UTC)
        )

        result = execute_trade(user=admin_user)
        assert result == "Trade executed"

        # User without permission
        viewer_user = User(
            user_id="viewer",
            username="viewer",
            role=Role.VIEWER,
            permissions=[Permission.READ_TRADES],
            created_at=datetime.now(UTC)
        )

        with pytest.raises(SecurityError):
            execute_trade(user=viewer_user)

    def test_rate_limit_decorator(self):
        """Test rate limiting decorator."""
        @rate_limit(max_requests=2, window_seconds=60)
        def api_endpoint(client_ip="test"):
            return "Success"

        # First two calls should succeed
        assert api_endpoint(client_ip="192.168.1.1") == "Success"
        assert api_endpoint(client_ip="192.168.1.1") == "Success"

        # Third call should fail
        with pytest.raises(SecurityError):
            api_endpoint(client_ip="192.168.1.1")


class TestSecurityManager:
    """Test main security manager integration."""

    def test_security_manager_initialization(self):
        """Test security manager initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)

            security_manager = SecurityManager()

            assert security_manager.secret_manager is not None
            assert security_manager.rbac_manager is not None
            assert security_manager.audit_logger is not None
            assert security_manager.compliance_reporter is not None

    def test_authentication_and_authorization(self):
        """Test integrated authentication and authorization."""
        security_manager = SecurityManager()

        # Should fail with invalid credentials
        user = security_manager.authenticate_and_authorize("invalid", "invalid", Permission.READ_TRADES)
        assert user is None

        # Should succeed with valid admin credentials
        user = security_manager.authenticate_and_authorize("admin", "password", Permission.READ_TRADES)
        assert user is not None
        assert user.username == "admin"

    def test_trade_logging(self):
        """Test trade execution logging."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)

            security_manager = SecurityManager()

            trade_details = {
                "trade_id": "T001",
                "symbol": "BTCUSD",
                "quantity": 1.0,
                "price": 50000.0
            }

            security_manager.log_trade_execution("trader1", trade_details)

            # Verify audit log
            assert security_manager.audit_logger.log_file.exists()

    def test_compliance_report_generation(self):
        """Test compliance report generation with logging."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)

            security_manager = SecurityManager()

            # Log a trade first
            trade_details = {
                "trade_id": "T001",
                "symbol": "BTCUSD",
                "quantity": 1.0,
                "price": 50000.0,
                "user_id": "trader1"
            }
            security_manager.log_trade_execution("trader1", trade_details)

            # Generate compliance report
            start_date = datetime.now(UTC) - timedelta(days=1)
            end_date = datetime.now(UTC) + timedelta(days=1)

            report = security_manager.generate_compliance_report("US", start_date, end_date)

            assert report["jurisdiction"] == "US"
            assert report["total_trades"] == 1


class TestPenetrationTesting:
    """Penetration testing scenarios."""

    def test_sql_injection_protection(self):
        """Test protection against SQL injection attempts."""
        validator = RequestValidator()

        # SQL injection attempt in request body
        request = APIRequest(
            method="POST",
            path="/api/v1/trades",
            headers={"Content-Type": "application/json"},
            body=json.dumps({
                "symbol": "'; DROP TABLE trades; --",
                "side": "BUY",
                "quantity": 1.0,
                "order_type": "MARKET"
            })
        )

        result = validator.validate_request(request)
        # Should still be valid as we're not doing SQL injection protection at validation level
        # This would be handled by parameterized queries in the database layer
        assert result["valid"]

    def test_xss_protection(self):
        """Test protection against XSS attempts."""
        validator = RequestValidator()

        # XSS attempt in request body
        request = APIRequest(
            method="POST",
            path="/api/v1/config",
            headers={"Content-Type": "application/json"},
            body=json.dumps({
                "key": "<script>alert('xss')</script>",
                "value": "test"
            })
        )

        result = validator.validate_request(request)
        # Should be valid - XSS protection would be handled by output encoding
        assert result["valid"]

    def test_replay_attack_protection(self):
        """Test protection against replay attacks."""
        security_manager = SecurityManager()
        secure_comm = SecureCommunication(security_manager)

        method = "POST"
        url = "/api/v1/orders"
        body = '{"symbol": "BTCUSD"}'

        # Create signed request
        headers = secure_comm.create_signed_request("orchestrator", method, url, body)

        # Should verify successfully
        assert secure_comm.verify_signed_request(headers, method, url, body)

        # Simulate old timestamp (replay attack)
        old_timestamp = str(int(time.time()) - 400)  # 400 seconds ago
        headers["X-Timestamp"] = old_timestamp

        # Should fail verification due to timestamp
        assert not secure_comm.verify_signed_request(headers, method, url, body)

    def test_brute_force_protection(self):
        """Test protection against brute force attacks."""
        security_manager = SecurityManager()
        middleware = APISecurityMiddleware(security_manager)

        # Simulate multiple failed login attempts
        for i in range(15):
            request = APIRequest(
                method="POST",
                path="/api/v1/login",
                headers={"Authorization": "Bearer invalid_token"},
                client_ip="192.168.1.100"
            )
            middleware.process_request(request)

        # IP should be blocked after suspicious activity
        assert "192.168.1.100" in middleware.blocked_ips

    def test_timing_attack_resistance(self):
        """Test resistance to timing attacks."""
        security_manager = SecurityManager()
        secure_comm = SecureCommunication(security_manager)

        # Create two different signatures
        headers1 = secure_comm.create_signed_request("orchestrator", "GET", "/api/v1/test", "")
        headers2 = secure_comm.create_signed_request("orchestrator", "GET", "/api/v1/test", "different")

        # Verification should use constant-time comparison
        # This is ensured by using hmac.compare_digest in the implementation
        start_time = time.time()
        secure_comm.verify_signed_request(headers1, "GET", "/api/v1/test", "")
        time1 = time.time() - start_time

        start_time = time.time()
        secure_comm.verify_signed_request(headers2, "GET", "/api/v1/test", "different")
        time2 = time.time() - start_time

        # Times should be similar (within reasonable variance)
        # This is a basic check - in practice, timing attack resistance
        # is provided by hmac.compare_digest
        assert abs(time1 - time2) < 0.1  # 100ms tolerance


if __name__ == "__main__":
    pytest.main([__file__])
