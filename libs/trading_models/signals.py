"""Trading signal models."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import Field, model_validator

from .base import BaseModel
from .enums import Direction, MarketRegime, Timeframe
from .market_data import IndicatorSnapshot
from .patterns import PatternHit


class TimeframeAnalysis(BaseModel):
    """Analysis results for a specific timeframe."""

    timeframe: Timeframe = Field(..., description="Analysis timeframe")
    timestamp: datetime = Field(..., description="Analysis timestamp")

    # Technical analysis scores
    trend_score: float = Field(..., ge=-10, le=10, description="Trend strength (-10 to 10)")
    momentum_score: float = Field(..., ge=-10, le=10, description="Momentum score (-10 to 10)")
    volatility_score: float = Field(..., ge=0, le=10, description="Volatility score (0-10)")
    volume_score: float = Field(..., ge=0, le=10, description="Volume score (0-10)")

    # Pattern analysis
    pattern_count: int = Field(0, ge=0, description="Number of patterns detected")
    strongest_pattern_confidence: float = Field(0, ge=0, le=1, description="Strongest pattern confidence")

    # Indicator summary
    bullish_indicators: int = Field(0, ge=0, description="Count of bullish indicators")
    bearish_indicators: int = Field(0, ge=0, description="Count of bearish indicators")
    neutral_indicators: int = Field(0, ge=0, description="Count of neutral indicators")

    # Weight for confluence calculation
    timeframe_weight: float = Field(..., gt=0, le=1, description="Weight in confluence calculation")


class LLMAnalysis(BaseModel):
    """LLM analysis results."""

    model_id: str = Field(..., description="LLM model identifier")
    timestamp: datetime = Field(..., description="Analysis timestamp")

    # Analysis results
    market_sentiment: str = Field(..., description="Market sentiment analysis")
    key_insights: list[str] = Field(default_factory=list, description="Key market insights")
    risk_factors: list[str] = Field(default_factory=list, description="Identified risk factors")

    # Scoring
    bullish_score: float = Field(..., ge=0, le=10, description="Bullish sentiment score (0-10)")
    bearish_score: float = Field(..., ge=0, le=10, description="Bearish sentiment score (0-10)")
    confidence: float = Field(..., ge=0, le=1, description="Analysis confidence (0-1)")

    # Performance metrics
    tokens_used: int = Field(..., gt=0, description="Tokens consumed")
    latency_ms: int = Field(..., gt=0, description="Response latency in milliseconds")
    cost_usd: float = Field(..., ge=0, description="Analysis cost in USD")


class Signal(BaseModel):
    """Trading signal with confluence analysis."""

    signal_id: str = Field(..., description="Unique signal identifier")
    symbol: str = Field(..., description="Trading symbol")
    timestamp: datetime = Field(..., description="Signal generation timestamp")

    # Signal direction and strength
    direction: Direction = Field(..., description="Signal direction (long/short)")
    confluence_score: float = Field(..., ge=0, le=100, description="Confluence score (0-100)")
    confidence: float = Field(..., ge=0, le=1, description="Signal confidence (0-1)")

    # Market context
    market_regime: MarketRegime = Field(..., description="Current market regime")
    primary_timeframe: Timeframe = Field(..., description="Primary analysis timeframe")

    # Analysis components
    timeframe_analysis: dict[Timeframe, TimeframeAnalysis] = Field(
        default_factory=dict,
        description="Analysis by timeframe"
    )
    patterns: list[PatternHit] = Field(default_factory=list, description="Supporting patterns")
    indicators: dict[Timeframe, IndicatorSnapshot] = Field(
        default_factory=dict,
        description="Indicator snapshots by timeframe"
    )
    llm_analysis: Optional[LLMAnalysis] = Field(None, description="LLM analysis results")

    # Price targets
    entry_price: Optional[Decimal] = Field(None, gt=0, description="Suggested entry price")
    stop_loss: Optional[Decimal] = Field(None, gt=0, description="Suggested stop loss")
    take_profit: Optional[Decimal] = Field(None, gt=0, description="Suggested take profit")

    # Risk metrics
    risk_reward_ratio: Optional[float] = Field(None, gt=0, description="Risk/reward ratio")
    max_risk_pct: Optional[float] = Field(None, gt=0, le=10, description="Maximum risk percentage")

    # Signal reasoning
    reasoning: str = Field(..., description="Human-readable signal reasoning")
    key_factors: list[str] = Field(default_factory=list, description="Key supporting factors")

    # Metadata
    expires_at: Optional[datetime] = Field(None, description="Signal expiration time")
    priority: int = Field(1, ge=1, le=5, description="Signal priority (1-5)")

    @model_validator(mode='after')
    def validate_signal_consistency(self):
        """Validate signal consistency."""
        # High confluence should have high confidence
        if self.confluence_score > 90 and self.confidence < 0.8:
            raise ValueError("High confluence score requires high confidence")

        # Validate risk/reward ratio calculation
        if (self.risk_reward_ratio and self.entry_price and
            self.stop_loss and self.take_profit):

            if self.direction == Direction.LONG:
                risk = float(self.entry_price - self.stop_loss)
                reward = float(self.take_profit - self.entry_price)
            else:  # SHORT
                risk = float(self.stop_loss - self.entry_price)
                reward = float(self.entry_price - self.take_profit)

            if risk > 0:
                calculated_rr = reward / risk
                if abs(calculated_rr - self.risk_reward_ratio) > 0.1:
                    raise ValueError("Risk/reward ratio doesn't match price levels")

        return self

    def add_timeframe_analysis(self, analysis: TimeframeAnalysis) -> None:
        """Add timeframe analysis to the signal."""
        self.timeframe_analysis[analysis.timeframe] = analysis

    def get_weighted_confluence(self) -> float:
        """Calculate weighted confluence score from timeframe analyses."""
        if not self.timeframe_analysis:
            return self.confluence_score

        total_weight = sum(ta.timeframe_weight for ta in self.timeframe_analysis.values())
        if total_weight == 0:
            return self.confluence_score

        weighted_sum = sum(
            (ta.trend_score + ta.momentum_score) * ta.timeframe_weight
            for ta in self.timeframe_analysis.values()
        )

        # Normalize to 0-100 scale
        normalized_score = max(0, min(100, (weighted_sum / total_weight + 10) * 5))
        return normalized_score


class TradingSignal(BaseModel):
    """Simplified trading signal for backtesting and testing."""

    symbol: str = Field(..., description="Trading symbol")
    direction: Direction = Field(..., description="Trade direction")
    confidence: float = Field(..., ge=0, le=1, description="Signal confidence")
    position_size: float = Field(..., gt=0, description="Position size")
    stop_loss: Optional[float] = Field(None, description="Stop loss price")
    take_profit: Optional[float] = Field(None, description="Take profit price")
    reasoning: str = Field(..., description="Signal reasoning")
    timeframe_analysis: dict[str, Any] = Field(default_factory=dict, description="Timeframe analysis")
