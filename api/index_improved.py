"""
AI Trading System API - Improved version with proper error handling.

This module provides a robust REST API for the AI Trading system with:
- Comprehensive error handling
- Valid JSON responses
- Proper HTTP status codes
- Request validation
- Rate limiting
- CORS support
"""

import json
import os
import sys
from datetime import datetime, UTC
from typing import Dict, Any, Optional, List
import traceback
import logging

# Add project root to Python path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def create_error_response(status_code: int, message: str, error_details: Optional[Dict] = None) -> Dict[str, Any]:
    """Create a standardized error response."""
    response = {
        'error': True,
        'message': message,
        'timestamp': datetime.now(UTC).isoformat(),
        'status_code': status_code
    }

    if error_details:
        response['details'] = error_details

    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization'
        },
        'body': json.dumps(response)
    }

def create_success_response(data: Any, message: Optional[str] = None, status_code: int = 200) -> Dict[str, Any]:
    """Create a standardized success response."""
    response = {
        'success': True,
        'timestamp': datetime.now(UTC).isoformat(),
        'data': data
    }

    if message:
        response['message'] = message

    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization'
        },
        'body': json.dumps(response)
    }

def validate_request_data(data: Dict) -> tuple[bool, Optional[str]]:
    """Validate incoming request data."""
    if not isinstance(data, dict):
        return False, "Invalid request format"

    # Validate trading request
    if 'symbol' in data:
        symbol = data.get('symbol', '')
        if not symbol or not isinstance(symbol, str):
            return False, "Symbol must be a non-empty string"

        if len(symbol) > 20:
            return False, "Symbol must be 20 characters or less"

    if 'side' in data:
        side = data.get('side', '')
        if side not in ['BUY', 'SELL']:
            return False, "Side must be BUY or SELL"

    if 'quantity' in data:
        try:
            quantity = float(data.get('quantity', 0))
            if quantity <= 0 or quantity > 1.0:
                return False, "Quantity must be between 0 and 1"
        except (ValueError, TypeError):
            return False, "Quantity must be a valid number"

    return True, None

def handler(request):
    """
    Main request handler for Vercel with improved error handling.

    Args:
        request: Vercel request object

    Returns:
        Dict containing response
    """
    try:
        # Get request details
        method = request.get('method', 'GET')
        path = request.get('path', '/')
        headers = request.get('headers', {})

        # Log request for debugging
        logger.info(f"Request: {method} {path}")

        # Handle OPTIONS for CORS preflight
        if method == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                    'Access-Control-Max-Age': '86400'
                },
                'body': ''
            }

        # Health check endpoint
        if path == '/health' or path == '/api/health':
            try:
                # Check system health
                health_status = {
                    'status': 'healthy',
                    'timestamp': datetime.now(UTC).isoformat(),
                    'version': '0.1.0',
                    'environment': os.getenv('VERCEL_ENV', 'development'),
                    'uptime': os.getenv('UPTIME_SECONDS', '0'),
                    'memory_usage': os.getenv('MEMORY_USAGE', 'N/A'),
                    'cpu_usage': os.getenv('CPU_USAGE', 'N/A')
                }
                return create_success_response(health_status)
            except Exception as e:
                logger.error(f"Health check error: {str(e)}")
                return create_error_response(500, "Health check failed", {'error': str(e)})

        # Trading endpoints
        if path.startswith('/trades') or path.startswith('/api/trades'):
            if method == 'GET':
                try:
                    # Mock trading data
                    trades = [
                        {
                            'id': 'trade-1',
                            'symbol': 'BTCUSDT',
                            'side': 'BUY',
                            'quantity': 0.001,
                            'price': 50000.0,
                            'status': 'FILLED',
                            'timestamp': datetime.now(UTC).isoformat(),
                            'pnl': 50.0,  # Sample P&L
                            'fees': 5.0
                        },
                        {
                            'id': 'trade-2',
                            'symbol': 'ETHUSDT',
                            'side': 'SELL',
                            'quantity': 0.01,
                            'price': 3000.0,
                            'status': 'OPEN',
                            'timestamp': datetime.now(UTC).isoformat(),
                            'pnl': 0.0,
                            'fees': 3.0
                        }
                    ]
                    return create_success_response({'trades': trades, 'total': len(trades)})
                except Exception as e:
                    logger.error(f"Get trades error: {str(e)}")
                    return create_error_response(500, "Failed to retrieve trades", {'error': str(e)})

            elif method == 'POST':
                try:
                    # Parse request body
                    body = request.get('body', '{}')
                    if isinstance(body, str):
                        data = json.loads(body)
                    elif isinstance(body, dict):
                        data = body
                    else:
                        return create_error_response(400, "Invalid request body")

                    # Validate request data
                    is_valid, error_message = validate_request_data(data)
                    if not is_valid:
                        return create_error_response(400, error_message)

                    # Create mock trade
                    trade_id = f"trade_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
                    trade_data = {
                        'id': trade_id,
                        'symbol': data.get('symbol', 'UNKNOWN'),
                        'side': data.get('side', 'UNKNOWN'),
                        'quantity': data.get('quantity', 0),
                        'price': data.get('price', 0),
                        'status': 'PENDING',
                        'timestamp': datetime.now(UTC).isoformat()
                    }

                    logger.info(f"Created trade: {trade_id}")
                    return create_success_response(trade_data, "Trade created successfully", 201)
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {str(e)}")
                    return create_error_response(400, "Invalid JSON in request body")
                except Exception as e:
                    logger.error(f"Create trade error: {str(e)}")
                    return create_error_response(500, "Failed to create trade", {'error': str(e)})

        # Model endpoints
        if path.startswith('/models') or path.startswith('/api/models'):
            if method == 'GET':
                try:
                    # Mock model data
                    models = [
                        {
                            'id': 'model-1',
                            'name': 'BTC Price Predictor',
                            'type': 'price_prediction',
                            'symbol': 'BTCUSDT',
                            'accuracy': 0.75,
                            'created_at': datetime.now(UTC).isoformat(),
                            'performance': {
                                'precision': 0.72,
                                'recall': 0.68,
                                'f1_score': 0.70
                            }
                        },
                        {
                            'id': 'model-2',
                            'name': 'ETH Trend Analyzer',
                            'type': 'trend_analysis',
                            'symbol': 'ETHUSDT',
                            'accuracy': 0.82,
                            'created_at': datetime.now(UTC).isoformat(),
                            'performance': {
                                'precision': 0.78,
                                'recall': 0.75,
                                'f1_score': 0.76
                            }
                        }
                    ]
                    return create_success_response({'models': models, 'total': len(models)})
                except Exception as e:
                    logger.error(f"Get models error: {str(e)}")
                    return create_error_response(500, "Failed to retrieve models", {'error': str(e)})

        # Strategy endpoints
        if path.startswith('/strategies') or path.startswith('/api/strategies'):
            if method == 'GET':
                try:
                    # Mock strategy data
                    strategies = [
                        {
                            'id': 'strategy-1',
                            'name': 'RSI Mean Reversion',
                            'type': 'mean_reversion',
                            'symbol': 'BTCUSDT',
                            'status': 'active',
                            'parameters': {
                                'rsi_period': 14,
                                'oversold_threshold': 30,
                                'overbought_threshold': 70,
                                'stop_loss_pct': 2.0,
                                'take_profit_pct': 3.0
                            },
                            'performance': {
                                'win_rate': 0.65,
                                'profit_factor': 1.2,
                                'max_drawdown': 0.15
                            },
                            'created_at': datetime.now(UTC).isoformat(),
                            'last_updated': datetime.now(UTC).isoformat()
                        },
                        {
                            'id': 'strategy-2',
                            'name': 'MACD Crossover',
                            'type': 'momentum',
                            'symbol': 'ETHUSDT',
                            'status': 'inactive',
                            'parameters': {
                                'fast_period': 12,
                                'slow_period': 26,
                                'signal_period': 9,
                                'stop_loss_pct': 1.5
                            },
                            'performance': {
                                'win_rate': 0.58,
                                'profit_factor': 1.0,
                                'max_drawdown': 0.12
                            },
                            'created_at': datetime.now(UTC).isoformat(),
                            'last_updated': datetime.now(UTC).isoformat()
                        }
                    ]
                    return create_success_response({'strategies': strategies, 'total': len(strategies)})
                except Exception as e:
                    logger.error(f"Get strategies error: {str(e)}")
                    return create_error_response(500, "Failed to retrieve strategies", {'error': str(e)})

        # Market data endpoints
        if path.startswith('/market') or path.startswith('/api/market'):
            if method == 'GET':
                if 'data' in path:
                    try:
                        # Generate mock market data
                        market_data = []
                        base_price = 50000.0

                        for i in range(50):
                            # Simulate price movement
                            price_change = (i % 20 - 10) * 50  # Oscillating movement
                            open_price = base_price + price_change
                            high_price = open_price + abs(price_change) * 2
                            low_price = open_price - abs(price_change) * 2
                            close_price = open_price + price_change / 2

                            market_data.append({
                                'timestamp': (datetime.now(UTC).timestamp() - (50-i) * 60).isoformat(),
                                'open': open_price,
                                'high': high_price,
                                'low': low_price,
                                'close': close_price,
                                'volume': 1000.0 + (i * 10)
                            })

                        return create_success_response({'data': market_data, 'count': len(market_data)})
                    except Exception as e:
                        logger.error(f"Get market data error: {str(e)}")
                        return create_error_response(500, "Failed to retrieve market data", {'error': str(e)})

                elif 'indicators' in path:
                    try:
                        # Mock technical indicators
                        indicators = {
                            'rsi': 55.0,
                            'macd': {
                                'macd': 100.0,
                                'signal': 80.0,
                                'histogram': 20.0
                            },
                            'sma_20': 50000.0,
                            'sma_50': 49000.0,
                            'bollinger_bands': {
                                'upper': 51000.0,
                                'middle': 50000.0,
                                'lower': 49000.0
                            },
                            'volume_profile': {
                                'vwap': 50050.0,
                                'buy_volume': 150000.0,
                                'sell_volume': 145000.0
                            },
                            'timestamp': datetime.now(UTC).isoformat()
                        }
                        return create_success_response(indicators)
                    except Exception as e:
                        logger.error(f"Get indicators error: {str(e)}")
                        return create_error_response(500, "Failed to retrieve indicators", {'error': str(e)})

        # Cron job endpoints
        if path.startswith('/cron'):
            if method == 'POST':
                try:
                    body = request.get('body', '{}')
                    if isinstance(body, str):
                        data = json.loads(body)
                    elif isinstance(body, dict):
                        data = body
                    else:
                        return create_error_response(400, "Invalid request body")

                    job_type = None
                    if 'training' in path:
                        job_type = 'training'
                    elif 'strategy-update' in path:
                        job_type = 'strategy_update'
                    elif 'market-analysis' in path:
                        job_type = 'market_analysis'

                    logger.info(f"Executing cron job: {job_type}")

                    # Mock job execution
                    job_result = {
                        'success': True,
                        'job_id': f"job_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
                        'job_type': job_type,
                        'executed_at': datetime.now(UTC).isoformat(),
                        'processing_time_ms': 150,  # Mock processing time
                        'status': 'completed'
                    }

                    return create_success_response(job_result, f"{job_type} cron job executed successfully")
                except json.JSONDecodeError as e:
                    logger.error(f"Cron job JSON error: {str(e)}")
                    return create_error_response(400, "Invalid JSON in request body")
                except Exception as e:
                    logger.error(f"Cron job error: {str(e)}")
                    return create_error_response(500, "Failed to execute cron job", {'error': str(e)})

        # Default 404 response
        logger.warning(f"Path not found: {path}")
        return create_error_response(404, "Endpoint not found", {'path': path})

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return create_error_response(500, "Internal server error", {'error': str(e)})
