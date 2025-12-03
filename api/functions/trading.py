"""
Trading API serverless function for Vercel deployment.
Handles all trading-related operations including order execution,
position management, and trade history.
"""

import json
import os
import sys
from datetime import datetime, UTC
from typing import Dict, Any, List, Optional

# Add the project root to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from libs.trading_models.base import Trade, Position, Portfolio, TradingSignal
    from libs.trading_models.orchestrator import TradingOrchestrator
    from libs.trading_models.risk_management import RiskManager
    from libs.trading_models.persistence import TradingPersistence
    from libs.trading_models.monitoring import get_metrics_collector
    from libs.trading_models.config_manager import get_config_manager
except ImportError:
    # Fallback for serverless environment
    class MockTrade:
        def __init__(self, **kwargs):
            self.id = kwargs.get('id', 'mock-id')
            self.symbol = kwargs.get('symbol', 'BTCUSDT')
            self.side = kwargs.get('side', 'BUY')
            self.quantity = kwargs.get('quantity', 0.001)
            self.price = kwargs.get('price', 50000.0)
            self.status = kwargs.get('status', 'FILLED')
            self.timestamp = kwargs.get('timestamp', datetime.now(UTC))

    Trade = MockTrade
    Position = Portfolio = TradingSignal = RiskManager = TradingPersistence = None
    get_metrics_collector = get_config_manager = lambda: None


def handler(request_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main handler for trading API requests.

    Args:
        request_context: Dictionary containing request information

    Returns:
        Dict containing the response
    """
    method = request_context.get('method', 'GET')
    path = request_context.get('path', '')
    body = request_context.get('body')
    headers = request_context.get('headers', {})
    query = request_context.get('query', {})

    # Initialize components if available
    orchestrator = None
    risk_manager = None
    persistence = None

    try:
        config = get_config_manager() if get_config_manager else None
        if config:
            orchestrator = TradingOrchestrator(config.get_trading_config())
            risk_manager = RiskManager(config.get_risk_config())
            persistence = TradingPersistence(config.get_database_config())
    except Exception as e:
        print(f"Warning: Could not initialize trading components: {e}")

    try:
        # Parse request body if present
        request_data = {}
        if body:
            try:
                request_data = json.loads(body)
            except json.JSONDecodeError:
                pass

        # Route based on path and method
        if path.endswith('/trades'):
            if method == 'GET':
                return handle_get_trades(persistence, query)
            elif method == 'POST':
                return handle_create_trade(request_data, orchestrator, risk_manager, persistence)

        elif path.endswith('/positions'):
            if method == 'GET':
                return handle_get_positions(persistence, query)

        elif path.endswith('/portfolio'):
            if method == 'GET':
                return handle_get_portfolio(persistence)

        elif path.endswith('/signals'):
            if method == 'GET':
                return handle_get_signals(persistence, query)
            elif method == 'POST':
                return handle_create_signal(request_data, persistence)

        elif '/trades/close' in path:
            if method == 'POST':
                return handle_close_trade(request_data, orchestrator, persistence)

        else:
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': True, 'message': 'Endpoint not found'})
            }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': True, 'message': f'Internal server error: {str(e)}'})
        }


def handle_get_trades(persistence, query: Dict[str, str]) -> Dict[str, Any]:
    """
    Handle GET request for trades.

    Args:
        persistence: Trading persistence instance
        query: Query parameters

    Returns:
        Dict containing the response
    """
    try:
        # Parse query parameters
        limit = int(query.get('limit', 100))
        offset = int(query.get('offset', 0))
        status = query.get('status')
        symbol = query.get('symbol')

        if persistence:
            # Get trades from database
            trades = persistence.get_trades(limit=limit, offset=offset, status=status, symbol=symbol)
            total = persistence.count_trades(status=status, symbol=symbol)

            trades_data = [trade.to_dict() for trade in trades]
        else:
            # Mock response
            trades_data = [
                {
                    'id': 'mock-trade-1',
                    'symbol': symbol or 'BTCUSDT',
                    'side': 'BUY',
                    'quantity': 0.001,
                    'price': 50000.0,
                    'status': status or 'FILLED',
                    'timestamp': datetime.now(UTC).isoformat()
                }
            ]
            total = 1

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'trades': trades_data,
                'total': total,
                'limit': limit,
                'offset': offset
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': True, 'message': f'Failed to get trades: {str(e)}'})
        }


def handle_create_trade(request_data: Dict[str, Any], orchestrator, risk_manager, persistence) -> Dict[str, Any]:
    """
    Handle POST request to create a trade.

    Args:
        request_data: Request body data
        orchestrator: Trading orchestrator instance
        risk_manager: Risk manager instance
        persistence: Trading persistence instance

    Returns:
        Dict containing the response
    """
    try:
        # Validate required fields
        required_fields = ['symbol', 'side', 'quantity', 'price']
        for field in required_fields:
            if field not in request_data:
                return {
                    'statusCode': 400,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({
                        'error': True,
                        'message': f'Missing required field: {field}'
                    })
                }

        # Create trade object
        trade_data = {
            'symbol': request_data['symbol'],
            'side': request_data['side'],
            'quantity': float(request_data['quantity']),
            'price': float(request_data['price']),
            'type': request_data.get('type', 'MARKET'),
            'timestamp': datetime.now(UTC),
            'status': 'PENDING'
        }

        # Check risk limits
        if risk_manager:
            risk_check = risk_manager.check_trade_risk(trade_data)
            if not risk_check['allowed']:
                return {
                    'statusCode': 403,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({
                        'error': True,
                        'message': 'Trade rejected by risk manager',
                        'reason': risk_check['reason']
                    })
                }

        # Execute trade
        if orchestrator:
            trade = orchestrator.execute_trade(trade_data)
        else:
            # Mock trade execution
            trade = Trade(
                id=f"trade-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
                **trade_data
            )
            trade.status = 'FILLED'

        # Save trade to database
        if persistence:
            persistence.save_trade(trade)

        return {
            'statusCode': 201,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'success': True,
                'trade': trade.to_dict() if hasattr(trade, 'to_dict') else trade.__dict__
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': True, 'message': f'Failed to create trade: {str(e)}'})
        }


def handle_get_positions(persistence, query: Dict[str, str]) -> Dict[str, Any]:
    """
    Handle GET request for positions.

    Args:
        persistence: Trading persistence instance
        query: Query parameters

    Returns:
        Dict containing the response
    """
    try:
        if persistence:
            positions = persistence.get_positions()
            positions_data = [position.to_dict() for position in positions]
        else:
            # Mock response
            positions_data = [
                {
                    'id': 'mock-position-1',
                    'symbol': query.get('symbol', 'BTCUSDT'),
                    'quantity': 0.001,
                    'side': 'LONG',
                    'entry_price': 50000.0,
                    'current_price': 51000.0,
                    'unrealized_pnl': 10.0,
                    'timestamp': datetime.now(UTC).isoformat()
                }
            ]

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'positions': positions_data
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': True, 'message': f'Failed to get positions: {str(e)}'})
        }


def handle_get_portfolio(persistence) -> Dict[str, Any]:
    """
    Handle GET request for portfolio.

    Args:
        persistence: Trading persistence instance

    Returns:
        Dict containing the response
    """
    try:
        if persistence:
            portfolio = persistence.get_portfolio()
            portfolio_data = portfolio.to_dict()
        else:
            # Mock response
            portfolio_data = {
                'id': 'mock-portfolio',
                'balance': 10000.0,
                'equity': 10100.0,
                'unrealized_pnl': 100.0,
                'realized_pnl': 50.0,
                'total_trades': 10,
                'winning_trades': 6,
                'losing_trades': 4,
                'win_rate': 0.6
            }

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'portfolio': portfolio_data
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': True, 'message': f'Failed to get portfolio: {str(e)}'})
        }


def handle_get_signals(persistence, query: Dict[str, str]) -> Dict[str, Any]:
    """
    Handle GET request for trading signals.

    Args:
        persistence: Trading persistence instance
        query: Query parameters

    Returns:
        Dict containing the response
    """
    try:
        # Parse query parameters
        limit = int(query.get('limit', 100))
        offset = int(query.get('offset', 0))
        symbol = query.get('symbol')

        if persistence:
            signals = persistence.get_signals(limit=limit, offset=offset, symbol=symbol)
            signals_data = [signal.to_dict() for signal in signals]
        else:
            # Mock response
            signals_data = [
                {
                    'id': 'mock-signal-1',
                    'symbol': symbol or 'BTCUSDT',
                    'action': 'BUY',
                    'strength': 0.8,
                    'confidence': 0.75,
                    'reason': 'Mock technical analysis',
                    'timestamp': datetime.now(UTC).isoformat()
                }
            ]

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'signals': signals_data
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': True, 'message': f'Failed to get signals: {str(e)}'})
        }


def handle_create_signal(request_data: Dict[str, Any], persistence) -> Dict[str, Any]:
    """
    Handle POST request to create a trading signal.

    Args:
        request_data: Request body data
        persistence: Trading persistence instance

    Returns:
        Dict containing the response
    """
    try:
        # Validate required fields
        required_fields = ['symbol', 'action', 'strength', 'confidence']
        for field in required_fields:
            if field not in request_data:
                return {
                    'statusCode': 400,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({
                        'error': True,
                        'message': f'Missing required field: {field}'
                    })
                }

        # Create signal object
        signal_data = {
            'symbol': request_data['symbol'],
            'action': request_data['action'],
            'strength': float(request_data['strength']),
            'confidence': float(request_data['confidence']),
            'reason': request_data.get('reason', 'Manual signal'),
            'timestamp': datetime.now(UTC)
        }

        # Save signal to database
        if persistence:
            signal = persistence.save_signal(signal_data)
        else:
            # Mock signal creation
            signal = {
                'id': f"signal-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
                **signal_data
            }

        return {
            'statusCode': 201,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'success': True,
                'signal': signal
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': True, 'message': f'Failed to create signal: {str(e)}'})
        }


def handle_close_trade(request_data: Dict[str, Any], orchestrator, persistence) -> Dict[str, Any]:
    """
    Handle POST request to close a trade.

    Args:
        request_data: Request body data
        orchestrator: Trading orchestrator instance
        persistence: Trading persistence instance

    Returns:
        Dict containing the response
    """
    try:
        # Validate required fields
        if 'trade_id' not in request_data:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': True,
                    'message': 'Missing required field: trade_id'
                })
            }

        trade_id = request_data['trade_id']

        # Get trade from database
        if persistence:
            trade = persistence.get_trade_by_id(trade_id)
            if not trade:
                return {
                    'statusCode': 404,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({
                        'error': True,
                        'message': 'Trade not found'
                    })
                }
        else:
            # Mock trade
            trade = Trade(
                id=trade_id,
                symbol=request_data.get('symbol', 'BTCUSDT'),
                side='BUY',
                quantity=request_data.get('quantity', 0.001),
                price=request_data.get('price', 50000.0),
                status='FILLED',
                timestamp=datetime.now(UTC)
            )

        # Close trade
        if orchestrator:
            result = orchestrator.close_trade(trade_id)
        else:
            # Mock close trade
            result = {
                'success': True,
                'close_price': request_data.get('close_price', 51000.0),
                'pnl': 10.0,
                'timestamp': datetime.now(UTC).isoformat()
            }

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'success': True,
                'result': result
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': True, 'message': f'Failed to close trade: {str(e)}'})
        }
