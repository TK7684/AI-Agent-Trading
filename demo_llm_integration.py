#!/usr/bin/env python3
"""
Demo script for Multi-LLM Router and Integration System

This script demonstrates the capabilities of the multi-LLM router including:
- Multiple LLM client abstractions
- Intelligent routing policies
- Performance tracking and optimization
- Dynamic prompt generation
- Fallback mechanisms and error handling
- Token cost tracking
"""

import asyncio
import time

from libs.trading_models.llm_integration import (
    MarketRegime,
    MultiLLMRouter,
    RoutingPolicy,
)


async def demo_basic_routing():
    """Demonstrate basic LLM routing functionality"""
    print("=== Demo: Basic LLM Routing ===")

    # Configuration for multiple LLM providers
    config = {
        "clients": {
            "claude": {
                "enabled": True,
                "api_key": "demo-claude-key",
                "model_version": "claude-3-sonnet-20240229"
            },
            "gemini": {
                "enabled": True,
                "api_key": "demo-gemini-key",
                "model_version": "gemini-1.5-pro"
            },
            "gpt4_turbo": {
                "enabled": True,
                "api_key": "demo-gpt4-key",
                "model_version": "gpt-4-turbo-preview"
            },
            "mixtral": {
                "enabled": True,
                "api_key": "demo-mixtral-key",
                "model_version": "mixtral-8x7b-instruct"
            },
            "llama": {
                "enabled": True,
                "api_key": "demo-llama-key",
                "model_version": "llama-2-70b-chat"
            }
        }
    }

    # Initialize router
    router = MultiLLMRouter(config)
    print(f"Initialized router with {len(router.clients)} LLM clients:")
    for model_id in router.clients.keys():
        print(f"  - {model_id}")

    # Test basic routing
    print("\n--- Testing Basic Request Routing ---")

    response = await router.route_request(
        prompt="Analyze the current market conditions for Bitcoin",
        context={
            "symbol": "BTCUSD",
            "timeframe": "1h",
            "current_price": 45000
        }
    )

    print(f"Response from {response.model_id}:")
    print(f"  Content: {response.content}")
    print(f"  Tokens: {response.tokens_used}")
    print(f"  Latency: {response.latency_ms}ms")
    print(f"  Cost: ${response.cost_usd:.6f}")
    print(f"  Confidence: {response.confidence:.2f}")


async def demo_routing_policies():
    """Demonstrate different routing policies"""
    print("\n=== Demo: Routing Policies ===")

    config = {
        "clients": {
            "claude": {"enabled": True, "api_key": "demo-key"},
            "gemini": {"enabled": True, "api_key": "demo-key"},
            "gpt4_turbo": {"enabled": True, "api_key": "demo-key"}
        }
    }

    router = MultiLLMRouter(config)

    # Build some performance history first
    print("Building performance history...")
    for i in range(5):
        await router.route_request(
            f"Test request {i}",
            {"symbol": "BTCUSD"}
        )

    # Test different routing policies
    policies = [
        RoutingPolicy.ACCURACY_FIRST,
        RoutingPolicy.COST_AWARE,
        RoutingPolicy.LATENCY_AWARE
    ]

    for policy in policies:
        print(f"\n--- Testing {policy.value} Policy ---")

        response = await router.route_request(
            "Analyze Ethereum price action",
            {"symbol": "ETHUSD"},
            policy=policy
        )

        print(f"Selected model: {response.model_id}")
        print(f"Success: {response.success}")

        if response.success:
            print(f"Latency: {response.latency_ms}ms")
            print(f"Cost: ${response.cost_usd:.6f}")


async def demo_prompt_generation():
    """Demonstrate dynamic prompt generation"""
    print("\n=== Demo: Dynamic Prompt Generation ===")

    config = {
        "clients": {
            "claude": {"enabled": True, "api_key": "demo-key"}
        }
    }

    router = MultiLLMRouter(config)

    # Sample market data
    indicators = {
        "RSI": 68.5,
        "EMA_20": 44500,
        "EMA_50": 43800,
        "MACD": 0.15,
        "Bollinger_Upper": 45200,
        "Bollinger_Lower": 43500,
        "ATR": 850,
        "Volume_Profile": "High at 44800"
    }

    patterns = [
        {"name": "Bull Flag", "confidence": 0.82},
        {"name": "Support Level", "confidence": 0.75},
        {"name": "Volume Breakout", "confidence": 0.68}
    ]

    # Test different market regimes
    regimes = [
        MarketRegime.BULL,
        MarketRegime.BEAR,
        MarketRegime.SIDEWAYS,
        MarketRegime.HIGH_VOLATILITY
    ]

    for regime in regimes:
        print(f"\n--- {regime.value.upper()} Market Regime ---")

        prompt = router.generate_market_analysis_prompt(
            symbol="BTCUSD",
            timeframe="4h",
            regime=regime,
            indicators=indicators,
            patterns=patterns,
            volatility=0.28
        )

        print("Generated prompt preview:")
        print(prompt[:200] + "..." if len(prompt) > 200 else prompt)

        # Get LLM analysis
        response = await router.route_request(prompt, {
            "symbol": "BTCUSD",
            "regime": regime.value
        })

        print(f"LLM Response: {response.content}")


async def demo_fallback_mechanisms():
    """Demonstrate fallback mechanisms and error handling"""
    print("\n=== Demo: Fallback Mechanisms ===")

    config = {
        "clients": {
            "claude": {"enabled": True, "api_key": "demo-key"},
            "gemini": {"enabled": True, "api_key": "demo-key"},
            "mixtral": {"enabled": True, "api_key": "demo-key"}
        }
    }

    router = MultiLLMRouter(config)

    # Get model IDs
    model_ids = list(router.clients.keys())
    primary_model = model_ids[0]

    print(f"Primary model: {primary_model}")
    print(f"Available fallback models: {model_ids[1:]}")

    # Simulate primary model failure by tripping circuit breaker
    print(f"\nSimulating failures for {primary_model}...")
    cb = router.circuit_breakers[primary_model]

    for i in range(5):  # Trip the circuit breaker
        cb.record_failure()
        print(f"  Failure {i+1}/5 recorded")

    print(f"Circuit breaker state: {cb.state}")
    print(f"Can execute: {cb.can_execute()}")

    # Now try to route a request - should fallback
    print("\nRouting request with primary model unavailable...")

    response = await router.route_request(
        "Analyze market conditions despite primary model failure",
        {"symbol": "ETHUSD"},
        preferred_model=primary_model  # Try to use failed model
    )

    print(f"Request routed to: {response.model_id}")
    print(f"Success: {response.success}")
    print(f"Used fallback: {response.model_id != primary_model}")

    # Reset circuit breaker
    print(f"\nResetting circuit breaker for {primary_model}")
    router.reset_circuit_breaker(primary_model)
    print(f"Circuit breaker state: {router.circuit_breakers[primary_model].state}")


async def demo_performance_tracking():
    """Demonstrate performance tracking and optimization"""
    print("\n=== Demo: Performance Tracking ===")

    config = {
        "clients": {
            "claude": {"enabled": True, "api_key": "demo-key"},
            "gemini": {"enabled": True, "api_key": "demo-key"},
            "gpt4_turbo": {"enabled": True, "api_key": "demo-key"}
        }
    }

    router = MultiLLMRouter(config)

    # Generate multiple requests to build performance history
    print("Generating requests to build performance history...")

    symbols = ["BTCUSD", "ETHUSD", "ADAUSD", "SOLUSD", "DOTUSD"]

    for i, symbol in enumerate(symbols):
        print(f"  Request {i+1}/{len(symbols)}: {symbol}")

        response = await router.route_request(
            f"Analyze {symbol} market conditions",
            {"symbol": symbol, "timeframe": "1h"}
        )

        print(f"    Routed to: {response.model_id}")
        print(f"    Latency: {response.latency_ms}ms")
        print(f"    Cost: ${response.cost_usd:.6f}")

    # Display performance metrics
    print("\n--- Performance Metrics ---")
    metrics = router.get_performance_metrics()

    for model_id, model_metrics in metrics.items():
        print(f"\n{model_id}:")
        print(f"  Total requests: {model_metrics.total_requests}")
        print(f"  Success rate: {model_metrics.successful_requests/model_metrics.total_requests:.2%}")
        print(f"  Avg latency: {model_metrics.avg_latency_ms:.1f}ms")
        print(f"  Avg confidence: {model_metrics.avg_confidence:.2f}")
        print(f"  Avg cost/token: ${model_metrics.avg_cost_per_token:.8f}")

    # Display cost summary
    print("\n--- Cost Summary (Last Hour) ---")
    cost_summary = router.get_cost_summary(1)

    print(f"Total requests: {cost_summary['total_requests']}")
    print(f"Total cost: ${cost_summary['total_cost_usd']:.6f}")
    print(f"Total tokens: {cost_summary['total_tokens']:,}")
    print(f"Avg cost per token: ${cost_summary['avg_cost_per_token']:.8f}")

    print("\nCost by model:")
    for model_id, cost in cost_summary['cost_by_model'].items():
        tokens = cost_summary['tokens_by_model'][model_id]
        print(f"  {model_id}: ${cost:.6f} ({tokens:,} tokens)")


async def demo_token_optimization():
    """Demonstrate token cost tracking and optimization"""
    print("\n=== Demo: Token Cost Optimization ===")

    config = {
        "clients": {
            "claude": {"enabled": True, "api_key": "demo-key"},
            "gemini": {"enabled": True, "api_key": "demo-key"},
            "mixtral": {"enabled": True, "api_key": "demo-key"}  # Cheapest model
        }
    }

    router = MultiLLMRouter(config)

    # Test cost-aware routing
    print("Testing cost-aware routing...")

    # Build some history first
    for i in range(3):
        await router.route_request(f"Test {i}", {"test": True})

    # Set cost-aware policy
    router.set_routing_policy(RoutingPolicy.COST_AWARE)

    # Make several requests
    total_cost_before = 0
    total_cost_after = 0

    for i in range(5):
        response = await router.route_request(
            f"Cost-optimized analysis request {i}",
            {"symbol": "BTCUSD", "optimization": "cost"}
        )

        total_cost_after += response.cost_usd
        print(f"  Request {i+1}: {response.model_id} - ${response.cost_usd:.6f}")

    print(f"\nTotal cost with cost-aware routing: ${total_cost_after:.6f}")

    # Compare with accuracy-first routing
    print("\nComparing with accuracy-first routing...")
    router.set_routing_policy(RoutingPolicy.ACCURACY_FIRST)

    for i in range(5):
        response = await router.route_request(
            f"Accuracy-first analysis request {i}",
            {"symbol": "BTCUSD", "optimization": "accuracy"}
        )

        total_cost_before += response.cost_usd
        print(f"  Request {i+1}: {response.model_id} - ${response.cost_usd:.6f}")

    print(f"\nTotal cost with accuracy-first routing: ${total_cost_before:.6f}")
    print(f"Cost savings: ${total_cost_before - total_cost_after:.6f} ({((total_cost_before - total_cost_after) / total_cost_before * 100):.1f}%)")


async def demo_real_world_scenario():
    """Demonstrate real-world trading scenario"""
    print("\n=== Demo: Real-World Trading Scenario ===")

    config = {
        "clients": {
            "claude": {"enabled": True, "api_key": "demo-key"},
            "gemini": {"enabled": True, "api_key": "demo-key"},
            "gpt4_turbo": {"enabled": True, "api_key": "demo-key"}
        }
    }

    router = MultiLLMRouter(config)

    # Simulate real market analysis scenario
    print("Simulating real-time market analysis...")

    # Market data snapshot
    market_data = {
        "symbol": "BTCUSD",
        "current_price": 44750,
        "24h_change": 2.3,
        "volume": 28500000000,
        "market_cap": 875000000000
    }

    indicators = {
        "RSI_14": 62.5,
        "EMA_20": 44200,
        "EMA_50": 43100,
        "EMA_200": 41800,
        "MACD": 0.12,
        "MACD_Signal": 0.08,
        "BB_Upper": 45500,
        "BB_Lower": 42900,
        "ATR_14": 920,
        "Stoch_K": 68,
        "Stoch_D": 65
    }

    patterns = [
        {"name": "Ascending Triangle", "confidence": 0.78, "timeframe": "4h"},
        {"name": "Support Retest", "confidence": 0.85, "timeframe": "1h"},
        {"name": "Volume Breakout", "confidence": 0.72, "timeframe": "15m"}
    ]

    # Generate comprehensive analysis prompt
    prompt = router.generate_market_analysis_prompt(
        symbol=market_data["symbol"],
        timeframe="1h",
        regime=MarketRegime.BULL,
        indicators=indicators,
        patterns=patterns,
        volatility=0.32
    )

    print("Generated analysis prompt (first 300 chars):")
    print(prompt[:300] + "...")

    # Route to best model for accuracy
    print("\nRouting to best model for market analysis...")

    start_time = time.time()
    response = await router.route_request(
        prompt,
        {
            "symbol": market_data["symbol"],
            "analysis_type": "comprehensive",
            "market_data": market_data,
            "priority": "accuracy"
        },
        policy=RoutingPolicy.ACCURACY_FIRST
    )

    analysis_time = time.time() - start_time

    print(f"Analysis completed in {analysis_time:.2f} seconds")
    print(f"Model used: {response.model_id}")
    print(f"Confidence: {response.confidence:.2f}")
    print(f"Cost: ${response.cost_usd:.6f}")
    print(f"Tokens: {response.tokens_used}")

    print("\nLLM Analysis Result:")
    print(response.content)

    # Generate risk assessment
    print("\n--- Risk Assessment ---")

    risk_prompt = router.prompt_generator.generate_risk_assessment_prompt(
        symbol=market_data["symbol"],
        direction="LONG",
        entry_price=44750,
        stop_loss=43800,
        take_profit=46200,
        position_size=0.02,
        market_context={"volatility": 0.32, "trend": "bullish"},
        portfolio_exposure={"total_risk": 0.12, "btc_exposure": 0.08}
    )

    risk_response = await router.route_request(
        risk_prompt,
        {"analysis_type": "risk_assessment"},
        policy=RoutingPolicy.ACCURACY_FIRST
    )

    print(f"Risk assessment from {risk_response.model_id}:")
    print(risk_response.content)

    # Final performance summary
    print("\n--- Session Performance Summary ---")
    final_metrics = router.get_performance_metrics()
    final_costs = router.get_cost_summary(1)

    print(f"Total requests processed: {final_costs['total_requests']}")
    print(f"Total cost: ${final_costs['total_cost_usd']:.6f}")
    print(f"Average latency: {sum(m.avg_latency_ms for m in final_metrics.values()) / len(final_metrics):.1f}ms")
    print(f"Overall success rate: {sum(m.successful_requests for m in final_metrics.values()) / sum(m.total_requests for m in final_metrics.values()):.2%}")


async def main():
    """Run all demos"""
    print("Multi-LLM Router Integration System Demo")
    print("=" * 50)

    demos = [
        demo_basic_routing,
        demo_routing_policies,
        demo_prompt_generation,
        demo_fallback_mechanisms,
        demo_performance_tracking,
        demo_token_optimization,
        demo_real_world_scenario
    ]

    for demo in demos:
        try:
            await demo()
            print("\n" + "─" * 50)
            await asyncio.sleep(0.5)  # Brief pause between demos
        except Exception as e:
            print(f"Error in {demo.__name__}: {e}")
            continue

    print("\nDemo completed successfully!")
    print("The Multi-LLM Router system is ready for integration.")


if __name__ == "__main__":
    asyncio.run(main())
