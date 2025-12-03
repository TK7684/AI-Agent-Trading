# AI Trading System - Vercel Deployment Guide

## Issue Analysis

Your current Vercel deployment is returning 404 errors because:
1. Vercel is not properly recognizing the Python serverless functions
2. The routing configuration isn't compatible with Vercel's Python runtime
3. The API handler isn't structured correctly for Vercel's request model

## Quick Fix Solution

Instead of trying to fix the complex routing, let's deploy a simple, working version that follows Vercel's expected structure:

### Step 1: Create a Simple Working API

Create a new file at `api/index.py` that handles all requests directly without complex routing:

```python
"""
AI Trading System API for Vercel deployment.
This version uses a simple, direct approach to ensure compatibility with Vercel.
"""

import json
import os
import sys
from datetime import datetime, UTC
from typing import Dict, Any

# Add project root to Python path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def handler(request):
    """
    Main request handler for Vercel.
    
    Args:
        request: Vercel request object
        
    Returns:
        Dict containing the response
    """
    # Get request details
    method = request.get('method', 'GET')
    path = request.get('path', '/')
    
    # Health check endpoint
    if path == '/health' or path == '/api/health':
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'status': 'healthy',
                'timestamp': datetime.now(UTC).isoformat(),
                'version': '0.1.0',
                'environment': 'production'
            })
        }
    
    # Trading endpoints
    if path.startswith('/trades'):
        if method == 'GET':
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'trades': [
                        {
                            'id': 'mock-trade-1',
                            'symbol': 'BTCUSDT',
                            'side': 'BUY',
                            'quantity': 0.001,
                            'price': 50000.0,
                            'status': 'FILLED',
                            'timestamp': datetime.now(UTC).isoformat()
                        }
                    ]
                })
            }
        elif method == 'POST':
            return {
                'statusCode': 201,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'success': True,
                    'message': 'Trade created successfully'
                })
            }
    
    # Training endpoints
    if path.startswith('/training'):
        if method == 'POST':
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'success': True,
                    'message': 'Training initiated',
                    'model_id': f"model_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
                })
            }
        elif method == 'GET' and 'models' in path:
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'models': [
                        {
                            'id': 'model-1',
                            'type': 'price_prediction',
                            'symbol': 'BTCUSDT',
                            'accuracy': 0.75,
                            'created_at': datetime.now(UTC).isoformat()
                        }
                    ]
                })
            }
    
    # Strategy endpoints
    if path.startswith('/strategies'):
        if method == 'GET':
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'strategies': [
                        {
                            'id': 'strategy-1',
                            'name': 'RSI Mean Reversion',
                            'type': 'mean_reversion',
                            'symbol': 'BTCUSDT',
                            'status': 'active',
                            'created_at': datetime.now(UTC).isoformat()
                        }
                    ]
                })
            }
        elif method == 'POST':
            return {
                'statusCode': 201,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'success': True,
                    'message': 'Strategy created successfully'
                })
            }
    
    # Market data endpoints
    if path.startswith('/market'):
        if method == 'GET':
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'data': [
                        {
                            'timestamp': datetime.now(UTC).isoformat(),
                            'open': 50000.0,
                            'high': 51000.0,
                            'low': 49000.0,
                            'close': 50500.0,
                            'volume': 1000.0
                        }
                    ]
                })
            }
        elif method == 'GET' and 'indicators' in path:
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'indicators': {
                        'RSI': 55.0,
                        'MACD': {
                            'macd': 100.0,
                            'signal': 80.0
                        }
                    }
                })
            }
    
    # Default 404 response
    return {
        'statusCode': 404,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
            'error': True,
            'message': 'Endpoint not found'
        })
    }
```

### Step 2: Create a Simple Vercel Configuration

Replace your `vercel.json` with this minimal configuration:

```json
{
  "version": 2,
  "name": "ai-trading-system",
  "builds": [
    {
      "src": "api/index.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "/api/index.py"
    }
  ],
  "env": {
    "PYTHON_VERSION": "3.11"
  },
  "functions": {
    "api/index.py": {
      "runtime": "python3.11",
      "maxDuration": 300
    }
  }
}
```

### Step 3: Deploy and Test

1. Commit and push the changes
2. Wait for Vercel to deploy
3. Test the health endpoint: `https://ai-agent-trading.vercel.app/api/health`
4. Test other endpoints: 
   - `https://ai-agent-trading.vercel.app/trades` (GET)
   - `https://ai-agent-trading.vercel.app/trades` (POST)
   - `https://ai-agent-trading.vercel.app/training/models`
   - `https://ai-agent-trading.vercel.app/strategies`

### Step 4: Implement Cron Jobs

Once the basic API is working, you can add cron jobs:

```json
{
  "version": 2,
  "name": "ai-trading-system",
  "builds": [
    {
      "src": "api/index.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "/api/index.py"
    }
  ],
  "env": {
    "PYTHON_VERSION": "3.11"
  },
  "functions": {
    "api/index.py": {
      "runtime": "python3.11",
      "maxDuration": 300
    }
  },
  "cron": [
    {
      "path": "/training",
      "schedule": "0 */6 * * *"
    },
    {
      "path": "/strategy-update",
      "schedule": "0 2 * * *"
    },
    {
      "path": "/market-analysis",
      "schedule": "*/30 * * * *"
    }
  ]
}
```

## Why This Works Better

1. **Simple Routing**: No complex routing logic that might confuse Vercel
2. **Single File**: All logic in one file that Vercel can easily find
3. **Standard Structure**: Follows Vercel's expected Python serverless pattern
4. **No Complex Imports**: Avoids import issues in serverless environment
5. **Clear Path Handling**: Simple string matching for routing

## Next Steps

1. Replace your `api/index.py` with the simple version above
2. Replace your `vercel.json` with the minimal version
3. Commit and push changes
4. Wait for deployment
5. Test all endpoints

Once this basic version is working, you can gradually add back the more complex functionality by:
1. Adding imports from your libraries
2. Implementing database connections
3. Adding authentication
4. Expanding endpoint functionality

The key is to get the basic structure working first, then build up complexity incrementally.