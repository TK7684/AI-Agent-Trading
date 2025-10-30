#!/usr/bin/env python3
"""
Demo script showcasing security and compliance features.
"""

import json
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

from libs.trading_models.api_security import (
    APIRequest,
    APISecurityMiddleware,
    SecureCommunication,
)
from libs.trading_models.security import (
    AuditEvent,
    AuditEventType,
    Permission,
    Role,
    SecurityManager,
)


def demo_secret_management():
    """Demonstrate secure secret management."""
    print("=== Secret Management Demo ===")

    security_manager = SecurityManager()
    secret_manager = security_manager.secret_manager

    # Store and retrieve secrets
    print("1. Storing API key securely...")
    success = secret_manager.set_secret("EXCHANGE_API_KEY", "sk_test_12345")
    print(f"   Secret stored: {success}")

    print("2. Retrieving API key...")
    api_key = secret_manager.get_secret("EXCHANGE_API_KEY")
    print(f"   Retrieved key: {api_key[:10]}..." if api_key else "   Key not found")

    print("3. Rotating secret...")
    success = secret_manager.rotate_secret("EXCHANGE_API_KEY", "sk_test_67890")
    print(f"   Secret rotated: {success}")

    new_key = secret_manager.get_secret("EXCHANGE_API_KEY")
    print(f"   New key: {new_key[:10]}..." if new_key else "   Key not found")

    print()


def demo_rbac():
    """Demonstrate Role-Based Access Control."""
    print("=== RBAC Demo ===")

    security_manager = SecurityManager()
    rbac = security_manager.rbac_manager

    # Create users with different roles
    print("1. Creating users with different roles...")
    admin = rbac.create_user("alice", Role.ADMIN)
    trader = rbac.create_user("bob", Role.TRADER)
    viewer = rbac.create_user("charlie", Role.VIEWER)

    print(f"   Admin user: {admin.username} ({admin.role.value})")
    print(f"   Trader user: {trader.username} ({trader.role.value})")
    print(f"   Viewer user: {viewer.username} ({viewer.role.value})")

    # Test permissions
    print("\n2. Testing permissions...")
    permissions_to_test = [
        Permission.EXECUTE_ORDERS,
        Permission.READ_SECRETS,
        Permission.READ_TRADES,
        Permission.WRITE_CONFIG
    ]

    users = [("Admin", admin), ("Trader", trader), ("Viewer", viewer)]

    for user_type, user in users:
        print(f"   {user_type} permissions:")
        for perm in permissions_to_test:
            has_perm = rbac.check_permission(user.user_id, perm)
            status = "✓" if has_perm else "✗"
            print(f"     {status} {perm.value}")

    # Signed configuration
    print("\n3. Testing signed configuration...")
    config = {
        "max_position_size": 10000,
        "risk_limit": 0.02,
        "leverage_limit": 5.0
    }

    signed_config = rbac.generate_signed_config(config, admin.user_id)
    print(f"   Signed config generated: {len(signed_config)} characters")

    verified_config = rbac.verify_signed_config(signed_config)
    print(f"   Config verified: {verified_config == config}")

    print()


def demo_audit_logging():
    """Demonstrate tamper-evident audit logging."""
    print("=== Audit Logging Demo ===")

    security_manager = SecurityManager()

    # Log various events
    print("1. Logging audit events...")

    events = [
        ("User login", AuditEventType.LOGIN, "alice", {"success": True, "ip": "192.168.1.100"}),
        ("Trade executed", AuditEventType.TRADE_EXECUTED, "alice", {
            "trade_id": "T001",
            "symbol": "BTCUSD",
            "quantity": 1.5,
            "price": 50000.0,
            "side": "BUY"
        }),
        ("Config changed", AuditEventType.CONFIG_CHANGED, "alice", {
            "config_name": "max_position_size",
            "old_value": "5000",
            "new_value": "10000"
        }),
        ("User logout", AuditEventType.LOGOUT, "alice", {"session_duration": 3600})
    ]

    for desc, event_type, user_id, details in events:
        event = AuditEvent(
            event_id=f"evt_{int(time.time() * 1000)}",
            event_type=event_type,
            user_id=user_id,
            timestamp=datetime.now(UTC),
            details=details
        )

        success = security_manager.audit_logger.log_event(event)
        print(f"   {desc}: {'✓' if success else '✗'}")
        time.sleep(0.001)  # Ensure unique timestamps

    # Verify audit log integrity
    print("\n2. Verifying audit log integrity...")
    integrity_ok = security_manager.audit_logger.verify_integrity()
    print(f"   Audit log integrity: {'✓' if integrity_ok else '✗'}")

    # Show audit log file
    if security_manager.audit_logger.log_file.exists():
        print(f"\n3. Audit log file: {security_manager.audit_logger.log_file}")
        print(f"   File size: {security_manager.audit_logger.log_file.stat().st_size} bytes")
        print(f"   Hash chain length: {len(security_manager.audit_logger.hash_chain)}")

    print()


def demo_compliance_reporting():
    """Demonstrate compliance reporting."""
    print("=== Compliance Reporting Demo ===")

    security_manager = SecurityManager()

    # Log some trade events for reporting
    print("1. Logging trade events...")

    trades = [
        {"trade_id": "T001", "symbol": "BTCUSD", "quantity": 1.0, "price": 50000.0, "user_id": "alice"},
        {"trade_id": "T002", "symbol": "ETHUSD", "quantity": 5.0, "price": 3000.0, "user_id": "bob"},
        {"trade_id": "T003", "symbol": "BTCUSD", "quantity": 0.5, "price": 51000.0, "user_id": "alice"},
    ]

    for trade in trades:
        security_manager.log_trade_execution(trade["user_id"], trade)
        print(f"   Logged trade {trade['trade_id']}")

    # Generate compliance reports
    print("\n2. Generating compliance reports...")

    start_date = datetime.now(UTC) - timedelta(days=1)
    end_date = datetime.now(UTC) + timedelta(days=1)

    jurisdictions = ["US", "EU", "UK"]

    for jurisdiction in jurisdictions:
        report = security_manager.generate_compliance_report(jurisdiction, start_date, end_date)
        print(f"   {jurisdiction} Report:")
        print(f"     Total trades: {report['total_trades']}")
        print(f"     Compliance status: {report['compliance_status']}")
        print(f"     Required fields: {len(report['rules_applied'].get('required_fields', []))}")

    # Generate audit summary
    print("\n3. Generating audit summary...")
    summary = security_manager.compliance_reporter.generate_audit_summary(start_date, end_date)
    print(f"   Total events: {summary['total_events']}")
    print(f"   Event types: {list(summary['event_summary'].keys())}")
    print(f"   Active users: {len(summary['user_activity'])}")

    print()


def demo_api_security():
    """Demonstrate API security features."""
    print("=== API Security Demo ===")

    security_manager = SecurityManager()
    middleware = APISecurityMiddleware(security_manager)

    # Test valid request
    print("1. Testing valid API request...")

    valid_request = APIRequest(
        method="POST",
        path="/api/v1/trades",
        headers={
            "Authorization": "Bearer admin_token",
            "Content-Type": "application/json",
            "X-Request-ID": "req_123"
        },
        body=json.dumps({
            "symbol": "BTCUSD",
            "side": "BUY",
            "quantity": 1.0,
            "order_type": "MARKET"
        }),
        client_ip="192.168.1.100"
    )

    result = middleware.process_request(valid_request)
    print(f"   Request allowed: {result['allowed']}")
    print(f"   Status code: {result['status_code']}")
    print(f"   Rate limit remaining: {result['headers'].get('X-RateLimit-Remaining', 'N/A')}")

    # Test invalid request
    print("\n2. Testing invalid API request...")

    invalid_request = APIRequest(
        method="POST",
        path="/api/v1/trades",
        headers={"Content-Type": "application/json"},  # Missing auth
        body=json.dumps({
            "symbol": "",  # Invalid
            "side": "INVALID",  # Invalid
            "quantity": -1.0  # Invalid
        }),
        client_ip="192.168.1.101"
    )

    result = middleware.process_request(invalid_request)
    print(f"   Request allowed: {result['allowed']}")
    print(f"   Status code: {result['status_code']}")
    print(f"   Message: {result['message']}")

    # Test rate limiting
    print("\n3. Testing rate limiting...")

    rate_limit_request = APIRequest(
        method="GET",
        path="/api/v1/positions",
        headers={"Authorization": "Bearer admin_token"},
        client_ip="192.168.1.102"
    )

    # Make many requests to trigger rate limit
    for i in range(105):  # Exceed default limit of 100
        result = middleware.process_request(rate_limit_request)
        if not result['allowed']:
            print(f"   Rate limited after {i+1} requests")
            print(f"   Status code: {result['status_code']}")
            break

    print()


def demo_secure_communication():
    """Demonstrate secure inter-service communication."""
    print("=== Secure Communication Demo ===")

    security_manager = SecurityManager()
    secure_comm = SecureCommunication(security_manager)

    # Service-to-service tokens
    print("1. Testing service-to-service authentication...")

    token = secure_comm.create_service_token("orchestrator", "execution-gateway")
    print(f"   Service token created: {len(token)} characters")

    valid = secure_comm.verify_service_token(token, "execution-gateway")
    print(f"   Token verification (correct service): {valid}")

    invalid = secure_comm.verify_service_token(token, "wrong-service")
    print(f"   Token verification (wrong service): {invalid}")

    # Request signing
    print("\n2. Testing request signing...")

    method = "POST"
    url = "/api/v1/orders"
    body = json.dumps({"symbol": "BTCUSD", "side": "BUY", "quantity": 1.0})

    headers = secure_comm.create_signed_request("orchestrator", method, url, body)
    print(f"   Signed headers created: {len(headers)} headers")
    print(f"   Service name: {headers['X-Service-Name']}")
    print(f"   Signature: {headers['X-Signature'][:20]}...")

    verified = secure_comm.verify_signed_request(headers, method, url, body)
    print(f"   Signature verification: {verified}")

    # Test tampered request
    tampered_verified = secure_comm.verify_signed_request(headers, method, url, "tampered")
    print(f"   Tampered request verification: {tampered_verified}")

    # TLS context
    print("\n3. Testing TLS context creation...")

    tls_context = secure_comm.create_tls_context()
    print(f"   TLS context created: {type(tls_context).__name__}")
    print(f"   Minimum TLS version: {tls_context.minimum_version}")
    print(f"   Certificate verification: {tls_context.check_hostname}")

    print()


def demo_penetration_testing():
    """Demonstrate security testing scenarios."""
    print("=== Penetration Testing Demo ===")

    security_manager = SecurityManager()
    middleware = APISecurityMiddleware(security_manager)

    # Test SQL injection attempt
    print("1. Testing SQL injection protection...")

    sql_injection_request = APIRequest(
        method="POST",
        path="/api/v1/trades",
        headers={
            "Authorization": "Bearer admin_token",
            "Content-Type": "application/json"
        },
        body=json.dumps({
            "symbol": "'; DROP TABLE trades; --",
            "side": "BUY",
            "quantity": 1.0,
            "order_type": "MARKET"
        }),
        client_ip="192.168.1.200"
    )

    result = middleware.process_request(sql_injection_request)
    print(f"   SQL injection attempt allowed: {result['allowed']}")
    print(f"   Status: {result['status_code']} - {result['message']}")

    # Test XSS attempt
    print("\n2. Testing XSS protection...")

    xss_request = APIRequest(
        method="POST",
        path="/api/v1/config",
        headers={
            "Authorization": "Bearer admin_token",
            "Content-Type": "application/json"
        },
        body=json.dumps({
            "key": "<script>alert('xss')</script>",
            "value": "malicious"
        }),
        client_ip="192.168.1.201"
    )

    result = middleware.process_request(xss_request)
    print(f"   XSS attempt allowed: {result['allowed']}")
    print(f"   Status: {result['status_code']} - {result['message']}")

    # Test brute force protection
    print("\n3. Testing brute force protection...")

    attacker_ip = "192.168.1.202"
    failed_attempts = 0

    for i in range(20):
        brute_force_request = APIRequest(
            method="POST",
            path="/api/v1/login",
            headers={"Authorization": "Bearer invalid_token"},
            client_ip=attacker_ip
        )

        result = middleware.process_request(brute_force_request)
        if not result['allowed'] and result['status_code'] == 403:
            print(f"   IP blocked after {i+1} failed attempts")
            break
        elif not result['allowed']:
            failed_attempts += 1

    print(f"   Total failed attempts before blocking: {failed_attempts}")

    # Test replay attack protection
    print("\n4. Testing replay attack protection...")

    secure_comm = SecureCommunication(security_manager)

    method = "POST"
    url = "/api/v1/orders"
    body = '{"symbol": "BTCUSD"}'

    headers = secure_comm.create_signed_request("orchestrator", method, url, body)

    # Valid request
    valid = secure_comm.verify_signed_request(headers, method, url, body)
    print(f"   Original request verification: {valid}")

    # Simulate old timestamp (replay attack)
    headers["X-Timestamp"] = str(int(time.time()) - 400)  # 400 seconds ago
    replay_valid = secure_comm.verify_signed_request(headers, method, url, body)
    print(f"   Replay attack verification: {replay_valid}")

    print()


def main():
    """Run all security demos."""
    print("🔒 Autonomous Trading System - Security & Compliance Demo")
    print("=" * 60)
    print()

    try:
        demo_secret_management()
        demo_rbac()
        demo_audit_logging()
        demo_compliance_reporting()
        demo_api_security()
        demo_secure_communication()
        demo_penetration_testing()

        print("✅ All security demos completed successfully!")
        print()
        print("Security Features Demonstrated:")
        print("• Secure secret management with encryption")
        print("• Role-Based Access Control (RBAC)")
        print("• Tamper-evident audit logging")
        print("• Compliance reporting for multiple jurisdictions")
        print("• API request validation and rate limiting")
        print("• Secure inter-service communication")
        print("• Protection against common attacks")
        print()

        # Show generated files
        print("Generated Files:")
        files_to_check = [
            "audit.jsonl",
            ".secrets.enc"
        ]

        for file_path in files_to_check:
            path = Path(file_path)
            if path.exists():
                print(f"• {file_path} ({path.stat().st_size} bytes)")

    except Exception as e:
        print(f"❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
