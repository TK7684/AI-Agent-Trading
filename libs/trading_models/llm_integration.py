"""
Multi-LLM Router and Integration System

This module provides a unified interface for interacting with multiple LLM providers,
intelligent routing based on various policies, performance tracking, and fallback mechanisms.
Optimized for performance, memory efficiency, and reliability.
"""

import asyncio
import json
import logging
import statistics
import time
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Optional

import aiohttp
from aiohttp import ClientSession, ClientTimeout
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class ModelProvider(Enum):
    """Supported LLM providers"""
    CLAUDE = "claude"
    GEMINI = "gemini"
    GPT4_TURBO = "gpt4_turbo"
    MIXTRAL = "mixtral"
    LLAMA = "llama"


class RoutingPolicy(Enum):
    """Available routing policies"""
    ACCURACY_FIRST = "accuracy_first"
    COST_AWARE = "cost_aware"
    LATENCY_AWARE = "latency_aware"
    LOAD_BALANCED = "load_balanced"
    ADAPTIVE = "adaptive"


class MarketRegime(Enum):
    """Market regime types for prompt adaptation"""
    BULL = "bull"
    BEAR = "bear"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"


@dataclass
class LLMRequest:
    """Request structure for LLM calls with optimization features"""
    prompt: str
    model_id: str
    context: dict[str, Any]
    max_tokens: int = 1000
    temperature: float = 0.7
    timeout_seconds: int = 30
    request_id: Optional[str] = None
    priority: int = 1  # Higher number = higher priority
    retry_count: int = 0
    max_retries: int = 3

    def __post_init__(self):
        """Validate request parameters."""
        if self.temperature < 0 or self.temperature > 2:
            raise ValueError("Temperature must be between 0 and 2")
        if self.max_tokens <= 0:
            raise ValueError("Max tokens must be positive")
        if self.timeout_seconds <= 0:
            raise ValueError("Timeout must be positive")


@dataclass
class LLMResponse:
    """Response structure from LLM calls with enhanced metadata"""
    content: str
    model_id: str
    tokens_used: int
    latency_ms: int
    cost_usd: float
    confidence: float
    request_id: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    success: bool = True
    error_message: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_high_confidence(self) -> bool:
        """Check if response has high confidence."""
        return self.confidence >= 0.8

    @property
    def cost_per_token(self) -> float:
        """Calculate cost per token."""
        return self.cost_usd / max(self.tokens_used, 1)


@dataclass
class ModelMetrics:
    """Performance metrics for a specific model with rolling statistics"""
    model_id: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_latency_ms: float = 0.0
    avg_cost_per_token: float = 0.0
    avg_confidence: float = 0.0
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    recent_latencies: deque = field(default_factory=lambda: deque(maxlen=100))
    recent_costs: deque = field(default_factory=lambda: deque(maxlen=100))
    recent_confidences: deque = field(default_factory=lambda: deque(maxlen=100))

    # Performance tracking
    success_rate: float = 0.0
    avg_tokens_per_request: float = 0.0
    total_cost_usd: float = 0.0

    def update_metrics(self, response: LLMResponse) -> None:
        """Update metrics with new response data."""
        self.total_requests += 1

        if response.success:
            self.successful_requests += 1
            self.last_success = response.timestamp
            self.recent_latencies.append(response.latency_ms)
            self.recent_costs.append(response.cost_usd)
            self.recent_confidences.append(response.confidence)
        else:
            self.failed_requests += 1
            self.last_failure = response.timestamp

        # Update rolling averages
        self._update_rolling_averages()
        self._update_derived_metrics()

    def _update_rolling_averages(self) -> None:
        """Update rolling averages efficiently."""
        if self.recent_latencies:
            self.avg_latency_ms = statistics.mean(self.recent_latencies)
        if self.recent_costs:
            self.avg_cost_per_token = statistics.mean(self.recent_costs)
        if self.recent_confidences:
            self.avg_confidence = statistics.mean(self.recent_confidences)

    def _update_derived_metrics(self) -> None:
        """Update derived metrics."""
        if self.total_requests > 0:
            self.success_rate = self.successful_requests / self.total_requests


class ConnectionPool:
    """Connection pool for HTTP clients with optimization."""

    def __init__(self, max_connections: int = 100, max_keepalive: int = 20):
        self.max_connections = max_connections
        self.max_keepalive = max_keepalive
        self._sessions: dict[str, ClientSession] = {}
        self._lock = asyncio.Lock()

    async def get_session(self, base_url: str) -> ClientSession:
        """Get or create a session for a base URL."""
        async with self._lock:
            if base_url not in self._sessions:
                timeout = ClientTimeout(total=30, connect=10)
                connector = aiohttp.TCPConnector(
                    limit=self.max_connections,
                    limit_per_host=20,
                    keepalive_timeout=30,
                    enable_cleanup_closed=True
                )
                self._sessions[base_url] = ClientSession(
                    timeout=timeout,
                    connector=connector,
                    headers={'User-Agent': 'TradingSystem/1.0'}
                )
            return self._sessions[base_url]

    async def close_all(self) -> None:
        """Close all sessions."""
        async with self._lock:
            for session in self._sessions.values():
                await session.close()
            self._sessions.clear()


class LLMClient(ABC):
    """Abstract base class for LLM clients with optimization features."""

    def __init__(self, model_id: str, api_key: str, **kwargs):
        self.model_id = model_id
        self.api_key = api_key
        self.config = kwargs
        self.connection_pool = ConnectionPool()
        self._request_cache = {}
        self._cache_ttl = 300  # 5 minutes

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate response from LLM."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the LLM service is healthy."""
        pass

    def _get_cache_key(self, request: LLMRequest) -> str:
        """Generate cache key for request."""
        # Simple hash of prompt and context
        content = f"{request.prompt}:{json.dumps(request.context, sort_keys=True)}"
        return f"{self.model_id}:{hash(content)}"

    def get_cost_per_token(self) -> float:
        """Get cost per token for this model."""
        # Default implementation - subclasses can override
        return 0.00002  # $0.00002 per token as default

    def get_max_tokens(self) -> int:
        """Get maximum tokens supported by this model."""
        # Default implementation - subclasses can override
        return 4000  # 4k tokens as default

    def _get_cached_response(self, cache_key: str) -> Optional[LLMResponse]:
        """Get cached response if available and not expired."""
        if cache_key in self._request_cache:
            cached_item = self._request_cache[cache_key]
            if time.time() - cached_item['timestamp'] < self._cache_ttl:
                return cached_item['response']
            else:
                del self._request_cache[cache_key]
        return None

    def _cache_response(self, cache_key: str, response: LLMResponse) -> None:
        """Cache response with timestamp."""
        self._request_cache[cache_key] = {
            'response': response,
            'timestamp': time.time()
        }

    async def close(self) -> None:
        """Close client resources."""
        await self.connection_pool.close_all()


class ClaudeClient(LLMClient):
    """Anthropic Claude client with optimization."""

    def __init__(self, model_id: str, api_key: str, **kwargs):
        super().__init__(model_id, api_key, **kwargs)
        self.base_url = "https://api.anthropic.com/v1"
        self.model_mapping = {
            "claude-3-opus": "claude-3-opus-20240229",
            "claude-3-sonnet": "claude-3-sonnet-20240229",
            "claude-3-haiku": "claude-3-haiku-20240307"
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate response from Claude with retry logic."""
        start_time = time.time()

        # Check cache first
        cache_key = self._get_cache_key(request)
        cached_response = self._get_cached_response(cache_key)
        if cached_response:
            return cached_response

        try:
            session = await self.connection_pool.get_session(self.base_url)

            payload = {
                "model": self.model_mapping.get(request.model_id, request.model_id),
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
                "messages": [{"role": "user", "content": request.prompt}]
            }

            async with session.post(
                f"{self.base_url}/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json=payload,
                timeout=aiohttp.ClientTimeout(total=request.timeout_seconds)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    latency_ms = int((time.time() - start_time) * 1000)

                    llm_response = LLMResponse(
                        content=data["content"][0]["text"],
                        model_id=request.model_id,
                        tokens_used=data["usage"]["input_tokens"] + data["usage"]["output_tokens"],
                        latency_ms=latency_ms,
                        cost_usd=self._calculate_cost(data["usage"]),
                        confidence=0.8,  # Default confidence for Claude
                        request_id=request.request_id,
                        metadata={"claude_response": data}
                    )

                    # Cache the response
                    self._cache_response(cache_key, llm_response)
                    return llm_response
                else:
                    error_text = await response.text()
                    raise Exception(f"Claude API error: {response.status} - {error_text}")

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            return LLMResponse(
                content="",
                model_id=request.model_id,
                tokens_used=0,
                latency_ms=latency_ms,
                cost_usd=0.0,
                confidence=0.0,
                request_id=request.request_id,
                success=False,
                error_message=str(e)
            )

    async def health_check(self) -> bool:
        """Check Claude API health."""
        try:
            session = await self.connection_pool.get_session(self.base_url)
            async with session.get(
                f"{self.base_url}/models",
                headers={"x-api-key": self.api_key}
            ) as response:
                return response.status == 200
        except Exception:
            return False

    def _calculate_cost(self, usage: dict[str, int]) -> float:
        """Calculate cost based on token usage."""
        # Claude pricing (approximate)
        input_cost_per_1k = 0.015
        output_cost_per_1k = 0.075

        input_cost = (usage["input_tokens"] / 1000) * input_cost_per_1k
        output_cost = (usage["output_tokens"] / 1000) * output_cost_per_1k

        return input_cost + output_cost


class MultiLLMRouter:
    """Optimized multi-LLM router with intelligent routing and load balancing."""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.clients: dict[str, LLMClient] = {}
        self.circuit_breakers: dict[str, CircuitBreaker] = {}
        self.metrics: dict[str, ModelMetrics] = defaultdict(ModelMetrics)
        self.routing_policy = RoutingPolicy.ADAPTIVE
        self.default_policy = RoutingPolicy.ACCURACY_FIRST
        self._load_balancer_state = defaultdict(int)
        self._circuit_breakers: dict[str, bool] = defaultdict(lambda: True)
        self._lock = asyncio.Lock()
        self.performance_tracker = ModelPerformanceTracker()
        self.prompt_generator = PromptGenerator()

        # Initialize clients
        self._initialize_clients()

    def _initialize_clients(self) -> None:
        """Initialize LLM clients based on configuration."""
        # Handle both 'providers' and 'clients' config formats
        clients_config = self.config.get("clients", self.config.get("providers", {}))

        for provider, provider_config in clients_config.items():
            if provider_config.get("enabled", False):
                client_class = self._get_client_class(provider)
                if client_class:
                    model_id = provider_config.get("model_version", provider_config.get("model_id", f"{provider}-default"))
                    api_key = provider_config["api_key"]

                    self.clients[model_id] = client_class(
                        api_key=api_key,
                        model_id=model_id
                    )
                    self.circuit_breakers[model_id] = CircuitBreaker()
                    self.metrics[model_id] = ModelMetrics()

    def _get_client_class(self, provider: str) -> Optional[type[LLMClient]]:
        """Get client class for provider."""
        client_map = {
            "claude": ClaudeClient,
            "gemini": GeminiClient,
            "gpt4": GPT4TurboClient,
            "mixtral": MixtralClient,
            "llama": LlamaClient,
        }
        return client_map.get(provider)

    async def route_request(self, request: LLMRequest, policy: Optional[RoutingPolicy] = None) -> LLMResponse:
        """Route request to best available LLM based on policy."""
        available_clients = self._get_available_clients()

        if not available_clients:
            raise Exception("No available LLM clients")

        # Use provided policy or default
        routing_policy = policy or self.routing_policy

        # Select client based on routing policy
        selected_client = await self._select_client(request, available_clients, routing_policy)

        # Execute request
        response = await selected_client.generate(request)

        # Update metrics and performance tracker
        self.performance_tracker.record_request(response)

        return response

    def _get_available_clients(self) -> list[LLMClient]:
        """Get list of available clients."""
        return [
            client for provider, client in self.clients.items()
            if self._circuit_breakers[provider]
        ]

    async def _select_client(self, request: LLMRequest, available_clients: list[LLMClient],
                            policy: RoutingPolicy) -> LLMClient:
        """Select best client based on routing policy."""
        if policy == RoutingPolicy.ACCURACY_FIRST:
            return self._select_by_accuracy(available_clients)
        elif policy == RoutingPolicy.COST_AWARE:
            return self._select_by_cost(available_clients)
        elif policy == RoutingPolicy.LATENCY_AWARE:
            return self._select_by_latency(available_clients)
        elif policy == RoutingPolicy.LOAD_BALANCED:
            return self._select_by_load_balance(available_clients)
        else:  # ADAPTIVE
            return await self._select_adaptive(available_clients, request)

    def _select_by_accuracy(self, clients: list[LLMClient]) -> LLMClient:
        """Select client with highest confidence."""
        return max(clients, key=lambda c: self.metrics[c.model_id].avg_confidence)

    def _select_by_cost(self, clients: list[LLMClient]) -> LLMClient:
        """Select client with lowest cost per token."""
        return min(clients, key=lambda c: self.metrics[c.model_id].avg_cost_per_token)

    def _select_by_latency(self, clients: list[LLMClient]) -> LLMClient:
        """Select client with lowest latency."""
        return min(clients, key=lambda c: self.metrics[c.model_id].avg_latency_ms)

    def _select_by_load_balance(self, clients: list[LLMClient]) -> LLMClient:
        """Select client with lowest load."""
        return min(clients, key=lambda c: self._load_balancer_state[c.model_id])

    async def _select_adaptive(self, clients: list[LLMClient], request: LLMRequest) -> LLMClient:
        """Adaptive selection based on multiple factors."""
        scores = {}

        for client in clients:
            metrics = self.metrics[client.model_id]

            # Normalize scores (0-1)
            accuracy_score = metrics.avg_confidence
            cost_score = 1 - min(metrics.avg_cost_per_token * 1000, 1)  # Normalize cost
            latency_score = 1 - min(metrics.avg_latency_ms / 1000, 1)  # Normalize latency
            success_score = metrics.success_rate

            # Weighted combination
            total_score = (
                accuracy_score * 0.3 +
                cost_score * 0.2 +
                latency_score * 0.2 +
                success_score * 0.3
            )

            scores[client] = total_score

        return max(clients, key=lambda c: scores[c])

    async def close(self) -> None:
        """Close all clients."""
        for client in self.clients.values():
            await client.close()

    def get_metrics_summary(self) -> dict[str, Any]:
        """Get summary of all metrics."""
        summary = {}
        for provider, metrics in self.metrics.items():
            summary[provider] = {
                "success_rate": metrics.success_rate,
                "avg_latency_ms": metrics.avg_latency_ms,
                "avg_cost_per_token": metrics.avg_cost_per_token,
                "avg_confidence": metrics.avg_confidence,
                "total_requests": metrics.total_requests,
                "circuit_breaker_open": not self._circuit_breakers[provider]
            }
        return summary

    # Additional methods expected by tests
    def generate_market_analysis_prompt(self, **kwargs) -> str:
        """Generate market analysis prompt using the internal prompt generator."""
        return self.prompt_generator.generate_market_analysis_prompt(**kwargs)

    def get_performance_metrics(self) -> dict[str, Any]:
        """Get performance metrics for all models."""
        return {
            model_id: {
                "total_requests": metrics.total_requests,
                "success_rate": metrics.success_rate,
                "avg_latency_ms": metrics.avg_latency_ms,
                "avg_cost_usd": metrics.avg_cost_usd,
                "avg_confidence": metrics.avg_confidence
            }
            for model_id, metrics in self.performance_tracker.metrics.items()
        }

    def get_cost_summary(self) -> dict[str, float]:
        """Get cost summary for all models."""
        return {
            model_id: metrics.total_cost_usd
            for model_id, metrics in self.performance_tracker.metrics.items()
        }

    def reset_circuit_breaker(self, model_id: str) -> None:
        """Reset circuit breaker for a specific model."""
        if model_id in self.circuit_breakers:
            self.circuit_breakers[model_id].record_success()

    def set_routing_policy(self, policy: RoutingPolicy) -> None:
        """Set the routing policy."""
        self.routing_policy = policy
        self.default_policy = policy


class CircuitBreaker:
    """Simple circuit breaker implementation."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def record_success(self):
        """Record a successful call."""
        self.failure_count = 0
        self.state = "CLOSED"

    def record_failure(self):
        """Record a failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"

    def can_execute(self) -> bool:
        """Check if calls can be executed."""
        if self.state == "CLOSED":
            return True

        if self.state == "OPEN":
            if self.last_failure_time and time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                return True
            return False

        # HALF_OPEN state
        return True

    # Aliases for backward compatibility
    def call_succeeded(self):
        """Alias for record_success."""
        self.record_success()

    def call_failed(self):
        """Alias for record_failure."""
        self.record_failure()


class PromptGenerator:
    """Generates optimized prompts for different market conditions."""

    def __init__(self):
        self.base_prompts = {
            "technical_analysis": "Analyze the following technical indicators and market data:",
            "risk_assessment": "Assess the risk level of the following trading scenario:",
            "pattern_recognition": "Identify patterns in the following market data:",
        }

        self.regime_guidance = {
            "BULL": "momentum continuation",
            "BEAR": "reversal opportunities",
            "SIDEWAYS": "range trading"
        }

    def generate_prompt(self, prompt_type: str, context: dict[str, Any]) -> str:
        """Generate a context-aware prompt."""
        base = self.base_prompts.get(prompt_type, "Analyze the following data:")

        # Add market regime context
        if "market_regime" in context:
            regime = context["market_regime"]
            base += f" Consider the current {regime} market conditions."

        # Add symbol context
        if "symbol" in context:
            base += f" Focus on {context['symbol']}."

        # Add timeframe context
        if "timeframe" in context:
            base += f" Use {context['timeframe']} timeframe analysis."

        return base

    def generate_market_analysis_prompt(self, symbol: str, timeframe: str, regime,
                                      indicators: dict[str, float], patterns: list[dict],
                                      volatility: float) -> str:
        """Generate market analysis prompt with detailed context."""
        regime_str = regime.value if hasattr(regime, 'value') else str(regime)

        prompt = f"Analyze {symbol} on {timeframe} timeframe in {regime_str.lower()} market conditions.\n\n"

        # Add indicators
        prompt += "Technical Indicators:\n"
        for name, value in indicators.items():
            prompt += f"- {name}: {value}\n"

        # Add patterns
        if patterns:
            prompt += "\nIdentified Patterns:\n"
            for pattern in patterns:
                prompt += f"- {pattern['name']}: {pattern['confidence']} confidence\n"

        # Add volatility
        prompt += f"\nVolatility: {volatility}\n"

        # Add regime-specific guidance
        guidance = self.regime_guidance.get(regime_str.upper(), "general analysis")
        prompt += f"\nFocus on {guidance} opportunities."

        return prompt

    def generate_risk_assessment_prompt(self, position_size: float, stop_loss: float,
                                      take_profit: float, portfolio_exposure: float) -> str:
        """Generate risk assessment prompt."""
        prompt = "Assess the risk of this trading scenario:\n\n"
        prompt += f"Position Size: {position_size}\n"
        prompt += f"Stop Loss: {stop_loss}\n"
        prompt += f"Take Profit: {take_profit}\n"
        prompt += f"Portfolio Exposure: {portfolio_exposure}%\n\n"
        prompt += "Evaluate risk-reward ratio and provide recommendations."

        return prompt


@dataclass
class ModelMetrics:
    """Metrics for a specific model."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_latency_ms: float = 0.0
    total_cost_usd: float = 0.0
    total_confidence: float = 0.0

    @property
    def avg_latency_ms(self) -> float:
        """Average latency in milliseconds."""
        return self.total_latency_ms / max(self.total_requests, 1)

    @property
    def avg_cost_usd(self) -> float:
        """Average cost in USD."""
        return self.total_cost_usd / max(self.total_requests, 1)

    @property
    def avg_confidence(self) -> float:
        """Average confidence score."""
        return self.total_confidence / max(self.total_requests, 1)

    @property
    def success_rate(self) -> float:
        """Success rate as a percentage."""
        return self.successful_requests / max(self.total_requests, 1)


class ModelPerformanceTracker:
    """Tracks and analyzes model performance over time."""

    def __init__(self):
        self.performance_history = defaultdict(list)
        self.accuracy_history = defaultdict(list)
        self.latency_history = defaultdict(list)
        self.metrics = defaultdict(ModelMetrics)

    def record_request(self, response):
        """Record a request response for performance tracking."""
        model_id = response.model_id
        metrics = self.metrics[model_id]

        metrics.total_requests += 1
        metrics.total_latency_ms += response.latency_ms
        metrics.total_cost_usd += response.cost_usd
        metrics.total_confidence += response.confidence

        if response.success:
            metrics.successful_requests += 1
        else:
            metrics.failed_requests += 1

    def record_performance(self, model_id: str, accuracy: float, latency_ms: float):
        """Record performance metrics for a model."""
        timestamp = datetime.now(UTC)

        self.performance_history[model_id].append({
            "timestamp": timestamp,
            "accuracy": accuracy,
            "latency_ms": latency_ms
        })

        self.accuracy_history[model_id].append(accuracy)
        self.latency_history[model_id].append(latency_ms)

        # Keep only last 1000 records
        if len(self.performance_history[model_id]) > 1000:
            self.performance_history[model_id].pop(0)
            self.accuracy_history[model_id].pop(0)
            self.latency_history[model_id].pop(0)

    def get_average_accuracy(self, model_id: str) -> float:
        """Get average accuracy for a model."""
        if not self.accuracy_history[model_id]:
            return 0.0
        return statistics.mean(self.accuracy_history[model_id])

    def get_average_latency(self, model_id: str) -> float:
        """Get average latency for a model."""
        if not self.latency_history[model_id]:
            return 0.0
        return statistics.mean(self.latency_history[model_id])

    def get_best_model(self, policy: RoutingPolicy, available_models: list[str]) -> Optional[str]:
        """Get the best performing model based on routing policy."""
        if not self.metrics or not available_models:
            return None

        # Filter to only available models
        available_metrics = {k: v for k, v in self.metrics.items() if k in available_models}
        if not available_metrics:
            return None

        if policy == RoutingPolicy.ACCURACY_FIRST:
            return max(available_metrics.keys(), key=lambda m: available_metrics[m].avg_confidence)
        elif policy == RoutingPolicy.LATENCY_AWARE:
            return min(available_metrics.keys(), key=lambda m: available_metrics[m].avg_latency_ms)
        elif policy == RoutingPolicy.COST_AWARE:
            return min(available_metrics.keys(), key=lambda m: available_metrics[m].avg_cost_usd)
        else:
            return max(available_metrics.keys(), key=lambda m: available_metrics[m].success_rate)

    def get_model_score(self, model_id: str, policy: RoutingPolicy) -> float:
        """Get model score based on routing policy."""
        if model_id not in self.metrics:
            return 0.0

        metrics = self.metrics[model_id]

        if policy == RoutingPolicy.ACCURACY_FIRST:
            return metrics.avg_confidence
        elif policy == RoutingPolicy.LATENCY_AWARE:
            # Higher score for lower latency (invert)
            return 1.0 / max(metrics.avg_latency_ms, 1.0)
        elif policy == RoutingPolicy.COST_AWARE:
            # Higher score for lower cost (invert)
            return 1.0 / max(metrics.avg_cost_usd, 0.001)
        else:
            return metrics.success_rate


class GeminiClient(LLMClient):
    """Google Gemini API client."""

    def __init__(self, api_key: str, model_id: str = "gemini-pro"):
        super().__init__(model_id, api_key)
        self.api_key = api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1/models"

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate response using Gemini."""
        start_time = time.time()

        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/{self.model_id}:generateContent"
                headers = {"x-goog-api-key": self.api_key}

                payload = {
                    "contents": [{"parts": [{"text": request.prompt}]}],
                    "generationConfig": {
                        "maxOutputTokens": request.max_tokens,
                        "temperature": request.temperature
                    }
                }

                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status != 200:
                        raise Exception(f"Gemini API error: {response.status}")

                    data = await response.json()
                    content = data["candidates"][0]["content"]["parts"][0]["text"]

                    return LLMResponse(
                        content=content,
                        model_id=self.model_id,
                        tokens_used=len(content.split()) * 2,  # Rough estimate
                        confidence=0.8,  # Default confidence
                        latency_ms=int((time.time() - start_time) * 1000),
                        cost_usd=0.01  # Default cost
                    )

        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            raise

    async def health_check(self) -> bool:
        """Check if Gemini API is healthy."""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/gemini-pro:generateContent"
                headers = {"x-goog-api-key": self.api_key}
                payload = {"contents": [{"parts": [{"text": "test"}]}]}

                async with session.post(url, json=payload, headers=headers) as response:
                    return response.status == 200
        except Exception:
            return False


class GPT4TurboClient(LLMClient):
    """OpenAI GPT-4 Turbo API client."""

    def __init__(self, api_key: str, model_id: str = "gpt-4-turbo-preview"):
        super().__init__(model_id, api_key)
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1"

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate response using GPT-4 Turbo."""
        start_time = time.time()

        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/chat/completions"
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }

                payload = {
                    "model": self.model_id,
                    "messages": [{"role": "user", "content": request.prompt}],
                    "max_tokens": request.max_tokens,
                    "temperature": request.temperature
                }

                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status != 200:
                        raise Exception(f"OpenAI API error: {response.status}")

                    data = await response.json()
                    content = data["choices"][0]["message"]["content"]
                    usage = data["usage"]

                    return LLMResponse(
                        content=content,
                        model_id=self.model_id,
                        tokens_used=usage["total_tokens"],
                        confidence=0.85,  # Default confidence
                        latency_ms=int((time.time() - start_time) * 1000),
                        cost_usd=usage["total_tokens"] * 0.00002  # Rough cost estimate
                    )

        except Exception as e:
            logger.error(f"GPT-4 Turbo generation failed: {e}")
            raise

    async def health_check(self) -> bool:
        """Check if OpenAI API is healthy."""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {self.api_key}"}
                async with session.get(f"{self.base_url}/models", headers=headers) as response:
                    return response.status == 200
        except Exception:
            return False


class MixtralClient(LLMClient):
    """Mixtral API client."""

    def __init__(self, api_key: str, model_id: str = "mixtral-8x7b-instruct"):
        super().__init__(model_id, api_key)
        self.api_key = api_key
        self.base_url = "https://api.together.xyz/v1"

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate response using Mixtral."""
        start_time = time.time()

        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/chat/completions"
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }

                payload = {
                    "model": self.model_id,
                    "messages": [{"role": "user", "content": request.prompt}],
                    "max_tokens": request.max_tokens,
                    "temperature": request.temperature
                }

                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status != 200:
                        raise Exception(f"Mixtral API error: {response.status}")

                    data = await response.json()
                    content = data["choices"][0]["message"]["content"]

                    return LLMResponse(
                        content=content,
                        model_id=self.model_id,
                        tokens_used=len(content.split()) * 2,  # Rough estimate
                        confidence=0.75,  # Default confidence
                        latency_ms=int((time.time() - start_time) * 1000),
                        cost_usd=0.005  # Default cost
                    )

        except Exception as e:
            logger.error(f"Mixtral generation failed: {e}")
            raise

    async def health_check(self) -> bool:
        """Check if Mixtral API is healthy."""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {self.api_key}"}
                async with session.get(f"{self.base_url}/models", headers=headers) as response:
                    return response.status == 200
        except Exception:
            return False


class LlamaClient(LLMClient):
    """Llama API client."""

    def __init__(self, api_key: str, model_id: str = "llama-2-70b-chat"):
        super().__init__(model_id, api_key)
        self.api_key = api_key
        self.base_url = "https://api.together.xyz/v1"

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate response using Llama."""
        start_time = time.time()

        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/chat/completions"
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }

                payload = {
                    "model": self.model_id,
                    "messages": [{"role": "user", "content": request.prompt}],
                    "max_tokens": request.max_tokens,
                    "temperature": request.temperature
                }

                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status != 200:
                        raise Exception(f"Llama API error: {response.status}")

                    data = await response.json()
                    content = data["choices"][0]["message"]["content"]

                    return LLMResponse(
                        content=content,
                        model_id=self.model_id,
                        tokens_used=len(content.split()) * 2,  # Rough estimate
                        confidence=0.7,  # Default confidence
                        latency_ms=int((time.time() - start_time) * 1000),
                        cost_usd=0.003  # Default cost
                    )

        except Exception as e:
            logger.error(f"Llama generation failed: {e}")
            raise

    async def health_check(self) -> bool:
        """Check if Llama API is healthy."""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {self.api_key}"}
                async with session.get(f"{self.base_url}/models", headers=headers) as response:
                    return response.status == 200
        except Exception:
            return False


# Alias for backwards compatibility
LLMRouter = MultiLLMRouter
