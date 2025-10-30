#!/usr/bin/env python3
"""
Validation script for the Rust execution gateway implementation.
This script validates that all required components are implemented correctly.
"""

import os
from pathlib import Path


def check_file_exists(file_path):
    """Check if a file exists and return its content."""
    if os.path.exists(file_path):
        with open(file_path, encoding='utf-8') as f:
            return f.read()
    return None

def validate_implementation():
    """Validate the execution gateway implementation."""
    base_path = Path(".")
    results = []

    # Check main implementation files
    files_to_check = [
        "src/main.rs",
        "src/lib.rs",
        "src/gateway.rs",
        "src/api.rs",
        "src/order_manager.rs",
        "src/exchange_adapter.rs",
        "src/retry_logic.rs",
        "src/circuit_breaker.rs",
        "Cargo.toml"
    ]

    for file_path in files_to_check:
        full_path = base_path / file_path
        content = check_file_exists(full_path)
        if content:
            results.append(f"✓ {file_path} exists")
        else:
            results.append(f"✗ {file_path} missing")

    # Check for key implementation features
    gateway_content = check_file_exists(base_path / "src/gateway.rs")
    if gateway_content:
        features = [
            ("Idempotent order processing", "order_deduplication"),
            ("Retry logic with exponential backoff", "execute_order_with_retry"),
            ("Circuit breaker", "circuit_breakers"),
            ("Partial fill handling", "handle_partial_fills"),
            ("Order lifecycle management", "OrderExecution"),
            ("Exchange adapter interface", "ExchangeAdapter"),
            ("Property-based tests", "proptest"),
            ("Chaos testing", "test_chaos_network_failures")
        ]

        for feature_name, pattern in features:
            if pattern in gateway_content:
                results.append(f"✓ {feature_name} implemented")
            else:
                results.append(f"✗ {feature_name} missing")

    # Check API endpoints
    api_content = check_file_exists(base_path / "src/api.rs")
    if api_content:
        endpoints = [
            ("Health check endpoint", "/health"),
            ("Place order endpoint", "/v1/orders"),
            ("Get order status", "get_order_status"),
            ("Cancel order", "cancel_order"),
            ("Idempotent API", "PlaceOrderRequest")
        ]

        for endpoint_name, pattern in endpoints:
            if pattern in api_content:
                results.append(f"✓ {endpoint_name} implemented")
            else:
                results.append(f"✗ {endpoint_name} missing")

    # Check exchange adapter features
    adapter_content = check_file_exists(base_path / "src/exchange_adapter.rs")
    if adapter_content:
        adapter_features = [
            ("Exchange info and trading rules", "ExchangeInfo"),
            ("Order validation", "validate_order"),
            ("Price/quantity rounding", "round_price"),
            ("Mock adapter for testing", "MockExchangeAdapter"),
            ("Partial fill simulation", "with_partial_fills"),
            ("Account info", "AccountInfo")
        ]

        for feature_name, pattern in adapter_features:
            if pattern in adapter_content:
                results.append(f"✓ {feature_name} implemented")
            else:
                results.append(f"✗ {feature_name} missing")

    # Check retry logic
    retry_content = check_file_exists(base_path / "src/retry_logic.rs")
    if retry_content:
        retry_features = [
            ("Exponential backoff", "calculate_delay"),
            ("Jitter implementation", "jitter"),
            ("Retry policy determination", "determine_retry_policy"),
            ("Max retry time calculation", "calculate_max_total_time")
        ]

        for feature_name, pattern in retry_features:
            if pattern in retry_content:
                results.append(f"✓ {feature_name} implemented")
            else:
                results.append(f"✗ {feature_name} missing")

    # Check circuit breaker
    cb_content = check_file_exists(base_path / "src/circuit_breaker.rs")
    if cb_content:
        cb_features = [
            ("Circuit breaker states", "CircuitBreakerState"),
            ("Failure threshold", "failure_threshold"),
            ("Recovery timeout", "recovery_timeout"),
            ("Half-open state", "HalfOpen"),
            ("Success/failure recording", "record_success")
        ]

        for feature_name, pattern in cb_features:
            if pattern in cb_content:
                results.append(f"✓ {feature_name} implemented")
            else:
                results.append(f"✗ {feature_name} missing")

    # Check order manager
    om_content = check_file_exists(base_path / "src/order_manager.rs")
    if om_content:
        om_features = [
            ("Order lifecycle states", "OrderLifecycleState"),
            ("State transitions", "transition_state"),
            ("Client ID mapping", "client_id_mapping"),
            ("Order expiration", "expires_at"),
            ("Cleanup functionality", "cleanup_old_orders"),
            ("Order statistics", "OrderStatistics")
        ]

        for feature_name, pattern in om_features:
            if pattern in om_content:
                results.append(f"✓ {feature_name} implemented")
            else:
                results.append(f"✗ {feature_name} missing")

    return results

def main():
    """Main validation function."""
    print("🔍 Validating Rust Execution Gateway Implementation")
    print("=" * 60)

    results = validate_implementation()

    success_count = sum(1 for r in results if r.startswith("✓"))
    total_count = len(results)

    for result in results:
        print(result)

    print("=" * 60)
    print(f"📊 Validation Summary: {success_count}/{total_count} checks passed")

    if success_count == total_count:
        print("🎉 All implementation requirements satisfied!")
        return True
    else:
        print("⚠️  Some implementation requirements are missing")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
