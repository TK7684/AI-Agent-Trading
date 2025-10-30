#!/bin/bash

# Health check script for trading system deployment
# Usage: ./health-check.sh <environment> <color>

set -e

ENVIRONMENT=${1:-production}
COLOR=${2:-blue}
NAMESPACE=${ENVIRONMENT}
TIMEOUT=300
RETRY_INTERVAL=10

echo "Starting health check for ${ENVIRONMENT} environment (${COLOR} deployment)"

# Function to check if a service is responding
check_service() {
    local service_name=$1
    local port=$2
    local path=$3
    local expected_status=${4:-200}
    
    echo "Checking ${service_name}..."
    
    for i in $(seq 1 $((TIMEOUT / RETRY_INTERVAL))); do
        if kubectl exec -n ${NAMESPACE} deployment/trading-system-${COLOR} -- \
           curl -s -o /dev/null -w "%{http_code}" http://localhost:${port}${path} | grep -q ${expected_status}; then
            echo "✓ ${service_name} is healthy"
            return 0
        fi
        
        echo "  Attempt ${i}/${$((TIMEOUT / RETRY_INTERVAL))}: ${service_name} not ready, waiting..."
        sleep ${RETRY_INTERVAL}
    done
    
    echo "✗ ${service_name} health check failed"
    return 1
}

# Function to check database connectivity
check_database() {
    echo "Checking database connectivity..."
    
    if kubectl exec -n ${NAMESPACE} deployment/trading-system-${COLOR} -- \
       python -c "
import psycopg2
import os
try:
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    conn.close()
    print('Database connection successful')
except Exception as e:
    print(f'Database connection failed: {e}')
    exit(1)
"; then
        echo "✓ Database connectivity is healthy"
        return 0
    else
        echo "✗ Database connectivity check failed"
        return 1
    fi
}

# Function to check Redis connectivity
check_redis() {
    echo "Checking Redis connectivity..."
    
    if kubectl exec -n ${NAMESPACE} deployment/trading-system-${COLOR} -- \
       python -c "
import redis
import os
try:
    r = redis.from_url(os.environ['REDIS_URL'])
    r.ping()
    print('Redis connection successful')
except Exception as e:
    print(f'Redis connection failed: {e}')
    exit(1)
"; then
        echo "✓ Redis connectivity is healthy"
        return 0
    else
        echo "✗ Redis connectivity check failed"
        return 1
    fi
}

# Function to check trading system functionality
check_trading_functionality() {
    echo "Checking trading system functionality..."
    
    # Check if system can analyze market data
    if kubectl exec -n ${NAMESPACE} deployment/trading-system-${COLOR} -- \
       curl -s -f http://localhost:8080/api/analyze/BTCUSD > /dev/null; then
        echo "✓ Market analysis endpoint is working"
    else
        echo "✗ Market analysis endpoint failed"
        return 1
    fi
    
    # Check if system is not in safe mode (unless expected)
    SAFE_MODE=$(kubectl exec -n ${NAMESPACE} deployment/trading-system-${COLOR} -- \
                curl -s http://localhost:8080/api/status | jq -r .safe_mode)
    
    if [ "$SAFE_MODE" = "false" ]; then
        echo "✓ System is not in safe mode"
    else
        echo "⚠ System is in safe mode"
    fi
    
    return 0
}

# Function to check metrics collection
check_metrics() {
    echo "Checking metrics collection..."
    
    # Check Prometheus metrics endpoint
    if kubectl exec -n ${NAMESPACE} deployment/trading-system-${COLOR} -- \
       curl -s http://localhost:9090/metrics | grep -q "trading_"; then
        echo "✓ Metrics are being collected"
        return 0
    else
        echo "✗ Metrics collection failed"
        return 1
    fi
}

# Function to check resource usage
check_resources() {
    echo "Checking resource usage..."
    
    # Get pod resource usage
    RESOURCE_INFO=$(kubectl top pod -n ${NAMESPACE} -l color=${COLOR} --no-headers)
    
    if [ -n "$RESOURCE_INFO" ]; then
        echo "✓ Resource usage:"
        echo "$RESOURCE_INFO"
        
        # Check if CPU usage is reasonable (< 80%)
        CPU_USAGE=$(echo "$RESOURCE_INFO" | awk '{print $2}' | sed 's/m//' | head -1)
        if [ "$CPU_USAGE" -lt 800 ]; then
            echo "✓ CPU usage is within normal limits"
        else
            echo "⚠ High CPU usage detected: ${CPU_USAGE}m"
        fi
        
        return 0
    else
        echo "✗ Could not retrieve resource usage"
        return 1
    fi
}

# Function to run smoke tests
run_smoke_tests() {
    echo "Running smoke tests..."
    
    # Test basic API endpoints
    ENDPOINTS=(
        "/health:8080"
        "/ready:8080"
        "/metrics:9090"
        "/health:3000"
    )
    
    for endpoint in "${ENDPOINTS[@]}"; do
        IFS=':' read -r path port <<< "$endpoint"
        if kubectl exec -n ${NAMESPACE} deployment/trading-system-${COLOR} -- \
           curl -s -f http://localhost:${port}${path} > /dev/null; then
            echo "✓ ${path} endpoint is responding"
        else
            echo "✗ ${path} endpoint failed"
            return 1
        fi
    done
    
    return 0
}

# Main health check execution
main() {
    local exit_code=0
    
    echo "========================================="
    echo "Trading System Health Check"
    echo "Environment: ${ENVIRONMENT}"
    echo "Color: ${COLOR}"
    echo "Namespace: ${NAMESPACE}"
    echo "========================================="
    
    # Wait for pods to be ready
    echo "Waiting for pods to be ready..."
    if ! kubectl wait --for=condition=ready pod -l color=${COLOR} -n ${NAMESPACE} --timeout=300s; then
        echo "✗ Pods failed to become ready within timeout"
        exit 1
    fi
    echo "✓ All pods are ready"
    
    # Run health checks
    check_service "Orchestrator" "8080" "/health" || exit_code=1
    check_service "Execution Gateway" "3000" "/health" || exit_code=1
    check_database || exit_code=1
    check_redis || exit_code=1
    check_trading_functionality || exit_code=1
    check_metrics || exit_code=1
    check_resources || exit_code=1
    run_smoke_tests || exit_code=1
    
    echo "========================================="
    if [ $exit_code -eq 0 ]; then
        echo "✓ All health checks passed"
        echo "System is ready for traffic"
    else
        echo "✗ Some health checks failed"
        echo "System is NOT ready for traffic"
    fi
    echo "========================================="
    
    exit $exit_code
}

# Run main function
main "$@"