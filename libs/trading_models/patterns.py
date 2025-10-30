"""Pattern recognition models."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import Field, field_validator

from .base import BaseModel
from .enums import PatternType, Timeframe


class PatternHit(BaseModel):
    """Detected pattern with confidence and metadata."""

    pattern_id: str = Field(..., description="Unique pattern identifier")
    pattern_type: PatternType = Field(..., description="Type of pattern detected")
    symbol: str = Field(..., description="Trading symbol")
    timeframe: Timeframe = Field(..., description="Timeframe where pattern was detected")
    timestamp: datetime = Field(..., description="Pattern detection timestamp")

    # Pattern confidence and scoring
    confidence: float = Field(..., ge=0, le=1, description="Pattern confidence (0-1)")
    strength: float = Field(..., ge=0, le=10, description="Pattern strength (0-10)")

    # Price levels
    entry_price: Optional[Decimal] = Field(None, gt=0, description="Suggested entry price")
    stop_loss: Optional[Decimal] = Field(None, gt=0, description="Suggested stop loss")
    take_profit: Optional[Decimal] = Field(None, gt=0, description="Suggested take profit")

    # Support/Resistance levels
    support_levels: list[Decimal] = Field(default_factory=list, description="Support price levels")
    resistance_levels: list[Decimal] = Field(default_factory=list, description="Resistance price levels")

    # Pattern-specific data
    pattern_data: dict[str, Any] = Field(default_factory=dict, description="Pattern-specific metadata")

    # Validation context
    bars_analyzed: int = Field(..., gt=0, description="Number of bars used in analysis")
    lookback_period: int = Field(..., gt=0, description="Lookback period for pattern detection")

    # Performance tracking
    historical_win_rate: Optional[float] = Field(None, ge=0, le=1, description="Historical win rate for this pattern")
    avg_return: Optional[float] = Field(None, description="Average return for this pattern")

    @field_validator("support_levels", "resistance_levels")
    @classmethod
    def validate_price_levels(cls, v):
        """Validate price levels are positive and sorted."""
        if v:
            if any(level <= 0 for level in v):
                raise ValueError("All price levels must be positive")
            if v != sorted(v):
                raise ValueError("Price levels must be sorted")
        return v

    @field_validator("stop_loss")
    @classmethod
    def validate_stop_loss(cls, v, info):
        """Validate stop loss relative to entry price."""
        if v and info.data and "entry_price" in info.data and info.data["entry_price"]:
            entry = info.data["entry_price"]
            # For long positions, stop should be below entry
            # For short positions, stop should be above entry
            # We'll validate this is reasonable (within 50% of entry)
            diff_pct = abs(float(v - entry) / float(entry))
            if diff_pct > 0.5:
                raise ValueError("Stop loss too far from entry price (>50%)")
        return v

    @field_validator("take_profit")
    @classmethod
    def validate_take_profit(cls, v, info):
        """Validate take profit relative to entry price."""
        if v and info.data and "entry_price" in info.data and info.data["entry_price"]:
            entry = info.data["entry_price"]
            # Validate reasonable take profit (within 200% of entry)
            diff_pct = abs(float(v - entry) / float(entry))
            if diff_pct > 2.0:
                raise ValueError("Take profit too far from entry price (>200%)")
        return v


class PatternCollection(BaseModel):
    """Collection of patterns for a symbol/timeframe."""

    symbol: str = Field(..., description="Trading symbol")
    timeframe: Timeframe = Field(..., description="Analysis timeframe")
    timestamp: datetime = Field(..., description="Analysis timestamp")

    patterns: list[PatternHit] = Field(default_factory=list, description="Detected patterns")

    # Summary statistics
    total_patterns: int = Field(0, ge=0, description="Total number of patterns")
    avg_confidence: float = Field(0, ge=0, le=1, description="Average pattern confidence")
    strongest_pattern: Optional[str] = Field(None, description="ID of strongest pattern")

    def add_pattern(self, pattern: PatternHit) -> None:
        """Add a pattern to the collection."""
        self.patterns.append(pattern)
        self._update_stats()

    def _update_stats(self) -> None:
        """Update summary statistics."""
        self.total_patterns = len(self.patterns)
        if self.patterns:
            self.avg_confidence = sum(p.confidence for p in self.patterns) / len(self.patterns)
            strongest = max(self.patterns, key=lambda p: p.strength)
            self.strongest_pattern = strongest.pattern_id
        else:
            self.avg_confidence = 0.0
            self.strongest_pattern = None

    def get_patterns_by_type(self, pattern_type: PatternType) -> list[PatternHit]:
        """Get patterns of a specific type."""
        return [p for p in self.patterns if p.pattern_type == pattern_type]

    def get_high_confidence_patterns(self, min_confidence: float = 0.7) -> list[PatternHit]:
        """Get patterns above confidence threshold."""
        return [p for p in self.patterns if p.confidence >= min_confidence]
