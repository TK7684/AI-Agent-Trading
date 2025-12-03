import json
import os
import sys
from datetime import datetime, UTC

# Add project root to Python path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def handler(request):
    """
    Main request handler for Vercel.
    """
    # Get request details
    method = request.get("method", "GET")
    path = request.get("path", "/")
    headers = request.get("headers", {})
    body = request.get("body", "")

    # Health check endpoint
    if path == "/health" or path == "/api/health":
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "status": "healthy",
                "timestamp": datetime.now(UTC).isoformat(),
                "version": "0.1.0",
                "environment": "production"
            })
        }

    # Trading endpoints
    if path.startswith("/trades") or path.startswith("/api/trades"):
        if method == "GET":
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "trades": [
                        {
                            "id": "mock-trade-1",
                            "symbol": "BTCUSDT",
                            "side": "BUY",
                            "quantity": 0.001,
                            "price": 50000.0,
                            "status": "FILLED",
                            "timestamp": datetime.now(UTC).isoformat()
                        }
                    ]
                })
            }
        elif method == "POST":
            return {
                "statusCode": 201,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "success": True,
                    "message": "Trade created successfully",
                    "trade_id": f"trade_{datetime.now(UTC).strftime(%Y%m%d%H%M%S)}"
                })
            }

    # Default 404 response
    return {
        "statusCode": 404,
        "headers": {"Content-Type": application/json},
        "body": json.dumps({
            "error": True,
            "message": "Endpoint not found"
        })
    }

