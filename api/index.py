"""
Main API entry point for Vercel deployment.
This file handles routing requests to the appropriate serverless functions.
"""

import json
import os
import sys
from http.server import BaseHTTPRequestHandler
from typing import Dict, Any, Optional

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class handler(BaseHTTPRequestHandler):
    """Main request handler for Vercel serverless functions."""

    def __init__(self, *args, **kwargs):
        # Initialize request context
        self.request_id = None
        self.method = None
        self.path = None
        self.headers = {}
        self.body = None
        super().__init__(*args, **kwargs)

    def do_GET(self):
        """Handle GET requests."""
        self._handle_request("GET")

    def do_POST(self):
        """Handle POST requests."""
        self._handle_request("POST")

    def do_PUT(self):
        """Handle PUT requests."""
        self._handle_request("PUT")

    def do_DELETE(self):
        """Handle DELETE requests."""
        self._handle_request("DELETE")

    def _handle_request(self, method: str):
        """Route request to appropriate handler."""
        self.method = method
        self.path = self.path

        try:
            # Parse request body
            content_length = int(self.headers.get('Content-Length', 0))
            self.body = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else None

            # Route based on path
            if self.path.startswith('/api/trading'):
                self._route_to_module('trading')
            elif self.path.startswith('/api/training'):
                self._route_to_module('training')
            elif self.path.startswith('/api/strategies'):
                self._route_to_module('strategies')
            elif self.path.startswith('/api/market'):
                self._route_to_module('market')
            elif self.path == '/api/health':
                self._route_to_module('health')
            elif self.path == '/api/cron/training':
                self._route_to_module('cron_training')
            elif self.path == '/api/cron/strategy-update':
                self._route_to_module('cron_strategy_update')
            elif self.path == '/api/cron/market-analysis':
                self._route_to_module('cron_market_analysis')
            else:
                self._send_error(404, "Endpoint not found")
        except Exception as e:
            self._send_error(500, f"Internal server error: {str(e)}")

    def _route_to_module(self, module_name: str):
        """Import and execute the appropriate module."""
        try:
            # Import the module dynamically
            module_path = f"api.functions.{module_name}"
            module = __import__(module_path, fromlist=['handler'])

            # Create request context
            request_context = {
                'method': self.method,
                'path': self.path,
                'headers': dict(self.headers),
                'body': self.body,
                'query': self._parse_query_string()
            }

            # Call the handler function
            response = module.handler(request_context)

            # Send response
            self._send_response(response.get('statusCode', 200),
                              response.get('headers', {}),
                              response.get('body', ''))
        except ImportError as e:
            self._send_error(500, f"Module not found: {str(e)}")
        except Exception as e:
            self._send_error(500, f"Handler error: {str(e)}")

    def _parse_query_string(self) -> Dict[str, str]:
        """Parse query string from path."""
        if '?' not in self.path:
            return {}

        query_part = self.path.split('?', 1)[1]
        params = {}
        for param in query_part.split('&'):
            if '=' in param:
                key, value = param.split('=', 1)
                params[key] = value
        return params

    def _send_response(self, status_code: int, headers: Dict[str, str], body: str):
        """Send HTTP response."""
        self.send_response(status_code)

        # Set default headers
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')

        # Set custom headers
        for key, value in headers.items():
            self.send_header(key, value)

        self.end_headers()
        self.wfile.write(body.encode('utf-8'))

    def _send_error(self, status_code: int, message: str):
        """Send error response."""
        error_body = json.dumps({
            'error': True,
            'message': message
        })
        self._send_response(status_code, {}, error_body)
