"""
Mock Market Data Provider
Simulates realistic market data for demo and testing purposes.
"""

import asyncio
import json
import logging
import random
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


class MockMarketDataProvider:
    """Provides realistic mock market data for trading simulations"""

    def __init__(self):
        self.base_prices = {
            "BTCUSDT": 45000.0,
            "ETHUSDT": 2500.0,
            "ADAUSDT": 0.5,
            "SOLUSDT": 100.0,
            "BNBUSDT": 300.0,
        }

        self.current_prices = self.base_prices.copy()
        self.price_history = {symbol: [] for symbol in self.base_prices}
        self.volatility = {symbol: 0.02 for symbol in self.base_prices}
        self.trends = {symbol: 0.0 for symbol in self.base_prices}

        # Initialize price history
        for symbol in self.base_prices:
            for _ in range(100):
                self._update_price_history(symbol)

    def _update_price_history(self, symbol: str) -> None:
        """Update price history with realistic movement"""
        if symbol not in self.current_prices:
            return

        # Get current state
        current_price = self.current_prices[symbol]
        vol = self.volatility[symbol]
        trend = self.trends[symbol]

        # Generate realistic price movement
        random_walk = random.gauss(0, vol)
        trend_component = trend * vol
        mean_reversion = (
            -0.1
            * (self.current_prices[symbol] - self.base_prices[symbol])
            / self.base_prices[symbol]
        )

        price_change = random_walk + trend_component + mean_reversion
        new_price = current_price * (1 + price_change)

        # Update price and history
        self.current_prices[symbol] = new_price
        self.price_history[symbol].append(new_price)

        # Keep only last 200 prices
        if len(self.price_history[symbol]) > 200:
            self.price_history[symbol] = self.price_history[symbol][-200:]

        # Occasionally change trend
        if random.random() < 0.01:  # 1% chance
            self.trends[symbol] = random.uniform(-0.5, 0.5)

    def _calculate_technical_indicators(self, symbol: str) -> Dict[str, float]:
        """Calculate realistic technical indicators"""
        if symbol not in self.price_history or len(self.price_history[symbol]) < 20:
            return self._default_indicators()

        prices = np.array(self.price_history[symbol][-50:])  # Last 50 prices

        # RSI calculation
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[-14:]) if len(gains) >= 14 else 0
        avg_loss = np.mean(losses[-14:]) if len(losses) >= 14 else 0

        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

        # MACD calculation (simplified)
        ema_12 = self._calculate_ema(prices, 12)
        ema_26 = self._calculate_ema(prices, 26)
        macd = ema_12 - ema_26

        # Bollinger Bands
        sma_20 = np.mean(prices[-20:])
        std_20 = np.std(prices[-20:])
        bb_upper = sma_20 + (2 * std_20)
        bb_lower = sma_20 - (2 * std_20)

        # Volume simulation
        base_volume = random.uniform(1000, 10000)
        volume_multiplier = 1 + abs(trend) + abs(random.gauss(0, 0.5))
        volume = base_volume * volume_multiplier

        # Volume MA
        volume_ma = np.mean([base_volume * random.uniform(0.5, 2.0) for _ in range(20)])

        # Recent price change
        price_change_24h = (
            ((prices[-1] / prices[-24]) - 1) * 100
            if len(prices) >= 24
            else random.uniform(-5, 5)
        )

        return {
            "rsi": float(np.clip(rsi, 0, 100)),
            "macd": float(macd),
            "bb_upper": float(bb_upper),
            "bb_lower": float(bb_lower),
            "bb_middle": float(sma_20),
            "volume": float(volume),
            "volume_ma": float(volume_ma),
            "change_24h": float(price_change_24h),
            "volatility": float(self.volatility[symbol]),
            "trend_strength": float(abs(self.trends[symbol])),
        }

    def _calculate_ema(self, prices: np.ndarray, period: int) -> float:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return float(np.mean(prices))

        alpha = 2 / (period + 1)
        ema = prices[0]

        for price in prices[1:]:
            ema = alpha * price + (1 - alpha) * ema

        return float(ema)

    def _default_indicators(self) -> Dict[str, float]:
        """Default indicators when insufficient data"""
        return {
            "rsi": random.uniform(30, 70),
            "macd": random.uniform(-0.5, 0.5),
            "bb_upper": 0,
            "bb_lower": 0,
            "bb_middle": 0,
            "volume": random.uniform(1000, 10000),
            "volume_ma": random.uniform(5000, 8000),
            "change_24h": random.uniform(-5, 5),
            "volatility": 0.02,
            "trend_strength": 0.1,
        }

    async def get_market_data(self, symbols: List[str]) -> Dict[str, Any]:
        """Get current market data for specified symbols"""
        market_data = {}

        for symbol in symbols:
            try:
                # Update price history
                self._update_price_history(symbol)

                # Get current price
                current_price = self.current_prices.get(
                    symbol, self.base_prices.get(symbol, 100)
                )

                # Calculate technical indicators
                indicators = self._calculate_technical_indicators(symbol)

                # Create comprehensive market data
                market_data[symbol] = {
                    "symbol": symbol,
                    "price": current_price,
                    "timestamp": datetime.now(timezone.utc),
                    **indicators,
                }

            except Exception as e:
                logger.error(f"Error generating mock data for {symbol}: {e}")
                continue

        return market_data

    async def stream_market_data(
        self, symbols: List[str], callback, interval: float = 1.0
    ):
        """Stream real-time market data"""
        logger.info(f"Starting market data stream for {symbols}")

        while True:
            try:
                market_data = await self.get_market_data(symbols)
                await callback(market_data)
                await asyncio.sleep(interval)

            except Exception as e:
                logger.error(f"Error in market data stream: {e}")
                await asyncio.sleep(5)

    def get_historical_data(
        self, symbol: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get historical price data"""
        if symbol not in self.price_history:
            return []

        historical_prices = self.price_history[symbol][-limit:]
        historical_data = []

        for i, price in enumerate(historical_prices):
            historical_data.append(
                {
                    "timestamp": (
                        datetime.now(timezone.utc) - timedelta(minutes=limit - i)
                    ).isoformat(),
                    "open": price * random.uniform(0.99, 1.01),
                    "high": price * random.uniform(1.0, 1.02),
                    "low": price * random.uniform(0.98, 1.0),
                    "close": price,
                    "volume": random.uniform(1000, 10000),
                }
            )

        return historical_data

    def add_symbol(self, symbol: str, base_price: float) -> None:
        """Add a new symbol to track"""
        self.base_prices[symbol] = base_price
        self.current_prices[symbol] = base_price
        self.price_history[symbol] = []
        self.volatility[symbol] = 0.02
        self.trends[symbol] = 0.0

        # Initialize price history
        for _ in range(100):
            self._update_price_history(symbol)

    def set_volatility(self, symbol: str, volatility: float) -> None:
        """Set volatility for a symbol"""
        if 0 < volatility < 1:
            self.volatility[symbol] = volatility

    def set_trend(self, symbol: str, trend: float) -> None:
        """Set trend for a symbol (-1 to 1)"""
        self.trends[symbol] = max(-1, min(1, trend))


class MarketDataSimulator:
    """Advanced market data simulator with realistic patterns"""

    def __init__(self):
        self.provider = MockMarketDataProvider()
        self.running = False

    async def start_simulation(self, symbols: List[str], interval: float = 1.0):
        """Start market data simulation"""
        self.running = True

        async def data_callback(market_data):
            # Process and log the data
            for symbol, data in market_data.items():
                logger.debug(f"{symbol}: ${data['price']:.2f} (RSI: {data['rsi']:.1f})")

        await self.provider.stream_market_data(symbols, data_callback, interval)

    def stop_simulation(self):
        """Stop market data simulation"""
        self.running = False

    def create_market_scenario(self, scenario: str):
        """Create specific market scenarios"""
        if scenario == "bull_market":
            # Set bullish trends
            for symbol in self.provider.trends:
                self.provider.set_trend(symbol, 0.3)
                self.provider.set_volatility(symbol, 0.015)

        elif scenario == "bear_market":
            # Set bearish trends
            for symbol in self.provider.trends:
                self.provider.set_trend(symbol, -0.3)
                self.provider.set_volatility(symbol, 0.025)

        elif scenario == "sideways":
            # Set sideways market
            for symbol in self.provider.trends:
                self.provider.set_trend(symbol, 0.0)
                self.provider.set_volatility(symbol, 0.01)

        elif scenario == "high_volatility":
            # High volatility scenario
            for symbol in self.provider.trends:
                self.provider.set_trend(symbol, random.uniform(-0.2, 0.2))
                self.provider.set_volatility(symbol, 0.05)


# Demo function
async def demo_market_data():
    """Demonstrate the mock market data provider"""
    provider = MockMarketDataProvider()

    print("📊 Mock Market Data Demo")
    print("=" * 50)

    # Get current market data
    symbols = ["BTCUSDT", "ETHUSDT"]
    market_data = await provider.get_market_data(symbols)

    for symbol, data in market_data.items():
        print(f"\n📈 {symbol}:")
        print(f"   Price: ${data['price']:.2f}")
        print(f"   RSI: {data['rsi']:.1f}")
        print(f"   MACD: {data['macd']:.4f}")
        print(f"   Volume: {data['volume']:,.0f}")
        print(f"   24h Change: {data['change_24h']:.2f}%")
        print(f"   Volatility: {data['volatility']:.3f}")


if __name__ == "__main__":
    asyncio.run(demo_market_data())
