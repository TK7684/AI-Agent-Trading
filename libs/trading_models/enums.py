"""TypeScript-style enums and literals for trading system."""

from enum import Enum
from typing import Literal


class Timeframe(str, Enum):
    """Trading timeframes."""
    M15 = "15m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"


class TradingAction(str, Enum):
    """Trading actions."""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"


class Direction(str, Enum):
    """Trade direction."""
    LONG = "long"
    SHORT = "short"


class OrderType(str, Enum):
    """Order types."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(str, Enum):
    """Order status."""
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class PatternType(str, Enum):
    """Pattern types."""
    SUPPORT_RESISTANCE = "support_resistance"
    BREAKOUT = "breakout"
    TREND_REVERSAL = "trend_reversal"
    PIN_BAR = "pin_bar"
    ENGULFING = "engulfing"
    DOJI = "doji"
    DIVERGENCE = "divergence"


class MarketRegime(str, Enum):
    """Market regime types."""
    BULL = "bull"
    BEAR = "bear"
    SIDEWAYS = "sideways"


# TypeScript-style literals
TimeframeLiteral = Literal["15m", "1h", "4h", "1d"]
TradingActionLiteral = Literal["buy", "sell", "hold", "close_long", "close_short"]
DirectionLiteral = Literal["long", "short"]
OrderTypeLiteral = Literal["market", "limit", "stop", "stop_limit"]
OrderStatusLiteral = Literal["pending", "open", "filled", "partially_filled", "cancelled", "rejected", "expired"]
