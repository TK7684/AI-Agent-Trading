"""
Tests for Multi-LLM Router and Integration System
"""

from unittest.mock import AsyncMock, patch

import pytest

from libs.trading_models.llm_integration import (
    CircuitBreaker,
    ClaudeClient,
    GeminiClient,
    GPT4TurboClient,
    LlamaClient,
    LLMRequest,
    LLMResponse,
    MarketRegime,
    MixtralClient,
    ModelPerformanceTracker,
    MultiLLMRouter,
    PromptGenerator,
    RoutingPolicy,
)


class TestLLMClients:
    """Test individual LLM client implementations"""

    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.post')
    async def test_claude_client_success(self, mock_post):
        """Test Claude client successful response"""
        # Mock successful API response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "content": [{"text": "Analysis of BTCUSD shows bullish momentum"}],
            "usage": {"input_tokens": 10, "output_tokens": 20}
        }
        mock_post.return_value.__aenter__.return_value = mock_response

        client = ClaudeClient("test-api-key", "claude-3-sonnet")

        request = LLMRequest(
            prompt="Analyze BTCUSD",
            model_id=client.model_id,
            context={"symbol": "BTCUSD", "timeframe": "1h"}
        )

        response = await client.generate(request)

        assert response.success
        assert response.model_id == client.model_id
        assert "BTCUSD" in response.content
        assert response.tokens_used > 0
        assert response.latency_ms > 0
        assert response.cost_usd > 0
        assert 0 <= response.confidence <= 1

    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.post')
    async def test_gemini_client_success(self, mock_post):
        """Test Gemini client successful response"""
        # Mock successful API response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "Analysis of ETHUSD shows consolidation"}]}}]
        }
        mock_post.return_value.__aenter__.return_value = mock_response

        client = GeminiClient("test-api-key", "gemini-pro")

        request = LLMRequest(
            prompt="Analyze ETHUSD",
            model_id=client.model_id,
            context={"symbol": "ETHUSD", "timeframe": "4h"}
        )

        response = await client.generate(request)

        assert response.success
        assert response.model_id == client.model_id
        assert "ETHUSD" in response.content
        assert response.tokens_used > 0
        assert response.cost_usd >= 0

    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.post')
    async def test_gpt4_turbo_client_success(self, mock_post):
        """Test GPT-4 Turbo client successful response"""
        # Mock successful API response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "GPT-4 analysis of market conditions"}}],
            "usage": {"total_tokens": 150}
        }
        mock_post.return_value.__aenter__.return_value = mock_response

        client = GPT4TurboClient("test-api-key", "gpt-4-turbo-preview")

        request = LLMRequest(
            prompt="Analyze ADAUSD",
            model_id=client.model_id,
            context={"symbol": "ADAUSD", "timeframe": "1d"}
        )

        response = await client.generate(request)

        assert response.success
        assert response.model_id == client.model_id
        assert "ADAUSD" in response.content

    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.post')
    async def test_mixtral_client_success(self, mock_post):
        """Test Mixtral client successful response"""
        # Mock successful API response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Mixtral analysis shows strong trends"}}]
        }
        mock_post.return_value.__aenter__.return_value = mock_response

        client = MixtralClient("test-api-key", "mixtral-8x7b-instruct")

        request = LLMRequest(
            prompt="Analyze SOLUSD",
            model_id=client.model_id,
            context={"symbol": "SOLUSD", "timeframe": "15m"}
        )

        response = await client.generate(request)

        assert response.success
        assert response.model_id == client.model_id
        assert "SOLUSD" in response.content

    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.post')
    async def test_llama_client_success(self, mock_post):
        """Test Llama client successful response"""
        # Mock successful API response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Llama analysis indicates market sentiment"}}]
        }
        mock_post.return_value.__aenter__.return_value = mock_response

        client = LlamaClient("test-api-key", "llama-2-70b-chat")

        request = LLMRequest(
            prompt="Analyze DOTUSD",
            model_id=client.model_id,
            context={"symbol": "DOTUSD", "timeframe": "1h"}
        )

        response = await client.generate(request)

        assert response.success
        assert response.model_id == client.model_id
        assert "DOTUSD" in response.content

    def test_client_cost_per_token(self):
        """Test that all clients return valid cost per token"""
        clients = [
            ClaudeClient("test-key", "claude-3-sonnet"),
            GeminiClient("test-key", "gemini-pro"),
            GPT4TurboClient("test-key", "gpt-4-turbo"),
            MixtralClient("test-key", "mixtral-8x7b"),
            LlamaClient("test-key", "llama-2-70b")
        ]

        for client in clients:
            cost = client.get_cost_per_token()
            assert cost > 0
            assert cost < 1  # Should be less than $1 per token

    def test_client_max_tokens(self):
        """Test that all clients return valid max tokens"""
        clients = [
            ClaudeClient("test-key", "claude-3-sonnet"),
            GeminiClient("test-key", "gemini-pro"),
            GPT4TurboClient("test-key", "gpt-4-turbo"),
            MixtralClient("test-key", "mixtral-8x7b"),
            LlamaClient("test-key", "llama-2-70b")
        ]

        for client in clients:
            max_tokens = client.get_max_tokens()
            assert max_tokens > 1000  # Should support reasonable context


class TestCircuitBreaker:
    """Test circuit breaker functionality"""

    def test_circuit_breaker_initial_state(self):
        """Test circuit breaker starts in closed state"""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)

        assert cb.can_execute()
        assert cb.state == "CLOSED"
        assert cb.failure_count == 0

    def test_circuit_breaker_failure_tracking(self):
        """Test circuit breaker tracks failures correctly"""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)

        # Record failures
        cb.record_failure()
        assert cb.failure_count == 1
        assert cb.can_execute()  # Still closed

        cb.record_failure()
        assert cb.failure_count == 2
        assert cb.can_execute()  # Still closed

        cb.record_failure()
        assert cb.failure_count == 3
        assert not cb.can_execute()  # Now open
        assert cb.state == "OPEN"

    def test_circuit_breaker_success_reset(self):
        """Test circuit breaker resets on success"""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)

        # Record some failures
        cb.record_failure()
        cb.record_failure()
        assert cb.failure_count == 2

        # Record success
        cb.record_success()
        assert cb.failure_count == 0
        assert cb.state == "CLOSED"

    def test_circuit_breaker_recovery_timeout(self):
        """Test circuit breaker recovery after timeout"""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0)  # 0 second timeout

        # Trip the breaker
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "OPEN"

        # With 0 timeout, should immediately allow execution (HALF_OPEN)
        import time
        time.sleep(0.01)  # Small delay to ensure timeout passes
        assert cb.can_execute()  # Should be HALF_OPEN now
        assert cb.state == "HALF_OPEN"


class TestPromptGenerator:
    """Test dynamic prompt generation"""

    def test_market_analysis_prompt_generation(self):
        """Test market analysis prompt generation"""
        generator = PromptGenerator()

        indicators = {
            "RSI": 65.5,
            "EMA_20": 45000,
            "MACD": 0.15
        }

        patterns = [
            {"name": "Bull Flag", "confidence": 0.85},
            {"name": "Support Level", "confidence": 0.72}
        ]

        prompt = generator.generate_market_analysis_prompt(
            symbol="BTCUSD",
            timeframe="1h",
            regime=MarketRegime.BULL,
            indicators=indicators,
            patterns=patterns,
            volatility=0.25
        )

        assert "BTCUSD" in prompt
        assert "1h" in prompt
        assert "bull" in prompt.lower()
        assert "RSI: 65.5" in prompt
        assert "Bull Flag: 0.85 confidence" in prompt
        assert "momentum continuation" in prompt  # Bull regime guidance

    def test_risk_assessment_prompt_generation(self):
        """Test risk assessment prompt generation"""
        generator = PromptGenerator()

        market_context = {"volatility": 0.3, "trend": "bullish"}
        portfolio_exposure = {"total_risk": 0.15, "correlation": 0.2}

        prompt = generator.generate_risk_assessment_prompt(
            symbol="ETHUSD",
            direction="LONG",
            entry_price=3500.0,
            stop_loss=3400.0,
            take_profit=3700.0,
            position_size=0.02,
            market_context=market_context,
            portfolio_exposure=portfolio_exposure
        )

        assert "ETHUSD" in prompt
        assert "LONG" in prompt
        assert "3500.0" in prompt
        assert "3400.0" in prompt
        assert "3700.0" in prompt
        assert "0.02" in prompt

    def test_regime_specific_guidance(self):
        """Test that different regimes produce different guidance"""
        generator = PromptGenerator()

        base_params = {
            "symbol": "BTCUSD",
            "timeframe": "1h",
            "indicators": {"RSI": 50},
            "patterns": [],
            "volatility": 0.2
        }

        bull_prompt = generator.generate_market_analysis_prompt(
            regime=MarketRegime.BULL, **base_params
        )
        bear_prompt = generator.generate_market_analysis_prompt(
            regime=MarketRegime.BEAR, **base_params
        )
        sideways_prompt = generator.generate_market_analysis_prompt(
            regime=MarketRegime.SIDEWAYS, **base_params
        )

        assert "momentum continuation" in bull_prompt
        assert "reversal patterns" in bear_prompt
        assert "range-bound trading" in sideways_prompt


class TestModelPerformanceTracker:
    """Test model performance tracking"""

    def test_performance_tracker_initialization(self):
        """Test performance tracker initializes correctly"""
        tracker = ModelPerformanceTracker()

        assert len(tracker.metrics) == 0
        assert len(tracker.performance_history) == 0

    def test_record_successful_request(self):
        """Test recording successful requests"""
        tracker = ModelPerformanceTracker()

        response = LLMResponse(
            content="Test response",
            model_id="test-model",
            tokens_used=100,
            latency_ms=500,
            cost_usd=0.01,
            confidence=0.85,
            success=True
        )

        tracker.record_request(response)

        assert "test-model" in tracker.metrics
        metrics = tracker.metrics["test-model"]
        assert metrics.total_requests == 1
        assert metrics.successful_requests == 1
        assert metrics.failed_requests == 0
        assert metrics.avg_latency_ms == 500
        assert metrics.avg_confidence == 0.85
        assert len(tracker.performance_history) == 1

    def test_record_failed_request(self):
        """Test recording failed requests"""
        tracker = ModelPerformanceTracker()

        response = LLMResponse(
            content="",
            model_id="test-model",
            tokens_used=0,
            latency_ms=1000,
            cost_usd=0.0,
            confidence=0.0,
            success=False,
            error_message="API timeout"
        )

        tracker.record_request(response)

        metrics = tracker.metrics["test-model"]
        assert metrics.total_requests == 1
        assert metrics.successful_requests == 0
        assert metrics.failed_requests == 1

    def test_model_scoring_accuracy_first(self):
        """Test model scoring with accuracy-first policy"""
        tracker = ModelPerformanceTracker()

        # Record successful request
        response = LLMResponse(
            content="Test",
            model_id="model-a",
            tokens_used=100,
            latency_ms=500,
            cost_usd=0.01,
            confidence=0.9,
            success=True
        )
        tracker.record_request(response)

        score = tracker.get_model_score("model-a", RoutingPolicy.ACCURACY_FIRST)
        assert score == 0.9  # success_rate (1.0) * confidence (0.9)

    def test_model_scoring_cost_aware(self):
        """Test model scoring with cost-aware policy"""
        tracker = ModelPerformanceTracker()

        response = LLMResponse(
            content="Test",
            model_id="model-b",
            tokens_used=100,
            latency_ms=500,
            cost_usd=0.01,
            confidence=0.8,
            success=True
        )
        tracker.record_request(response)

        score = tracker.get_model_score("model-b", RoutingPolicy.COST_AWARE)
        assert score > 0  # Should factor in cost efficiency

    def test_model_scoring_latency_aware(self):
        """Test model scoring with latency-aware policy"""
        tracker = ModelPerformanceTracker()

        response = LLMResponse(
            content="Test",
            model_id="model-c",
            tokens_used=100,
            latency_ms=200,  # Fast response
            cost_usd=0.01,
            confidence=0.8,
            success=True
        )
        tracker.record_request(response)

        score = tracker.get_model_score("model-c", RoutingPolicy.LATENCY_AWARE)
        assert score > 0  # Should factor in latency efficiency

    def test_get_best_model(self):
        """Test getting best model based on policy"""
        tracker = ModelPerformanceTracker()

        # Add performance data for multiple models
        models_data = [
            ("model-fast", 100, 0.8, 0.005),  # Fast, decent accuracy, cheap
            ("model-accurate", 500, 0.95, 0.02),  # Slow, very accurate, expensive
            ("model-cheap", 300, 0.7, 0.001)  # Medium speed, lower accuracy, very cheap
        ]

        for model_id, latency, confidence, cost in models_data:
            response = LLMResponse(
                content="Test",
                model_id=model_id,
                tokens_used=100,
                latency_ms=latency,
                cost_usd=cost,
                confidence=confidence,
                success=True
            )
            tracker.record_request(response)

        available_models = ["model-fast", "model-accurate", "model-cheap"]

        # Test different policies
        best_accuracy = tracker.get_best_model(RoutingPolicy.ACCURACY_FIRST, available_models)
        assert best_accuracy == "model-accurate"

        best_latency = tracker.get_best_model(RoutingPolicy.LATENCY_AWARE, available_models)
        assert best_latency == "model-fast"


class TestMultiLLMRouter:
    """Test the main multi-LLM router"""

    def test_router_initialization(self):
        """Test router initializes with configuration"""
        config = {
            "clients": {
                "claude": {
                    "enabled": True,
                    "api_key": "test-claude-key",
                    "model_version": "claude-3-sonnet-20240229"
                },
                "gemini": {
                    "enabled": True,
                    "api_key": "test-gemini-key",
                    "model_version": "gemini-1.5-pro"
                }
            }
        }

        router = MultiLLMRouter(config)

        assert len(router.clients) == 2
        assert len(router.circuit_breakers) == 2
        assert router.default_policy == RoutingPolicy.ACCURACY_FIRST

    def test_router_disabled_client(self):
        """Test router skips disabled clients"""
        config = {
            "clients": {
                "claude": {
                    "enabled": True,
                    "api_key": "test-claude-key"
                },
                "gemini": {
                    "enabled": False,  # Disabled
                    "api_key": "test-gemini-key"
                }
            }
        }

        router = MultiLLMRouter(config)

        assert len(router.clients) == 1  # Only Claude should be initialized
        claude_model_id = list(router.clients.keys())[0]
        assert "claude" in claude_model_id

    @pytest.mark.asyncio
    async def test_router_request_routing(self):
        """Test router routes requests correctly"""
        config = {
            "clients": {
                "claude": {
                    "enabled": True,
                    "api_key": "test-claude-key"
                }
            }
        }

        router = MultiLLMRouter(config)

        response = await router.route_request(
            prompt="Analyze BTCUSD market conditions",
            context={"symbol": "BTCUSD", "timeframe": "1h"}
        )

        assert response.success
        assert "claude" in response.model_id
        assert "BTCUSD" in response.content

    @pytest.mark.asyncio
    async def test_router_fallback_mechanism(self):
        """Test router fallback when primary model fails"""
        config = {
            "clients": {
                "claude": {
                    "enabled": True,
                    "api_key": "test-claude-key"
                },
                "gemini": {
                    "enabled": True,
                    "api_key": "test-gemini-key"
                }
            }
        }

        router = MultiLLMRouter(config)

        # Trip the circuit breaker for Claude
        claude_model_id = [k for k in router.clients.keys() if "claude" in k][0]
        for _ in range(5):  # Default failure threshold
            router.circuit_breakers[claude_model_id].record_failure()

        response = await router.route_request(
            prompt="Analyze ETHUSD",
            context={"symbol": "ETHUSD"}
        )

        # Should fallback to Gemini
        assert response.success
        assert "gemini" in response.model_id

    @pytest.mark.asyncio
    async def test_router_preferred_model(self):
        """Test router uses preferred model when specified"""
        config = {
            "clients": {
                "claude": {
                    "enabled": True,
                    "api_key": "test-claude-key"
                },
                "gemini": {
                    "enabled": True,
                    "api_key": "test-gemini-key"
                }
            }
        }

        router = MultiLLMRouter(config)
        gemini_model_id = [k for k in router.clients.keys() if "gemini" in k][0]

        response = await router.route_request(
            prompt="Analyze ADAUSD",
            context={"symbol": "ADAUSD"},
            preferred_model=gemini_model_id
        )

        assert response.success
        assert response.model_id == gemini_model_id

    def test_router_prompt_generation(self):
        """Test router prompt generation"""
        config = {
            "clients": {
                "claude": {
                    "enabled": True,
                    "api_key": "test-key"
                }
            }
        }

        router = MultiLLMRouter(config)

        prompt = router.generate_market_analysis_prompt(
            symbol="BTCUSD",
            timeframe="4h",
            regime=MarketRegime.BULL,
            indicators={"RSI": 70, "EMA_20": 45000},
            patterns=[{"name": "Breakout", "confidence": 0.8}],
            volatility=0.3
        )

        assert "BTCUSD" in prompt
        assert "4h" in prompt
        assert "bull" in prompt.lower()
        assert "RSI: 70" in prompt

    def test_router_performance_metrics(self):
        """Test router performance metrics retrieval"""
        config = {
            "clients": {
                "claude": {
                    "enabled": True,
                    "api_key": "test-key"
                }
            }
        }

        router = MultiLLMRouter(config)
        metrics = router.get_performance_metrics()

        assert isinstance(metrics, dict)
        # Should be empty initially
        assert len(metrics) == 0

    def test_router_cost_summary(self):
        """Test router cost summary"""
        config = {
            "clients": {
                "claude": {
                    "enabled": True,
                    "api_key": "test-key"
                }
            }
        }

        router = MultiLLMRouter(config)
        cost_summary = router.get_cost_summary(24)

        assert "time_window_hours" in cost_summary
        assert "total_cost_usd" in cost_summary
        assert "total_tokens" in cost_summary
        assert "cost_by_model" in cost_summary
        assert cost_summary["time_window_hours"] == 24

    def test_router_circuit_breaker_reset(self):
        """Test manual circuit breaker reset"""
        config = {
            "clients": {
                "claude": {
                    "enabled": True,
                    "api_key": "test-key"
                }
            }
        }

        router = MultiLLMRouter(config)
        claude_model_id = list(router.clients.keys())[0]

        # Trip the circuit breaker
        cb = router.circuit_breakers[claude_model_id]
        for _ in range(5):
            cb.record_failure()
        assert cb.state == "OPEN"

        # Reset it
        router.reset_circuit_breaker(claude_model_id)
        assert router.circuit_breakers[claude_model_id].state == "CLOSED"

    def test_router_policy_setting(self):
        """Test setting routing policy"""
        config = {
            "clients": {
                "claude": {
                    "enabled": True,
                    "api_key": "test-key"
                }
            }
        }

        router = MultiLLMRouter(config)
        assert router.default_policy == RoutingPolicy.ACCURACY_FIRST

        router.set_routing_policy(RoutingPolicy.COST_AWARE)
        assert router.default_policy == RoutingPolicy.COST_AWARE


@pytest.mark.asyncio
async def test_integration_full_workflow():
    """Test complete integration workflow"""
    config = {
        "clients": {
            "claude": {
                "enabled": True,
                "api_key": "test-claude-key"
            },
            "gemini": {
                "enabled": True,
                "api_key": "test-gemini-key"
            },
            "gpt4_turbo": {
                "enabled": True,
                "api_key": "test-gpt4-key"
            }
        }
    }

    router = MultiLLMRouter(config)

    # Test multiple requests to build performance history
    symbols = ["BTCUSD", "ETHUSD", "ADAUSD"]

    for symbol in symbols:
        # Generate prompt
        prompt = router.generate_market_analysis_prompt(
            symbol=symbol,
            timeframe="1h",
            regime=MarketRegime.BULL,
            indicators={"RSI": 65, "EMA_20": 45000},
            patterns=[{"name": "Bull Flag", "confidence": 0.8}],
            volatility=0.25
        )

        # Route request
        response = await router.route_request(
            prompt=prompt,
            context={"symbol": symbol, "timeframe": "1h"}
        )

        assert response.success
        assert symbol in response.content

    # Check that performance metrics were recorded
    metrics = router.get_performance_metrics()
    assert len(metrics) > 0

    # Check cost summary
    cost_summary = router.get_cost_summary(1)  # Last hour
    assert cost_summary["total_requests"] == 3
    assert cost_summary["total_cost_usd"] > 0


if __name__ == "__main__":
    pytest.main([__file__])
