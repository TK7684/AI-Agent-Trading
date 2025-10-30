"""Order and execution models."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Optional
from uuid import uuid4

from pydantic import Field, field_validator, model_validator

from .base import BaseModel
from .enums import Direction, OrderStatus, OrderType, Timeframe


class OrderDecision(BaseModel):
    """Trading order decision with risk management."""

    decision_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique decision ID")
    signal_id: str = Field(..., description="Source signal ID")
    symbol: str = Field(..., description="Trading symbol")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Decision timestamp")

    # Order details
    direction: Direction = Field(..., description="Trade direction")
    order_type: OrderType = Field(..., description="Order type")

    # Position sizing
    base_quantity: Decimal = Field(..., gt=0, description="Base position size")
    risk_adjusted_quantity: Decimal = Field(..., gt=0, description="Risk-adjusted position size")
    max_position_value: Decimal = Field(..., gt=0, description="Maximum position value")

    # Price levels
    entry_price: Decimal = Field(..., gt=0, description="Target entry price")
    stop_loss: Decimal = Field(..., gt=0, description="Stop loss price")
    take_profit: Optional[Decimal] = Field(None, gt=0, description="Take profit price")

    # Risk management
    risk_amount: Decimal = Field(..., gt=0, description="Risk amount in base currency")
    risk_percentage: float = Field(..., gt=0, le=10, description="Risk as percentage of portfolio")
    leverage: float = Field(1.0, gt=0, le=50, description="Leverage multiplier")

    # Portfolio context
    portfolio_value: Decimal = Field(..., gt=0, description="Current portfolio value")
    available_margin: Decimal = Field(..., ge=0, description="Available margin")
    current_exposure: float = Field(0, ge=0, le=1, description="Current portfolio exposure")

    # Decision factors
    confidence_score: float = Field(..., ge=0, le=1, description="Decision confidence")
    confluence_score: float = Field(..., ge=0, le=100, description="Signal confluence score")
    risk_reward_ratio: float = Field(..., gt=0, description="Expected risk/reward ratio")

    # Execution parameters
    slippage_tolerance: float = Field(0.001, ge=0, le=0.1, description="Acceptable slippage")
    max_execution_time: int = Field(300, gt=0, description="Max execution time in seconds")
    partial_fill_acceptable: bool = Field(True, description="Accept partial fills")

    # Decision reasoning
    decision_reason: str = Field(..., description="Human-readable decision reasoning")
    risk_factors: list[str] = Field(default_factory=list, description="Identified risk factors")
    supporting_factors: list[str] = Field(default_factory=list, description="Supporting factors")

    # Metadata
    timeframe_context: Timeframe = Field(..., description="Primary analysis timeframe")
    market_conditions: dict[str, Any] = Field(default_factory=dict, description="Market condition snapshot")

    @field_validator("risk_adjusted_quantity")
    @classmethod
    def validate_risk_adjustment(cls, v, info):
        """Validate risk-adjusted quantity is reasonable."""
        if info.data and "base_quantity" in info.data and info.data["base_quantity"]:
            base = info.data["base_quantity"]
            if v > base * Decimal("2"):
                raise ValueError("Risk-adjusted quantity cannot exceed 2x base quantity")
            if v < base * Decimal("0.1"):
                raise ValueError("Risk-adjusted quantity cannot be less than 10% of base")
        return v

    @model_validator(mode='after')
    def validate_total_portfolio_risk(self):
        """Validate total portfolio risk doesn't exceed 20%."""
        total_risk = self.risk_percentage + (self.current_exposure * 100)
        if total_risk > 20:  # 20% max portfolio risk
            raise ValueError("Total portfolio risk would exceed 20%")
        return self

    @field_validator("leverage")
    @classmethod
    def validate_leverage(cls, v, info):
        """Validate leverage limits."""
        if v > 10:  # Max 10x leverage
            raise ValueError("Leverage cannot exceed 10x")
        if info.data and "risk_percentage" in info.data and info.data["risk_percentage"]:
            # Higher leverage requires lower risk percentage
            max_risk_for_leverage = 5.0 / v  # Inverse relationship
            if info.data["risk_percentage"] > max_risk_for_leverage:
                raise ValueError(f"Risk percentage too high for {v}x leverage")
        return v

    @field_validator("stop_loss")
    @classmethod
    def validate_stop_loss(cls, v, info):
        """Validate stop loss placement."""
        if info.data and "entry_price" in info.data and "direction" in info.data:
            entry = info.data["entry_price"]
            direction = info.data["direction"]

            if direction == Direction.LONG and v >= entry:
                raise ValueError("Stop loss must be below entry price for long positions")
            elif direction == Direction.SHORT and v <= entry:
                raise ValueError("Stop loss must be above entry price for short positions")

            # Validate stop loss is not too far (max 20% from entry)
            diff_pct = abs(float(v - entry) / float(entry))
            if diff_pct > 0.2:
                raise ValueError("Stop loss too far from entry (>20%)")
        return v

    @field_validator("take_profit")
    @classmethod
    def validate_take_profit(cls, v, info):
        """Validate take profit placement."""
        if v and info.data and "entry_price" in info.data and "direction" in info.data:
            entry = info.data["entry_price"]
            direction = info.data["direction"]

            if direction == Direction.LONG and v <= entry:
                raise ValueError("Take profit must be above entry price for long positions")
            elif direction == Direction.SHORT and v >= entry:
                raise ValueError("Take profit must be below entry price for short positions")
        return v

    def calculate_position_value(self) -> Decimal:
        """Calculate total position value including leverage."""
        return self.risk_adjusted_quantity * self.entry_price * Decimal(str(self.leverage))

    def calculate_margin_required(self) -> Decimal:
        """Calculate margin required for position."""
        position_value = self.calculate_position_value()
        return position_value / Decimal(str(self.leverage))

    def validate_margin_requirements(self) -> bool:
        """Check if sufficient margin is available."""
        required_margin = self.calculate_margin_required()
        return self.available_margin >= required_margin

    def get_risk_metrics(self) -> dict[str, float]:
        """Get comprehensive risk metrics."""
        position_value = float(self.calculate_position_value())
        portfolio_value = float(self.portfolio_value)

        return {
            "position_size_pct": (position_value / portfolio_value) * 100,
            "risk_amount": float(self.risk_amount),
            "risk_percentage": self.risk_percentage,
            "leverage": self.leverage,
            "risk_reward_ratio": self.risk_reward_ratio,
            "margin_utilization": float(self.calculate_margin_required() / self.available_margin) * 100 if self.available_margin > 0 else 0,
        }


class ExecutionResult(BaseModel):
    """Result of order execution."""

    execution_id: str = Field(default_factory=lambda: str(uuid4()), description="Execution ID")
    decision_id: str = Field(..., description="Source decision ID")
    order_id: str = Field(..., description="Exchange order ID")

    # Execution details
    status: OrderStatus = Field(..., description="Execution status")
    filled_quantity: Decimal = Field(0, ge=0, description="Filled quantity")
    average_price: Optional[Decimal] = Field(None, gt=0, description="Average fill price")

    # Timing
    submitted_at: datetime = Field(..., description="Order submission time")
    filled_at: Optional[datetime] = Field(None, description="Order fill time")

    # Costs
    commission: Decimal = Field(0, ge=0, description="Commission paid")
    slippage: Optional[float] = Field(None, description="Execution slippage")

    # Execution quality
    execution_time_ms: Optional[int] = Field(None, gt=0, description="Execution time in milliseconds")
    partial_fills: list[dict[str, Any]] = Field(default_factory=list, description="Partial fill details")

    # Error handling
    error_message: Optional[str] = Field(None, description="Error message if failed")
    retry_count: int = Field(0, ge=0, description="Number of retries attempted")

    def is_fully_filled(self) -> bool:
        """Check if order is fully filled."""
        return self.status == OrderStatus.FILLED

    def is_partially_filled(self) -> bool:
        """Check if order is partially filled."""
        return self.status == OrderStatus.PARTIALLY_FILLED

    def get_fill_percentage(self, original_quantity: Decimal) -> float:
        """Get fill percentage."""
        if original_quantity <= 0:
            return 0.0
        return float(self.filled_quantity / original_quantity) * 100

class TradeOutcome(BaseModel):
    """Complete trade outcome with performance metrics."""

    trade_id: str = Field(..., description="Unique trade identifier")
    symbol: str = Field(..., description="Trading symbol")
    direction: Direction = Field(..., description="Trade direction")

    # Price and sizing
    entry_price: Decimal = Field(..., gt=0, description="Entry price")
    exit_price: Decimal = Field(..., gt=0, description="Exit price")
    position_size: Decimal = Field(..., gt=0, description="Position size")

    # Timing
    entry_time: datetime = Field(..., description="Entry timestamp")
    exit_time: datetime = Field(..., description="Exit timestamp")

    # Performance
    pnl: Decimal = Field(..., description="Profit/Loss in base currency")
    commission: Decimal = Field(0, ge=0, description="Total commission paid")

    # Analysis metadata
    confidence: float = Field(..., ge=0, le=1, description="Signal confidence")
    pattern_id: str = Field(..., description="Pattern that triggered trade")
    market_regime: str = Field(..., description="Market regime during trade")

    @property
    def holding_period(self) -> timedelta:
        """Calculate holding period."""
        return self.exit_time - self.entry_time

    @property
    def return_percentage(self) -> float:
        """Calculate return percentage."""
        if self.direction == Direction.LONG:
            return float((self.exit_price - self.entry_price) / self.entry_price) * 100
        else:
            return float((self.entry_price - self.exit_price) / self.entry_price) * 100

    @property
    def is_winner(self) -> bool:
        """Check if trade was profitable."""
        return self.pnl > 0

    def get_r_multiple(self, initial_risk: Decimal) -> float:
        """Calculate R-multiple (profit/loss relative to initial risk)."""
        if initial_risk <= 0:
            return 0.0
        return float(self.pnl / initial_risk)
