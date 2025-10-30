"""
Performance Monitoring and Optimization System

This module provides comprehensive performance monitoring, profiling, and optimization
capabilities for the trading system, including:
- Real-time performance metrics
- Memory usage monitoring
- CPU profiling and optimization
- Database query performance
- Cache performance analysis
- Automated optimization suggestions
"""

import cProfile
import io
import json
import logging
import pstats
import statistics
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps
from typing import Any, Optional

import psutil
from pydantic import BaseModel

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric(BaseModel):
    """Individual performance metric."""
    name: str
    value: float
    unit: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_anomaly(self) -> bool:
        """Check if metric value is anomalous."""
        # This would implement anomaly detection logic
        return False


@dataclass
class SystemMetrics(BaseModel):
    """System-wide performance metrics."""
    timestamp: datetime = field(default_factory=datetime.now)
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_available_gb: float = 0.0
    disk_usage_percent: float = 0.0
    network_io_mbps: float = 0.0
    process_count: int = 0
    load_average: float = 0.0

    @property
    def is_healthy(self) -> bool:
        """Check if system metrics indicate healthy state."""
        return (
            self.cpu_percent < 80 and
            self.memory_percent < 85 and
            self.disk_usage_percent < 90 and
            self.load_average < 5.0
        )


@dataclass
class ApplicationMetrics(BaseModel):
    """Application-specific performance metrics."""
    timestamp: datetime = field(default_factory=datetime.now)
    request_count: int = 0
    response_time_ms: float = 0.0
    error_rate: float = 0.0
    cache_hit_rate: float = 0.0
    database_query_time_ms: float = 0.0
    memory_usage_mb: float = 0.0
    active_connections: int = 0

    @property
    def is_performing_well(self) -> bool:
        """Check if application is performing well."""
        return (
            self.response_time_ms < 1000 and
            self.error_rate < 0.05 and
            self.cache_hit_rate > 0.7
        )


@dataclass
class TradingMetrics(BaseModel):
    """Trading-specific performance metrics."""
    timestamp: datetime = field(default_factory=datetime.now)
    analysis_time_ms: float = 0.0
    signal_generation_time_ms: float = 0.0
    order_execution_time_ms: float = 0.0
    risk_calculation_time_ms: float = 0.0
    llm_response_time_ms: float = 0.0
    market_data_latency_ms: float = 0.0
    trades_per_second: float = 0.0
    profit_loss: float = 0.0

    @property
    def is_efficient(self) -> bool:
        """Check if trading operations are efficient."""
        return (
            self.analysis_time_ms < 5000 and
            self.signal_generation_time_ms < 1000 and
            self.order_execution_time_ms < 2000 and
            self.llm_response_time_ms < 5000
        )


class PerformanceProfiler:
    """Performance profiling and analysis."""

    def __init__(self):
        self.profiles: dict[str, cProfile.Profile] = {}
        self.stats: dict[str, pstats.Stats] = {}
        self.active_profiles: dict[str, bool] = {}

    def start_profile(self, name: str) -> None:
        """Start profiling for a named operation."""
        if name in self.active_profiles and self.active_profiles[name]:
            logger.warning(f"Profile {name} is already active")
            return

        profile = cProfile.Profile()
        profile.enable()

        self.profiles[name] = profile
        self.active_profiles[name] = True

        logger.debug(f"Started profiling: {name}")

    def stop_profile(self, name: str) -> pstats.Stats:
        """Stop profiling and return statistics."""
        if name not in self.active_profiles or not self.active_profiles[name]:
            logger.warning(f"Profile {name} is not active")
            return None

        profile = self.profiles[name]
        profile.disable()

        # Create stats object
        stats = pstats.Stats(profile)
        self.stats[name] = stats
        self.active_profiles[name] = False

        logger.debug(f"Stopped profiling: {name}")
        return stats

    def get_profile_summary(self, name: str) -> dict[str, Any]:
        """Get summary of profiling results."""
        if name not in self.stats:
            return {"error": "Profile not found"}

        stats = self.stats[name]

        # Capture stats output
        output = io.StringIO()
        stats.print_stats(file=output)
        stats_output = output.getvalue()
        output.close()

        # Parse key metrics
        lines = stats_output.split('\n')
        total_calls = 0
        total_time = 0.0

        for line in lines:
            if 'function calls' in line:
                parts = line.split()
                if len(parts) >= 4:
                    total_calls = int(parts[0])
                    total_time = float(parts[3])
                break

        return {
            "name": name,
            "total_calls": total_calls,
            "total_time": total_time,
            "full_stats": stats_output,
            "top_functions": self._get_top_functions(stats)
        }

    def _get_top_functions(self, stats: pstats.Stats) -> list[dict[str, Any]]:
        """Get top functions by execution time."""
        top_functions = []

        # Get top 10 functions by cumulative time
        stats.sort_stats('cumulative')

        for func, (cc, nc, tt, ct, callers) in list(stats.stats.items())[:10]:
            filename, line_num, func_name = func

            top_functions.append({
                "filename": filename,
                "line": line_num,
                "function": func_name,
                "calls": nc,
                "total_time": tt,
                "cumulative_time": ct
            })

        return top_functions

    def clear_profiles(self) -> None:
        """Clear all profiling data."""
        self.profiles.clear()
        self.stats.clear()
        self.active_profiles.clear()
        logger.info("All profiling data cleared")


class MemoryMonitor:
    """Memory usage monitoring and analysis."""

    def __init__(self):
        self.memory_snapshots: list[dict[str, Any]] = []
        self.leak_detector = None
        self.max_snapshots = 1000

        # Start memory monitoring
        self._start_memory_monitoring()

    def _start_memory_monitoring(self) -> None:
        """Start memory monitoring thread."""
        def monitor_memory():
            while True:
                try:
                    self._take_memory_snapshot()
                    time.sleep(30)  # Take snapshot every 30 seconds
                except Exception as e:
                    logger.error(f"Error in memory monitoring: {e}")
                    time.sleep(60)

        thread = threading.Thread(target=monitor_memory, daemon=True)
        thread.start()
        logger.info("Memory monitoring started")

    def _take_memory_snapshot(self) -> None:
        """Take a memory usage snapshot."""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()

            snapshot = {
                "timestamp": datetime.now(),
                "rss_mb": memory_info.rss / 1024 / 1024,
                "vms_mb": memory_info.vms / 1024 / 1024,
                "percent": process.memory_percent(),
                "available_gb": psutil.virtual_memory().available / 1024 / 1024 / 1024
            }

            self.memory_snapshots.append(snapshot)

            # Keep only recent snapshots
            if len(self.memory_snapshots) > self.max_snapshots:
                self.memory_snapshots = self.memory_snapshots[-self.max_snapshots:]

        except Exception as e:
            logger.error(f"Error taking memory snapshot: {e}")

    def get_memory_summary(self) -> dict[str, Any]:
        """Get memory usage summary."""
        if not self.memory_snapshots:
            return {"error": "No memory data available"}

        recent_snapshots = self.memory_snapshots[-100:]  # Last 100 snapshots

        rss_values = [s["rss_mb"] for s in recent_snapshots]
        vms_values = [s["vms_mb"] for s in recent_snapshots]
        percent_values = [s["percent"] for s in recent_snapshots]

        return {
            "current_rss_mb": rss_values[-1] if rss_values else 0,
            "current_vms_mb": vms_values[-1] if vms_values else 0,
            "current_percent": percent_values[-1] if percent_values else 0,
            "avg_rss_mb": statistics.mean(rss_values) if rss_values else 0,
            "max_rss_mb": max(rss_values) if rss_values else 0,
            "min_rss_mb": min(rss_values) if rss_values else 0,
            "trend": self._calculate_memory_trend(),
            "snapshots_count": len(self.memory_snapshots)
        }

    def _calculate_memory_trend(self) -> str:
        """Calculate memory usage trend."""
        if len(self.memory_snapshots) < 10:
            return "insufficient_data"

        recent = self.memory_snapshots[-10:]
        first_rss = recent[0]["rss_mb"]
        last_rss = recent[-1]["rss_mb"]

        change_percent = ((last_rss - first_rss) / first_rss) * 100

        if change_percent > 10:
            return "increasing"
        elif change_percent < -10:
            return "decreasing"
        else:
            return "stable"

    def detect_memory_leaks(self) -> list[dict[str, Any]]:
        """Detect potential memory leaks."""
        if len(self.memory_snapshots) < 50:
            return []

        potential_leaks = []

        # Check for consistent memory growth over time
        for window_size in [10, 20, 50]:
            if len(self.memory_snapshots) >= window_size:
                recent = self.memory_snapshots[-window_size:]
                rss_values = [s["rss_mb"] for s in recent]

                # Calculate growth rate
                if len(rss_values) >= 2:
                    growth_rate = (rss_values[-1] - rss_values[0]) / len(rss_values)

                    if growth_rate > 1.0:  # More than 1MB growth per snapshot
                        potential_leaks.append({
                            "window_size": window_size,
                            "growth_rate_mb_per_snapshot": growth_rate,
                            "total_growth_mb": rss_values[-1] - rss_values[0],
                            "severity": "high" if growth_rate > 5.0 else "medium"
                        })

        return potential_leaks


class PerformanceOptimizer:
    """Automated performance optimization suggestions."""

    def __init__(self, profiler: PerformanceProfiler, memory_monitor: MemoryMonitor):
        self.profiler = profiler
        self.memory_monitor = memory_monitor
        self.optimization_suggestions: list[dict[str, Any]] = []

    def analyze_performance(self) -> list[dict[str, Any]]:
        """Analyze performance and generate optimization suggestions."""
        suggestions = []

        # Analyze profiling data
        for profile_name in self.profiler.stats:
            profile_summary = self.profiler.get_profile_summary(profile_name)
            profile_suggestions = self._analyze_profile(profile_summary)
            suggestions.extend(profile_suggestions)

        # Analyze memory usage
        memory_summary = self.memory_monitor.get_memory_summary()
        memory_suggestions = self._analyze_memory(memory_summary)
        suggestions.extend(memory_suggestions)

        # Analyze system metrics
        system_suggestions = self._analyze_system_metrics()
        suggestions.extend(system_suggestions)

        self.optimization_suggestions = suggestions
        return suggestions

    def _analyze_profile(self, profile_summary: dict[str, Any]) -> list[dict[str, Any]]:
        """Analyze profiling data for optimization opportunities."""
        suggestions = []

        if "error" in profile_summary:
            return suggestions

        total_time = profile_summary.get("total_time", 0)
        top_functions = profile_summary.get("top_functions", [])

        # Check for slow functions
        for func in top_functions:
            if func["cumulative_time"] > 1.0:  # More than 1 second
                suggestions.append({
                    "type": "slow_function",
                    "severity": "high" if func["cumulative_time"] > 5.0 else "medium",
                    "function": func["function"],
                    "filename": func["filename"],
                    "line": func["line"],
                    "cumulative_time": func["cumulative_time"],
                    "suggestion": f"Consider optimizing function {func['function']} in {func['filename']}:{func['line']}"
                })

        # Check for frequently called functions
        for func in top_functions:
            if func["calls"] > 1000:  # More than 1000 calls
                suggestions.append({
                    "type": "frequent_calls",
                    "severity": "medium",
                    "function": func["function"],
                    "calls": func["calls"],
                    "suggestion": f"Consider caching or memoization for {func['function']} (called {func['calls']} times)"
                })

        return suggestions

    def _analyze_memory(self, memory_summary: dict[str, Any]) -> list[dict[str, Any]]:
        """Analyze memory usage for optimization opportunities."""
        suggestions = []

        if "error" in memory_summary:
            return suggestions

        current_rss = memory_summary.get("current_rss_mb", 0)
        trend = memory_summary.get("trend", "stable")

        # Check for high memory usage
        if current_rss > 1000:  # More than 1GB
            suggestions.append({
                "type": "high_memory_usage",
                "severity": "high" if current_rss > 2000 else "medium",
                "current_usage_mb": current_rss,
                "suggestion": f"High memory usage ({current_rss:.1f}MB). Consider memory profiling and optimization."
            })

        # Check for memory leaks
        if trend == "increasing":
            suggestions.append({
                "type": "memory_leak_suspected",
                "severity": "high",
                "trend": trend,
                "suggestion": "Memory usage is consistently increasing. Check for memory leaks."
            })

        # Check for memory leaks
        memory_leaks = self.memory_monitor.detect_memory_leaks()
        for leak in memory_leaks:
            suggestions.append({
                "type": "memory_leak_detected",
                "severity": leak["severity"],
                "growth_rate": leak["growth_rate_mb_per_snapshot"],
                "suggestion": f"Potential memory leak detected. Growth rate: {leak['growth_rate_mb_per_snapshot']:.2f}MB per snapshot"
            })

        return suggestions

    def _analyze_system_metrics(self) -> list[dict[str, Any]]:
        """Analyze system metrics for optimization opportunities."""
        suggestions = []

        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()

            # Check CPU usage
            if cpu_percent > 80:
                suggestions.append({
                    "type": "high_cpu_usage",
                    "severity": "high" if cpu_percent > 90 else "medium",
                    "cpu_percent": cpu_percent,
                    "suggestion": f"High CPU usage ({cpu_percent:.1f}%). Consider optimizing CPU-intensive operations."
                })

            # Check memory pressure
            if memory.percent > 85:
                suggestions.append({
                    "type": "high_memory_pressure",
                    "severity": "high" if memory.percent > 95 else "medium",
                    "memory_percent": memory.percent,
                    "suggestion": f"High memory pressure ({memory.percent:.1f}%). Consider reducing memory usage."
                })

            # Check disk usage
            disk = psutil.disk_usage('/')
            if disk.percent > 90:
                suggestions.append({
                    "type": "high_disk_usage",
                    "severity": "high",
                    "disk_percent": disk.percent,
                    "suggestion": f"High disk usage ({disk.percent:.1f}%). Consider cleanup or expansion."
                })

        except Exception as e:
            logger.error(f"Error analyzing system metrics: {e}")

        return suggestions

    def get_optimization_report(self) -> dict[str, Any]:
        """Get comprehensive optimization report."""
        suggestions = self.analyze_performance()

        # Categorize suggestions
        high_severity = [s for s in suggestions if s["severity"] == "high"]
        medium_severity = [s for s in suggestions if s["severity"] == "medium"]
        low_severity = [s for s in suggestions if s["severity"] == "low"]

        return {
            "timestamp": datetime.now().isoformat(),
            "total_suggestions": len(suggestions),
            "high_severity_count": len(high_severity),
            "medium_severity_count": len(medium_severity),
            "low_severity_count": len(low_severity),
            "suggestions_by_type": self._group_suggestions_by_type(suggestions),
            "high_priority_suggestions": high_severity,
            "all_suggestions": suggestions
        }

    def _group_suggestions_by_type(self, suggestions: list[dict[str, Any]]) -> dict[str, int]:
        """Group suggestions by type."""
        grouped = defaultdict(int)
        for suggestion in suggestions:
            grouped[suggestion["type"]] += 1
        return dict(grouped)


class PerformanceMonitor:
    """Main performance monitoring system."""

    def __init__(self):
        self.profiler = PerformanceProfiler()
        self.memory_monitor = MemoryMonitor()
        self.optimizer = PerformanceOptimizer(self.profiler, self.memory_monitor)

        # Metrics storage
        self.system_metrics: list[SystemMetrics] = []
        self.application_metrics: list[ApplicationMetrics] = []
        self.trading_metrics: list[TradingMetrics] = []

        # Monitoring state
        self._monitoring = False
        self._monitor_thread = None

        # Start monitoring
        self.start_monitoring()

    def start_monitoring(self) -> None:
        """Start performance monitoring."""
        if self._monitoring:
            return

        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("Performance monitoring started")

    def stop_monitoring(self) -> None:
        """Stop performance monitoring."""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join()
        logger.info("Performance monitoring stopped")

    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self._monitoring:
            try:
                self._collect_metrics()
                time.sleep(30)  # Collect metrics every 30 seconds
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(60)

    def _collect_metrics(self) -> None:
        """Collect all performance metrics."""
        try:
            # System metrics
            system_metric = self._collect_system_metrics()
            self.system_metrics.append(system_metric)

            # Application metrics
            app_metric = self._collect_application_metrics()
            self.application_metrics.append(app_metric)

            # Trading metrics
            trading_metric = self._collect_trading_metrics()
            self.trading_metrics.append(trading_metric)

            # Keep only recent metrics
            max_metrics = 1000
            if len(self.system_metrics) > max_metrics:
                self.system_metrics = self.system_metrics[-max_metrics:]
            if len(self.application_metrics) > max_metrics:
                self.application_metrics = self.application_metrics[-max_metrics:]
            if len(self.trading_metrics) > max_metrics:
                self.trading_metrics = self.trading_metrics[-max_metrics:]

        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")

    def _collect_system_metrics(self) -> SystemMetrics:
        """Collect system performance metrics."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            # Network I/O
            net_io = psutil.net_io_counters()
            network_io_mbps = (net_io.bytes_sent + net_io.bytes_recv) / 1024 / 1024 / 1024

            # Load average (Unix-like systems)
            try:
                load_avg = psutil.getloadavg()[0]
            except AttributeError:
                load_avg = 0.0

            return SystemMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_available_gb=memory.available / 1024 / 1024 / 1024,
                disk_usage_percent=disk.percent,
                network_io_mbps=network_io_mbps,
                process_count=len(psutil.pids()),
                load_average=load_avg
            )
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return SystemMetrics()

    def _collect_application_metrics(self) -> ApplicationMetrics:
        """Collect application performance metrics."""
        # This would collect application-specific metrics
        # Implementation depends on your application structure
        return ApplicationMetrics()

    def _collect_trading_metrics(self) -> TradingMetrics:
        """Collect trading performance metrics."""
        # This would collect trading-specific metrics
        # Implementation depends on your trading system structure
        return TradingMetrics()

    def get_performance_summary(self) -> dict[str, Any]:
        """Get comprehensive performance summary."""
        return {
            "system": self._get_system_summary(),
            "application": self._get_application_summary(),
            "trading": self._get_trading_summary(),
            "memory": self.memory_monitor.get_memory_summary(),
            "optimization": self.optimizer.get_optimization_report()
        }

    def _get_system_summary(self) -> dict[str, Any]:
        """Get system metrics summary."""
        if not self.system_metrics:
            return {"error": "No system metrics available"}

        recent = self.system_metrics[-100:]  # Last 100 metrics

        return {
            "current_cpu_percent": recent[-1].cpu_percent if recent else 0,
            "current_memory_percent": recent[-1].memory_percent if recent else 0,
            "avg_cpu_percent": statistics.mean([m.cpu_percent for m in recent]) if recent else 0,
            "avg_memory_percent": statistics.mean([m.memory_percent for m in recent]) if recent else 0,
            "is_healthy": recent[-1].is_healthy if recent else False,
            "metrics_count": len(self.system_metrics)
        }

    def _get_application_summary(self) -> dict[str, Any]:
        """Get application metrics summary."""
        if not self.application_metrics:
            return {"error": "No application metrics available"}

        recent = self.application_metrics[-100:]  # Last 100 metrics

        return {
            "current_response_time": recent[-1].response_time_ms if recent else 0,
            "current_error_rate": recent[-1].error_rate if recent else 0,
            "avg_response_time": statistics.mean([m.response_time_ms for m in recent]) if recent else 0,
            "avg_error_rate": statistics.mean([m.error_rate for m in recent]) if recent else 0,
            "is_performing_well": recent[-1].is_performing_well if recent else False,
            "metrics_count": len(self.application_metrics)
        }

    def _get_trading_summary(self) -> dict[str, Any]:
        """Get trading metrics summary."""
        if not self.trading_metrics:
            return {"error": "No trading metrics available"}

        recent = self.trading_metrics[-100:]  # Last 100 metrics

        return {
            "current_analysis_time": recent[-1].analysis_time_ms if recent else 0,
            "current_execution_time": recent[-1].order_execution_time_ms if recent else 0,
            "avg_analysis_time": statistics.mean([m.analysis_time_ms for m in recent]) if recent else 0,
            "avg_execution_time": statistics.mean([m.order_execution_time_ms for m in recent]) if recent else 0,
            "is_efficient": recent[-1].is_efficient if recent else False,
            "metrics_count": len(self.trading_metrics)
        }

    def profile_function(self, name: str):
        """Decorator to profile function performance."""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                self.profiler.start_profile(name)
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    self.profiler.stop_profile(name)
            return wrapper
        return decorator

    def export_metrics(self, format: str = 'json') -> str:
        """Export performance metrics."""
        summary = self.get_performance_summary()

        if format == 'json':
            return json.dumps(summary, indent=2, default=str)
        elif format == 'csv':
            # Implement CSV export
            return "CSV export not implemented"
        else:
            raise ValueError(f"Unsupported format: {format}")

    def clear_metrics(self) -> None:
        """Clear all performance metrics."""
        self.system_metrics.clear()
        self.application_metrics.clear()
        self.trading_metrics.clear()
        self.profiler.clear_profiles()
        logger.info("All performance metrics cleared")


# Global performance monitor instance
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


def profile_function(name: str):
    """Decorator to profile function performance."""
    return get_performance_monitor().profile_function(name)


def get_performance_summary() -> dict[str, Any]:
    """Get performance summary."""
    return get_performance_monitor().get_performance_summary()


def start_profiling(name: str) -> None:
    """Start profiling for a named operation."""
    get_performance_monitor().profiler.start_profile(name)


def stop_profiling(name: str) -> pstats.Stats:
    """Stop profiling and return statistics."""
    return get_performance_monitor().profiler.stop_profile(name)
