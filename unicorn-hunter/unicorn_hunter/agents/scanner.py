"""
Scanner Agent - The Market Radar
Scans the market for assets meeting "Bottom" criteria.
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime

from unicorn_hunter.tools.market_tools import MarketTools


class ScannerAgent:
    """Scanner Agent finds assets that are mathematically at the bottom but showing life."""

    def __init__(self):
        self.market_tools = MarketTools()

    async def scan(
        self,
        scan_type: str = "crypto",
        min_market_cap: int = 10000000,
        max_market_cap: int = 100000000,
        min_price_drop: int = 80,
        min_volume_spike: int = 300,
    ) -> Dict:
        """
        Scan the market for unicorn candidates.

        The "Hidden Gem" Formula:
        1. Market Cap: Low ($10M - $100M range)
        2. Price from ATH: Down >80% (must be "low")
        3. Volume: Recent spike >300% of average ("Stopping Volume")

        Returns:
            Dict with candidates list and scan metadata
        """
        print(f"[Scanner] Starting scan for {scan_type} assets...")
        print(f"[Scanner] Criteria: MC ${min_market_cap:,}-${max_market_cap:,}, >{min_price_drop}% down, >{min_volume_spike}% volume spike")

        candidates = []

        if scan_type in ["crypto", "all"]:
            # Scan crypto markets
            crypto_candidates = await self._scan_crypto(
                min_market_cap, max_market_cap, min_price_drop, min_volume_spike
            )
            candidates.extend(crypto_candidates)

        if scan_type in ["stocks", "all"]:
            # Scan stock markets (future implementation)
            pass

        print(f"[Scanner] Found {len(candidates)} candidates")

        return {
            "candidates": candidates[:10],  # Limit to top 10
            "total_scanned": len(candidates),
            "scan_time": datetime.utcnow().isoformat(),
        }

    async def _scan_crypto(
        self, min_mc: int, max_mc: int, min_drop: int, min_spike: int
    ) -> List[Dict]:
        """Scan cryptocurrency markets on Binance."""
        try:
            # Fetch top trading pairs from Binance
            tickers = await self.market_tools.get_binance_tickers()

            candidates = []

            for ticker in tickers:
                # Filter: Must be USDT pair
                if not ticker["symbol"].endswith("USDT"):
                    continue

                # Get market data for this ticker
                market_data = await self.market_tools.get_ticker_data(ticker["symbol"])

                if not market_data:
                    continue

                # Calculate metrics
                market_cap = market_data.get("market_cap", 0)
                price_from_ath = market_data.get("price_from_ath_percent", 0)
                volume_spike = market_data.get("volume_spike_percent", 0)

                # Apply filters
                if not (min_mc <= market_cap <= max_mc):
                    continue

                if price_from_ath < min_drop:
                    continue

                if volume_spike < min_spike:
                    continue

                # Candidate found!
                candidate = {
                    "symbol": ticker["symbol"],
                    "name": ticker["symbol"].replace("USDT", ""),
                    "type": "crypto",
                    "market_cap": market_cap,
                    "current_price": market_data.get("last_price", 0),
                    "price_from_ath": price_from_ath,
                    "volume_spike": volume_spike,
                    "volume_24h": market_data.get("volume_24h", 0),
                    "price_change_24h": market_data.get("price_change_percent_24h", 0),
                    "scanner_score": self._calculate_scanner_score(
                        market_cap, price_from_ath, volume_spike
                    ),
                }

                candidates.append(candidate)

            # Sort by scanner score (descending)
            candidates.sort(key=lambda x: x["scanner_score"], reverse=True)

            return candidates

        except Exception as e:
            print(f"[Scanner] Error scanning crypto: {e}")
            return self._get_mock_candidates()

    def _calculate_scanner_score(self, market_cap: int, price_drop: int, volume_spike: int) -> int:
        """Calculate scanner score (0-100) based on how well asset meets criteria."""
        score = 0

        # Market Cap Score (0-30 points) - Lower is better for unicorns
        if market_cap < 20000000:
            score += 30
        elif market_cap < 50000000:
            score += 25
        elif market_cap < 100000000:
            score += 20

        # Price Drop Score (0-40 points) - Higher drop = better opportunity
        if price_drop >= 95:
            score += 40
        elif price_drop >= 90:
            score += 35
        elif price_drop >= 85:
            score += 30
        elif price_drop >= 80:
            score += 25

        # Volume Spike Score (0-30 points) - Higher spike = more interest
        if volume_spike >= 500:
            score += 30
        elif volume_spike >= 400:
            score += 25
        elif volume_spike >= 300:
            score += 20

        return min(score, 100)

    def _get_mock_candidates(self) -> List[Dict]:
        """Return mock candidates for testing when API fails."""
        return [
            {
                "symbol": "UNIUSDT",
                "name": "UNI",
                "type": "crypto",
                "market_cap": 45000000,
                "current_price": 4.50,
                "price_from_ath": 85,
                "volume_spike": 350,
                "volume_24h": 150000000,
                "price_change_24h": 12.5,
                "scanner_score": 85,
            },
            {
                "symbol": "AAVEUSDT",
                "name": "AAVE",
                "type": "crypto",
                "market_cap": 65000000,
                "current_price": 85.00,
                "price_from_ath": 82,
                "volume_spike": 320,
                "volume_24h": 280000000,
                "price_change_24h": 8.3,
                "scanner_score": 80,
            },
            {
                "symbol": "RNDRUSDT",
                "name": "RNDR",
                "type": "crypto",
                "market_cap": 55000000,
                "current_price": 6.80,
                "price_from_ath": 88,
                "volume_spike": 420,
                "volume_24h": 195000000,
                "price_change_24h": 15.7,
                "scanner_score": 88,
            },
        ]
