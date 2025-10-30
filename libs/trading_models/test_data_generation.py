"""
Test data generation for various market scenarios and edge cases.
"""

import math
import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

import numpy as np
import pandas as pd

from .enums import Direction
from .market_data import MarketBar
from .orders import TradeOutcome
from .signals import TradingSignal


class MarketRegime(Enum):
    """Market regime types for test data generation."""
    BULL_MARKET = "bull"
    BEAR_MARKET = "bear"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_vol"
    LOW_VOLATILITY = "low_vol"
    TRENDING = "trending"
    RANGING = "ranging"

@dataclass
class MarketScenarioConfig:
    """Configuration for market scenario generation."""
    regime: MarketRegime
    duration_days: int
    initial_price: float
    volatility: float
    trend_strength: float
    noise_level: float
    volume_base: float
    volume_volatility: float

class MarketDataGenerator:
    """Generates realistic market data for testing."""

    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)
        self.logger = None

    def generate_market_scenario(
        self,
        config: MarketScenarioConfig,
        symbol: str = "BTCUSD",
        timeframe: str = "1h"
    ) -> list[MarketBar]:
        """Generate market data for a specific scenario."""

        bars = []
        current_price = Decimal(str(config.initial_price))
        current_time = datetime.now(UTC) - timedelta(days=config.duration_days)

        # Calculate time delta based on timeframe
        time_delta = self._get_time_delta(timeframe)
        total_bars = int(config.duration_days * 24 * 60 / self._get_minutes(timeframe))

        for i in range(total_bars):
            # Generate price movement based on regime
            price_change = self._generate_price_change(config, i, total_bars)

            # Calculate OHLC
            open_price = current_price
            close_price = current_price + Decimal(str(price_change))

            # Generate high/low with realistic spread
            spread = abs(float(price_change)) + (float(current_price) * config.volatility * random.uniform(0.001, 0.01))
            high_price = max(float(open_price), float(close_price)) + spread * random.uniform(0, 1)
            low_price = min(float(open_price), float(close_price)) - spread * random.uniform(0, 1)

            # Generate volume
            volume = self._generate_volume(config, abs(price_change), current_price)

            from .enums import Timeframe

            bar = MarketBar(
                symbol=symbol,
                timeframe=Timeframe.H1,  # Default to 1h
                timestamp=current_time,
                open=Decimal(str(round(float(open_price), 2))),
                high=Decimal(str(round(high_price, 2))),
                low=Decimal(str(round(low_price, 2))),
                close=Decimal(str(round(float(close_price), 2))),
                volume=Decimal(str(round(volume, 2)))
            )

            bars.append(bar)
            current_price = close_price
            current_time += time_delta

        return bars

    def _generate_price_change(
        self,
        config: MarketScenarioConfig,
        current_bar: int,
        total_bars: int
    ) -> float:
        """Generate price change based on market regime."""

        base_change = 0.0

        if config.regime == MarketRegime.BULL_MARKET:
            # Upward trend with occasional pullbacks
            trend_component = config.trend_strength * 0.001
            pullback_probability = 0.2
            if random.random() < pullback_probability:
                base_change = -trend_component * random.uniform(0.5, 2.0)
            else:
                base_change = trend_component * random.uniform(0.5, 3.0)

        elif config.regime == MarketRegime.BEAR_MARKET:
            # Downward trend with occasional rallies
            trend_component = -config.trend_strength * 0.001
            rally_probability = 0.15
            if random.random() < rally_probability:
                base_change = -trend_component * random.uniform(0.5, 2.0)
            else:
                base_change = trend_component * random.uniform(0.5, 3.0)

        elif config.regime == MarketRegime.SIDEWAYS:
            # Mean-reverting behavior
            progress = current_bar / total_bars
            cycle_position = math.sin(progress * 4 * math.pi)  # 4 cycles
            base_change = cycle_position * config.trend_strength * 0.0005

        elif config.regime == MarketRegime.HIGH_VOLATILITY:
            # Large random movements
            base_change = random.gauss(0, config.volatility * 0.01)

        elif config.regime == MarketRegime.LOW_VOLATILITY:
            # Small random movements
            base_change = random.gauss(0, config.volatility * 0.001)

        elif config.regime == MarketRegime.TRENDING:
            # Strong directional movement
            direction = 1 if config.trend_strength > 0 else -1
            base_change = direction * abs(config.trend_strength) * 0.002 * random.uniform(0.5, 1.5)

        elif config.regime == MarketRegime.RANGING:
            # Bounded movement between levels
            progress = current_bar / total_bars
            range_position = math.sin(progress * 2 * math.pi)
            base_change = range_position * config.trend_strength * 0.001

        # Add noise
        noise = random.gauss(0, config.noise_level * 0.001)

        return base_change + noise

    def _generate_volume(
        self,
        config: MarketScenarioConfig,
        price_change_magnitude: float,
        current_price: float
    ) -> float:
        """Generate realistic volume based on price movement."""

        # Base volume
        base_volume = config.volume_base

        # Volume increases with price movement
        volume_multiplier = 1 + (price_change_magnitude / float(current_price)) * 10

        # Add random variation
        volume_noise = random.uniform(1 - config.volume_volatility, 1 + config.volume_volatility)

        return base_volume * volume_multiplier * volume_noise

    def _get_time_delta(self, timeframe: str) -> timedelta:
        """Get time delta for timeframe."""
        timeframe_map = {
            "1m": timedelta(minutes=1),
            "5m": timedelta(minutes=5),
            "15m": timedelta(minutes=15),
            "1h": timedelta(hours=1),
            "4h": timedelta(hours=4),
            "1d": timedelta(days=1)
        }
        return timeframe_map.get(timeframe, timedelta(hours=1))

    def _get_minutes(self, timeframe: str) -> int:
        """Get minutes for timeframe."""
        timeframe_map = {
            "1m": 1,
            "5m": 5,
            "15m": 15,
            "1h": 60,
            "4h": 240,
            "1d": 1440
        }
        return timeframe_map.get(timeframe, 60)

    def generate_multi_regime_data(
        self,
        regimes: list[tuple[MarketRegime, int]],  # (regime, duration_days)
        initial_price: float = 100.0,
        symbol: str = "BTCUSD",
        timeframe: str = "1h"
    ) -> list[MarketBar]:
        """Generate data with multiple market regimes."""

        all_bars = []
        current_price = initial_price

        for regime, duration in regimes:
            # Configure scenario based on regime
            if regime == MarketRegime.BULL_MARKET:
                config = MarketScenarioConfig(
                    regime=regime,
                    duration_days=duration,
                    initial_price=current_price,
                    volatility=0.15,
                    trend_strength=2.0,
                    noise_level=0.5,
                    volume_base=1000.0,
                    volume_volatility=0.3
                )
            elif regime == MarketRegime.BEAR_MARKET:
                config = MarketScenarioConfig(
                    regime=regime,
                    duration_days=duration,
                    initial_price=current_price,
                    volatility=0.20,
                    trend_strength=-2.0,
                    noise_level=0.6,
                    volume_base=1200.0,
                    volume_volatility=0.4
                )
            elif regime == MarketRegime.SIDEWAYS:
                config = MarketScenarioConfig(
                    regime=regime,
                    duration_days=duration,
                    initial_price=current_price,
                    volatility=0.10,
                    trend_strength=0.5,
                    noise_level=0.3,
                    volume_base=800.0,
                    volume_volatility=0.2
                )
            else:
                config = MarketScenarioConfig(
                    regime=regime,
                    duration_days=duration,
                    initial_price=current_price,
                    volatility=0.25,
                    trend_strength=1.0,
                    noise_level=0.4,
                    volume_base=1000.0,
                    volume_volatility=0.3
                )

            regime_bars = self.generate_market_scenario(config, symbol, timeframe)
            all_bars.extend(regime_bars)

            # Update current price for next regime
            if regime_bars:
                current_price = regime_bars[-1].close

        return all_bars

    def generate_edge_case_scenarios(self) -> dict[str, list[MarketBar]]:
        """Generate edge case scenarios for testing."""

        scenarios = {}

        # Flash crash scenario
        scenarios['flash_crash'] = self._generate_flash_crash()

        # Gap up/down scenarios
        scenarios['gap_up'] = self._generate_gap_scenario(gap_percentage=0.05)
        scenarios['gap_down'] = self._generate_gap_scenario(gap_percentage=-0.05)

        # Low liquidity scenario
        scenarios['low_liquidity'] = self._generate_low_liquidity_scenario()

        # High frequency scenario
        scenarios['high_frequency'] = self._generate_high_frequency_scenario()

        # Consolidation breakout
        scenarios['consolidation_breakout'] = self._generate_consolidation_breakout()

        return scenarios

    def _generate_flash_crash(self) -> list[MarketBar]:
        """Generate flash crash scenario."""
        bars = []
        base_price = 100.0
        start_time = datetime.now(UTC) - timedelta(hours=24)

        # Normal trading for first 20 bars
        for i in range(20):
            price_change = random.gauss(0, 0.001) * base_price
            bars.append(MarketBar(
                symbol="BTCUSD",
                timeframe="15m",
                timestamp=start_time + timedelta(minutes=i*15),
                open=base_price,
                high=base_price + abs(price_change),
                low=base_price - abs(price_change),
                close=base_price + price_change,
                volume=1000.0
            ))
            base_price += price_change

        # Flash crash - 10% drop in 5 periods
        crash_start_price = base_price
        for i in range(5):
            crash_progress = (i + 1) / 5
            price_drop = crash_start_price * 0.10 * crash_progress
            current_price = crash_start_price - price_drop

            bars.append(MarketBar(
                symbol="BTCUSD",
                timeframe="15m",
                timestamp=start_time + timedelta(minutes=(20 + i)*15),
                open=base_price,
                high=base_price,
                low=current_price,
                close=current_price,
                volume=10000.0  # High volume during crash
            ))
            base_price = current_price

        # Recovery
        recovery_target = crash_start_price * 0.97  # Partial recovery
        for i in range(10):
            recovery_progress = (i + 1) / 10
            current_price = base_price + (recovery_target - base_price) * recovery_progress

            bars.append(MarketBar(
                symbol="BTCUSD",
                timeframe="15m",
                timestamp=start_time + timedelta(minutes=(25 + i)*15),
                open=base_price,
                high=max(base_price, current_price),
                low=min(base_price, current_price),
                close=current_price,
                volume=5000.0
            ))
            base_price = current_price

        return bars

    def _generate_gap_scenario(self, gap_percentage: float) -> list[MarketBar]:
        """Generate gap up/down scenario."""
        bars = []
        base_price = 100.0
        start_time = datetime.now(UTC) - timedelta(hours=12)

        # Normal trading before gap
        for i in range(10):
            price_change = random.gauss(0, 0.001) * base_price
            bars.append(MarketBar(
                symbol="BTCUSD",
                timeframe="1h",
                timestamp=start_time + timedelta(hours=i),
                open=base_price,
                high=base_price + abs(price_change),
                low=base_price - abs(price_change),
                close=base_price + price_change,
                volume=1000.0
            ))
            base_price += price_change

        # Gap
        gap_price = base_price * (1 + gap_percentage)
        bars.append(MarketBar(
            symbol="BTCUSD",
            timeframe="1h",
            timestamp=start_time + timedelta(hours=10),
            open=gap_price,
            high=gap_price + abs(gap_price * 0.01),
            low=gap_price - abs(gap_price * 0.01),
            close=gap_price + random.gauss(0, 0.005) * gap_price,
            volume=2000.0
        ))

        return bars

    def _generate_low_liquidity_scenario(self) -> list[MarketBar]:
        """Generate low liquidity scenario with wide spreads."""
        bars = []
        base_price = 100.0
        start_time = datetime.now(UTC) - timedelta(hours=6)

        for i in range(24):  # 15-minute bars
            # Low volume, wide spreads
            volume = random.uniform(10, 100)  # Very low volume
            spread = base_price * random.uniform(0.005, 0.02)  # Wide spread

            price_change = random.gauss(0, 0.002) * base_price
            open_price = base_price
            close_price = base_price + price_change
            high_price = max(open_price, close_price) + spread
            low_price = min(open_price, close_price) - spread

            bars.append(MarketBar(
                symbol="BTCUSD",
                timeframe="15m",
                timestamp=start_time + timedelta(minutes=i * 15),
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=volume
            ))
            base_price = close_price

        return bars

    def _generate_high_frequency_scenario(self) -> list[MarketBar]:
        """Generate high frequency trading scenario."""
        bars = []
        base_price = 100.0
        start_time = datetime.now(UTC) - timedelta(hours=1)

        for i in range(16):  # 15-minute bars for 4 hours
            # High volume, small price movements
            volume = random.uniform(5000, 20000)
            price_change = random.gauss(0, 0.0005) * base_price  # Very small movements

            close_price = base_price + price_change
            high_price = max(base_price, close_price) + abs(price_change) * 0.5
            low_price = min(base_price, close_price) - abs(price_change) * 0.5

            bars.append(MarketBar(
                symbol="BTCUSD",
                timeframe="15m",
                timestamp=start_time + timedelta(minutes=i*15),
                open=base_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=volume
            ))
            base_price += price_change

        return bars

    def _generate_consolidation_breakout(self) -> list[MarketBar]:
        """Generate consolidation followed by breakout."""
        bars = []
        base_price = 100.0
        start_time = datetime.now(UTC) - timedelta(days=2)

        # Consolidation phase (tight range)
        consolidation_range = base_price * 0.02  # 2% range
        for i in range(40):
            # Price oscillates within range
            range_position = math.sin(i * 0.3) * 0.5 + 0.5  # 0 to 1
            target_price = base_price - consolidation_range/2 + consolidation_range * range_position

            high_price = max(base_price, target_price) + base_price * 0.001
            low_price = min(base_price, target_price) - base_price * 0.001

            bars.append(MarketBar(
                symbol="BTCUSD",
                timeframe="1h",
                timestamp=start_time + timedelta(hours=i),
                open=base_price,
                high=high_price,
                low=low_price,
                close=target_price,
                volume=800.0
            ))
            base_price = target_price

        # Breakout phase
        breakout_target = base_price * 1.05  # 5% breakout
        for i in range(8):
            breakout_progress = (i + 1) / 8
            current_price = base_price + (breakout_target - base_price) * breakout_progress

            high_price = max(base_price, current_price)
            low_price = min(base_price, current_price)

            bars.append(MarketBar(
                symbol="BTCUSD",
                timeframe="1h",
                timestamp=start_time + timedelta(hours=40 + i),
                open=base_price,
                high=high_price,
                low=low_price,
                close=current_price,
                volume=3000.0  # High volume on breakout
            ))
            base_price = current_price

        return bars

class SignalDataGenerator:
    """Generates trading signals for testing."""

    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)

    def generate_signal_sequence(
        self,
        count: int,
        symbols: list[str] = None,
        confidence_range: tuple[float, float] = (0.3, 0.9)
    ) -> list[TradingSignal]:
        """Generate sequence of trading signals."""

        if symbols is None:
            symbols = ["BTCUSD", "ETHUSD", "ADAUSD"]

        signals = []

        for i in range(count):
            signal = TradingSignal(
                symbol=random.choice(symbols),
                direction=random.choice([Direction.LONG, Direction.SHORT]),
                confidence=random.uniform(*confidence_range),
                position_size=random.uniform(100, 2000),
                stop_loss=random.uniform(95, 105) if random.random() < 0.8 else None,
                take_profit=random.uniform(105, 120) if random.random() < 0.7 else None,
                reasoning=f"Test signal {i}",
                timeframe_analysis={
                    "1h": {"rsi": random.uniform(20, 80), "trend": random.choice(["up", "down", "sideways"])},
                    "4h": {"rsi": random.uniform(20, 80), "trend": random.choice(["up", "down", "sideways"])}
                }
            )
            signals.append(signal)

        return signals

    def generate_correlated_signals(
        self,
        base_symbol: str,
        correlated_symbols: list[str],
        correlation_strength: float = 0.8
    ) -> list[TradingSignal]:
        """Generate correlated signals for testing correlation limits."""

        signals = []

        # Base signal
        base_direction = random.choice([Direction.LONG, Direction.SHORT])
        base_confidence = random.uniform(0.6, 0.9)

        base_signal = TradingSignal(
            symbol=base_symbol,
            direction=base_direction,
            confidence=base_confidence,
            position_size=random.uniform(500, 1500),
            stop_loss=None,
            take_profit=None,
            reasoning="Base correlated signal",
            timeframe_analysis={}
        )
        signals.append(base_signal)

        # Correlated signals
        for symbol in correlated_symbols:
            # Determine if signal should be correlated
            if random.random() < correlation_strength:
                direction = base_direction
                confidence = base_confidence + random.gauss(0, 0.1)
                confidence = max(0.1, min(1.0, confidence))
            else:
                direction = random.choice([Direction.LONG, Direction.SHORT])
                confidence = random.uniform(0.3, 0.8)

            signal = TradingSignal(
                symbol=symbol,
                direction=direction,
                confidence=confidence,
                position_size=random.uniform(300, 1200),
                stop_loss=None,
                take_profit=None,
                reasoning=f"Correlated signal for {symbol}",
                timeframe_analysis={}
            )
            signals.append(signal)

        return signals

class TradeOutcomeGenerator:
    """Generates trade outcomes for testing."""

    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)

    def generate_trade_history(
        self,
        count: int,
        win_rate: float = 0.6,
        avg_win: float = 100.0,
        avg_loss: float = -50.0
    ) -> list[TradeOutcome]:
        """Generate realistic trade history."""

        trades = []

        for i in range(count):
            is_winner = random.random() < win_rate

            if is_winner:
                pnl = random.gauss(avg_win, avg_win * 0.3)
                pnl = max(1.0, pnl)  # Ensure positive
            else:
                pnl = random.gauss(avg_loss, abs(avg_loss) * 0.3)
                pnl = min(-1.0, pnl)  # Ensure negative

            entry_time = datetime.now(UTC) - timedelta(days=random.randint(1, 365))
            holding_time = timedelta(hours=random.randint(1, 72))

            trade = TradeOutcome(
                trade_id=f"test_trade_{i}",
                symbol=random.choice(["BTCUSD", "ETHUSD", "ADAUSD"]),
                direction=random.choice([Direction.LONG, Direction.SHORT]),
                entry_price=random.uniform(90, 110),
                exit_price=random.uniform(85, 115),
                position_size=random.uniform(100, 1000),
                entry_time=entry_time,
                exit_time=entry_time + holding_time,
                pnl=pnl,
                commission=abs(pnl) * 0.001,  # 0.1% commission
                confidence=random.uniform(0.4, 0.9),
                pattern_id=random.choice(["breakout", "reversal", "continuation", "divergence"]),
                market_regime=random.choice(["bull", "bear", "sideways"])
            )
            trades.append(trade)

        return trades

    def generate_drawdown_scenario(
        self,
        initial_capital: float = 10000.0,
        max_drawdown: float = 0.15
    ) -> list[TradeOutcome]:
        """Generate trade sequence that creates specific drawdown."""

        trades = []
        current_capital = initial_capital
        peak_capital = initial_capital

        trade_count = 0

        while True:
            # Calculate current drawdown
            current_drawdown = (peak_capital - current_capital) / peak_capital

            if current_drawdown >= max_drawdown:
                break

            # Generate trade that moves toward target drawdown
            remaining_drawdown = max_drawdown - current_drawdown
            target_loss = peak_capital * remaining_drawdown * random.uniform(0.1, 0.5)

            # Create losing trade
            pnl = -min(target_loss, current_capital * 0.05)  # Max 5% loss per trade

            entry_time = datetime.now(UTC) - timedelta(days=trade_count)

            trade = TradeOutcome(
                trade_id=f"drawdown_trade_{trade_count}",
                symbol="BTCUSD",
                direction=random.choice([Direction.LONG, Direction.SHORT]),
                entry_price=100.0,
                exit_price=95.0,
                position_size=abs(pnl) / 5.0,
                entry_time=entry_time,
                exit_time=entry_time + timedelta(hours=random.randint(1, 24)),
                pnl=pnl,
                commission=abs(pnl) * 0.001,
                confidence=random.uniform(0.3, 0.7),
                pattern_id="drawdown_test",
                market_regime="bear"
            )

            trades.append(trade)
            current_capital += pnl
            trade_count += 1

            # Occasional small wins to make it realistic
            if random.random() < 0.2:
                win_pnl = abs(pnl) * random.uniform(0.2, 0.5)
                current_capital += win_pnl

                if current_capital > peak_capital:
                    peak_capital = current_capital

        return trades

class TestDataSuite:
    """Complete test data generation suite."""

    def __init__(self, seed: Optional[int] = None):
        self.market_generator = MarketDataGenerator(seed)
        self.signal_generator = SignalDataGenerator(seed)
        self.trade_generator = TradeOutcomeGenerator(seed)

    def generate_comprehensive_test_dataset(self) -> dict[str, Any]:
        """Generate comprehensive test dataset for all scenarios."""

        dataset = {}

        # Market data scenarios
        dataset['market_scenarios'] = {
            'bull_market': self.market_generator.generate_market_scenario(
                MarketScenarioConfig(
                    regime=MarketRegime.BULL_MARKET,
                    duration_days=90,
                    initial_price=100.0,
                    volatility=0.15,
                    trend_strength=2.0,
                    noise_level=0.5,
                    volume_base=1000.0,
                    volume_volatility=0.3
                )
            ),
            'bear_market': self.market_generator.generate_market_scenario(
                MarketScenarioConfig(
                    regime=MarketRegime.BEAR_MARKET,
                    duration_days=60,
                    initial_price=100.0,
                    volatility=0.20,
                    trend_strength=-2.0,
                    noise_level=0.6,
                    volume_base=1200.0,
                    volume_volatility=0.4
                )
            ),
            'sideways_market': self.market_generator.generate_market_scenario(
                MarketScenarioConfig(
                    regime=MarketRegime.SIDEWAYS,
                    duration_days=120,
                    initial_price=100.0,
                    volatility=0.10,
                    trend_strength=0.5,
                    noise_level=0.3,
                    volume_base=800.0,
                    volume_volatility=0.2
                )
            )
        }

        # Multi-regime data
        dataset['multi_regime_data'] = self.market_generator.generate_multi_regime_data([
            (MarketRegime.BULL_MARKET, 30),
            (MarketRegime.SIDEWAYS, 20),
            (MarketRegime.BEAR_MARKET, 25),
            (MarketRegime.HIGH_VOLATILITY, 10),
            (MarketRegime.BULL_MARKET, 15)
        ])

        # Edge cases
        dataset['edge_cases'] = self.market_generator.generate_edge_case_scenarios()

        # Trading signals
        dataset['signals'] = {
            'random_signals': self.signal_generator.generate_signal_sequence(100),
            'high_confidence_signals': self.signal_generator.generate_signal_sequence(
                50, confidence_range=(0.7, 0.95)
            ),
            'low_confidence_signals': self.signal_generator.generate_signal_sequence(
                30, confidence_range=(0.2, 0.5)
            ),
            'correlated_signals': self.signal_generator.generate_correlated_signals(
                "BTCUSD", ["ETHUSD", "ADAUSD"], 0.8
            )
        }

        # Trade outcomes
        dataset['trade_outcomes'] = {
            'profitable_strategy': self.trade_generator.generate_trade_history(
                200, win_rate=0.65, avg_win=150.0, avg_loss=-75.0
            ),
            'break_even_strategy': self.trade_generator.generate_trade_history(
                150, win_rate=0.50, avg_win=100.0, avg_loss=-100.0
            ),
            'losing_strategy': self.trade_generator.generate_trade_history(
                100, win_rate=0.35, avg_win=80.0, avg_loss=-120.0
            ),
            'drawdown_scenario': self.trade_generator.generate_drawdown_scenario(
                initial_capital=10000.0, max_drawdown=0.20
            )
        }

        return dataset

    def save_test_dataset(self, dataset: dict[str, Any], output_path: str) -> None:
        """Save test dataset to files."""
        import pickle
        from pathlib import Path

        import pandas as pd

        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save complete dataset as pickle
        with open(output_dir / 'test_dataset.pkl', 'wb') as f:
            pickle.dump(dataset, f)

        # Save market scenarios as CSV files
        if 'market_scenarios' in dataset:
            for scenario_name, bars in dataset['market_scenarios'].items():
                df_data = []
                for bar in bars:
                    df_data.append({
                        'timestamp': bar.timestamp,
                        'open': bar.open,
                        'high': bar.high,
                        'low': bar.low,
                        'close': bar.close,
                        'volume': bar.volume
                    })

                df = pd.DataFrame(df_data)
                df.to_csv(output_dir / f'{scenario_name}.csv', index=False)

        print(f"Test dataset saved to {output_dir}")

    def load_test_dataset(self, input_path: str) -> dict[str, Any]:
        """Load test dataset from files."""
        import pickle
        from pathlib import Path

        input_dir = Path(input_path)

        # Load complete dataset from pickle
        with open(input_dir / 'test_dataset.pkl', 'rb') as f:
            dataset = pickle.load(f)

        return dataset

    def save_test_dataset(self, dataset: dict[str, Any], output_path: str) -> None:
        """Save test dataset to files."""
        import pickle
        from pathlib import Path

        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save as pickle for Python objects
        with open(output_dir / 'test_dataset.pkl', 'wb') as f:
            pickle.dump(dataset, f)

        # Save market data as CSV for external tools
        for scenario_name, bars in dataset['market_scenarios'].items():
            df = pd.DataFrame([{
                'timestamp': bar.timestamp,
                'open': bar.open,
                'high': bar.high,
                'low': bar.low,
                'close': bar.close,
                'volume': bar.volume
            } for bar in bars])

            df.to_csv(output_dir / f'{scenario_name}.csv', index=False)

    def load_test_dataset(self, input_path: str) -> dict[str, Any]:
        """Load test dataset from file."""
        import pickle
        from pathlib import Path

        with open(Path(input_path) / 'test_dataset.pkl', 'rb') as f:
            return pickle.load(f)
