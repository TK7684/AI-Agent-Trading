#!/usr/bin/env python3
"""
Demo script for WebSocket Service functionality
This demonstrates the key features of the WebSocket service implementation
"""

import asyncio
import json
import logging
import time
from datetime import datetime

import websockets
from websockets.server import WebSocketServerProtocol

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MockWebSocketServer:
    """Mock WebSocket server to demonstrate the service functionality"""

    def __init__(self, host: str = 'localhost', port: int = 8001):
        self.host = host
        self.port = port
        self.clients: set[WebSocketServerProtocol] = set()
        self.subscriptions: dict[str, set[WebSocketServerProtocol]] = {}
        self.running = False

    async def start(self):
        """Start the WebSocket server"""
        self.running = True
        logger.info(f"Starting WebSocket server on ws://{self.host}:{self.port}")

        async with websockets.serve(self.handle_client, self.host, self.port):
            await asyncio.Future()  # Run forever

    async def handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """Handle individual client connections"""
        client_id = f"client_{id(websocket)}"
        logger.info(f"Client {client_id} connected from {websocket.remote_address}")

        self.clients.add(websocket)

        try:
            # Send welcome message
            await self.send_message(websocket, {
                "type": "CONNECTION_STATUS",
                "data": {"status": "connected", "clientId": client_id},
                "timestamp": datetime.now().isoformat(),
                "id": f"welcome_{client_id}",
            })

            # Handle incoming messages
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.process_message(websocket, data, client_id)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from client {client_id}: {message}")

        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {client_id} disconnected")
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {e}")
        finally:
            self.clients.remove(websocket)
            # Remove from all subscriptions
            for subscribers in self.subscriptions.values():
                subscribers.discard(websocket)
            logger.info(f"Client {client_id} cleanup completed")

    async def process_message(self, websocket: WebSocketServerProtocol, data: dict, client_id: str):
        """Process incoming messages from clients"""
        msg_type = data.get('type')

        if msg_type == 'SUBSCRIBE':
            channel = data.get('channel') or data.get('event')
            if channel:
                if channel not in self.subscriptions:
                    self.subscriptions[channel] = set()
                self.subscriptions[channel].add(websocket)
                logger.info(f"Client {client_id} subscribed to {channel}")

                # Send confirmation
                await self.send_message(websocket, {
                    "type": "SUBSCRIPTION_CONFIRMED",
                    "data": {"channel": channel, "status": "subscribed"},
                    "timestamp": datetime.now().isoformat(),
                    "id": f"sub_{client_id}_{channel}",
                    "channel": channel,
                })

        elif msg_type == 'UNSUBSCRIBE':
            channel = data.get('channel') or data.get('event')
            if channel and channel in self.subscriptions:
                self.subscriptions[channel].discard(websocket)
                if not self.subscriptions[channel]:
                    del self.subscriptions[channel]
                logger.info(f"Client {client_id} unsubscribed from {channel}")

        elif msg_type == 'PING':
            # Respond to heartbeat
            await self.send_message(websocket, {
                "type": "PONG",
                "data": {
                    "timestamp": data.get('data', {}).get('timestamp', int(time.time() * 1000)),
                    "clientId": client_id,
                },
                "timestamp": datetime.now().isoformat(),
                "id": f"pong_{client_id}",
            })

        else:
            logger.info(f"Received message from {client_id}: {msg_type}")

    async def send_message(self, websocket: WebSocketServerProtocol, message: dict):
        """Send a message to a specific client"""
        try:
            await websocket.send(json.dumps(message))
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Failed to send message - connection closed")
        except Exception as e:
            logger.error(f"Error sending message: {e}")

    async def broadcast_to_channel(self, channel: str, message: dict):
        """Broadcast a message to all subscribers of a channel"""
        if channel in self.subscriptions:
            subscribers = self.subscriptions[channel].copy()
            for websocket in subscribers:
                try:
                    await self.send_message(websocket, message)
                except Exception as e:
                    logger.error(f"Failed to broadcast to client: {e}")

    async def simulate_trading_updates(self):
        """Simulate trading updates for demonstration"""
        while self.running:
            try:
                # Simulate trade updates
                trade_update = {
                    "type": "TRADE_OPENED",
                    "data": {
                        "id": f"trade_{int(time.time())}",
                        "symbol": "BTCUSD",
                        "side": "LONG",
                        "quantity": 0.1,
                        "price": 45000 + (time.time() % 1000),
                        "timestamp": datetime.now().isoformat(),
                    },
                    "timestamp": datetime.now().isoformat(),
                    "id": f"trade_{int(time.time())}",
                    "channel": "trading",
                }

                await self.broadcast_to_channel("trading", trade_update)
                logger.info("Broadcasted trade update")

                # Simulate system updates
                system_update = {
                    "type": "METRICS_UPDATE",
                    "data": {
                        "cpu_usage": 45 + (time.time() % 20),
                        "memory_usage": 60 + (time.time() % 15),
                        "active_agents": 3,
                        "timestamp": datetime.now().isoformat(),
                    },
                    "timestamp": datetime.now().isoformat(),
                    "id": f"system_{int(time.time())}",
                    "channel": "system",
                }

                await self.broadcast_to_channel("system", system_update)
                logger.info("Broadcasted system update")

                await asyncio.sleep(5)  # Update every 5 seconds

            except Exception as e:
                logger.error(f"Error in trading updates simulation: {e}")
                await asyncio.sleep(5)

class WebSocketServiceDemo:
    """Demonstration of WebSocket service features"""

    def __init__(self):
        self.server = MockWebSocketServer()

    async def run_demo(self):
        """Run the complete WebSocket service demonstration"""
        logger.info("Starting WebSocket Service Demo")
        logger.info("=" * 50)

        # Start the server
        server_task = asyncio.create_task(self.server.start())

        # Start the trading updates simulation
        updates_task = asyncio.create_task(self.server.simulate_trading_updates())

        try:
            # Let the demo run for a while
            await asyncio.sleep(30)
            logger.info("Demo completed successfully")

        except KeyboardInterrupt:
            logger.info("Demo interrupted by user")
        finally:
            self.server.running = False
            server_task.cancel()
            updates_task.cancel()

            try:
                await server_task
            except asyncio.CancelledError:
                pass

            try:
                await updates_task
            except asyncio.CancelledError:
                pass

def main():
    """Main entry point for the demo"""
    print("WebSocket Service Demo")
    print("=" * 30)
    print("This demo shows the key features of the WebSocket service:")
    print("1. Connection management with automatic reconnection")
    print("2. Message parsing and routing")
    print("3. Channel-based subscriptions")
    print("4. Heartbeat and keep-alive")
    print("5. Error handling and status monitoring")
    print()
    print("The demo will run for 30 seconds, showing:")
    print("- WebSocket server startup")
    print("- Client connection handling")
    print("- Real-time trading updates")
    print("- System metrics updates")
    print("- Subscription management")
    print()
    print("Press Ctrl+C to stop early")
    print()

    demo = WebSocketServiceDemo()

    try:
        asyncio.run(demo.run_demo())
    except KeyboardInterrupt:
        print("\nDemo stopped by user")
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())
