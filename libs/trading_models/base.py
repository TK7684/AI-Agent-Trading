"""Base model with common functionality and optimizations."""

from datetime import datetime
from typing import Any, Optional, TypeVar

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict, Field, computed_field

T = TypeVar('T', bound='BaseModel')


class BaseModel(PydanticBaseModel):
    """Base model with common configuration and optimized methods."""

    model_config = ConfigDict(
        # Enable validation on assignment
        validate_assignment=True,
        # Use enum values instead of names in serialization
        use_enum_values=True,
        # Validate default values
        validate_default=True,
        # Extra fields are forbidden
        extra="forbid",
        # Enable frozen models for immutability
        frozen=False,
        # Use arbitrary types for better performance
        arbitrary_types_allowed=True,
        # Enable computed fields
        computed_fields=True,
    )

    # Cache for computed fields
    _computed_cache: Optional[dict[str, Any]] = None

    def __init__(self, **data):
        super().__init__(**data)
        self._computed_cache = {}

    def to_dict(self, exclude_none: bool = True, exclude_defaults: bool = False) -> dict[str, Any]:
        """Convert model to dictionary with optimization options."""
        return self.model_dump(
            exclude_none=exclude_none,
            exclude_defaults=exclude_defaults,
            exclude_unset=True
        )

    def to_json(self, exclude_none: bool = True, exclude_defaults: bool = False) -> str:
        """Convert model to JSON string with optimization options."""
        return self.model_dump_json(
            exclude_none=exclude_none,
            exclude_defaults=exclude_defaults,
            exclude_unset=True
        )

    @classmethod
    def from_dict(cls: type[T], data: dict[str, Any]) -> T:
        """Create model from dictionary with validation."""
        return cls.model_validate(data)

    @classmethod
    def from_json(cls: type[T], json_str: str) -> T:
        """Create model from JSON string with validation."""
        return cls.model_validate_json(json_str)

    def __str__(self) -> str:
        """String representation with caching."""
        if not hasattr(self, '_str_cache'):
            self._str_cache = f"{self.__class__.__name__}({self.to_json()})"
        return self._str_cache

    def __repr__(self) -> str:
        """Detailed representation."""
        return self.__str__()

    def copy(self, **kwargs) -> 'BaseModel':
        """Create a copy with optional updates."""
        return self.model_copy(update=kwargs)

    def dict(self, **kwargs) -> dict[str, Any]:
        """Alias for to_dict for backward compatibility."""
        return self.to_dict(**kwargs)

    def json(self, **kwargs) -> str:
        """Alias for to_json for backward compatibility."""
        return self.to_json(**kwargs)

    def clear_cache(self) -> None:
        """Clear internal caches."""
        self._computed_cache = {}
        if hasattr(self, '_str_cache'):
            delattr(self, '_str_cache')


# Trading-specific models for E2E integration with optimizations

class MarketData(BaseModel):
    """Market data container with memory optimizations."""
    symbol: str
    timeframe: str
    data: list[dict[str, Any]]
    timestamp: datetime = Field(default_factory=datetime.now)

    @computed_field
    @property
    def data_length(self) -> int:
        """Get data length efficiently."""
        return len(self.data)

    @computed_field
    @property
    def is_empty(self) -> bool:
        """Check if data is empty efficiently."""
        return len(self.data) == 0


class TradingSignal(BaseModel):
    """Trading signal for E2E integration with validation."""
    symbol: str
    direction: str = Field(..., pattern=r"^(LONG|SHORT)$")  # "LONG" or "SHORT"
    confidence: float = Field(ge=0, le=1)
    confluence_score: float = Field(ge=0, le=100)
    reasoning: str
    timeframe_analysis: dict[str, Any] = Field(default_factory=dict)

    @computed_field
    @property
    def is_high_confidence(self) -> bool:
        """Check if signal has high confidence."""
        return self.confidence >= 0.8

    @computed_field
    @property
    def is_strong_confluence(self) -> bool:
        """Check if signal has strong confluence."""
        return self.confluence_score >= 80


class Position(BaseModel):
    """Trading position with computed fields."""
    symbol: str
    side: str = Field(..., pattern=r"^(LONG|SHORT)$")  # "LONG" or "SHORT"
    size: float = Field(gt=0)
    entry_price: float = Field(gt=0)
    current_price: float = Field(gt=0)
    unrealized_pnl: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)

    @computed_field
    @property
    def market_value(self) -> float:
        """Calculate current market value."""
        return self.size * self.current_price

    @computed_field
    @property
    def pnl_percentage(self) -> float:
        """Calculate PnL percentage."""
        if self.side == "LONG":
            return ((self.current_price - self.entry_price) / self.entry_price) * 100
        else:
            return ((self.entry_price - self.current_price) / self.entry_price) * 100


class Portfolio(BaseModel):
    """Portfolio state with computed metrics."""
    total_equity: float = Field(ge=0)
    available_margin: float = Field(ge=0)
    positions: list[Position] = Field(default_factory=list)
    daily_pnl: float = 0.0
    unrealized_pnl: float = 0.0

    @computed_field
    @property
    def total_positions(self) -> int:
        """Get total number of positions."""
        return len(self.positions)

    @computed_field
    @property
    def total_market_value(self) -> float:
        """Calculate total market value of all positions."""
        return sum(pos.market_value for pos in self.positions)

    @computed_field
    @property
    def margin_utilization(self) -> float:
        """Calculate margin utilization percentage."""
        if self.total_equity == 0:
            return 0.0
        return (self.total_market_value / self.total_equity) * 100


class Trade(BaseModel):
    """Completed trade with validation."""
    id: str
    symbol: str
    side: str = Field(..., pattern=r"^(LONG|SHORT)$")  # "LONG" or "SHORT"
    size: float = Field(gt=0)
    entry_price: float = Field(gt=0)
    exit_price: Optional[float] = Field(None, gt=0)
    pnl: Optional[float] = None
    status: str = Field(default="OPEN", pattern=r"^(OPEN|CLOSED|CANCELLED)$")
    created_at: datetime = Field(default_factory=datetime.now)
    closed_at: Optional[datetime] = None

    @computed_field
    @property
    def is_closed(self) -> bool:
        """Check if trade is closed."""
        return self.status == "CLOSED"

    @computed_field
    @property
    def duration(self) -> Optional[float]:
        """Calculate trade duration in seconds if closed."""
        if self.closed_at and self.created_at:
            return (self.closed_at - self.created_at).total_seconds()
        return None
