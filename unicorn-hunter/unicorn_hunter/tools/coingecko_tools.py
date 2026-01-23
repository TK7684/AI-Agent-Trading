"""
CoinGecko Tools - Trend Discovery & Market Data
Leverages CoinGecko API for trending coins, market data, and sentiment.
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime
import aiohttp


class CoinGeckoTools:
    """Tools for fetching market data and trends from CoinGecko."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.base_url = "https://api.coingecko.com/api/v3"
        self.pro_base_url = "https://pro-api.coingecko.com/api/v3"
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            headers = {}
            if self.api_key:
                headers["x-cg-pro-api-key"] = self.api_key
            self.session = aiohttp.ClientSession(headers=headers)
        return self.session

    async def get_trending_coins(self, limit: int = 20) -> List[Dict]:
        """
        Get trending coins from CoinGecko.
        These are coins with highest search volume and price interest.
        """
        try:
            session = await self._get_session()
            url = f"{self.base_url}/search/trending"

            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    trending = []

                    for item in data.get("coins", [])[:limit]:
                        coin = item.get("item", {})

                        trending.append({
                            "id": coin.get("id"),
                            "symbol": coin.get("symbol", "").upper(),
                            "name": coin.get("name"),
                            "market_cap_rank": coin.get("market_cap_rank"),
                            "score": coin.get("score", 0),  # Trending score
                            "price_btc": coin.get("price_btc"),
                            "thumb": coin.get("thumb"),
                            "small": coin.get("small"),
                            "large": coin.get("large"),
                            "slug": coin.get("slug"),
                        })

                    return trending
                else:
                    print(f"[CoinGecko] Error fetching trending: {response.status}")
                    return []

        except Exception as e:
            print(f"[CoinGecko] Exception fetching trending: {e}")
            return []

    async def get_coin_market_data(
        self,
        coin_id: str,
        vs_currency: str = "usd"
    ) -> Optional[Dict]:
        """
        Get detailed market data for a specific coin.
        Includes price, market cap, volume, ATH, circulating supply, etc.
        """
        try:
            session = await self._get_session()
            url = f"{self.base_url}/coins/{coin_id}"

            params = {
                "localization": "false",
                "tickers": "false",
                "market_data": "true",
                "community_data": "true",
                "developer_data": "true",
            }

            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    market_data = data.get("market_data", {})

                    return {
                        "id": data.get("id"),
                        "symbol": data.get("symbol", "").upper(),
                        "name": data.get("name"),
                        "hashing_algorithm": data.get("hashing_algorithm"),
                        "categories": data.get("categories", []),
                        "public_interest_score": data.get("public_interest_score"),
                        "public_interest_stats": data.get("public_interest_stats", {}),
                        "market_data": {
                            "current_price": market_data.get("current_price", {}).get(vs_currency),
                            "ath": market_data.get("ath", {}).get(vs_currency),
                            "ath_date": market_data.get("ath_date", {}).get(vs_currency),
                            "ath_change_percentage": market_data.get("ath_change_percentage", {}).get(vs_currency),
                            "atl": market_data.get("atl", {}).get(vs_currency),
                            "atl_date": market_data.get("atl_date", {}).get(vs_currency),
                            "atl_change_percentage": market_data.get("atl_change_percentage", {}).get(vs_currency),
                            "market_cap": market_data.get("market_cap", {}).get(vs_currency),
                            "market_cap_rank": market_data.get("market_cap_rank"),
                            "fully_diluted_valuation": market_data.get("fully_diluted_valuation", {}).get(vs_currency),
                            "total_volume": market_data.get("total_volume", {}).get(vs_currency),
                            "high_24h": market_data.get("high_24h", {}).get(vs_currency),
                            "low_24h": market_data.get("low_24h", {}).get(vs_currency),
                            "price_change_24h": market_data.get("price_change_24h"),
                            "price_change_percentage_24h": market_data.get("price_change_percentage_24h"),
                            "price_change_percentage_7d": market_data.get("price_change_percentage_7d"),
                            "price_change_percentage_30d": market_data.get("price_change_percentage_30d"),
                            "circulating_supply": market_data.get("circulating_supply"),
                            "total_supply": market_data.get("total_supply"),
                            "max_supply": market_data.get("max_supply"),
                        },
                        "community_data": {
                            "twitter_followers": data.get("community_data", {}).get("twitter_followers"),
                            "reddit_subscribers": data.get("community_data", {}).get("reddit_subscribers"),
                            "telegram_users": data.get("community_data", {}).get("telegram_channel_user_count"),
                        },
                        "developer_data": {
                            "forks": data.get("developer_data", {}).get("forks"),
                            "stars": data.get("developer_data", {}).get("stars"),
                            "subscribers": data.get("developer_data", {}).get("subscribers"),
                            "total_issues": data.get("developer_data", {}).get("total_issues"),
                            "closed_issues": data.get("developer_data", {}).get("closed_issues"),
                        },
                    }
                else:
                    print(f"[CoinGecko] Error fetching market data for {coin_id}: {response.status}")
                    return None

        except Exception as e:
            print(f"[CoinGecko] Exception fetching market data for {coin_id}: {e}")
            return None

    async def get_coins_by_market_cap(
        self,
        vs_currency: str = "usd",
        per_page: int = 250,
        page: int = 1,
        min_market_cap: Optional[int] = None,
        max_market_cap: Optional[int] = None
    ) -> List[Dict]:
        """
        Get coins by market cap range.
        Useful for finding small-cap gems.
        """
        try:
            session = await self._get_session()
            url = f"{self.base_url}/coins/markets"

            params = {
                "vs_currency": vs_currency,
                "order": "market_cap_desc",
                "per_page": per_page,
                "page": page,
                "sparkline": "false",
            }

            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    coins = []

                    for coin in data:
                        market_cap = coin.get("market_cap", 0)

                        # Apply filters
                        if min_market_cap and market_cap < min_market_cap:
                            continue
                        if max_market_cap and market_cap > max_market_cap:
                            continue

                        coins.append({
                            "id": coin.get("id"),
                            "symbol": coin.get("symbol", "").upper(),
                            "name": coin.get("name"),
                            "image": coin.get("image"),
                            "current_price": coin.get("current_price"),
                            "market_cap": market_cap,
                            "market_cap_rank": coin.get("market_cap_rank"),
                            "fully_diluted_valuation": coin.get("fully_diluted_valuation"),
                            "total_volume": coin.get("total_volume"),
                            "high_24h": coin.get("high_24h"),
                            "low_24h": coin.get("low_24h"),
                            "price_change_24h": coin.get("price_change_24h"),
                            "price_change_percentage_24h": coin.get("price_change_percentage_24h"),
                            "price_change_percentage_7d_in_currency": coin.get("price_change_percentage_7d_in_currency"),
                            "price_change_percentage_30d_in_currency": coin.get("price_change_percentage_30d_in_currency"),
                            "ath": coin.get("ath"),
                            "ath_change_percentage": coin.get("ath_change_percentage"),
                            "atl": coin.get("atl"),
                            "atl_change_percentage": coin.get("atl_change_percentage"),
                            "circulating_supply": coin.get("circulating_supply"),
                            "total_supply": coin.get("total_supply"),
                            "max_supply": coin.get("max_supply"),
                        })

                    return coins
                else:
                    print(f"[CoinGecko] Error fetching coins by market cap: {response.status}")
                    return []

        except Exception as e:
            print(f"[CoinGecko] Exception fetching coins by market cap: {e}")
            return []

    async def get_coin_price_history(
        self,
        coin_id: str,
        vs_currency: str = "usd",
        days: int = 30
    ) -> List[Dict]:
        """
        Get historical price data for a coin.
        Useful for charting and trend analysis.
        """
        try:
            session = await self._get_session()
            url = f"{self.base_url}/coins/{coin_id}/market_chart"

            params = {
                "vs_currency": vs_currency,
                "days": days,
            }

            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    prices = data.get("prices", [])
                    market_caps = data.get("market_caps", [])
                    volumes = data.get("total_volumes", [])

                    return [
                        {
                            "timestamp": p[0],
                            "price": p[1],
                            "market_cap": mc[1] if i < len(market_caps) else None,
                            "volume": v[1] if i < len(volumes) else None,
                        }
                        for i, p in enumerate(prices)
                    ]
                else:
                    return []

        except Exception as e:
            print(f"[CoinGecko] Exception fetching price history for {coin_id}: {e}")
            return []

    async def search_coins(self, query: str) -> List[Dict]:
        """
        Search for coins by name, symbol, or ID.
        """
        try:
            session = await self._get_session()
            url = f"{self.base_url}/search"

            params = {"query": query}

            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    coins = data.get("coins", [])

                    return [
                        {
                            "id": coin.get("id"),
                            "name": coin.get("name"),
                            "symbol": coin.get("symbol", "").upper(),
                            "market_cap_rank": coin.get("market_cap_rank"),
                            "thumb": coin.get("thumb"),
                            "large": coin.get("large"),
                        }
                        for coin in coins
                    ]
                else:
                    return []

        except Exception as e:
            print(f"[CoinGecko] Exception searching coins: {e}")
            return []

    async def get_gainers_losers(
        self,
        vs_currency: str = "usd",
        duration: str = "24h",
        top: int = 50
    ) -> Dict[str, List[Dict]]:
        """
        Get top gainers and losers.
        Duration: 1h, 24h, 7d, 14d, 30d, 1y
        """
        try:
            session = await self._get_session()
            url = f"{self.base_url}/coins/markets"

            params = {
                "vs_currency": vs_currency,
                "order": "price_change_percentage_24h_desc",  # Default
                "per_page": top * 2,  # Get more to find both gainers and losers
                "page": 1,
                "sparkline": "false",
            }

            # Map duration to order parameter
            duration_map = {
                "1h": "price_change_percentage_1h_in_currency",
                "24h": "price_change_percentage_24h",
                "7d": "price_change_percentage_7d_in_currency",
                "14d": "price_change_percentage_14d_in_currency",
                "30d": "price_change_percentage_30d_in_currency",
                "1y": "price_change_percentage_1y_in_currency",
            }

            if duration in duration_map:
                params["order"] = f"{duration_map[duration]}_desc"

            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    gainers = [coin for coin in data[:top] if coin.get(f"price_change_percentage_{duration}_in_currency" if duration != "24h" else "price_change_percentage_24h", 0) > 0]
                    losers = [coin for coin in data if coin.get(f"price_change_percentage_{duration}_in_currency" if duration != "24h" else "price_change_percentage_24h", 0) < 0][:top]

                    return {
                        "gainers": gainers[:top],
                        "losers": losers[:top],
                    }
                else:
                    return {"gainers": [], "losers": []}

        except Exception as e:
            print(f"[CoinGecko] Exception fetching gainers/losers: {e}")
            return {"gainers": [], "losers": []}

    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
