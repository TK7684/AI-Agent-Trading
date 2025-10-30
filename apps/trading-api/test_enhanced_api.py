#!/usr/bin/env python3
"""
Test enhanced trading API functionality
"""

import asyncio
import json

import httpx
import websockets


class TestTradingAPI:
    """Test suite for enhanced trading API."""

    BASE_URL = "http://localhost:8000"
    WS_URL = "ws://localhost:8000"

    def __init__(self):
        self.token = None
        self.client = httpx.AsyncClient(base_url=self.BASE_URL)

    async def setup(self):
        """Setup test environment."""
        # Login to get token
        login_response = await self.client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "password123"
        })

        if login_response.status_code == 200:
            data = login_response.json()
            self.token = data["token"]
            print("✅ Authentication successful")
        else:
            print(f"❌ Authentication failed: {login_response.text}")
            return False

        return True

    async def test_health_endpoint(self):
        """Test system health endpoint."""
        response = await self.client.get("/system/health")

        if response.status_code == 200:
            data = response.json()
            print("✅ Health endpoint working")
            print(f"   CPU: {data['cpu']}%, Memory: {data['memory']}%")
            return True
        else:
            print(f"❌ Health endpoint failed: {response.text}")
            return False

    async def test_trading_performance(self):
        """Test trading performance endpoint."""
        headers = {"Authorization": f"Bearer {self.token}"}
        response = await self.client.get("/trading/performance", headers=headers)

        if response.status_code == 200:
            data = response.json()
            print("✅ Trading performance endpoint working")
            print(f"   Total P&L: ${data['totalPnl']:.2f}")
            print(f"   Win Rate: {data['winRate']:.1f}%")
            return True
        else:
            print(f"❌ Trading performance failed: {response.text}")
            return False

    async def test_trading_logs(self):
        """Test trading logs with filtering."""
        headers = {"Authorization": f"Bearer {self.token}"}

        # Test basic logs
        response = await self.client.get("/trading/trades", headers=headers)
        if response.status_code != 200:
            print(f"❌ Trading logs failed: {response.text}")
            return False

        data = response.json()
        print(f"✅ Trading logs working - {data['total']} trades found")

        # Test filtering
        response = await self.client.get(
            "/trading/trades?symbols=BTCUSDT&status=CLOSED&page=1&pageSize=5",
            headers=headers
        )

        if response.status_code == 200:
            filtered_data = response.json()
            print(f"✅ Trading logs filtering working - {filtered_data['total']} filtered trades")
            return True
        else:
            print(f"❌ Trading logs filtering failed: {response.text}")
            return False

    async def test_agent_control(self):
        """Test agent control functionality."""
        headers = {"Authorization": f"Bearer {self.token}"}

        # Test agent status
        response = await self.client.get("/system/agents", headers=headers)
        if response.status_code != 200:
            print(f"❌ Agent status failed: {response.text}")
            return False

        status_data = response.json()
        print(f"✅ Agent status working - State: {status_data['state']}")

        # Test agent control
        control_response = await self.client.post(
            "/system/agents/main/control",
            headers=headers,
            json={"action": "pause", "parameters": {}}
        )

        if control_response.status_code == 200:
            control_data = control_response.json()
            print(f"✅ Agent control working - {control_data['message']}")
            return True
        else:
            print(f"❌ Agent control failed: {control_response.text}")
            return False

    async def test_notifications(self):
        """Test notifications system."""
        headers = {"Authorization": f"Bearer {self.token}"}

        # Get notifications
        response = await self.client.get("/system/notifications", headers=headers)
        if response.status_code != 200:
            print(f"❌ Notifications failed: {response.text}")
            return False

        data = response.json()
        print(f"✅ Notifications working - {data['total']} notifications found")

        # Test marking as read
        if data['items']:
            notification_id = data['items'][0]['id']
            read_response = await self.client.post(
                f"/system/notifications/{notification_id}/read",
                headers=headers
            )

            if read_response.status_code == 200:
                print("✅ Mark notification as read working")
                return True
            else:
                print(f"❌ Mark notification as read failed: {read_response.text}")
                return False

        return True

    async def test_websocket_trading(self):
        """Test trading WebSocket connection."""
        try:
            uri = f"{self.WS_URL}/ws/trading"
            async with websockets.connect(uri) as websocket:
                print("✅ Trading WebSocket connected")

                # Send ping
                await websocket.send("ping")
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)

                if response == "pong":
                    print("✅ Trading WebSocket ping/pong working")
                    return True
                else:
                    print(f"❌ Unexpected WebSocket response: {response}")
                    return False

        except Exception as e:
            print(f"❌ Trading WebSocket failed: {e}")
            return False

    async def test_websocket_system(self):
        """Test system WebSocket connection."""
        try:
            uri = f"{self.WS_URL}/ws/system"
            async with websockets.connect(uri) as websocket:
                print("✅ System WebSocket connected")

                # Wait for initial message
                message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(message)

                if data.get("type") == "CONNECTION_ESTABLISHED":
                    print("✅ System WebSocket initial message received")
                    return True
                else:
                    print(f"❌ Unexpected initial message: {data}")
                    return False

        except Exception as e:
            print(f"❌ System WebSocket failed: {e}")
            return False

    async def test_rate_limiting(self):
        """Test API rate limiting."""
        headers = {"Authorization": f"Bearer {self.token}"}

        # Make multiple rapid requests
        tasks = []
        for i in range(10):
            task = self.client.get("/trading/performance", headers=headers)
            tasks.append(task)

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = sum(1 for r in responses if hasattr(r, 'status_code') and r.status_code == 200)
        rate_limited_count = sum(1 for r in responses if hasattr(r, 'status_code') and r.status_code == 429)

        print(f"✅ Rate limiting test - {success_count} successful, {rate_limited_count} rate limited")
        return True

    async def test_export_functionality(self):
        """Test trade export functionality."""
        headers = {"Authorization": f"Bearer {self.token}"}

        # Test CSV export
        export_response = await self.client.post(
            "/trading/trades/export?format=csv",
            headers=headers,
            json={
                "symbols": ["BTCUSDT"],
                "status": ["CLOSED"]
            }
        )

        if export_response.status_code == 200:
            data = export_response.json()
            if data.get("format") == "csv" and data.get("data"):
                print("✅ CSV export working")
                return True
            else:
                print(f"❌ CSV export invalid response: {data}")
                return False
        else:
            print(f"❌ CSV export failed: {export_response.text}")
            return False

    async def run_all_tests(self):
        """Run all tests."""
        print("🚀 Starting Enhanced Trading API Tests\n")

        # Setup
        if not await self.setup():
            print("❌ Setup failed, aborting tests")
            return

        # Run tests
        tests = [
            ("Health Endpoint", self.test_health_endpoint),
            ("Trading Performance", self.test_trading_performance),
            ("Trading Logs", self.test_trading_logs),
            ("Agent Control", self.test_agent_control),
            ("Notifications", self.test_notifications),
            ("WebSocket Trading", self.test_websocket_trading),
            ("WebSocket System", self.test_websocket_system),
            ("Rate Limiting", self.test_rate_limiting),
            ("Export Functionality", self.test_export_functionality),
        ]

        results = []
        for test_name, test_func in tests:
            print(f"\n📋 Running {test_name} test...")
            try:
                result = await test_func()
                results.append((test_name, result))
            except Exception as e:
                print(f"❌ {test_name} test failed with exception: {e}")
                results.append((test_name, False))

        # Summary
        print("\n" + "="*50)
        print("📊 TEST RESULTS SUMMARY")
        print("="*50)

        passed = sum(1 for _, result in results if result)
        total = len(results)

        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} - {test_name}")

        print(f"\n🎯 Overall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")

        await self.client.aclose()


async def main():
    """Main test runner."""
    tester = TestTradingAPI()
    await tester.run_all_tests()


if __name__ == "__main__":
    print("Enhanced Trading API Test Suite")
    print("Make sure the API server is running on http://localhost:8000")
    print("Start server with: uvicorn apps.trading-api.main:app --reload\n")

    asyncio.run(main())
