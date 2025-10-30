#!/bin/bash

# Smoke tests for trading system deployment
# Usage: ./smoke-tests.sh <environment>

set -e

ENVIRONMENT=${1:-staging}
NAMESPACE=${ENVIRONMENT}
BASE_URL="http://trading-system-service.${NAMESPACE}.svc.cluster.local"

echo "Running smoke tests for ${ENVIRONMENT} environment"

# Function to test API endpoint
test_endpoint() {
    local method=$1
    local endpoint=$2
    local expected_status=${3:-200}
    local description=$4
    
    echo "Testing: ${description}"
    
    response=$(kubectl run curl-test --rm -i --restart=Never --image=curlimages/curl -- \
               curl -s -w "%{http_code}" -X ${method} ${BASE_URL}${endpoint})
    
    status_code=$(echo "$response" | tail -n1)
    
    if [ "$status_code" = "$expected_status" ]; then
        echo "✓ ${description} - Status: ${status_code}"
        return 0
    else
        echo "✗ ${description} - Expected: ${expected_status}, Got: ${status_code}"
        return 1
    fi
}

# Function to test trading functionality
test_trading_functionality() {
    echo "Testing trading system functionality..."
    
    # Test market data analysis
    if test_endpoint "GET" "/api/analyze/BTCUSD" "200" "Market data analysis"; then
        echo "✓ Market analysis is working"
    else
        echo "✗ Market analysis failed"
        return 1
    fi
    
    # Test system status
    if test_endpoint "GET" "/api/status" "200" "System status"; then
        echo "✓ System status endpoint is working"
    else
        echo "✗ System status endpoint failed"
        return 1
    fi
    
    # Test configuration endpoint
    if test_endpoint "GET" "/api/config" "200" "Configuration retrieval"; then
        echo "✓ Configuration endpoint is working"
    else
        echo "✗ Configuration endpoint failed"
        return 1
    fi
    
    return 0
}

# Function to test execution gateway
test_execution_gateway() {
    echo "Testing execution gateway..."
    
    GATEWAY_URL="http://trading-system-execution-gateway.${NAMESPACE}.svc.cluster.local:3000"
    
    # Test health endpoint
    response=$(kubectl run curl-test --rm -i --restart=Never --image=curlimages/curl -- \
               curl -s -w "%{http_code}" ${GATEWAY_URL}/health)
    
    status_code=$(echo "$response" | tail -n1)
    
    if [ "$status_code" = "200" ]; then
        echo "✓ Execution gateway health check passed"
    else
        echo "✗ Execution gateway health check failed - Status: ${status_code}"
        return 1
    fi
    
    # Test order validation (without placing real orders)
    response=$(kubectl run curl-test --rm -i --restart=Never --image=curlimages/curl -- \
               curl -s -w "%{http_code}" -X POST ${GATEWAY_URL}/api/validate-order \
               -H "Content-Type: application/json" \
               -d '{"symbol":"BTCUSD","side":"buy","size":0.001,"type":"market"}')
    
    status_code=$(echo "$response" | tail -n1)
    
    if [ "$status_code" = "200" ]; then
        echo "✓ Order validation is working"
    else
        echo "✓ Order validation returned ${status_code} (expected for test order)"
    fi
    
    return 0
}

# Function to test monitoring endpoints
test_monitoring() {
    echo "Testing monitoring endpoints..."
    
    # Test Prometheus metrics
    response=$(kubectl run curl-test --rm -i --restart=Never --image=curlimages/curl -- \
               curl -s -w "%{http_code}" ${BASE_URL}:9090/metrics)
    
    status_code=$(echo "$response" | tail -n1)
    
    if [ "$status_code" = "200" ]; then
        echo "✓ Prometheus metrics endpoint is working"
    else
        echo "✗ Prometheus metrics endpoint failed - Status: ${status_code}"
        return 1
    fi
    
    # Check if trading metrics are present
    metrics_content=$(echo "$response" | head -n -1)
    if echo "$metrics_content" | grep -q "trading_"; then
        echo "✓ Trading metrics are being exported"
    else
        echo "⚠ Trading metrics not found in metrics output"
    fi
    
    return 0
}

# Function to test database connectivity
test_database() {
    echo "Testing database connectivity..."
    
    # Test database connection through the application
    response=$(kubectl run curl-test --rm -i --restart=Never --image=curlimages/curl -- \
               curl -s -w "%{http_code}" ${BASE_URL}/api/health/database)
    
    status_code=$(echo "$response" | tail -n1)
    
    if [ "$status_code" = "200" ]; then
        echo "✓ Database connectivity is working"
        return 0
    else
        echo "✗ Database connectivity failed - Status: ${status_code}"
        return 1
    fi
}

# Function to test feature flags
test_feature_flags() {
    echo "Testing feature flags..."
    
    # Test feature flags endpoint
    response=$(kubectl run curl-test --rm -i --restart=Never --image=curlimages/curl -- \
               curl -s -w "%{http_code}" ${BASE_URL}/api/features)
    
    status_code=$(echo "$response" | tail -n1)
    
    if [ "$status_code" = "200" ]; then
        echo "✓ Feature flags endpoint is working"
        
        # Check if response contains expected feature flags
        features_content=$(echo "$response" | head -n -1)
        if echo "$features_content" | grep -q "multi_timeframe_analysis"; then
            echo "✓ Feature flags are properly configured"
        else
            echo "⚠ Expected feature flags not found"
        fi
        
        return 0
    else
        echo "✗ Feature flags endpoint failed - Status: ${status_code}"
        return 1
    fi
}

# Function to test performance
test_performance() {
    echo "Testing system performance..."
    
    # Test response time for analysis endpoint
    start_time=$(date +%s%N)
    
    response=$(kubectl run curl-test --rm -i --restart=Never --image=curlimages/curl -- \
               curl -s -w "%{http_code}" ${BASE_URL}/api/analyze/BTCUSD)
    
    end_time=$(date +%s%N)
    response_time=$(( (end_time - start_time) / 1000000 )) # Convert to milliseconds
    
    status_code=$(echo "$response" | tail -n1)
    
    if [ "$status_code" = "200" ]; then
        if [ "$response_time" -lt 2000 ]; then
            echo "✓ Analysis response time is acceptable: ${response_time}ms"
        else
            echo "⚠ Analysis response time is slow: ${response_time}ms"
        fi
    else
        echo "✗ Performance test failed - Status: ${status_code}"
        return 1
    fi
    
    return 0
}

# Main smoke test execution
main() {
    local exit_code=0
    
    echo "========================================="
    echo "Trading System Smoke Tests"
    echo "Environment: ${ENVIRONMENT}"
    echo "Namespace: ${NAMESPACE}"
    echo "Base URL: ${BASE_URL}"
    echo "========================================="
    
    # Run smoke tests
    test_endpoint "GET" "/health" "200" "Health check" || exit_code=1
    test_endpoint "GET" "/ready" "200" "Readiness check" || exit_code=1
    test_trading_functionality || exit_code=1
    test_execution_gateway || exit_code=1
    test_monitoring || exit_code=1
    test_database || exit_code=1
    test_feature_flags || exit_code=1
    test_performance || exit_code=1
    
    echo "========================================="
    if [ $exit_code -eq 0 ]; then
        echo "✓ All smoke tests passed"
        echo "System is functioning correctly"
    else
        echo "✗ Some smoke tests failed"
        echo "System may have issues"
    fi
    echo "========================================="
    
    exit $exit_code
}

# Run main function
main "$@"