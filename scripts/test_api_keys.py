#!/usr/bin/env python3
"""
API Key Testing Script
Tests OpenAI and Gemini API connectivity and functionality.
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

try:
    from auto_trading_system.api.llm_client import LLMProvider, TradingAnalyzer
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the AI Agent Trading directory")
    sys.exit(1)


def load_env_vars():
    """Load environment variables from .env file"""
    try:
        from dotenv import load_dotenv

        load_dotenv()
        return True
    except ImportError:
        print("⚠️  python-dotenv not installed, using system environment")
        return False


def check_api_keys():
    """Check if API keys are present"""
    openai_key = os.getenv("OPENAI_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")

    print("🔑 API Key Status:")
    print(f"   OpenAI: {'✅ Found' if openai_key else '❌ Missing'}")
    print(f"   Gemini: {'✅ Found' if gemini_key else '❌ Missing'}")
    print()

    if not openai_key and not gemini_key:
        print("❌ No API keys found!")
        print("Please set your API keys in the .env file:")
        print("   OPENAI_API_KEY=your_openai_key_here")
        print("   GEMINI_API_KEY=your_gemini_key_here")
        return False, None

    return True, {"openai": openai_key, "gemini": gemini_key}


async def test_openai_api(api_key: str) -> dict:
    """Test OpenAI API connectivity"""
    print("🧠 Testing OpenAI API...")

    try:
        provider = LLMProvider(openai_api_key=api_key, gemini_api_key="")

        # Test with a simple trading analysis prompt
        result = await provider.call_openai(
            prompt="Analyze BTCUSDT at $45,000 with RSI 45. Provide BUY/SELL/HOLD signal.",
            model="gpt-4",
            temperature=0.3,
            max_tokens=100,
        )

        if result["success"]:
            print(f"   ✅ OpenAI API working!")
            print(f"   📊 Response: {json.dumps(result['content'], indent=6)}")
            print(f"   ⚡ Latency: {result['latency_ms']}ms")
            print(f"   🔢 Tokens used: {result['tokens_used']}")
            return {"status": "success", "result": result}
        else:
            print(f"   ❌ OpenAI API error: {result['error']}")
            return {"status": "error", "error": result["error"]}

    except Exception as e:
        print(f"   ❌ OpenAI API test failed: {e}")
        return {"status": "error", "error": str(e)}


async def test_gemini_api(api_key: str) -> dict:
    """Test Gemini API connectivity"""
    print("🪐 Testing Gemini API...")

    try:
        provider = LLMProvider(openai_api_key="", gemini_api_key=api_key)

        # Test with a simple trading analysis prompt
        result = await provider.call_gemini(
            prompt="Analyze ETHUSDT at $2,500 with MACD positive. Provide BUY/SELL/HOLD signal.",
            model="gemini-1.5-pro",
            temperature=0.3,
            max_tokens=100,
        )

        if result["success"]:
            print(f"   ✅ Gemini API working!")
            print(f"   📊 Response: {json.dumps(result['content'], indent=6)}")
            print(f"   ⚡ Latency: {result['latency_ms']}ms")
            print(f"   🔢 Tokens used: {result['tokens_used']}")
            return {"status": "success", "result": result}
        else:
            print(f"   ❌ Gemini API error: {result['error']}")
            return {"status": "error", "error": result["error"]}

    except Exception as e:
        print(f"   ❌ Gemini API test failed: {e}")
        return {"status": "error", "error": str(e)}


async def test_trading_analysis(provider: LLMProvider) -> dict:
    """Test full trading analysis workflow"""
    print("📈 Testing Trading Analysis...")

    try:
        analyzer = TradingAnalyzer(provider)

        # Test market conditions analysis
        market_data = {
            "symbol": "BTCUSDT",
            "price": 45000.0,
            "volume": 5000000,
            "change_24h": 2.5,
            "rsi": 55.0,
            "macd": 0.02,
            "bb_upper": 46000,
            "bb_lower": 44000,
            "bb_middle": 45000,
            "volume_ma": 4500000,
            "volatility": 0.025,
            "trend_strength": 0.3,
        }

        result = await provider.get_trading_signal("BTCUSDT", market_data, "openai")

        if result["success"]:
            print(f"   ✅ Trading analysis working!")
            print(f"   📊 Signal: {result['content'].get('signal', 'N/A')}")
            print(f"   🎯 Confidence: {result['content'].get('confidence', 'N/A')}")
            print(f"   💰 Entry: ${result['content'].get('entry_price', 'N/A')}")
            print(f"   🛡️  Stop Loss: ${result['content'].get('stop_loss', 'N/A')}")
            print(f"   🎯 Take Profit: ${result['content'].get('take_profit', 'N/A')}")
            return {"status": "success", "result": result}
        else:
            print(f"   ❌ Trading analysis error: {result['error']}")
            return {"status": "error", "error": result["error"]}

    except Exception as e:
        print(f"   ❌ Trading analysis test failed: {e}")
        return {"status": "error", "error": str(e)}


async def test_provider_comparison(provider: LLMProvider) -> dict:
    """Test comparison between providers"""
    print("🔄 Testing Provider Comparison...")

    try:
        market_data = {
            "symbol": "ETHUSDT",
            "price": 2500.0,
            "volume": 3000000,
            "change_24h": -1.2,
            "rsi": 35.0,
            "macd": -0.01,
            "bb_upper": 2600,
            "bb_lower": 2400,
            "bb_middle": 2500,
            "volume_ma": 2800000,
            "volatility": 0.030,
            "trend_strength": 0.2,
        }

        result = await provider.compare_providers("ETHUSDT", market_data)

        print(f"   ✅ Provider comparison working!")
        print(f"   📊 Consensus Signal: {result.get('consensus_signal', 'N/A')}")
        print(
            f"   🎯 Consensus Confidence: {result.get('consensus_confidence', 'N/A')}"
        )
        print(f"   🤝 Signal Agreement: {result.get('signal_agreement', 'N/A')}")

        return {"status": "success", "result": result}

    except Exception as e:
        print(f"   ❌ Provider comparison test failed: {e}")
        return {"status": "error", "error": str(e)}


async def main():
    """Main test function"""
    print("=" * 80)
    print("🚀 AI TRADING SYSTEM - API KEY TESTER")
    print("=" * 80)
    print()

    # Load environment variables
    load_env_vars()

    # Check API keys
    keys_ok, api_keys = check_api_keys()
    if not keys_ok:
        print("\n❌ Cannot proceed without API keys")
        return

    print("🧪 Starting API Tests...")
    print("=" * 50)

    test_results = {}

    # Test OpenAI if key available
    if api_keys.get("openai"):
        test_results["openai"] = await test_openai_api(api_keys["openai"])
        print()

    # Test Gemini if key available
    if api_keys.get("gemini"):
        test_results["gemini"] = await test_gemini_api(api_keys["gemini"])
        print()

    # Test with both providers if both are available
    if api_keys.get("openai") and api_keys.get("gemini"):
        print("🔗 Testing with both providers...")
        provider = LLMProvider(
            openai_api_key=api_keys["openai"], gemini_api_key=api_keys["gemini"]
        )

        test_results["trading_analysis"] = await test_trading_analysis(provider)
        print()

        test_results["provider_comparison"] = await test_provider_comparison(provider)
        print()

    # Final results
    print("=" * 80)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 80)

    success_count = 0
    total_tests = 0

    for test_name, result in test_results.items():
        total_tests += 1
        if result["status"] == "success":
            success_count += 1
            print(f"✅ {test_name.upper()}: PASSED")
        else:
            print(f"❌ {test_name.upper()}: FAILED")
            print(f"   Error: {result.get('error', 'Unknown error')}")

    print()
    print(f"🎯 Overall Result: {success_count}/{total_tests} tests passed")

    if success_count == total_tests:
        print("🎉 ALL TESTS PASSED! Your system is ready for trading!")
        print("💡 You can now run: python scripts/start_system.bat")
    elif success_count > 0:
        print("⚠️  Some tests passed. You can run in limited mode.")
        print("💡 Consider fixing failed tests for full functionality.")
    else:
        print("❌ All tests failed. Please check your API keys and configuration.")

    print()
    print("=" * 80)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Test cancelled by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback

        traceback.print_exc()
