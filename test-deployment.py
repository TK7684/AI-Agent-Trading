#!/usr/bin/env python
"""
Test script for AI Trading System deployment on Vercel.
This script tests all API endpoints and cron jobs to ensure deployment is working correctly.
"""

import json
import sys
import time
from datetime import datetime, UTC
import requests
from typing import Dict, Any, List

# Configuration
BASE_URL = "https://ai-agent-trading.vercel.app"
TIMEOUT = 30

def print_header(title: str):
    """Print a formatted header."""
    print(f"\n{'=' * 60}")
    print(f" {title}")
    print(f"{'=' * 60}")

def print_test_result(test_name: str, success: bool, message: str = ""):
    """Print a test result."""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"  {status}: {test_name}")
    if message:
        print(f"    {message}")

def make_request(endpoint: str, method: str = "GET", data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Make an HTTP request to the API."""
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}

    try:
        if method == "GET":
            response = requests.get(url, timeout=TIMEOUT, headers=headers)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=TIMEOUT, headers=headers)
        elif method == "PUT":
            response = requests.put(url, json=data, timeout=TIMEOUT, headers=headers)
        elif method == "DELETE":
            response = requests.delete(url, timeout=TIMEOUT, headers=headers)
        else:
            raise ValueError(f"Unsupported method: {method}")

        return {
            "status_code": response.status_code,
            "success": response.status_code < 400,
            "data": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
            "response_time": response.elapsed.total_seconds()
        }
    except requests.exceptions.RequestException as e:
        return {
            "status_code": 0,
            "success": False,
            "data": str(e),
            "response_time": TIMEOUT
        }

def test_health_endpoint():
    """Test the health check endpoint."""
    print("\nTesting Health Check Endpoint")
    print("-" * 30)

    response = make_request("/api/health")

    if response["success"] and response["status_code"] == 200:
        data = response.get("data", {})
        if isinstance(data, dict):
            status = data.get("status", "unknown")
            print_test_result("Health Check", True, f"Status: {status}")

            # Check component health
            components = data.get("components", {})
            for component, health in components.items():
                if isinstance(health, dict):
                    comp_status = health.get("status", "unknown")
                    print_test_result(f"Component: {component}", comp_status == "healthy",
                                     f"Status: {comp_status}")
        return True
    else:
        print_test_result("Health Check", False, f"Status Code: {response['status_code']}")
        return False

def test_trading_endpoints():
    """Test trading-related endpoints."""
    print("\nTesting Trading Endpoints")
    print("-" * 30)

    success_count = 0
    total_tests = 0

    # Test Get Trades
    total_tests += 1
    response = make_request("/api/trading/trades?limit=10")
    if response["success"] and response["status_code"] == 200:
        print_test_result("Get Trades", True)
        success_count += 1
    else:
        print_test_result("Get Trades", False, f"Status Code: {response['status_code']}")

    # Test Create Trade
    total_tests += 1
    trade_data = {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "quantity": 0.001,
        "price": 50000.0,
        "type": "LIMIT"
    }
    response = make_request("/api/trading/trades", "POST", trade_data)
    if response["success"] and response["status_code"] in [200, 201]:
        print_test_result("Create Trade", True)
        success_count += 1
    else:
        print_test_result("Create Trade", False, f"Status Code: {response['status_code']}")

    # Test Get Positions
    total_tests += 1
    response = make_request("/api/trading/positions")
    if response["success"] and response["status_code"] == 200:
        print_test_result("Get Positions", True)
        success_count += 1
    else:
        print_test_result("Get Positions", False, f"Status Code: {response['status_code']}")

    # Test Get Portfolio
    total_tests += 1
    response = make_request("/api/trading/portfolio")
    if response["success"] and response["status_code"] == 200:
        print_test_result("Get Portfolio", True)
        success_count += 1
    else:
        print_test_result("Get Portfolio", False, f"Status Code: {response['status_code']}")

    return success_count, total_tests

def test_training_endpoints():
    """Test training-related endpoints."""
    print("\nTesting Training Endpoints")
    print("-" * 30)

    success_count = 0
    total_tests = 0

    # Test Get Models
    total_tests += 1
    response = make_request("/api/training/models?limit=5")
    if response["success"] and response["status_code"] == 200:
        print_test_result("Get Models", True)
        success_count += 1
    else:
        print_test_result("Get Models", False, f"Status Code: {response['status_code']}")

    # Test Train Model
    total_tests += 1
    training_data = {
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "model_type": "price_prediction",
        "lookback_period": 500
    }
    response = make_request("/api/training/train", "POST", training_data)
    # Training might take time, so we check if it was initiated
    if response["success"] and response["status_code"] in [200, 202]:
        print_test_result("Train Model", True, "Training initiated")
        success_count += 1
    else:
        print_test_result("Train Model", False, f"Status Code: {response['status_code']}")

    return success_count, total_tests

def test_strategy_endpoints():
    """Test strategy-related endpoints."""
    print("\nTesting Strategy Endpoints")
    print("-" * 30)

    success_count = 0
    total_tests = 0

    # Test Get Strategies
    total_tests += 1
    response = make_request("/api/strategies?status=active&limit=5")
    if response["success"] and response["status_code"] == 200:
        print_test_result("Get Strategies", True)
        success_count += 1
    else:
        print_test_result("Get Strategies", False, f"Status Code: {response['status_code']}")

    # Test Generate Strategy
    total_tests += 1
    strategy_data = {
        "name": "Test Strategy",
        "type": "mean_reversion",
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "description": "Test strategy for deployment verification"
    }
    response = make_request("/api/strategies", "POST", strategy_data)
    if response["success"] and response["status_code"] in [200, 201]:
        print_test_result("Create Strategy", True)
        success_count += 1
    else:
        print_test_result("Create Strategy", False, f"Status Code: {response['status_code']}")

    return success_count, total_tests

def test_market_endpoints():
    """Test market data endpoints."""
    print("\nTesting Market Data Endpoints")
    print("-" * 30)

    success_count = 0
    total_tests = 0

    # Test Get Market Data
    total_tests += 1
    response = make_request("/api/market/data?symbol=BTCUSDT&timeframe=1h&limit=10")
    if response["success"] and response["status_code"] == 200:
        print_test_result("Get Market Data", True)
        success_count += 1
    else:
        print_test_result("Get Market Data", False, f"Status Code: {response['status_code']}")

    # Test Get Technical Indicators
    total_tests += 1
    response = make_request("/api/market/data/indicators?symbol=BTCUSDT&timeframe=1h&indicators=RSI,MACD")
    if response["success"] and response["status_code"] == 200:
        print_test_result("Get Technical Indicators", True)
        success_count += 1
    else:
        print_test_result("Get Technical Indicators", False, f"Status Code: {response['status_code']}")

    return success_count, total_tests

def test_cron_jobs():
    """Test cron job endpoints."""
    print("\nTesting Cron Job Endpoints")
    print("-" * 30)

    success_count = 0
    total_tests = 0

    # Test Training Cron
    total_tests += 1
    response = make_request("/api/cron/training", "POST")
    # Cron jobs might return immediately
    if response["success"] or response["status_code"] == 200:
        print_test_result("Training Cron", True, "Cron can be triggered")
        success_count += 1
    else:
        print_test_result("Training Cron", False, f"Status Code: {response['status_code']}")

    # Test Strategy Update Cron
    total_tests += 1
    response = make_request("/api/cron/strategy-update", "POST")
    if response["success"] or response["status_code"] == 200:
        print_test_result("Strategy Update Cron", True, "Cron can be triggered")
        success_count += 1
    else:
        print_test_result("Strategy Update Cron", False, f"Status Code: {response['status_code']}")

    # Test Market Analysis Cron
    total_tests += 1
    response = make_request("/api/cron/market-analysis", "POST")
    if response["success"] or response["status_code"] == 200:
        print_test_result("Market Analysis Cron", True, "Cron can be triggered")
        success_count += 1
    else:
        print_test_result("Market Analysis Cron", False, f"Status Code: {response['status_code']}")

    return success_count, total_tests

def calculate_performance_metrics(results: List[Dict[str, int]]):
    """Calculate overall performance metrics."""
    total_passed = sum(result["passed"] for result in results)
    total_tests = sum(result["total"] for result in results)

    if total_tests == 0:
        return {"success_rate": 0, "grade": "F"}

    success_rate = (total_passed / total_tests) * 100

    if success_rate >= 90:
        grade = "A"
    elif success_rate >= 80:
        grade = "B"
    elif success_rate >= 70:
        grade = "C"
    elif success_rate >= 60:
        grade = "D"
    else:
        grade = "F"

    return {
        "success_rate": success_rate,
        "grade": grade,
        "total_passed": total_passed,
        "total_tests": total_tests
    }

def main():
    """Main test execution function."""
    print_header("AI Trading System - Deployment Test")
    print(f"Testing deployment at: {BASE_URL}")
    print(f"Test started at: {datetime.now(UTC).isoformat()}")

    # Run tests
    health_passed = test_health_endpoint()

    trading_passed, trading_total = test_trading_endpoints()
    training_passed, training_total = test_training_endpoints()
    strategy_passed, strategy_total = test_strategy_endpoints()
    market_passed, market_total = test_market_endpoints()
    cron_passed, cron_total = test_cron_jobs()

    # Calculate metrics
    results = [
        {"name": "Health Check", "passed": 1 if health_passed else 0, "total": 1},
        {"name": "Trading", "passed": trading_passed, "total": trading_total},
        {"name": "Training", "passed": training_passed, "total": training_total},
        {"name": "Strategies", "passed": strategy_passed, "total": strategy_total},
        {"name": "Market Data", "passed": market_passed, "total": market_total},
        {"name": "Cron Jobs", "passed": cron_passed, "total": cron_total}
    ]

    metrics = calculate_performance_metrics(results)

    # Print summary
    print_header("Test Results Summary")
    for result in results:
        status = "✅" if result["passed"] == result["total"] else "❌"
        print(f"{status} {result['name']}: {result['passed']}/{result['total']}")

    print_header("Overall Performance")
    print(f"Success Rate: {metrics['success_rate']:.1f}%")
    print(f"Grade: {metrics['grade']}")
    print(f"Total Passed: {metrics['total_passed']}/{metrics['total_tests']}")

    # Exit with appropriate code
    if metrics["success_rate"] >= 80:
        print("\n🎉 Deployment test PASSED! Your AI Trading System is working correctly.")
        sys.exit(0)
    else:
        print("\n⚠️ Deployment test FAILED! Some components are not working correctly.")
        print("Please check the failing tests and fix any issues.")
        sys.exit(1)

if __name__ == "__main__":
    main()
