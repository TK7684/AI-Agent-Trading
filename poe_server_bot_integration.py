#!/usr/bin/env python3
"""
Poe Server Bot Integration for AI Trading Agent
Based on the official Poe Creator API documentation
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

import aiohttp

logger = logging.getLogger(__name__)

# Your Poe API key for server bot access
POE_API_KEY = "YtE8ejRowwXJI4O1h.wTLBfVWZDzyRXByhei3tWXaqs-1758274795-1.0.1.1-JT23ROAcW9m81vcLzW9Ft9z80QUV7otJzKot1_iFDkMiThFgMUnkY1z80QUV7otJzKot1_iFDkMiThFgMUnkY1zCxd3z5ByIEkUQG4VvF3UOyalwGf0UiaBhZvmyKlyXSGfGDcSGvCA"

@dataclass
class PoeServerResponse:
    """Response from Poe Server Bot."""
    content: str
    model: str
    success: bool
    response_time_ms: int
    confidence_score: float = 0.0
    error: Optional[str] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

class PoeServerBotClient:
    """Client for interacting with Poe server bots."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or POE_API_KEY
        if not self.api_key:
            raise ValueError("Poe API key required")

        # Based on Poe documentation - these are the available bots
        self.available_bots = {
            'claude_3_5_sonnet': 'Claude-3.5-Sonnet',
            'gpt4_turbo': 'GPT-4-Turbo',
            'gpt4o': 'GPT-4o',
            'gemini_pro': 'Gemini-Pro',
            'claude_3_opus': 'Claude-3-Opus',
            'llama_3_70b': 'Llama-3-70B-Instruct'
        }

        self.base_url = "https://api.poe.com"
        self.requests_today = 0

    async def query_bot(self,
                       bot_name: str,
                       query: str,
                       conversation_id: Optional[str] = None) -> PoeServerResponse:
        """Query a specific bot on Poe."""

        start_time = time.time()

        try:
            # Poe server bot query format based on documentation
            payload = {
                "version": 1,
                "type": "query",
                "query": [
                    {
                        "role": "user",
                        "content": query,
                        "content_type": "text/markdown"
                    }
                ],
                "user_id": "trading_agent",
                "conversation_id": conversation_id or f"trading_session_{int(time.time())}",
                "message_id": f"msg_{int(time.time() * 1000)}"
            }

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "AI-Trading-Agent/1.0"
            }

            # Try different endpoint patterns based on documentation
            endpoints_to_try = [
                f"{self.base_url}/bot/{bot_name}",
                f"{self.base_url}/v1/bot/{bot_name}",
                f"{self.base_url}/bots/{bot_name}/query",
                f"{self.base_url}/query/{bot_name}"
            ]

            async with aiohttp.ClientSession() as session:
                for endpoint in endpoints_to_try:
                    try:
                        async with session.post(
                            endpoint,
                            headers=headers,
                            json=payload,
                            timeout=aiohttp.ClientTimeout(total=30)
                        ) as response:

                            response_time = int((time.time() - start_time) * 1000)

                            if response.status == 200:
                                data = await response.json()

                                # Extract content based on Poe response format
                                content = self._extract_content(data)
                                confidence = self._calculate_confidence(content)

                                self.requests_today += 1

                                return PoeServerResponse(
                                    content=content,
                                    model=bot_name,
                                    success=True,
                                    response_time_ms=response_time,
                                    confidence_score=confidence
                                )

                            elif response.status == 401:
                                error_text = await response.text()
                                return PoeServerResponse(
                                    content="", model=bot_name, success=False,
                                    response_time_ms=response_time,
                                    error=f"Authentication failed: {error_text[:200]}..."
                                )

                            elif response.status == 403:
                                return PoeServerResponse(
                                    content="", model=bot_name, success=False,
                                    response_time_ms=response_time,
                                    error="Access forbidden - check bot permissions"
                                )

                    except Exception as e:
                        logger.debug(f"Endpoint {endpoint} failed: {e}")
                        continue

                # If all endpoints failed
                return PoeServerResponse(
                    content="", model=bot_name, success=False,
                    response_time_ms=int((time.time() - start_time) * 1000),
                    error="All endpoints failed - API format may have changed"
                )

        except Exception as e:
            return PoeServerResponse(
                content="", model=bot_name, success=False,
                response_time_ms=int((time.time() - start_time) * 1000),
                error=str(e)
            )

    def _extract_content(self, data: dict[str, Any]) -> str:
        """Extract content from Poe response."""

        # Try different response formats
        if isinstance(data, dict):
            # Standard response format
            if 'text' in data:
                return data['text']
            elif 'content' in data:
                return data['content']
            elif 'response' in data:
                return data['response']
            elif 'message' in data:
                return data['message']
            # Streaming response format
            elif 'choices' in data and len(data['choices']) > 0:
                choice = data['choices'][0]
                if 'text' in choice:
                    return choice['text']
                elif 'message' in choice and 'content' in choice['message']:
                    return choice['message']['content']

        # If we can't parse it, return the raw data as string
        return str(data)[:500] + "..." if len(str(data)) > 500 else str(data)

    def _calculate_confidence(self, content: str) -> float:
        """Calculate confidence based on response quality."""
        if not content or len(content) < 10:
            return 0.1

        # Look for confidence indicators in the response
        content_lower = content.lower()

        confidence = 0.7  # Base confidence

        # Positive indicators
        if any(word in content_lower for word in ['confident', 'certain', 'clear', 'strong']):
            confidence += 0.1

        # Negative indicators
        if any(word in content_lower for word in ['uncertain', 'maybe', 'possibly', 'unclear']):
            confidence -= 0.1

        # Length consideration
        if 50 <= len(content) <= 1000:
            confidence += 0.05

        return max(0.1, min(1.0, confidence))

class PoeMultiBotAnalyzer:
    """Multi-bot analysis using Poe server bots."""

    def __init__(self, api_key: str = None):
        self.client = PoeServerBotClient(api_key)

        # Preferred bots for different types of analysis
        self.trading_bots = {
            'primary': 'Claude-3.5-Sonnet',      # Best reasoning
            'secondary': 'GPT-4-Turbo',          # Good patterns
            'alternative': 'Gemini-Pro',         # Different perspective
            'fast': 'Llama-3-70B-Instruct'       # Quick analysis
        }

    async def analyze_market(self,
                           market_data: dict[str, Any],
                           analysis_type: str = 'comprehensive') -> Optional[dict[str, Any]]:
        """Analyze market using Poe server bots."""

        prompt = self._create_trading_prompt(market_data)

        if analysis_type == 'quick':
            # Use single fast bot
            bot = self.trading_bots['fast']
            response = await self.client.query_bot(bot, prompt)

            if response.success:
                return self._parse_response(response, market_data)

        elif analysis_type == 'comprehensive':
            # Use multiple bots for consensus
            return await self._get_consensus_analysis(market_data, prompt)

        else:
            # Use primary bot
            bot = self.trading_bots['primary']
            response = await self.client.query_bot(bot, prompt)

            if response.success:
                return self._parse_response(response, market_data)

        return None

    async def _get_consensus_analysis(self,
                                    market_data: dict[str, Any],
                                    prompt: str) -> Optional[dict[str, Any]]:
        """Get consensus from multiple bots."""

        bots_to_use = [
            self.trading_bots['primary'],
            self.trading_bots['secondary'],
            self.trading_bots['alternative']
        ]

        # Query multiple bots in parallel
        tasks = []
        for bot in bots_to_use:
            task = self.client.query_bot(bot, prompt)
            tasks.append(task)

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Process successful responses
        successful_analyses = []
        for i, response in enumerate(responses):
            if isinstance(response, PoeServerResponse) and response.success:
                analysis = self._parse_response(response, market_data)
                if analysis:
                    analysis['source_bot'] = bots_to_use[i]
                    successful_analyses.append(analysis)

        if not successful_analyses:
            return None

        # Create consensus
        return self._create_consensus(successful_analyses, market_data)

    def _create_trading_prompt(self, market_data: dict[str, Any]) -> str:
        """Create optimized trading prompt."""

        symbol = market_data.get('symbol', 'Unknown')
        timeframe = market_data.get('timeframe', '1h')

        prompt = f"""
        **TRADING ANALYSIS REQUEST**

        Symbol: {symbol}
        Timeframe: {timeframe}

        **Market Data:**
        - Current Price: {market_data.get('current_price', 'N/A')}
        - RSI: {market_data.get('rsi', 'N/A')}
        - MACD: {market_data.get('macd', 'N/A')}
        - Volume: {market_data.get('volume', 'N/A')}
        - Trend: {market_data.get('trend', 'N/A')}
        - Support: {market_data.get('support', 'N/A')}
        - Resistance: {market_data.get('resistance', 'N/A')}

        **Required Analysis Format:**
        Please provide your analysis in this exact structure:

        **SENTIMENT:** [BULLISH/BEARISH/NEUTRAL]
        **CONFIDENCE:** [0-100]
        **ACTION:** [BUY/SELL/HOLD]
        **ENTRY:** [specific price level]
        **STOP_LOSS:** [stop loss level]
        **TARGET:** [take profit level]
        **RISK:** [HIGH/MEDIUM/LOW]
        **TIMEFRAME:** [SHORT/MEDIUM/LONG]
        **REASONING:** [brief technical explanation]

        Focus on actionable insights for algorithmic trading. Be specific with price levels and risk assessment.
        """

        return prompt

    def _parse_response(self, response: PoeServerResponse, market_data: dict[str, Any]) -> dict[str, Any]:
        """Parse bot response into structured format."""

        content = response.content.upper()

        analysis = {
            'symbol': market_data.get('symbol', 'Unknown'),
            'model': response.model,
            'sentiment': 'NEUTRAL',
            'confidence': int(response.confidence_score * 100),
            'action': 'HOLD',
            'entry_price': None,
            'stop_loss': None,
            'target_price': None,
            'risk_level': 'MEDIUM',
            'timeframe': 'MEDIUM',
            'reasoning': response.content[:300] + '...' if len(response.content) > 300 else response.content,
            'response_time': response.response_time_ms,
            'timestamp': response.timestamp.isoformat()
        }

        # Parse structured fields
        lines = content.split('\n')
        for line in lines:
            line = line.strip()

            if 'SENTIMENT:' in line:
                sentiment = line.split('SENTIMENT:')[1].strip()
                if sentiment in ['BULLISH', 'BEARISH', 'NEUTRAL']:
                    analysis['sentiment'] = sentiment

            elif 'CONFIDENCE:' in line:
                try:
                    confidence_str = ''.join(filter(str.isdigit, line))
                    if confidence_str:
                        analysis['confidence'] = min(100, max(0, int(confidence_str)))
                except:
                    pass

            elif 'ACTION:' in line:
                action = line.split('ACTION:')[1].strip()
                if action in ['BUY', 'SELL', 'HOLD']:
                    analysis['action'] = action

            elif 'RISK:' in line:
                risk = line.split('RISK:')[1].strip()
                if risk in ['HIGH', 'MEDIUM', 'LOW']:
                    analysis['risk_level'] = risk

            elif 'ENTRY:' in line:
                try:
                    entry_str = line.split('ENTRY:')[1].strip()
                    # Extract numeric value
                    entry_price = float(''.join(c for c in entry_str if c.isdigit() or c == '.'))
                    analysis['entry_price'] = entry_price
                except:
                    pass

        return analysis

    def _create_consensus(self, analyses: list[dict[str, Any]], market_data: dict[str, Any]) -> dict[str, Any]:
        """Create consensus from multiple analyses."""

        if not analyses:
            return None

        # Count votes
        sentiments = [a['sentiment'] for a in analyses]
        actions = [a['action'] for a in analyses]

        sentiment_counts = {s: sentiments.count(s) for s in set(sentiments)}
        action_counts = {a: actions.count(a) for a in set(actions)}

        consensus_sentiment = max(sentiment_counts, key=sentiment_counts.get)
        consensus_action = max(action_counts, key=action_counts.get)

        # Calculate agreement levels
        sentiment_agreement = sentiment_counts[consensus_sentiment] / len(analyses)
        action_agreement = action_counts[consensus_action] / len(analyses)

        # Average confidence
        avg_confidence = sum(a['confidence'] for a in analyses) / len(analyses)

        # Average response time
        avg_response_time = sum(a['response_time'] for a in analyses) / len(analyses)

        return {
            'symbol': market_data.get('symbol', 'Unknown'),
            'consensus_sentiment': consensus_sentiment,
            'consensus_action': consensus_action,
            'consensus_confidence': int(avg_confidence),
            'sentiment_agreement': f"{sentiment_agreement:.1%}",
            'action_agreement': f"{action_agreement:.1%}",
            'models_used': [a['model'] for a in analyses],
            'source_bots': [a.get('source_bot', 'unknown') for a in analyses],
            'individual_analyses': analyses,
            'average_response_time': int(avg_response_time),
            'recommendation_strength': 'STRONG' if min(sentiment_agreement, action_agreement) >= 0.67 else 'MODERATE',
            'timestamp': datetime.utcnow().isoformat()
        }

# Main integration function
async def get_poe_trading_analysis(symbol: str,
                                 market_data: dict[str, Any],
                                 analysis_type: str = 'normal') -> Optional[dict[str, Any]]:
    """Get trading analysis using Poe server bots."""

    try:
        analyzer = PoeMultiBotAnalyzer()

        if analysis_type == 'consensus':
            return await analyzer.analyze_market(market_data, 'comprehensive')
        else:
            return await analyzer.analyze_market(market_data, analysis_type)

    except Exception as e:
        logger.error(f"Poe analysis failed for {symbol}: {e}")
        return None

# Test the integration
async def test_poe_server_integration():
    """Test Poe server bot integration."""
    print("🤖 TESTING POE SERVER BOT INTEGRATION")
    print("=" * 50)

    # Test market data
    market_data = {
        'symbol': 'EURUSD',
        'timeframe': '1h',
        'current_price': 1.0875,
        'rsi': 45.2,
        'macd': 'bullish_crossover',
        'volume': 'above_average',
        'trend': 'upward',
        'support': 1.0850,
        'resistance': 1.0920
    }

    print(f"📊 Testing analysis for {market_data['symbol']}...")

    # Test 1: Quick analysis
    print("\n🧪 Test 1: Quick Analysis")
    analysis = await get_poe_trading_analysis('EURUSD', market_data, 'quick')

    if analysis:
        print("✅ Quick analysis successful!")
        print(f"   Model: {analysis['model']}")
        print(f"   Action: {analysis['action']}")
        print(f"   Sentiment: {analysis['sentiment']}")
        print(f"   Confidence: {analysis['confidence']}%")
        print(f"   Risk: {analysis['risk_level']}")
        print(f"   Response Time: {analysis['response_time']}ms")
    else:
        print("❌ Quick analysis failed")

    # Test 2: Consensus analysis
    print("\n🧪 Test 2: Consensus Analysis")
    consensus = await get_poe_trading_analysis('EURUSD', market_data, 'consensus')

    if consensus:
        print("✅ Consensus analysis successful!")
        print(f"   Consensus Action: {consensus['consensus_action']}")
        print(f"   Consensus Sentiment: {consensus['consensus_sentiment']}")
        print(f"   Confidence: {consensus['consensus_confidence']}%")
        print(f"   Agreement: {consensus['action_agreement']}")
        print(f"   Bots Used: {', '.join(consensus['source_bots'])}")
        print(f"   Avg Response Time: {consensus['average_response_time']}ms")
    else:
        print("❌ Consensus analysis failed")

    print(f"\n📊 Total requests made: {PoeServerBotClient(POE_API_KEY).requests_today}")

if __name__ == "__main__":
    print("🚀 POE SERVER BOT INTEGRATION TEST")
    print("=" * 60)
    print("Testing with your Poe server bot API key...")
    print(f"Key: {POE_API_KEY[:30]}...{POE_API_KEY[-20:]}")
    print()

    try:
        asyncio.run(test_poe_server_integration())
        print("\n🎉 Poe server bot integration test completed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        print("\nNext steps:")
        print("1. Verify your Poe server bot is properly configured")
        print("2. Check API key permissions")
        print("3. Review Poe Creator documentation for updates")

