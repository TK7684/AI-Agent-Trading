"""
Binance Exchange Adapter

This module provides a comprehensive adapter for Binance Spot and Futures trading,
including authentication, market data, order execution, and account management.
"""

import hashlib
import hmac
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Optional

import httpx
import structlog

logger = structlog.get_logger(__name__)


class BinanceOrderType(str, Enum):
    """Binance order types."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    STOP_LOSS_LIMIT = "STOP_LOSS_LIMIT"
    TAKE_PROFIT = "TAKE_PROFIT"
    TAKE_PROFIT_LIMIT = "TAKE_PROFIT_LIMIT"
    LIMIT_MAKER = "LIMIT_MAKER"


class BinanceOrderSide(str, Enum):
    """Binance order sides."""
    BUY = "BUY"
    SELL = "SELL"


class BinanceOrderStatus(str, Enum):
    """Binance order status."""
    NEW = "NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    PENDING_CANCEL = "PENDING_CANCEL"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


@dataclass
class BinanceCredentials:
    """Binance API credentials."""
    api_key: str
    api_secret: str
    testnet: bool = True

    def __post_init__(self):
        if not self.api_key or not self.api_secret:
            raise ValueError("API key and secret are required")


@dataclass
class BinanceSymbolInfo:
    """Binance symbol information."""
    symbol: str
    base_asset: str
    quote_asset: str
    status: str
    min_qty: float
    max_qty: float
    step_size: float
    tick_size: float
    min_notional: float
    is_spot_trading_allowed: bool
    is_margin_trading_allowed: bool


@dataclass
class BinanceOrder:
    """Binance order representation."""
    symbol: str
    order_id: int
    client_order_id: str
    side: BinanceOrderSide
    type: BinanceOrderType
    status: BinanceOrderStatus
    quantity: float
    price: Optional[float]
    executed_qty: float
    cummulative_quote_qty: float
    time: datetime
    update_time: datetime


class BinanceAdapter:
    """
    Comprehensive Binance exchange adapter.

    Provides secure API connectivity, real-time data, and order execution
    for both Spot and Futures trading.
    """

    def __init__(self, credentials: BinanceCredentials):
        """
        Initialize Binance adapter.

        Args:
            credentials: Binance API credentials
        """
        self.credentials = credentials
        self.testnet = credentials.testnet

        # API endpoints
        if self.testnet:
            self.spot_base_url = "https://testnet.binance.vision"
            self.futures_base_url = "https://testnet.binancefuture.com"
            self.ws_base_url = "wss://testnet.binance.vision/ws"
        else:
            self.spot_base_url = "https://api.binance.com"
            self.futures_base_url = "https://fapi.binance.com"
            self.ws_base_url = "wss://stream.binance.com:9443/ws"

        # HTTP client
        self.client = httpx.AsyncClient(timeout=30.0)

        # WebSocket connections
        self.ws_connections: dict[str, Any] = {}

        # Symbol information cache
        self.spot_symbols: dict[str, BinanceSymbolInfo] = {}
        self.futures_symbols: dict[str, BinanceSymbolInfo] = {}

        # Rate limiting
        self.request_weights = {}
        self.last_request_time = 0

        self.logger = logger.bind(
            component="BinanceAdapter",
            testnet=self.testnet
        )

        self.logger.info("Binance adapter initialized")

    def _generate_signature(self, query_string: str) -> str:
        """
        Generate HMAC-SHA256 signature for Binance API.

        Args:
            query_string: Query parameters string

        Returns:
            HMAC signature
        """
        return hmac.new(
            self.credentials.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    def _get_headers(self) -> dict[str, str]:
        """Get API request headers."""
        return {
            "X-MBX-APIKEY": self.credentials.api_key,
            "Content-Type": "application/json"
        }

    def _add_timestamp_and_signature(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Add timestamp and signature to API parameters.

        Args:
            params: Request parameters

        Returns:
            Parameters with timestamp and signature
        """
        params["timestamp"] = int(time.time() * 1000)
        params["recvWindow"] = 5000

        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        params["signature"] = self._generate_signature(query_string)

        return params

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        signed: bool = False,
        futures: bool = False
    ) -> dict[str, Any]:
        """
        Make authenticated API request to Binance.

        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Request parameters
            signed: Whether request needs signature
            futures: Whether to use futures API

        Returns:
            API response
        """
        base_url = self.futures_base_url if futures else self.spot_base_url
        url = f"{base_url}{endpoint}"

        if params is None:
            params = {}

        headers = self._get_headers() if signed else {}

        if signed:
            params = self._add_timestamp_and_signature(params)

        try:
            if method.upper() == "GET":
                response = await self.client.get(url, params=params, headers=headers)
            elif method.upper() == "POST":
                response = await self.client.post(url, json=params, headers=headers)
            elif method.upper() == "DELETE":
                response = await self.client.delete(url, params=params, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            self.logger.error(
                "Binance API error",
                status_code=e.response.status_code,
                response=e.response.text,
                endpoint=endpoint
            )
            raise
        except Exception as e:
            self.logger.error(
                "Request failed",
                error=str(e),
                endpoint=endpoint
            )
            raise

    async def get_server_time(self) -> int:
        """
        Get Binance server time.

        Returns:
            Server timestamp in milliseconds
        """
        response = await self._make_request("GET", "/api/v3/time")
        return response["serverTime"]

    async def test_connectivity(self) -> bool:
        """
        Test API connectivity.

        Returns:
            True if connection successful
        """
        try:
            await self._make_request("GET", "/api/v3/ping")
            self.logger.info("Binance connectivity test passed")
            return True
        except Exception as e:
            self.logger.error("Binance connectivity test failed", error=str(e))
            return False

    async def get_account_info(self, futures: bool = False) -> dict[str, Any]:
        """
        Get account information.

        Args:
            futures: Whether to get futures account info

        Returns:
            Account information
        """
        endpoint = "/fapi/v2/account" if futures else "/api/v3/account"
        return await self._make_request("GET", endpoint, signed=True, futures=futures)

    async def get_exchange_info(self, futures: bool = False) -> dict[str, Any]:
        """
        Get exchange information including symbol details.

        Args:
            futures: Whether to get futures exchange info

        Returns:
            Exchange information
        """
        endpoint = "/fapi/v1/exchangeInfo" if futures else "/api/v3/exchangeInfo"
        return await self._make_request("GET", endpoint, futures=futures)

    async def load_symbol_info(self) -> None:
        """Load and cache symbol information for both spot and futures."""
        try:
            # Load spot symbols
            spot_info = await self.get_exchange_info(futures=False)
            for symbol_data in spot_info["symbols"]:
                if symbol_data["status"] == "TRADING":
                    # Extract filters
                    min_qty = 0.0
                    max_qty = float('inf')
                    step_size = 0.0
                    tick_size = 0.0
                    min_notional = 0.0

                    for filter_info in symbol_data["filters"]:
                        if filter_info["filterType"] == "LOT_SIZE":
                            min_qty = float(filter_info["minQty"])
                            max_qty = float(filter_info["maxQty"])
                            step_size = float(filter_info["stepSize"])
                        elif filter_info["filterType"] == "PRICE_FILTER":
                            tick_size = float(filter_info["tickSize"])
                        elif filter_info["filterType"] == "MIN_NOTIONAL":
                            min_notional = float(filter_info["minNotional"])

                    symbol_info = BinanceSymbolInfo(
                        symbol=symbol_data["symbol"],
                        base_asset=symbol_data["baseAsset"],
                        quote_asset=symbol_data["quoteAsset"],
                        status=symbol_data["status"],
                        min_qty=min_qty,
                        max_qty=max_qty,
                        step_size=step_size,
                        tick_size=tick_size,
                        min_notional=min_notional,
                        is_spot_trading_allowed=symbol_data["isSpotTradingAllowed"],
                        is_margin_trading_allowed=symbol_data["isMarginTradingAllowed"]
                    )
                    self.spot_symbols[symbol_data["symbol"]] = symbol_info

            # Load futures symbols
            futures_info = await self.get_exchange_info(futures=True)
            for symbol_data in futures_info["symbols"]:
                if symbol_data["status"] == "TRADING":
                    # Extract filters for futures
                    min_qty = 0.0
                    max_qty = float('inf')
                    step_size = 0.0
                    tick_size = 0.0
                    min_notional = 0.0

                    for filter_info in symbol_data["filters"]:
                        if filter_info["filterType"] == "LOT_SIZE":
                            min_qty = float(filter_info["minQty"])
                            max_qty = float(filter_info["maxQty"])
                            step_size = float(filter_info["stepSize"])
                        elif filter_info["filterType"] == "PRICE_FILTER":
                            tick_size = float(filter_info["tickSize"])
                        elif filter_info["filterType"] == "MIN_NOTIONAL":
                            min_notional = float(filter_info["notional"])

                    symbol_info = BinanceSymbolInfo(
                        symbol=symbol_data["symbol"],
                        base_asset=symbol_data["baseAsset"],
                        quote_asset=symbol_data["quoteAsset"],
                        status=symbol_data["status"],
                        min_qty=min_qty,
                        max_qty=max_qty,
                        step_size=step_size,
                        tick_size=tick_size,
                        min_notional=min_notional,
                        is_spot_trading_allowed=True,  # Futures are always tradeable
                        is_margin_trading_allowed=True
                    )
                    self.futures_symbols[symbol_data["symbol"]] = symbol_info

            self.logger.info(
                "Symbol information loaded",
                spot_symbols=len(self.spot_symbols),
                futures_symbols=len(self.futures_symbols)
            )

        except Exception as e:
            self.logger.error("Failed to load symbol information", error=str(e))
            raise

    def validate_order_params(
        self,
        symbol: str,
        quantity: float,
        price: Optional[float] = None,
        futures: bool = False
    ) -> bool:
        """
        Validate order parameters against symbol filters.

        Args:
            symbol: Trading symbol
            quantity: Order quantity
            price: Order price (for limit orders)
            futures: Whether this is a futures order

        Returns:
            True if parameters are valid
        """
        symbols_dict = self.futures_symbols if futures else self.spot_symbols

        if symbol not in symbols_dict:
            self.logger.error("Unknown symbol", symbol=symbol)
            return False

        symbol_info = symbols_dict[symbol]

        # Check quantity
        if quantity < symbol_info.min_qty:
            self.logger.error(
                "Quantity below minimum",
                quantity=quantity,
                min_qty=symbol_info.min_qty
            )
            return False

        if quantity > symbol_info.max_qty:
            self.logger.error(
                "Quantity above maximum",
                quantity=quantity,
                max_qty=symbol_info.max_qty
            )
            return False

        # Check step size
        if symbol_info.step_size > 0:
            remainder = (quantity - symbol_info.min_qty) % symbol_info.step_size
            if remainder != 0:
                self.logger.error(
                    "Invalid quantity step size",
                    quantity=quantity,
                    step_size=symbol_info.step_size
                )
                return False

        # Check price (for limit orders)
        if price is not None and symbol_info.tick_size > 0:
            remainder = price % symbol_info.tick_size
            if remainder != 0:
                self.logger.error(
                    "Invalid price tick size",
                    price=price,
                    tick_size=symbol_info.tick_size
                )
                return False

        return True

    async def place_spot_order(
        self,
        symbol: str,
        side: BinanceOrderSide,
        order_type: BinanceOrderType,
        quantity: float,
        price: Optional[float] = None,
        client_order_id: Optional[str] = None
    ) -> BinanceOrder:
        """
        Place a spot trading order.

        Args:
            symbol: Trading symbol
            side: Order side (BUY/SELL)
            order_type: Order type
            quantity: Order quantity
            price: Order price (required for limit orders)
            client_order_id: Custom order ID

        Returns:
            Order information
        """
        if not self.validate_order_params(symbol, quantity, price, futures=False):
            raise ValueError("Invalid order parameters")

        params = {
            "symbol": symbol,
            "side": side.value,
            "type": order_type.value,
            "quantity": quantity
        }

        if price is not None:
            params["price"] = price

        if client_order_id:
            params["newClientOrderId"] = client_order_id

        # Add time in force for limit orders
        if order_type in [BinanceOrderType.LIMIT, BinanceOrderType.STOP_LOSS_LIMIT, BinanceOrderType.TAKE_PROFIT_LIMIT]:
            params["timeInForce"] = "GTC"  # Good Till Canceled

        response = await self._make_request(
            "POST",
            "/api/v3/order",
            params=params,
            signed=True,
            futures=False
        )

        return BinanceOrder(
            symbol=response["symbol"],
            order_id=response["orderId"],
            client_order_id=response["clientOrderId"],
            side=BinanceOrderSide(response["side"]),
            type=BinanceOrderType(response["type"]),
            status=BinanceOrderStatus(response["status"]),
            quantity=float(response["origQty"]),
            price=float(response["price"]) if response.get("price") else None,
            executed_qty=float(response["executedQty"]),
            cummulative_quote_qty=float(response["cummulativeQuoteQty"]),
            time=datetime.fromtimestamp(response["transactTime"] / 1000, tz=UTC),
            update_time=datetime.fromtimestamp(response["transactTime"] / 1000, tz=UTC)
        )

    async def place_futures_order(
        self,
        symbol: str,
        side: BinanceOrderSide,
        order_type: BinanceOrderType,
        quantity: float,
        price: Optional[float] = None,
        client_order_id: Optional[str] = None,
        reduce_only: bool = False
    ) -> BinanceOrder:
        """
        Place a futures trading order.

        Args:
            symbol: Trading symbol
            side: Order side (BUY/SELL)
            order_type: Order type
            quantity: Order quantity
            price: Order price (required for limit orders)
            client_order_id: Custom order ID
            reduce_only: Whether this is a reduce-only order

        Returns:
            Order information
        """
        if not self.validate_order_params(symbol, quantity, price, futures=True):
            raise ValueError("Invalid order parameters")

        params = {
            "symbol": symbol,
            "side": side.value,
            "type": order_type.value,
            "quantity": quantity
        }

        if price is not None:
            params["price"] = price

        if client_order_id:
            params["newClientOrderId"] = client_order_id

        if reduce_only:
            params["reduceOnly"] = "true"

        # Add time in force for limit orders
        if order_type in [BinanceOrderType.LIMIT, BinanceOrderType.STOP_LOSS_LIMIT, BinanceOrderType.TAKE_PROFIT_LIMIT]:
            params["timeInForce"] = "GTC"

        response = await self._make_request(
            "POST",
            "/fapi/v1/order",
            params=params,
            signed=True,
            futures=True
        )

        return BinanceOrder(
            symbol=response["symbol"],
            order_id=response["orderId"],
            client_order_id=response["clientOrderId"],
            side=BinanceOrderSide(response["side"]),
            type=BinanceOrderType(response["type"]),
            status=BinanceOrderStatus(response["status"]),
            quantity=float(response["origQty"]),
            price=float(response["price"]) if response.get("price") else None,
            executed_qty=float(response["executedQty"]),
            cummulative_quote_qty=float(response["cumQuote"]),
            time=datetime.fromtimestamp(response["updateTime"] / 1000, tz=UTC),
            update_time=datetime.fromtimestamp(response["updateTime"] / 1000, tz=UTC)
        )

    async def cancel_order(
        self,
        symbol: str,
        order_id: Optional[int] = None,
        client_order_id: Optional[str] = None,
        futures: bool = False
    ) -> dict[str, Any]:
        """
        Cancel an existing order.

        Args:
            symbol: Trading symbol
            order_id: Binance order ID
            client_order_id: Custom order ID
            futures: Whether this is a futures order

        Returns:
            Cancellation response
        """
        if not order_id and not client_order_id:
            raise ValueError("Either order_id or client_order_id must be provided")

        params = {"symbol": symbol}

        if order_id:
            params["orderId"] = order_id
        if client_order_id:
            params["origClientOrderId"] = client_order_id

        endpoint = "/fapi/v1/order" if futures else "/api/v3/order"

        return await self._make_request(
            "DELETE",
            endpoint,
            params=params,
            signed=True,
            futures=futures
        )

    async def get_order_status(
        self,
        symbol: str,
        order_id: Optional[int] = None,
        client_order_id: Optional[str] = None,
        futures: bool = False
    ) -> BinanceOrder:
        """
        Get order status.

        Args:
            symbol: Trading symbol
            order_id: Binance order ID
            client_order_id: Custom order ID
            futures: Whether this is a futures order

        Returns:
            Order information
        """
        if not order_id and not client_order_id:
            raise ValueError("Either order_id or client_order_id must be provided")

        params = {"symbol": symbol}

        if order_id:
            params["orderId"] = order_id
        if client_order_id:
            params["origClientOrderId"] = client_order_id

        endpoint = "/fapi/v1/order" if futures else "/api/v3/order"

        response = await self._make_request(
            "GET",
            endpoint,
            params=params,
            signed=True,
            futures=futures
        )

        return BinanceOrder(
            symbol=response["symbol"],
            order_id=response["orderId"],
            client_order_id=response["clientOrderId"],
            side=BinanceOrderSide(response["side"]),
            type=BinanceOrderType(response["type"]),
            status=BinanceOrderStatus(response["status"]),
            quantity=float(response["origQty"]),
            price=float(response["price"]) if response.get("price") else None,
            executed_qty=float(response["executedQty"]),
            cummulative_quote_qty=float(response.get("cummulativeQuoteQty", response.get("cumQuote", 0))),
            time=datetime.fromtimestamp(response["time"] / 1000, tz=UTC),
            update_time=datetime.fromtimestamp(response["updateTime"] / 1000, tz=UTC)
        )

    async def close(self) -> None:
        """Close HTTP client and WebSocket connections."""
        await self.client.aclose()

        for ws in self.ws_connections.values():
            if hasattr(ws, 'close'):
                await ws.close()

        self.logger.info("Binance adapter closed")
