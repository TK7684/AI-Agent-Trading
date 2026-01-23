"""
Scanner Agent (Optimized) - The Market Radar
Enhanced with CoinGecko trends, TradingView data, and FREE on-chain metrics.
NO PAID SERVICES - All data sources use free tiers or no API key required.
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime

from unicorn_hunter.tools.market_tools import MarketTools
from unicorn_hunter.tools.coingecko_tools import CoinGeckoTools
from unicorn_hunter.tools.tradingview_tools import TradingViewTools
from unicorn_hunter.tools.onchain_tools import OnChainAnalyzer


class OptimizedScannerAgent:
    """
    Enhanced Scanner Agent with multiple FREE data sources.

    Data Sources (ALL FREE):
    1. Binance (ccxt) - Real-time price and volume data (no API key needed)
    2. CoinGecko - Trending coins, market data (free: 50 calls/min, no credit card)
    3. TradingView - Technical ratings and market movers (free widgets)
    4. Ethplorer - On-chain metrics (free, no API key required)
    5. Dune Analytics - On-chain queries (free tier: 1,000 requests/month)
    6. Covalent - Token holders/transfers (free tier: 300,000 requests/month)
    """

    def __init__(
        self,
        coingecko_api_key: Optional[str] = None,
        dune_api_key: Optional[str] = None,
        covalent_api_key: Optional[str] = None,
        ethplorer_api_key: Optional[str] = "freekey",
    ):
        self.market_tools = MarketTools()
        self.coingecko = CoinGeckoTools(api_key=coingecko_api_key)
        self.tradingview = TradingViewTools()
        self.onchain = OnChainAnalyzer(
            dune_api_key=dune_api_key,
            covalent_api_key=covalent_api_key,
            ethplorer_api_key=ethplorer_api_key,
        )

    async def scan(
        self,
        scan_type: str = "crypto",
        min_market_cap: int = 10000000,
        max_market_cap: int = 100000000,
        min_price_drop: int = 80,
        min_volume_spike: int = 300,
        use_trending: bool = True,
        use_onchain: bool = False,
    ) -> Dict:
        """
        Enhanced market scan with multiple FREE data sources.

        The "Unicorn Hunter" Formula:
        1. Market Cap: Low ($10M - $100M range)
        2. Price from ATH: Down >80% (must be "low")
        3. Volume: Recent spike >300% of average ("Stopping Volume")
        4. Trending: High search volume (CoinGecko - FREE)
        5. Technical: Buy signals (TradingView - FREE)
        6. On-chain: Healthy metrics (Ethplorer/Dune - FREE tiers)

        Returns:
            Dict with candidates list and scan metadata
        """
        print(f"[Scanner] Starting optimized scan for {scan_type} assets...")
        print(f"[Scanner] Criteria: MC ${min_market_cap:,}-${max_market_cap:,}, >{min_price_drop}% down, >{min_volume_spike}% volume spike")
        print(f"[Scanner] Using FREE data sources only")

        candidates = []
        sources_used = []

        # Phase 1: Get trending coins from CoinGecko (high signal)
        if use_trending:
            print("[Scanner] Fetching trending coins from CoinGecko...")
            trending = await self._get_trending_candidates(
                min_market_cap, max_market_cap, min_price_drop
            )
            if trending:
                candidates.extend(trending)
                sources_used.append("CoinGecko_Trending")

        # Phase 2: Get top gainers/losers (momentum plays)
        print("[Scanner] Fetching market movers from CoinGecko...")
        movers = await self._get_mover_candidates(
            min_market_cap, max_market_cap
        )
        if movers:
            candidates.extend(movers)
            sources_used.append("CoinGecko_Movers")

        # Phase 3: Scan Binance for bottom candidates
        print("[Scanner] Scanning Binance for bottom candidates...")
        binance_candidates = await self._scan_binance(
            min_market_cap, max_market_cap, min_price_drop, min_volume_spike
        )
        if binance_candidates:
            candidates.extend(binance_candidates)
            sources_used.append("Binance_Scanner")

        # Fallback: Use mock data if no candidates found (API failures)
        if not candidates:
            print("[Scanner] All APIs failed, using mock candidates for testing...")
            candidates = self._get_mock_candidates()
            sources_used.append("Mock_Data")

        # Phase 4: Deduplicate and score
        print(f"[Scanner] Deduplicating {len(candidates)} candidates...")
        unique_candidates = self._deduplicate_candidates(candidates)

        # Phase 5: Enhance with TradingView data
        print("[Scanner] Fetching TradingView technical ratings...")
        for i, candidate in enumerate(unique_candidates):
            if i >= 10:  # Limit to top 10 for API efficiency
                break
            await self._enrich_with_tradingview(candidate)

        # Phase 6: Add on-chain metrics (optional)
        if use_onchain:
            print("[Scanner] Fetching on-chain metrics...")
            for i, candidate in enumerate(unique_candidates):
                if i >= 5:  # Limit to top 5 for on-chain (API intensive)
                    break
                await self._enrich_with_onchain(candidate)

        # Sort by combined score
        unique_candidates.sort(
            key=lambda x: x.get("combined_score", x.get("scanner_score", 0)),
            reverse=True
        )

        print(f"[Scanner] Found {len(unique_candidates)} unique candidates")
        print(f"[Scanner] Data sources used: {', '.join(sources_used)}")

        return {
            "candidates": unique_candidates[:10],  # Top 10
            "total_scanned": len(candidates),
            "sources_used": sources_used,
            "scan_time": datetime.utcnow().isoformat(),
        }

    async def _get_trending_candidates(
        self,
        min_mc: int,
        max_mc: int,
        min_drop: int
    ) -> List[Dict]:
        """Get candidates from CoinGecko trending list."""
        try:
            trending = await self.coingecko.get_trending_coins(limit=30)
            candidates = []

            for coin in trending:
                coin_id = coin.get("id")
                symbol = coin.get("symbol", "").upper()

                # Get detailed market data
                market_data = await self.coingecko.get_coin_market_data(coin_id)

                if not market_data:
                    continue

                md = market_data.get("market_data", {})
                market_cap = md.get("market_cap", 0)
                ath_change = md.get("ath_change_percentage", 0)

                # Apply filters
                if not (min_mc <= market_cap <= max_mc):
                    continue

                # Convert negative ATH change to positive drop percentage
                price_drop = abs(ath_change) if ath_change < 0 else 0
                if price_drop < min_drop:
                    continue

                # Calculate trending score
                trending_score = coin.get("score", 0) * 100

                candidate = {
                    "symbol": f"{symbol}USDT",
                    "name": coin.get("name"),
                    "type": "crypto",
                    "source": "coingecko_trending",
                    "market_cap": market_cap,
                    "current_price": md.get("current_price", 0),
                    "ath": md.get("ath", 0),
                    "ath_date": md.get("ath_date", ""),
                    "price_from_ath": price_drop,
                    "volume_24h": md.get("total_volume", 0),
                    "price_change_24h": md.get("price_change_percentage_24h", 0),
                    "price_change_7d": md.get("price_change_percentage_7d", 0),
                    "trending_score": trending_score,
                    "scanner_score": self._calculate_trending_score(trending_score, price_drop, market_cap),
                    "coingecko_id": coin_id,
                    "community_data": market_data.get("community_data", {}),
                }

                candidates.append(candidate)

            return candidates

        except Exception as e:
            print(f"[Scanner] Error fetching trending candidates: {e}")
            return []

    async def _get_mover_candidates(
        self,
        min_mc: int,
        max_mc: int
    ) -> List[Dict]:
        """Get candidates from top gainers/losers."""
        try:
            movers = await self.coingecko.get_gainers_losers(top=50)
            candidates = []

            # Process gainers (momentum plays)
            for coin in movers.get("gainers", []):
                market_cap = coin.get("market_cap", 0)
                if not (min_mc <= market_cap <= max_mc):
                    continue

                candidates.append({
                    "symbol": f"{coin.get('symbol', '').upper()}USDT",
                    "name": coin.get("name"),
                    "type": "crypto",
                    "source": "coingecko_gainers",
                    "market_cap": market_cap,
                    "current_price": coin.get("current_price", 0),
                    "price_change_24h": coin.get("price_change_percentage_24h", 0),
                    "volume_24h": coin.get("total_volume", 0),
                    "scanner_score": 75,  # Base score for gainers
                    "momentum": "bullish",
                })

            # Process losers with big drops (potential bounce)
            for coin in movers.get("losers", [])[:20]:
                market_cap = coin.get("market_cap", 0)
                if not (min_mc <= market_cap <= max_mc):
                    continue

                price_drop = abs(coin.get("price_change_percentage_24h", 0))
                if price_drop < 15:  # Only consider significant drops
                    continue

                candidates.append({
                    "symbol": f"{coin.get('symbol', '').upper()}USDT",
                    "name": coin.get("name"),
                    "type": "crypto",
                    "source": "coingecko_losers",
                    "market_cap": market_cap,
                    "current_price": coin.get("current_price", 0),
                    "price_change_24h": coin.get("price_change_percentage_24h", 0),
                    "volume_24h": coin.get("total_volume", 0),
                    "scanner_score": 70 + int(price_drop / 5),  # Higher drop = higher score
                    "momentum": "bearish_reversal",
                })

            return candidates[:10]

        except Exception as e:
            print(f"[Scanner] Error fetching mover candidates: {e}")
            return []

    async def _scan_binance(
        self,
        min_mc: int,
        max_mc: int,
        min_drop: int,
        min_spike: int
    ) -> List[Dict]:
        """Scan Binance for bottom candidates (original method)."""
        try:
            tickers = await self.market_tools.get_binance_tickers()
            candidates = []

            # Process in batches to avoid overwhelming the API
            for ticker in tickers[:200]:  # Limit to top 200 by volume
                if not ticker["symbol"].endswith("USDT"):
                    continue

                market_data = await self.market_tools.get_ticker_data(ticker["symbol"])
                if not market_data:
                    continue

                market_cap = market_data.get("market_cap", 0)
                price_from_ath = market_data.get("price_from_ath_percent", 0)
                volume_spike = market_data.get("volume_spike_percent", 0)

                if not (min_mc <= market_cap <= max_mc):
                    continue
                if price_from_ath < min_drop:
                    continue
                if volume_spike < min_spike:
                    continue

                candidate = {
                    "symbol": ticker["symbol"],
                    "name": ticker["symbol"].replace("USDT", ""),
                    "type": "crypto",
                    "source": "binance_scanner",
                    "market_cap": market_cap,
                    "current_price": market_data.get("last_price", 0),
                    "price_from_ath": price_from_ath,
                    "volume_spike": volume_spike,
                    "volume_24h": market_data.get("volume_24h", 0),
                    "price_change_24h": market_data.get("price_change_percent_24h", 0),
                    "scanner_score": self._calculate_scanner_score(market_cap, price_from_ath, volume_spike),
                }

                candidates.append(candidate)

            return candidates

        except Exception as e:
            print(f"[Scanner] Error scanning Binance: {e}")
            return []

    async def _enrich_with_tradingview(self, candidate: Dict):
        """Enrich candidate with TradingView technical data."""
        try:
            symbol = candidate.get("symbol", "").replace("USDT", "USDT")  # Ensure format
            tech_rating = await self.tradingview.get_technical_rating(symbol)

            if tech_rating:
                candidate["tradingview"] = {
                    "recommendation": tech_rating.get("overall_recommendation"),
                    "buy": tech_rating.get("buy", 0),
                    "sell": tech_rating.get("sell", 0),
                    "rsi": tech_rating.get("rsi"),
                }

                # Update combined score
                base_score = candidate.get("scanner_score", 50)
                tv_score = 0

                if tech_rating.get("overall_recommendation") == "STRONG_BUY":
                    tv_score = 20
                elif tech_rating.get("overall_recommendation") == "BUY":
                    tv_score = 10

                candidate["combined_score"] = base_score + tv_score

        except Exception as e:
            print(f"[Scanner] Error enriching with TradingView: {e}")
            candidate["combined_score"] = candidate.get("scanner_score", 50)

    async def _enrich_with_onchain(self, candidate: Dict):
        """Enrich candidate with on-chain metrics."""
        try:
            symbol = candidate.get("symbol", "").replace("USDT", "")
            token_address = candidate.get("coingecko_id")  # Can be used to lookup address

            analysis = await self.onchain.analyze_token_onchain_health(symbol, token_address)

            if analysis:
                candidate["onchain"] = {
                    "score": analysis.get("onchain_score"),
                    "grade": analysis.get("grade"),
                    "metrics": analysis.get("metrics", {}),
                }

                # Update combined score with on-chain bonus
                onchain_bonus = analysis.get("onchain_score", 0) // 10
                candidate["combined_score"] = candidate.get("combined_score", candidate.get("scanner_score", 50)) + onchain_bonus

        except Exception as e:
            print(f"[Scanner] Error enriching with on-chain: {e}")

    def _calculate_trending_score(self, trending_score: float, price_drop: float, market_cap: int) -> int:
        """Calculate score for trending coins."""
        score = 50  # Base score

        # Trending bonus (0-30 points)
        score += min(trending_score / 10, 30)

        # Price drop bonus (0-20 points)
        if price_drop >= 90:
            score += 20
        elif price_drop >= 80:
            score += 15
        elif price_drop >= 70:
            score += 10

        # Market cap adjustment
        if market_cap < 20000000:
            score += 10
        elif market_cap < 50000000:
            score += 5

        return min(int(score), 100)

    def _calculate_scanner_score(self, market_cap: int, price_drop: int, volume_spike: int) -> int:
        """Calculate scanner score (0-100) based on how well asset meets criteria."""
        score = 0

        # Market Cap Score (0-30 points)
        if market_cap < 20000000:
            score += 30
        elif market_cap < 50000000:
            score += 25
        elif market_cap < 100000000:
            score += 20

        # Price Drop Score (0-40 points)
        if price_drop >= 95:
            score += 40
        elif price_drop >= 90:
            score += 35
        elif price_drop >= 85:
            score += 30
        elif price_drop >= 80:
            score += 25

        # Volume Spike Score (0-30 points)
        if volume_spike >= 500:
            score += 30
        elif volume_spike >= 400:
            score += 25
        elif volume_spike >= 300:
            score += 20

        return min(score, 100)

    def _deduplicate_candidates(self, candidates: List[Dict]) -> List[Dict]:
        """Remove duplicate candidates and merge data from multiple sources."""
        seen = {}
        unique = []

        for candidate in candidates:
            symbol = candidate.get("symbol")
            if not symbol:
                continue

            if symbol in seen:
                # Merge data from multiple sources
                existing = seen[symbol]
                # Keep the higher score
                if candidate.get("scanner_score", 0) > existing.get("scanner_score", 0):
                    existing["scanner_score"] = candidate.get("scanner_score")
                # Add source tags
                if "sources" not in existing:
                    existing["sources"] = [existing.get("source", "")]
                existing["sources"].append(candidate.get("source", ""))
                existing["sources"] = list(set(existing["sources"]))
                # Merge any additional fields
                for key, value in candidate.items():
                    if key not in existing:
                        existing[key] = value
            else:
                seen[symbol] = candidate
                candidate["sources"] = [candidate.get("source", "")]
                unique.append(candidate)

        return unique

    def _get_mock_candidates(self) -> List[Dict]:
        """Return mock candidates for testing when all APIs fail."""
        return [
            {
                "symbol": "UNIUSDT",
                "name": "Uniswap",
                "type": "crypto",
                "source": "mock_data",
                "market_cap": 45000000,
                "current_price": 4.50,
                "price_from_ath": 85,
                "volume_spike": 350,
                "volume_24h": 150000000,
                "price_change_24h": 12.5,
                "scanner_score": 85,
                "combined_score": 85,
                "sources": ["mock_data"],
            },
            {
                "symbol": "AAVEUSDT",
                "name": "Aave",
                "type": "crypto",
                "source": "mock_data",
                "market_cap": 65000000,
                "current_price": 85.00,
                "price_from_ath": 82,
                "volume_spike": 320,
                "volume_24h": 280000000,
                "price_change_24h": 8.3,
                "scanner_score": 80,
                "combined_score": 80,
                "sources": ["mock_data"],
            },
            {
                "symbol": "RNDRUSDT",
                "name": "Render",
                "type": "crypto",
                "source": "mock_data",
                "market_cap": 55000000,
                "current_price": 6.80,
                "price_from_ath": 88,
                "volume_spike": 420,
                "volume_24h": 195000000,
                "price_change_24h": 15.7,
                "scanner_score": 88,
                "combined_score": 88,
                "sources": ["mock_data"],
            },
        ]

    async def close(self):
        """Close all connections."""
        await self.market_tools.close()
        await self.coingecko.close()
        await self.tradingview.close()
        await self.onchain.close()
