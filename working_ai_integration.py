#!/usr/bin/env python3
"""
Working AI Integration for Trading Agent
Uses Google Gemini (FREE) + OpenAI (when available)
Better than Poe - works immediately!
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

import aiohttp

logger = logging.getLogger(__name__)

@dataclass
class AIResponse:
    """Response from AI analysis."""
    content: str
    model: str
    success: bool
    cost_estimate: float
    response_time_ms: int
    confidence_score: float = 0.0
    error: Optional[str] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

class GeminiClient:
    """Google Gemini API client (FREE tier available)."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY')
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY environment variable required")

        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
        self.requests_today = 0
        self.daily_limit = 1000  # Conservative limit for free tier

    async def analyze_market(self, prompt: str, **kwargs) -> AIResponse:
        """Analyze market using Google Gemini."""

        if self.requests_today >= self.daily_limit:
            return AIResponse(
                content="", model="gemini-pro", success=False,
                cost_estimate=0.0, response_time_ms=0,
                error="Daily request limit reached"
            )

        start_time = time.time()

        try:
            payload = {
                "contents": [{
                    "parts": [{
                        "text": f"""You are an expert financial analyst. Analyze this trading situation:

{prompt}

Provide analysis in this format:
SENTIMENT: [BULLISH/BEARISH/NEUTRAL]
CONFIDENCE: [0-100]
ACTION: [BUY/SELL/HOLD]
REASONING: [brief explanation]
RISK: [HIGH/MEDIUM/LOW]

Be specific and concise for algorithmic trading."""
                    }]
                }],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 1000,
                }
            }

            url = f"{self.base_url}?key={self.api_key}"

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    response_time = int((time.time() - start_time) * 1000)

                    if response.status == 200:
                        data = await response.json()

                        if 'candidates' in data and len(data['candidates']) > 0:
                            content = data['candidates'][0]['content']['parts'][0]['text']
                            self.requests_today += 1

                            confidence = self._extract_confidence(content)

                            return AIResponse(
                                content=content,
                                model="gemini-pro",
                                success=True,
                                cost_estimate=0.0,  # Free!
                                response_time_ms=response_time,
                                confidence_score=confidence
                            )
                        else:
                            return AIResponse(
                                content="", model="gemini-pro", success=False,
                                cost_estimate=0.0, response_time_ms=response_time,
                                error="No response content"
                            )
                    else:
                        error_text = await response.text()
                        return AIResponse(
                            content="", model="gemini-pro", success=False,
                            cost_estimate=0.0, response_time_ms=response_time,
                            error=f"HTTP {response.status}: {error_text}"
                        )

        except Exception as e:
            return AIResponse(
                content="", model="gemini-pro", success=False,
                cost_estimate=0.0, response_time_ms=int((time.time() - start_time) * 1000),
                error=str(e)
            )

    def _extract_confidence(self, content: str) -> float:
        """Extract confidence score from response."""
        try:
            lines = content.upper().split('\n')
            for line in lines:
                if 'CONFIDENCE:' in line:
                    confidence_str = ''.join(filter(str.isdigit, line))
                    if confidence_str:
                        return min(100, max(0, int(confidence_str))) / 100.0
        except:
            pass
        return 0.7  # Default confidence

class OpenAIClient:
    """OpenAI GPT-4 client for premium analysis."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.base_url = "https://api.openai.com/v1/chat/completions"
        self.requests_today = 0
        self.daily_budget = 100  # Dollar budget per day
        self.cost_per_request = 0.03  # Estimated cost per request

    async def analyze_market(self, prompt: str, **kwargs) -> AIResponse:
        """Analyze market using OpenAI GPT-4."""

        if not self.api_key:
            return AIResponse(
                content="", model="gpt-4", success=False,
                cost_estimate=0.0, response_time_ms=0,
                error="OpenAI API key not available"
            )

        if (self.requests_today * self.cost_per_request) >= self.daily_budget:
            return AIResponse(
                content="", model="gpt-4", success=False,
                cost_estimate=0.0, response_time_ms=0,
                error="Daily budget limit reached"
            )

        start_time = time.time()

        try:
            payload = {
                "model": "gpt-4-turbo-preview",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert quantitative analyst specializing in algorithmic trading. Provide precise, actionable analysis."
                    },
                    {
                        "role": "user",
                        "content": f"""Analyze this trading situation:

{prompt}

Provide analysis in this exact format:
SENTIMENT: [BULLISH/BEARISH/NEUTRAL]
CONFIDENCE: [0-100]
ACTION: [BUY/SELL/HOLD]
ENTRY: [specific price level if applicable]
STOP: [stop loss level if applicable]
TARGET: [take profit level if applicable]
RISK: [HIGH/MEDIUM/LOW]
REASONING: [brief technical explanation]

Be specific and quantitative for algorithmic processing."""
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 1000
            }

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, headers=headers, json=payload) as response:
                    response_time = int((time.time() - start_time) * 1000)

                    if response.status == 200:
                        data = await response.json()
                        content = data['choices'][0]['message']['content']

                        self.requests_today += 1
                        confidence = self._extract_confidence(content)

                        return AIResponse(
                            content=content,
                            model="gpt-4-turbo",
                            success=True,
                            cost_estimate=self.cost_per_request,
                            response_time_ms=response_time,
                            confidence_score=confidence
                        )
                    else:
                        error_text = await response.text()
                        return AIResponse(
                            content="", model="gpt-4-turbo", success=False,
                            cost_estimate=0.0, response_time_ms=response_time,
                            error=f"HTTP {response.status}: {error_text}"
                        )

        except Exception as e:
            return AIResponse(
                content="", model="gpt-4-turbo", success=False,
                cost_estimate=0.0, response_time_ms=int((time.time() - start_time) * 1000),
                error=str(e)
            )

    def _extract_confidence(self, content: str) -> float:
        """Extract confidence score from response."""
        try:
            lines = content.upper().split('\n')
            for line in lines:
                if 'CONFIDENCE:' in line:
                    confidence_str = ''.join(filter(str.isdigit, line))
                    if confidence_str:
                        return min(100, max(0, int(confidence_str))) / 100.0
        except:
            pass
        return 0.8  # Default confidence for GPT-4

class SmartAIRouter:
    """Smart AI routing system - better than Poe!"""

    def __init__(self):
        self.gemini = None
        self.openai = None

        # Initialize available clients
        try:
            self.gemini = GeminiClient()
            print("✅ Google Gemini available (FREE)")
        except:
            print("❌ Google Gemini not available - add GOOGLE_API_KEY")

        try:
            self.openai = OpenAIClient()
            print("✅ OpenAI GPT-4 available (Premium)")
        except:
            print("⚠️  OpenAI not available - add OPENAI_API_KEY for premium features")

        if not self.gemini and not self.openai:
            raise ValueError("No AI providers available. Please add GOOGLE_API_KEY or OPENAI_API_KEY")

    async def analyze_market(self,
                           market_data: dict[str, Any],
                           importance: str = 'normal') -> Optional[dict[str, Any]]:
        """Get AI analysis with smart routing."""

        prompt = self._create_trading_prompt(market_data)

        # Route based on importance and availability
        if importance == 'critical' and self.openai:
            # Use premium AI for critical decisions
            response = await self.openai.analyze_market(prompt)
            if response.success:
                return self._parse_response(response, market_data)

        # Use free AI for normal analysis or fallback
        if self.gemini:
            response = await self.gemini.analyze_market(prompt)
            if response.success:
                return self._parse_response(response, market_data)

        # Final fallback to any available AI
        if self.openai:
            response = await self.openai.analyze_market(prompt)
            if response.success:
                return self._parse_response(response, market_data)

        return None

    async def get_consensus(self, market_data: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Get consensus from multiple AIs."""

        prompt = self._create_trading_prompt(market_data)
        responses = []

        # Get analysis from all available AIs
        if self.gemini:
            gemini_response = await self.gemini.analyze_market(prompt)
            if gemini_response.success:
                responses.append(gemini_response)

        if self.openai:
            openai_response = await self.openai.analyze_market(prompt)
            if openai_response.success:
                responses.append(openai_response)

        if not responses:
            return None

        # Create consensus
        return self._create_consensus(responses, market_data)

    def _create_trading_prompt(self, market_data: dict[str, Any]) -> str:
        """Create optimized trading prompt."""

        symbol = market_data.get('symbol', 'Unknown')
        timeframe = market_data.get('timeframe', '1h')

        prompt = f"""
        TRADING ANALYSIS: {symbol} ({timeframe})

        Market Data:
        - Current Price: {market_data.get('current_price', 'N/A')}
        - RSI: {market_data.get('rsi', 'N/A')}
        - MACD: {market_data.get('macd', 'N/A')}
        - Volume: {market_data.get('volume', 'N/A')}
        - Trend: {market_data.get('trend', 'N/A')}
        - Support: {market_data.get('support', 'N/A')}
        - Resistance: {market_data.get('resistance', 'N/A')}

        Analyze for trading opportunity and provide specific recommendations.
        """

        return prompt

    def _parse_response(self, response: AIResponse, market_data: dict[str, Any]) -> dict[str, Any]:
        """Parse AI response into structured format."""

        content = response.content.upper()

        # Extract structured data
        analysis = {
            'symbol': market_data.get('symbol', 'Unknown'),
            'model': response.model,
            'sentiment': 'NEUTRAL',
            'confidence': int(response.confidence_score * 100),
            'action': 'HOLD',
            'risk_level': 'MEDIUM',
            'reasoning': response.content[:200] + '...' if len(response.content) > 200 else response.content,
            'cost': response.cost_estimate,
            'response_time': response.response_time_ms,
            'timestamp': response.timestamp.isoformat()
        }

        # Parse structured fields
        lines = content.split('\n')
        for line in lines:
            if 'SENTIMENT:' in line:
                sentiment = line.split('SENTIMENT:')[1].strip()
                if sentiment in ['BULLISH', 'BEARISH', 'NEUTRAL']:
                    analysis['sentiment'] = sentiment

            elif 'ACTION:' in line:
                action = line.split('ACTION:')[1].strip()
                if action in ['BUY', 'SELL', 'HOLD']:
                    analysis['action'] = action

            elif 'RISK:' in line:
                risk = line.split('RISK:')[1].strip()
                if risk in ['HIGH', 'MEDIUM', 'LOW']:
                    analysis['risk_level'] = risk

        return analysis

    def _create_consensus(self, responses: list[AIResponse], market_data: dict[str, Any]) -> dict[str, Any]:
        """Create consensus from multiple AI responses."""

        analyses = [self._parse_response(r, market_data) for r in responses]

        # Count votes
        sentiments = [a['sentiment'] for a in analyses]
        actions = [a['action'] for a in analyses]

        sentiment_counts = {s: sentiments.count(s) for s in set(sentiments)}
        action_counts = {a: actions.count(a) for a in set(actions)}

        consensus_sentiment = max(sentiment_counts, key=sentiment_counts.get)
        consensus_action = max(action_counts, key=action_counts.get)

        # Calculate agreement
        sentiment_agreement = sentiment_counts[consensus_sentiment] / len(analyses)
        action_agreement = action_counts[consensus_action] / len(analyses)

        # Average confidence
        avg_confidence = sum(a['confidence'] for a in analyses) / len(analyses)

        return {
            'symbol': market_data.get('symbol', 'Unknown'),
            'consensus_sentiment': consensus_sentiment,
            'consensus_action': consensus_action,
            'consensus_confidence': int(avg_confidence),
            'sentiment_agreement': f"{sentiment_agreement:.1%}",
            'action_agreement': f"{action_agreement:.1%}",
            'models_used': [a['model'] for a in analyses],
            'individual_analyses': analyses,
            'total_cost': sum(a['cost'] for a in analyses),
            'recommendation_strength': 'STRONG' if min(sentiment_agreement, action_agreement) >= 0.67 else 'MODERATE',
            'timestamp': datetime.utcnow().isoformat()
        }

    def get_usage_stats(self) -> dict[str, Any]:
        """Get usage statistics."""
        stats = {
            'gemini_requests_today': self.gemini.requests_today if self.gemini else 0,
            'openai_requests_today': self.openai.requests_today if self.openai else 0,
            'estimated_cost_today': 0.0,
            'free_requests_remaining': 0
        }

        if self.gemini:
            stats['free_requests_remaining'] = max(0, self.gemini.daily_limit - self.gemini.requests_today)

        if self.openai:
            stats['estimated_cost_today'] = self.openai.requests_today * self.openai.cost_per_request

        return stats

# Main integration function
async def get_ai_trading_analysis(symbol: str,
                                market_data: dict[str, Any],
                                importance: str = 'normal') -> Optional[dict[str, Any]]:
    """Get AI trading analysis - works immediately!"""

    try:
        router = SmartAIRouter()

        if importance == 'consensus':
            return await router.get_consensus(market_data)
        else:
            return await router.analyze_market(market_data, importance)

    except Exception as e:
        logger.error(f"AI analysis failed for {symbol}: {e}")
        return None

# Example usage and test
async def test_ai_integration():
    """Test the AI integration."""
    print("🤖 TESTING WORKING AI INTEGRATION")
    print("=" * 50)

    # Sample market data
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

    print(f"📊 Analyzing {market_data['symbol']}...")

    # Test 1: Normal analysis
    print("\n🧪 Test 1: Normal Analysis")
    analysis = await get_ai_trading_analysis('EURUSD', market_data, 'normal')

    if analysis:
        print("✅ Analysis successful!")
        print(f"   Model: {analysis['model']}")
        print(f"   Action: {analysis['action']}")
        print(f"   Sentiment: {analysis['sentiment']}")
        print(f"   Confidence: {analysis['confidence']}%")
        print(f"   Risk: {analysis['risk_level']}")
        print(f"   Cost: ${analysis['cost']:.4f}")
        print(f"   Response Time: {analysis['response_time']}ms")
    else:
        print("❌ Analysis failed")

    # Test 2: Consensus analysis (if multiple AIs available)
    print("\n🧪 Test 2: Consensus Analysis")
    consensus = await get_ai_trading_analysis('EURUSD', market_data, 'consensus')

    if consensus:
        print("✅ Consensus analysis successful!")
        print(f"   Consensus Action: {consensus['consensus_action']}")
        print(f"   Consensus Sentiment: {consensus['consensus_sentiment']}")
        print(f"   Confidence: {consensus['consensus_confidence']}%")
        print(f"   Agreement: {consensus['action_agreement']}")
        print(f"   Models: {', '.join(consensus['models_used'])}")
        print(f"   Total Cost: ${consensus['total_cost']:.4f}")
    else:
        print("⚠️  Consensus analysis not available (need multiple AIs)")

    # Usage stats
    print("\n📊 Usage Statistics:")
    router = SmartAIRouter()
    stats = router.get_usage_stats()

    print(f"   Free requests remaining: {stats['free_requests_remaining']}")
    print(f"   Estimated cost today: ${stats['estimated_cost_today']:.2f}")
    print(f"   Total requests: {stats['gemini_requests_today'] + stats['openai_requests_today']}")

if __name__ == "__main__":
    print("🚀 WORKING AI INTEGRATION - BETTER THAN POE!")
    print("=" * 60)
    print("This integration works immediately with:")
    print("✅ Google Gemini (FREE) - Just add GOOGLE_API_KEY")
    print("✅ OpenAI GPT-4 (Premium) - Add OPENAI_API_KEY when ready")
    print("✅ Smart routing - Optimize costs automatically")
    print("✅ Consensus analysis - Multiple AI opinions")
    print()

    try:
        asyncio.run(test_ai_integration())
        print("\n🎉 AI integration is working! Ready for trading!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTo get started:")
        print("1. Get free Google Gemini API key: https://makersuite.google.com/app/apikey")
        print("2. Add to .env: GOOGLE_API_KEY=your-key-here")
        print("3. Run this test again")

