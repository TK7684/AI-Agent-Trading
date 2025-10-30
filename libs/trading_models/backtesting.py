"""
Backtesting engine for comprehensive strategy validation.
"""

import hashlib
import json
import logging
import random
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

from .enums import Direction
from .market_data import MarketBar
from .orders import TradeOutcome

# MarketDataProvider will be passed as parameter
from .signals import TradingSignal

# TradingOrchestrator will be passed as parameter

logger = logging.getLogger(__name__)

@dataclass
class BacktestConfig:
    """Configuration for backtesting runs."""
    start_date: datetime
    end_date: datetime
    initial_capital: float
    symbols: list[str]
    timeframes: list[str]
    commission_rate: float = 0.001
    slippage_bps: int = 2
    random_seed: Optional[int] = None
    data_window_hash: Optional[str] = None
    max_positions: int = 10

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary for serialization."""
        return asdict(self)

@dataclass
class BacktestMetrics:
    """Comprehensive backtesting performance metrics."""
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    calmar_ratio: float
    win_rate: float
    profit_factor: float
    avg_trade_return: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    largest_win: float
    largest_loss: float
    avg_holding_period: timedelta
    volatility: float
    beta: float
    alpha: float
    sortino_ratio: float

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary for serialization."""
        result = asdict(self)
        # Convert timedelta to seconds for JSON serialization
        result['avg_holding_period'] = self.avg_holding_period.total_seconds()
        return result

@dataclass
class BacktestResult:
    """Complete backtesting results."""
    config: BacktestConfig
    metrics: BacktestMetrics
    trades: list[TradeOutcome]
    equity_curve: pd.DataFrame
    drawdown_curve: pd.DataFrame
    monthly_returns: pd.DataFrame
    benchmark_comparison: Optional[pd.DataFrame]
    execution_time: float
    data_integrity_hash: str

    def save_report(self, output_path: Path) -> None:
        """Save comprehensive backtest report."""
        report = {
            'config': self.config.to_dict(),
            'metrics': self.metrics.to_dict(),
            'execution_time': self.execution_time,
            'data_integrity_hash': self.data_integrity_hash,
            'trade_count': len(self.trades),
            'generated_at': datetime.now(UTC).isoformat()
        }

        with open(output_path / 'backtest_report.json', 'w') as f:
            json.dump(report, f, indent=2, default=str)

        # Save detailed data
        self.equity_curve.to_csv(output_path / 'equity_curve.csv')
        self.drawdown_curve.to_csv(output_path / 'drawdown_curve.csv')
        self.monthly_returns.to_csv(output_path / 'monthly_returns.csv')

        if self.benchmark_comparison is not None:
            self.benchmark_comparison.to_csv(output_path / 'benchmark_comparison.csv')

class BacktestEngine:
    """High-performance backtesting engine with data integrity validation."""

    def __init__(self, data_provider=None):
        self.data_provider = data_provider
        self.logger = logging.getLogger(__name__)

    def run_backtest(
        self,
        strategy,
        config: BacktestConfig
    ) -> BacktestResult:
        """
        Run comprehensive backtest with locked data windows and reproducible results.
        """
        start_time = datetime.now(UTC)

        # Set random seed for reproducibility
        if config.random_seed is not None:
            random.seed(config.random_seed)
            np.random.seed(config.random_seed)

        # Load and validate historical data
        historical_data = self._load_historical_data(config)
        data_hash = self._calculate_data_hash(historical_data)

        # Validate data window integrity
        if config.data_window_hash and config.data_window_hash != data_hash:
            raise ValueError(f"Data integrity check failed. Expected {config.data_window_hash}, got {data_hash}")

        # Initialize portfolio state
        portfolio_value = config.initial_capital
        positions = {}
        trades = []
        equity_curve = []

        # Run simulation
        for timestamp, market_data in self._iterate_market_data(historical_data, config):
            # Update portfolio valuation
            portfolio_value = self._update_portfolio_value(positions, market_data, portfolio_value)

            # Generate trading signals
            signals = strategy.analyze_market(market_data, timestamp)

            # Execute trades with realistic constraints
            new_trades = self._execute_trades(
                signals, positions, portfolio_value, market_data, config, timestamp
            )
            trades.extend(new_trades)

            # Record equity curve
            equity_curve.append({
                'timestamp': timestamp,
                'portfolio_value': portfolio_value,
                'positions_count': len(positions),
                'cash': portfolio_value - sum(pos['value'] for pos in positions.values())
            })

        # Calculate comprehensive metrics
        metrics = self._calculate_metrics(trades, equity_curve, config)

        # Generate result dataframes
        equity_df = pd.DataFrame(equity_curve).set_index('timestamp')
        drawdown_df = self._calculate_drawdown_curve(equity_df)
        monthly_returns = self._calculate_monthly_returns(equity_df)

        execution_time = (datetime.now(UTC) - start_time).total_seconds()

        return BacktestResult(
            config=config,
            metrics=metrics,
            trades=trades,
            equity_curve=equity_df,
            drawdown_curve=drawdown_df,
            monthly_returns=monthly_returns,
            benchmark_comparison=None,  # TODO: Implement benchmark comparison
            execution_time=execution_time,
            data_integrity_hash=data_hash
        )

    def _load_historical_data(self, config: BacktestConfig) -> dict[str, pd.DataFrame]:
        """Load historical market data for backtesting."""
        data = {}

        for symbol in config.symbols:
            for timeframe in config.timeframes:
                try:
                    df = self.data_provider.get_historical_data(
                        symbol, timeframe, config.start_date, config.end_date
                    )
                    data[f"{symbol}_{timeframe}"] = df
                    self.logger.info(f"Loaded {len(df)} bars for {symbol} {timeframe}")
                except Exception as e:
                    self.logger.error(f"Failed to load data for {symbol} {timeframe}: {e}")
                    raise

        return data

    def _calculate_data_hash(self, data: dict[str, pd.DataFrame]) -> str:
        """Calculate hash of historical data for integrity verification."""
        combined_data = ""
        for key in sorted(data.keys()):
            df = data[key]
            # Include shape, columns, and sample of data in hash
            combined_data += f"{key}:{df.shape}:{list(df.columns)}:{df.head().to_string()}"

        return hashlib.sha256(combined_data.encode()).hexdigest()[:16]

    def _iterate_market_data(
        self,
        historical_data: dict[str, pd.DataFrame],
        config: BacktestConfig
    ) -> tuple[datetime, dict[str, MarketBar]]:
        """Iterate through historical data chronologically."""
        # Create unified timeline
        all_timestamps = set()
        for df in historical_data.values():
            all_timestamps.update(df.index)

        for timestamp in sorted(all_timestamps):
            market_snapshot = {}

            for key, df in historical_data.items():
                if timestamp in df.index:
                    row = df.loc[timestamp]
                    symbol, timeframe = key.split('_', 1)

                    market_snapshot[key] = MarketBar(
                        symbol=symbol,
                        timeframe=timeframe,
                        timestamp=timestamp,
                        open=float(row['open']),
                        high=float(row['high']),
                        low=float(row['low']),
                        close=float(row['close']),
                        volume=float(row['volume'])
                    )

            if market_snapshot:
                yield timestamp, market_snapshot

    def _execute_trades(
        self,
        signals: list[TradingSignal],
        positions: dict[str, dict],
        portfolio_value: float,
        market_data: dict[str, MarketBar],
        config: BacktestConfig,
        timestamp: datetime
    ) -> list[TradeOutcome]:
        """Execute trades with realistic slippage and commission."""
        executed_trades = []

        for signal in signals:
            if len(positions) >= config.max_positions and signal.symbol not in positions:
                continue  # Skip if max positions reached

            # Get current market price
            market_bar = None
            for key, bar in market_data.items():
                if bar.symbol == signal.symbol:
                    market_bar = bar
                    break

            if not market_bar:
                continue

            # Calculate position size (simplified)
            position_size = min(
                signal.position_size,
                portfolio_value * 0.02  # Max 2% per trade
            )

            # Apply slippage
            slippage_factor = 1 + (config.slippage_bps / 10000)
            if signal.direction == Direction.LONG:
                execution_price = market_bar.close * slippage_factor
            else:
                execution_price = market_bar.close / slippage_factor

            # Calculate commission
            commission = position_size * config.commission_rate

            # Create trade outcome
            trade = TradeOutcome(
                trade_id=f"bt_{timestamp.timestamp()}_{signal.symbol}",
                symbol=signal.symbol,
                direction=signal.direction,
                entry_price=execution_price,
                exit_price=execution_price,  # Will be updated on exit
                position_size=position_size,
                entry_time=timestamp,
                exit_time=timestamp,  # Will be updated on exit
                pnl=0.0,  # Will be calculated on exit
                commission=commission,
                confidence=signal.confidence,
                pattern_id=getattr(signal, 'pattern_id', 'unknown'),
                market_regime=getattr(signal, 'market_regime', 'unknown')
            )

            # Update positions
            positions[signal.symbol] = {
                'trade': trade,
                'value': position_size,
                'entry_price': execution_price
            }

            executed_trades.append(trade)

        return executed_trades

    def _update_portfolio_value(
        self,
        positions: dict[str, dict],
        market_data: dict[str, MarketBar],
        current_value: float
    ) -> float:
        """Update portfolio value based on current market prices."""
        total_position_value = 0.0

        for symbol, position in positions.items():
            # Find current market price
            current_price = None
            for bar in market_data.values():
                if bar.symbol == symbol:
                    current_price = bar.close
                    break

            if current_price:
                # Update position value
                entry_price = position['entry_price']
                position_size = position['value']

                if position['trade'].direction == Direction.LONG:
                    current_position_value = position_size * (current_price / entry_price)
                else:
                    current_position_value = position_size * (2 - current_price / entry_price)

                position['value'] = current_position_value
                total_position_value += current_position_value

        return total_position_value + (current_value - sum(pos['value'] for pos in positions.values()))

    def _calculate_metrics(
        self,
        trades: list[TradeOutcome],
        equity_curve: list[dict],
        config: BacktestConfig
    ) -> BacktestMetrics:
        """Calculate comprehensive performance metrics."""
        if not trades or not equity_curve:
            return BacktestMetrics(
                total_return=0.0, sharpe_ratio=0.0, max_drawdown=0.0,
                calmar_ratio=0.0, win_rate=0.0, profit_factor=0.0,
                avg_trade_return=0.0, total_trades=0, winning_trades=0,
                losing_trades=0, largest_win=0.0, largest_loss=0.0,
                avg_holding_period=timedelta(0), volatility=0.0,
                beta=0.0, alpha=0.0, sortino_ratio=0.0
            )

        # Convert equity curve to pandas for calculations
        equity_df = pd.DataFrame(equity_curve)
        equity_df['returns'] = equity_df['portfolio_value'].pct_change().fillna(0)

        # Basic metrics
        total_return = (equity_df['portfolio_value'].iloc[-1] / config.initial_capital) - 1

        # Risk metrics
        returns = equity_df['returns'].dropna()
        volatility = returns.std() * np.sqrt(252)  # Annualized
        sharpe_ratio = (returns.mean() * 252) / volatility if volatility > 0 else 0

        # Drawdown calculation
        running_max = equity_df['portfolio_value'].expanding().max()
        drawdown = (equity_df['portfolio_value'] - running_max) / running_max
        max_drawdown = abs(drawdown.min())

        # Calmar ratio
        calmar_ratio = (total_return * 252) / max_drawdown if max_drawdown > 0 else 0

        # Trade-based metrics
        winning_trades = sum(1 for t in trades if t.pnl > 0)
        losing_trades = sum(1 for t in trades if t.pnl < 0)
        win_rate = winning_trades / len(trades) if trades else 0

        gross_profit = sum(t.pnl for t in trades if t.pnl > 0)
        gross_loss = abs(sum(t.pnl for t in trades if t.pnl < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        avg_trade_return = sum(t.pnl for t in trades) / len(trades) if trades else 0
        largest_win = max((t.pnl for t in trades), default=0)
        largest_loss = min((t.pnl for t in trades), default=0)

        # Holding period
        holding_periods = [t.exit_time - t.entry_time for t in trades if t.exit_time > t.entry_time]
        avg_holding_period = sum(holding_periods, timedelta(0)) / len(holding_periods) if holding_periods else timedelta(0)

        # Sortino ratio (downside deviation)
        negative_returns = returns[returns < 0]
        downside_deviation = negative_returns.std() * np.sqrt(252) if len(negative_returns) > 0 else 0
        sortino_ratio = (returns.mean() * 252) / downside_deviation if downside_deviation > 0 else 0

        return BacktestMetrics(
            total_return=total_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            calmar_ratio=calmar_ratio,
            win_rate=win_rate,
            profit_factor=profit_factor,
            avg_trade_return=avg_trade_return,
            total_trades=len(trades),
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            largest_win=largest_win,
            largest_loss=largest_loss,
            avg_holding_period=avg_holding_period,
            volatility=volatility,
            beta=0.0,  # TODO: Calculate vs benchmark
            alpha=0.0,  # TODO: Calculate vs benchmark
            sortino_ratio=sortino_ratio
        )

    def _calculate_drawdown_curve(self, equity_df: pd.DataFrame) -> pd.DataFrame:
        """Calculate detailed drawdown curve."""
        running_max = equity_df['portfolio_value'].expanding().max()
        drawdown = (equity_df['portfolio_value'] - running_max) / running_max

        return pd.DataFrame({
            'drawdown': drawdown,
            'running_max': running_max,
            'underwater_duration': self._calculate_underwater_duration(drawdown)
        }, index=equity_df.index)

    def _calculate_underwater_duration(self, drawdown: pd.Series) -> pd.Series:
        """Calculate how long portfolio has been underwater."""
        underwater = drawdown < 0
        duration = pd.Series(0, index=drawdown.index)

        current_duration = 0
        for i, is_underwater in enumerate(underwater):
            if is_underwater:
                current_duration += 1
            else:
                current_duration = 0
            duration.iloc[i] = current_duration

        return duration

    def _calculate_monthly_returns(self, equity_df: pd.DataFrame) -> pd.DataFrame:
        """Calculate monthly return statistics."""
        monthly = equity_df.resample('ME')['portfolio_value'].last()
        monthly_returns = monthly.pct_change().fillna(0)

        return pd.DataFrame({
            'monthly_return': monthly_returns,
            'cumulative_return': (1 + monthly_returns).cumprod() - 1,
            'portfolio_value': monthly
        })

class BacktestValidator:
    """Validates backtesting results against performance thresholds."""

    def __init__(self, baseline_metrics: Optional[BacktestMetrics] = None):
        self.baseline_metrics = baseline_metrics
        self.logger = logging.getLogger(__name__)

    def validate_performance(
        self,
        result: BacktestResult,
        min_sharpe: float = 0.5,
        max_drawdown: float = 0.25,
        min_win_rate: float = 0.4
    ) -> bool:
        """
        Validate backtest results against minimum performance criteria.
        Returns True if all criteria are met.
        """
        metrics = result.metrics

        # Check minimum performance criteria
        criteria = [
            (metrics.sharpe_ratio >= min_sharpe, f"Sharpe ratio {metrics.sharpe_ratio:.3f} < {min_sharpe}"),
            (metrics.max_drawdown <= max_drawdown, f"Max drawdown {metrics.max_drawdown:.3f} > {max_drawdown}"),
            (metrics.win_rate >= min_win_rate, f"Win rate {metrics.win_rate:.3f} < {min_win_rate}"),
            (metrics.total_trades >= 10, f"Insufficient trades: {metrics.total_trades}"),
            (metrics.profit_factor > 1.0, f"Profit factor {metrics.profit_factor:.3f} <= 1.0")
        ]

        all_passed = True
        for passed, message in criteria:
            if not passed:
                self.logger.error(f"Performance validation failed: {message}")
                all_passed = False

        # Compare against baseline if available
        if self.baseline_metrics and all_passed:
            baseline_comparison = self._compare_to_baseline(metrics)
            if not baseline_comparison:
                all_passed = False

        return all_passed

    def _compare_to_baseline(self, metrics: BacktestMetrics) -> bool:
        """Compare current metrics against baseline performance."""
        if not self.baseline_metrics:
            return True

        # Allow small degradation in performance
        tolerance = 0.05  # 5% tolerance

        comparisons = [
            (
                metrics.sharpe_ratio >= self.baseline_metrics.sharpe_ratio * (1 - tolerance),
                f"Sharpe degraded: {metrics.sharpe_ratio:.3f} vs baseline {self.baseline_metrics.sharpe_ratio:.3f}"
            ),
            (
                metrics.max_drawdown <= self.baseline_metrics.max_drawdown * (1 + tolerance),
                f"Max drawdown worsened: {metrics.max_drawdown:.3f} vs baseline {self.baseline_metrics.max_drawdown:.3f}"
            )
        ]

        all_passed = True
        for passed, message in comparisons:
            if not passed:
                self.logger.warning(f"Baseline comparison failed: {message}")
                all_passed = False

        return all_passed
