"""
Technical Indicator Calculation Engine

This module provides implementations for all major technical indicators
used in the autonomous trading system.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

import numpy as np

from .market_data import MarketBar

logger = logging.getLogger(__name__)


@dataclass
class IndicatorResult:
    """Base class for indicator results"""
    timestamp: datetime
    value: float

    def __post_init__(self):
        if not isinstance(self.value, (int, float)) or np.isnan(self.value):
            raise ValueError(f"Invalid indicator value: {self.value}")


@dataclass
class RSIResult(IndicatorResult):
    """RSI indicator result"""
    pass


@dataclass
class EMAResult(IndicatorResult):
    """EMA indicator result"""
    period: int = 0


@dataclass
class MACDResult(IndicatorResult):
    """MACD indicator result"""
    signal: float = 0.0
    histogram: float = 0.0


@dataclass
class BollingerBandsResult(IndicatorResult):
    """Bollinger Bands result"""
    upper: float = 0.0
    middle: float = 0.0  # This is the value field
    lower: float = 0.0

    def __post_init__(self):
        super().__post_init__()
        self.middle = self.value  # Ensure consistency


@dataclass
class ATRResult(IndicatorResult):
    """ATR indicator result"""
    pass


@dataclass
class StochasticResult(IndicatorResult):
    """Stochastic oscillator result"""
    k_percent: float = 0.0  # This is the value field
    d_percent: float = 0.0

    def __post_init__(self):
        super().__post_init__()
        self.k_percent = self.value  # Ensure consistency


@dataclass
class CCIResult(IndicatorResult):
    """CCI indicator result"""
    pass


@dataclass
class MFIResult(IndicatorResult):
    """MFI indicator result"""
    pass


@dataclass
class VolumeProfileResult:
    """Volume Profile result"""
    timestamp: datetime
    price_levels: list[float]
    volumes: list[float]
    poc: float  # Point of Control
    value_area_high: float
    value_area_low: float


class TechnicalIndicators:
    """Technical indicator calculation engine"""

    @staticmethod
    def rsi(data: list[MarketBar], period: int = 14) -> list[RSIResult]:
        """Calculate RSI (Relative Strength Index)"""
        if len(data) < period + 1:
            return []

        closes = np.array([float(bar.close) for bar in data])
        deltas = np.diff(closes)

        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        # Calculate initial averages
        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])

        results = []

        for i in range(period, len(data)):
            if i == period:
                # First RSI calculation
                if avg_loss == 0:
                    rsi_value = 100.0 if avg_gain > 0 else 50.0
                else:
                    rs = avg_gain / avg_loss
                    rsi_value = 100 - (100 / (1 + rs))
            else:
                # Smoothed averages (Wilder's smoothing)
                avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
                avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period

                if avg_loss == 0:
                    rsi_value = 100.0 if avg_gain > 0 else 50.0
                else:
                    rs = avg_gain / avg_loss
                    rsi_value = 100 - (100 / (1 + rs))
            results.append(RSIResult(
                timestamp=data[i].timestamp,
                value=rsi_value
            ))

        return results

    @staticmethod
    def ema(data: list[MarketBar], period: int) -> list[EMAResult]:
        """Calculate EMA (Exponential Moving Average)"""
        if len(data) < period:
            return []

        closes = np.array([float(bar.close) for bar in data])
        alpha = 2.0 / (period + 1)

        # Initialize with SMA
        ema_value = np.mean(closes[:period])
        results = [EMAResult(
            timestamp=data[period - 1].timestamp,
            value=ema_value,
            period=period
        )]

        # Calculate EMA for remaining data
        for i in range(period, len(data)):
            ema_value = alpha * closes[i] + (1 - alpha) * ema_value
            results.append(EMAResult(
                timestamp=data[i].timestamp,
                value=ema_value,
                period=period
            ))

        return results

    @staticmethod
    def macd(data: list[MarketBar], fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> list[MACDResult]:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        if len(data) < slow_period + signal_period:
            return []

        # Calculate EMAs
        fast_ema = TechnicalIndicators.ema(data, fast_period)
        slow_ema = TechnicalIndicators.ema(data, slow_period)

        # Align EMAs (slow EMA starts later)
        start_idx = slow_period - fast_period
        fast_ema_aligned = fast_ema[start_idx:]

        # Calculate MACD line
        macd_line = []
        for i in range(len(slow_ema)):
            macd_value = fast_ema_aligned[i].value - slow_ema[i].value
            macd_line.append((slow_ema[i].timestamp, macd_value))

        # Calculate signal line (EMA of MACD line)
        if len(macd_line) < signal_period:
            return []

        macd_values = np.array([val for _, val in macd_line])
        alpha = 2.0 / (signal_period + 1)
        signal_value = np.mean(macd_values[:signal_period])

        results = []

        for i in range(signal_period - 1, len(macd_line)):
            if i == signal_period - 1:
                # First signal calculation
                pass
            else:
                signal_value = alpha * macd_values[i] + (1 - alpha) * signal_value

            histogram = macd_values[i] - signal_value

            results.append(MACDResult(
                timestamp=macd_line[i][0],
                value=macd_values[i],
                signal=signal_value,
                histogram=histogram
            ))

        return results

    @staticmethod
    def bollinger_bands(data: list[MarketBar], period: int = 20, std_dev: float = 2.0) -> list[BollingerBandsResult]:
        """Calculate Bollinger Bands"""
        if len(data) < period:
            return []

        closes = np.array([float(bar.close) for bar in data])
        results = []

        for i in range(period - 1, len(data)):
            window = closes[i - period + 1:i + 1]
            middle = np.mean(window)
            std = np.std(window, ddof=0)

            upper = middle + (std_dev * std)
            lower = middle - (std_dev * std)

            results.append(BollingerBandsResult(
                timestamp=data[i].timestamp,
                value=middle,
                upper=upper,
                lower=lower
            ))

        return results

    @staticmethod
    def atr(data: list[MarketBar], period: int = 14) -> list[ATRResult]:
        """Calculate ATR (Average True Range)"""
        if len(data) < period + 1:
            return []

        true_ranges = []

        for i in range(1, len(data)):
            high_low = float(data[i].high - data[i].low)
            high_close_prev = abs(float(data[i].high - data[i - 1].close))
            low_close_prev = abs(float(data[i].low - data[i - 1].close))

            true_range = max(high_low, high_close_prev, low_close_prev)
            true_ranges.append(true_range)

        # Calculate ATR using Wilder's smoothing
        atr_value = np.mean(true_ranges[:period])
        results = [ATRResult(
            timestamp=data[period].timestamp,
            value=atr_value
        )]

        for i in range(period, len(true_ranges)):
            atr_value = (atr_value * (period - 1) + true_ranges[i]) / period
            results.append(ATRResult(
                timestamp=data[i + 1].timestamp,
                value=atr_value
            ))

        return results

    @staticmethod
    def stochastic(data: list[MarketBar], k_period: int = 14, d_period: int = 3) -> list[StochasticResult]:
        """Calculate Stochastic Oscillator"""
        if len(data) < k_period + d_period - 1:
            return []

        k_values = []

        # Calculate %K
        for i in range(k_period - 1, len(data)):
            window = data[i - k_period + 1:i + 1]
            highest_high = max(float(bar.high) for bar in window)
            lowest_low = min(float(bar.low) for bar in window)

            if highest_high == lowest_low:
                k_percent = 50.0  # Avoid division by zero
            else:
                k_percent = ((float(data[i].close) - lowest_low) / (highest_high - lowest_low)) * 100

            k_values.append((data[i].timestamp, k_percent))

        # Calculate %D (SMA of %K)
        results = []
        for i in range(d_period - 1, len(k_values)):
            d_window = k_values[i - d_period + 1:i + 1]
            d_percent = np.mean([val for _, val in d_window])

            results.append(StochasticResult(
                timestamp=k_values[i][0],
                value=k_values[i][1],
                d_percent=d_percent
            ))

        return results

    @staticmethod
    def cci(data: list[MarketBar], period: int = 20) -> list[CCIResult]:
        """Calculate CCI (Commodity Channel Index)"""
        if len(data) < period:
            return []

        results = []

        for i in range(period - 1, len(data)):
            window = data[i - period + 1:i + 1]

            # Calculate typical prices
            typical_prices = [float(bar.high + bar.low + bar.close) / 3 for bar in window]
            sma_tp = np.mean(typical_prices)

            # Calculate mean deviation
            mean_deviation = np.mean([abs(tp - sma_tp) for tp in typical_prices])

            if mean_deviation == 0:
                cci_value = 0.0
            else:
                current_tp = float(data[i].high + data[i].low + data[i].close) / 3
                cci_value = (current_tp - sma_tp) / (0.015 * mean_deviation)

            results.append(CCIResult(
                timestamp=data[i].timestamp,
                value=cci_value
            ))

        return results

    @staticmethod
    def mfi(data: list[MarketBar], period: int = 14) -> list[MFIResult]:
        """Calculate MFI (Money Flow Index)"""
        if len(data) < period + 1:
            return []

        results = []

        for i in range(period, len(data)):
            window = data[i - period:i + 1]

            positive_flow = 0.0
            negative_flow = 0.0

            for j in range(1, len(window)):
                typical_price = float(window[j].high + window[j].low + window[j].close) / 3
                prev_typical_price = float(window[j-1].high + window[j-1].low + window[j-1].close) / 3
                money_flow = typical_price * float(window[j].volume)

                if typical_price > prev_typical_price:
                    positive_flow += money_flow
                elif typical_price < prev_typical_price:
                    negative_flow += money_flow

            if negative_flow == 0:
                mfi_value = 100.0
            else:
                money_ratio = positive_flow / negative_flow
                mfi_value = 100 - (100 / (1 + money_ratio))

            results.append(MFIResult(
                timestamp=data[i].timestamp,
                value=mfi_value
            ))

        return results

    @staticmethod
    def volume_profile(data: list[MarketBar], num_levels: int = 50) -> Optional[VolumeProfileResult]:
        """Calculate Volume Profile"""
        if len(data) < 10:  # Need minimum data
            return None

        # Find price range
        all_highs = [float(bar.high) for bar in data]
        all_lows = [float(bar.low) for bar in data]
        price_min = min(all_lows)
        price_max = max(all_highs)

        if price_max == price_min:
            return None

        # Create price levels
        price_step = (price_max - price_min) / num_levels
        price_levels = [price_min + i * price_step for i in range(num_levels + 1)]
        volume_at_price = [0.0] * num_levels

        # Distribute volume across price levels
        for bar in data:
            # Simple distribution: assume uniform volume distribution within bar range
            bar_range = float(bar.high - bar.low)
            if bar_range == 0:
                # Single price point
                level_idx = min(int((float(bar.close) - price_min) / price_step), num_levels - 1)
                volume_at_price[level_idx] += float(bar.volume)
            else:
                # Distribute volume proportionally across price levels within bar range
                start_level = max(0, int((float(bar.low) - price_min) / price_step))
                end_level = min(num_levels - 1, int((float(bar.high) - price_min) / price_step))

                levels_in_range = end_level - start_level + 1
                volume_per_level = float(bar.volume) / levels_in_range

                for level_idx in range(start_level, end_level + 1):
                    volume_at_price[level_idx] += volume_per_level

        # Find Point of Control (POC) - price level with highest volume
        poc_idx = np.argmax(volume_at_price)
        poc = price_levels[poc_idx]

        # Calculate Value Area (70% of total volume)
        total_volume = sum(volume_at_price)
        target_volume = total_volume * 0.7

        # Expand from POC to find value area
        value_area_volume = volume_at_price[poc_idx]
        va_low_idx = poc_idx
        va_high_idx = poc_idx

        while value_area_volume < target_volume and (va_low_idx > 0 or va_high_idx < num_levels - 1):
            # Choose direction with higher volume
            low_volume = volume_at_price[va_low_idx - 1] if va_low_idx > 0 else 0
            high_volume = volume_at_price[va_high_idx + 1] if va_high_idx < num_levels - 1 else 0

            if low_volume >= high_volume and va_low_idx > 0:
                va_low_idx -= 1
                value_area_volume += volume_at_price[va_low_idx]
            elif va_high_idx < num_levels - 1:
                va_high_idx += 1
                value_area_volume += volume_at_price[va_high_idx]
            else:
                break

        return VolumeProfileResult(
            timestamp=data[-1].timestamp,
            price_levels=price_levels[:-1],  # Remove last level (upper bound)
            volumes=volume_at_price,
            poc=poc,
            value_area_high=price_levels[va_high_idx],
            value_area_low=price_levels[va_low_idx]
        )


class IndicatorEngine:
    """Main engine for calculating all technical indicators"""

    def __init__(self):
        self.indicators = TechnicalIndicators()

    def calculate_all_indicators(self, data: list[MarketBar]) -> dict[str, Any]:
        """Calculate all indicators for given OHLCV data"""
        if len(data) < 50:  # Need sufficient data for all indicators
            logger.warning(f"Insufficient data for indicators: {len(data)} bars")
            return {}

        try:
            results = {
                'rsi': self.indicators.rsi(data, 14),
                'ema_20': self.indicators.ema(data, 20),
                'ema_50': self.indicators.ema(data, 50),
                'ema_200': self.indicators.ema(data, 200),
                'macd': self.indicators.macd(data),
                'bollinger_bands': self.indicators.bollinger_bands(data),
                'atr': self.indicators.atr(data),
                'stochastic': self.indicators.stochastic(data),
                'cci': self.indicators.cci(data),
                'mfi': self.indicators.mfi(data),
                'volume_profile': self.indicators.volume_profile(data)
            }

            # Log calculation success
            indicator_counts = {k: len(v) if isinstance(v, list) else (1 if v else 0)
                              for k, v in results.items()}
            logger.info(f"Calculated indicators: {indicator_counts}")

            return results

        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            return {}

    def get_latest_values(self, indicator_results: dict[str, Any]) -> dict[str, float]:
        """Extract latest values from all indicators"""
        latest = {}

        for name, results in indicator_results.items():
            if isinstance(results, list) and results:
                latest[name] = results[-1].value
            elif results and hasattr(results, 'value'):
                latest[name] = results.value

        return latest
