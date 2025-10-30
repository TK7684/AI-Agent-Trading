"""Comprehensive risk management system."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

from pydantic import Field

from .base import BaseModel
from .enums import Direction


class SafeMode(str, Enum):
    """Safe mode states."""
    NORMAL = "normal"
    CAUTION = "caution"
    SAFE_MODE = "safe_mode"
    EMERGENCY = "emergency"


class StopType(str, Enum):
    """Stop loss types."""
    ATR_BASED = "atr_based"
    BREAKEVEN = "breakeven"
    TRAILING = "trailing"
    FIXED = "fixed"


@dataclass
class PortfolioMetrics:
    """Portfolio performance metrics."""
    total_equity: Decimal
    available_margin: Decimal
    used_margin: Decimal
    unrealized_pnl: Decimal
    daily_pnl: Decimal
    monthly_pnl: Decimal
    daily_drawdown: float
    monthly_drawdown: float
    max_drawdown: float
    win_rate: float
    sharpe_ratio: float
    total_trades: int
    open_positions: int


class RiskLimits(BaseModel):
    """Risk management limits and parameters."""

    # Position sizing limits
    min_risk_per_trade: float = Field(0.0025, ge=0.001, le=0.01, description="Minimum risk per trade (0.25%)")
    max_risk_per_trade: float = Field(0.02, ge=0.005, le=0.05, description="Maximum risk per trade (2%)")
    max_portfolio_risk: float = Field(0.20, ge=0.10, le=0.30, description="Maximum portfolio risk (20%)")

    # Leverage limits
    default_leverage: float = Field(3.0, ge=1.0, le=10.0, description="Default leverage (3x)")
    max_leverage: float = Field(10.0, ge=1.0, le=50.0, description="Maximum leverage (10x)")

    # Drawdown protection
    daily_drawdown_limit: float = Field(0.08, ge=0.05, le=0.15, description="Daily drawdown limit (8%)")
    monthly_drawdown_limit: float = Field(0.20, ge=0.10, le=0.30, description="Monthly drawdown limit (20%)")

    # Correlation limits
    max_correlation_exposure: float = Field(0.15, ge=0.05, le=0.25, description="Max correlated exposure (15%)")
    correlation_threshold: float = Field(0.7, ge=0.5, le=0.9, description="Correlation threshold")

    # Stop loss parameters
    min_atr_multiplier: float = Field(1.5, ge=1.0, le=3.0, description="Minimum ATR multiplier for stops")
    max_atr_multiplier: float = Field(3.0, ge=2.0, le=5.0, description="Maximum ATR multiplier for stops")
    trailing_stop_activation: float = Field(0.02, ge=0.01, le=0.05, description="Trailing stop activation (2%)")

    # Safe mode parameters
    safe_mode_cooldown_hours: int = Field(24, ge=1, le=72, description="Safe mode cooldown period")
    position_reduction_factor: float = Field(0.5, ge=0.1, le=0.8, description="Position size reduction in safe mode")


class Position(BaseModel):
    """Trading position model."""

    position_id: str = Field(..., description="Unique position ID")
    symbol: str = Field(..., description="Trading symbol")
    direction: Direction = Field(..., description="Position direction")

    # Size and pricing
    quantity: Decimal = Field(..., gt=0, description="Position quantity")
    entry_price: Decimal = Field(..., gt=0, description="Average entry price")
    current_price: Decimal = Field(..., gt=0, description="Current market price")

    # Risk management
    stop_loss: Decimal = Field(..., gt=0, description="Stop loss price")
    take_profit: Optional[Decimal] = Field(None, gt=0, description="Take profit price")
    stop_type: StopType = Field(StopType.ATR_BASED, description="Stop loss type")

    # Position metrics
    unrealized_pnl: Decimal = Field(..., description="Unrealized P&L")
    realized_pnl: Decimal = Field(0, description="Realized P&L")
    leverage: float = Field(1.0, gt=0, le=50, description="Position leverage")

    # Timing
    opened_at: datetime = Field(..., description="Position open time")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update time")

    # Risk tracking
    initial_risk: Decimal = Field(..., gt=0, description="Initial risk amount")
    current_risk: Decimal = Field(..., description="Current risk amount")
    max_adverse_excursion: Decimal = Field(0, description="Maximum adverse excursion")

    def calculate_unrealized_pnl(self) -> Decimal:
        """Calculate current unrealized P&L."""
        if self.direction == Direction.LONG:
            pnl = (self.current_price - self.entry_price) * self.quantity
        else:
            pnl = (self.entry_price - self.current_price) * self.quantity

        self.unrealized_pnl = pnl
        return pnl

    def calculate_position_value(self) -> Decimal:
        """Calculate total position value."""
        return self.quantity * self.current_price

    def get_risk_percentage(self, portfolio_value: Decimal) -> float:
        """Get position risk as percentage of portfolio."""
        return float(abs(self.current_risk) / portfolio_value) * 100

    def should_trail_stop(self) -> bool:
        """Check if trailing stop should be activated."""
        if self.stop_type != StopType.TRAILING:
            return False

        pnl_pct = float(self.unrealized_pnl / (self.entry_price * self.quantity))
        return abs(pnl_pct) > 0.02  # 2% profit threshold


class RiskAssessment(BaseModel):
    """Risk assessment result."""

    approved: bool = Field(..., description="Whether trade is approved")
    risk_score: float = Field(..., ge=0, le=100, description="Risk score (0-100)")

    # Risk metrics
    position_risk_pct: float = Field(..., description="Position risk percentage")
    portfolio_risk_pct: float = Field(..., description="Total portfolio risk percentage")
    leverage_used: float = Field(..., description="Leverage used")
    margin_utilization: float = Field(..., description="Margin utilization percentage")

    # Risk factors
    risk_factors: list[str] = Field(default_factory=list, description="Identified risk factors")
    warnings: list[str] = Field(default_factory=list, description="Risk warnings")

    # Adjustments
    suggested_position_size: Optional[Decimal] = Field(None, description="Suggested position size")
    suggested_leverage: Optional[float] = Field(None, description="Suggested leverage")

    # Reasoning
    assessment_reason: str = Field(..., description="Assessment reasoning")
    safe_mode_status: SafeMode = Field(SafeMode.NORMAL, description="Current safe mode status")


class PositionSizer(BaseModel):
    """Position sizing calculator with confidence-based scaling."""

    base_risk_pct: float = Field(0.01, ge=0.0025, le=0.02, description="Base risk percentage (1%)")
    confidence_multiplier_range: tuple[float, float] = Field((0.25, 2.0), description="Confidence scaling range")

    def calculate_position_size(
        self,
        portfolio_value: Decimal,
        entry_price: Decimal,
        stop_loss: Decimal,
        confidence: float,
        leverage: float = 1.0
    ) -> tuple[Decimal, float]:
        """
        Calculate position size based on risk and confidence.

        Returns:
            Tuple of (position_size, risk_percentage)
        """
        # Scale risk based on confidence (0.25x to 2x)
        confidence_multiplier = self._calculate_confidence_multiplier(confidence)
        risk_pct = self.base_risk_pct * confidence_multiplier

        # Ensure risk stays within bounds
        risk_pct = max(0.0025, min(0.02, risk_pct))  # 0.25% to 2%

        # Calculate risk amount
        risk_amount = portfolio_value * Decimal(str(risk_pct))

        # Calculate stop distance
        stop_distance = abs(entry_price - stop_loss)
        if stop_distance == 0:
            raise ValueError("Stop loss cannot equal entry price")

        # Calculate base position size (in base currency units)
        position_size = risk_amount / stop_distance



        # Note: leverage doesn't multiply position size, it reduces margin requirement
        # Position size stays the same, but we can control more with less margin

        return position_size, risk_pct

    def _calculate_confidence_multiplier(self, confidence: float) -> float:
        """Calculate confidence-based multiplier."""
        # Normalize confidence to 0-1 range
        confidence = max(0.0, min(1.0, confidence))

        # Map confidence to multiplier range
        min_mult, max_mult = self.confidence_multiplier_range
        multiplier = min_mult + (confidence * (max_mult - min_mult))

        return multiplier


class CorrelationMonitor(BaseModel):
    """Portfolio correlation monitoring."""

    correlation_matrix: dict[str, dict[str, float]] = Field(default_factory=dict, description="Symbol correlation matrix")
    correlation_threshold: float = Field(0.7, ge=0.5, le=0.9, description="Correlation threshold")
    max_correlated_exposure: float = Field(0.15, ge=0.05, le=0.25, description="Max correlated exposure")

    def update_correlation(self, symbol1: str, symbol2: str, correlation: float) -> None:
        """Update correlation between two symbols."""
        if symbol1 not in self.correlation_matrix:
            self.correlation_matrix[symbol1] = {}
        if symbol2 not in self.correlation_matrix:
            self.correlation_matrix[symbol2] = {}

        self.correlation_matrix[symbol1][symbol2] = correlation
        self.correlation_matrix[symbol2][symbol1] = correlation

    def check_correlation_limits(
        self,
        new_symbol: str,
        new_position_value: Decimal,
        existing_positions: list[Position],
        portfolio_value: Decimal
    ) -> tuple[bool, list[str]]:
        """
        Check if new position would violate correlation limits.

        Returns:
            Tuple of (is_allowed, violation_reasons)
        """
        violations = []

        # Calculate existing correlated exposure
        correlated_exposure = Decimal(0)
        correlated_symbols = []

        for position in existing_positions:
            correlation = self.get_correlation(new_symbol, position.symbol)
            # Only consider positions with significant correlation
            if abs(correlation) >= self.correlation_threshold:
                correlated_exposure += position.calculate_position_value()
                correlated_symbols.append(f"{position.symbol}({correlation:+.2f})")

        # Only check limits if there are actually correlated positions
        if correlated_exposure > 0:
            # Add new position exposure
            total_correlated_exposure = correlated_exposure + new_position_value
            exposure_pct = float(total_correlated_exposure / portfolio_value)

            if exposure_pct > self.max_correlated_exposure:
                violations.append(
                    f"Correlated exposure would be {exposure_pct:.1%}, exceeding limit of {self.max_correlated_exposure:.1%}"
                )
                violations.append(f"Correlated symbols: {correlated_symbols}")

        return len(violations) == 0, violations

    def get_correlation(self, symbol1: str, symbol2: str) -> float:
        """Get correlation between two symbols."""
        if symbol1 == symbol2:
            return 1.0

        if symbol1 in self.correlation_matrix and symbol2 in self.correlation_matrix[symbol1]:
            return self.correlation_matrix[symbol1][symbol2]

        return 0.0  # Default to no correlation if not available


class DrawdownProtection(BaseModel):
    """Drawdown protection and safe mode management."""

    daily_limit: float = Field(0.08, ge=0.05, le=0.15, description="Daily drawdown limit (8%)")
    monthly_limit: float = Field(0.20, ge=0.10, le=0.30, description="Monthly drawdown limit (20%)")
    safe_mode_cooldown: timedelta = Field(default_factory=lambda: timedelta(hours=24), description="Safe mode cooldown")

    # State tracking
    current_safe_mode: SafeMode = Field(SafeMode.NORMAL, description="Current safe mode")
    safe_mode_triggered_at: Optional[datetime] = Field(None, description="When safe mode was triggered")
    daily_high_water_mark: Decimal = Field(Decimal(0), description="Daily high water mark")
    monthly_high_water_mark: Decimal = Field(Decimal(0), description="Monthly high water mark")

    def check_drawdown_limits(self, portfolio_metrics: PortfolioMetrics) -> tuple[SafeMode, list[str]]:
        """
        Check drawdown limits and determine safe mode status.

        Returns:
            Tuple of (safe_mode_status, trigger_reasons)
        """
        triggers = []
        new_safe_mode = SafeMode.NORMAL

        # Check daily drawdown
        if portfolio_metrics.daily_drawdown >= self.daily_limit:
            triggers.append(f"Daily drawdown {portfolio_metrics.daily_drawdown:.1%} exceeds limit {self.daily_limit:.1%}")
            new_safe_mode = SafeMode.SAFE_MODE

        # Check monthly drawdown
        if portfolio_metrics.monthly_drawdown >= self.monthly_limit:
            triggers.append(f"Monthly drawdown {portfolio_metrics.monthly_drawdown:.1%} exceeds limit {self.monthly_limit:.1%}")
            new_safe_mode = SafeMode.SAFE_MODE

        # Emergency mode for extreme drawdowns
        if portfolio_metrics.daily_drawdown >= self.daily_limit * 1.5:
            triggers.append(f"Extreme daily drawdown {portfolio_metrics.daily_drawdown:.1%}")
            new_safe_mode = SafeMode.EMERGENCY

        # Update safe mode status
        if new_safe_mode != SafeMode.NORMAL and self.current_safe_mode == SafeMode.NORMAL:
            self.safe_mode_triggered_at = datetime.now(UTC)

        self.current_safe_mode = new_safe_mode
        return new_safe_mode, triggers

    def can_exit_safe_mode(self) -> bool:
        """Check if safe mode cooldown period has passed."""
        if self.current_safe_mode == SafeMode.NORMAL:
            return True

        if not self.safe_mode_triggered_at:
            return False

        # Ensure both datetimes are timezone-aware for comparison
        triggered_at = self.safe_mode_triggered_at
        if triggered_at.tzinfo is None:
            triggered_at = triggered_at.replace(tzinfo=UTC)
        return datetime.now(UTC) - triggered_at >= self.safe_mode_cooldown

    def get_position_size_adjustment(self) -> float:
        """Get position size adjustment factor based on safe mode."""
        if self.current_safe_mode == SafeMode.NORMAL:
            return 1.0
        elif self.current_safe_mode == SafeMode.CAUTION:
            return 0.75
        elif self.current_safe_mode == SafeMode.SAFE_MODE:
            return 0.5
        else:  # EMERGENCY
            return 0.0


class StopLossManager(BaseModel):
    """Stop loss management system."""

    atr_multiplier: float = Field(2.0, ge=1.0, le=5.0, description="ATR multiplier for stops")
    trailing_activation_pct: float = Field(0.02, ge=0.01, le=0.05, description="Trailing stop activation")
    breakeven_trigger_pct: float = Field(0.015, ge=0.01, le=0.03, description="Breakeven trigger")

    def calculate_atr_stop(
        self,
        entry_price: Decimal,
        direction: Direction,
        atr_value: float,
        multiplier: Optional[float] = None
    ) -> Decimal:
        """Calculate ATR-based stop loss."""
        if multiplier is None:
            multiplier = self.atr_multiplier

        # Convert entry_price to Decimal if it's not already
        if not isinstance(entry_price, Decimal):
            entry_price = Decimal(str(entry_price))

        stop_distance = Decimal(str(atr_value * multiplier))

        if direction == Direction.LONG:
            return entry_price - stop_distance
        else:
            return entry_price + stop_distance

    def calculate_trailing_stop(
        self,
        position: Position,
        current_price: Decimal,
        atr_value: float
    ) -> Optional[Decimal]:
        """Calculate trailing stop loss."""
        if position.stop_type != StopType.TRAILING:
            return None

        # Check if trailing should be activated
        pnl_pct = float(position.unrealized_pnl / (position.entry_price * position.quantity))
        if abs(pnl_pct) < self.trailing_activation_pct:
            return position.stop_loss  # Keep original stop

        # Calculate new trailing stop
        trail_distance = Decimal(str(atr_value * self.atr_multiplier))

        if position.direction == Direction.LONG:
            new_stop = current_price - trail_distance
            # Only move stop up for long positions
            return max(new_stop, position.stop_loss)
        else:
            new_stop = current_price + trail_distance
            # Only move stop down for short positions
            return min(new_stop, position.stop_loss)

    def calculate_breakeven_stop(self, position: Position) -> Optional[Decimal]:
        """Calculate breakeven stop loss."""
        pnl_pct = float(position.unrealized_pnl / (position.entry_price * position.quantity))

        if abs(pnl_pct) >= self.breakeven_trigger_pct:
            return position.entry_price

        return None

    def update_stop_loss(self, position: Position, current_price: Decimal, atr_value: float) -> Decimal:
        """Update stop loss based on position type and market conditions."""
        if position.stop_type == StopType.TRAILING:
            new_stop = self.calculate_trailing_stop(position, current_price, atr_value)
            if new_stop:
                return new_stop

        elif position.stop_type == StopType.BREAKEVEN:
            breakeven_stop = self.calculate_breakeven_stop(position)
            if breakeven_stop:
                return breakeven_stop

        elif position.stop_type == StopType.ATR_BASED:
            # For ATR-based stops, recalculate based on current price and ATR
            new_stop = self.calculate_atr_stop(current_price, position.direction, atr_value)
            # Only move stop in favorable direction
            if position.direction == Direction.LONG:
                return max(new_stop, position.stop_loss)
            else:
                return min(new_stop, position.stop_loss)

        return position.stop_loss


class RiskManager(BaseModel):
    """Comprehensive risk management system."""

    # Components
    risk_limits: RiskLimits = Field(default_factory=RiskLimits, description="Risk limits configuration")
    position_sizer: PositionSizer = Field(default_factory=PositionSizer, description="Position sizing calculator")
    correlation_monitor: CorrelationMonitor = Field(default_factory=CorrelationMonitor, description="Correlation monitor")
    drawdown_protection: DrawdownProtection = Field(default_factory=DrawdownProtection, description="Drawdown protection")
    stop_manager: StopLossManager = Field(default_factory=StopLossManager, description="Stop loss manager")

    # State
    current_positions: list[Position] = Field(default_factory=list, description="Current positions")
    portfolio_metrics: Optional[PortfolioMetrics] = Field(None, description="Current portfolio metrics")

    def assess_trade_risk(
        self,
        symbol: str,
        direction: Direction,
        entry_price: Decimal,
        stop_loss: Decimal,
        confidence: float,
        portfolio_value: Decimal,
        available_margin: Decimal,
        leverage: float = 3.0
    ) -> RiskAssessment:
        """
        Comprehensive trade risk assessment.

        Returns:
            RiskAssessment with approval status and risk metrics
        """
        risk_factors = []
        warnings = []
        approved = True

        # Check safe mode status
        safe_mode = self.drawdown_protection.current_safe_mode
        if safe_mode == SafeMode.EMERGENCY:
            return RiskAssessment(
                approved=False,
                risk_score=100.0,
                position_risk_pct=0.0,
                portfolio_risk_pct=0.0,
                leverage_used=0.0,
                margin_utilization=0.0,
                risk_factors=["Emergency safe mode active - no new positions allowed"],
                assessment_reason="Emergency safe mode prevents new positions",
                safe_mode_status=safe_mode
            )

        # Calculate position size
        try:
            position_size, risk_pct = self.position_sizer.calculate_position_size(
                portfolio_value, entry_price, stop_loss, confidence, leverage
            )
        except ValueError as e:
            return RiskAssessment(
                approved=False,
                risk_score=100.0,
                position_risk_pct=0.0,
                portfolio_risk_pct=0.0,
                leverage_used=leverage,
                margin_utilization=0.0,
                risk_factors=[f"Position sizing error: {str(e)}"],
                assessment_reason="Invalid position sizing parameters",
                safe_mode_status=safe_mode
            )

        # Apply safe mode adjustment
        safe_mode_adjustment = self.drawdown_protection.get_position_size_adjustment()
        adjusted_position_size = position_size * Decimal(str(safe_mode_adjustment))
        adjusted_risk_pct = risk_pct * safe_mode_adjustment

        # Calculate position value and margin
        position_value = adjusted_position_size * entry_price
        margin_required = position_value / Decimal(str(leverage))
        margin_utilization = float(margin_required / available_margin) * 100 if available_margin > 0 else 100



        # Check leverage limits
        if leverage > self.risk_limits.max_leverage:
            risk_factors.append(f"Leverage {leverage}x exceeds maximum {self.risk_limits.max_leverage}x")
            approved = False

        # Check risk percentage limits
        if adjusted_risk_pct > self.risk_limits.max_risk_per_trade:
            risk_factors.append(f"Risk {adjusted_risk_pct:.2%} exceeds maximum {self.risk_limits.max_risk_per_trade:.2%}")
            approved = False

        # Check portfolio risk
        current_portfolio_risk = self._calculate_current_portfolio_risk(portfolio_value)
        total_portfolio_risk = current_portfolio_risk + adjusted_risk_pct

        if total_portfolio_risk > self.risk_limits.max_portfolio_risk:
            risk_factors.append(f"Total portfolio risk {total_portfolio_risk:.2%} exceeds limit {self.risk_limits.max_portfolio_risk:.2%}")
            approved = False

        # Check margin requirements
        if margin_utilization > 90:
            risk_factors.append(f"Margin utilization {margin_utilization:.1f}% too high")
            approved = False
        elif margin_utilization > 75:
            warnings.append(f"High margin utilization {margin_utilization:.1f}%")

        # Check correlation limits
        correlation_allowed, correlation_violations = self.correlation_monitor.check_correlation_limits(
            symbol, position_value, self.current_positions, portfolio_value
        )

        if not correlation_allowed:
            risk_factors.extend(correlation_violations)
            approved = False

        # Calculate risk score
        risk_score = self._calculate_risk_score(
            adjusted_risk_pct, total_portfolio_risk, leverage, margin_utilization, len(risk_factors)
        )

        # Generate assessment reason
        if approved:
            reason = f"Trade approved with {adjusted_risk_pct:.2%} risk, {leverage}x leverage"
        else:
            reason = f"Trade rejected due to: {'; '.join(risk_factors[:2])}"

        return RiskAssessment(
            approved=approved,
            risk_score=risk_score,
            position_risk_pct=adjusted_risk_pct * 100,
            portfolio_risk_pct=total_portfolio_risk * 100,
            leverage_used=leverage,
            margin_utilization=margin_utilization,
            risk_factors=risk_factors,
            warnings=warnings,
            suggested_position_size=adjusted_position_size if safe_mode_adjustment < 1.0 else None,
            suggested_leverage=min(leverage, self.risk_limits.default_leverage) if leverage > self.risk_limits.default_leverage else None,
            assessment_reason=reason,
            safe_mode_status=safe_mode
        )

    def update_portfolio_metrics(self, metrics: PortfolioMetrics) -> None:
        """Update portfolio metrics and check drawdown limits."""
        self.portfolio_metrics = metrics

        # Check drawdown limits
        safe_mode, triggers = self.drawdown_protection.check_drawdown_limits(metrics)

        if triggers:
            print(f"Drawdown protection triggered: {'; '.join(triggers)}")

    def add_position(self, position: Position) -> None:
        """Add a new position to tracking."""
        self.current_positions.append(position)

    def remove_position(self, position_id: str) -> None:
        """Remove a position from tracking."""
        self.current_positions = [p for p in self.current_positions if p.position_id != position_id]

    def update_position_stops(self, symbol: str, current_price: Decimal, atr_value: float) -> None:
        """Update stop losses for positions."""
        for position in self.current_positions:
            if position.symbol == symbol:
                new_stop = self.stop_manager.update_stop_loss(position, current_price, atr_value)
                if new_stop != position.stop_loss:
                    position.stop_loss = new_stop
                    position.updated_at = datetime.now(UTC)

    def _calculate_current_portfolio_risk(self, portfolio_value: Decimal) -> float:
        """Calculate current portfolio risk from open positions."""
        total_risk = Decimal(0)

        for position in self.current_positions:
            total_risk += abs(position.current_risk)

        return float(total_risk / portfolio_value) if portfolio_value > 0 else 0.0

    def _calculate_risk_score(
        self,
        risk_pct: float,
        portfolio_risk: float,
        leverage: float,
        margin_util: float,
        risk_factor_count: int
    ) -> float:
        """Calculate overall risk score (0-100)."""
        # Base score from risk percentage (0-40 points)
        risk_score = (risk_pct / self.risk_limits.max_risk_per_trade) * 40

        # Portfolio risk component (0-25 points)
        portfolio_score = (portfolio_risk / self.risk_limits.max_portfolio_risk) * 25

        # Leverage component (0-20 points)
        leverage_score = (leverage / self.risk_limits.max_leverage) * 20

        # Margin utilization component (0-10 points)
        margin_score = (margin_util / 100) * 10

        # Risk factor penalty (5 points per factor)
        penalty = risk_factor_count * 5

        total_score = risk_score + portfolio_score + leverage_score + margin_score + penalty
        return min(100.0, max(0.0, total_score))

    def get_risk_summary(self) -> dict[str, Any]:
        """Get comprehensive risk summary."""
        if not self.portfolio_metrics:
            return {"error": "No portfolio metrics available"}

        return {
            "safe_mode": self.drawdown_protection.current_safe_mode,
            "daily_drawdown": f"{self.portfolio_metrics.daily_drawdown:.2%}",
            "monthly_drawdown": f"{self.portfolio_metrics.monthly_drawdown:.2%}",
            "portfolio_risk": f"{self._calculate_current_portfolio_risk(self.portfolio_metrics.total_equity):.2%}",
            "open_positions": len(self.current_positions),
            "margin_utilization": f"{float(self.portfolio_metrics.used_margin / self.portfolio_metrics.total_equity) * 100:.1f}%",
            "can_exit_safe_mode": self.drawdown_protection.can_exit_safe_mode(),
        }
