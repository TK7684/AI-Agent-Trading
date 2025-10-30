"""
Shared trading data models and contracts.

This module provides Pydantic models for trading data structures
that are shared between Python and Rust components.
"""

from .base import BaseModel
from .enums import (
    Direction,
    MarketRegime,
    OrderStatus,
    OrderType,
    PatternType,
    Timeframe,
    TradingAction,
)
from .llm_integration import (
    CircuitBreaker,
    ClaudeClient,
    GeminiClient,
    GPT4TurboClient,
    LlamaClient,
    LLMClient,
    LLMRequest,
    LLMResponse,
    MixtralClient,
    ModelMetrics,
    ModelPerformanceTracker,
    ModelProvider,
    MultiLLMRouter,
    PromptGenerator,
    RoutingPolicy,
)
from .market_data import IndicatorSnapshot, MarketBar
from .memory_learning import (
    BanditAlgorithm,
    MemoryLearningSystem,
    MultiArmedBandit,
    PatternPerformance,
    PerformanceWindow,
    TradeOutcome,
)
from .migrations import BackupManager, DataReplaySystem, MigrationManager
from .orders import ExecutionResult, OrderDecision
from .patterns import PatternCollection, PatternHit
from .persistence import (
    AuditLog,
    AuditLogModel,
    DatabaseManager,
    DecisionContext,
    JournalEntry,
    JSONJournal,
    MarketSnapshot,
    PerformanceMetric,
    PerformanceMetricModel,
    PersistenceManager,
    PositionRecord,
    PositionRecordModel,
    StructuredLogger,
    TradeRecord,
    TradeRecordModel,
)
from .risk_management import (
    CorrelationMonitor,
    DrawdownProtection,
    PortfolioMetrics,
    Position,
    PositionSizer,
    RiskAssessment,
    RiskLimits,
    RiskManager,
    SafeMode,
    StopLossManager,
    StopType,
)
from .signals import LLMAnalysis, Signal, TimeframeAnalysis

__all__ = [
    "MarketBar",
    "IndicatorSnapshot",
    "PatternHit",
    "PatternCollection",
    "Signal",
    "TimeframeAnalysis",
    "LLMAnalysis",
    "OrderDecision",
    "ExecutionResult",
    "Timeframe",
    "TradingAction",
    "Direction",
    "OrderType",
    "OrderStatus",
    "PatternType",
    "MarketRegime",
    "BaseModel",
    # LLM Integration
    "MultiLLMRouter",
    "LLMRequest",
    "LLMResponse",
    "ModelMetrics",
    "RoutingPolicy",
    "ModelProvider",
    "CircuitBreaker",
    "PromptGenerator",
    "ModelPerformanceTracker",
    "LLMClient",
    "ClaudeClient",
    "GeminiClient",
    "GPT4TurboClient",
    "MixtralClient",
    "LlamaClient",
    # Risk Management
    "RiskManager",
    "RiskAssessment",
    "RiskLimits",
    "Position",
    "PositionSizer",
    "CorrelationMonitor",
    "DrawdownProtection",
    "StopLossManager",
    "PortfolioMetrics",
    "SafeMode",
    "StopType",
    # Memory Learning
    "TradeOutcome",
    "PatternPerformance",
    "PerformanceWindow",
    "MultiArmedBandit",
    "BanditAlgorithm",
    "MemoryLearningSystem",
    # Persistence & Audit Logging
    "DatabaseManager",
    "JSONJournal",
    "StructuredLogger",
    "PersistenceManager",
    "TradeRecordModel",
    "PositionRecordModel",
    "PerformanceMetricModel",
    "AuditLogModel",
    "JournalEntry",
    "MarketSnapshot",
    "DecisionContext",
    "TradeRecord",
    "PositionRecord",
    "PerformanceMetric",
    "AuditLog",
    "MigrationManager",
    "BackupManager",
    "DataReplaySystem",
]
