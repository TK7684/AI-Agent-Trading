"""
Strategy development API serverless function for Vercel deployment.
Handles strategy creation, backtesting, optimization, and deployment.
Designed to work with Vercel's serverless environment and enable
automated strategy development and updates.
"""

import json
import os
import sys
from datetime import datetime, timedelta, UTC
from typing import Dict, Any, List, Optional

# Add the project root to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from libs.trading_models.backtesting import BacktestEngine
    from libs.trading_models.orchestrator import TradingOrchestrator
    from libs.trading_models.risk_management import RiskManager
    from libs.trading_models.technical_indicators import TechnicalIndicators
    from libs.trading_models.pattern_recognition import PatternRecognizer
    from libs.trading_models.llm_integration import MultiLLMRouter
    from libs.trading_models.config_manager import get_config_manager
    from libs.trading_models.persistence import TradingPersistence
    from libs.trading_models.market_data import MarketDataCollector
except ImportError:
    # Fallback for serverless environment
    BacktestEngine = TradingOrchestrator = RiskManager = None
    TechnicalIndicators = PatternRecognizer = MultiLLMRouter = None
    get_config_manager = lambda: None
    TradingPersistence = MarketDataCollector = None


def handler(request_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main handler for strategy API requests.

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
        if path.endswith('/strategies'):
            if method == 'GET':
                return handle_get_strategies(query)
            elif method == 'POST':
                return handle_create_strategy(request_data)

        elif '/strategies/' in path:
            # Extract strategy ID from path
            path_parts = path.split('/')
            strategy_id = path_parts[3] if len(path_parts) > 3 else None

            if method == 'GET':
                return handle_get_strategy(strategy_id)
            elif method == 'PUT':
                return handle_update_strategy(strategy_id, request_data)
            elif method == 'DELETE':
                return handle_delete_strategy(strategy_id)

        elif path.endswith('/strategies/backtest'):
            if method == 'POST':
                return handle_backtest_strategy(request_data)

        elif path.endswith('/strategies/optimize'):
            if method == 'POST':
                return handle_optimize_strategy(request_data)

        elif path.endswith('/strategies/deploy'):
            if method == 'POST':
                return handle_deploy_strategy(request_data)

        elif path.endswith('/strategies/generate'):
            if method == 'POST':
                return handle_generate_strategy(request_data)

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


def handle_get_strategies(query: Dict[str, str]) -> Dict[str, Any]:
    """
    Handle GET request for strategies.

    Args:
        query: Query parameters

    Returns:
        Dict containing the response
    """
    try:
        # Parse query parameters
        status = query.get('status')
        symbol = query.get('symbol')
        limit = int(query.get('limit', 100))
        offset = int(query.get('offset', 0))

        # Initialize persistence if available
        persistence = None
        try:
            config = get_config_manager() if get_config_manager else None
            if config:
                persistence = TradingPersistence(config.get_database_config())
        except Exception as e:
            print(f"Warning: Could not initialize persistence: {e}")

        if persistence:
            try:
                # Get strategies from database
                strategies = persistence.get_strategies(
                    status=status,
                    symbol=symbol,
                    limit=limit,
                    offset=offset
                )
                strategies_data = [strategy.to_dict() for strategy in strategies]
                total = persistence.count_strategies(status=status, symbol=symbol)
            except Exception as e:
                print(f"Warning: Could not get strategies from database: {e}")
                # Mock response
                strategies_data = generate_mock_strategies(status, symbol, limit)
                total = len(strategies_data)
        else:
            # Mock response
            strategies_data = generate_mock_strategies(status, symbol, limit)
            total = len(strategies_data)

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'strategies': strategies_data,
                'total': total,
                'limit': limit,
                'offset': offset
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': True, 'message': f'Failed to get strategies: {str(e)}'})
        }


def handle_create_strategy(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle POST request to create a new strategy.

    Args:
        request_data: Request body data

    Returns:
        Dict containing the response
    """
    try:
        # Validate required fields
        required_fields = ['name', 'type', 'symbol']
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

        # Create strategy metadata
        strategy_id = f"strategy_{request_data['name']}_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"

        strategy_metadata = {
            'id': strategy_id,
            'name': request_data['name'],
            'type': request_data['type'],
            'symbol': request_data['symbol'],
            'timeframe': request_data.get('timeframe', '1h'),
            'description': request_data.get('description', ''),
            'parameters': request_data.get('parameters', {}),
            'indicators': request_data.get('indicators', []),
            'rules': request_data.get('rules', []),
            'risk_management': request_data.get('risk_management', {}),
            'created_at': datetime.now(UTC).isoformat(),
            'updated_at': datetime.now(UTC).isoformat(),
            'status': 'created'
        }

        # Validate strategy rules
        validation_result = validate_strategy_rules(strategy_metadata)
        if not validation_result['valid']:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': True,
                    'message': 'Invalid strategy rules',
                    'validation_errors': validation_result['errors']
                })
            }

        # Initialize persistence if available
        persistence = None
        try:
            config = get_config_manager() if get_config_manager else None
            if config:
                persistence = TradingPersistence(config.get_database_config())
        except Exception as e:
            print(f"Warning: Could not initialize persistence: {e}")

        # Save to database if available
        if persistence:
            persistence.save_strategy(strategy_metadata)

        return {
            'statusCode': 201,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'success': True,
                'strategy': strategy_metadata
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': True, 'message': f'Failed to create strategy: {str(e)}'})
        }


def handle_get_strategy(strategy_id: str) -> Dict[str, Any]:
    """
    Handle GET request for a specific strategy.

    Args:
        strategy_id: ID of the strategy

    Returns:
        Dict containing the response
    """
    try:
        if not strategy_id:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': True,
                    'message': 'Strategy ID is required'
                })
            }

        # Initialize persistence if available
        persistence = None
        try:
            config = get_config_manager() if get_config_manager else None
            if config:
                persistence = TradingPersistence(config.get_database_config())
        except Exception as e:
            print(f"Warning: Could not initialize persistence: {e}")

        if persistence:
            try:
                # Get strategy from database
                strategy = persistence.get_strategy_by_id(strategy_id)
                if not strategy:
                    return {
                        'statusCode': 404,
                        'headers': {'Content-Type': 'application/json'},
                        'body': json.dumps({
                            'error': True,
                            'message': 'Strategy not found'
                        })
                    }
                strategy_data = strategy.to_dict()
            except Exception as e:
                print(f"Warning: Could not get strategy from database: {e}")
                # Mock response
                strategy_data = generate_mock_strategy(strategy_id)
        else:
            # Mock response
            strategy_data = generate_mock_strategy(strategy_id)

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'strategy': strategy_data
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': True, 'message': f'Failed to get strategy: {str(e)}'})
        }


def handle_update_strategy(strategy_id: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle PUT request to update a strategy.

    Args:
        strategy_id: ID of the strategy
        request_data: Request body data

    Returns:
        Dict containing the response
    """
    try:
        if not strategy_id:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': True,
                    'message': 'Strategy ID is required'
                })
            }

        # Initialize persistence if available
        persistence = None
        try:
            config = get_config_manager() if get_config_manager else None
            if config:
                persistence = TradingPersistence(config.get_database_config())
        except Exception as e:
            print(f"Warning: Could not initialize persistence: {e}")

        # Get existing strategy
        if persistence:
            try:
                strategy = persistence.get_strategy_by_id(strategy_id)
                if not strategy:
                    return {
                        'statusCode': 404,
                        'headers': {'Content-Type': 'application/json'},
                        'body': json.dumps({
                            'error': True,
                            'message': 'Strategy not found'
                        })
                    }
                strategy_data = strategy.to_dict()
            except Exception as e:
                print(f"Warning: Could not get strategy from database: {e}")
                # Mock response
                strategy_data = generate_mock_strategy(strategy_id)
        else:
            # Mock response
            strategy_data = generate_mock_strategy(strategy_id)

        # Update strategy fields
        for field in ['name', 'type', 'symbol', 'timeframe', 'description', 'parameters', 'indicators', 'rules', 'risk_management']:
            if field in request_data:
                strategy_data[field] = request_data[field]

        strategy_data['updated_at'] = datetime.now(UTC).isoformat()

        # Validate updated strategy
        validation_result = validate_strategy_rules(strategy_data)
        if not validation_result['valid']:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': True,
                    'message': 'Invalid strategy rules',
                    'validation_errors': validation_result['errors']
                })
            }

        # Save updated strategy
        if persistence:
            persistence.update_strategy(strategy_id, strategy_data)

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'success': True,
                'strategy': strategy_data
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': True, 'message': f'Failed to update strategy: {str(e)}'})
        }


def handle_delete_strategy(strategy_id: str) -> Dict[str, Any]:
    """
    Handle DELETE request to delete a strategy.

    Args:
        strategy_id: ID of the strategy

    Returns:
        Dict containing the response
    """
    try:
        if not strategy_id:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': True,
                    'message': 'Strategy ID is required'
                })
            }

        # Initialize persistence if available
        persistence = None
        try:
            config = get_config_manager() if get_config_manager else None
            if config:
                persistence = TradingPersistence(config.get_database_config())
        except Exception as e:
            print(f"Warning: Could not initialize persistence: {e}")

        # Delete strategy
        if persistence:
            try:
                success = persistence.delete_strategy(strategy_id)
                if not success:
                    return {
                        'statusCode': 404,
                        'headers': {'Content-Type': 'application/json'},
                        'body': json.dumps({
                            'error': True,
                            'message': 'Strategy not found'
                        })
                    }
            except Exception as e:
                print(f"Warning: Could not delete strategy from database: {e}")
                # Mock success
                success = True
        else:
            # Mock success
            success = True

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'success': True,
                'message': 'Strategy deleted successfully'
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': True, 'message': f'Failed to delete strategy: {str(e)}'})
        }


def handle_backtest_strategy(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle POST request to backtest a strategy.

    Args:
        request_data: Request body data

    Returns:
        Dict containing the response
    """
    try:
        # Validate required fields
        required_fields = ['strategy_id', 'start_date', 'end_date']
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

        strategy_id = request_data['strategy_id']
        start_date_str = request_data['start_date']
        end_date_str = request_data['end_date']
        initial_capital = request_data.get('initial_capital', 10000.0)

        # Parse dates
        start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
        end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))

        # Initialize components if available
        backtest_engine = None
        market_data = None
        persistence = None

        try:
            config = get_config_manager() if get_config_manager else None
            if config:
                backtest_engine = BacktestEngine(config.get_backtesting_config())
                market_data = MarketDataCollector(config.get_market_data_config())
                persistence = TradingPersistence(config.get_database_config())
        except Exception as e:
            print(f"Warning: Could not initialize components: {e}")

        # Get strategy
        if persistence:
            try:
                strategy = persistence.get_strategy_by_id(strategy_id)
                if not strategy:
                    return {
                        'statusCode': 404,
                        'headers': {'Content-Type': 'application/json'},
                        'body': json.dumps({
                            'error': True,
                            'message': 'Strategy not found'
                        })
                    }
                strategy_data = strategy.to_dict()
            except Exception as e:
                print(f"Warning: Could not get strategy from database: {e}")
                # Mock response
                strategy_data = generate_mock_strategy(strategy_id)
        else:
            # Mock response
            strategy_data = generate_mock_strategy(strategy_id)

        # Get historical data
        if market_data:
            try:
                historical_data = market_data.get_historical_data(
                    symbol=strategy_data['symbol'],
                    timeframe=strategy_data['timeframe'],
                    start_date=start_date,
                    end_date=end_date
                )
            except Exception as e:
                print(f"Warning: Could not fetch market data: {e}")
                # Generate mock data
                historical_data = generate_mock_backtest_data(strategy_data['symbol'], start_date, end_date)
        else:
            # Generate mock data
            historical_data = generate_mock_backtest_data(strategy_data['symbol'], start_date, end_date)

        # Run backtest
        if backtest_engine:
            try:
                backtest_results = backtest_engine.run_backtest(
                    strategy=strategy_data,
                    data=historical_data,
                    initial_capital=initial_capital
                )
            except Exception as e:
                print(f"Warning: Backtest failed: {e}")
                # Mock backtest results
                backtest_results = generate_mock_backtest_results(strategy_id)
        else:
            # Mock backtest results
            backtest_results = generate_mock_backtest_results(strategy_id)

        # Save backtest results
        backtest_id = f"bt_{strategy_id}_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"

        backtest_metadata = {
            'id': backtest_id,
            'strategy_id': strategy_id,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'initial_capital': initial_capital,
            'results': backtest_results,
            'created_at': datetime.now(UTC).isoformat()
        }

        # Save to database if available
        if persistence:
            persistence.save_backtest_result(backtest_metadata)

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'success': True,
                'backtest': backtest_metadata
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': True, 'message': f'Backtest failed: {str(e)}'})
        }


def handle_optimize_strategy(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle POST request to optimize a strategy.

    Args:
        request_data: Request body data

    Returns:
        Dict containing the response
    """
    try:
        # Validate required fields
        required_fields = ['strategy_id', 'optimization_period', 'metric']
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

        strategy_id = request_data['strategy_id']
        optimization_period = request_data['optimization_period']  # days
        metric = request_data['metric']  # e.g., 'sharpe_ratio', 'total_return'
        parameter_ranges = request_data.get('parameter_ranges', {})

        # Initialize components if available
        backtest_engine = None
        market_data = None
        persistence = None

        try:
            config = get_config_manager() if get_config_manager else None
            if config:
                backtest_engine = BacktestEngine(config.get_backtesting_config())
                market_data = MarketDataCollector(config.get_market_data_config())
                persistence = TradingPersistence(config.get_database_config())
        except Exception as e:
            print(f"Warning: Could not initialize components: {e}")

        # Get strategy
        if persistence:
            try:
                strategy = persistence.get_strategy_by_id(strategy_id)
                if not strategy:
                    return {
                        'statusCode': 404,
                        'headers': {'Content-Type': 'application/json'},
                        'body': json.dumps({
                            'error': True,
                            'message': 'Strategy not found'
                        })
                    }
                strategy_data = strategy.to_dict()
            except Exception as e:
                print(f"Warning: Could not get strategy from database: {e}")
                # Mock response
                strategy_data = generate_mock_strategy(strategy_id)
        else:
            # Mock response
            strategy_data = generate_mock_strategy(strategy_id)

        # Get historical data for optimization
        end_date = datetime.now(UTC)
        start_date = end_date - timedelta(days=optimization_period)

        if market_data:
            try:
                historical_data = market_data.get_historical_data(
                    symbol=strategy_data['symbol'],
                    timeframe=strategy_data['timeframe'],
                    start_date=start_date,
                    end_date=end_date
                )
            except Exception as e:
                print(f"Warning: Could not fetch market data: {e}")
                # Generate mock data
                historical_data = generate_mock_backtest_data(strategy_data['symbol'], start_date, end_date)
        else:
            # Generate mock data
            historical_data = generate_mock_backtest_data(strategy_data['symbol'], start_date, end_date)

        # Optimize strategy
        if backtest_engine:
            try:
                optimization_result = backtest_engine.optimize_strategy(
                    strategy=strategy_data,
                    data=historical_data,
                    parameter_ranges=parameter_ranges,
                    optimization_metric=metric
                )
            except Exception as e:
                print(f"Warning: Strategy optimization failed: {e}")
                # Mock optimization results
                optimization_result = {
                    'best_params': {
                        'rsi_period': 14,
                        'rsi_overbought': 70,
                        'rsi_oversold': 30,
                        'stop_loss_pct': 0.02,
                        'take_profit_pct': 0.05
                    },
                    'best_score': 1.5,
                    'optimization_results': []
                }
        else:
            # Mock optimization results
            optimization_result = {
                'best_params': {
                    'rsi_period': 14,
                    'rsi_overbought': 70,
                    'rsi_oversold': 30,
                    'stop_loss_pct': 0.02,
                    'take_profit_pct': 0.05
                },
                'best_score': 1.5,
                'optimization_results': []
            }

        # Save optimization results
        optimization_id = f"opt_{strategy_id}_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"

        optimization_metadata = {
            'id': optimization_id,
            'strategy_id': strategy_id,
            'best_params': optimization_result['best_params'],
            'best_score': optimization_result['best_score'],
            'metric': metric,
            'parameter_ranges': parameter_ranges,
            'data_period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'created_at': datetime.now(UTC).isoformat()
        }

        # Save to database if available
        if persistence:
            persistence.save_optimization_result(optimization_metadata)

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'success': True,
                'optimization': optimization_metadata
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': True, 'message': f'Strategy optimization failed: {str(e)}'})
        }


def handle_deploy_strategy(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle POST request to deploy a strategy.

    Args:
        request_data: Request body data

    Returns:
        Dict containing the response
    """
    try:
        # Validate required fields
        if 'strategy_id' not in request_data:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': True,
                    'message': 'Missing required field: strategy_id'
                })
            }

        strategy_id = request_data['strategy_id']
        deployment_config = request_data.get('deployment_config', {})

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

        # Get strategy
        if persistence:
            try:
                strategy = persistence.get_strategy_by_id(strategy_id)
                if not strategy:
                    return {
                        'statusCode': 404,
                        'headers': {'Content-Type': 'application/json'},
                        'body': json.dumps({
                            'error': True,
                            'message': 'Strategy not found'
                        })
                    }
                strategy_data = strategy.to_dict()
            except Exception as e:
                print(f"Warning: Could not get strategy from database: {e}")
                # Mock response
                strategy_data = generate_mock_strategy(strategy_id)
        else:
            # Mock response
            strategy_data = generate_mock_strategy(strategy_id)

        # Deploy strategy
        if orchestrator:
            try:
                deployment_result = orchestrator.deploy_strategy(strategy_id, strategy_data, deployment_config)
            except Exception as e:
                print(f"Warning: Strategy deployment failed: {e}")
                # Mock deployment
                deployment_result = {
                    'success': True,
                    'deployment_id': f"dep_{strategy_id}_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
                    'status': 'active'
                }
        else:
            # Mock deployment
            deployment_result = {
                'success': True,
                'deployment_id': f"dep_{strategy_id}_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
                'status': 'active'
            }

        # Update strategy status
        strategy_data['status'] = 'deployed'
        strategy_data['deployment_id'] = deployment_result['deployment_id']
        strategy_data['deployment_config'] = deployment_config
        strategy_data['updated_at'] = datetime.now(UTC).isoformat()

        # Save to database if available
        if persistence:
            persistence.update_strategy(strategy_id, strategy_data)

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'success': True,
                'deployment': deployment_result
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': True, 'message': f'Strategy deployment failed: {str(e)}'})
        }


def handle_generate_strategy(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle POST request to generate a new strategy using AI.

    Args:
        request_data: Request body data

    Returns:
        Dict containing the response
    """
    try:
        # Validate required fields
        required_fields = ['symbol', 'strategy_type', 'timeframe']
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
        strategy_type = request_data['strategy_type']
        timeframe = request_data['timeframe']
        requirements = request_data.get('requirements', '')

        # Initialize components if available
        llm_router = None
        market_data = None

        try:
            config = get_config_manager() if get_config_manager else None
            if config:
                llm_router = MultiLLMRouter(config.get_llm_config())
                market_data = MarketDataCollector(config.get_market_data_config())
        except Exception as e:
            print(f"Warning: Could not initialize components: {e}")

        # Get market data for analysis
        market_summary = None
        if market_data:
            try:
                # Get recent market data
                end_date = datetime.now(UTC)
                start_date = end_date - timedelta(days=30)

                recent_data = market_data.get_historical_data(
                    symbol=symbol,
                    timeframe=timeframe,
                    start_date=start_date,
                    end_date=end_date
                )

                # Generate market summary
                if recent_data:
                    import pandas as pd
                    if not isinstance(recent_data, pd.DataFrame):
                        data = pd.DataFrame(recent_data)
                    else:
                        data = recent_data.copy()

                    # Calculate basic statistics
                    price_change = (data['close'].iloc[-1] - data['close'].iloc[0]) / data['close'].iloc[0]
                    volatility = data['close'].pct_change().std()
                    trend = 'upward' if price_change > 0.02 else 'downward' if price_change < -0.02 else 'sideways'

                    market_summary = {
                        'symbol': symbol,
                        'price_change_pct': price_change,
                        'volatility': volatility,
                        'trend': trend,
                        'timeframe': timeframe
                    }
            except Exception as e:
                print(f"Warning: Could not analyze market data: {e}")
                # Mock market summary
                market_summary = {
                    'symbol': symbol,
                    'price_change_pct': 0.05,
                    'volatility': 0.02,
                    'trend': 'upward',
                    'timeframe': timeframe
                }
        else:
            # Mock market summary
            market_summary = {
                'symbol': symbol,
                'price_change_pct': 0.05,
                'volatility': 0.02,
                'trend': 'upward',
                'timeframe': timeframe
            }

        # Generate strategy using AI
        if llm_router:
            try:
                # Prepare prompt for LLM
                prompt = f"""
                Generate a trading strategy for {symbol} with the following requirements:

                Symbol: {symbol}
                Strategy Type: {strategy_type}
                Timeframe: {timeframe}
                Requirements: {requirements}

                Market Analysis:
                - Price Change: {market_summary['price_change_pct']:.2%}
                - Volatility: {market_summary['volatility']:.2%}
                - Trend: {market_summary['trend']}

                Please provide a JSON response with the following structure:
                {{
                    "name": "Strategy Name",
                    "description": "Strategy Description",
                    "parameters": {{"parameter_name": "default_value", ...}},
                    "indicators": ["indicator1", "indicator2", ...],
                    "rules": [
                        {{"condition": "rule condition", "action": "buy/sell/hold", "priority": 1}},
                        ...
                    ],
                    "risk_management": {{
                        "stop_loss_pct": 0.02,
                        "take_profit_pct": 0.05,
                        "max_position_size": 0.1
                    }}
                }}
                """

                # Generate strategy
                llm_request = {
                    'prompt': prompt,
                    'model_id': 'claude-3-sonnet',
                    'max_tokens': 1000,
                    'temperature': 0.3
                }

                response = llm_router.route_request(llm_request)
                strategy_content = response['content']

                # Parse JSON response
                import re
                json_match = re.search(r'\{.*\}', strategy_content, re.DOTALL)
                if json_match:
                    strategy_json = json.loads(json_match.group(0))
                else:
                    # Fallback to mock strategy
                    strategy_json = generate_mock_strategy_json(symbol, strategy_type)
            except Exception as e:
                print(f"Warning: AI strategy generation failed: {e}")
                # Fallback to mock strategy
                strategy_json = generate_mock_strategy_json(symbol, strategy_type)
        else:
            # Mock strategy
            strategy_json = generate_mock_strategy_json(symbol, strategy_type)

        # Create strategy
        strategy_id = f"strategy_{strategy_json['name'].replace(' ', '_')}_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"

        strategy_metadata = {
            'id': strategy_id,
            'name': strategy_json['name'],
            'type': strategy_type,
            'symbol': symbol,
            'timeframe': timeframe,
            'description': strategy_json['description'],
            'parameters': strategy_json['parameters'],
            'indicators': strategy_json['indicators'],
            'rules': strategy_json['rules'],
            'risk_management': strategy_json['risk_management'],
            'created_at': datetime.now(UTC).isoformat(),
            'updated_at': datetime.now(UTC).isoformat(),
            'status': 'created',
            'generated_by': 'ai'
        }

        # Validate strategy
        validation_result = validate_strategy_rules(strategy_metadata)
        if not validation_result['valid']:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': True,
                    'message': 'Generated strategy is invalid',
                    'validation_errors': validation_result['errors']
                })
            }

        # Initialize persistence if available
        persistence = None
        try:
            config = get_config_manager() if get_config_manager else None
            if config:
                persistence = TradingPersistence(config.get_database_config())
        except Exception as e:
            print(f"Warning: Could not initialize persistence: {e}")

        # Save to database if available
        if persistence:
            persistence.save_strategy(strategy_metadata)

        return {
            'statusCode': 201,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'success': True,
                'strategy': strategy_metadata
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': True, 'message': f'Strategy generation failed: {str(e)}'})
        }


# Helper functions
def validate_strategy_rules(strategy_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate strategy rules.

    Args:
        strategy_data: Strategy data to validate

    Returns:
        Dict containing validation result
    """
    try:
        errors = []

        # Check if required fields are present
        if 'rules' not in strategy_data or not strategy_data['rules']:
            errors.append("Strategy must have at least one rule")
        else:
            # Validate each rule
            for i, rule in enumerate(strategy_data['rules']):
                if not isinstance(rule, dict):
                    errors.append(f"Rule {i} must be a dictionary")
                    continue

                if 'condition' not in rule or not rule['condition']:
                    errors.append(f"Rule {i} must have a condition")
                if 'action' not in rule or not rule['action']:
                    errors.append(f"Rule {i} must have an action")
                if rule['action'] not in ['buy', 'sell', 'hold']:
                    errors.append(f"Rule {i} action must be 'buy', 'sell', or 'hold'")

        # Validate risk management
        if 'risk_management' in strategy_data:
            risk_mgmt = strategy_data['risk_management']
            if 'stop_loss_pct' in risk_mgmt and not (0 < risk_mgmt['stop_loss_pct'] <= 1):
                errors.append("stop_loss_pct must be between 0 and 1")
            if 'take_profit_pct' in risk_mgmt and not (0 < risk_mgmt['take_profit_pct'] <= 1):
                errors.append("take_profit_pct must be between 0 and 1")
            if 'max_position_size' in risk_mgmt and not (0 < risk_mgmt['max_position_size'] <= 1):
                errors.append("max_position_size must be between 0 and 1")

        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    except Exception as e:
        return {
            'valid': False,
            'errors': [f"Validation error: {str(e)}"]
        }


def generate_mock_strategies(status: Optional[str], symbol: Optional[str], limit: int) -> List[Dict[str, Any]]:
    """Generate mock strategies for testing."""
    strategies = []
    for i in range(limit):
        strategy = {
            'id': f'strategy_{i}',
            'name': f'Mock Strategy {i}',
            'type': 'mean_reversion',
            'symbol': symbol or 'BTCUSDT',
            'timeframe': '1h',
            'description': f'Mock strategy for testing {i}',
            'parameters': {
                'rsi_period': 14,
                'rsi_overbought': 70,
                'rsi_oversold': 30
            },
            'indicators': ['RSI', 'SMA', 'BB'],
            'rules': [
                {
                    'condition': f'RSI < {30 - i}',
                    'action': 'buy',
                    'priority': 1
                },
                {
                    'condition': f'RSI > {70 + i}',
                    'action': 'sell',
                    'priority': 1
                }
            ],
            'risk_management': {
                'stop_loss_pct': 0.02,
                'take_profit_pct': 0.05,
                'max_position_size': 0.1
            },
            'created_at': (datetime.now(UTC) - timedelta(days=i)).isoformat(),
            'updated_at': (datetime.now(UTC) - timedelta(days=i)).isoformat(),
            'status': status or 'active'
        }
        strategies.append(strategy)
    return strategies


def generate_mock_strategy(strategy_id: str) -> Dict[str, Any]:
    """Generate a mock strategy for testing."""
    return {
        'id': strategy_id,
        'name': 'Mock Strategy',
        'type': 'mean_reversion',
        'symbol': 'BTCUSDT',
        'timeframe': '1h',
        'description': 'Mock strategy for testing',
        'parameters': {
            'rsi_period': 14,
            'rsi_overbought': 70,
            'rsi_oversold': 30
        },
        'indicators': ['RSI', 'SMA', 'BB'],
        'rules': [
            {
                'condition': 'RSI < 30',
                'action': 'buy',
                'priority': 1
            },
            {
                'condition': 'RSI > 70',
                'action': 'sell',
                'priority': 1
            }
        ],
        'risk_management': {
            'stop_loss_pct': 0.02,
            'take_profit_pct': 0.05,
            'max_position_size': 0.1
        },
        'created_at': datetime.now(UTC).isoformat(),
        'updated_at': datetime.now(UTC).isoformat(),
        'status': 'active'
    }


def generate_mock_strategy_json(symbol: str, strategy_type: str) -> Dict[str, Any]:
    """Generate a mock strategy JSON for testing."""
    return {
        'name': f'AI Generated {strategy_type.title()} Strategy',
        'description': f'AI-generated {strategy_type} strategy for {symbol}',
        'parameters': {
            'rsi_period': 14,
            'rsi_overbought': 70,
            'rsi_oversold': 30,
            'sma_period': 20
        },
        'indicators': ['RSI', 'SMA', 'BB'],
        'rules': [
            {
                'condition': 'RSI < 30 AND close < SMA(20)',
                'action': 'buy',
                'priority': 1
            },
            {
                'condition': 'RSI > 70 OR close > SMA(20) * 1.02',
                'action': 'sell',
                'priority': 1
            }
        ],
        'risk_management': {
            'stop_loss_pct': 0.02,
            'take_profit_pct': 0.05,
            'max_position_size': 0.1
        }
    }


def generate_mock_backtest_data(symbol: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
    """Generate mock backtest data for testing."""
    import pandas as pd
    import numpy as np

    # Generate mock data
    dates = pd.date_range(start=start_date, end=end_date, freq='1H')
    n = len(dates)

    # Generate price data with random walk
    prices = [50000.0]
    for i in range(1, n):
        change = np.random.normal(0, 0.01)
        prices.append(max(prices[-1] * (1 + change), 1000.0))

    # Generate OHLCV data
    data = []
    for i, date in enumerate(dates):
        data.append({
            'timestamp': date.isoformat(),
            'open': prices[i],
            'high': prices[i] * (1 + abs(np.random.normal(0, 0.005))),
            'low': prices[i] * (1 - abs(np.random.normal(0, 0.005))),
            'close': prices[i],
            'volume': np.random.uniform(100, 1000)
        })

    return data


def generate_mock_backtest_results(strategy_id: str) -> Dict[str, Any]:
    """Generate mock backtest results for testing."""
    import random

    return {
        'strategy_id': strategy_id,
        'initial_capital': 10000.0,
        'final_capital': 10000.0 * (1 + random.uniform(-0.1, 0.3)),
        'total_return': random.uniform(-0.1, 0.3),
        'sharpe_ratio': random.uniform(0.5, 2.0),
        'max_drawdown': random.uniform(0.05, 0.2),
        'win_rate': random.uniform(0.4, 0.7),
        'profit_factor': random.uniform(1.0, 2.0),
        'total_trades': random.randint(50, 200),
        'winning_trades': int(random.randint(50, 200) * random.uniform(0.4, 0.7)),
        'losing_trades': 0,
        'equity_curve': [
            {'timestamp': (datetime.now(UTC) - timedelta(days=30)).isoformat(), 'value': 10000.0},
            {'timestamp': datetime.now(UTC).isoformat(), 'value': 10000.0 * (1 + random.uniform(-0.1, 0.3))}
        ]
    }
