"""
Core Live Trading Engine
Automates real trading execution with risk management, database integration, and adaptive learning.
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

import numpy as np

from libs.trading_models.config_manager import get_config_manager
from libs.trading_models.memory_learning import MemoryLearningSystem, TradeOutcome
from libs.trading_models.orchestrator import TradingOrchestrator

from ..api.llm_client import LLMProvider, TradingAnalyzer
from ..database.performance_repository import PerformanceRepository
from ..database.trade_repository import TradeRepository
from ..learning.adaptive_strategy import AdaptiveStrategyManager
from ..market_data.mock_provider import MockMarketDataProvider
from ..monitoring.performance_monitor import PerformanceMonitor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TradeSignal:
    """Represents a trading signal with all necessary parameters"""

    symbol: str
    side: str  # 'LONG' or 'SHORT'
    entry_price: float
    quantity: float
    stop_loss: float
    take_profit: float
    confidence: float
    pattern: str
    strategy: str
    timeframe: str
    entry_reason: str
    risk_reward_ratio: float


@dataclass
class Position:
    """Represents an active trading position"""

    id: str
    symbol: str
    side: str
    entry_price: float
    quantity: float
    stop_loss: float
    take_profit: float
    entry_time: datetime
    current_pnl: float = 0.0


class LiveTradingEngine:
    """
    Core live trading engine that handles automated trading execution,
    database integration, and adaptive learning.
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config_manager = get_config_manager()
        self.config = self.config_manager.get_config()

        # Initialize components
        self.memory_learning = MemoryLearningSystem()
        self.trade_repository = TradeRepository()
        self.performance_repository = PerformanceRepository()
        self.performance_monitor = PerformanceMonitor()
        self.adaptive_strategy = AdaptiveStrategyManager()

        # Initialize LLM providers
        self.llm_provider = LLMProvider(
            openai_api_key=self.config.get("llm", {}).get("openai_api_key", ""),
            gemini_api_key=self.config.get("llm", {}).get("gemini_api_key", ""),
        )
        self.trading_analyzer = TradingAnalyzer(self.llm_provider)

        # Initialize market data provider
        self.market_data_provider = MockMarketDataProvider()

        # Trading state
        self.is_running = False
        self.active_positions: Dict[str, Position] = {}
        self.trade_count = 0
        self.last_learning_cycle = datetime.now(timezone.utc)
        self.last_performance_update = datetime.now(timezone.utc)

        # Performance metrics
        self.daily_pnl = 0.0
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0

        logger.info("Live Trading Engine initialized")

    async def start_trading(self) -> None:
        """Start the main trading loop"""
        if self.is_running:
            logger.warning("Trading is already running")
            return

        logger.info("Starting live trading engine")
        self.is_running = True

        try:
            await self._trading_loop()
        except Exception as e:
            logger.error(f"Trading loop error: {e}")
            raise
        finally:
            await self.stop_trading()

    async def stop_trading(self) -> None:
        """Stop the trading engine and clean up"""
        logger.info("Stopping live trading engine")
        self.is_running = False

        # Close all positions before stopping
        await self.close_all_positions()

        # Save learning state
        await self.memory_learning.save_state()

        logger.info("Live trading engine stopped")

    async def _trading_loop(self) -> None:
        """Main trading loop that runs continuously"""
        trading_interval = self.config.get("trading", {}).get("interval_seconds", 60)
        learning_interval = self.config.get("learning", {}).get(
            "cycle_interval_trades", 50
        )

        while self.is_running:
            try:
                # Get current market data
                market_data = await self._get_market_data()

                # Generate trading signals
                signals = await self._generate_trading_signals(market_data)

                # Apply adaptive learning adjustments
                adjusted_signals = await self._apply_learning_adjustments(signals)

                # Execute trades based on adjusted signals
                await self._execute_trades(adjusted_signals)

                # Monitor and manage existing positions
                await self._manage_positions()

                # Update performance metrics
                await self._update_performance_metrics()

                # Perform learning cycle periodically
                if self.trade_count % learning_interval == 0:
                    await self._perform_learning_cycle()

                # Adaptive strategy optimization
                if (
                    datetime.now(timezone.utc) - self.last_learning_cycle
                ).seconds > 3600:  # Every hour
                    await self._optimize_strategies()
                    self.last_learning_cycle = datetime.now(timezone.utc)

                await asyncio.sleep(trading_interval)

            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                await asyncio.sleep(5)  # Brief pause on error

    async def _get_market_data(self) -> Dict[str, Any]:
        """Fetch current market data for all configured symbols"""
        symbols = self.config.get("trading", {}).get("symbols", ["BTCUSDT"])

        try:
            # Use mock market data provider for realistic data
            market_data = await self.market_data_provider.get_market_data(symbols)
            return market_data
        except Exception as e:
            logger.error(f"Error fetching market data: {e}")
            # Fallback to basic simulated data
            market_data = {}
            for symbol in symbols:
                market_data[symbol] = {
                    "symbol": symbol,
                    "price": np.random.uniform(40000, 50000),  # Simulated price
                    "volume": np.random.uniform(1000, 10000),
                    "timestamp": datetime.now(timezone.utc),
                    "indicators": self._calculate_technical_indicators(symbol),
                }
            return market_data

    async def _generate_trading_signals(
        self, market_data: Dict[str, Any]
    ) -> List[TradeSignal]:
        """Generate trading signals using LLM providers"""
        signals = []

        for symbol, data in market_data.items():
            try:
                # Get trading signal from LLM provider
                result = await self.llm_provider.get_trading_signal(
                    symbol=symbol,
                    market_data=data,
                    provider="openai",  # Use OpenAI as primary
                )

                if result["success"] and result["content"]:
                    signal_data = result["content"]

                    if signal_data.get("signal") in ["BUY", "SELL"]:
                        signal = TradeSignal(
                            symbol=symbol,
                            side="LONG" if signal_data["signal"] == "BUY" else "SHORT",
                            entry_price=data["price"],
                            quantity=self._calculate_position_size(
                                symbol, data["price"]
                            ),
                            stop_loss=signal_data.get(
                                "stop_loss", data["price"] * 0.98
                            ),
                            take_profit=signal_data.get(
                                "take_profit", data["price"] * 1.02
                            ),
                            confidence=signal_data.get("confidence", 0.5),
                            pattern=signal_data.get("pattern", "UNKNOWN"),
                            strategy=signal_data.get("strategy", "OPENAI_ANALYSIS"),
                            timeframe=signal_data.get("timeframe", "1h"),
                            entry_reason=signal_data.get("reason", "AI_SIGNAL"),
                            risk_reward_ratio=self._calculate_risk_reward_ratio(
                                signal_data.get("stop_loss", data["price"] * 0.98),
                                data["price"],
                                signal_data.get("take_profit", data["price"] * 1.02),
                            ),
                        )
                        signals.append(signal)
                else:
                    # Fallback to orchestrator if LLM fails
                    logger.warning(
                        f"LLM failed for {symbol}, using orchestrator fallback"
                    )
                    signal_data = await self.orchestrator.analyze_symbol(data)

                    if signal_data.get("signal") in ["BUY", "SELL"]:
                        signal = TradeSignal(
                            symbol=symbol,
                            side="LONG" if signal_data["signal"] == "BUY" else "SHORT",
                            entry_price=data["price"],
                            quantity=self._calculate_position_size(
                                symbol, data["price"]
                            ),
                            stop_loss=signal_data.get(
                                "stop_loss", data["price"] * 0.98
                            ),
                            take_profit=signal_data.get(
                                "take_profit", data["price"] * 1.02
                            ),
                            confidence=signal_data.get("confidence", 0.5),
                            pattern=signal_data.get("pattern", "UNKNOWN"),
                            strategy=signal_data.get(
                                "strategy", "FALLBACK_ORCHESTRATOR"
                            ),
                            timeframe=signal_data.get("timeframe", "1h"),
                            entry_reason=signal_data.get("reason", "FALLBACK_SIGNAL"),
                            risk_reward_ratio=self._calculate_risk_reward_ratio(
                                signal_data.get("stop_loss", data["price"] * 0.98),
                                data["price"],
                                signal_data.get("take_profit", data["price"] * 1.02),
                            ),
                        )
                        signals.append(signal)

            except Exception as e:
                logger.error(f"Error generating signal for {symbol}: {e}")
                continue

        return signals

    async def _apply_learning_adjustments(
        self, signals: List[TradeSignal]
    ) -> List[TradeSignal]:
        """Apply machine learning adjustments to trading signals"""
        adjusted_signals = []

        for signal in signals:
            try:
                # Get pattern performance from memory learning
                pattern_weights = self.memory_learning.get_pattern_weights()
                position_multiplier = (
                    self.memory_learning.get_adaptive_position_size_multiplier(
                        signal.pattern, signal.strategy
                    )
                )

                # Adjust signal based on historical performance
                pattern_weight = pattern_weights.get(signal.pattern, 1.0)
                adjusted_confidence = signal.confidence * pattern_weight
                adjusted_quantity = signal.quantity * position_multiplier

                # Apply adaptive strategy adjustments
                strategy_adjustments = await self.adaptive_strategy.get_adjustments(
                    signal
                )

                if adjusted_confidence > self.config.get("trading", {}).get(
                    "min_confidence", 0.6
                ):
                    adjusted_signal = TradeSignal(
                        symbol=signal.symbol,
                        side=signal.side,
                        entry_price=signal.entry_price,
                        quantity=min(
                            adjusted_quantity,
                            self._get_max_position_size(signal.symbol),
                        ),
                        stop_loss=signal.stop_loss,
                        take_profit=signal.take_profit,
                        confidence=adjusted_confidence,
                        pattern=signal.pattern,
                        strategy=signal.strategy,
                        timeframe=signal.timeframe,
                        entry_reason=f"{signal.entry_reason} (ADJUSTED)",
                        risk_reward_ratio=signal.risk_reward_ratio
                        * strategy_adjustments.get("risk_adjustment", 1.0),
                    )
                    adjusted_signals.append(adjusted_signal)

            except Exception as e:
                logger.error(f"Error applying learning adjustments: {e}")
                continue

        return adjusted_signals

    async def _execute_trades(self, signals: List[TradeSignal]) -> None:
        """Execute trades based on processed signals"""
        for signal in signals:
            try:
                # Risk management check
                if not await self._risk_management_check(signal):
                    logger.warning(
                        f"Trade rejected by risk management: {signal.symbol}"
                    )
                    continue

                # Execute the trade (this would integrate with your broker API)
                position_id = await self._place_order(signal)

                if position_id:
                    # Create position object
                    position = Position(
                        id=position_id,
                        symbol=signal.symbol,
                        side=signal.side,
                        entry_price=signal.entry_price,
                        quantity=signal.quantity,
                        stop_loss=signal.stop_loss,
                        take_profit=signal.take_profit,
                        entry_time=datetime.now(timezone.utc),
                    )

                    self.active_positions[position_id] = position

                    # Record trade in database
                    await self.trade_repository.create_trade(
                        position_id=position_id,
                        symbol=signal.symbol,
                        side=signal.side,
                        entry_price=signal.entry_price,
                        quantity=signal.quantity,
                        stop_loss=signal.stop_loss,
                        take_profit=signal.take_profit,
                        confidence=signal.confidence,
                        pattern=signal.pattern,
                        strategy=signal.strategy,
                        timeframe=signal.timeframe,
                        entry_reason=signal.entry_reason,
                        risk_reward_ratio=signal.risk_reward_ratio,
                    )

                    self.trade_count += 1
                    logger.info(
                        f"Trade executed: {signal.symbol} {signal.side} @ {signal.entry_price}"
                    )

            except Exception as e:
                logger.error(f"Error executing trade for {signal.symbol}: {e}")
                continue

    async def _manage_positions(self) -> None:
        """Monitor and manage active positions"""
        positions_to_close = []

        for position_id, position in self.active_positions.items():
            try:
                # Get current market price
                current_price = await self._get_current_price(position.symbol)
                if current_price is None:
                    continue

                # Calculate current PnL
                if position.side == "LONG":
                    position.current_pnl = (
                        current_price - position.entry_price
                    ) * position.quantity
                else:
                    position.current_pnl = (
                        position.entry_price - current_price
                    ) * position.quantity

                # Check exit conditions
                should_close = False
                exit_reason = ""

                if position.side == "LONG":
                    if current_price <= position.stop_loss:
                        should_close = True
                        exit_reason = "STOP_LOSS"
                    elif current_price >= position.take_profit:
                        should_close = True
                        exit_reason = "TAKE_PROFIT"
                else:  # SHORT
                    if current_price >= position.stop_loss:
                        should_close = True
                        exit_reason = "STOP_LOSS"
                    elif current_price <= position.take_profit:
                        should_close = True
                        exit_reason = "TAKE_PROFIT"

                # Apply adaptive exit adjustments
                if not should_close:
                    exit_signal = await self.adaptive_strategy.should_exit_position(
                        position, current_price
                    )
                    if exit_signal["should_exit"]:
                        should_close = True
                        exit_reason = exit_signal["reason"]

                if should_close:
                    positions_to_close.append((position_id, current_price, exit_reason))

            except Exception as e:
                logger.error(f"Error managing position {position_id}: {e}")
                continue

        # Close positions that need to be closed
        for position_id, exit_price, exit_reason in positions_to_close:
            await self._close_position(position_id, exit_price, exit_reason)

    async def _close_position(
        self, position_id: str, exit_price: float, exit_reason: str
    ) -> None:
        """Close a position and record the outcome"""
        try:
            position = self.active_positions[position_id]

            # Calculate final PnL
            if position.side == "LONG":
                final_pnl = (exit_price - position.entry_price) * position.quantity
            else:
                final_pnl = (position.entry_price - exit_price) * position.quantity

            # Record trade outcome in database
            await self.trade_repository.close_trade(
                position_id=position_id,
                exit_price=exit_price,
                final_pnl=final_pnl,
                exit_reason=exit_reason,
                duration=int(
                    (datetime.now(timezone.utc) - position.entry_time).total_seconds()
                ),
            )

            # Record outcome for learning
            outcome = TradeOutcome(
                pattern=position.strategy,
                strategy=position.strategy,
                timeframe=position.timeframe,
                symbol=position.symbol,
                side=position.side,
                entry_price=position.entry_price,
                exit_price=exit_price,
                quantity=position.quantity,
                pnl=final_pnl,
                duration=int(
                    (datetime.now(timezone.utc) - position.entry_time).total_seconds()
                ),
                confidence=0.8,  # Would be stored with the position
                risk_reward_ratio=position.take_profit
                / abs(position.stop_loss - position.entry_price),
                market_volatility=0.2,  # Would be calculated
                success=final_pnl > 0,
            )

            self.memory_learning.record_trade_outcome(outcome)

            # Update daily PnL
            self.daily_pnl += final_pnl
            self.total_trades += 1
            if final_pnl > 0:
                self.winning_trades += 1
            else:
                self.losing_trades += 1

            # Remove from active positions
            del self.active_positions[position_id]

            logger.info(
                f"Position closed: {position.symbol} PnL: {final_pnl:.2f} Reason: {exit_reason}"
            )

        except Exception as e:
            logger.error(f"Error closing position {position_id}: {e}")

    async def _perform_learning_cycle(self) -> None:
        """Perform a learning cycle to update trading logic"""
        logger.info("Starting learning cycle")

        try:
            # Calibrate the memory learning system
            calibration_results = self.memory_learning.calibrate_system()

            # Update adaptive strategies based on performance
            await self.adaptive_strategy.update_strategies(calibration_results)

            # Get performance report
            performance_report = self.memory_learning.get_performance_report()

            # Store learning results in database
            await self.performance_repository.save_learning_results(
                calibration_results=calibration_results,
                performance_report=performance_report,
                timestamp=datetime.now(timezone.utc),
            )

            logger.info("Learning cycle completed successfully")

        except Exception as e:
            logger.error(f"Error in learning cycle: {e}")

    async def _optimize_strategies(self) -> None:
        """Perform strategy optimization based on recent performance"""
        try:
            # Get recent performance data
            recent_performance = await self.trade_repository.get_recent_performance(
                days=7
            )

            # Generate optimization recommendations
            optimization_results = await self.adaptive_strategy.optimize_strategies(
                recent_performance
            )

            # Apply optimizations
            await self.adaptive_strategy.apply_optimizations(optimization_results)

            logger.info(f"Strategy optimization completed: {optimization_results}")

        except Exception as e:
            logger.error(f"Error in strategy optimization: {e}")

    # Helper methods
    async def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current market price for a symbol"""
        # This would integrate with your real market data feed
        return np.random.uniform(40000, 50000)  # Simulated

    async def _place_order(self, signal: TradeSignal) -> Optional[str]:
        """Place an order and return position ID"""
        # This would integrate with your broker API
        # For now, return a simulated position ID
        return f"pos_{datetime.now(timezone.utc).timestamp()}"

    def _calculate_position_size(self, symbol: str, price: float) -> float:
        """Calculate position size based on risk management rules"""
        account_balance = self.config.get("trading", {}).get("account_balance", 10000)
        max_risk_per_trade = self.config.get("trading", {}).get(
            "max_risk_per_trade", 0.02
        )
        risk_amount = account_balance * max_risk_per_trade

        # Simple position sizing based on fixed risk amount
        position_size = risk_amount / (price * 0.02)  # Assuming 2% stop loss
        return min(position_size, self._get_max_position_size(symbol))

    def _get_max_position_size(self, symbol: str) -> float:
        """Get maximum position size for a symbol"""
        return self.config.get("trading", {}).get("max_position_size", 1.0)

    async def _risk_management_check(self, signal: TradeSignal) -> bool:
        """Perform risk management checks before executing trade"""
        # Check if we already have too many positions
        max_positions = self.config.get("trading", {}).get(
            "max_concurrent_positions", 10
        )
        if len(self.active_positions) >= max_positions:
            return False

        # Check correlation with existing positions
        correlation_risk = await self._check_correlation_risk(signal)
        if correlation_risk > 0.8:
            return False

        # Check account risk
        current_risk = sum(pos.current_pnl for pos in self.active_positions.values())
        max_drawdown = self.config.get("trading", {}).get("max_drawdown", 0.1)
        if (
            current_risk
            < -self.config.get("trading", {}).get("account_balance", 10000)
            * max_drawdown
        ):
            return False

        return True

    async def _check_correlation_risk(self, signal: TradeSignal) -> float:
        """Check correlation risk with existing positions"""
        # Simple correlation check (would be more sophisticated in practice)
        similar_positions = [
            pos for pos in self.active_positions.values() if pos.symbol == signal.symbol
        ]
        return len(similar_positions) / max(len(self.active_positions), 1)

    def _calculate_technical_indicators(self, symbol: str) -> Dict[str, float]:
        """Calculate technical indicators for a symbol"""
        # This would use real market data
        return {
            "rsi": np.random.uniform(30, 70),
            "macd": np.random.uniform(-0.5, 0.5),
            "bb_upper": np.random.uniform(45000, 50000),
            "bb_lower": np.random.uniform(40000, 45000),
            "volume_ma": np.random.uniform(5000, 8000),
        }

    def _calculate_risk_reward_ratio(
        self, stop_loss: float, entry_price: float, take_profit: float
    ) -> float:
        """Calculate risk/reward ratio"""
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)
        return reward / risk if risk > 0 else 0

    async def close_all_positions(self) -> None:
        """Close all active positions"""
        logger.info(f"Closing all {len(self.active_positions)} positions")

        for position_id in list(self.active_positions.keys()):
            current_price = await self._get_current_price(
                self.active_positions[position_id].symbol
            )
            if current_price:
                await self._close_position(
                    position_id, current_price, "SYSTEM_SHUTDOWN"
                )

    async def _update_performance_metrics(self) -> None:
        """Update performance metrics"""
        now = datetime.now(timezone.utc)
        if (now - self.last_performance_update).seconds >= 300:  # Every 5 minutes
            try:
                performance_metrics = {
                    "daily_pnl": self.daily_pnl,
                    "total_trades": self.total_trades,
                    "winning_trades": self.winning_trades,
                    "losing_trades": self.losing_trades,
                    "win_rate": self.winning_trades / max(self.total_trades, 1),
                    "active_positions": len(self.active_positions),
                    "timestamp": now,
                }

                await self.performance_repository.save_performance_metrics(
                    performance_metrics
                )
                self.last_performance_update = now

            except Exception as e:
                logger.error(f"Error updating performance metrics: {e}")
