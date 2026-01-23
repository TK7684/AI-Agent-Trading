"""
On-Chain Tools - Free Data Sources Only
Fetches on-chain metrics from free APIs and public sources.
NO PAID SERVICES - All integrations use free tiers.
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime
import aiohttp


class DuneAnalyticsTools:
    """
    Tools for fetching on-chain data from Dune Analytics.
    Free tier: 1,000 requests/month - no credit card required.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.base_url = "https://api.dune.com/api/v1"
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            headers = {}
            if self.api_key:
                headers["x-dune-api-key"] = self.api_key
            self.session = aiohttp.ClientSession(headers=headers)
        return self.session

    async def execute_query(
        self,
        query_id: int,
        parameters: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        Execute a Dune query by ID.
        Returns the query execution results.
        """
        if not self.api_key:
            print("[Dune] No API key provided - skipping Dune queries")
            return None

        try:
            session = await self._get_session()

            # Execute query
            execute_url = f"{self.base_url}/query/{query_id}/execute"
            execute_payload = {"parameters": parameters or {}}

            async with session.post(execute_url, json=execute_payload) as response:
                if response.status in [200, 201]:
                    execution_data = await response.json()
                    execution_id = execution_data.get("execution_id")

                    if not execution_id:
                        return None

                    # Poll for results
                    return await self._get_query_results(execution_id)
                else:
                    print(f"[Dune] Error executing query {query_id}: {response.status}")
                    return None

        except Exception as e:
            print(f"[Dune] Exception executing query {query_id}: {e}")
            return None

    async def _get_query_results(
        self,
        execution_id: str,
        max_attempts: int = 30,
        poll_interval: float = 1.0
    ) -> Optional[Dict]:
        """Poll for query execution results."""
        try:
            session = await self._get_session()
            results_url = f"{self.base_url}/execution/{execution_id}/results"

            for _ in range(max_attempts):
                await asyncio.sleep(poll_interval)

                async with session.get(results_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    elif response.status == 202:
                        # Still running, continue polling
                        continue
                    else:
                        print(f"[Dune] Error fetching results: {response.status}")
                        return None

            print(f"[Dune] Query {execution_id} timed out")
            return None

        except Exception as e:
            print(f"[Dune] Exception fetching results: {e}")
            return None

    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()


class CovalentTools:
    """
    Tools for fetching on-chain data from Covalent.
    Free tier: 300,000 requests/month - no credit card required.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.base_url = "https://api.covalent.com/v1"
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def get_token_holders(
        self,
        chain_id: int = 1,  # Ethereum mainnet
        contract_address: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get token holders from Covalent.
        Free tier: Supports multiple chains.
        """
        if not self.api_key or not contract_address:
            return []

        try:
            session = await self._get_session()
            url = f"{self.base_url}/{chain_id}/tokens/{contract_address}/token_holders/"

            params = {
                "key": self.api_key,
                "page-size": limit,
            }

            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("data", {}).get("items", [])
                else:
                    return []

        except Exception as e:
            print(f"[Covalent] Error fetching token holders: {e}")
            return []

    async def get_token_transfers(
        self,
        chain_id: int = 1,
        contract_address: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get recent token transfers."""
        if not self.api_key or not contract_address:
            return []

        try:
            session = await self._get_session()
            url = f"{self.base_url}/{chain_id}/tokens/{contract_address}/transfers/"

            params = {
                "key": self.api_key,
                "page-size": limit,
            }

            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("data", {}).get("items", [])
                else:
                    return []

        except Exception as e:
            print(f"[Covalent] Error fetching transfers: {e}")
            return []

    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()


class EthplorerTools:
    """
    Tools for fetching Ethereum data from Ethplorer.
    Free tier: No API key required for basic requests.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or "freekey"
        self.base_url = "https://api.ethplorer.io"
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def get_token_info(self, token_address: str) -> Optional[Dict]:
        """Get token information from Ethplorer."""
        try:
            session = await self._get_session()
            url = f"{self.base_url}/getTokenInfo/{token_address}"

            params = {"apiKey": self.api_key}

            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "address": data.get("address"),
                        "name": data.get("name"),
                        "symbol": data.get("symbol"),
                        "decimals": data.get("decimals"),
                        "totalSupply": data.get("totalSupply"),
                        "owner": data.get("owner"),
                        "txsCount": data.get("txsCount", 0),
                        "transfersCount": data.get("transfersCount", 0),
                        "holdersCount": data.get("holdersCount", 0),
                        "price": data.get("price", {}),
                    }
                else:
                    return None

        except Exception as e:
            print(f"[Ethplorer] Error fetching token info: {e}")
            return None

    async def get_top_token_holders(self, token_address: str, limit: int = 100) -> List[Dict]:
        """Get top token holders."""
        try:
            session = await self._get_session()
            url = f"{self.base_url}/getTopTokenHolders/{token_address}"

            params = {
                "apiKey": self.api_key,
                "limit": limit,
            }

            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("holders", [])
                else:
                    return []

        except Exception as e:
            print(f"[Ethplorer] Error fetching holders: {e}")
            return []

    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()


class OnChainAnalyzer:
    """
    Free on-chain analyzer using only free-tier APIs.
    NO PAID SERVICES - All free tiers or no key required.
    """

    def __init__(
        self,
        dune_api_key: Optional[str] = None,
        covalent_api_key: Optional[str] = None,
        ethplorer_api_key: Optional[str] = None,
    ):
        self.dune = DuneAnalyticsTools(dune_api_key) if dune_api_key else None
        self.covalent = CovalentTools(covalent_api_key) if covalent_api_key else None
        self.ethplorer = EthplorerTools(ethplorer_api_key)

    async def analyze_token_onchain_health(
        self,
        symbol: str,
        token_address: Optional[str] = None
    ) -> Dict:
        """
        Comprehensive on-chain health analysis using free APIs.
        Returns a score (0-100) and key metrics.
        """
        metrics = {}
        score = 50  # Base score

        # Ethplorer analysis (free, no key required)
        if token_address:
            try:
                token_info = await self.ethplorer.get_token_info(token_address)
                if token_info:
                    metrics["holders_count"] = token_info.get("holdersCount", 0)
                    metrics["transfers_count"] = token_info.get("transfersCount", 0)
                    metrics["txs_count"] = token_info.get("txsCount", 0)

                    # Score based on holder count
                    holders = metrics["holders_count"]
                    if holders > 10000:
                        score += 20
                    elif holders > 5000:
                        score += 15
                    elif holders > 1000:
                        score += 10

                    # Score based on activity
                    if metrics["transfers_count"] > 100000:
                        score += 10
                    elif metrics["transfers_count"] > 50000:
                        score += 5

            except Exception as e:
                print(f"[OnChain] Ethplorer analysis error: {e}")

        # Covalent analysis (free tier: 300k requests/month)
        if self.covalent and token_address:
            try:
                transfers = await self.covalent.get_token_transfers(
                    contract_address=token_address,
                    limit=50
                )

                if transfers:
                    metrics["recent_transfers"] = len(transfers)

                    # Check for whale activity
                    large_transfers = [
                        t for t in transfers
                        if float(t.get("transferEvent", {}).get("amount", 0)) > 1000
                    ]
                    metrics["whale_transfers_24h"] = len(large_transfers)

            except Exception as e:
                print(f"[OnChain] Covalent analysis error: {e}")

        # Dune Analytics (free tier: 1,000 requests/month)
        if self.dune and token_address:
            try:
                # Would need custom query IDs from your Dune account
                # This is a placeholder for future implementation
                pass
            except Exception as e:
                print(f"[OnChain] Dune analysis error: {e}")

        return {
            "symbol": symbol,
            "onchain_score": min(score, 100),
            "metrics": metrics,
            "grade": self._get_grade(min(score, 100)),
            "data_sources": self._get_data_sources_used(),
        }

    def _get_grade(self, score: int) -> str:
        """Convert score to grade."""
        if score >= 80:
            return "A"
        elif score >= 60:
            return "B"
        elif score >= 40:
            return "C"
        else:
            return "D"

    def _get_data_sources_used(self) -> List[str]:
        """List which data sources are active."""
        sources = ["Ethplorer (Free)"]
        if self.dune:
            sources.append("Dune Analytics (Free Tier)")
        if self.covalent:
            sources.append("Covalent (Free Tier)")
        return sources

    async def close(self):
        """Close all sessions."""
        if self.dune:
            await self.dune.close()
        if self.covalent:
            await self.covalent.close()
        await self.ethplorer.close()


# Free on-chain data alternatives (no API keys needed)

class FreeOnChainData:
    """
    Completely free on-chain data sources.
    No API keys required - uses public explorers and indices.
    """

    @staticmethod
    def get_etherscan_token_url(token_address: str) -> str:
        """Generate Etherscan token URL."""
        return f"https://etherscan.io/token/{token_address}"

    @staticmethod
    def get_bscscan_token_url(token_address: str) -> str:
        """Generate BscScan token URL."""
        return f"https://bscscan.com/token/{token_address}"

    @staticmethod
    def get_polygonscan_token_url(token_address: str) -> str:
        """Generate PolygonScan token URL."""
        return f"https://polygonscan.com/token/{token_address}"

    @staticmethod
    def get_defi_llama_protocol_url(protocol_slug: str) -> str:
        """Generate DeFi Llama protocol URL."""
        return f"https://defillama.com/protocol/{protocol_slug}"

    @staticmethod
    def get_nft_marketplace_url(collection_address: str, platform: str = "opensea") -> str:
        """Generate NFT marketplace URL."""
        if platform == "opensea":
            return f"https://opensea.io/assets/ethereum/{collection_address}"
        elif platform == "blur":
            return f"https://blur.io/asset/{collection_address}"
        return ""
