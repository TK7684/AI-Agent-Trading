"""
Market Tools - Binance API integration
"""

import ccxt.async_support as ccxt
from typing import Dict, List, Optional
import asyncio


class MarketTools:
    """Tools for fetching market data from Binance."""

    def __init__(self):
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
        })

    async def get_binance_tickers(self) -> List[Dict]:
        """Get all trading pairs from Binance."""
        try:
            markets = await self.exchange.load_markets()
            tickers = []

            for symbol, market in markets.items():
                if market.get('active', False):
                    tickers.append({
                        'symbol': symbol,
                        'base': market.get('base'),
                        'quote': market.get('quote'),
                        'type': market.get('type'),
                    })

            return tickers

        except Exception as e:
            print(f"[MarketTools] Error fetching tickers: {e}")
            return []

    async def get_ticker_data(self, symbol: str) -> Optional[Dict]:
        """Get detailed ticker data for a symbol."""
        try:
            ticker = await self.exchange.fetch_ticker(symbol)

            # Calculate additional metrics
            return {
                'symbol': symbol,
                'last_price': ticker.get('last'),
                'high_24h': ticker.get('high'),
                'low_24h': ticker.get('low'),
                'volume_24h': ticker.get('baseVolume'),
                'quote_volume_24h': ticker.get('quoteVolume'),
                'price_change_percent_24h': ticker.get('percentage'),
                'market_cap': ticker.get('quoteVolume', 0),  # Approximate
                'price_from_ath_percent': self._estimate_ath_drop(ticker),
                'volume_spike_percent': self._calculate_volume_spike(ticker),
            }

        except Exception as e:
            print(f"[MarketTools] Error fetching ticker for {symbol}: {e}")
            return None

    async def get_ohlcv(self, symbol: str, timeframe: str = "1d", limit: int = 100) -> List[Dict]:
        """Get OHLCV (candlestick) data."""
        try:
            ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)

            return [
                {
                    'timestamp': c[0],
                    'open': c[1],
                    'high': c[2],
                    'low': c[3],
                    'close': c[4],
                    'volume': c[5],
                }
                for c in ohlcv
            ]

        except Exception as e:
            print(f"[MarketTools] Error fetching OHLCV for {symbol}: {e}")
            return []

    def _estimate_ath_drop(self, ticker: Dict) -> int:
        """Estimate percentage drop from all-time high."""
        high = ticker.get('high', ticker.get('last', 0))
        last = ticker.get('last', 0)

        if high > 0 and last > 0:
            drop = ((high - last) / high) * 100
            return int(drop)

        return 0

    def _calculate_volume_spike(self, ticker: Dict) -> int:
        """Calculate volume spike percentage (simplified)."""
        # In production, compare with average volume over period
        # For now, use a simple heuristic
        quote_vol = ticker.get('quoteVolume', 0)

        if quote_vol > 500_000_000:  # Very high volume
            return 400
        elif quote_vol > 200_000_000:
            return 350
        elif quote_vol > 100_000_000:
            return 300
        else:
            return 100

    async def close(self):
        """Close the exchange connection."""
        await self.exchange.close()
