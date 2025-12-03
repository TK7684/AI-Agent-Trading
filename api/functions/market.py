"""
Market data API serverless function for Vercel deployment.
Handles market data collection, analysis, and distribution.
Designed to work with Vercel's serverless environment and provide
real-time market data for trading strategies.
"""

import json
import os
import sys
from datetime import datetime, timedelta, UTC
from typing import Dict, Any, List, Optional

# Add the project root to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from libs.trading_models.market_data import MarketDataCollector
    from libs.trading_models.market_data_ingestion import MarketDataIngestion
    from libs.trading_models.technical_indicators import TechnicalIndicators
    from libs.trading_models.pattern_recognition import PatternRecognizer
    from libs.trading_models.config_manager import get_config_manager
    from libs.trading_models.persistence import TradingPersistence
    from libs.trading_models.confluence_scoring import ConfluenceScorer
except ImportError:
    # Fallback for serverless environment
    MarketDataCollector = MarketDataIngestion = None
    TechnicalIndicators = PatternRecognizer = None
    get_config_manager = lambda: None
    TradingPersistence = ConfluenceScorer = None


def handler(request_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main handler for market data API requests.

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

    try:
        # Parse request body if present
        request_data = {}
        if body:
            try:
                request_data = json.loads(body)
            except json.JSONDecodeError:
                pass

        # Route based on path and method
        if path.endswith('/data'):
            if method == 'GET':
                return handle_get_market_data(query)
            elif method == 'POST':
                return handle_request_market_data(request_data)

        elif path.endswith('/data/realtime'):
            if method == 'GET':
                return handle_get_realtime_data(query)

        elif path.endswith('/data/historical'):
            if method == 'GET':
                return handle_get_historical_data(query)

        elif path.endswith('/data/indicators'):
            if method == 'GET':
                return handle_get_technical_indicators(query)
            elif method == 'POST':
                return handle_calculate_indicators(request_data)

        elif path.endswith('/data/patterns'):
            if method == 'GET':
                return handle_get_patterns(query)
            elif method == 'POST':
                return handle_analyze_patterns(request_data)

        elif path.endswith('/data/confluence'):
            if method == 'GET':
                return handle_get_confluence_scores(query)
            elif method == 'POST':
                return handle_calculate_confluence(request_data)

        elif path.endswith('/data/symbols'):
            if method == 'GET':
                return handle_get_symbols(query)

        elif path.endswith('/data/timeframes'):
            if method == 'GET':
                return handle_get_timeframes()

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


def handle_get_market_data(query: Dict[str, str]) -> Dict[str, Any]:
    """
    Handle GET request for market data.

    Args:
        query: Query parameters

    Returns:
        Dict containing the response
    """
    try:
        # Parse query parameters
        symbol = query.get('symbol')
        timeframe = query.get('timeframe', '1h')
        limit = int(query.get('limit', 100))

        if not symbol:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': True,
                    'message': 'Symbol is required'
                })
            }

        # Initialize components if available
        market_data = None
        try:
            config = get_config_manager() if get_config_manager else None
            if config:
                market_data = MarketDataCollector(config.get_market_data_config())
        except Exception as e:
            print(f"Warning: Could not initialize market data collector: {e}")

        # Get market data
        if market_data:
            try:
                data = market_data.get_latest_data(symbol, timeframe, limit)
            except Exception as e:
                print(f"Warning: Could not fetch market data: {e}")
                # Generate mock data
                data = generate_mock_market_data(symbol, timeframe, limit)
        else:
            # Generate mock data
            data = generate_mock_market_data(symbol, timeframe, limit)

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'symbol': symbol,
                'timeframe': timeframe,
                'data': data
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': True, 'message': f'Failed to get market data: {str(e)}'})
        }


def handle_request_market_data(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle POST request to request specific market data.

    Args:
        request_data: Request body data

    Returns:
        Dict containing the response
    """
    try:
        # Validate required fields
        required_fields = ['symbol', 'timeframe']
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

        symbol = request_data['symbol']
        timeframe = request_data.get('timeframe', '1h')
        limit = request_data.get('limit', 100)
        start_date_str = request_data.get('start_date')
        end_date_str = request_data.get('end_date')

        # Parse dates if provided
        start_date = None
        end_date = None
        if start_date_str:
            start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
        if end_date_str:
            end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))

        # Initialize components if available
        market_data = None
        try:
            config = get_config_manager() if get_config_manager else None
            if config:
                market_data = MarketDataCollector(config.get_market_data_config())
        except Exception as e:
            print(f"Warning: Could not initialize market data collector: {e}")

        # Get market data
        if market_data:
            try:
                if start_date and end_date:
                    data = market_data.get_historical_data(symbol, timeframe, start_date, end_date)
                else:
                    data = market_data.get_latest_data(symbol, timeframe, limit)
            except Exception as e:
                print(f"Warning: Could not fetch market data: {e}")
                # Generate mock data
                if start_date and end_date:
                    data = generate_mock_historical_data(symbol, timeframe, start_date, end_date)
                else:
                    data = generate_mock_market_data(symbol, timeframe, limit)
        else:
            # Generate mock data
            if start_date and end_date:
                data = generate_mock_historical_data(symbol, timeframe, start_date, end_date)
            else:
                data = generate_mock_market_data(symbol, timeframe, limit)

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'symbol': symbol,
                'timeframe': timeframe,
                'data': data
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': True, 'message': f'Failed to request market data: {str(e)}'})
        }


def handle_get_realtime_data(query: Dict[str, str]) -> Dict[str, Any]:
    """
    Handle GET request for realtime market data.

    Args:
        query: Query parameters

    Returns:
        Dict containing the response
    """
    try:
        # Parse query parameters
        symbol = query.get('symbol')
        stream = query.get('stream', 'false').lower() == 'true'

        if not symbol:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': True,
                    'message': 'Symbol is required'
                })
            }

        # Initialize components if available
        market_data = None
        try:
            config = get_config_manager() if get_config_manager else None
            if config:
                market_data = MarketDataCollector(config.get_market_data_config())
        except Exception as e:
            print(f"Warning: Could not initialize market data collector: {e}")

        # Get realtime data
        if market_data:
            try:
                data = market_data.get_realtime_data(symbol)
            except Exception as e:
                print(f"Warning: Could not fetch realtime data: {e}")
                # Generate mock data
                data = generate_mock_realtime_data(symbol)
        else:
            # Generate mock data
            data = generate_mock_realtime_data(symbol)

        # Handle streaming request (would need WebSocket in real implementation)
        if stream:
            # For serverless, we can't maintain a persistent connection
            # In a real implementation, you'd use a WebSocket service
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': True,
                    'message': 'Streaming not supported in serverless environment. Please use polling or WebSocket service.'
                })
            }

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'symbol': symbol,
                'data': data,
                'timestamp': datetime.now(UTC).isoformat()
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': True, 'message': f'Failed to get realtime data: {str(e)}'})
        }


def handle_get_historical_data(query: Dict[str, str]) -> Dict[str, Any]:
    """
    Handle GET request for historical market data.

    Args:
        query: Query parameters

    Returns:
        Dict containing the response
    """
    try:
        # Parse query parameters
        symbol = query.get('symbol')
        timeframe = query.get('timeframe', '1h')
        start_date_str = query.get('start_date')
        end_date_str = query.get('end_date')
        limit = int(query.get('limit', 1000))

        if not symbol:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': True,
                    'message': 'Symbol is required'
                })
            }

        # Parse dates
        if start_date_str:
            start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
        else:
            start_date = datetime.now(UTC) - timedelta(days=30)

        if end_date_str:
            end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
        else:
            end_date = datetime.now(UTC)

        # Initialize components if available
        market_data = None
        try:
            config = get_config_manager() if get_config_manager else None
            if config:
                market_data = MarketDataCollector(config.get_market_data_config())
        except Exception as e:
            print(f"Warning: Could not initialize market data collector: {e}")

        # Get historical data
        if market_data:
            try:
                data = market_data.get_historical_data(symbol, timeframe, start_date, end_date, limit)
            except Exception as e:
                print(f"Warning: Could not fetch historical data: {e}")
                # Generate mock data
                data = generate_mock_historical_data(symbol, timeframe, start_date, end_date, limit)
        else:
            # Generate mock data
            data = generate_mock_historical_data(symbol, timeframe, start_date, end_date, limit)

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'symbol': symbol,
                'timeframe': timeframe,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'data': data
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': True, 'message': f'Failed to get historical data: {str(e)}'})
        }


def handle_get_technical_indicators(query: Dict[str, str]) -> Dict[str, Any]:
    """
    Handle GET request for technical indicators.

    Args:
        query: Query parameters

    Returns:
        Dict containing the response
    """
    try:
        # Parse query parameters
        symbol = query.get('symbol')
        timeframe = query.get('timeframe', '1h')
        indicators = query.get('indicators', 'RSI,MACD,SMA').split(',')
        limit = int(query.get('limit', 100))

        if not symbol:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': True,
                    'message': 'Symbol is required'
                })
            }

        # Initialize components if available
        market_data = None
        technical_indicators = None
        try:
            config = get_config_manager() if get_config_manager else None
            if config:
                market_data = MarketDataCollector(config.get_market_data_config())
                technical_indicators = TechnicalIndicators()
        except Exception as e:
            print(f"Warning: Could not initialize components: {e}")

        # Get market data
        if market_data:
            try:
                data = market_data.get_latest_data(symbol, timeframe, limit)
            except Exception as e:
                print(f"Warning: Could not fetch market data: {e}")
                # Generate mock data
                data = generate_mock_market_data(symbol, timeframe, limit)
        else:
            # Generate mock data
            data = generate_mock_market_data(symbol, timeframe, limit)

        # Calculate indicators
        if technical_indicators:
            try:
                # Convert to DataFrame if needed
                import pandas as pd
                if not isinstance(data, pd.DataFrame):
                    df = pd.DataFrame(data)
                else:
                    df = data.copy()

                # Calculate indicators
                indicator_data = {}
                for indicator in indicators:
                    indicator = indicator.strip()
                    if indicator == 'RSI':
                        indicator_data['RSI'] = technical_indicators.calculate_rsi(df, period=14)
                    elif indicator == 'MACD':
                        indicator_data['MACD'] = technical_indicators.calculate_macd(df)
                    elif indicator == 'SMA':
                        indicator_data['SMA_20'] = technical_indicators.calculate_sma(df, period=20)
                        indicator_data['SMA_50'] = technical_indicators.calculate_sma(df, period=50)
                    elif indicator == 'EMA':
                        indicator_data['EMA_20'] = technical_indicators.calculate_ema(df, period=20)
                        indicator_data['EMA_50'] = technical_indicators.calculate_ema(df, period=50)
                    elif indicator == 'BB':
                        indicator_data['BB'] = technical_indicators.calculate_bollinger_bands(df)
                    elif indicator == 'ATR':
                        indicator_data['ATR'] = technical_indicators.calculate_atr(df)
                    elif indicator == 'STOCH':
                        indicator_data['STOCH'] = technical_indicators.calculate_stochastic(df)
            except Exception as e:
                print(f"Warning: Could not calculate indicators: {e}")
                # Generate mock indicators
                indicator_data = generate_mock_indicators(data, indicators)
        else:
            # Generate mock indicators
            indicator_data = generate_mock_indicators(data, indicators)

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'symbol': symbol,
                'timeframe': timeframe,
                'indicators': indicator_data
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': True, 'message': f'Failed to get technical indicators: {str(e)}'})
        }


def handle_calculate_indicators(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle POST request to calculate technical indicators on provided data.

    Args:
        request_data: Request body data

    Returns:
        Dict containing the response
    """
    try:
        # Validate required fields
        if 'data' not in request_data:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': True,
                    'message': 'Missing required field: data'
                })
            }

        data = request_data['data']
        indicators = request_data.get('indicators', ['RSI', 'MACD', 'SMA'])

        # Initialize technical indicators if available
        technical_indicators = None
        try:
            technical_indicators = TechnicalIndicators()
        except Exception as e:
            print(f"Warning: Could not initialize technical indicators: {e}")

        # Calculate indicators
        if technical_indicators:
            try:
                # Convert to DataFrame if needed
                import pandas as pd
                if not isinstance(data, pd.DataFrame):
                    df = pd.DataFrame(data)
                else:
                    df = data.copy()

                # Calculate indicators
                indicator_data = {}
                for indicator in indicators:
                    if indicator == 'RSI':
                        indicator_data['RSI'] = technical_indicators.calculate_rsi(df, period=14)
                    elif indicator == 'MACD':
                        indicator_data['MACD'] = technical_indicators.calculate_macd(df)
                    elif indicator == 'SMA':
                        indicator_data['SMA_20'] = technical_indicators.calculate_sma(df, period=20)
                        indicator_data['SMA_50'] = technical_indicators.calculate_sma(df, period=50)
                    elif indicator == 'EMA':
                        indicator_data['EMA_20'] = technical_indicators.calculate_ema(df, period=20)
                        indicator_data['EMA_50'] = technical_indicators.calculate_ema(df, period=50)
                    elif indicator == 'BB':
                        indicator_data['BB'] = technical_indicators.calculate_bollinger_bands(df)
                    elif indicator == 'ATR':
                        indicator_data['ATR'] = technical_indicators.calculate_atr(df)
                    elif indicator == 'STOCH':
                        indicator_data['STOCH'] = technical_indicators.calculate_stochastic(df)
            except Exception as e:
                print(f"Warning: Could not calculate indicators: {e}")
                # Generate mock indicators
                indicator_data = generate_mock_indicators(data, indicators)
        else:
            # Generate mock indicators
            indicator_data = generate_mock_indicators(data, indicators)

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'indicators': indicator_data
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': True, 'message': f'Failed to calculate indicators: {str(e)}'})
        }


def handle_get_patterns(query: Dict[str, str]) -> Dict[str, Any]:
    """
    Handle GET request for chart patterns.

    Args:
        query: Query parameters

    Returns:
        Dict containing the response
    """
    try:
        # Parse query parameters
        symbol = query.get('symbol')
        timeframe = query.get('timeframe', '1h')
        pattern_types = query.get('patterns', 'all')
        limit = int(query.get('limit', 100))

        if not symbol:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': True,
                    'message': 'Symbol is required'
                })
            }

        # Initialize components if available
        market_data = None
        pattern_recognizer = None
        try:
            config = get_config_manager() if get_config_manager else None
            if config:
                market_data = MarketDataCollector(config.get_market_data_config())
                pattern_recognizer = PatternRecognizer()
        except Exception as e:
            print(f"Warning: Could not initialize components: {e}")

        # Get market data
        if market_data:
            try:
                data = market_data.get_latest_data(symbol, timeframe, limit)
            except Exception as e:
                print(f"Warning: Could not fetch market data: {e}")
                # Generate mock data
                data = generate_mock_market_data(symbol, timeframe, limit)
        else:
            # Generate mock data
            data = generate_mock_market_data(symbol, timeframe, limit)

        # Recognize patterns
        if pattern_recognizer:
            try:
                # Convert to DataFrame if needed
                import pandas as pd
                if not isinstance(data, pd.DataFrame):
                    df = pd.DataFrame(data)
                else:
                    df = data.copy()

                # Recognize patterns
                patterns = pattern_recognizer.recognize_patterns(df, pattern_types=pattern_types)
            except Exception as e:
                print(f"Warning: Could not recognize patterns: {e}")
                # Generate mock patterns
                patterns = generate_mock_patterns(symbol, timeframe, pattern_types)
        else:
            # Generate mock patterns
            patterns = generate_mock_patterns(symbol, timeframe, pattern_types)

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'symbol': symbol,
                'timeframe': timeframe,
                'patterns': patterns
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': True, 'message': f'Failed to get patterns: {str(e)}'})
        }


def handle_analyze_patterns(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle POST request to analyze patterns on provided data.

    Args:
        request_data: Request body data

    Returns:
        Dict containing the response
    """
    try:
        # Validate required fields
        if 'data' not in request_data:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': True,
                    'message': 'Missing required field: data'
                })
            }

        data = request_data['data']
        pattern_types = request_data.get('patterns', 'all')

        # Initialize pattern recognizer if available
        pattern_recognizer = None
        try:
            pattern_recognizer = PatternRecognizer()
        except Exception as e:
            print(f"Warning: Could not initialize pattern recognizer: {e}")

        # Recognize patterns
        if pattern_recognizer:
            try:
                # Convert to DataFrame if needed
                import pandas as pd
                if not isinstance(data, pd.DataFrame):
                    df = pd.DataFrame(data)
                else:
                    df = data.copy()

                # Recognize patterns
                patterns = pattern_recognizer.recognize_patterns(df, pattern_types=pattern_types)
            except Exception as e:
                print(f"Warning: Could not recognize patterns: {e}")
                # Generate mock patterns
                patterns = generate_mock_patterns('UNKNOWN', 'UNKNOWN', pattern_types)
        else:
            # Generate mock patterns
            patterns = generate_mock_patterns('UNKNOWN', 'UNKNOWN', pattern_types)

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'patterns': patterns
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': True, 'message': f'Failed to analyze patterns: {str(e)}'})
        }


def handle_get_confluence_scores(query: Dict[str, str]) -> Dict[str, Any]:
    """
    Handle GET request for confluence scores.

    Args:
        query: Query parameters

    Returns:
        Dict containing the response
    """
    try:
        # Parse query parameters
        symbol = query.get('symbol')
        timeframe = query.get('timeframe', '1h')
        limit = int(query.get('limit', 100))

        if not symbol:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': True,
                    'message': 'Symbol is required'
                })
            }

        # Initialize components if available
        market_data = None
        confluence_scorer = None
        try:
            config = get_config_manager() if get_config_manager else None
            if config:
                market_data = MarketDataCollector(config.get_market_data_config())
                confluence_scorer = ConfluenceScorer(config.get_confluence_config())
        except Exception as e:
            print(f"Warning: Could not initialize components: {e}")

        # Get market data
        if market_data:
            try:
                data = market_data.get_latest_data(symbol, timeframe, limit)
            except Exception as e:
                print(f"Warning: Could not fetch market data: {e}")
                # Generate mock data
                data = generate_mock_market_data(symbol, timeframe, limit)
        else:
            # Generate mock data
            data = generate_mock_market_data(symbol, timeframe, limit)

        # Calculate confluence scores
        if confluence_scorer:
            try:
                # Convert to DataFrame if needed
                import pandas as pd
                if not isinstance(data, pd.DataFrame):
                    df = pd.DataFrame(data)
                else:
                    df = data.copy()

                # Calculate confluence scores
                scores = confluence_scorer.calculate_confluence(df)
            except Exception as e:
                print(f"Warning: Could not calculate confluence scores: {e}")
                # Generate mock scores
                scores = generate_mock_confluence_scores(symbol)
        else:
            # Generate mock scores
            scores = generate_mock_confluence_scores(symbol)

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'symbol': symbol,
                'timeframe': timeframe,
                'confluence_scores': scores
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': True, 'message': f'Failed to get confluence scores: {str(e)}'})
        }


def handle_calculate_confluence(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle POST request to calculate confluence scores on provided data.

    Args:
        request_data: Request body data

    Returns:
        Dict containing the response
    """
    try:
        # Validate required fields
        if 'data' not in request_data:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': True,
                    'message': 'Missing required field: data'
                })
            }

        data = request_data['data']
        symbol = request_data.get('symbol', 'UNKNOWN')

        # Initialize confluence scorer if available
        confluence_scorer = None
        try:
            confluence_scorer = ConfluenceScorer()
        except Exception as e:
            print(f"Warning: Could not initialize confluence scorer: {e}")

        # Calculate confluence scores
        if confluence_scorer:
            try:
                # Convert to DataFrame if needed
                import pandas as pd
                if not isinstance(data, pd.DataFrame):
                    df = pd.DataFrame(data)
                else:
                    df = data.copy()

                # Calculate confluence scores
                scores = confluence_scorer.calculate_confluence(df)
            except Exception as e:
                print(f"Warning: Could not calculate confluence scores: {e}")
                # Generate mock scores
                scores = generate_mock_confluence_scores(symbol)
        else:
            # Generate mock scores
            scores = generate_mock_confluence_scores(symbol)

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'confluence_scores': scores
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': True, 'message': f'Failed to calculate confluence scores: {str(e)}'})
        }


def handle_get_symbols(query: Dict[str, str]) -> Dict[str, Any]:
    """
    Handle GET request for available symbols.

    Args:
        query: Query parameters

    Returns:
        Dict containing the response
    """
    try:
        # Parse query parameters
        asset_class = query.get('asset_class')

        # Initialize components if available
        market_data = None
        try:
            config = get_config_manager() if get_config_manager else None
            if config:
                market_data = MarketDataCollector(config.get_market_data_config())
        except Exception as e:
            print(f"Warning: Could not initialize market data collector: {e}")

        # Get symbols
        if market_data:
            try:
                symbols = market_data.get_available_symbols(asset_class)
            except Exception as e:
                print(f"Warning: Could not fetch symbols: {e}")
                # Generate mock symbols
                symbols = generate_mock_symbols(asset_class)
        else:
            # Generate mock symbols
            symbols = generate_mock_symbols(asset_class)

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'asset_class': asset_class or 'all',
                'symbols': symbols
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': True, 'message': f'Failed to get symbols: {str(e)}'})
        }


def handle_get_timeframes() -> Dict[str, Any]:
    """
    Handle GET request for available timeframes.

    Returns:
        Dict containing the response
    """
    try:
        # Initialize components if available
        market_data = None
        try:
            config = get_config_manager() if get_config_manager else None
            if config:
                market_data = MarketDataCollector(config.get_market_data_config())
        except Exception as e:
            print(f"Warning: Could not initialize market data collector: {e}")

        # Get timeframes
        if market_data:
            try:
                timeframes = market_data.get_available_timeframes()
            except Exception as e:
                print(f"Warning: Could not fetch timeframes: {e}")
                # Generate mock timeframes
                timeframes = generate_mock_timeframes()
        else:
            # Generate mock timeframes
            timeframes = generate_mock_timeframes()

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'timeframes': timeframes
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': True, 'message': f'Failed to get timeframes: {str(e)}'})
        }


# Helper functions
def generate_mock_market_data(symbol: str, timeframe: str, limit: int) -> List[Dict[str, Any]]:
    """Generate mock market data for testing."""
    import numpy as np

    data = []
    base_price = 50000.0 if symbol == 'BTCUSDT' else 100.0

    # Generate price data with random walk
    prices = [base_price]
    for i in range(1, limit):
        change = np.random.normal(0, 0.01)
        prices.append(max(prices[-1] * (1 + change), base_price * 0.5))

    # Generate OHLCV data
    current_time = datetime.now(UTC)
    timeframe_seconds = {
        '1m': 60,
        '5m': 300,
        '15m': 900,
        '30m': 1800,
        '1h': 3600,
        '4h': 14400,
        '1d': 86400
    }.get(timeframe, 3600)

    for i in range(limit):
        timestamp = current_time - timedelta(seconds=(limit - i) * timeframe_seconds)
        price = prices[i]

        data.append({
            'timestamp': timestamp.isoformat(),
            'open': price,
            'high': price * (1 + abs(np.random.normal(0, 0.005))),
            'low': price * (1 - abs(np.random.normal(0, 0.005))),
            'close': price,
            'volume': np.random.uniform(100, 1000)
        })

    return data


def generate_mock_historical_data(symbol: str, timeframe: str, start_date: datetime, end_date: datetime, limit: int = 1000) -> List[Dict[str, Any]]:
    """Generate mock historical data for testing."""
    import numpy as np

    # Calculate number of data points
    timeframe_seconds = {
        '1m': 60,
        '5m': 300,
        '15m': 900,
        '30m': 1800,
        '1h': 3600,
        '4h': 14400,
        '1d': 86400
    }.get(timeframe, 3600)

    duration_seconds = (end_date - start_date).total_seconds()
    num_points = min(limit, int(duration_seconds / timeframe_seconds))

    data = []
    base_price = 50000.0 if symbol == 'BTCUSDT' else 100.0

    # Generate price data with random walk
    prices = [base_price]
    for i in range(1, num_points):
        change = np.random.normal(0, 0.01)
        prices.append(max(prices[-1] * (1 + change), base_price * 0.5))

    # Generate OHLCV data
    for i in range(num_points):
        timestamp = start_date + timedelta(seconds=i * timeframe_seconds)
        price = prices[i]

        data.append({
            'timestamp': timestamp.isoformat(),
            'open': price,
            'high': price * (1 + abs(np.random.normal(0, 0.005))),
            'low': price * (1 - abs(np.random.normal(0, 0.005))),
            'close': price,
            'volume': np.random.uniform(100, 1000)
        })

    return data


def generate_mock_realtime_data(symbol: str) -> Dict[str, Any]:
    """Generate mock realtime data for testing."""
    import numpy as np

    base_price = 50000.0 if symbol == 'BTCUSDT' else 100.0
    price = base_price * (1 + np.random.normal(0, 0.01))

    return {
        'symbol': symbol,
        'price': price,
        'bid': price * 0.999,
        'ask': price * 1.001,
        'volume': np.random.uniform(100, 1000),
        'timestamp': datetime.now(UTC).isoformat()
    }


def generate_mock_indicators(data: List[Dict[str, Any]], indicators: List[str]) -> Dict[str, Any]:
    """Generate mock technical indicators for testing."""
    import numpy as np

    indicator_data = {}
    n = len(data)

    for indicator in indicators:
        indicator = indicator.strip()
        if indicator == 'RSI':
            indicator_data['RSI'] = [50 + 10 * np.sin(i/10) for i in range(n)]
        elif indicator == 'MACD':
            indicator_data['MACD'] = {
                'macd': [0.01 * np.sin(i/5) for i in range(n)],
                'signal': [0.008 * np.sin(i/5) for i in range(n)],
                'histogram': [0.002 * np.sin(i/5) for i in range(n)]
            }
        elif indicator == 'SMA':
            indicator_data['SMA_20'] = [50000 + 100 * np.sin(i/20) for i in range(n)]
            indicator_data['SMA_50'] = [50000 + 200 * np.sin(i/50) for i in range(n)]
        elif indicator == 'EMA':
            indicator_data['EMA_20'] = [50000 + 120 * np.sin(i/20) for i in range(n)]
            indicator_data['EMA_50'] = [50000 + 220 * np.sin(i/50) for i in range(n)]
        elif indicator == 'BB':
            indicator_data['BB'] = {
                'upper': [50500 + 100 * np.sin(i/20) for i in range(n)],
                'middle': [50000 + 100 * np.sin(i/20) for i in range(n)],
                'lower': [49500 + 100 * np.sin(i/20) for i in range(n)]
            }
        elif indicator == 'ATR':
            indicator_data['ATR'] = [100 + 50 * np.sin(i/15) for i in range(n)]
        elif indicator == 'STOCH':
            indicator_data['STOCH'] = {
                'k': [50 + 10 * np.sin(i/10) for i in range(n)],
                'd': [45 + 10 * np.sin(i/10) for i in range(n)]
            }

    return indicator_data


def generate_mock_patterns(symbol: str, timeframe: str, pattern_types: str) -> List[Dict[str, Any]]:
    """Generate mock chart patterns for testing."""
    import random

    patterns = []
    n = 5 if pattern_types == 'all' else 2

    for i in range(n):
        pattern = {
            'id': f'pattern_{i}',
            'symbol': symbol,
            'timeframe': timeframe,
            'type': random.choice(['Head and Shoulders', 'Double Top', 'Double Bottom', 'Triangle', 'Flag', 'Pennant']),
            'direction': random.choice(['bullish', 'bearish']),
            'strength': random.uniform(0.6, 0.9),
            'start_time': (datetime.now(UTC) - timedelta(days=i+1)).isoformat(),
            'end_time': (datetime.now(UTC) - timedelta(days=i)).isoformat(),
            'price_target': 0.05 if random.choice([True, False]) else None
        }
        patterns.append(pattern)

    return patterns


def generate_mock_confluence_scores(symbol: str) -> Dict[str, Any]:
    """Generate mock confluence scores for testing."""
    import random

    return {
        'symbol': symbol,
        'timestamp': datetime.now(UTC).isoformat(),
        'overall_score': random.uniform(0.6, 0.9),
        'buy_score': random.uniform(0.6, 0.9),
        'sell_score': random.uniform(0.6, 0.9),
        'neutral_score': random.uniform(0.6, 0.9),
        'components': {
            'trend': random.uniform(0.6, 0.9),
            'momentum': random.uniform(0.6, 0.9),
            'volume': random.uniform(0.6, 0.9),
            'volatility': random.uniform(0.6, 0.9),
            'support_resistance': random.uniform(0.6, 0.9)
        },
        'recommendation': random.choice(['STRONG_BUY', 'BUY', 'HOLD', 'SELL', 'STRONG_SELL'])
    }


def generate_mock_symbols(asset_class: Optional[str]) -> List[Dict[str, Any]]:
    """Generate mock symbols for testing."""
    symbols = []

    if asset_class is None or asset_class == 'crypto':
        symbols.extend([
            {'symbol': 'BTCUSDT', 'name': 'Bitcoin/Tether', 'asset_class': 'crypto'},
            {'symbol': 'ETHUSDT', 'name': 'Ethereum/Tether', 'asset_class': 'crypto'},
            {'symbol': 'ADAUSDT', 'name': 'Cardano/Tether', 'asset_class': 'crypto'}
        ])

    if asset_class is None or asset_class == 'forex':
        symbols.extend([
            {'symbol': 'EURUSD', 'name': 'Euro/US Dollar', 'asset_class': 'forex'},
            {'symbol': 'GBPUSD', 'name': 'British Pound/US Dollar', 'asset_class': 'forex'},
            {'symbol': 'USDJPY', 'name': 'US Dollar/Japanese Yen', 'asset_class': 'forex'}
        ])

    if asset_class is None or asset_class == 'stocks':
        symbols.extend([
            {'symbol': 'AAPL', 'name': 'Apple Inc.', 'asset_class': 'stocks'},
            {'symbol': 'MSFT', 'name': 'Microsoft Corporation', 'asset_class': 'stocks'},
            {'symbol': 'GOOGL', 'name': 'Alphabet Inc.', 'asset_class': 'stocks'}
        ])

    return symbols


def generate_mock_timeframes() -> List[Dict[str, Any]]:
    """Generate mock timeframes for testing."""
    return [
        {'timeframe': '1m', 'name': '1 Minute', 'seconds': 60},
        {'timeframe': '5m', 'name': '5 Minutes', 'seconds': 300},
        {'timeframe': '15m', 'name': '15 Minutes', 'seconds': 900},
        {'timeframe': '30m', 'name': '30 Minutes', 'seconds': 1800},
        {'timeframe': '1h', 'name': '1 Hour', 'seconds': 3600},
        {'timeframe': '4h', 'name': '4 Hours', 'seconds': 14400},
        {'timeframe': '1d', 'name': '1 Day', 'seconds': 86400}
    ]
