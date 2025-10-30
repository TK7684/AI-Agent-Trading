#!/usr/bin/env python3
"""
Test Poe API Integration for AI Trading Agent
"""

import asyncio
import os
import sys
from datetime import datetime

# Add the libs directory to the path
sys.path.append('libs')

# Load environment variables from .env.poe
def load_poe_env():
    """Load Poe environment variables."""
    env_file = '.env.poe'
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
        print("✅ Poe environment variables loaded")
    else:
        print("❌ .env.poe file not found")

# Load environment
load_poe_env()

# Import our Poe integration
try:
    from POE_PRACTICAL_INTEGRATION import (
        PoeAIClient,
        PoeModel,
        PoeMultiModelConsensus,
        get_poe_trading_analysis,
    )
    print("✅ Poe integration modules imported successfully")
except ImportError as e:
    print(f"❌ Failed to import Poe integration: {e}")
    sys.exit(1)

async def test_basic_connection():
    """Test basic Poe API connection."""
    print("\n🔍 Testing Basic Poe API Connection...")
    print("=" * 50)

    api_key = os.getenv('POE_API_KEY')
    if not api_key:
        print("❌ POE_API_KEY not found in environment")
        return False

    print(f"✅ API Key loaded: {api_key[:20]}...{api_key[-10:]}")

    try:
        async with PoeAIClient(api_key) as client:
            # Simple test prompt
            response = await client.analyze_market(
                "Test connection: What is 2+2?",
                model=PoeModel.FAST_ANALYSIS,
                max_tokens=50
            )

            if response.success:
                print("✅ Connection successful!")
                print(f"   Model: {response.model}")
                print(f"   Response: {response.content[:100]}...")
                print(f"   Points used: {response.points_used}")
                print(f"   Response time: {response.response_time_ms}ms")
                print(f"   Confidence: {response.confidence_score:.2f}")
                return True
            else:
                print(f"❌ Connection failed: {response.error}")
                return False

    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False

async def test_trading_analysis():
    """Test trading-specific analysis."""
    print("\n📊 Testing Trading Analysis...")
    print("=" * 50)

    # Sample market data for EURUSD
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

    print(f"📈 Analyzing {market_data['symbol']} on {market_data['timeframe']} timeframe")
    print(f"   Current Price: {market_data['current_price']}")
    print(f"   RSI: {market_data['rsi']}")
    print(f"   MACD: {market_data['macd']}")
    print(f"   Volume: {market_data['volume']}")

    try:
        analysis = await get_poe_trading_analysis(
            market_data['symbol'],
            market_data,
            'quick'  # Start with quick analysis to save points
        )

        if analysis:
            print("\n✅ Analysis completed successfully!")
            print(f"   Consensus Action: {analysis['consensus_action']}")
            print(f"   Consensus Sentiment: {analysis['consensus_sentiment']}")
            print(f"   Confidence: {analysis['consensus_confidence']}%")
            print(f"   Agreement Level: {analysis['action_agreement']}")
            print(f"   Models Consulted: {analysis['models_consulted']}")
            print(f"   Points Used: {analysis['total_points_used']}")
            print(f"   Recommendation Strength: {analysis['recommendation_strength']}")
            print(f"   Reasoning: {analysis['reasoning'][:150]}...")

            # Show individual model analyses
            if analysis.get('model_analyses'):
                print("\n🤖 Individual Model Results:")
                for i, model_analysis in enumerate(analysis['model_analyses'][:3]):  # Show first 3
                    print(f"   Model {i+1}: {model_analysis['model']}")
                    print(f"   Action: {model_analysis['action']}")
                    print(f"   Confidence: {model_analysis['confidence']}%")
                    print(f"   Points: {model_analysis['points_used']}")

            return True
        else:
            print("❌ Analysis failed - no results returned")
            return False

    except Exception as e:
        print(f"❌ Trading analysis failed: {e}")
        return False

async def test_multi_model_consensus():
    """Test multi-model consensus analysis."""
    print("\n🧠 Testing Multi-Model Consensus...")
    print("=" * 50)

    market_data = {
        'symbol': 'BTCUSD',
        'timeframe': '4h',
        'current_price': 45000,
        'rsi': 65.8,
        'macd': 'bearish_divergence',
        'volume': 'declining',
        'trend': 'sideways',
        'support': 44500,
        'resistance': 46000
    }

    print(f"🪙 Analyzing {market_data['symbol']} for consensus decision")

    try:
        consensus_analyzer = PoeMultiModelConsensus()
        analysis = await consensus_analyzer.get_trading_consensus(
            market_data,
            analysis_type='full'  # Full consensus analysis
        )

        if analysis:
            print("\n✅ Multi-model consensus completed!")
            print(f"   Final Recommendation: {analysis['consensus_action']}")
            print(f"   Sentiment: {analysis['consensus_sentiment']}")
            print(f"   Confidence: {analysis['consensus_confidence']}%")
            print(f"   Sentiment Agreement: {analysis['sentiment_agreement']}")
            print(f"   Action Agreement: {analysis['action_agreement']}")
            print(f"   Strength: {analysis['recommendation_strength']}")
            print(f"   Total Points: {analysis['total_points_used']}")
            print(f"   Models Used: {analysis['models_consulted']}")

            return True
        else:
            print("❌ Consensus analysis failed")
            return False

    except Exception as e:
        print(f"❌ Consensus test failed: {e}")
        return False

async def test_points_management():
    """Test points usage tracking and management."""
    print("\n💰 Testing Points Management...")
    print("=" * 50)

    try:
        async with PoeAIClient() as client:
            # Check initial usage stats
            initial_stats = client.get_usage_summary()
            print("📊 Usage Statistics:")
            print(f"   Points used today: {initial_stats['points_used_today']}")
            print(f"   Points remaining: {initial_stats['points_remaining']}")
            print(f"   Requests last hour: {initial_stats['requests_last_hour']}")
            print(f"   Success rate: {initial_stats['success_rate']:.1%}")
            print(f"   Avg response time: {initial_stats['average_response_time']:.0f}ms")

            # Test points estimation
            estimated_cost = client.points_manager.estimate_cost(PoeModel.CLAUDE_3_5_SONNET, 1)
            print("\n💡 Cost Estimation:")
            print(f"   Claude 3.5 Sonnet: ~{estimated_cost} points per request")

            can_afford = client.points_manager.can_afford(PoeModel.CLAUDE_3_5_SONNET, 10)
            print(f"   Can afford 10 requests: {can_afford}")

            # Test model suggestion
            suggested = client.points_manager.suggest_model(PoeModel.O1_PREVIEW)
            print(f"   Suggested model for o1-preview: {suggested.value}")

            return True

    except Exception as e:
        print(f"❌ Points management test failed: {e}")
        return False

async def run_comprehensive_test():
    """Run comprehensive test suite."""
    print("🚀 POE API INTEGRATION TEST SUITE")
    print("=" * 60)
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    tests = [
        ("Basic Connection", test_basic_connection),
        ("Trading Analysis", test_trading_analysis),
        ("Multi-Model Consensus", test_multi_model_consensus),
        ("Points Management", test_points_management)
    ]

    results = {}

    for test_name, test_func in tests:
        try:
            print(f"\n🧪 Running: {test_name}")
            result = await test_func()
            results[test_name] = result

            if result:
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")

        except Exception as e:
            print(f"💥 {test_name}: ERROR - {e}")
            results[test_name] = False

    # Summary
    print("\n" + "=" * 60)
    print("📋 TEST RESULTS SUMMARY")
    print("=" * 60)

    passed = sum(1 for result in results.values() if result)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")

    print(f"\n🏆 Overall: {passed}/{total} tests passed ({passed/total*100:.0f}%)")

    if passed == total:
        print("🎉 ALL TESTS PASSED! Your Poe integration is ready for trading!")
        print("\n🚀 Next steps:")
        print("   1. Update your main trading system to use Poe")
        print("   2. Start with paper trading to validate")
        print("   3. Monitor points usage and optimize")
        print("   4. Scale up to live trading when confident")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        print("   - Verify your API key is correct")
        print("   - Check your internet connection")
        print("   - Ensure you have Poe subscription active")

    print(f"\n⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return passed == total

if __name__ == "__main__":
    try:
        success = asyncio.run(run_comprehensive_test())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)

