"""
Paper Trading Mode Implementation

This module provides simulated trading functionality that executes all trading logic
without placing real orders. It tracks simulated positions, P&L, and performance
metrics to validate the system before live trading.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Optional

from .live_trading_config import (
    PerformanceMetrics,
    PerformanceThresholds,
    ValidationIssue,
    ValidationResult,
)

logger = logging.getLogger(__name__)


@dataclass
class SimulatedOrder:
    """Represents a simulated order in paper trading."""
    id: str
    symbol: str
    side: str  # "BUY" or "SELL"
    order_type: str  # "MARKET", "LIMIT"
    quantity: float
    price: Optional[float]
    status: str  # "NEW", "FILLED", "CANCELLED"
    created_at: datetime
    filled_at: Optional[datetime] = None
    filled_price: Optional[float] = None
    filled_quantity: float = 0.0
    commission: float = 0.0

    def __post_init__(self):
        if self.quantity <= 0:
            raise ValueError("Order quantity must be positive")
        if self.price is not None and self.price <= 0:
            raise ValueError("Order price must be positive")


@dataclass
class SimulatedPosition:
    """Represents a simulated position in paper trading."""
    symbol: str
    side: str  # "LONG" or "SHORT"
    size: float
    entry_price: float
    current_price: float
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    entry_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

    def update_price(self, new_price: float) -> None:
        """Update current price and calculate unrealized P&L."""
        self.current_price = new_price

        if self.side == "LONG":
            self.unrealized_pnl = (new_price - self.entry_price) * self.size
        else:  # SHORT
            self.unrealized_pnl = (self.entry_price - new_price) * self.size

    def get_total_pnl(self) -> float:
        """Get total P&L (realized + unrealized)."""
        return self.realized_pnl + self.unrealized_pnl

    def should_trigger_stop_loss(self) -> bool:
        """Check if stop loss should be triggered."""
        if self.stop_loss is None:
            return False

        if self.side == "LONG":
            return self.current_price <= self.stop_loss
        else:  # SHORT
            return self.current_price >= self.stop_loss

    def should_trigger_take_profit(self) -> bool:
        """Check if take profit should be triggered."""
        if self.take_profit is None:
            return False

        if self.side == "LONG":
            return self.current_price >= self.take_profit
        else:  # SHORT
            return self.current_price <= self.take_profit


@dataclass
class SimulatedTrade:
    """Represents a completed simulated trade."""
    id: str
    symbol: str
    side: str
    entry_price: float
    exit_price: float
    quantity: float
    entry_time: datetime
    exit_time: datetime
    pnl: float
    commission: float
    duration: timedelta
    exit_reason: str  # "STOP_LOSS", "TAKE_PROFIT", "MANUAL", "TIMEOUT"

    def get_return_multiple(self) -> float:
        """Calculate return multiple (R-multiple)."""
        if self.pnl == 0:
            return 0.0

        # Calculate risk (distance from entry to stop loss)
        # For simplicity, assume 2% risk per trade
        risk_amount = abs(self.entry_price * self.quantity * 0.02)

        if risk_amount == 0:
            return 0.0

        return self.pnl / risk_amount


@dataclass
class SimulatedPortfolio:
    """Represents the simulated portfolio state."""
    initial_balance: float
    current_balance: float
    available_balance: float
    positions: dict[str, SimulatedPosition] = field(default_factory=dict)
    orders: dict[str, SimulatedOrder] = field(default_factory=dict)
    completed_trades: list[SimulatedTrade] = field(default_factory=list)
    daily_pnl: float = 0.0
    total_pnl: float = 0.0
    max_drawdown: float = 0.0
    peak_balance: float = 0.0

    def __post_init__(self):
        self.peak_balance = self.initial_balance

    def get_total_exposure(self) -> float:
        """Calculate total portfolio exposure."""
        total_exposure = 0.0
        for position in self.positions.values():
            exposure = abs(position.size * position.current_price)
            total_exposure += exposure
        return total_exposure / self.current_balance if self.current_balance > 0 else 0.0

    def get_unrealized_pnl(self) -> float:
        """Calculate total unrealized P&L."""
        return sum(pos.unrealized_pnl for pos in self.positions.values())

    def update_balance(self) -> None:
        """Update current balance and drawdown metrics."""
        unrealized_pnl = self.get_unrealized_pnl()
        self.current_balance = self.initial_balance + self.total_pnl + unrealized_pnl

        # Update peak and drawdown
        if self.current_balance > self.peak_balance:
            self.peak_balance = self.current_balance

        current_drawdown = (self.peak_balance - self.current_balance) / self.peak_balance
        if current_drawdown > self.max_drawdown:
            self.max_drawdown = current_drawdown


class PaperTradingMode:
    """
    Paper trading implementation that simulates all trading operations
    without executing real orders.
    """

    def __init__(self, initial_balance: float = 10000.0, commission_rate: float = 0.001):
        """
        Initialize paper trading mode.

        Args:
            initial_balance: Starting balance for simulation
            commission_rate: Commission rate (0.001 = 0.1%)
        """
        self.portfolio = SimulatedPortfolio(
            initial_balance=initial_balance,
            current_balance=initial_balance,
            available_balance=initial_balance
        )
        self.commission_rate = commission_rate
        self.market_prices: dict[str, float] = {}
        self.start_time = datetime.now(UTC)
        self.is_active = True

        logger.info("Paper trading mode initialized successfully")

    def start_paper_trading(self) -> None:
        """Start paper trading mode."""
        self.is_active = True
        logger.info("Paper trading mode started")

    async def update_market_price(self, symbol: str, price: float) -> None:
        """Update market price for a symbol."""
        self.market_prices[symbol] = price

        # Update position prices
        if symbol in self.portfolio.positions:
            self.portfolio.positions[symbol].update_price(price)

        # Check for stop loss/take profit triggers
        await self._check_position_triggers(symbol)

        # Update portfolio balance
        self.portfolio.update_balance()

    async def execute_simulated_trade(self, signal: dict[str, Any]) -> SimulatedOrder:
        """
        Execute a simulated trade based on a trading signal.

        Args:
            signal: Trading signal with symbol, side, quantity, etc.

        Returns:
            SimulatedOrder representing the executed trade
        """
        if not self.is_active:
            raise RuntimeError("Paper trading is not active")

        symbol = signal["symbol"]
        side = signal["side"]  # "BUY" or "SELL"
        quantity = signal["quantity"]
        order_type = signal.get("order_type", "MARKET")
        price = signal.get("price")

        # Get current market price
        if symbol not in self.market_prices:
            raise ValueError(f"No market price available for {symbol}")

        market_price = self.market_prices[symbol]

        # Create simulated order
        order = SimulatedOrder(
            id=str(uuid.uuid4()),
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            status="NEW",
            created_at=datetime.now(UTC)
        )

        # Execute order immediately (simulate market execution)
        if order_type == "MARKET" or (order_type == "LIMIT" and self._should_fill_limit_order(order, market_price)):
            await self._fill_order(order, market_price)

        self.portfolio.orders[order.id] = order

        logger.info(f"Simulated {side} order: {quantity} {symbol} at ${market_price:.2f}")

        return order

    def _should_fill_limit_order(self, order: SimulatedOrder, market_price: float) -> bool:
        """Check if a limit order should be filled at current market price."""
        if order.price is None:
            return False

        if order.side == "BUY":
            return market_price <= order.price
        else:  # SELL
            return market_price >= order.price

    async def _fill_order(self, order: SimulatedOrder, fill_price: float) -> None:
        """Fill a simulated order."""
        order.status = "FILLED"
        order.filled_at = datetime.now(UTC)
        order.filled_price = fill_price
        order.filled_quantity = order.quantity
        order.commission = order.quantity * fill_price * self.commission_rate

        # Update portfolio
        await self._update_portfolio_for_fill(order)

    async def _update_portfolio_for_fill(self, order: SimulatedOrder) -> None:
        """Update portfolio state after order fill."""
        symbol = order.symbol

        # Calculate position side
        position_side = "LONG" if order.side == "BUY" else "SHORT"

        if symbol in self.portfolio.positions:
            # Modify existing position
            position = self.portfolio.positions[symbol]

            if position.side == position_side:
                # Add to position
                total_value = (position.size * position.entry_price) + (order.filled_quantity * order.filled_price)
                total_size = position.size + order.filled_quantity
                position.entry_price = total_value / total_size
                position.size = total_size
            else:
                # Close or reverse position
                if order.filled_quantity >= position.size:
                    # Close and potentially reverse
                    await self._close_position(symbol, position.size, order.filled_price, "MANUAL")

                    remaining_quantity = order.filled_quantity - position.size
                    if remaining_quantity > 0:
                        # Create new position in opposite direction
                        new_position = SimulatedPosition(
                            symbol=symbol,
                            side=position_side,
                            size=remaining_quantity,
                            entry_price=order.filled_price,
                            current_price=order.filled_price
                        )
                        self.portfolio.positions[symbol] = new_position
                else:
                    # Partially close position
                    await self._close_position(symbol, order.filled_quantity, order.filled_price, "PARTIAL")
        else:
            # Create new position
            position = SimulatedPosition(
                symbol=symbol,
                side=position_side,
                size=order.filled_quantity,
                entry_price=order.filled_price,
                current_price=order.filled_price
            )
            self.portfolio.positions[symbol] = position

        # Update available balance
        trade_value = order.filled_quantity * order.filled_price
        if order.side == "BUY":
            self.portfolio.available_balance -= (trade_value + order.commission)
        else:
            self.portfolio.available_balance += (trade_value - order.commission)

    async def _close_position(self, symbol: str, quantity: float, exit_price: float, reason: str) -> None:
        """Close a position and record the trade."""
        if symbol not in self.portfolio.positions:
            return

        position = self.portfolio.positions[symbol]

        # Calculate P&L
        if position.side == "LONG":
            pnl = (exit_price - position.entry_price) * quantity
        else:  # SHORT
            pnl = (position.entry_price - exit_price) * quantity

        # Calculate commission
        commission = quantity * exit_price * self.commission_rate
        net_pnl = pnl - commission

        # Create trade record
        trade = SimulatedTrade(
            id=str(uuid.uuid4()),
            symbol=symbol,
            side=position.side,
            entry_price=position.entry_price,
            exit_price=exit_price,
            quantity=quantity,
            entry_time=position.entry_time,
            exit_time=datetime.now(UTC),
            pnl=net_pnl,
            commission=commission,
            duration=datetime.now(UTC) - position.entry_time,
            exit_reason=reason
        )

        self.portfolio.completed_trades.append(trade)
        self.portfolio.total_pnl += net_pnl

        # Update position
        if quantity >= position.size:
            # Fully close position
            del self.portfolio.positions[symbol]
        else:
            # Partially close position
            position.size -= quantity
            position.realized_pnl += net_pnl

        logger.info(f"Closed {quantity} {symbol} position: P&L ${net_pnl:.2f}")

    async def _check_position_triggers(self, symbol: str) -> None:
        """Check if any positions should be closed due to stop loss or take profit."""
        if symbol not in self.portfolio.positions:
            return

        position = self.portfolio.positions[symbol]

        if position.should_trigger_stop_loss():
            await self._close_position(symbol, position.size, position.current_price, "STOP_LOSS")
        elif position.should_trigger_take_profit():
            await self._close_position(symbol, position.size, position.current_price, "TAKE_PROFIT")

    def update_simulated_portfolio(self) -> SimulatedPortfolio:
        """Update and return current portfolio state."""
        self.portfolio.update_balance()
        return self.portfolio

    def calculate_simulated_pnl(self) -> float:
        """Calculate total simulated P&L."""
        realized_pnl = self.portfolio.total_pnl
        unrealized_pnl = self.portfolio.get_unrealized_pnl()
        return realized_pnl + unrealized_pnl

    def generate_validation_report(self, thresholds: PerformanceThresholds) -> ValidationResult:
        """Generate validation report for paper trading results."""
        performance = self._calculate_performance_metrics()
        issues = self._validate_performance(performance, thresholds)

        # Check validation criteria
        win_rate_passed = performance.win_rate >= thresholds.min_win_rate
        sharpe_ratio_passed = performance.sharpe_ratio >= thresholds.min_sharpe_ratio
        drawdown_passed = performance.max_drawdown <= thresholds.max_drawdown
        profit_factor_passed = performance.profit_factor >= thresholds.min_profit_factor
        min_trades_passed = performance.total_trades >= thresholds.min_trades

        passed = all([
            win_rate_passed,
            sharpe_ratio_passed,
            drawdown_passed,
            profit_factor_passed,
            min_trades_passed
        ])

        return ValidationResult(
            passed=passed,
            performance=performance,
            validation_period=datetime.now(UTC) - self.start_time,
            issues=issues,
            timestamp=datetime.now(UTC),
            win_rate_passed=win_rate_passed,
            sharpe_ratio_passed=sharpe_ratio_passed,
            drawdown_passed=drawdown_passed,
            profit_factor_passed=profit_factor_passed,
            min_trades_passed=min_trades_passed
        )

    def _calculate_performance_metrics(self) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics."""
        trades = self.portfolio.completed_trades

        if not trades:
            return PerformanceMetrics(
                win_rate=0.0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                total_pnl=0.0,
                gross_profit=0.0,
                gross_loss=0.0,
                profit_factor=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0,
                avg_win=0.0,
                avg_loss=0.0,
                largest_win=0.0,
                largest_loss=0.0,
                avg_trade_duration=timedelta(0),
                start_date=self.start_time,
                end_date=datetime.now(UTC)
            )

        # Basic statistics
        total_trades = len(trades)
        winning_trades = len([t for t in trades if t.pnl > 0])
        losing_trades = len([t for t in trades if t.pnl < 0])

        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0

        # P&L calculations
        total_pnl = sum(t.pnl for t in trades)
        gross_profit = sum(t.pnl for t in trades if t.pnl > 0)
        gross_loss = sum(t.pnl for t in trades if t.pnl < 0)

        profit_factor = abs(gross_profit / gross_loss) if gross_loss != 0 else float('inf')

        # Win/Loss statistics
        winning_pnls = [t.pnl for t in trades if t.pnl > 0]
        losing_pnls = [t.pnl for t in trades if t.pnl < 0]

        avg_win = sum(winning_pnls) / len(winning_pnls) if winning_pnls else 0.0
        avg_loss = sum(losing_pnls) / len(losing_pnls) if losing_pnls else 0.0
        largest_win = max(winning_pnls) if winning_pnls else 0.0
        largest_loss = min(losing_pnls) if losing_pnls else 0.0

        # Duration statistics
        durations = [t.duration for t in trades]
        avg_duration = sum(durations, timedelta(0)) / len(durations) if durations else timedelta(0)

        # Sharpe ratio calculation (simplified)
        if total_trades > 1:
            returns = [t.pnl / self.portfolio.initial_balance for t in trades]
            avg_return = sum(returns) / len(returns)
            return_std = (sum((r - avg_return) ** 2 for r in returns) / (len(returns) - 1)) ** 0.5
            sharpe_ratio = avg_return / return_std if return_std > 0 else 0.0
        else:
            sharpe_ratio = 0.0

        return PerformanceMetrics(
            win_rate=win_rate,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            total_pnl=total_pnl,
            gross_profit=gross_profit,
            gross_loss=gross_loss,
            profit_factor=profit_factor,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=self.portfolio.max_drawdown,
            avg_win=avg_win,
            avg_loss=avg_loss,
            largest_win=largest_win,
            largest_loss=largest_loss,
            avg_trade_duration=avg_duration,
            start_date=self.start_time,
            end_date=datetime.now(UTC)
        )

    def _validate_performance(self, performance: PerformanceMetrics, thresholds: PerformanceThresholds) -> list[ValidationIssue]:
        """Validate performance against thresholds and return issues."""
        issues = []

        if performance.win_rate < thresholds.min_win_rate:
            issues.append(ValidationIssue(
                severity="error",
                category="performance",
                message=f"Win rate {performance.win_rate:.1%} below threshold {thresholds.min_win_rate:.1%}",
                timestamp=datetime.now(UTC)
            ))

        if performance.sharpe_ratio < thresholds.min_sharpe_ratio:
            issues.append(ValidationIssue(
                severity="error",
                category="performance",
                message=f"Sharpe ratio {performance.sharpe_ratio:.2f} below threshold {thresholds.min_sharpe_ratio:.2f}",
                timestamp=datetime.now(UTC)
            ))

        if performance.max_drawdown > thresholds.max_drawdown:
            issues.append(ValidationIssue(
                severity="error",
                category="risk",
                message=f"Max drawdown {performance.max_drawdown:.1%} exceeds threshold {thresholds.max_drawdown:.1%}",
                timestamp=datetime.now(UTC)
            ))

        if performance.profit_factor < thresholds.min_profit_factor:
            issues.append(ValidationIssue(
                severity="warning",
                category="performance",
                message=f"Profit factor {performance.profit_factor:.2f} below threshold {thresholds.min_profit_factor:.2f}",
                timestamp=datetime.now(UTC)
            ))

        if performance.total_trades < thresholds.min_trades:
            issues.append(ValidationIssue(
                severity="error",
                category="system",
                message=f"Total trades {performance.total_trades} below minimum {thresholds.min_trades}",
                timestamp=datetime.now(UTC)
            ))

        return issues

    def compare_with_backtest(self, backtest_results: dict[str, Any]) -> dict[str, Any]:
        """Compare paper trading results with backtesting results."""
        current_performance = self._calculate_performance_metrics()

        comparison = {
            "paper_trading": {
                "win_rate": current_performance.win_rate,
                "sharpe_ratio": current_performance.sharpe_ratio,
                "max_drawdown": current_performance.max_drawdown,
                "profit_factor": current_performance.profit_factor,
                "total_trades": current_performance.total_trades
            },
            "backtest": backtest_results,
            "differences": {},
            "status": "unknown"
        }

        # Calculate differences
        for metric in ["win_rate", "sharpe_ratio", "max_drawdown", "profit_factor"]:
            if metric in backtest_results:
                paper_value = getattr(current_performance, metric)
                backtest_value = backtest_results[metric]
                difference = paper_value - backtest_value
                comparison["differences"][metric] = {
                    "absolute": difference,
                    "relative": (difference / backtest_value * 100) if backtest_value != 0 else 0
                }

        # Determine overall status
        significant_degradation = any(
            abs(diff["relative"]) > 20 for diff in comparison["differences"].values()
        )

        if significant_degradation:
            comparison["status"] = "degraded"
        else:
            comparison["status"] = "consistent"

        return comparison

    def get_portfolio_summary(self) -> dict[str, Any]:
        """Get current portfolio summary."""
        return {
            "initial_balance": self.portfolio.initial_balance,
            "current_balance": self.portfolio.current_balance,
            "available_balance": self.portfolio.available_balance,
            "total_pnl": self.portfolio.total_pnl,
            "unrealized_pnl": self.portfolio.get_unrealized_pnl(),
            "total_exposure": self.portfolio.get_total_exposure(),
            "max_drawdown": self.portfolio.max_drawdown,
            "active_positions": len(self.portfolio.positions),
            "completed_trades": len(self.portfolio.completed_trades),
            "is_active": self.is_active
        }

    def stop_paper_trading(self) -> None:
        """Stop paper trading and close all positions."""
        self.is_active = False

        # Close all open positions
        for symbol in list(self.portfolio.positions.keys()):
            if symbol in self.market_prices:
                asyncio.create_task(
                    self._close_position(symbol, self.portfolio.positions[symbol].size,
                                       self.market_prices[symbol], "MANUAL")
                )

        logger.info("Paper trading stopped")


@dataclass
class PaperTradingConfig:
    """Configuration for paper trading."""
    initial_capital: float = 100000.0
    commission_rate: float = 0.001
    slippage_rate: float = 0.0005
    slippage_bps: float = 5.0  # Slippage in basis points
    max_position_size: float = 0.1
    max_positions: int = 10
    risk_free_rate: float = 0.02
    enable_stop_losses: bool = True
    stop_loss_percentage: float = 0.02
    symbols: list[str] = field(default_factory=lambda: ["BTCUSDT", "ETHUSDT"])
    timeframes: list[str] = field(default_factory=lambda: ["15m", "1h", "4h"])
    session_duration_days: int = 30
    risk_per_trade: float = 0.02
    max_daily_loss: float = 0.05


class PaperTradingEngine:
    """Main paper trading engine that coordinates all components."""

    def __init__(self, config: PaperTradingConfig, data_provider, strategy):
        self.config = config
        self.data_provider = data_provider
        self.strategy = strategy
        self.portfolio = SimulatedPortfolio(
            initial_balance=config.initial_capital,
            current_balance=config.initial_capital,
            available_balance=config.initial_capital
        )
        self.mode = PaperTradingMode(initial_balance=config.initial_capital, commission_rate=config.commission_rate)
        self.is_running = False

    async def start(self):
        """Start the paper trading engine."""
        self.is_running = True
        self.mode.start_paper_trading()
        logger.info("Paper trading engine started")

    async def stop(self):
        """Stop the paper trading engine."""
        self.is_running = False
        self.mode.stop_paper_trading()
        logger.info("Paper trading engine stopped")

    def get_portfolio_summary(self):
        """Get current portfolio summary."""
        return self.portfolio.get_portfolio_summary()

    def get_current_metrics(self):
        """Get current trading metrics."""
        # Use self.portfolio directly since this is on PaperTradingEngine
        return {
            'portfolio_value': self.portfolio.current_balance,
            'total_trades': len(self.portfolio.completed_trades),
            'active_positions': len(self.portfolio.positions),
            'is_running': self.is_running,
            'start_time': self.mode.start_time.isoformat() if hasattr(self.mode, 'start_time') else None
        }

    async def start_paper_trading(self):
        """Start paper trading session."""
        await self.start()
        self.mode.start_paper_trading()

    async def stop_paper_trading(self):
        """Stop paper trading session."""
        await self.stop()
        self.mode.stop_paper_trading()

    def get_trading_results(self):
        """Get trading results summary."""
        return {
            "portfolio_value": self.portfolio.current_balance,
            "total_pnl": self.portfolio.total_pnl,
            "trades_count": len(self.portfolio.completed_trades),
            "positions_count": len(self.portfolio.positions),
            "is_running": self.is_running
        }


class PaperTradingValidator:
    """Validates paper trading results and configurations."""

    def __init__(self):
        self.validation_rules = []

    def validate_config(self, config: PaperTradingConfig) -> bool:
        """Validate paper trading configuration."""
        if config.initial_capital <= 0:
            return False
        if config.commission_rate < 0 or config.commission_rate > 1:
            return False
        if config.slippage_rate < 0 or config.slippage_rate > 1:
            return False
        return True

    def validate_trade(self, trade: SimulatedTrade) -> bool:
        """Validate a simulated trade."""
        if trade.quantity <= 0:
            return False
        if trade.price <= 0:
            return False
        return True

    def validate_portfolio(self, portfolio: SimulatedPortfolio) -> bool:
        """Validate portfolio state."""
        if portfolio.cash < 0:
            logger.warning("Portfolio has negative cash balance")
        return True
