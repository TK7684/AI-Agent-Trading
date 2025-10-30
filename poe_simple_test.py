#!/usr/bin/env python3
"""
Simple Poe API Test - Verify your API key works
"""

import asyncio
import json
from datetime import datetime

import aiohttp

# Your Poe API key
POE_API_KEY = "RquMo_2I1XBh78q9UeR_RltxwhzFzL15HMadTn2MVMc-1758275293-1.0.1.1-Dg_8A7NUo6A0.qbC3yaoolnBTN6DbglTwLuGLQGIkMGsL03gHo_pqy6mnoruzfjL7qRyGJM6rPQfG2aKsxxnlqhv_1eYL2jdZV4GyKHMd7Y"

async def test_poe_connection():
    """Simple test of Poe API connection."""
    print("🚀 Testing Poe API Connection...")
    print("=" * 40)
    print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔑 API Key: {POE_API_KEY[:20]}...{POE_API_KEY[-10:]}")
    print()

    # Test different endpoints to find the right one
    test_endpoints = [
        "https://api.poe.com/bot/chat",
        "https://api.poe.com/v1/chat/completions",
        "https://api.poe.com/chat",
        "https://poe.com/api/chat"
    ]

    headers = {
        "Authorization": f"Bearer {POE_API_KEY}",
        "Content-Type": "application/json",
        "User-Agent": "AI-Trading-Agent/1.0"
    }

    # Simple test payload
    test_payloads = [
        # OpenAI-compatible format
        {
            "model": "Claude-3.5-Sonnet",
            "messages": [
                {"role": "user", "content": "Hello! Can you respond with just 'API TEST SUCCESS' if you receive this?"}
            ],
            "max_tokens": 50,
            "temperature": 0.1
        },
        # Poe-specific format
        {
            "version": "1.0",
            "type": "query",
            "query": [
                {"role": "user", "content": "Hello! Can you respond with just 'API TEST SUCCESS' if you receive this?"}
            ],
            "model": "Claude-3.5-Sonnet",
            "max_tokens": 50
        }
    ]

    async with aiohttp.ClientSession() as session:
        for i, endpoint in enumerate(test_endpoints):
            for j, payload in enumerate(test_payloads):
                print(f"🧪 Test {i+1}.{j+1}: {endpoint}")
                print(f"   Payload format: {'OpenAI-compatible' if j == 0 else 'Poe-specific'}")

                try:
                    async with session.post(
                        endpoint,
                        headers=headers,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:

                        print(f"   Status: {response.status}")

                        if response.status == 200:
                            try:
                                data = await response.json()
                                print("   ✅ SUCCESS! Response received:")
                                print(f"   📝 Content: {json.dumps(data, indent=2)[:200]}...")
                                return True
                            except:
                                text = await response.text()
                                print(f"   ✅ SUCCESS! Raw response: {text[:200]}...")
                                return True
                        else:
                            error_text = await response.text()
                            print(f"   ❌ Error: {error_text[:200]}...")

                except asyncio.TimeoutError:
                    print("   ⏰ Timeout after 30 seconds")
                except Exception as e:
                    print(f"   💥 Exception: {e}")

                print()

    print("❌ All tests failed. Possible issues:")
    print("   1. API key might be invalid or expired")
    print("   2. Poe API endpoint might have changed")
    print("   3. Authentication format might be different")
    print("   4. Network connectivity issues")

    return False

async def test_alternative_approach():
    """Test alternative approaches to Poe API."""
    print("\n🔄 Testing Alternative Approaches...")
    print("=" * 40)

    # Try different authentication methods
    auth_methods = [
        {"Authorization": f"Bearer {POE_API_KEY}"},
        {"Authorization": f"Token {POE_API_KEY}"},
        {"X-API-Key": POE_API_KEY},
        {"poe-api-key": POE_API_KEY}
    ]

    simple_payload = {
        "message": "Hello, this is a test",
        "model": "Claude-3.5-Sonnet"
    }

    async with aiohttp.ClientSession() as session:
        for i, headers in enumerate(auth_methods):
            headers["Content-Type"] = "application/json"
            headers["User-Agent"] = "AI-Trading-Agent/1.0"

            print(f"🔐 Auth method {i+1}: {list(headers.keys())[0]}")

            try:
                async with session.post(
                    "https://api.poe.com/bot/chat",
                    headers=headers,
                    json=simple_payload,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:

                    print(f"   Status: {response.status}")

                    if response.status in [200, 201]:
                        data = await response.text()
                        print(f"   ✅ Success with auth method {i+1}!")
                        print(f"   Response: {data[:100]}...")
                        return True
                    else:
                        error = await response.text()
                        print(f"   Response: {error[:100]}...")

            except Exception as e:
                print(f"   Error: {e}")

            print()

    return False

async def main():
    """Main test function."""
    print("🤖 POE API INTEGRATION TEST")
    print("=" * 50)

    # Test 1: Standard API approaches
    success1 = await test_poe_connection()

    if not success1:
        # Test 2: Alternative approaches
        success2 = await test_alternative_approach()

        if not success2:
            print("\n💡 TROUBLESHOOTING SUGGESTIONS:")
            print("=" * 40)
            print("1. 🔍 Check if your Poe API key is active:")
            print("   - Log into poe.com")
            print("   - Go to Settings > API")
            print("   - Verify key is enabled")
            print()
            print("2. 📖 Check Poe documentation:")
            print("   - Visit: https://creator.poe.com/docs")
            print("   - Look for current API endpoints")
            print("   - Check authentication format")
            print()
            print("3. 💰 Verify subscription:")
            print("   - Ensure you have active Poe subscription")
            print("   - Check if API access is included")
            print("   - Verify points/credits available")
            print()
            print("4. 🌐 Network check:")
            print("   - Try from different network")
            print("   - Check firewall/proxy settings")
            print("   - Verify DNS resolution")

            return False

    print("\n🎉 POE API TEST COMPLETED!")
    print("✅ Your API key appears to be working!")
    print("\n🚀 Next steps:")
    print("1. Integrate with your trading system")
    print("2. Start with paper trading")
    print("3. Monitor points usage")
    print("4. Scale up gradually")

    return True

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        if success:
            print("\n🏆 Ready to enhance your AI trading agent with Poe!")
        else:
            print("\n⚠️  Please resolve the issues above before proceeding.")
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        print("Please check your Python environment and dependencies.")

