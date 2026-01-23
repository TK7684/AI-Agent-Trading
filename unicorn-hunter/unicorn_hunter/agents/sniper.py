"""
Sniper Agent - The Technical Executor
Confirms the specific entry signals: Divergence and Wyckoff Spring.
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime

from unicorn_hunter.tools.market_tools import MarketTools


class SniperAgent:
    """Sniper Agent confirms technical entry signals."""

    def __init__(self):
        self.market_tools = MarketTools()

    async def analyze(self, candidate: Dict) -> Dict:
        """
        Analyze a candidate for entry signals.

        Key signals:
        1. RSI Bullish Divergence - Price lower low + RSI higher low
        2. Wyckoff Spring - False breakdown + recovery
        3. Volume confirmation

        Returns:
            Dict with technical analysis and recommendation
        """
        symbol = candidate.get("symbol", "")

        print(f"[Sniper] Analyzing {symbol} for entry signals...")

        result = {
            "rsi": 0,
            "rsi_divergence": 0,
            "wyckoff_spring": 0,
            "volume_confirmation": 0,
            "support_level": 0,
            "resistance_level": 0,
            "entry_price": 0,
            "stop_loss": 0,
            "take_profit": 0,
            "recommendation": "WAIT",
            "technical_score": 0,
            "analysis_notes": [],
        }

        try:
            # Get OHLCV data for technical analysis
            ohlcv = await self.market_tools.get_ohlcv(symbol, timeframe="1d", limit=100)

            if not ohlcv or len(ohlcv) < 50:
                # Use mock analysis for testing when API fails
                if candidate.get("source") == "mock_data":
                    return self._get_mock_analysis(candidate)
                result["analysis_notes"].append("⚠ Insufficient data for technical analysis")
                return result

            # 1. RSI Analysis
            rsi_data = await self._calculate_rsi(ohlcv)
            result["rsi"] = rsi_data["current_rsi"]
            result["rsi_divergence"] = 1 if rsi_data["bullish_divergence"] else 0

            if rsi_data["bullish_divergence"]:
                result["analysis_notes"].append("✓ RSI Bullish Divergence detected")
            elif rsi_data["current_rsi"] < 30:
                result["analysis_notes"].append(f"○ RSI oversold ({rsi_data['current_rsi']:.1f})")
            else:
                result["analysis_notes"].append(f"○ RSI neutral ({rsi_data['current_rsi']:.1f})")

            # 2. Wyckoff Spring Detection
            wyckoff_data = await self._detect_wyckoff_spring(ohlcv)
            result["wyckoff_spring"] = 1 if wyckoff_data["is_spring"] else 0

            if wyckoff_data["is_spring"]:
                result["analysis_notes"].append("✓ Wyckoff Spring pattern detected")
            else:
                result["analysis_notes"].append("○ No Wyckoff Spring detected")

            # 3. Volume Confirmation
            volume_data = await self._check_volume_confirmation(ohlcv)
            result["volume_confirmation"] = 1 if volume_data["confirmed"] else 0

            if volume_data["confirmed"]:
                result["analysis_notes"].append("✓ Volume confirms reversal")

            # 4. Support/Resistance Levels
            levels = await self._calculate_support_resistance(ohlcv)
            result["support_level"] = levels["support"]
            result["resistance_level"] = levels["resistance"]

            # 5. Calculate Entry, Stop Loss, Take Profit
            current_price = ohlcv[-1]["close"]
            result["entry_price"] = current_price * 1.02  # 2% above current for confirmation
            result["stop_loss"] = levels["support"] * 0.95  # 5% below support
            result["take_profit"] = levels["resistance"] * 0.98  # 2% below resistance

            # 6. Calculate Technical Score
            result["technical_score"] = self._calculate_technical_score(result)

            # 7. Generate Recommendation
            result["recommendation"] = self._generate_recommendation(result)

            result["analysis_notes"].append(
                f"Entry: ${result['entry_price']:.4f} | "
                f"Stop: ${result['stop_loss']:.4f} | "
                f"TP: ${result['take_profit']:.4f}"
            )

        except Exception as e:
            print(f"[Sniper] Analysis failed: {e}")
            result["analysis_notes"].append(f"✗ Analysis error: {str(e)}")

        return result

    async def _calculate_rsi(self, ohlcv: List[Dict]) -> Dict:
        """Calculate RSI and detect bullish divergence."""
        closes = [c["close"] for c in ohlcv]

        # Calculate RSI using wilder's smoothing
        period = 14
        deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]

        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]

        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        rs = avg_gain / avg_loss if avg_loss != 0 else 0
        current_rsi = 100 - (100 / (1 + rs))

        # Detect bullish divergence
        # Price makes lower low but RSI makes higher low
        recent_lows = [min(closes[i:i + 5]) for i in range(len(closes) - 20, len(closes) - 5)]
        if len(recent_lows) >= 2:
            price_lower_low = recent_lows[-1] < recent_lows[-2]

            # Simplified RSI lows check
            rsi_values = [self._calculate_rsi_at_point(closes, i) for i in range(len(closes) - 20, len(closes))]
            rsi_higher_low = rsi_values[-1] > min(rsi_values[-5:-1]) if len(rsi_values) > 5 else False

            bullish_divergence = price_lower_low and rsi_higher_low
        else:
            bullish_divergence = False

        return {
            "current_rsi": current_rsi,
            "bullish_divergence": bullish_divergence,
        }

    def _calculate_rsi_at_point(self, closes: List[float], end_idx: int) -> float:
        """Calculate RSI at a specific point."""
        if end_idx < 14:
            return 50

        period = 14
        sub_closes = closes[:end_idx + 1]
        deltas = [sub_closes[i] - sub_closes[i - 1] for i in range(1, len(sub_closes))]

        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]

        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period

        rs = avg_gain / avg_loss if avg_loss != 0 else 0
        return 100 - (100 / (1 + rs))

    async def _detect_wyckoff_spring(self, ohlcv: List[Dict]) -> Dict:
        """
        Detect Wyckoff Spring pattern.

        Spring characteristics:
        1. Price breaks below support (trapping sellers)
        2. Quickly recovers back above support
        3. High volume on the breakdown
        4. Follow-through buying pressure
        """
        recent = ohlcv[-20:]  # Last 20 days

        # Find support level (recent low)
        lows = [c["low"] for c in recent]
        support = min(lows[:-5])  # Support from 5+ days ago

        # Check for recent break below support
        recent_lows = lows[-5:]
        broke_support = any(low < support * 0.98 for low in recent_lows)

        # Check for recovery
        if broke_support:
            current_price = ohlcv[-1]["close"]
            recovered = current_price > support * 0.99
            volume_spike = recent[-1]["volume"] > sum(c["volume"] for c in recent[-10:-1]) / 7

            is_spring = recovered and volume_spike
        else:
            is_spring = False

        return {
            "is_spring": is_spring,
            "support_level": support,
        }

    async def _check_volume_confirmation(self, ohlcv: List[Dict]) -> Dict:
        """Check if volume confirms the reversal."""
        recent = ohlcv[-10:]
        older = ohlcv[-30:-10]

        recent_avg_vol = sum(c["volume"] for c in recent) / len(recent)
        older_avg_vol = sum(c["volume"] for c in older) / len(older)

        # Volume should be significantly higher
        confirmed = recent_avg_vol > older_avg_vol * 1.5

        return {
            "confirmed": confirmed,
            "recent_avg": recent_avg_vol,
            "older_avg": older_avg_vol,
        }

    async def _calculate_support_resistance(self, ohlcv: List[Dict]) -> Dict:
        """Calculate support and resistance levels."""
        recent = ohlcv[-50:]  # Last 50 periods

        highs = [c["high"] for c in recent]
        lows = [c["low"] for c in recent]

        # Simple pivot-based levels
        resistance = max(highs[-20:])
        support = min(lows[-20:])

        return {
            "support": support,
            "resistance": resistance,
        }

    def _calculate_technical_score(self, result: Dict) -> int:
        """Calculate technical score (0-100)."""
        score = 0

        # RSI Divergence (40 points)
        if result["rsi_divergence"]:
            score += 40
        elif result["rsi"] < 35:
            score += 20

        # Wyckoff Spring (35 points)
        if result["wyckoff_spring"]:
            score += 35

        # Volume Confirmation (25 points)
        if result["volume_confirmation"]:
            score += 25

        return score

    def _generate_recommendation(self, result: Dict) -> str:
        """Generate trading recommendation."""
        score = result["technical_score"]

        # Also consider fundamental score if available
        fundamental = result.get("fundamental_score", 50)

        combined_score = (score * 0.6) + (fundamental * 0.4)

        if combined_score >= 70 and result["rsi_divergence"]:
            return "STRONG_BUY"
        elif combined_score >= 50:
            return "BUY"
        elif combined_score >= 30:
            return "HOLD"
        else:
            return "WAIT"

    def _get_mock_analysis(self, candidate: Dict) -> Dict:
        """Generate mock technical analysis for testing when APIs fail."""
        symbol = candidate.get("symbol", "")
        price = candidate.get("current_price", 0)
        score = candidate.get("scanner_score", 75)

        # Generate realistic-looking mock data
        entry_price = price * 1.02
        stop_loss = price * 0.92
        take_profit = price * 1.20

        return {
            "rsi": 32 + (score % 20),  # RSI 32-52 (oversold to neutral)
            "rsi_divergence": 1 if score > 80 else 0,
            "wyckoff_spring": 1 if score > 75 else 0,
            "volume_confirmation": 1,
            "support_level": price * 0.92,
            "resistance_level": price * 1.25,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "recommendation": "STRONG_BUY" if score >= 85 else "BUY",
            "technical_score": score,
            "analysis_notes": [
                "✓ RSI Bullish Divergence detected (mock data)",
                "✓ Wyckoff Spring pattern detected (mock data)",
                "✓ Volume confirms reversal (mock data)",
                f"Entry: ${entry_price:.4f} | Stop: ${stop_loss:.4f} | TP: ${take_profit:.4f}",
            ],
        }
