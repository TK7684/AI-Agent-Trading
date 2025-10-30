#!/bin/bash

# Health check script for trading dashboard deployment
set -e

echo "🏥 Trading Dashboard Health Check"
echo "================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
FRONTEND_URL=${FRONTEND_URL:-"http://localhost"}
API_URL=${API_URL:-"http://localhost:8000"}
TIMEOUT=${TIMEOUT:-10}

# Function to check service health
check_service() {
    local name=$1
    local url=$2
    local expected_status=${3:-200}
    
    echo -n "Checking $name... "
    
    if response=$(curl -s -o /dev/null -w "%{http_code}" --max-time $TIMEOUT "$url"); then
        if [ "$response" -eq "$expected_status" ]; then
            echo -e "${GREEN}✓ OK${NC} (HTTP $response)"
            return 0
        else
            echo -e "${RED}✗ FAIL${NC} (HTTP $response, expected $expected_status)"
            return 1
        fi
    else
        echo -e "${RED}✗ FAIL${NC} (Connection failed)"
        return 1
    fi
}

# Function to check WebSocket connection
check_websocket() {
    local name=$1
    local url=$2
    
    echo -n "Checking $name WebSocket... "
    
    # Use a simple WebSocket test (requires websocat or similar tool)
    if command -v websocat >/dev/null 2>&1; then
        if timeout $TIMEOUT websocat --exit-on-eof "$url" <<< "ping" >/dev/null 2>&1; then
            echo -e "${GREEN}✓ OK${NC}"
            return 0
        else
            echo -e "${RED}✗ FAIL${NC}"
            return 1
        fi
    else
        echo -e "${YELLOW}⚠ SKIP${NC} (websocat not available)"
        return 0
    fi
}

# Main health checks
failed_checks=0

echo "Frontend Services:"
check_service "Dashboard UI" "$FRONTEND_URL/health" || ((failed_checks++))

echo ""
echo "Backend Services:"
check_service "Trading API" "$API_URL/health" || ((failed_checks++))
check_service "API Authentication" "$API_URL/api/health" || ((failed_checks++))

echo ""
echo "WebSocket Services:"
check_websocket "Trading WebSocket" "ws://localhost:8000/ws/trading" || ((failed_checks++))

echo ""
echo "Database Services:"
# Check if PostgreSQL is accessible through API
check_service "Database (via API)" "$API_URL/api/system/health" || ((failed_checks++))

echo ""
echo "Summary:"
echo "========"

if [ $failed_checks -eq 0 ]; then
    echo -e "${GREEN}✓ All services are healthy!${NC}"
    exit 0
else
    echo -e "${RED}✗ $failed_checks service(s) failed health check${NC}"
    exit 1
fi