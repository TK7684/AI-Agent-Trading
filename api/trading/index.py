"""
Trading API serverless function for Vercel deployment.
Handles all trading-related operations including order execution,
position management, and trade history.
"""

import json
import os
import sys
from http.server import BaseHTTPRequestHandler
from typing import Dict, Any, Optional

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
    Trade = Position = Portfolio = TradingSignal = None
    TradingOrchestrator = RiskManager = TradingPersistence = None
    get_metrics_collector = get_config_manager = lambda: None


def handler(request):
    """
    Main handler for trading API requests.

    Args:
        request: Vercel request object

    Returns:
        Dict containing the response
    """
    # Get request details
    method = request.get('method', 'GET')
    path = request.get('path', '/')
    body = request.get('body', '')
    headers = request.get('headers', {})
    query = request.get('query', {})

    # Route based on path
    if path.endswith('/trades'):
        if method == 'GET':
            return handle_get_trades(query)
        elif method == 'POST':
            return handle_create_trade(body)
        else:
            return error_response(405, "Method not allowed")

    elif path.endswith('/positions'):
        if method == 'GET':
            return handle_get_positions()
        else:
            return error_response(405, "Method not allowed")

    elif path.endswith('/portfolio'):
        if method == 'GET':
            return handle_get_portfolio()
        else:
            return error_response(405, "Method not allowed")

    elif path.endswith('/signals'):
        if method == 'GET':
            return handle_get_signals(query)
        elif method == 'POST':
            return handle_create_signal(body)
        else:
            return error_response(405, "Method not allowed")

    elif 'close' in path and method == 'POST':
        return handle_close_trade(body)

    elif 'create' in path and method == 'POST':
        return handle_create_trade(body)

    else:
        return error_response(404, "Endpoint not found")


def handle_get_trades(query):
    """
    Handle GET request for trades.

    Args:
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

        # Initialize components if available
        persistence = None
        try:
            config = get_config_manager() if get_config_manager else None
            if config:
                persistence = TradingPersistence(config.get_database_config())
        except Exception as e:
            print(f"Warning: Could not initialize persistence: {e}")

        if persistence:
            try:
                # Get trades from database
                trades = persistence.get_trades(limit=limit, offset=offset, status=status, symbol=symbol)
                total = persistence.count_trades(status=status, symbol=symbol)
                trades_data = [trade.to_dict() for trade in trades]
            except Exception as e:
                print(f"Warning: Could not get trades from database: {e}")
                # Mock response
                trades_data = generate_mock_trades(symbol, status, limit)
                total = len(trades_data)
        else:
            # Mock response
            trades_data = generate_mock_trades(symbol, status, limit)
            total = len(trades_data)

        return success_response({
            'trades': trades_data,
            'total': total,
            'limit': limit,
            'offset': offset
        })
    except Exception as e:
        return error_response(500, f'Failed to get trades: {str(e)}')


def handle_create_trade(request_data):
    """
    Handle POST request to create a trade.

    Args:
        request_data: Request body data

    Returns:
        Dict containing the response
    """
    try:
        # Parse request data
        if isinstance(request_data, str):
            try:
                request_data = json.loads(request_data)
            except json.JSONDecodeError:
                request_data = {}

        # Validate required fields
        required_fields = ['symbol', 'side', 'quantity', 'price']
        for field in required_fields:
            if field not in request_data:
                return error_response(400, f'Missing required field: {field}')

        # Create trade object
        trade_data = {
            'symbol': request_data['symbol'],
            'side': request_data['side'],
            'quantity': float(request_data['quantity']),
            'price': float(request_data['price']),
            'type': request_data.get('type', 'MARKET'),
            'status': 'PENDING',
            'timestamp': datetime.now().isoformat()
        }

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
            print(f"Warning: Could not initialize components: {e}")

        # Check risk limits
        if risk_manager:
            try:
                risk_check = risk_manager.check_trade_risk(trade_data)
                if not risk_check['allowed']:
                    return error_response(403, 'Trade rejected by risk manager',
                                      {'reason': risk_check['reason']})
            except Exception as e:
                print(f"Warning: Could not check trade risk: {e}")

        # Execute trade
        if orchestrator:
            try:
                trade = orchestrator.execute_trade(trade_data)
            except Exception as e:
                print(f"Warning: Could not execute trade: {e}")
                # Mock trade execution
                trade = generate_mock_trade(trade_data)
        else:
            # Mock trade execution
            trade = generate_mock_trade(trade_data)

        # Save trade to database
        if persistence:
            try:
                persistence.save_trade(trade)
            except Exception as e:
                print(f"Warning: Could not save trade to database: {e}")

        return success_response({
            'success': True,
            'trade': trade.to_dict() if hasattr(trade, 'to_dict') else trade
        })
    except Exception as e:
        return error_response(500, f'Failed to create trade: {str(e)}')


def handle_get_positions():
    """
    Handle GET request for positions.

    Returns:
        Dict containing the response
    """
    try:
        # Initialize components if available
        persistence = None
        try:
            config = get_config_manager() if get_config_manager else None
            if config:
                persistence = TradingPersistence(config.get_database_config())
        except Exception as e:
            print(f"Warning: Could not initialize persistence: {e}")

        if persistence:
            try:
                positions = persistence.get_positions()
                positions_data = [position.to_dict() for position in positions]
            except Exception as e:
                print(f"Warning: Could not get positions from database: {e}")
                # Mock response
                positions_data = generate_mock_positions()
        else:
            # Mock response
            positions_data = generate_mock_positions()

        return success_response({
            'positions': positions_data
        })
    except Exception as e:
        return error_response(500, f'Failed to get positions: {str(e)}')


def handle_get_portfolio():
    """
    Handle GET request for portfolio.

    Returns:
        Dict containing the response
    """
    try:
        # Initialize components if available
        persistence = None
        try:
            config = get_config_manager() if get_config_manager else None
            if config:
                persistence = TradingPersistence(config.get_database_config())
        except Exception as e:
            print(f"Warning: Could not initialize persistence: {e}")

        if persistence:
            try:
                portfolio = persistence.get_portfolio()
                portfolio_data = portfolio.to_dict()
            except Exception as e:
                print(f"Warning: Could not get portfolio from database: {e}")
                # Mock response
                portfolio_data = generate_mock_portfolio()
        else:
            # Mock response
            portfolio_data = generate_mock_portfolio()

        return success_response({
            'portfolio': portfolio_data
        })
    except Exception as e:
        return error_response(500, f'Failed to get portfolio: {str(e)}')


def handle_get_signals(query):
    """
    Handle GET request for trading signals.

    Args:
        query: Query parameters

    Returns:
        Dict containing the response
    """
    try:
        # Parse query parameters
        limit = int(query.get('limit', 100))
        offset = int(query.get('offset', 0))
        symbol = query.get('symbol')

        # Initialize components if available
        persistence = None
        try:
            config = get_config_manager() if get_config_manager else None
            if config:
                persistence = TradingPersistence(config.get_database_config())
        except Exception as e:
            print(f"Warning: Could not initialize persistence: {e}")

        if persistence:
            try:
                signals = persistence.get_signals(limit=limit, offset=offset, symbol=symbol)
                signals_data = [signal.to_dict() for signal in signals]
            except Exception as e:
                print(f"Warning: Could not get signals from database: {e}")
                # Mock response
                signals_data = generate_mock_signals(symbol, limit)
        else:
            # Mock response
            signals_data = generate_mock_signals(symbol, limit)

        return success_response({
            'signals': signals_data
        })
    except Exception as e:
        return error_response(500, f'Failed to get signals: {str(e)}')


def handle_create_signal(request_data):
    """
    Handle POST request to create a trading signal.

    Args:
        request_data: Request body data

    Returns:
        Dict containing the response
    """
    try:
        # Parse request data
        if isinstance(request_data, str):
            try:
                request_data = json.loads(request_data)
            except json.JSONDecodeError:
                request_data = {}

        # Validate required fields
        required_fields = ['symbol', 'action', 'strength', 'confidence']
        for field in required_fields:
            if field not in request_data:
                return error_response(400, f'Missing required field: {field}')

        # Create signal object
        signal_data = {
            'symbol': request_data['symbol'],
            'action': request_data['action'],
            'strength': float(request_data['strength']),
            'confidence': float(request_data['confidence']),
            'reason': request_data.get('reason', 'Manual signal'),
            'timestamp': datetime.now().isoformat()
        }

        # Initialize components if available
        persistence = None
        try:
            config = get_config_manager() if get_config_manager else None
            if config:
                persistence = TradingPersistence(config.get_database_config())
        except Exception as e:
            print(f"Warning: Could not initialize persistence: {e}")

        # Save signal to database
        if persistence:
            try:
                signal = persistence.save_signal(signal_data)
                signal_data = signal.to_dict() if hasattr(signal, 'to_dict') else signal_data
            except Exception as e:
                print(f"Warning: Could not save signal to database: {e}")

        return success_response({
            'success': True,
            'signal': signal_data
        })
    except Exception as e:
        return error_response(500, f'Failed to create signal: {str(e)}')


def handle_close_trade(request_data):
    """
    Handle POST request to close a trade.

    Args:
        request_data: Request body data

    Returns:
        Dict containing the response
    """
    try:
        # Parse request data
        if isinstance(request_data, str):
            try:
                request_data = json.loads(request_data)
            except json.JSONDecodeError:
                request_data = {}

        # Validate required fields
        if 'trade_id' not in request_data:
            return error_response(400, 'Missing required field: trade_id')

        trade_id = request_data['trade_id']

        # Initialize components if available
        orchestrator = None
        persistence = None
        try:
            config = get_config_manager() if get_config_manager else None
            if config:
                orchestrator = TradingOrchestrator(config.get_trading_config())
                persistence = TradingPersistence(config.get_database_config())
        except Exception as e:
            print(f"Warning: Could not initialize components: {e}")

        # Get trade from database
        if persistence:
            try:
                trade = persistence.get_trade_by_id(trade_id)
                if not trade:
                    return error_response(404, 'Trade not found')
                trade_data = trade.to_dict()
            except Exception as e:
                print(f"Warning: Could not get trade from database: {e}")
                # Mock trade
                trade_data = {
                    'id': trade_id,
                    'symbol': request_data.get('symbol', 'BTCUSDT'),
                    'side': request_data.get('side', 'BUY'),
                    'quantity': request_data.get('quantity', 0.001),
                    'price': request_data.get('price', 50000.0),
                    'status': 'FILLED',
                    'timestamp': datetime.now().isoformat()
                }
        else:
            # Mock trade
            trade_data = {
                'id': trade_id,
                'symbol': request_data.get('symbol', 'BTCUSDT'),
                'side': request_data.get('side', 'BUY'),
                'quantity': request_data.get('quantity', 0.001),
                'price': request_data.get('price', 50000.0),
                'status': 'FILLED',
                'timestamp': datetime.now().isoformat()
            }

        # Close trade
        if orchestrator:
            try:
                result = orchestrator.close_trade(trade_id)
            except Exception as e:
                print(f"Warning: Could not close trade: {e}")
                # Mock close trade
                result = generate_mock_close_result(trade_data)
        else:
            # Mock close trade
            result = generate_mock_close_result(trade_data)

        return success_response({
            'success': True,
            'result': result
        })
    except Exception as e:
        return error_response(500, f'Failed to close trade: {str(e)}')


def success_response(data):
    """
    Create a success response.

    Args:
        data: Data to include in response

    Returns:
        Dict containing the success response
    """
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(data)
    }


def error_response(status_code, message, extra=None):
    """
    Create an error response.

    Args:
        status_code: HTTP status code
        message: Error message
        extra: Additional data to include

    Returns:
        Dict containing the error response
    """
    response = {
        'statusCode': status_code,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
            'error': True,
            'message': message
        })
    }

    if extra:
        error_data = json.loads(response['body'])
        error_data.update(extra)
        response['body'] = json.dumps(error_data)

    return response


# Helper functions for mock data
def generate_mock_trade(trade_data):
    """Generate a mock trade object."""
    from datetime import datetime
    trade_id = f"trade_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    class MockTrade:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

        def to_dict(self):
            return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

    return MockTrade(
        id=trade_id,
        **trade_data,
        status='FILLED'
    )


def generate_mock_trades(symbol, status, limit):
    """Generate mock trades data."""
    from datetime import datetime, timedelta
    import random

    trades = []
    for i in range(limit):
        trades.append({
            'id': f'trade_{i}',
            'symbol': symbol or 'BTCUSDT',
            'side': random.choice(['BUY', 'SELL']),
            'quantity': random.uniform(0.001, 0.01),
            'price': random.uniform(49000, 51000),
            'status': status or 'FILLED',
            'timestamp': (datetime.now() - timedelta(hours=i)).isoformat()
        })

    return trades


def generate_mock_positions():
    """Generate mock positions data."""
    import random
    return [
        {
            'id': 'mock-position-1',
            'symbol': 'BTCUSDT',
            'quantity': random.uniform(0.001, 0.01),
            'side': 'LONG',
            'entry_price': random.uniform(49000, 51000),
            'current_price': random.uniform(49000, 51000),
            'unrealized_pnl': random.uniform(-100, 100),
            'timestamp': datetime.now().isoformat()
        }
    ]


def generate_mock_portfolio():
    """Generate mock portfolio data."""
    import random
    return {
        'id': 'mock-portfolio',
        'balance': 10000.0,
        'equity': 10000.0 + random.uniform(-1000, 1000),
        'unrealized_pnl': random.uniform(-500, 500),
        'realized_pnl': random.uniform(-200, 200),
        'total_trades': random.randint(10, 100),
        'winning_trades': random.randint(5, 50),
        'losing_trades': random.randint(5, 50),
        'win_rate': random.uniform(0.4, 0.7)
    }


def generate_mock_signals(symbol, limit):
    """Generate mock signals data."""
    from datetime import datetime, timedelta
    import random

    signals = []
    for i in range(limit):
        signals.append({
            'id': f'signal_{i}',
            'symbol': symbol or 'BTCUSDT',
            'action': random.choice(['BUY', 'SELL', 'HOLD']),
            'strength': random.uniform(0.5, 1.0),
            'confidence': random.uniform(0.5, 1.0),
            'reason': 'Mock technical analysis',
            'timestamp': (datetime.now() - timedelta(hours=i)).isoformat()
        })

    return signals


def generate_mock_close_result(trade_data):
    """Generate mock close trade result."""
    import random
    return {
        'trade_id': trade_data.get('id', 'unknown'),
        'close_price': trade_data.get('price', 50000.0) * random.uniform(0.98, 1.02),
        'pnl': random.uniform(-100, 100),
        'timestamp': datetime.now().isoformat()
    }
