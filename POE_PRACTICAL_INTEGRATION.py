"""
Practical Poe Integration for AI Trading Agent
Based on Poe Subscriptions FAQ and best practices
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional

import aiohttp

logger = logging.getLogger(__name__)

class PoeModel(Enum):
    """Available Poe AI models optimized for trading analysis."""
    # Premium models available through Poe subscription
    CLAUDE_3_5_SONNET = "Claude-3.5-Sonnet"      # Best for market analysis
    GPT_4_TURBO = "GPT-4-Turbo"                  # Excellent for patterns
    GPT_4O = "GPT-4o"                            # Latest OpenAI model
    O1_PREVIEW = "o1-preview"                    # Advanced reasoning
    GEMINI_PRO = "Gemini-Pro"                    # Google's model
    CLAUDE_3_OPUS = "Claude-3-Opus"             # Most capable Claude
    LLAMA_3_70B = "Llama-3-70B-Instruct"        # Meta's model

    # Specialized models for specific tasks
    FAST_ANALYSIS = "Claude-3-Haiku"            # Quick analysis
    COST_EFFECTIVE = "Llama-3-8B-Instruct"     # Budget option

@dataclass
class PoeUsageStats:
    """Track Poe compute points usage."""
    points_used_today: int = 0
    points_remaining: int = 0
    daily_limit: int = 0
    reset_time: Optional[datetime] = None
    cost_per_point: float = 0.0001  # Estimated cost per point

@dataclass
class PoeResponse:
    """Enhanced response from Poe API with usage tracking."""
    content: str
    model: str
    success: bool
    points_used: int
    response_time_ms: int
    confidence_score: float = 0.0
    error: Optional[str] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

class PoePointsManager:
    """Manage Poe compute points efficiently."""

    def __init__(self):
        self.usage_stats = PoeUsageStats()
        self.model_costs = {
            # Estimated points per request based on model complexity
            PoeModel.O1_PREVIEW: 100,           # Most expensive
            PoeModel.CLAUDE_3_OPUS: 50,
            PoeModel.GPT_4_TURBO: 40,
            PoeModel.CLAUDE_3_5_SONNET: 30,
            PoeModel.GPT_4O: 35,
            PoeModel.GEMINI_PRO: 25,
            PoeModel.LLAMA_3_70B: 20,
            PoeModel.FAST_ANALYSIS: 10,         # Cheapest
            PoeModel.COST_EFFECTIVE: 8,
        }

    def estimate_cost(self, model: PoeModel, requests: int = 1) -> int:
        """Estimate points cost for requests."""
        return self.model_costs.get(model, 30) * requests

    def can_afford(self, model: PoeModel, requests: int = 1) -> bool:
        """Check if we have enough points for the request."""
        estimated_cost = self.estimate_cost(model, requests)
        return self.usage_stats.points_remaining >= estimated_cost

    def suggest_model(self, preferred_model: PoeModel) -> PoeModel:
        """Suggest alternative model if preferred is too expensive."""
        if self.can_afford(preferred_model):
            return preferred_model

        # Fallback hierarchy based on remaining points
        remaining = self.usage_stats.points_remaining

        if remaining >= 50:
            return PoeModel.CLAUDE_3_5_SONNET
        elif remaining >= 30:
            return PoeModel.GEMINI_PRO
        elif remaining >= 20:
            return PoeModel.LLAMA_3_70B
        elif remaining >= 10:
            return PoeModel.FAST_ANALYSIS
        else:
            return PoeModel.COST_EFFECTIVE

    def update_usage(self, points_used: int):
        """Update usage statistics."""
        self.usage_stats.points_used_today += points_used
        self.usage_stats.points_remaining -= points_used

class PoeAIClient:
    """Production-ready Poe API client for trading."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('POE_API_KEY')
        if not self.api_key:
            raise ValueError("POE_API_KEY environment variable required")

        self.base_url = "https://api.poe.com/bot"
        self.session: Optional[aiohttp.ClientSession] = None
        self.points_manager = PoePointsManager()
        self.request_history: list[PoeResponse] = []

        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Minimum seconds between requests

    async def __aenter__(self):
        """Async context manager entry."""
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
        timeout = aiohttp.ClientTimeout(total=30, connect=10)

        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "AI-Trading-Agent/1.0"
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def _rate_limit(self):
        """Implement rate limiting."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - time_since_last)

        self.last_request_time = time.time()

    async def analyze_market(self,
                           prompt: str,
                           model: PoeModel = PoeModel.CLAUDE_3_5_SONNET,
                           max_tokens: int = 1000,
                           temperature: float = 0.1) -> PoeResponse:
        """Analyze market using Poe AI model with optimization."""

        # Rate limiting
        await self._rate_limit()

        # Points management
        suggested_model = self.points_manager.suggest_model(model)
        if suggested_model != model:
            logger.info(f"Switching from {model.value} to {suggested_model.value} due to points limit")
            model = suggested_model

        start_time = time.time()

        try:
            # Poe API request format (based on their documentation)
            payload = {
                "version": "1.0",
                "type": "query",
                "query": [
                    {
                        "role": "system",
                        "content": "You are an expert financial analyst specializing in algorithmic trading. Provide concise, actionable analysis."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "model": model.value,
                "temperature": temperature,
                "max_tokens": max_tokens
            }

            async with self.session.post(f"{self.base_url}/chat", json=payload) as response:
                response_time = int((time.time() - start_time) * 1000)

                if response.status == 200:
                    data = await response.json()

                    # Extract response content
                    content = data.get("text", "")
                    points_used = data.get("compute_points_used", self.points_manager.estimate_cost(model))

                    # Update usage tracking
                    self.points_manager.update_usage(points_used)

                    # Calculate confidence based on response quality
                    confidence = self._calculate_confidence(content, model)

                    poe_response = PoeResponse(
                        content=content,
                        model=model.value,
                        success=True,
                        points_used=points_used,
                        response_time_ms=response_time,
                        confidence_score=confidence
                    )

                    # Store for analytics
                    self.request_history.append(poe_response)

                    logger.info(f"Poe analysis: {model.value}, {points_used} points, {response_time}ms")
                    return poe_response

                else:
                    error_text = await response.text()
                    logger.error(f"Poe API error {response.status}: {error_text}")

                    return PoeResponse(
                        content="",
                        model=model.value,
                        success=False,
                        points_used=0,
                        response_time_ms=response_time,
                        error=f"HTTP {response.status}: {error_text}"
                    )

        except asyncio.TimeoutError:
            logger.error("Poe API timeout")
            return PoeResponse(
                content="",
                model=model.value,
                success=False,
                points_used=0,
                response_time_ms=int((time.time() - start_time) * 1000),
                error="Request timeout"
            )

        except Exception as e:
            logger.error(f"Poe API error: {e}")
            return PoeResponse(
                content="",
                model=model.value,
                success=False,
                points_used=0,
                response_time_ms=int((time.time() - start_time) * 1000),
                error=str(e)
            )

    def _calculate_confidence(self, content: str, model: PoeModel) -> float:
        """Calculate confidence score based on response quality."""
        if not content:
            return 0.0

        # Base confidence by model capability
        model_confidence = {
            PoeModel.O1_PREVIEW: 0.95,
            PoeModel.CLAUDE_3_OPUS: 0.90,
            PoeModel.CLAUDE_3_5_SONNET: 0.88,
            PoeModel.GPT_4_TURBO: 0.85,
            PoeModel.GPT_4O: 0.87,
            PoeModel.GEMINI_PRO: 0.80,
            PoeModel.LLAMA_3_70B: 0.75,
            PoeModel.FAST_ANALYSIS: 0.70,
            PoeModel.COST_EFFECTIVE: 0.65,
        }.get(model, 0.70)

        # Adjust based on response characteristics
        content_lower = content.lower()

        # Positive indicators
        if any(word in content_lower for word in ['confident', 'strong', 'clear', 'definitive']):
            model_confidence += 0.05

        # Negative indicators
        if any(word in content_lower for word in ['uncertain', 'unclear', 'maybe', 'possibly']):
            model_confidence -= 0.05

        # Length consideration (too short or too long might indicate issues)
        if 100 <= len(content) <= 1000:
            model_confidence += 0.02

        return max(0.0, min(1.0, model_confidence))

    def get_usage_summary(self) -> dict[str, Any]:
        """Get usage summary for monitoring."""
        recent_requests = [r for r in self.request_history if
                          (datetime.utcnow() - r.timestamp).total_seconds() < 3600]

        return {
            'points_used_today': self.points_manager.usage_stats.points_used_today,
            'points_remaining': self.points_manager.usage_stats.points_remaining,
            'requests_last_hour': len(recent_requests),
            'average_response_time': sum(r.response_time_ms for r in recent_requests) / max(len(recent_requests), 1),
            'success_rate': sum(1 for r in recent_requests if r.success) / max(len(recent_requests), 1),
            'total_requests_today': len(self.request_history)
        }

class PoeMultiModelConsensus:
    """Get consensus from multiple Poe models for critical decisions."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key

        # Model selection strategy for consensus
        self.consensus_models = [
            PoeModel.CLAUDE_3_5_SONNET,  # Best reasoning
            PoeModel.GPT_4_TURBO,        # Good patterns
            PoeModel.GEMINI_PRO          # Alternative view
        ]

        # Fast analysis for quick decisions
        self.fast_models = [
            PoeModel.FAST_ANALYSIS,
            PoeModel.COST_EFFECTIVE
        ]

    async def get_trading_consensus(self,
                                  market_data: dict[str, Any],
                                  analysis_type: str = "full") -> dict[str, Any]:
        """Get consensus analysis for trading decisions."""

        models = self.fast_models if analysis_type == "quick" else self.consensus_models
        prompt = self._create_trading_prompt(market_data)

        async with PoeAIClient(self.api_key) as client:
            # Get analyses from multiple models
            tasks = []
            for model in models:
                if client.points_manager.can_afford(model):
                    task = client.analyze_market(prompt, model)
                    tasks.append(task)

            if not tasks:
                logger.warning("No models available due to points limit")
                return self._create_fallback_analysis()

            responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Process responses
        successful_analyses = []
        total_points = 0

        for i, response in enumerate(responses):
            if isinstance(response, PoeResponse) and response.success:
                analysis = self._parse_trading_response(response.content)
                analysis.update({
                    'model': response.model,
                    'confidence': response.confidence_score,
                    'points_used': response.points_used,
                    'response_time': response.response_time_ms
                })
                successful_analyses.append(analysis)
                total_points += response.points_used

        if not successful_analyses:
            logger.error("All model analyses failed")
            return self._create_fallback_analysis()

        # Generate consensus
        consensus = self._generate_consensus(successful_analyses)
        consensus.update({
            'total_points_used': total_points,
            'models_consulted': len(successful_analyses),
            'analysis_type': analysis_type,
            'timestamp': datetime.utcnow().isoformat()
        })

        return consensus

    def _create_trading_prompt(self, market_data: dict[str, Any]) -> str:
        """Create optimized prompt for trading analysis."""

        symbol = market_data.get('symbol', 'Unknown')
        timeframe = market_data.get('timeframe', '1h')

        prompt = f"""
        TRADING ANALYSIS REQUEST
        Symbol: {symbol} | Timeframe: {timeframe}

        Market Data:
        - Price: {market_data.get('current_price', 'N/A')}
        - RSI: {market_data.get('rsi', 'N/A')}
        - MACD: {market_data.get('macd', 'N/A')}
        - Volume: {market_data.get('volume', 'N/A')}
        - Trend: {market_data.get('trend', 'N/A')}

        Provide analysis in this exact format:
        SENTIMENT: [BULLISH/BEARISH/NEUTRAL]
        CONFIDENCE: [0-100]
        ACTION: [BUY/SELL/HOLD]
        ENTRY: [price level]
        STOP: [stop loss level]
        TARGET: [take profit level]
        RISK: [HIGH/MEDIUM/LOW]
        TIMEFRAME: [SHORT/MEDIUM/LONG]
        REASONING: [brief explanation]

        Be specific and concise for algorithmic processing.
        """

        return prompt

    def _parse_trading_response(self, content: str) -> dict[str, Any]:
        """Parse structured trading response."""

        analysis = {
            'sentiment': 'NEUTRAL',
            'confidence': 50,
            'action': 'HOLD',
            'entry_price': None,
            'stop_loss': None,
            'take_profit': None,
            'risk_level': 'MEDIUM',
            'timeframe': 'MEDIUM',
            'reasoning': content[:200] + '...' if len(content) > 200 else content
        }

        lines = content.upper().split('\n')
        for line in lines:
            if 'SENTIMENT:' in line:
                sentiment = line.split('SENTIMENT:')[1].strip()
                if sentiment in ['BULLISH', 'BEARISH', 'NEUTRAL']:
                    analysis['sentiment'] = sentiment

            elif 'CONFIDENCE:' in line:
                try:
                    confidence = int(''.join(filter(str.isdigit, line)))
                    if 0 <= confidence <= 100:
                        analysis['confidence'] = confidence
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

        return analysis

    def _generate_consensus(self, analyses: list[dict[str, Any]]) -> dict[str, Any]:
        """Generate consensus from multiple analyses."""

        if not analyses:
            return self._create_fallback_analysis()

        # Weighted voting based on model confidence
        sentiments = []
        actions = []
        confidences = []
        weights = []

        for analysis in analyses:
            sentiments.append(analysis['sentiment'])
            actions.append(analysis['action'])
            confidences.append(analysis['confidence'])
            weights.append(analysis['confidence'] / 100.0)  # Use confidence as weight

        # Weighted consensus
        def weighted_majority(items, weights):
            counts = {}
            for item, weight in zip(items, weights, strict=False):
                counts[item] = counts.get(item, 0) + weight
            return max(counts, key=counts.get)

        consensus_sentiment = weighted_majority(sentiments, weights)
        consensus_action = weighted_majority(actions, weights)
        consensus_confidence = sum(c * w for c, w in zip(confidences, weights, strict=False)) / sum(weights)

        # Agreement level
        sentiment_agreement = sentiments.count(consensus_sentiment) / len(sentiments)
        action_agreement = actions.count(consensus_action) / len(actions)

        return {
            'consensus_sentiment': consensus_sentiment,
            'consensus_action': consensus_action,
            'consensus_confidence': int(consensus_confidence),
            'sentiment_agreement': f"{sentiment_agreement:.1%}",
            'action_agreement': f"{action_agreement:.1%}",
            'model_analyses': analyses,
            'recommendation_strength': 'STRONG' if min(sentiment_agreement, action_agreement) >= 0.67 else 'MODERATE',
            'reasoning': f"Consensus from {len(analyses)} models with {min(sentiment_agreement, action_agreement):.1%} agreement"
        }

    def _create_fallback_analysis(self) -> dict[str, Any]:
        """Create fallback analysis when models fail."""
        return {
            'consensus_sentiment': 'NEUTRAL',
            'consensus_action': 'HOLD',
            'consensus_confidence': 0,
            'sentiment_agreement': '0%',
            'action_agreement': '0%',
            'model_analyses': [],
            'recommendation_strength': 'WEAK',
            'reasoning': 'Fallback analysis - insufficient model responses',
            'total_points_used': 0,
            'models_consulted': 0
        }

# Integration with existing trading system
async def get_poe_trading_analysis(symbol: str,
                                 market_data: dict[str, Any],
                                 analysis_type: str = "full") -> Optional[dict[str, Any]]:
    """Main function to get Poe analysis for trading system."""

    try:
        consensus = PoeMultiModelConsensus()
        analysis = await consensus.get_trading_consensus(market_data, analysis_type)

        logger.info(f"Poe analysis for {symbol}: {analysis['consensus_action']} "
                   f"(Confidence: {analysis['consensus_confidence']}%, "
                   f"Points: {analysis['total_points_used']}, "
                   f"Models: {analysis['models_consulted']})")

        return analysis

    except Exception as e:
        logger.error(f"Poe analysis failed for {symbol}: {e}")
        return None

# Usage monitoring and optimization
class PoeUsageOptimizer:
    """Optimize Poe usage for cost-effective trading."""

    def __init__(self):
        self.daily_budget = 10000  # Daily points budget
        self.hourly_budget = self.daily_budget // 24
        self.usage_history = []

    def should_use_consensus(self, market_volatility: float, position_size: float) -> bool:
        """Decide whether to use expensive consensus analysis."""

        # Use consensus for high-value or high-volatility situations
        if position_size > 10000 or market_volatility > 0.02:
            return True

        # Check if we have budget remaining
        current_hour_usage = self._get_current_hour_usage()
        return current_hour_usage < self.hourly_budget * 0.8

    def recommend_analysis_type(self, trade_importance: str) -> str:
        """Recommend analysis type based on importance and budget."""

        current_usage = self._get_current_hour_usage()
        budget_remaining = self.hourly_budget - current_usage

        if trade_importance == "critical" and budget_remaining > 200:
            return "full"
        elif trade_importance == "high" and budget_remaining > 100:
            return "full"
        else:
            return "quick"

    def _get_current_hour_usage(self) -> int:
        """Get points used in current hour."""
        # Implementation would track actual usage
        return 0

# Example usage
async def example_poe_integration():
    """Example of how to use Poe in your trading agent."""

    # Sample market data
    market_data = {
        'symbol': 'EURUSD',
        'timeframe': '1h',
        'current_price': 1.0875,
        'rsi': 45.2,
        'macd': 'bullish_crossover',
        'volume': 'above_average',
        'trend': 'upward'
    }

    # Get analysis
    analysis = await get_poe_trading_analysis('EURUSD', market_data, 'full')

    if analysis:
        print(f"Consensus: {analysis['consensus_action']}")
        print(f"Confidence: {analysis['consensus_confidence']}%")
        print(f"Agreement: {analysis['action_agreement']}")
        print(f"Points used: {analysis['total_points_used']}")
        print(f"Models: {analysis['models_consulted']}")
        print(f"Reasoning: {analysis['reasoning']}")

if __name__ == "__main__":
    # Test the integration
    asyncio.run(example_poe_integration())
