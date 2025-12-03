"""
LLM Client for OpenAI and Gemini Integration
Provides unified interface for trading analysis using OpenAI GPT and Google Gemini models.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class LLMProvider:
    """Unified LLM provider interface for OpenAI and Gemini"""

    def __init__(self, openai_api_key: str, gemini_api_key: str):
        self.openai_api_key = openai_api_key
        self.gemini_api_key = gemini_api_key
        self.session: Optional[aiohttp.ClientSession] = None
        self._initialize_session()

    def _initialize_session(self):
        """Initialize HTTP session with proper configuration"""
        if not self.session or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(
                timeout=timeout, headers={"User-Agent": "AI-Trading-System/1.0"}
            )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session and not self.session.closed:
            await self.session.close()

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def call_openai(
        self,
        prompt: str,
        model: str = "gpt-4",
        temperature: float = 0.3,
        max_tokens: int = 1000,
    ) -> Dict[str, Any]:
        """Call OpenAI API for trading analysis"""

        if not self.openai_api_key:
            raise ValueError("OpenAI API key not provided")

        self._initialize_session()

        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert trading analyst providing trading signals and market analysis.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            # response_format: {"type": "json_object"},  # Removed for gpt-4 compatibility
        }

        start_time = time.time()

        try:
            async with self.session.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                if response.status == 200:
                    data = await response.json()

                    # Parse trading signals from response
                    content = data["choices"][0]["message"]["content"]
                    tokens_used = data["usage"]["total_tokens"]
                    latency_ms = int((time.time() - start_time) * 1000)

                    try:
                        trading_data = json.loads(content)
                    except json.JSONDecodeError:
                        # Fallback to basic signal extraction
                        trading_data = self._extract_fallback_signals(content)

                    return {
                        "provider": "openai",
                        "model": model,
                        "content": trading_data,
                        "tokens_used": tokens_used,
                        "latency_ms": latency_ms,
                        "success": True,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                else:
                    error_text = await response.text()
                    logger.error(f"OpenAI API error: {response.status} - {error_text}")
                    return {
                        "provider": "openai",
                        "model": model,
                        "content": None,
                        "error": f"API Error {response.status}: {error_text}",
                        "success": False,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }

        except aiohttp.ClientError as e:
            logger.error(f"OpenAI network error: {e}")
            return {
                "provider": "openai",
                "model": model,
                "content": None,
                "error": f"Network error: {str(e)}",
                "success": False,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error(f"OpenAI unexpected error: {e}")
            return {
                "provider": "openai",
                "model": model,
                "content": None,
                "error": f"Unexpected error: {str(e)}",
                "success": False,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def call_gemini(
        self,
        prompt: str,
        model: str = "gemini-1.5-pro",
        temperature: float = 0.3,
        max_tokens: int = 1000,
    ) -> Dict[str, Any]:
        """Call Google Gemini API for trading analysis"""

        if not self.gemini_api_key:
            raise ValueError("Gemini API key not provided")

        self._initialize_session()

        headers = {"Content-Type": "application/json"}

        # Enhanced prompt for structured trading analysis
        enhanced_prompt = f"""You are an expert cryptocurrency trading analyst.
Analyze market data and provide structured trading signals.

{prompt}

Please respond with ONLY a JSON object containing:
{{
    "signal": "BUY/SELL/HOLD",
    "confidence": 0.0-1.0,
    "reason": "brief explanation",
    "entry_price": suggested entry price,
    "stop_loss": stop loss price,
    "take_profit": take profit price,
    "pattern": "pattern name",
    "strategy": "strategy used",
    "timeframe": "recommended timeframe"
}}

Example response:
{{"signal": "BUY", "confidence": 0.8, "reason": "RSI oversold", "entry_price": 45000, "stop_loss": 44100, "take_profit": 46350, "pattern": "oversold", "strategy": "mean_reversion", "timeframe": "1h"}}"""

        payload = {
            "contents": [{"parts": [{"text": enhanced_prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "candidateCount": 1,
            },
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_NONE",
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_NONE",
                },
            ],
        }

        start_time = time.time()

        try:
            url = f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={self.gemini_api_key}"

            async with self.session.post(
                url, headers=headers, json=payload
            ) as response:
                if response.status == 200:
                    data = await response.json()

                    # Extract content from Gemini response
                    content = data["candidates"][0]["content"]["parts"][0]["text"]
                    tokens_used = len(content.split())  # Approximate token count
                    latency_ms = int((time.time() - start_time) * 1000)

                    try:
                        trading_data = json.loads(content)
                    except json.JSONDecodeError:
                        # Try to extract JSON from response
                        trading_data = self._extract_json_from_text(content)
                        if not trading_data:
                            trading_data = self._extract_fallback_signals(content)

                    return {
                        "provider": "gemini",
                        "model": model,
                        "content": trading_data,
                        "tokens_used": tokens_used,
                        "latency_ms": latency_ms,
                        "success": True,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                else:
                    error_text = await response.text()
                    logger.error(f"Gemini API error: {response.status} - {error_text}")
                    return {
                        "provider": "gemini",
                        "model": model,
                        "content": None,
                        "error": f"API Error {response.status}: {error_text}",
                        "success": False,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }

        except aiohttp.ClientError as e:
            logger.error(f"Gemini network error: {e}")
            return {
                "provider": "gemini",
                "model": model,
                "content": None,
                "error": f"Network error: {str(e)}",
                "success": False,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error(f"Gemini unexpected error: {e}")
            return {
                "provider": "gemini",
                "model": model,
                "content": None,
                "error": f"Unexpected error: {str(e)}",
                "success": False,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    async def get_trading_signal(
        self,
        symbol: str,
        market_data: Dict[str, Any],
        provider: str = "openai",
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get trading signal for a specific symbol"""

        # Create comprehensive trading prompt
        prompt = f"""Analyze the following market data for {symbol} and provide a trading recommendation:

Current Price: ${market_data.get("price", 0):.2f}
24h Volume: {market_data.get("volume", 0):,.0f}
24h Change: {market_data.get("change_24h", 0):.2f}%

Technical Indicators:
- RSI: {market_data.get("rsi", 50):.1f}
- MACD: {market_data.get("macd", 0):.4f}
- Bollinger Upper: ${market_data.get("bb_upper", 0):.2f}
- Bollinger Lower: ${market_data.get("bb_lower", 0):.2f}
- Volume MA: {market_data.get("volume_ma", 0):,.0f}

Provide detailed analysis and specific trading signals."""

        # Call appropriate provider
        if provider == "openai":
            model = model or "gpt-4"
            return await self.call_openai(prompt, model)
        elif provider == "gemini":
            model = model or "gemini-pro"
            return await self.call_gemini(prompt, model)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    async def compare_providers(
        self, symbol: str, market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get trading signals from both providers and compare"""

        tasks = [
            self.get_trading_signal(symbol, market_data, "openai"),
            self.get_trading_signal(symbol, market_data, "gemini"),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        comparison = {
            "symbol": symbol,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "market_data": market_data,
        }

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Provider comparison error: {result}")
                continue

            if result["success"]:
                provider = result["provider"]
                comparison[f"{provider}_signal"] = result["content"]
                comparison[f"{provider}_confidence"] = result["content"].get(
                    "confidence", 0
                )
                comparison[f"{provider}_latency"] = result["latency_ms"]
            else:
                provider = result["provider"]
                comparison[f"{provider}_error"] = result["error"]

        # Determine consensus signal
        self._determine_consensus(comparison)

        return comparison

    def _determine_consensus(self, comparison: Dict[str, Any]) -> None:
        """Determine consensus signal from multiple providers"""

        signals = []
        confidences = []

        # Collect signals from successful providers
        for provider in ["openai", "gemini"]:
            signal_key = f"{provider}_signal"
            conf_key = f"{provider}_confidence"

            if signal_key in comparison and comparison[signal_key]:
                signal = comparison[signal_key].get("signal", "HOLD")
                confidence = comparison.get(conf_key, 0)

                signals.append(signal)
                confidences.append(confidence)

        # Calculate consensus
        if signals:
            from collections import Counter

            signal_counts = Counter(signals)
            most_common_signal = signal_counts.most_common(1)[0][0]

            # Weight by confidence
            weighted_signals = []
            for i, signal in enumerate(signals):
                weight = confidences[i]
                weighted_signals.append((signal, weight))

            comparison["consensus_signal"] = most_common_signal
            comparison["consensus_confidence"] = sum(confidences) / len(confidences)
            comparison["signal_agreement"] = signal_counts[most_common_signal] / len(
                signals
            )
        else:
            comparison["consensus_signal"] = "HOLD"
            comparison["consensus_confidence"] = 0
            comparison["signal_agreement"] = 0

    def _extract_fallback_signals(self, content: str) -> Dict[str, Any]:
        """Extract basic trading signals from unstructured text"""

        content_lower = content.lower()

        # Extract signal
        signal = "HOLD"
        if "buy" in content_lower:
            signal = "BUY"
        elif "sell" in content_lower:
            signal = "SELL"

        # Extract confidence (simple heuristic)
        confidence = 0.5
        if "high confidence" in content_lower or "very confident" in content_lower:
            confidence = 0.9
        elif "moderate confidence" in content_lower:
            confidence = 0.7
        elif "low confidence" in content_lower:
            confidence = 0.3

        return {
            "signal": signal,
            "confidence": confidence,
            "reason": "Fallback extraction from unstructured text",
            "entry_price": None,
            "stop_loss": None,
            "take_profit": None,
            "pattern": "UNKNOWN",
            "strategy": "FALLBACK",
        }

    def _extract_json_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON object from text using regex"""

        import re

        # Look for JSON-like patterns
        json_pattern = r"\{[^{}]*\}"
        matches = re.findall(json_pattern, text)

        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

        return None


class TradingAnalyzer:
    """High-level trading analysis using LLM providers"""

    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider

    async def analyze_market_conditions(
        self, symbol: str, market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze overall market conditions"""

        prompt = f"""Analyze the current market conditions for {symbol}:

Market Data:
{json.dumps(market_data, indent=2)}

Provide analysis on:
1. Overall market trend (BULL/BEAR/SIDEWAYS)
2. Volatility level (LOW/MEDIUM/HIGH)
3. Volume profile (LOW/AVERAGE/HIGH)
4. Key support/resistance levels
5. Recommended trading strategy
6. Risk assessment (LOW/MEDIUM/HIGH)

Respond with JSON format."""

        # Get analysis from primary provider
        result = await self.llm_provider.call_openai(
            prompt, model="gpt-4", temperature=0.2
        )

        if result["success"]:
            return result["content"]
        else:
            # Fallback to Gemini
            return await self.llm_provider.call_gemini(prompt)

    async def analyze_strategy_performance(
        self, strategy_name: str, trade_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze strategy performance and provide recommendations"""

        prompt = f"""Analyze the performance of the {strategy_name} trading strategy:

Trade History:
{json.dumps(trade_history[-20:], indent=2)}  # Last 20 trades

Provide analysis on:
1. Overall strategy effectiveness
2. Win rate analysis
3. Risk/reward profile
4. Recent performance trends
5. Optimization recommendations
6. Parameter adjustments needed

Respond with JSON format including specific recommendations."""

        result = await self.llm_provider.call_openai(
            prompt, model="gpt-4", temperature=0.3
        )

        return result if result["success"] else {"error": result["error"]}

    async def get_learning_insights(
        self, performance_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get AI-powered insights for system learning"""

        prompt = f"""Analyze the trading system performance data and provide learning insights:

Performance Data:
{json.dumps(performance_data, indent=2)}

Provide insights on:
1. Pattern recognition opportunities
2. Strategy optimization areas
3. Risk management improvements
4. Market condition adaptations
5. Learning priorities
6. Next optimization steps

Respond with actionable recommendations in JSON format."""

        # Use both providers for comprehensive analysis
        openai_result = await self.llm_provider.call_openai(prompt, temperature=0.2)
        gemini_result = await self.llm_provider.call_gemini(prompt, temperature=0.2)

        return {
            "openai_insights": openai_result["content"]
            if openai_result["success"]
            else None,
            "gemini_insights": gemini_result["content"]
            if gemini_result["success"]
            else None,
            "combined_analysis": self._combine_insights(
                openai_result["content"] if openai_result["success"] else {},
                gemini_result["content"] if gemini_result["success"] else {},
            ),
        }

    def _combine_insights(
        self, openai_insights: Dict[str, Any], gemini_insights: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Combine insights from multiple providers"""

        combined = {
            "primary_recommendations": [],
            "optimization_priorities": [],
            "risk_adjustments": [],
        }

        # Extract and merge recommendations
        for insights in [openai_insights, gemini_insights]:
            if isinstance(insights, dict):
                if "recommendations" in insights:
                    combined["primary_recommendations"].extend(
                        insights["recommendations"]
                    )
                if "optimization" in insights:
                    combined["optimization_priorities"].extend(insights["optimization"])
                if "risk_management" in insights:
                    combined["risk_adjustments"].extend(insights["risk_management"])

        # Remove duplicates and prioritize
        combined["primary_recommendations"] = list(
            set(combined["primary_recommendations"])
        )
        combined["optimization_priorities"] = list(
            set(combined["optimization_priorities"])
        )
        combined["risk_adjustments"] = list(set(combined["risk_adjustments"]))

        return combined
