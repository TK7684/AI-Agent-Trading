"""Market data models."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import Field, model_validator

from .base import BaseModel
from .enums import Timeframe


class MarketBar(BaseModel):
    """OHLCV market data bar."""

    symbol: str = Field(..., description="Trading symbol (e.g., 'BTCUSDT')")
    timeframe: Timeframe = Field(..., description="Timeframe of the bar")
    timestamp: datetime = Field(..., description="Bar timestamp (open time)")

    # Price data as Decimal for precision
    open: Decimal = Field(..., gt=0, description="Opening price")
    high: Decimal = Field(..., gt=0, description="Highest price")
    low: Decimal = Field(..., gt=0, description="Lowest price")
    close: Decimal = Field(..., gt=0, description="Closing price")

    # Volume data
    volume: Decimal = Field(..., ge=0, description="Trading volume")
    quote_volume: Optional[Decimal] = Field(None, ge=0, description="Quote asset volume")

    # Additional metadata
    trades_count: Optional[int] = Field(None, ge=0, description="Number of trades")
    taker_buy_volume: Optional[Decimal] = Field(None, ge=0, description="Taker buy volume")

    @model_validator(mode='after')
    def validate_ohlc_prices(self):
        """Validate OHLC price relationships."""
        prices = [self.open, self.high, self.low, self.close]

        if self.high != max(prices):
            raise ValueError("High must be the highest price")

        if self.low != min(prices):
            raise ValueError("Low must be the lowest price")

        return self


class IndicatorSnapshot(BaseModel):
    """Snapshot of technical indicators at a point in time."""

    symbol: str = Field(..., description="Trading symbol")
    timeframe: Timeframe = Field(..., description="Timeframe")
    timestamp: datetime = Field(..., description="Calculation timestamp")

    # Trend indicators
    rsi: Optional[float] = Field(None, ge=0, le=100, description="RSI (0-100)")
    ema_20: Optional[Decimal] = Field(None, gt=0, description="20-period EMA")
    ema_50: Optional[Decimal] = Field(None, gt=0, description="50-period EMA")
    ema_200: Optional[Decimal] = Field(None, gt=0, description="200-period EMA")

    # MACD
    macd_line: Optional[float] = Field(None, description="MACD line")
    macd_signal: Optional[float] = Field(None, description="MACD signal line")
    macd_histogram: Optional[float] = Field(None, description="MACD histogram")

    # Bollinger Bands
    bb_upper: Optional[Decimal] = Field(None, gt=0, description="Bollinger upper band")
    bb_middle: Optional[Decimal] = Field(None, gt=0, description="Bollinger middle band")
    bb_lower: Optional[Decimal] = Field(None, gt=0, description="Bollinger lower band")
    bb_width: Optional[float] = Field(None, ge=0, description="Bollinger band width")

    # Volatility
    atr: Optional[Decimal] = Field(None, ge=0, description="Average True Range")

    # Volume indicators
    volume_sma: Optional[Decimal] = Field(None, ge=0, description="Volume SMA")
    volume_profile: Optional[dict[str, float]] = Field(None, description="Volume profile data")

    # Momentum oscillators
    stoch_k: Optional[float] = Field(None, ge=0, le=100, description="Stochastic %K")
    stoch_d: Optional[float] = Field(None, ge=0, le=100, description="Stochastic %D")
    cci: Optional[float] = Field(None, description="Commodity Channel Index")
    mfi: Optional[float] = Field(None, ge=0, le=100, description="Money Flow Index")

    @model_validator(mode='after')
    def validate_bollinger_bands(self):
        """Validate Bollinger Bands ordering."""
        if self.bb_upper and self.bb_middle and self.bb_lower:
            if self.bb_upper <= self.bb_middle:
                raise ValueError("Upper band must be greater than middle band")
            if self.bb_lower >= self.bb_middle:
                raise ValueError("Lower band must be less than middle band")
        return self
