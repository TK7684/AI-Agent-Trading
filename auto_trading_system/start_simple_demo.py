"""
Simplified Automated Trading Demo
Bypasses complex configuration to demonstrate core functionality.
"""

import asyncio
import json
import logging
import os
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List

import aiohttp
import numpy as np

# Load environment variables from .env file
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, use system env vars only

# Configure logging (without emojis for Windows compatibility)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("simple_trading_demo.log")],
)

logger = logging.getLogger(__name__)


@dataclass
class TradingSignal:
    """Simple trading signal data structure"""

    symbol: str
    signal: str  # BUY, SELL, HOLD
    confidence: float
    price: float
    reason: str


@dataclass
class Trade:
    """Simple trade record"""

    id: str
    symbol: str
    side: str
    entry_price: float
    quantity: float
    pnl: float = 0.0
    status: str = "OPEN"
    timestamp: datetime = None


class SimpleLLMClient:
    """Simplified LLM client for OpenAI only"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1"

    async def get_trading_signal(
        self, symbol: str, market_data: Dict[str, Any]
    ) -> TradingSignal:
        """Get trading signal from OpenAI"""

        prompt = f"""
        Analyze the following market data for {symbol} and provide a trading recommendation:

        Current Price: ${market_data.get("price", 0):.2f}
        RSI: {market_data.get("rsi", 50):.1f}
        MACD: {market_data.get("macd", 0):.4f}
        Volume: {market_data.get("volume", 0):,.0f}
        24h Change: {market_data.get("change_24h", 0):.2f}%

        Provide a clear trading decision: BUY, SELL, or HOLD.
        Also provide a confidence score from 0.0 to 1.0.
        Keep your response brief and direct.

        Format your response as:
        SIGNAL: [BUY/SELL/HOLD]
        CONFIDENCE: [0.0-1.0]
        REASON: [brief explanation]
        """

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert cryptocurrency trader providing concise trading signals.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 150,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions", headers=headers, json=payload
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        content = data["choices"][0]["message"]["content"]

                        # Parse response
                        signal = "HOLD"
                        confidence = 0.5
                        reason = "No signal generated"

                        for line in content.split("\n"):
                            if "SIGNAL:" in line:
                                signal = line.split("SIGNAL:")[1].strip()
                            elif "CONFIDENCE:" in line:
                                try:
                                    confidence = float(
                                        line.split("CONFIDENCE:")[1].strip()
                                    )
                                except:
                                    confidence = 0.5
                            elif "REASON:" in line:
                                reason = line.split("REASON:")[1].strip()

                        return TradingSignal(
                            symbol=symbol,
                            signal=signal,
                            confidence=confidence,
                            price=market_data.get("price", 0),
                            reason=reason,
                        )
                    else:
                        logger.error(f"OpenAI API error: {response.status}")
                        return self._fallback_signal(symbol, market_data)
        except Exception as e:
            logger.error(f"Error getting trading signal: {e}")
            return self._fallback_signal(symbol, market_data)

    def _fallback_signal(
        self, symbol: str, market_data: Dict[str, Any]
    ) -> TradingSignal:
        """Generate fallback signal when API fails"""
        rsi = market_data.get("rsi", 50)
        change_24h = market_data.get("change_24h", 0)

        if rsi < 30 and change_24h < -2:
            signal = "BUY"
            confidence = 0.7
            reason = "Oversold conditions"
        elif rsi > 70 and change_24h > 2:
            signal = "SELL"
            confidence = 0.7
            reason = "Overbought conditions"
        else:
            signal = "HOLD"
            confidence = 0.5
            reason = "Neutral conditions"

        return TradingSignal(
            symbol=symbol,
            signal=signal,
            confidence=confidence,
            price=market_data.get("price", 0),
            reason=reason,
        )


class SimpleMarketDataProvider:
    """Simple mock market data provider"""

    def __init__(self):
        self.prices = {"BTCUSDT": 45000.0, "ETHUSDT": 2500.0}
        self.trends = {symbol: 0.0 for symbol in self.prices}

    def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """Generate realistic market data"""
        base_price = self.prices[symbol]
        trend = self.trends[symbol]

        # Simulate price movement
        change = random.gauss(trend * 0.01, 0.02)
        new_price = base_price * (1 + change)
        self.prices[symbol] = new_price

        # Occasionally change trend
        if random.random() < 0.01:
            self.trends[symbol] = random.uniform(-0.5, 0.5)

        # Calculate indicators
        price_change_24h = ((new_price - base_price) / base_price) * 100
        rsi = 50 + random.gauss(0, 20)
        rsi = max(0, min(100, rsi))

        return {
            "symbol": symbol,
            "price": new_price,
            "volume": random.uniform(1000000, 10000000),
            "rsi": rsi,
            "macd": random.gauss(0, 0.01),
            "change_24h": price_change_24h,
            "timestamp": datetime.now(timezone.utc),
        }


class SimpleTradingEngine:
    """Simplified trading engine for demo"""

    def __init__(self):
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.gemini_key = os.getenv("GEMINI_API_KEY")

        if not self.openai_key:
            logger.warning("OpenAI API key not found")
        if not self.gemini_key:
            logger.warning("Gemini API key not found")

        self.llm_client = SimpleLLMClient(self.openai_key) if self.openai_key else None
        self.market_provider = SimpleMarketDataProvider()

        self.trades: List[Trade] = []
        self.positions: Dict[str, Trade] = {}
        self.running = False
        self.trade_count = 0
        self.wins = 0
        self.losses = 0
        self.total_pnl = 0.0

        logger.info("Simple Trading Engine initialized")

    async def start_trading(self, duration_minutes: int = 10):
        """Start trading for specified duration"""
        if not self.llm_client:
            logger.error("No LLM client available - cannot start trading")
            return

        self.running = True
        symbols = ["BTCUSDT", "ETHUSDT"]
        start_time = time.time()

        logger.info(f"[START] Starting {duration_minutes}-minute trading demo")
        logger.info(f"[SYMBOLS] Tracking: {', '.join(symbols)}")
        logger.info("[AI] Using AI for trading decisions")
        logger.info("=" * 80)

        try:
            while self.running and (time.time() - start_time) < duration_minutes * 60:
                # Analyze each symbol
                for symbol in symbols:
                    try:
                        # Get market data
                        market_data = self.market_provider.get_market_data(symbol)

                        # Get AI trading signal
                        signal = await self.llm_client.get_trading_signal(
                            symbol, market_data
                        )

                        logger.info(
                            f"[DATA] {symbol}: ${market_data['price']:.2f} | RSI: {market_data['rsi']:.1f} | AI: {signal.signal} (conf: {signal.confidence:.2f})"
                        )

                        # Execute trade if signal is strong enough
                        if signal.confidence > 0.6 and signal.signal in ["BUY", "SELL"]:
                            await self._execute_trade(
                                symbol, signal, market_data["price"]
                            )

                        # Check existing positions
                        await self._manage_positions(symbol, market_data["price"])

                    except Exception as e:
                        logger.error(f"Error processing {symbol}: {e}")

                # Wait for next cycle
                await asyncio.sleep(5)  # 5-second intervals

        except KeyboardInterrupt:
            logger.info("👋 Trading stopped by user")
        finally:
            self.running = False
            await self._close_all_positions()
            self._print_final_report()

    async def _execute_trade(self, symbol: str, signal: TradingSignal, price: float):
        """Execute a trade based on signal"""
        # Check if we already have a position
        if symbol in self.positions:
            return

        # Calculate position size (simplified)
        quantity = 0.1  # Fixed size for demo

        # Create trade
        trade_id = f"{symbol}_{int(time.time())}"
        trade = Trade(
            id=trade_id,
            symbol=symbol,
            side="LONG" if signal.signal == "BUY" else "SHORT",
            entry_price=price,
            quantity=quantity,
            timestamp=datetime.now(timezone.utc),
        )

        self.trades.append(trade)
        self.positions[symbol] = trade
        self.trade_count += 1

        logger.info(
            f"[TRADE] EXECUTED {signal.signal} {symbol} @ ${price:.2f} | Reason: {signal.reason}"
        )

    async def _manage_positions(self, symbol: str, current_price: float):
        """Manage existing positions"""
        if symbol not in self.positions:
            return

        position = self.positions[symbol]

        # Simple exit logic
        pnl_pct = 0.0
        if position.side == "LONG":
            pnl_pct = (
                (current_price - position.entry_price) / position.entry_price
            ) * 100
        else:
            pnl_pct = (
                (position.entry_price - current_price) / position.entry_price
            ) * 100

        position.pnl = (current_price - position.entry_price) * position.quantity

        # Exit conditions
        should_close = False
        exit_reason = ""

        if pnl_pct > 2.0:  # 2% profit
            should_close = True
            exit_reason = "Take Profit"
        elif pnl_pct < -1.5:  # 1.5% loss
            should_close = True
            exit_reason = "Stop Loss"

        if should_close:
            await self._close_position(symbol, current_price, exit_reason)

    async def _close_position(self, symbol: str, exit_price: float, reason: str):
        """Close a position"""
        if symbol not in self.positions:
            return

        position = self.positions[symbol]
        position.status = "CLOSED"
        position.pnl = (exit_price - position.entry_price) * position.quantity

        # Update statistics
        if position.pnl > 0:
            self.wins += 1
        else:
            self.losses += 1
        self.total_pnl += position.pnl

        # Remove from positions
        del self.positions[symbol]

        logger.info(
            f"[CLOSE] {symbol} @ ${exit_price:.2f} | PnL: ${position.pnl:+.2f} | {reason}"
        )

    async def _close_all_positions(self):
        """Close all open positions"""
        for symbol in list(self.positions.keys()):
            current_price = self.market_provider.get_market_data(symbol)["price"]
            await self._close_position(symbol, current_price, "Session End")

    def _print_final_report(self):
        """Print final trading report"""
        logger.info("\n" + "=" * 80)
        logger.info("[FINAL] TRADING REPORT")
        logger.info("=" * 80)

        win_rate = (self.wins / self.trade_count * 100) if self.trade_count > 0 else 0
        avg_pnl = self.total_pnl / self.trade_count if self.trade_count > 0 else 0

        logger.info(f"[TOTAL] Trades: {self.trade_count}")
        logger.info(f"[WINS] Winning Trades: {self.wins}")
        logger.info(f"[LOSSES] Losing Trades: {self.losses}")
        logger.info(f"[WINRATE] Win Rate: {win_rate:.1f}%")
        logger.info(f"[PNL] Total PnL: ${self.total_pnl:+.2f}")
        logger.info(f"[AVG] Average PnL per Trade: ${avg_pnl:+.2f}")

        # Grade performance
        if win_rate >= 70 and self.total_pnl > 0:
            grade = "A+ - EXCELLENT"
            message = "🏆 Outstanding performance! System is highly profitable."
        elif win_rate >= 60 and self.total_pnl > 0:
            grade = "A - VERY GOOD"
            message = "👍 Strong performance with good profitability."
        elif win_rate >= 50:
            grade = "B+ - GOOD"
            message = "📈 Decent performance with room for improvement."
        else:
            grade = "B - NEEDS IMPROVEMENT"
            message = "⚠️ Performance needs optimization."

        logger.info(f"[GRADE] System Grade: {grade}")
        logger.info(f"   {message}")
        logger.info("=" * 80)


async def main():
    """Main function"""
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║           SIMPLE AI TRADING DEMO v1.0                     ║
    ║                                                          ║
    ║  [AI] AI-Powered Trading Analysis                        ║
    ║  [DATA] Real-time Market Simulation                     ║
    ║  [LLM] OpenAI GPT Integration                            ║
    ║  [TRADE] Automated Trade Execution                         ║
    ║                                                          ║
    ║  Press Ctrl+C to stop                                ║
    ╚══════════════════════════════════════════════════════════╝
    """)

    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("[ERROR] OPENAI_API_KEY not found in environment variables")
        logger.error("Please set your API key in .env file")
        return

    logger.info("[SUCCESS] OpenAI API Key found - Ready to trade!")

    # Start trading engine
    engine = SimpleTradingEngine()

    try:
        await engine.start_trading(duration_minutes=5)  # 5-minute demo
    except KeyboardInterrupt:
        logger.info("[STOPPED] Demo stopped by user")
    except Exception as e:
        logger.error(f"[ERROR] Error in trading engine: {e}")


if __name__ == "__main__":
    asyncio.run(main())
