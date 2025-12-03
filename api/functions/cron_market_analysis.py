"""
Cron job for automated market analysis.
This function runs on a schedule (e.g., every 30 minutes) to analyze
market conditions, identify trading opportunities, and update the database
with the latest market insights.
Designed to work with Vercel's cron job functionality.
"""

import json
import os
import sys
from datetime import datetime, timedelta, UTC
from typing import Dict, Any, List

# Add project root to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from libs.trading_models.market_data import MarketDataCollector
    from libs.trading_models.market_data_ingestion import MarketDataIngestion
    from libs.trading_models.technical_indicators import TechnicalIndicators
    from libs.trading_models.pattern_recognition import PatternRecognizer
    from libs.trading_models.confluence_scoring import ConfluenceScorer
    from libs.trading_models.config_manager import get_config_manager
    from libs.trading_models.persistence import TradingPersistence
    from libs.trading_models.signals import SignalGenerator
    from libs.trading_models.llm_integration import MultiLLMRouter
    import pandas as pd
    import numpy as np
except ImportError:
    # Fallback for serverless environment
    MarketDataCollector = MarketDataIngestion = None
    TechnicalIndicators = PatternRecognizer = ConfluenceScorer = None
    get_config_manager = SignalGenerator = MultiLLMRouter = lambda: None
    TradingPersistence = None
    pd = np = None


def handler(request_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main handler for automated market analysis cron job.

    This function is triggered by Vercel's cron job scheduler and:
    1. Fetches latest market data for all configured symbols
    2. Analyzes technical indicators and patterns
    3. Generates trading signals based on multiple analysis methods
    4. Updates the database with new market insights
    5. Triggers alerts for significant market events

    Args:
        request_context: Dictionary containing request information

    Returns:
        Dict containing the response
    """
    try:
        # Initialize components
        config = get_config_manager() if get_config_manager else None
        persistence = TradingPersistence(config.get_database_config()) if config and TradingPersistence else None
        market_data = MarketDataCollector(config.get_market_data_config()) if config and MarketDataCollector else None
        technical_indicators = TechnicalIndicators() if TechnicalIndicators else None
        pattern_recognizer = PatternRecognizer() if PatternRecognizer else None
        confluence_scorer = ConfluenceScorer(config.get_confluence_config()) if config and ConfluenceScorer else None
        signal_generator = SignalGenerator(config.get_signal_config()) if config and SignalGenerator else None

        # Analysis results summary
        analysis_results = {
            'timestamp': datetime.now(UTC).isoformat(),
            'status': 'success',
            'symbols_analyzed': [],
            'signals_generated': [],
            'patterns_detected': [],
            'market_events': [],
            'errors': []
        }

        # Get symbols to analyze
        symbols = get_symbols_for_analysis(persistence)

        # Process each symbol
        for symbol in symbols:
            try:
                symbol_result = analyze_symbol(
                    symbol, market_data, technical_indicators,
                    pattern_recognizer, confluence_scorer, signal_generator
                )
                analysis_results['symbols_analyzed'].append(symbol)

                # Collect signals
                if symbol_result.get('signals'):
                    analysis_results['signals_generated'].extend(
                        [{'symbol': symbol, **signal} for signal in symbol_result['signals']]
                    )

                # Collect patterns
                if symbol_result.get('patterns'):
                    analysis_results['patterns_detected'].extend(
                        [{'symbol': symbol, **pattern} for pattern in symbol_result['patterns']]
                    )

                # Collect market events
                if symbol_result.get('market_events'):
                    analysis_results['market_events'].extend(
                        [{'symbol': symbol, **event} for event in symbol_result['market_events']]
                    )
            except Exception as e:
                analysis_results['errors'].append({
                    'symbol': symbol,
                    'error': str(e)
                })

        # Save analysis results to database
        if persistence:
            persistence.save_market_analysis(analysis_results)

        # Determine overall status
        if analysis_results['errors'] and len(analysis_results['errors']) == len(symbols):
            analysis_results['status'] = 'failed'
        elif analysis_results['errors']:
            analysis_results['status'] = 'partial_success'

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(analysis_results)
        }
    except Exception as e:
        error_response = {
            'timestamp': datetime.now(UTC).isoformat(),
            'status': 'error',
            'error': str(e)
        }

        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(error_response)
        }


def get_symbols_for_analysis(persistence) -> List[str]:
    """
    Get list of symbols to analyze.

    Args:
        persistence: Trading persistence instance

    Returns:
        List of symbols
    """
    try:
        if persistence:
            # Get active strategies from database
            strategies = persistence.get_strategies(status='active')
            symbols = list(set([strategy.symbol for strategy in strategies]))

            # If no strategies, get default symbols
            if not symbols:
                symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'DOTUSDT']
            return symbols
        else:
            # Mock symbols for testing
            return ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
    except Exception:
        # Fallback to default symbols
        return ['BTCUSDT', 'ETHUSDT']


def analyze_symbol(symbol: str, market_data, technical_indicators,
                pattern_recognizer, confluence_scorer, signal_generator) -> Dict[str, Any]:
    """
    Analyze a specific symbol for trading opportunities.

    Args:
        symbol: Trading symbol
        market_data: Market data collector instance
        technical_indicators: Technical indicators instance
        pattern_recognizer: Pattern recognizer instance
        confluence_scorer: Confluence scorer instance
        signal_generator: Signal generator instance

    Returns:
        Dict containing analysis results
    """
    try:
        result = {
            'symbol': symbol,
            'timestamp': datetime.now(UTC).isoformat(),
            'signals': [],
            'patterns': [],
            'market_events': [],
            'error': None
        }

        # Get market data for multiple timeframes
        timeframes = ['15m', '1h', '4h', '1d']
        market_data_dict = {}

        for timeframe in timeframes:
            try:
                if market_data:
                    data = market_data.get_latest_data(symbol, timeframe, 200)
                    # Convert to DataFrame if needed
                    if pd and not isinstance(data, pd.DataFrame):
                        df = pd.DataFrame(data)
                    elif pd:
                        df = data.copy()
                    else:
                        # Fallback for serverless
                        continue
                else:
                    # Generate mock data
                    df = generate_mock_market_data(symbol, timeframe, 200)

                market_data_dict[timeframe] = df
            except Exception as e:
                print(f"Error getting {timeframe} data for {symbol}: {e}")
                continue

        # Skip if no data available
        if not market_data_dict:
            result['error'] = "No market data available"
            return result

        # Analyze each timeframe
        for timeframe, df in market_data_dict.items():
            try:
                # Calculate technical indicators
                indicators = calculate_technical_indicators(df, technical_indicators)

                # Recognize patterns
                patterns = recognize_patterns(df, pattern_recognizer)

                # Calculate confluence score
                confluence = calculate_confluence_score(df, confluence_scorer)

                # Generate signals
                signals = generate_trading_signals(
                    symbol, df, indicators, patterns, confluence,
                    signal_generator, timeframe
                )

                # Detect market events
                market_events = detect_market_events(df, indicators, timeframe)

                # Add to results
                result['signals'].extend(signals)
                result['patterns'].extend(patterns)
                result['market_events'].extend(market_events)
            except Exception as e:
                print(f"Error analyzing {symbol} {timeframe}: {e}")
                continue

        return result
    except Exception as e:
        return {
            'symbol': symbol,
            'timestamp': datetime.now(UTC).isoformat(),
            'error': str(e),
            'signals': [],
            'patterns': [],
            'market_events': []
        }


def calculate_technical_indicators(df, technical_indicators) -> Dict[str, Any]:
    """
    Calculate technical indicators for market data.

    Args:
        df: DataFrame with OHLCV data
        technical_indicators: Technical indicators instance

    Returns:
        Dict containing indicator values
    """
    try:
        indicators = {}

        if technical_indicators and pd is not None:
            try:
                # Moving averages
                indicators['sma_20'] = technical_indicators.calculate_sma(df, period=20)
                indicators['sma_50'] = technical_indicators.calculate_sma(df, period=50)
                indicators['ema_12'] = technical_indicators.calculate_ema(df, period=12)
                indicators['ema_26'] = technical_indicators.calculate_ema(df, period=26)

                # MACD
                indicators['macd'] = technical_indicators.calculate_macd(df)

                # RSI
                indicators['rsi'] = technical_indicators.calculate_rsi(df, period=14)

                # Bollinger Bands
                indicators['bb'] = technical_indicators.calculate_bollinger_bands(df)

                # ATR
                indicators['atr'] = technical_indicators.calculate_atr(df)

                # Stochastic
                indicators['stoch'] = technical_indicators.calculate_stochastic(df)

                # Get latest values
                latest_indicators = {}
                for name, values in indicators.items():
                    if isinstance(values, dict):
                        latest_indicators[name] = {k: v.iloc[-1] if hasattr(v, 'iloc') else v for k, v in values.items()}
                    elif hasattr(values, 'iloc'):
                        latest_indicators[name] = values.iloc[-1]
                    else:
                        latest_indicators[name] = values

                return latest_indicators
            except Exception as e:
                print(f"Error calculating technical indicators: {e}")
                # Fall through to mock indicators
        else:
            # Generate mock indicators for serverless environment
            return {
                'sma_20': 50000.0,
                'sma_50': 49000.0,
                'ema_12': 50500.0,
                'ema_26': 49500.0,
                'macd': {'macd': 100.0, 'signal': 80.0, 'histogram': 20.0},
                'rsi': 55.0,
                'bb': {'upper': 51000.0, 'middle': 50000.0, 'lower': 49000.0},
                'atr': 500.0,
                'stoch': {'k': 60.0, 'd': 55.0}
            }
    except Exception as e:
        print(f"Error in calculate_technical_indicators: {e}")
        return {}


def recognize_patterns(df, pattern_recognizer) -> List[Dict[str, Any]]:
    """
    Recognize chart patterns in market data.

    Args:
        df: DataFrame with OHLCV data
        pattern_recognizer: Pattern recognizer instance

    Returns:
        List of detected patterns
    """
    try:
        if pattern_recognizer and pd is not None:
            try:
                patterns = pattern_recognizer.recognize_patterns(df, pattern_types='all')

                # Format patterns for consistency
                formatted_patterns = []
                for pattern in patterns:
                    if isinstance(pattern, dict):
                        formatted_patterns.append({
                            'type': pattern.get('type', 'Unknown'),
                            'direction': pattern.get('direction', 'neutral'),
                            'strength': pattern.get('strength', 0.5),
                            'timeframe': pattern.get('timeframe', 'unknown'),
                            'start_time': pattern.get('start_time', datetime.now(UTC).isoformat()),
                            'end_time': pattern.get('end_time', datetime.now(UTC).isoformat())
                        })

                return formatted_patterns
            except Exception as e:
                print(f"Error recognizing patterns: {e}")
                # Fall through to mock patterns
        else:
            # Generate mock patterns for serverless environment
            import random
            return [
                {
                    'type': random.choice(['Triangle', 'Flag', 'Head and Shoulders', 'Double Top']),
                    'direction': random.choice(['bullish', 'bearish']),
                    'strength': random.uniform(0.6, 0.9),
                    'timeframe': '1h',
                    'start_time': (datetime.now(UTC) - timedelta(hours=24)).isoformat(),
                    'end_time': datetime.now(UTC).isoformat()
                }
            ]
    except Exception as e:
        print(f"Error in recognize_patterns: {e}")
        return []


def calculate_confluence_score(df, confluence_scorer) -> Dict[str, Any]:
    """
    Calculate confluence score for market data.

    Args:
        df: DataFrame with OHLCV data
        confluence_scorer: Confluence scorer instance

    Returns:
        Dict containing confluence score
    """
    try:
        if confluence_scorer and pd is not None:
            try:
                confluence = confluence_scorer.calculate_confluence(df)

                # Format for consistency
                return {
                    'overall_score': confluence.get('overall_score', 0.5),
                    'buy_score': confluence.get('buy_score', 0.5),
                    'sell_score': confluence.get('sell_score', 0.5),
                    'neutral_score': confluence.get('neutral_score', 0.5),
                    'components': confluence.get('components', {}),
                    'recommendation': confluence.get('recommendation', 'HOLD')
                }
            except Exception as e:
                print(f"Error calculating confluence score: {e}")
                # Fall through to mock confluence
        else:
            # Generate mock confluence for serverless environment
            import random
            overall = random.uniform(0.3, 0.9)
            buy = overall * random.uniform(0.8, 1.2)
            sell = overall * random.uniform(0.8, 1.2)
            neutral = overall * random.uniform(0.8, 1.2)

            # Normalize
            total = buy + sell + neutral
            buy, sell, neutral = buy/total, sell/total, neutral/total

            return {
                'overall_score': overall,
                'buy_score': buy,
                'sell_score': sell,
                'neutral_score': neutral,
                'components': {
                    'trend': random.uniform(0.3, 0.9),
                    'momentum': random.uniform(0.3, 0.9),
                    'volume': random.uniform(0.3, 0.9),
                    'volatility': random.uniform(0.3, 0.9)
                },
                'recommendation': random.choice(['STRONG_BUY', 'BUY', 'HOLD', 'SELL', 'STRONG_SELL'])
            }
    except Exception as e:
        print(f"Error in calculate_confluence_score: {e}")
        return {
            'overall_score': 0.5,
            'buy_score': 0.33,
            'sell_score': 0.33,
            'neutral_score': 0.34,
            'components': {},
            'recommendation': 'HOLD'
        }


def generate_trading_signals(symbol: str, df, indicators: Dict[str, Any],
                         patterns: List[Dict[str, Any]], confluence: Dict[str, Any],
                         signal_generator, timeframe: str) -> List[Dict[str, Any]]:
    """
    Generate trading signals based on analysis.

    Args:
        symbol: Trading symbol
        df: DataFrame with OHLCV data
        indicators: Technical indicators
        patterns: Detected patterns
        confluence: Confluence score
        signal_generator: Signal generator instance
        timeframe: Timeframe of analysis

    Returns:
        List of trading signals
    """
    try:
        signals = []

        if signal_generator and pd is not None:
            try:
                # Generate signals using signal generator
                raw_signals = signal_generator.generate_signals(
                    symbol, df, indicators, patterns, confluence, timeframe
                )

                # Format signals for consistency
                for signal in raw_signals:
                    if isinstance(signal, dict):
                        signals.append({
                            'action': signal.get('action', 'HOLD'),
                            'strength': signal.get('strength', 0.5),
                            'confidence': signal.get('confidence', 0.5),
                            'reason': signal.get('reason', 'Automated analysis'),
                            'timeframe': timeframe,
                            'timestamp': datetime.now(UTC).isoformat()
                        })
            except Exception as e:
                print(f"Error generating signals with signal generator: {e}")
                # Fall through to custom signal generation
        else:
            # Generate mock signals for serverless environment
            import random

            # Generate signal based on confluence recommendation
            recommendation = confluence.get('recommendation', 'HOLD')
            strength = confluence.get('overall_score', 0.5)

            action = 'HOLD'
            if recommendation in ['STRONG_BUY', 'BUY']:
                action = 'BUY'
            elif recommendation in ['STRONG_SELL', 'SELL']:
                action = 'SELL'

            # Only generate signal if strength is above threshold
            if strength > 0.6:
                signals.append({
                    'action': action,
                    'strength': strength,
                    'confidence': min(strength + 0.1, 1.0),
                    'reason': f"Confluence analysis: {recommendation}",
                    'timeframe': timeframe,
                    'timestamp': datetime.now(UTC).isoformat()
                })

        return signals
    except Exception as e:
        print(f"Error in generate_trading_signals: {e}")
        return []


def detect_market_events(df, indicators: Dict[str, Any], timeframe: str) -> List[Dict[str, Any]]:
    """
    Detect significant market events.

    Args:
        df: DataFrame with OHLCV data
        indicators: Technical indicators
        timeframe: Timeframe of analysis

    Returns:
        List of market events
    """
    try:
        events = []

        if not df.empty and indicators:
            # Get current and previous values
            current_rsi = indicators.get('rsi')
            current_price = df['close'].iloc[-1] if hasattr(df, 'iloc') else None

            # Detect RSI extremes
            if current_rsi:
                if current_rsi > 70:
                    events.append({
                        'type': 'RSI_OVERBOUGHT',
                        'value': current_rsi,
                        'message': f"RSI indicates overbought conditions at {current_rsi:.2f}",
                        'timeframe': timeframe,
                        'timestamp': datetime.now(UTC).isoformat()
                    })
                elif current_rsi < 30:
                    events.append({
                        'type': 'RSI_OVERSOLD',
                        'value': current_rsi,
                        'message': f"RSI indicates oversold conditions at {current_rsi:.2f}",
                        'timeframe': timeframe,
                        'timestamp': datetime.now(UTC).isoformat()
                    })

            # Detect price SMA crossovers
            sma_20 = indicators.get('sma_20')
            sma_50 = indicators.get('sma_50')

            if sma_20 and sma_50 and current_price:
                if current_price > sma_20 > sma_50:
                    events.append({
                        'type': 'BULLISH_SMA_CROSSOVER',
                        'value': current_price,
                        'message': f"Price above both SMA20 ({sma_20:.2f}) and SMA50 ({sma_50:.2f})",
                        'timeframe': timeframe,
                        'timestamp': datetime.now(UTC).isoformat()
                    })
                elif current_price < sma_20 < sma_50:
                    events.append({
                        'type': 'BEARISH_SMA_CROSSOVER',
                        'value': current_price,
                        'message': f"Price below both SMA20 ({sma_20:.2f}) and SMA50 ({sma_50:.2f})",
                        'timeframe': timeframe,
                        'timestamp': datetime.now(UTC).isoformat()
                    })

            # Detect MACD crossovers
            macd = indicators.get('macd', {})
            macd_line = macd.get('macd')
            signal_line = macd.get('signal')
            histogram = macd.get('histogram')

            if macd_line and signal_line and histogram:
                if histogram > 0 and macd_line > signal_line:
                    events.append({
                        'type': 'BULLISH_MACD_CROSSOVER',
                        'value': histogram,
                        'message': f"MACD bullish crossover: MACD ({macd_line:.4f}) above Signal ({signal_line:.4f})",
                        'timeframe': timeframe,
                        'timestamp': datetime.now(UTC).isoformat()
                    })
                elif histogram < 0 and macd_line < signal_line:
                    events.append({
                        'type': 'BEARISH_MACD_CROSSOVER',
                        'value': histogram,
                        'message': f"MACD bearish crossover: MACD ({macd_line:.4f}) below Signal ({signal_line:.4f})",
                        'timeframe': timeframe,
                        'timestamp': datetime.now(UTC).isoformat()
                    })

            # Detect Bollinger Band breaks
            bb = indicators.get('bb', {})
            bb_upper = bb.get('upper')
            bb_lower = bb.get('lower')

            if bb_upper and bb_lower and current_price:
                if current_price > bb_upper:
                    events.append({
                        'type': 'UPPER_BB_BREAK',
                        'value': current_price,
                        'message': f"Price ({current_price:.2f}) broke above upper Bollinger Band ({bb_upper:.2f})",
                        'timeframe': timeframe,
                        'timestamp': datetime.now(UTC).isoformat()
                    })
                elif current_price < bb_lower:
                    events.append({
                        'type': 'LOWER_BB_BREAK',
                        'value': current_price,
                        'message': f"Price ({current_price:.2f}) broke below lower Bollinger Band ({bb_lower:.2f})",
                        'timeframe': timeframe,
                        'timestamp': datetime.now(UTC).isoformat()
                    })

        return events
    except Exception as e:
        print(f"Error in detect_market_events: {e}")
        return []


def generate_mock_market_data(symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
    """
    Generate mock market data for testing.

    Args:
        symbol: Trading symbol
        timeframe: Timeframe
        limit: Number of data points

    Returns:
        DataFrame with mock OHLCV data
    """
    try:
        if pd is None or np is None:
            return pd.DataFrame()

        # Generate dates
        timeframe_seconds = {
            '1m': 60, '5m': 300, '15m': 900, '30m': 1800,
            '1h': 3600, '4h': 14400, '1d': 86400
        }.get(timeframe, 3600)

        dates = pd.date_range(end=datetime.now(UTC), periods=limit, freq=f'{timeframe_seconds}S')

        # Generate price data with random walk
        base_price = 50000.0 if symbol == 'BTCUSDT' else 100.0
        prices = [base_price]

        for i in range(1, limit):
            change = np.random.normal(0, 0.01)
            prices.append(max(prices[-1] * (1 + change), base_price * 0.5))

        # Create DataFrame
        return pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, 0.005))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.005))) for p in prices],
            'close': prices,
            'volume': np.random.uniform(100, 1000, limit)
        })
    except Exception as e:
        print(f"Error generating mock market data: {e}")
        # Return empty DataFrame
        return pd.DataFrame()
