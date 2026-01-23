"""
TradingView Tools - Chart Analysis & Widget Generation
Provides integration with TradingView for technical analysis and chart widgets.
"""

import json
from typing import Dict, List, Optional
from datetime import datetime
import aiohttp


class TradingViewTools:
    """
    Tools for TradingView integration.
    Generates widget embed codes and fetches technical data.
    """

    def __init__(self):
        self.base_url = "https://scanner.tradingview.com"
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    def generate_chart_widget(
        self,
        symbol: str,
        exchange: str = "BINANCE",
        theme: str = "dark",
        height: int = 500,
        width: str = "100%",
        interval: str = "D",
        style: str = "1"
    ) -> Dict:
        """
        Generate TradingView Advanced Chart Widget embed code.

        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
            exchange: Exchange name (e.g., "BINANCE", "COINBASE")
            theme: "light" or "dark"
            height: Widget height in pixels
            width: Widget width (pixels or percentage)
            interval: Default timeframe ("1", "5", "15", "30", "60", "240", "D", "W", "M")
            style: Chart style ("1"=Bars, "2"=Candles, "3"=Line, "4"=Area)

        Returns:
            Dict with HTML embed code and configuration
        """
        tv_symbol = f"{exchange}:{symbol}"

        widget_config = {
            "autosize": True,
            "symbol": tv_symbol,
            "interval": interval,
            "timezone": "Etc/UTC",
            "theme": theme,
            "style": style,
            "locale": "en",
            "enable_publishing": False,
            "hide_side_toolbar": False,
            "allow_symbol_change": True,
            "calendar": False,
            "support_host": "https://www.tradingview.com",
        }

        html_code = f'''
<!-- TradingView Widget BEGIN -->
<div class="tradingview-widget-container" style="height:{height}px;width:{width}">
    <div id="tradingview_{symbol.lower()}"></div>
    <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
    <script type="text/javascript">
        new TradingView.widget({json.dumps(widget_config)});
    </script>
</div>
<!-- TradingView Widget END -->
'''

        return {
            "symbol": symbol,
            "tv_symbol": tv_symbol,
            "html": html_code.strip(),
            "config": widget_config,
        }

    def generate_ticker_tape_widget(
        self,
        symbols: List[str],
        theme: str = "dark",
        width: str = "100%"
    ) -> Dict:
        """
        Generate TradingView Ticker Tape Widget embed code.

        Args:
            symbols: List of symbols (e.g., ["BINANCE:BTCUSDT", "COINBASE:ETHUSD"])
            theme: "light" or "dark"
            width: Widget width

        Returns:
            Dict with HTML embed code
        """
        html_code = f'''
<!-- TradingView Ticker Tape Widget BEGIN -->
<div class="tradingview-widget-container">
    <div class="tradingview-widget-container__widget"></div>
    <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js" async>
    {{
        "symbols": {json.dumps(symbols)},
        "showSymbolLogo": true,
        "colorTheme": "{theme}",
        "isTransparent": false,
        "displayMode": "adaptive",
        "width": "{width}",
        "height": 60
    }}
    </script>
</div>
<!-- TradingView Ticker Tape Widget END -->
'''

        return {
            "symbols": symbols,
            "html": html_code.strip(),
        }

    def generate_market_overview_widget(
        self,
        screeners: List[str] = None,
        theme: str = "dark",
        height: int = 600
    ) -> Dict:
        """
        Generate TradingView Market Overview Widget.

        Args:
            screeners: List of screeners (default: crypto, forex, indices)
            theme: "light" or "dark"
            height: Widget height

        Returns:
            Dict with HTML embed code
        """
        if screeners is None:
            screeners = ["crypto", "forex", "indices"]

        screener_config = []
        for screener in screeners:
            screener_config.append({
                "screener": screener,
                "columns": ["Name", "Close", "Change", "Change%", "Volume"],
            })

        html_code = f'''
<!-- TradingView Market Overview Widget BEGIN -->
<div class="tradingview-widget-container" style="height:{height}px;width:100%">
    <div class="tradingview-widget-container__widget"></div>
    <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-market-quotes.js" async>
    {{
        "width": "100%",
        "height": "{height}",
        "symbolsGroups": {json.dumps(screener_config)},
        "showSymbolLogo": true,
        "colorTheme": "{theme}",
        "isTransparent": false,
        "locale": "en"
    }}
    </script>
</div>
<!-- TradingView Market Overview Widget END -->
'''

        return {
            "screeners": screeners,
            "html": html_code.strip(),
        }

    def generate_technical_summary_widget(
        self,
        symbol: str,
        exchange: str = "BINANCE",
        theme: str = "dark",
        width: int = 350
    ) -> Dict:
        """
        Generate TradingView Technical Analysis Summary Widget.

        Args:
            symbol: Trading symbol
            exchange: Exchange name
            theme: "light" or "dark"
            width: Widget width

        Returns:
            Dict with HTML embed code
        """
        tv_symbol = f"{exchange}:{symbol}"

        html_code = f'''
<!-- TradingView Technical Analysis Widget BEGIN -->
<div class="tradingview-widget-container">
    <div class="tradingview-widget-container__widget"></div>
    <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-technical-analysis.js" async>
    {{
        "interval": "1m",
        "width": "{width}",
        "isTransparent": false,
        "height": 450,
        "symbol": "{tv_symbol}",
        "showIntervalTabs": true,
        "displayMode": "single",
        "locale": "en",
        "colorTheme": "{theme}"
    }}
    </script>
</div>
<!-- TradingView Technical Analysis Widget END -->
'''

        return {
            "symbol": symbol,
            "tv_symbol": tv_symbol,
            "html": html_code.strip(),
        }

    async def get_technical_rating(
        self,
        symbol: str,
        exchange: str = "BINANCE"
    ) -> Optional[Dict]:
        """
        Fetch technical rating from TradingView Scanner.

        Returns a summary of technical indicators and overall rating.
        """
        try:
            session = await self._get_session()

            # TradingView screener API
            screener = "crypto"
            symbols = f"{exchange.lower()}:{symbol.replace('USDT', 'USDT')}"

            url = f"{self.base_url}/{screener}/scan"
            params = {
                "symbols": f'{{"{screener}":["{symbols}"]}}',
                "columns": "Recommend.All|Recommend.All|MA:MA10|MA:MA20|MA:MA50|MA:MA200|RSI|EMA:EMA10|EMA:EMA20"
            }

            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    if data.get("data"):
                        result = data["data"][0]
                        values = result.get("d", [])

                        return {
                            "symbol": symbol,
                            "overall_recommendation": self._parse_recommendation(values[0] if len(values) > 0 else 0),
                            "buy": values[1] if len(values) > 1 else 0,
                            "sell": values[2] if len(values) > 2 else 0,
                            "ma10": values[3] if len(values) > 3 else None,
                            "ma20": values[4] if len(values) > 4 else None,
                            "ma50": values[5] if len(values) > 5 else None,
                            "ma200": values[6] if len(values) > 6 else None,
                            "rsi": values[7] if len(values) > 7 else None,
                            "ema10": values[8] if len(values) > 8 else None,
                            "ema20": values[9] if len(values) > 9 else None,
                        }

                return None

        except Exception as e:
            print(f"[TradingView] Error fetching technical rating: {e}")
            return None

    def _parse_recommendation(self, value: float) -> str:
        """Parse numeric recommendation to string."""
        if value >= 0.8:
            return "STRONG_BUY"
        elif value >= 0.5:
            return "BUY"
        elif value >= 0.2:
            return "NEUTRAL"
        elif value >= -0.2:
            return "NEUTRAL"
        elif value >= -0.5:
            return "SELL"
        else:
            return "STRONG_SELL"

    async def get_market_movers(
        self,
        category: str = "crypto",
        limit: int = 20
    ) -> Dict[str, List[Dict]]:
        """
        Get top gainers and losers from TradingView Scanner.

        Args:
            category: Market category ("crypto", "forex", "america", etc.)
            limit: Number of results

        Returns:
            Dict with "gainers" and "losers" lists
        """
        try:
            session = await self._get_session()

            url = f"{self.base_url}/{category}/scan"
            params = {
                "filter": json.dumps([
                    {"left": "exchange", "operation": "equal", "right": "BINANCE"},
                    {"left": "name", "operation": "match", "right": "USDT$"}
                ]),
                "options": json.dumps({"lang": "en"}),
                "symbols": json.dumps({}),
                "columns": json.dumps([
                    "name",
                    "close",
                    "change",
                    "change_abs",
                    "Recommend.All",
                    "volume",
                    "market_cap"
                ]),
                "sort": "name",
                "sort_order": "asc",
                "range": [0, limit * 2]
            }

            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    gainers = []
                    losers = []

                    for item in data.get("data", []):
                        symbol = item.get("s", "").replace("BINANCE:", "")
                        values = item.get("d", [])

                        if len(values) >= 3:
                            change_pct = values[2]

                            mover = {
                                "symbol": symbol,
                                "price": values[0] if len(values) > 0 else 0,
                                "change": values[1] if len(values) > 1 else 0,
                                "change_pct": change_pct,
                                "recommendation": self._parse_recommendation(values[3] if len(values) > 3 else 0),
                                "volume": values[4] if len(values) > 4 else 0,
                                "market_cap": values[5] if len(values) > 5 else 0,
                            }

                            if change_pct > 0:
                                gainers.append(mover)
                            else:
                                losers.append(mover)

                    return {
                        "gainers": sorted(gainers, key=lambda x: x["change_pct"], reverse=True)[:limit],
                        "losers": sorted(losers, key=lambda x: x["change_pct"])[:limit],
                    }

                return {"gainers": [], "losers": []}

        except Exception as e:
            print(f"[TradingView] Error fetching market movers: {e}")
            return {"gainers": [], "losers": []}

    def generate_symbol_info(
        self,
        symbol: str,
        exchange: str = "BINANCE"
    ) -> Dict:
        """
        Generate TradingView symbol information for chart widget.

        Returns the proper symbol format for TradingView widgets.
        """
        # Map common exchanges to TradingView format
        exchange_map = {
            "BINANCE": "BINANCE",
            "COINBASE": "COINBASE",
            "KRAKEN": "KRAKEN",
            "BITSTAMP": "BITSTAMP",
            "BITFINEX": "BITFINEX",
            "OKX": "OKX",
            "BYBIT": "BYBIT",
        }

        tv_exchange = exchange_map.get(exchange.upper(), "BINANCE")
        tv_symbol = f"{tv_exchange}:{symbol}"

        # Generate widget URL
        widget_url = f"https://www.tradingview.com/chart/?symbol={tv_symbol}"

        return {
            "original_symbol": symbol,
            "exchange": exchange,
            "tv_exchange": tv_exchange,
            "tv_symbol": tv_symbol,
            "widget_url": widget_url,
        }

    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()


class TechnicalIndicators:
    """
    Calculate technical indicators for price data.
    Used when TradingView data is not available.
    """

    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> float:
        """Calculate Relative Strength Index."""
        if len(prices) < period + 1:
            return 50.0

        deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]

        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    @staticmethod
    def calculate_sma(prices: List[float], period: int) -> Optional[float]:
        """Calculate Simple Moving Average."""
        if len(prices) < period:
            return None
        return sum(prices[-period:]) / period

    @staticmethod
    def calculate_ema(prices: List[float], period: int) -> Optional[float]:
        """Calculate Exponential Moving Average."""
        if len(prices) < period:
            return None

        multiplier = 2 / (period + 1)
        ema = sum(prices[:period]) / period

        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema

        return ema

    @staticmethod
    def calculate_macd(prices: List[float]) -> Dict[str, Optional[float]]:
        """Calculate MACD (Moving Average Convergence Divergence)."""
        ema_12 = TechnicalIndicators.calculate_ema(prices, 12)
        ema_26 = TechnicalIndicators.calculate_ema(prices, 26)

        if ema_12 is None or ema_26 is None:
            return {"macd": None, "signal": None, "histogram": None}

        macd = ema_12 - ema_26

        # For signal line, we'd need a history of MACD values
        # This is simplified
        signal = macd * 0.8  # Approximation
        histogram = macd - signal

        return {
            "macd": macd,
            "signal": signal,
            "histogram": histogram,
        }

    @staticmethod
    def calculate_bollinger_bands(
        prices: List[float],
        period: int = 20,
        std_dev: float = 2
    ) -> Dict[str, Optional[float]]:
        """Calculate Bollinger Bands."""
        if len(prices) < period:
            return {"upper": None, "middle": None, "lower": None}

        middle = sum(prices[-period:]) / period
        variance = sum((p - middle) ** 2 for p in prices[-period:]) / period
        std = variance ** 0.5

        upper = middle + (std_dev * std)
        lower = middle - (std_dev * std)

        return {
            "upper": upper,
            "middle": middle,
            "lower": lower,
        }

    @staticmethod
    def get_support_resistance(prices: List[float]) -> Dict[str, List[float]]:
        """
        Identify support and resistance levels.
        Simplified approach using local minima/maxima.
        """
        if len(prices) < 5:
            return {"support": [], "resistance": []}

        supports = []
        resistances = []

        for i in range(2, len(prices) - 2):
            # Local minimum (support)
            if (prices[i] < prices[i - 1] and
                prices[i] < prices[i - 2] and
                prices[i] < prices[i + 1] and
                prices[i] < prices[i + 2]):
                supports.append(prices[i])

            # Local maximum (resistance)
            if (prices[i] > prices[i - 1] and
                prices[i] > prices[i - 2] and
                prices[i] > prices[i + 1] and
                prices[i] > prices[i + 2]):
                resistances.append(prices[i])

        return {
            "support": sorted(set(supports))[:5],  # Top 5 support levels
            "resistance": sorted(set(resistances), reverse=True)[:5],  # Top 5 resistance levels
        }
