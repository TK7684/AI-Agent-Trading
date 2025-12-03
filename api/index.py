"""
Main API entry point for Vercel deployment.
This file handles routing requests to the appropriate serverless functions.
"""

import json
import os
import sys
from typing import Dict, Any, Optional

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class handler:
    """Main request handler for Vercel serverless functions."""

    def __init__(self, request):
        # Initialize request context
        self.request = request

    def __call__(self, *args, **kwargs):
        return self.handle_request(*args, **kwargs)

    def handle_request(self, request, response):
        """Handle the incoming request and route to appropriate function."""
        try:
            # Get request details
            method = request.get('method', 'GET')
            path = request.get('path', '/')
            query = request.get('query', {})
            body = request.get('body', '')

            # Route based on path
            if path.startswith('/api/trading'):
                return self.route_to_module('trading', request, response)
            elif path.startswith('/api/training'):
                return self.route_to_module('training', request, response)
            elif path.startswith('/api/strategies'):
                return self.route_to_module('strategies', request, response)
            elif path.startswith('/api/market'):
                return self.route_to_module('market', request, response)
            elif path == '/api/health':
                return self.route_to_module('health', request, response)
            elif path == '/api/cron/training':
                return self.route_to_module('cron_training', request, response)
            elif path == '/api/cron/strategy-update':
                return self.route_to_module('cron_strategy_update', request, response)
            elif path == '/api/cron/market-analysis':
                return self.route_to_module('cron_market_analysis', request, response)
            else:
                return self.send_error(response, 404, "Endpoint not found")
        except Exception as e:
            return self.send_error(response, 500, f"Internal server error: {str(e)}")

    def route_to_module(self, module_name, request, response):
        """Import and execute the appropriate module."""
        try:
            # Import the module dynamically
            module_path = f"api.functions.{module_name}"
            module = __import__(module_path, fromlist=['handler'])

            # Create request context
            request_context = {
                'method': request.get('method', 'GET'),
                'path': request.get('path', '/'),
                'headers': request.get('headers', {}),
                'body': request.get('body'),
                'query': request.get('query', {})
            }

            # Call the handler function
            result = module.handler(request_context)

            # Send response
            return self.send_response(response, result.get('statusCode', 200),
                              result.get('headers', {}),
                              result.get('body', ''))
        except ImportError as e:
            return self.send_error(response, 500, f"Module not found: {str(e)}")
        except Exception as e:
            return self.send_error(response, 500, f"Handler error: {str(e)}")



    def send_response(self, response, status_code: int, headers: Dict[str, str], body: str):
        """Send HTTP response."""
        # Set default headers
        headers['Content-Type'] = headers.get('Content-Type', 'application/json')
        headers['Access-Control-Allow-Origin'] = '*'
        headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'

        # Send response
        response.set_status_code(status_code)
        response.set_headers(headers)
        response.send(body)

    def send_error(self, response, status_code: int, message: str):
        """Send error response."""
        error_body = json.dumps({
            'error': True,
            'message': message
        })
        return self.send_response(response, status_code, {'Content-Type': 'application/json'}, error_body)
