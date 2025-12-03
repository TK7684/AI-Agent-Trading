# AI Trading System - Vercel Deployment Fix

## Current Issue

The Vercel deployment is returning 404 errors for all API endpoints. This is likely because:

1. Vercel isn't properly recognizing the Python serverless functions
2. The routing configuration isn't working as expected
3. The Python runtime might not be properly configured

## Immediate Fix

### Step 1: Create Proper Serverless Function Structure

Vercel expects Python functions to be in the `/api` directory with a specific structure. Let's create the correct structure:

```bash
# Create a proper Vercel Python structure
mkdir -p api/trading
mkdir -p api/training
mkdir -p api/strategies
mkdir -p api/market
mkdir -p api/cron
```

### Step 2: Create Individual Function Files

Each endpoint needs to be its own file in the correct structure:

1. **api/trading/index.py** (for trading endpoints)
2. **api/training/index.py** (for training endpoints)
3. **api/strategies/index.py** (for strategy endpoints)
4. **api/market/index.py** (for market data endpoints)
5. **api/health.py** (for health check)
6. **api/cron/training.py** (for training cron)
7. **api/cron/strategy.py** (for strategy cron)
8. **api/cron/market.py** (for market analysis cron)

### Step 3: Create Correct Vercel Configuration

Replace `vercel.json` with:

```json
{
  "version": 2,
  "name": "ai-trading-system",
  "builds": [
    {
      "src": "api/trading/index.py",
      "use": "@vercel/python"
    },
    {
      "src": "api/training/index.py",
      "use": "@vercel/python"
    },
    {
      "src": "api/strategies/index.py",
      "use": "@vercel/python"
    },
    {
      "src": "api/market/index.py",
      "use": "@vercel/python"
    },
    {
      "src": "api/health.py",
      "use": "@vercel/python"
    },
    {
      "src": "api/cron/training.py",
      "use": "@vercel/python"
    },
    {
      "src": "api/cron/strategy.py",
      "use": "@vercel/python"
    },
    {
      "src": "api/cron/market.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/api/trading/(.*)",
      "dest": "/api/trading/index.py"
    },
    {
      "src": "/api/training/(.*)",
      "dest": "/api/training/index.py"
    },
    {
      "src": "/api/strategies/(.*)",
      "dest": "/api/strategies/index.py"
    },
    {
      "src": "/api/market/(.*)",
      "dest": "/api/market/index.py"
    },
    {
      "src": "/api/health",
      "dest": "/api/health.py"
    },
    {
      "src": "/api/cron/training",
      "dest": "/api/cron/training.py"
    },
    {
      "src": "/api/cron/strategy",
      "dest": "/api/cron/strategy.py"
    },
    {
      "src": "/api/cron/market",
      "dest": "/api/cron/market.py"
    }
  ],
  "env": {
    "PYTHON_VERSION": "3.11"
  },
  "functions": {
    "api/trading/index.py": {
      "runtime": "python3.11",
      "maxDuration": 30
    },
    "api/training/index.py": {
      "runtime": "python3.11",
      "maxDuration": 300
    },
    "api/strategies/index.py": {
      "runtime": "python3.11",
      "maxDuration": 60
    },
    "api/market/index.py": {
      "runtime": "python3.11",
      "maxDuration": 30
    },
    "api/health.py": {
      "runtime": "python3.11",
      "maxDuration": 30
    },
    "api/cron/training.py": {
      "runtime": "python3.11",
      "maxDuration": 300
    },
    "api/cron/strategy.py": {
      "runtime": "python3.11",
      "maxDuration": 300
    },
    "api/cron/market.py": {
      "runtime": "python3.11",
      "maxDuration": 300
    }
  },
  "cron": [
    {
      "path": "/api/cron/training",
      "schedule": "0 */6 * * *"
    },
    {
      "path": "/api/cron/strategy",
      "schedule": "0 2 * * *"
    },
    {
      "path": "/api/cron/market",
      "schedule": "*/30 * * * *"
    }
  ]
}
```

### Step 4: Create Individual Function Files

Each function file should follow this structure:

```python
# api/trading/index.py
import json
import os
import sys
from http.server import BaseHTTPRequestHandler
from typing import Dict, Any

# Add project root to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self._handle_request("GET")

    def do_POST(self):
        self._handle_request("POST")

    def _handle_request(self, method):
        # Get request details
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else ''
        
        # Parse path to determine sub-route
        path = self.path
        if path.startswith('/api/trading/'):
            path = path[len('/api/trading/'):]
        
        # Handle different endpoints
        if path == 'trades':
            # Handle trades endpoint
            response = handle_trades(method, body)
        elif path == 'positions':
            # Handle positions endpoint
            response = handle_positions(method, body)
        else:
            response = {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': True, 'message': 'Endpoint not found'})
            }
        
        # Send response
        self.send_response(response['statusCode'])
        self.send_header('Content-Type', response['headers'].get('Content-Type', 'application/json'))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
        self.wfile.write(response['body'].encode('utf-8'))

def handle_trades(method, body):
    """Handle trades endpoint."""
    if method == 'GET':
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'trades': []})
        }
    elif method == 'POST':
        # Handle creating a trade
        return {
            'statusCode': 201,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'success': True, 'message': 'Trade created'})
        }

def handle_positions(method, body):
    """Handle positions endpoint."""
    if method == 'GET':
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'positions': []})
        }
```

### Step 5: Test and Deploy

1. Create the new structure
2. Copy relevant code to each function file
3. Commit and push changes
4. Wait for Vercel to deploy
5. Test endpoints

## Alternative Approach: Single Function Router

If the above doesn't work, try this simpler approach with a single function that handles all routing:

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
      "path": "/cron/training",
      "schedule": "0 */6 * * *"
    },
    {
      "path": "/cron/strategy",
      "schedule": "0 2 * * *"
    },
    {
      "path": "/cron/market",
      "schedule": "*/30 * * * *"
    }
  ]
}
```

With this `api/index.py`:

```python
from http.server import BaseHTTPRequestHandler
import json
import os
import sys

# Add project root to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self._handle_request("GET")

    def do_POST(self):
        self._handle_request("POST")

    def _handle_request(self, method):
        # Get request details
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else ''
        
        # Simple routing based on path
        if self.path.startswith('/api/health'):
            response = handle_health()
        elif self.path.startswith('/api/trading/'):
            response = handle_trading(method, body)
        elif self.path.startswith('/api/training/'):
            response = handle_training(method, body)
        elif self.path.startswith('/api/strategies/'):
            response = handle_strategies(method, body)
        elif self.path.startswith('/api/market/'):
            response = handle_market(method, body)
        else:
            response = {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': True, 'message': 'Endpoint not found'})
            }
        
        # Send response
        self.send_response(response['statusCode'])
        self.send_header('Content-Type', response['headers'].get('Content-Type', 'application/json'))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
        self.wfile.write(response['body'].encode('utf-8'))

def handle_health():
    """Handle health check."""
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
            'status': 'healthy',
            'timestamp': '2023-12-03T06:00:00Z',
            'version': '0.1.0'
        })
    }

def handle_trading(method, body):
    """Handle trading endpoints."""
    if method == 'GET' and 'trades' in self.path:
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'trades': []})
        }
    elif method == 'POST' and 'trades' in self.path:
        return {
            'statusCode': 201,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'success': True, 'message': 'Trade created'})
        }
    else:
        return {
            'statusCode': 404,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': True, 'message': 'Endpoint not found'})
        }

def handle_training(method, body):
    """Handle training endpoints."""
    # Similar implementation for training endpoints
    pass

def handle_strategies(method, body):
    """Handle strategy endpoints."""
    # Similar implementation for strategy endpoints
    pass

def handle_market(method, body):
    """Handle market data endpoints."""
    # Similar implementation for market data endpoints
    pass
```

## Next Steps

1. Choose one of the approaches above
2. Implement the solution
3. Test locally with Vercel CLI: `vercel dev`
4. Deploy to Vercel
5. Test with the deployment test script

The issue is likely with how Vercel interprets the Python serverless function structure. The simpler single-function approach is more likely to work reliably.