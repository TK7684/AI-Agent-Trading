#!/usr/bin/env python3
"""
Test New Poe API Key
Updated format - let's see if this one works!
"""

import asyncio
import json
from datetime import datetime

import aiohttp

# Your updated Poe API key
POE_API_KEY = "YtE8ejRowwXJI4O1h.wTLBfVWZDzyRXByhei3tWXaqs-1758274795-1.0.1.1-JT23ROAcW9m81vcLzW9Ft9z80QUV7otJzKot1_iFDkMiThFgMUnkY1zCxd3z5ByIEkUQG4VvF3UOyalwGf0UiaBhZvmyKlyXSGfGDcSGvCA"

async def test_poe_api_comprehensive():
    """Comprehensive test of the new Poe API key."""
    print("🔑 TESTING NEW POE API KEY")
    print("=" * 50)
    print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔑 New API Key: {POE_API_KEY[:30]}...{POE_API_KEY[-20:]}")
    print()

    # Test different endpoint patterns based on research
    test_scenarios = [
        {
            "name": "Poe Creator API v1",
            "url": "https://api.poe.com/v1/bot/chat",
            "headers": {
                "Authorization": f"Bearer {POE_API_KEY}",
                "Content-Type": "application/json"
            },
            "payload": {
                "model": "Claude-3.5-Sonnet",
                "messages": [
                    {"role": "user", "content": "Hello! Please respond with 'API TEST SUCCESS' if you can see this message."}
                ],
                "stream": False
            }
        },
        {
            "name": "Poe Creator API v2",
            "url": "https://api.poe.com/v2/chat",
            "headers": {
                "Authorization": f"Bearer {POE_API_KEY}",
                "Content-Type": "application/json"
            },
            "payload": {
                "bot": "Claude-3.5-Sonnet",
                "query": "Hello! Please respond with 'API TEST SUCCESS' if you can see this message."
            }
        },
        {
            "name": "OpenAI Compatible Format",
            "url": "https://api.poe.com/v1/chat/completions",
            "headers": {
                "Authorization": f"Bearer {POE_API_KEY}",
                "Content-Type": "application/json"
            },
            "payload": {
                "model": "Claude-3.5-Sonnet",
                "messages": [
                    {"role": "user", "content": "Hello! Please respond with 'API TEST SUCCESS' if you can see this message."}
                ],
                "max_tokens": 50,
                "temperature": 0.1
            }
        },
        {
            "name": "Poe Bot Endpoint",
            "url": "https://api.poe.com/bot/Claude-3.5-Sonnet",
            "headers": {
                "Authorization": f"Bearer {POE_API_KEY}",
                "Content-Type": "application/json"
            },
            "payload": {
                "query": "Hello! Please respond with 'API TEST SUCCESS' if you can see this message.",
                "user_id": "test_user"
            }
        },
        {
            "name": "Alternative Auth Format",
            "url": "https://api.poe.com/v1/bot/chat",
            "headers": {
                "Poe-Api-Key": POE_API_KEY,
                "Content-Type": "application/json"
            },
            "payload": {
                "model": "Claude-3.5-Sonnet",
                "messages": [
                    {"role": "user", "content": "Hello! Please respond with 'API TEST SUCCESS' if you can see this message."}
                ]
            }
        }
    ]

    success_count = 0

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
        for i, scenario in enumerate(test_scenarios, 1):
            print(f"🧪 Test {i}: {scenario['name']}")
            print(f"   URL: {scenario['url']}")

            try:
                async with session.post(
                    scenario['url'],
                    headers=scenario['headers'],
                    json=scenario['payload']
                ) as response:

                    print(f"   Status: {response.status}")

                    if response.status == 200:
                        try:
                            data = await response.json()
                            print("   ✅ SUCCESS! Response received:")
                            print(f"   📝 Data: {json.dumps(data, indent=2)[:300]}...")
                            success_count += 1

                            # Try to extract the actual response content
                            if 'choices' in data and len(data['choices']) > 0:
                                content = data['choices'][0].get('message', {}).get('content', '')
                                print(f"   💬 AI Response: {content}")
                            elif 'text' in data:
                                print(f"   💬 AI Response: {data['text']}")
                            elif 'response' in data:
                                print(f"   💬 AI Response: {data['response']}")

                            return True  # Found working endpoint!

                        except json.JSONDecodeError:
                            text = await response.text()
                            print(f"   ✅ SUCCESS! Raw text: {text[:200]}...")
                            success_count += 1
                            return True

                    elif response.status == 401:
                        error_text = await response.text()
                        print(f"   🔐 Authentication Error: {error_text[:150]}...")

                    elif response.status == 403:
                        print("   🚫 Forbidden - API access may not be enabled")

                    elif response.status == 404:
                        print("   🔍 Not Found - Endpoint doesn't exist")

                    elif response.status == 429:
                        print("   ⏳ Rate Limited - Too many requests")

                    elif response.status >= 500:
                        print("   🔥 Server Error - Poe API having issues")

                    else:
                        error_text = await response.text()
                        print(f"   ❌ Error {response.status}: {error_text[:150]}...")

            except asyncio.TimeoutError:
                print("   ⏰ Timeout - Request took too long")
            except Exception as e:
                print(f"   💥 Exception: {str(e)[:100]}...")

            print()

    print(f"📊 Results: {success_count}/{len(test_scenarios)} tests successful")

    if success_count == 0:
        await test_alternative_approaches()

    return success_count > 0

async def test_alternative_approaches():
    """Test alternative approaches and provide guidance."""
    print("🔄 TESTING ALTERNATIVE APPROACHES")
    print("=" * 40)

    # Try different base URLs
    alternative_bases = [
        "https://poe.com/api/",
        "https://api.poe.ai/",
        "https://creator.poe.com/api/",
        "https://bot.poe.com/api/"
    ]

    simple_payload = {"message": "test", "bot": "Claude-3.5-Sonnet"}

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
        for base_url in alternative_bases:
            print(f"🌐 Testing base URL: {base_url}")

            try:
                headers = {
                    "Authorization": f"Bearer {POE_API_KEY}",
                    "Content-Type": "application/json"
                }

                async with session.post(
                    f"{base_url}chat",
                    headers=headers,
                    json=simple_payload
                ) as response:

                    print(f"   Status: {response.status}")
                    if response.status == 200:
                        data = await response.text()
                        print(f"   ✅ Success! Response: {data[:100]}...")
                        return True
                    else:
                        error = await response.text()
                        print(f"   Response: {error[:100]}...")

            except Exception as e:
                print(f"   Error: {str(e)[:50]}...")

            print()

    return False

async def provide_guidance():
    """Provide guidance based on test results."""
    print("💡 GUIDANCE AND NEXT STEPS")
    print("=" * 40)

    print("🔍 API Key Analysis:")
    print(f"   Format: {POE_API_KEY[:10]}...{POE_API_KEY[-10:]}")
    print(f"   Length: {len(POE_API_KEY)} characters")
    print("   Pattern: Contains periods and dashes (good sign)")
    print()

    print("📋 Possible Issues & Solutions:")
    print()

    print("1. 🔐 API Key Verification:")
    print("   ✓ Check if key is active in Poe settings")
    print("   ✓ Verify subscription includes API access")
    print("   ✓ Ensure key has proper permissions")
    print()

    print("2. 📖 Documentation Check:")
    print("   ✓ Visit: https://creator.poe.com/docs")
    print("   ✓ Look for current API endpoints")
    print("   ✓ Check authentication requirements")
    print()

    print("3. 🚀 Alternative Solution (Recommended):")
    print("   ✓ Use Google Gemini (FREE) - works immediately")
    print("   ✓ Add OpenAI for premium analysis")
    print("   ✓ Smart routing system already built")
    print("   ✓ Better cost control and reliability")
    print()

    print("4. 🎯 Immediate Action Options:")
    print("   A) Get free Gemini API: https://makersuite.google.com/app/apikey")
    print("   B) Continue troubleshooting Poe API")
    print("   C) Use hybrid approach (Gemini + Poe when working)")

async def main():
    """Main test function."""
    print("🤖 POE API KEY TEST - UPDATED")
    print("=" * 60)

    success = await test_poe_api_comprehensive()

    if success:
        print("🎉 SUCCESS! Your Poe API key is working!")
        print()
        print("🚀 Next steps:")
        print("1. Integrate with your trading system")
        print("2. Test with real market analysis")
        print("3. Monitor usage and costs")
        print("4. Set up fallback systems")

        # Test with actual trading prompt
        print("\n🧪 Testing with Trading Analysis...")
        await test_trading_analysis()
    else:
        print("⚠️  API key tests failed.")
        await provide_guidance()

        print("\n🎯 RECOMMENDED SOLUTION:")
        print("While we troubleshoot Poe, let's get you trading with AI immediately:")
        print()
        print("1. 🆓 Get Google Gemini API (FREE):")
        print("   - Visit: https://makersuite.google.com/app/apikey")
        print("   - 2 minutes setup, works immediately")
        print("   - Perfect for trading analysis")
        print()
        print("2. 🔧 Use our working AI integration:")
        print("   - Already built and tested")
        print("   - Smart routing and cost optimization")
        print("   - Multiple AI providers")
        print()
        print("3. 💰 Total cost: $0 to start, scales as needed")

async def test_trading_analysis():
    """Test with actual trading analysis prompt."""
    print("📊 Testing Trading Analysis...")

    trading_prompt = """
    Analyze EURUSD for trading opportunity:

    Current Price: 1.0875
    RSI: 45.2 (neutral)
    MACD: Bullish crossover detected
    Volume: Above average
    Trend: Upward on 1H timeframe
    Support: 1.0850
    Resistance: 1.0920

    Provide trading recommendation with confidence level.
    """

    # This would use the working endpoint found above
    print("   (Would test with actual trading prompt if API is working)")
    print("   Expected: BUY/SELL/HOLD recommendation with reasoning")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        print("\nTroubleshooting suggestions:")
        print("1. Check internet connection")
        print("2. Verify API key is correct")
        print("3. Try the free Gemini alternative")

