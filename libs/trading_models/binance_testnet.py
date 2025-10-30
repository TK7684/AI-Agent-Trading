"""
Binance Testnet Connection Module

This module provides a secure connection to Binance testnet for testing trading strategies
without using real funds. Features include:
- Secure credential management
- Testnet API endpoints
- Basic trading operations
- Real-time market data
- Account information
"""

import asyncio
import hashlib
import hmac
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional
from urllib.parse import urlencode

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class BinanceTestnetConfig:
    """Configuration for Binance testnet."""
    api_key: str
    api_secret: str
    base_url: str = "https://testnet.binance.vision"
    ws_url: str = "wss://testnet.binance.vision/ws"
    api_version: str = "v3"


@dataclass
class MarketData:
    """Market data structure."""
    symbol: str
    price: float
    volume: float
    timestamp: datetime
    bid: Optional[float] = None
    ask: Optional[float] = None
    high_24h: Optional[float] = None
    low_24h: Optional[float] = None
    change_24h: Optional[float] = None


@dataclass
class Order:
    """Order structure."""
    symbol: str
    side: str  # "BUY" or "SELL"
    order_type: str  # "MARKET", "LIMIT", "STOP", etc.
    quantity: float
    price: Optional[float] = None
    time_in_force: str = "GTC"  # GTC, IOC, FOK


class BinanceTestnetClient:
    """Client for connecting to Binance testnet."""

    def __init__(self, config: BinanceTestnetConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self._connected = False

    async def connect(self) -> bool:
        """Connect to Binance testnet."""
        try:
            self.session = aiohttp.ClientSession()

            # Test connection with ping endpoint
            async with self.session.get(f"{self.config.base_url}/api/{self.config.api_version}/ping") as response:
                if response.status == 200:
                    self._connected = True
                    logger.info("Successfully connected to Binance testnet")
                    return True
                else:
                    logger.error(f"Failed to connect to testnet: {response.status}")
                    return False

        except Exception as e:
            logger.error(f"Error connecting to testnet: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from Binance testnet."""
        if self.session:
            await self.session.close()
        self._connected = False
        logger.info("Disconnected from Binance testnet")

    def _generate_signature(self, params: dict[str, Any]) -> str:
        """Generate HMAC SHA256 signature for authenticated requests."""
        query_string = urlencode(params)
        signature = hmac.new(
            self.config.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature

    def _add_auth_headers(self, params: dict[str, Any]) -> dict[str, Any]:
        """Add authentication parameters to request."""
        params['timestamp'] = int(time.time() * 1000)
        params['signature'] = self._generate_signature(params)
        return params

    async def get_account_info(self) -> dict[str, Any]:
        """Get account information from testnet."""
        if not self._connected:
            raise ConnectionError("Not connected to testnet")

        try:
            params = self._add_auth_headers({})

            async with self.session.get(
                f"{self.config.base_url}/api/{self.config.api_version}/account",
                params=params,
                headers={'X-MBX-APIKEY': self.config.api_key}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info("Successfully retrieved account info")
                    return {
                        'maker_commission': data.get('makerCommission'),
                        'taker_commission': data.get('takerCommission'),
                        'buyer_commission': data.get('buyerCommission'),
                        'seller_commission': data.get('sellerCommission'),
                        'can_trade': data.get('canTrade'),
                        'can_withdraw': data.get('canWithdraw'),
                        'can_deposit': data.get('canDeposit'),
                        'balances': data.get('balances', [])
                    }
                else:
                    error_data = await response.json()
                    logger.error(f"Failed to get account info: {error_data}")
                    return {}

        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return {}

    async def get_market_data(self, symbol: str) -> Optional[MarketData]:
        """Get market data for a symbol from testnet."""
        if not self._connected:
            raise ConnectionError("Not connected to testnet")

        try:
            params = {'symbol': symbol}

            async with self.session.get(
                f"{self.config.base_url}/api/{self.config.api_version}/ticker/24hr",
                params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()

                    return MarketData(
                        symbol=data['symbol'],
                        price=float(data['lastPrice']),
                        volume=float(data['volume']),
                        timestamp=datetime.fromtimestamp(data['closeTime'] / 1000),
                        bid=float(data['bidPrice']) if data.get('bidPrice') else None,
                        ask=float(data['askPrice']) if data.get('askPrice') else None,
                        high_24h=float(data['highPrice']),
                        low_24h=float(data['lowPrice']),
                        change_24h=float(data['priceChangePercent'])
                    )
                else:
                    error_data = await response.json()
                    logger.error(f"Failed to get market data: {error_data}")
                    return None

        except Exception as e:
            logger.error(f"Error getting market data: {e}")
            return None

    async def place_order(self, order: Order) -> dict[str, Any]:
        """Place a new order on testnet."""
        if not self._connected:
            raise ConnectionError("Not connected to testnet")

        try:
            params = {
                'symbol': order.symbol,
                'side': order.side,
                'type': order.order_type,
                'quantity': order.quantity,
                'timeInForce': order.time_in_force
            }

            if order.price and order.order_type == 'LIMIT':
                params['price'] = order.price

            params = self._add_auth_headers(params)

            async with self.session.post(
                f"{self.config.base_url}/api/{self.config.api_version}/order",
                params=params,
                headers={'X-MBX-APIKEY': self.config.api_key}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Order placed successfully: {data['orderId']}")
                    return {
                        'order_id': data['orderId'],
                        'status': data['status'],
                        'filled_quantity': float(data['executedQty']),
                        'average_price': float(data['avgPrice']) if data.get('avgPrice') else None,
                        'commission': float(data['commission']) if data.get('commission') else 0.0
                    }
                else:
                    error_data = await response.json()
                    logger.error(f"Failed to place order: {error_data}")
                    return {'error': error_data}

        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return {'error': str(e)}

    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an existing order on testnet."""
        if not self._connected:
            raise ConnectionError("Not connected to testnet")

        try:
            params = {
                'symbol': symbol,
                'orderId': order_id
            }
            params = self._add_auth_headers(params)

            async with self.session.delete(
                f"{self.config.base_url}/api/{self.config.api_version}/order",
                params=params,
                headers={'X-MBX-APIKEY': self.config.api_key}
            ) as response:
                if response.status == 200:
                    logger.info(f"Order {order_id} cancelled successfully")
                    return True
                else:
                    error_data = await response.json()
                    logger.error(f"Failed to cancel order: {error_data}")
                    return False

        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return False

    async def get_order_status(self, order_id: str, symbol: str) -> dict[str, Any]:
        """Get order status from testnet."""
        if not self._connected:
            raise ConnectionError("Not connected to testnet")

        try:
            params = {
                'symbol': symbol,
                'orderId': order_id
            }
            params = self._add_auth_headers(params)

            async with self.session.get(
                f"{self.config.base_url}/api/{self.config.api_version}/order",
                params=params,
                headers={'X-MBX-APIKEY': self.config.api_key}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        'order_id': data['orderId'],
                        'symbol': data['symbol'],
                        'side': data['side'],
                        'type': data['type'],
                        'status': data['status'],
                        'quantity': float(data['origQty']),
                        'filled_quantity': float(data['executedQty']),
                        'price': float(data['price']),
                        'average_price': float(data['avgPrice']) if data.get('avgPrice') else None,
                        'created_at': datetime.fromtimestamp(data['time'] / 1000),
                        'commission': float(data['commission']) if data.get('commission') else 0.0
                    }
                else:
                    error_data = await response.json()
                    logger.error(f"Failed to get order status: {error_data}")
                    return {}

        except Exception as e:
            logger.error(f"Error getting order status: {e}")
            return {}

    async def get_open_orders(self, symbol: Optional[str] = None) -> list[dict[str, Any]]:
        """Get open orders from testnet."""
        if not self._connected:
            raise ConnectionError("Not connected to testnet")

        try:
            params = {}
            if symbol:
                params['symbol'] = symbol

            params = self._add_auth_headers(params)

            async with self.session.get(
                f"{self.config.base_url}/api/{self.config.api_version}/openOrders",
                params=params,
                headers={'X-MBX-APIKEY': self.config.api_key}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    error_data = await response.json()
                    logger.error(f"Failed to get open orders: {error_data}")
                    return []

        except Exception as e:
            logger.error(f"Error getting open orders: {e}")
            return []

    async def get_order_history(self, symbol: Optional[str] = None, limit: int = 100) -> list[dict[str, Any]]:
        """Get order history from testnet."""
        if not self._connected:
            raise ConnectionError("Not connected to testnet")

        try:
            params = {'limit': limit}
            if symbol:
                params['symbol'] = symbol

            params = self._add_auth_headers(params)

            async with self.session.get(
                f"{self.config.base_url}/api/{self.config.api_version}/allOrders",
                params=params,
                headers={'X-MBX-APIKEY': self.config.api_key}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    error_data = await response.json()
                    logger.error(f"Failed to get order history: {error_data}")
                    return []

        except Exception as e:
            logger.error(f"Error getting order history: {e}")
            return []

    async def get_exchange_info(self) -> dict[str, Any]:
        """Get exchange information from testnet."""
        if not self._connected:
            raise ConnectionError("Not connected to testnet")

        try:
            async with self.session.get(
                f"{self.config.base_url}/api/{self.config.api_version}/exchangeInfo"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    logger.error(f"Failed to get exchange info: {response.status}")
                    return {}

        except Exception as e:
            logger.error(f"Error getting exchange info: {e}")
            return {}

    def is_connected(self) -> bool:
        """Check if connected to testnet."""
        return self._connected


# Example usage and testing
async def test_binance_testnet():
    """Test connection to Binance testnet."""

    # Your testnet credentials
    config = BinanceTestnetConfig(
        api_key="NLCmACV1ZlF6nz4ZJex0FgGMCp0LJLEwbDJBbfNFTYtS4GBLuouiFdVrIrRpX3ZM",
        api_secret="Cstg7R9gYRwA7IaEbe8X26SgtF3J1GRZ9dzkQjfB6t4IcGksRkGd8V2yFPVAXnbN"
    )

    # Create client
    client = BinanceTestnetClient(config)

    try:
        # Connect to testnet
        print("Connecting to Binance testnet...")
        if await client.connect():
            print("✅ Connected to Binance testnet successfully!")

            # Get account info
            print("\n📊 Getting account information...")
            account_info = await client.get_account_info()
            if account_info:
                print(f"Can trade: {account_info.get('can_trade', False)}")
                print(f"Can withdraw: {account_info.get('can_withdraw', False)}")
                print(f"Can deposit: {account_info.get('can_deposit', False)}")

                # Show balances
                balances = account_info.get('balances', [])
                print("\n💰 Account balances:")
                for balance in balances:
                    free = float(balance.get('free', 0))
                    if free > 0:
                        print(f"  {balance['asset']}: {free}")

            # Get market data for BTCUSDT
            print("\n📈 Getting BTCUSDT market data...")
            market_data = await client.get_market_data("BTCUSDT")
            if market_data:
                print(f"Symbol: {market_data.symbol}")
                print(f"Price: ${market_data.price:,.2f}")
                print(f"24h Change: {market_data.change_24h:.2f}%")
                print(f"24h Volume: {market_data.volume:,.2f}")
                print(f"24h High: ${market_data.high_24h:,.2f}")
                print(f"24h Low: ${market_data.low_24h:,.2f}")

            # Get exchange info
            print("\n🏛️ Getting exchange information...")
            exchange_info = await client.get_exchange_info()
            if exchange_info:
                symbols = exchange_info.get('symbols', [])
                print(f"Total symbols available: {len(symbols)}")

                # Show some popular symbols
                popular_symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'DOGEUSDT']
                available_symbols = [s['symbol'] for s in symbols]

                print("Popular symbols available:")
                for symbol in popular_symbols:
                    if symbol in available_symbols:
                        print(f"  ✅ {symbol}")
                    else:
                        print(f"  ❌ {symbol}")

            # Test order placement (limit order - won't execute immediately)
            print("\n📝 Testing order placement (limit order)...")
            test_order = Order(
                symbol="BTCUSDT",
                side="BUY",
                order_type="LIMIT",
                quantity=0.001,  # Very small amount
                price=50000.0    # Low price that won't execute
            )

            order_result = await client.place_order(test_order)
            if 'error' not in order_result:
                print("✅ Test order placed successfully!")
                print(f"Order ID: {order_result['order_id']}")
                print(f"Status: {order_result['status']}")

                # Cancel the test order
                print("\n❌ Cancelling test order...")
                if await client.cancel_order(order_result['order_id'], "BTCUSDT"):
                    print("✅ Test order cancelled successfully!")
                else:
                    print("❌ Failed to cancel test order")
            else:
                print(f"❌ Failed to place test order: {order_result['error']}")

        else:
            print("❌ Failed to connect to Binance testnet")

    except Exception as e:
        print(f"❌ Error: {e}")

    finally:
        # Disconnect
        await client.disconnect()
        print("\n🔌 Disconnected from Binance testnet")


if __name__ == "__main__":
    print("🚀 Binance Testnet Connection Test")
    print("=" * 50)

    # Run the test
    asyncio.run(test_binance_testnet())
