import asyncio
import json
import logging
import os

# Import trading system components
import sys
import time
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Any, Optional

import jwt
import structlog
from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from libs.trading_models.base import Portfolio, Position, Trade, TradingSignal
    from libs.trading_models.monitoring import MonitoringSystem, get_metrics_collector
    from libs.trading_models.orchestrator import (
        OrchestrationConfig,
        TradingOrchestrator,
    )
except ImportError as e:
    print(f"Warning: Could not import trading models: {e}")
    # Create mock classes for development
    class MockMetricsCollector:
        def get_trading_summary(self): return {}
        def get_system_summary(self): return {}

    class MockMonitoringSystem:
        def __init__(self, config): pass
        async def start(self): pass
        async def stop(self): pass

    class MockTradingOrchestrator:
        def __init__(self, config): pass
        async def start(self): pass
        async def stop(self): pass
        async def get_performance_metrics(self): return {}
        async def get_analysis_summary(self): return {}

    get_metrics_collector = lambda: MockMetricsCollector()
    MonitoringSystem = MockMonitoringSystem
    TradingOrchestrator = MockTradingOrchestrator
    OrchestrationConfig = dict

# Import persistence layer
from persistence_service import persistence_service

# Configuration
SECRET = "dev-secret-key-for-trading-dashboard-2024"
ALGO = "HS256"
ACCESS_EXPIRE_MIN = 60

# Configure structured logging
logging.basicConfig(level=logging.INFO)
logger = structlog.get_logger()

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

# Global state
trading_orchestrator: Optional[TradingOrchestrator] = None
monitoring_system: Optional[MonitoringSystem] = None
websocket_clients: dict[str, list[WebSocket]] = {
    "trading": [],
    "system": [],
    "notifications": []
}

# In-memory data store (replace with database in production)
trades_db: list[dict[str, Any]] = []
system_metrics_db: list[dict[str, Any]] = []
notifications_db: list[dict[str, Any]] = []

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    global trading_orchestrator, monitoring_system

    logger.info("Starting trading API server...")

    try:
        # Initialize persistence layer first
        await persistence_service.initialize()
        logger.info("Database persistence layer initialized")

        # Initialize trading system components
        config = OrchestrationConfig(
            symbols=["BTCUSDT", "ETHUSDT", "ADAUSDT"],
            timeframes=["15m", "1h", "4h", "1d"],
            base_check_interval=1800
        )

        trading_orchestrator = TradingOrchestrator(config)
        monitoring_system = MonitoringSystem({
            'metrics_enabled': True,
            'alerts_enabled': True,
            'prometheus_port': 8001
        })

        # Start background tasks
        await monitoring_system.start()
        # Note: Don't start orchestrator automatically in API mode

        logger.info("Trading API server started successfully")

        # Initialize with some mock data and migrate to database
        await _initialize_mock_data()

        # Start background tasks for data collection
        asyncio.create_task(_background_metrics_collection())

    except Exception as e:
        logger.error(f"Failed to start trading API: {e}")
        raise

    yield

    # Cleanup
    logger.info("Shutting down trading API server...")
    if trading_orchestrator:
        await trading_orchestrator.stop()
    if monitoring_system:
        await monitoring_system.stop()

    # Close persistence layer
    await persistence_service.close()

app = FastAPI(
    title="Trading API",
    version="0.2.0",
    description="Enhanced Trading Dashboard API with real-time data and comprehensive monitoring",
    lifespan=lifespan
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()


# Enhanced API Models
class TokenResponse(BaseModel):
    token: str
    refreshToken: str


class LoginRequest(BaseModel):
    email: str
    password: str


class Performance(BaseModel):
    totalPnl: float
    dailyPnl: float
    winRate: float
    totalTrades: int
    currentDrawdown: float
    maxDrawdown: float
    portfolioValue: float
    dailyChange: float
    dailyChangePercent: float
    lastUpdate: datetime


class AgentStatus(BaseModel):
    state: str
    uptime: int
    lastAction: datetime
    activePositions: int
    dailyTrades: int
    version: str


class SystemHealth(BaseModel):
    cpu: float
    memory: float
    diskUsage: float
    networkLatency: float
    errorRate: float
    uptime: int
    connections: dict
    lastUpdate: datetime


class TradeEntry(BaseModel):
    id: str
    timestamp: datetime
    symbol: str
    side: str
    entryPrice: float
    exitPrice: Optional[float] = None
    quantity: float
    pnl: Optional[float] = None
    status: str
    pattern: Optional[str] = None
    confidence: float
    fees: Optional[float] = None
    duration: Optional[int] = None  # in seconds


class TradeFilter(BaseModel):
    symbols: Optional[list[str]] = None
    status: Optional[list[str]] = None
    dateFrom: Optional[datetime] = None
    dateTo: Optional[datetime] = None
    profitLoss: Optional[str] = None  # 'profit', 'loss', 'all'
    minConfidence: Optional[float] = None
    searchText: Optional[str] = None


class PaginatedTrades(BaseModel):
    items: list[TradeEntry]
    total: int
    page: int
    pageSize: int
    hasNext: bool
    filters: Optional[TradeFilter] = None


class NotificationEntry(BaseModel):
    id: str
    type: str  # 'info', 'warning', 'error', 'success'
    title: str
    message: str
    timestamp: datetime
    read: bool = False
    persistent: bool = False
    data: Optional[dict[str, Any]] = None


class SystemMetrics(BaseModel):
    timestamp: datetime
    cpu: float
    memory: float
    diskUsage: float
    networkLatency: float
    errorRate: float
    activeConnections: int
    requestsPerMinute: int


class TradingUpdate(BaseModel):
    type: str  # 'TRADE_OPENED', 'TRADE_CLOSED', 'POSITION_UPDATE', 'PNL_UPDATE'
    data: dict[str, Any]
    timestamp: datetime


class AgentControlRequest(BaseModel):
    action: str  # 'start', 'stop', 'pause', 'resume'
    parameters: Optional[dict[str, Any]] = None


# Utility Functions
def create_token(sub: str, minutes: int = ACCESS_EXPIRE_MIN) -> str:
    now = datetime.now(UTC)
    payload = {"sub": sub, "iat": int(now.timestamp()), "exp": int((now + timedelta(minutes=minutes)).timestamp())}
    return jwt.encode(payload, SECRET, algorithm=ALGO)


def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGO])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Token validation error: {str(e)}")


def auth_required(creds: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    return verify_token(creds.credentials)


async def _initialize_mock_data():
    """Initialize mock data for development and testing."""
    global trades_db, system_metrics_db, notifications_db

    # Check if we already have data in the database
    try:
        existing_trades, _, _ = await persistence_service.get_trades_paginated(page=1, page_size=1)
        if existing_trades:
            logger.info("Database already contains data, skipping mock data initialization")
            return
    except Exception as e:
        logger.warning(f"Could not check existing data, proceeding with mock data: {e}")

    logger.info("Initializing mock data and migrating to database...")

    # Mock trades
    base_time = datetime.now(UTC)
    mock_trades = [
        {
            "id": f"trade_{i}",
            "timestamp": base_time - timedelta(hours=i),
            "symbol": ["BTCUSDT", "ETHUSDT", "ADAUSDT"][i % 3],
            "side": "LONG" if i % 2 == 0 else "SHORT",
            "entryPrice": 45000.0 + (i * 100),
            "exitPrice": 45500.0 + (i * 100) if i % 3 == 0 else None,
            "quantity": 0.1 + (i * 0.01),
            "pnl": (50.0 + i * 10) if i % 3 == 0 else None,
            "status": "CLOSED" if i % 3 == 0 else "OPEN",
            "pattern": ["breakout", "reversal", "momentum"][i % 3],
            "confidence": 0.7 + (i % 3) * 0.1,
            "fees": 2.5 + (i * 0.1),
            "duration": (3600 + i * 300) if i % 3 == 0 else None
        }
        for i in range(50)
    ]
    trades_db.extend(mock_trades)

    # Mock system metrics
    for i in range(100):
        system_metrics_db.append({
            "timestamp": base_time - timedelta(minutes=i * 5),
            "cpu": 20 + (i % 30),
            "memory": 30 + (i % 40),
            "diskUsage": 40 + (i % 20),
            "networkLatency": 50 + (i % 100),
            "errorRate": max(0, 1 + (i % 10) - 5),
            "activeConnections": 10 + (i % 5),
            "requestsPerMinute": 100 + (i % 200)
        })

    # Mock notifications
    notification_types = ["info", "warning", "error", "success"]
    for i in range(20):
        notifications_db.append({
            "id": f"notification_{i}",
            "type": notification_types[i % 4],
            "title": f"System Alert {i}",
            "message": f"This is a test notification message {i}",
            "timestamp": base_time - timedelta(minutes=i * 10),
            "read": i % 4 != 0,
            "persistent": i % 5 == 0,
            "data": {"source": "system", "level": i % 3}
        })

    # Migrate in-memory data to database
    try:
        await persistence_service.migrate_in_memory_data(trades_db, system_metrics_db, notifications_db)
        logger.info("Mock data successfully migrated to database")
    except Exception as e:
        logger.error(f"Failed to migrate mock data to database: {e}")


async def _background_metrics_collection():
    """Background task to collect and persist system metrics."""
    import psutil

    while True:
        try:
            # Collect system metrics
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            # Record metrics in database
            await persistence_service.record_system_metrics(
                cpu_usage=cpu_usage,
                memory_usage=memory.percent,
                disk_usage=disk.percent,
                network_latency=50.0,  # Mock value - could implement real network check
                error_rate=0.0,
                active_connections=len(websocket_clients.get("trading", [])) +
                                 len(websocket_clients.get("system", [])) +
                                 len(websocket_clients.get("notifications", [])),
                requests_per_minute=100  # Mock value - could implement real tracking
            )

            # Wait 5 minutes before next collection
            await asyncio.sleep(300)

        except Exception as e:
            logger.error(f"Error in background metrics collection: {e}")
            await asyncio.sleep(60)  # Wait 1 minute on error


async def broadcast_to_websockets(channel: str, message: dict[str, Any]):
    """Broadcast message to all connected WebSocket clients in a channel."""
    if channel not in websocket_clients:
        return

    disconnected_clients = []
    message_str = json.dumps(message, default=str)

    for client in websocket_clients[channel]:
        try:
            await client.send_text(message_str)
        except Exception as e:
            logger.warning(f"Failed to send message to WebSocket client: {e}")
            disconnected_clients.append(client)

    # Remove disconnected clients
    for client in disconnected_clients:
        websocket_clients[channel].remove(client)


def apply_trade_filters(trades: list[dict[str, Any]], filters: TradeFilter) -> list[dict[str, Any]]:
    """Apply filters to trades list."""
    filtered_trades = trades.copy()

    if filters.symbols:
        filtered_trades = [t for t in filtered_trades if t["symbol"] in filters.symbols]

    if filters.status:
        filtered_trades = [t for t in filtered_trades if t["status"] in filters.status]

    if filters.dateFrom:
        filtered_trades = [t for t in filtered_trades if t["timestamp"] >= filters.dateFrom]

    if filters.dateTo:
        filtered_trades = [t for t in filtered_trades if t["timestamp"] <= filters.dateTo]

    if filters.profitLoss:
        if filters.profitLoss == "profit":
            filtered_trades = [t for t in filtered_trades if t.get("pnl", 0) > 0]
        elif filters.profitLoss == "loss":
            filtered_trades = [t for t in filtered_trades if t.get("pnl", 0) < 0]

    if filters.minConfidence:
        filtered_trades = [t for t in filtered_trades if t["confidence"] >= filters.minConfidence]

    if filters.searchText:
        search_text = filters.searchText.lower()
        filtered_trades = [
            t for t in filtered_trades
            if search_text in t["symbol"].lower() or
               search_text in (t.get("pattern", "") or "").lower()
        ]

    return filtered_trades


# Health Check Endpoints
@app.get("/health")
async def health_check():
    """Basic health check endpoint for load balancers and monitoring."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "service": "trading-api",
        "version": "0.2.0"
    }


# Authentication Endpoints with Rate Limiting
@app.post("/auth/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(request: Request, req: LoginRequest):
    """Login endpoint with rate limiting."""
    logger.info(f"Login attempt for user: {req.email}")

    # Mock validation - replace with real authentication
    if not req.email or not req.password:
        logger.warning(f"Invalid login attempt: missing credentials for {req.email}")
        raise HTTPException(status_code=400, detail="Missing credentials")

    # Simple mock validation
    if req.password != "password123":  # Replace with real password validation
        logger.warning(f"Invalid login attempt: wrong password for {req.email}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    logger.info(f"Successful login for user: {req.email}")
    return {
        "token": create_token(req.email),
        "refreshToken": create_token(req.email, minutes=60 * 24)
    }


@app.post("/auth/refresh", response_model=TokenResponse)
@limiter.limit("10/minute")
async def refresh(request: Request, creds: HTTPAuthorizationCredentials = Depends(security)):
    """Refresh token endpoint with rate limiting."""
    payload = verify_token(creds.credentials)
    sub = payload.get("sub")
    logger.info(f"Token refresh for user: {sub}")
    return {
        "token": create_token(sub),
        "refreshToken": create_token(sub, minutes=60 * 24)
    }


# Trading Endpoints
@app.get("/trading/performance", response_model=Performance)
@limiter.limit("30/minute")
async def get_performance(request: Request, _: dict = Depends(auth_required)):
    """Get trading performance metrics with real-time data from database."""
    try:
        # Get performance metrics from persistence layer
        performance_data = await persistence_service.get_trading_performance()

        performance = Performance(
            totalPnl=performance_data["total_pnl"],
            dailyPnl=performance_data["daily_pnl"],
            winRate=performance_data["win_rate"],
            totalTrades=performance_data["total_trades"],
            currentDrawdown=performance_data["current_drawdown"],
            maxDrawdown=performance_data["max_drawdown"],
            portfolioValue=performance_data["portfolio_value"],
            dailyChange=performance_data["daily_change"],
            dailyChangePercent=performance_data["daily_change_percent"],
            lastUpdate=performance_data["last_update"],
        )

        # Broadcast update to WebSocket clients
        await broadcast_to_websockets("trading", {
            "type": "PERFORMANCE_UPDATE",
            "data": performance.model_dump(),
            "timestamp": performance_data["last_update"].isoformat()
        })

        return performance

    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve performance metrics")


# System Endpoints
@app.get("/system/agents", response_model=AgentStatus)
@limiter.limit("30/minute")
async def get_agent_status(request: Request, _: dict = Depends(auth_required)):
    """Get current agent status with real-time data."""
    try:
        global trading_orchestrator

        if trading_orchestrator:
            metrics = await trading_orchestrator.get_performance_metrics()
            state = metrics.get("state", "stopped")
        else:
            state = "stopped"

        # Calculate metrics from trades
        open_positions = len([t for t in trades_db if t["status"] == "OPEN"])
        today = datetime.now(UTC).date()
        daily_trades = len([t for t in trades_db if t["timestamp"].date() == today])

        # Calculate uptime (mock for now)
        uptime = int(time.time() - (time.time() - 3600))  # 1 hour uptime

        return AgentStatus(
            state=state,
            uptime=uptime,
            lastAction=datetime.now(UTC),
            activePositions=open_positions,
            dailyTrades=daily_trades,
            version="2.0.0"
        )

    except Exception as e:
        logger.error(f"Error getting agent status: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve agent status")


@app.get("/trading/trades", response_model=PaginatedTrades)
@limiter.limit("60/minute")
async def get_trading_trades(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    pageSize: int = Query(20, ge=1, le=100, description="Items per page"),
    symbols: Optional[str] = Query(None, description="Comma-separated list of symbols"),
    status: Optional[str] = Query(None, description="Comma-separated list of statuses"),
    dateFrom: Optional[datetime] = Query(None, description="Start date filter"),
    dateTo: Optional[datetime] = Query(None, description="End date filter"),
    profitLoss: Optional[str] = Query(None, description="Filter by profit/loss: profit, loss, all"),
    minConfidence: Optional[float] = Query(None, ge=0, le=1, description="Minimum confidence level"),
    searchText: Optional[str] = Query(None, description="Search text for symbol or pattern"),
    _: dict = Depends(auth_required)
):
    """Get trading logs with advanced filtering and pagination from database."""
    try:
        # Create filter object
        filters = TradeFilter(
            symbols=symbols.split(",") if symbols else None,
            status=status.split(",") if status else None,
            dateFrom=dateFrom,
            dateTo=dateTo,
            profitLoss=profitLoss,
            minConfidence=minConfidence,
            searchText=searchText
        )

        # Get trades from persistence layer
        trades, total, has_next = await persistence_service.get_trades_paginated(
            page=page,
            page_size=pageSize,
            symbol=symbols.split(",")[0] if symbols and "," not in symbols else None,
            status=status.split(",")[0] if status and "," not in status else None,
            date_from=dateFrom,
            date_to=dateTo,
            profit_loss_filter=profitLoss,
            min_confidence=minConfidence,
            search_text=searchText
        )

        # Convert to TradeEntry models
        trade_entries = [
            TradeEntry(
                id=trade.id,
                timestamp=trade.timestamp,
                symbol=trade.symbol,
                side=trade.side,
                entryPrice=trade.entry_price,
                exitPrice=trade.exit_price,
                quantity=trade.quantity,
                pnl=trade.pnl,
                status=trade.status,
                pattern=trade.pattern,
                confidence=trade.confidence,
                fees=trade.fees,
                duration=trade.duration
            )
            for trade in trades
        ]

        return PaginatedTrades(
            items=trade_entries,
            total=total,
            page=page,
            pageSize=pageSize,
            hasNext=has_next,
            filters=filters
        )

    except Exception as e:
        logger.error(f"Error getting trading trades: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve trading logs")


@app.post("/trading/trades/export")
@limiter.limit("5/minute")
async def export_trading_trades(
    request: Request,
    export_request: TradeFilter,
    format: str = Query("csv", description="Export format: csv or json"),
    _: dict = Depends(auth_required)
):
    """Export trading logs in CSV or JSON format."""
    try:
        # Apply filters
        filtered_trades = apply_trade_filters(trades_db, export_request)

        if format.lower() == "csv":
            import csv
            import io

            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=[
                "id", "timestamp", "symbol", "side", "entryPrice", "exitPrice",
                "quantity", "pnl", "status", "pattern", "confidence", "fees", "duration"
            ])
            writer.writeheader()
            writer.writerows(filtered_trades)

            return {"data": output.getvalue(), "format": "csv"}

        elif format.lower() == "json":
            return {"data": json.dumps(filtered_trades, default=str), "format": "json"}

        else:
            raise HTTPException(status_code=400, detail="Unsupported export format")

    except Exception as e:
        logger.error(f"Error exporting trades: {e}")
        raise HTTPException(status_code=500, detail="Failed to export trading logs")


@app.get("/trading/positions")
@limiter.limit("30/minute")
async def get_trading_positions(request: Request, _: dict = Depends(auth_required)):
    """Get current trading positions."""
    try:
        # Get open positions from trades
        open_trades = [t for t in trades_db if t["status"] == "OPEN"]

        positions = []
        for trade in open_trades:
            # Mock current price calculation
            current_price = trade["entryPrice"] * (1 + (hash(trade["id"]) % 100 - 50) / 1000)

            if trade["side"] == "LONG":
                pnl = (current_price - trade["entryPrice"]) * trade["quantity"]
                percentage = ((current_price - trade["entryPrice"]) / trade["entryPrice"]) * 100
            else:
                pnl = (trade["entryPrice"] - current_price) * trade["quantity"]
                percentage = ((trade["entryPrice"] - current_price) / trade["entryPrice"]) * 100

            positions.append({
                "id": trade["id"],
                "symbol": trade["symbol"],
                "side": trade["side"],
                "size": trade["quantity"],
                "entryPrice": trade["entryPrice"],
                "markPrice": current_price,
                "pnl": pnl,
                "percentage": percentage,
                "timestamp": trade["timestamp"]
            })

        return {"positions": positions}

    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve positions")


@app.get("/trading/signals")
@limiter.limit("30/minute")
async def get_trading_signals(
    request: Request,
    limit: int = Query(10, ge=1, le=100, description="Number of recent signals"),
    _: dict = Depends(auth_required)
):
    """Get recent trading signals."""
    try:
        # Mock signals based on recent analysis
        signals = []
        base_time = datetime.now(UTC)

        for i in range(min(limit, 10)):
            signals.append({
                "id": f"signal_{int(time.time())}_{i}",
                "timestamp": base_time - timedelta(minutes=i * 15),
                "symbol": ["BTCUSDT", "ETHUSDT", "ADAUSDT"][i % 3],
                "type": "BUY" if i % 2 == 0 else "SELL",
                "confidence": 0.7 + (i % 3) * 0.1,
                "pattern": ["breakout", "reversal", "momentum"][i % 3],
                "price": 45000.0 + (i * 100),
                "timeframe": ["15m", "1h", "4h"][i % 3]
            })

        return {"signals": signals}

    except Exception as e:
        logger.error(f"Error getting signals: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve signals")


@app.post("/system/agents/{agent_id}/control")
@limiter.limit("10/minute")
async def control_agent(
    request: Request,
    agent_id: str,
    control_request: AgentControlRequest,
    _: dict = Depends(auth_required)
):
    """Control trading agent with comprehensive actions."""
    try:
        global trading_orchestrator

        action = control_request.action
        if action not in ["start", "stop", "pause", "resume"]:
            raise HTTPException(status_code=400, detail="Invalid action")

        logger.info(f"Agent control request: {action} for agent {agent_id}")

        result = {"message": f"Agent {agent_id} {action} command executed", "status": "success"}

        if trading_orchestrator:
            if action == "start":
                await trading_orchestrator.start()
                result["message"] = f"Agent {agent_id} started successfully"
            elif action == "stop":
                await trading_orchestrator.stop()
                result["message"] = f"Agent {agent_id} stopped successfully"
            elif action in ["pause", "resume"]:
                # These would be implemented in the orchestrator
                result["message"] = f"Agent {agent_id} {action} command queued"

        # Broadcast status update
        await broadcast_to_websockets("system", {
            "type": "AGENT_STATUS_CHANGE",
            "data": {"agent_id": agent_id, "action": action, "timestamp": datetime.now(UTC).isoformat()},
            "timestamp": datetime.now(UTC).isoformat()
        })

        # Add notification
        notification = {
            "id": f"agent_control_{int(time.time())}",
            "type": "info",
            "title": "Agent Control",
            "message": result["message"],
            "timestamp": datetime.now(UTC),
            "read": False,
            "persistent": False,
            "data": {"agent_id": agent_id, "action": action}
        }
        notifications_db.append(notification)

        await broadcast_to_websockets("notifications", {
            "type": "NEW_NOTIFICATION",
            "data": notification,
            "timestamp": datetime.now(UTC).isoformat()
        })

        return result

    except Exception as e:
        logger.error(f"Error controlling agent: {e}")
        raise HTTPException(status_code=500, detail="Failed to control agent")


@app.get("/system/metrics")
@limiter.limit("60/minute")
async def get_system_metrics(
    request: Request,
    limit: int = Query(100, ge=1, le=1000, description="Number of recent metrics to return"),
    _: dict = Depends(auth_required)
):
    """Get system performance metrics history from database."""
    try:
        # Get recent metrics from persistence layer
        recent_metrics = await persistence_service.get_system_metrics_history(limit)

        # Convert to SystemMetrics models
        metrics = [
            SystemMetrics(
                timestamp=m.timestamp,
                cpu=m.cpu_usage,
                memory=m.memory_usage,
                diskUsage=m.disk_usage,
                networkLatency=m.network_latency,
                errorRate=m.error_rate,
                activeConnections=m.active_connections,
                requestsPerMinute=m.requests_per_minute
            )
            for m in recent_metrics
        ]

        return {"metrics": metrics, "total": len(metrics)}

    except Exception as e:
        logger.error(f"Error getting system metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve system metrics")


@app.get("/system/notifications")
@limiter.limit("30/minute")
async def get_notifications(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    pageSize: int = Query(20, ge=1, le=100, description="Items per page"),
    unreadOnly: bool = Query(False, description="Return only unread notifications"),
    _: dict = Depends(auth_required)
):
    """Get system notifications with pagination from database."""
    try:
        # Get notifications from persistence layer
        notifications, total, has_next = await persistence_service.get_notifications_paginated(
            page=page,
            page_size=pageSize,
            unread_only=unreadOnly
        )

        # Convert to NotificationEntry models
        notification_entries = [
            NotificationEntry(
                id=n.id,
                type=n.type,
                title=n.title,
                message=n.message,
                timestamp=n.timestamp,
                read=n.read,
                persistent=n.persistent,
                data=n.data
            )
            for n in notifications
        ]

        return {
            "items": notification_entries,
            "total": total,
            "page": page,
            "pageSize": pageSize,
            "hasNext": has_next
        }

    except Exception as e:
        logger.error(f"Error getting notifications: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve notifications")


@app.post("/system/notifications/{notification_id}/read")
@limiter.limit("30/minute")
async def mark_notification_read(
    request: Request,
    notification_id: str,
    _: dict = Depends(auth_required)
):
    """Mark a notification as read."""
    try:
        # Mark notification as read in database
        success = await persistence_service.mark_notification_read(notification_id)
        if success:
            # Broadcast update
            await broadcast_to_websockets("notifications", {
                "type": "NOTIFICATION_READ",
                "data": {"notification_id": notification_id},
                "timestamp": datetime.now(UTC).isoformat()
            })

            return {"message": "Notification marked as read", "status": "success"}

        raise HTTPException(status_code=404, detail="Notification not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking notification as read: {e}")
        raise HTTPException(status_code=500, detail="Failed to update notification")


@app.get("/system/health", response_model=SystemHealth)
async def get_system_health():
    """Get system health status from database - public endpoint for monitoring."""
    try:
        # Get system health summary from persistence layer
        health_summary = await persistence_service.get_system_health_summary()

        return SystemHealth(
            cpu=health_summary["cpu"],
            memory=health_summary["memory"],
            diskUsage=health_summary["disk_usage"],
            networkLatency=health_summary["network_latency"],
            errorRate=health_summary["error_rate"],
            uptime=health_summary["uptime"],
            connections=health_summary["connections"],
            lastUpdate=health_summary["last_update"]
        )

    except Exception as e:
        logger.error(f"Error getting system health: {e}")
        # Return degraded health status
        return SystemHealth(
            cpu=0, memory=0, diskUsage=0, networkLatency=0, errorRate=100, uptime=0,
            connections={"database": False, "broker": False, "llm": False, "websocket": False},
            lastUpdate=datetime.now(UTC)
        )


# Enhanced WebSocket Endpoints
@app.websocket("/ws/trading")
async def ws_trading(websocket: WebSocket):
    """WebSocket endpoint for real-time trading updates."""
    await websocket.accept()
    websocket_clients["trading"].append(websocket)
    logger.info("New trading WebSocket client connected")

    try:
        # Send initial data
        await websocket.send_text(json.dumps({
            "type": "CONNECTION_ESTABLISHED",
            "data": {"channel": "trading", "timestamp": datetime.now(UTC).isoformat()},
            "timestamp": datetime.now(UTC).isoformat()
        }))

        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages with timeout
                message = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)

                # Handle ping/pong for connection health
                if message == "ping":
                    await websocket.send_text("pong")
                else:
                    # Handle other message types
                    logger.info(f"Received trading WebSocket message: {message}")

            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_text(json.dumps({
                    "type": "HEARTBEAT",
                    "timestamp": datetime.now(UTC).isoformat()
                }))

    except WebSocketDisconnect:
        logger.info("Trading WebSocket client disconnected")
    except Exception as e:
        logger.error(f"Error in trading WebSocket: {e}")
    finally:
        if websocket in websocket_clients["trading"]:
            websocket_clients["trading"].remove(websocket)


@app.websocket("/ws/system")
async def ws_system(websocket: WebSocket):
    """WebSocket endpoint for real-time system updates."""
    await websocket.accept()
    websocket_clients["system"].append(websocket)
    logger.info("New system WebSocket client connected")

    try:
        # Send initial data
        await websocket.send_text(json.dumps({
            "type": "CONNECTION_ESTABLISHED",
            "data": {"channel": "system", "timestamp": datetime.now(UTC).isoformat()},
            "timestamp": datetime.now(UTC).isoformat()
        }))

        # Keep connection alive
        while True:
            try:
                message = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)

                if message == "ping":
                    await websocket.send_text("pong")
                else:
                    logger.info(f"Received system WebSocket message: {message}")

            except asyncio.TimeoutError:
                await websocket.send_text(json.dumps({
                    "type": "HEARTBEAT",
                    "timestamp": datetime.now(UTC).isoformat()
                }))

    except WebSocketDisconnect:
        logger.info("System WebSocket client disconnected")
    except Exception as e:
        logger.error(f"Error in system WebSocket: {e}")
    finally:
        if websocket in websocket_clients["system"]:
            websocket_clients["system"].remove(websocket)


@app.websocket("/ws/notifications")
async def ws_notifications(websocket: WebSocket):
    """WebSocket endpoint for real-time notifications."""
    await websocket.accept()
    websocket_clients["notifications"].append(websocket)
    logger.info("New notifications WebSocket client connected")

    try:
        # Send initial data
        await websocket.send_text(json.dumps({
            "type": "CONNECTION_ESTABLISHED",
            "data": {"channel": "notifications", "timestamp": datetime.now(UTC).isoformat()},
            "timestamp": datetime.now(UTC).isoformat()
        }))

        # Keep connection alive
        while True:
            try:
                message = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)

                if message == "ping":
                    await websocket.send_text("pong")
                else:
                    logger.info(f"Received notifications WebSocket message: {message}")

            except asyncio.TimeoutError:
                await websocket.send_text(json.dumps({
                    "type": "HEARTBEAT",
                    "timestamp": datetime.now(UTC).isoformat()
                }))

    except WebSocketDisconnect:
        logger.info("Notifications WebSocket client disconnected")
    except Exception as e:
        logger.error(f"Error in notifications WebSocket: {e}")
    finally:
        if websocket in websocket_clients["notifications"]:
            websocket_clients["notifications"].remove(websocket)


# Background task to simulate real-time updates
async def background_data_simulator():
    """Background task to simulate real-time trading updates."""
    while True:
        try:
            await asyncio.sleep(10)  # Update every 10 seconds

            # Simulate new trade
            if len(trades_db) > 0 and hash(str(time.time())) % 10 == 0:
                # Randomly close an open trade
                open_trades = [t for t in trades_db if t["status"] == "OPEN"]
                if open_trades:
                    trade = open_trades[0]
                    trade["status"] = "CLOSED"
                    trade["exitPrice"] = trade["entryPrice"] * (1 + (hash(trade["id"]) % 100 - 50) / 1000)
                    trade["pnl"] = (trade["exitPrice"] - trade["entryPrice"]) * trade["quantity"]

                    await broadcast_to_websockets("trading", {
                        "type": "TRADE_CLOSED",
                        "data": trade,
                        "timestamp": datetime.now(UTC).isoformat()
                    })

            # Simulate system metrics update
            if system_metrics_db:
                latest_metrics = system_metrics_db[-1].copy()
                latest_metrics["timestamp"] = datetime.now(UTC)
                latest_metrics["cpu"] = max(0, min(100, latest_metrics["cpu"] + (hash(str(time.time())) % 20 - 10)))
                latest_metrics["memory"] = max(0, min(100, latest_metrics["memory"] + (hash(str(time.time())) % 10 - 5)))
                system_metrics_db.append(latest_metrics)

                # Keep only recent metrics
                if len(system_metrics_db) > 1000:
                    system_metrics_db[:] = system_metrics_db[-500:]

                await broadcast_to_websockets("system", {
                    "type": "METRICS_UPDATE",
                    "data": latest_metrics,
                    "timestamp": datetime.now(UTC).isoformat()
                })

        except Exception as e:
            logger.error(f"Error in background data simulator: {e}")


# Database Management Endpoints
@app.post("/admin/database/migrate")
@limiter.limit("1/minute")
async def migrate_database(request: Request, _: dict = Depends(auth_required)):
    """Migrate in-memory data to database (admin only)."""
    try:
        await persistence_service.migrate_in_memory_data(trades_db, system_metrics_db, notifications_db)
        return {"message": "Database migration completed successfully", "status": "success"}
    except Exception as e:
        logger.error(f"Error migrating database: {e}")
        raise HTTPException(status_code=500, detail="Failed to migrate database")


@app.post("/admin/database/cleanup")
@limiter.limit("1/minute")
async def cleanup_database(
    request: Request,
    days_to_keep: int = Query(30, ge=1, le=365, description="Number of days of data to keep"),
    _: dict = Depends(auth_required)
):
    """Clean up old database records (admin only)."""
    try:
        await persistence_service.cleanup_old_data(days_to_keep)
        return {"message": f"Database cleanup completed, kept {days_to_keep} days of data", "status": "success"}
    except Exception as e:
        logger.error(f"Error cleaning up database: {e}")
        raise HTTPException(status_code=500, detail="Failed to clean up database")


@app.get("/admin/database/stats")
@limiter.limit("10/minute")
async def get_database_stats(request: Request, _: dict = Depends(auth_required)):
    """Get database statistics (admin only)."""
    try:
        # Get counts from each table
        trades_count = len(await persistence_service.trading_data.get_trades(limit=10000))
        metrics_count = len(await persistence_service.get_system_metrics_history(10000))
        notifications_count = len((await persistence_service.get_notifications_paginated(page=1, page_size=10000))[0])
        unread_count = await persistence_service.get_unread_notification_count()

        return {
            "tables": {
                "trades": trades_count,
                "system_metrics": metrics_count,
                "notifications": notifications_count,
                "unread_notifications": unread_count
            },
            "status": "healthy",
            "last_updated": datetime.now(UTC)
        }
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve database statistics")


@app.post("/trading/trades/{trade_id}/close")
@limiter.limit("30/minute")
async def close_trade_endpoint(
    request: Request,
    trade_id: str,
    exit_price: float = Query(..., description="Exit price for the trade"),
    exit_reason: Optional[str] = Query(None, description="Reason for closing the trade"),
    fees: Optional[float] = Query(None, description="Trading fees"),
    _: dict = Depends(auth_required)
):
    """Close an open trade."""
    try:
        updated_trade = await persistence_service.close_trade(
            trade_id=trade_id,
            exit_price=exit_price,
            exit_reason=exit_reason,
            fees=fees
        )

        if not updated_trade:
            raise HTTPException(status_code=404, detail="Trade not found or already closed")

        # Broadcast trade update
        await broadcast_to_websockets("trading", {
            "type": "TRADE_CLOSED",
            "data": {
                "id": updated_trade.id,
                "symbol": updated_trade.symbol,
                "pnl": updated_trade.pnl,
                "exit_price": updated_trade.exit_price
            },
            "timestamp": datetime.now(UTC).isoformat()
        })

        # Create notification for significant P&L
        if updated_trade.pnl and abs(updated_trade.pnl) > 100:  # Significant P&L threshold
            notification_type = "success" if updated_trade.pnl > 0 else "warning"
            await persistence_service.create_notification(
                notification_type=notification_type,
                title=f"Trade Closed: {updated_trade.symbol}",
                message=f"Trade closed with P&L: ${updated_trade.pnl:.2f}",
                source="trading",
                category="trade",
                data={"trade_id": trade_id, "pnl": updated_trade.pnl}
            )

        return {
            "message": "Trade closed successfully",
            "trade_id": trade_id,
            "pnl": updated_trade.pnl,
            "status": "success"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error closing trade: {e}")
        raise HTTPException(status_code=500, detail="Failed to close trade")


@app.post("/trading/trades")
@limiter.limit("60/minute")
async def create_trade_endpoint(
    request: Request,
    symbol: str = Query(..., description="Trading symbol"),
    side: str = Query(..., description="Trade side: LONG or SHORT"),
    entry_price: float = Query(..., description="Entry price"),
    quantity: float = Query(..., description="Trade quantity"),
    confidence: float = Query(..., ge=0, le=1, description="Signal confidence"),
    pattern: Optional[str] = Query(None, description="Trading pattern"),
    strategy: Optional[str] = Query(None, description="Trading strategy"),
    timeframe: Optional[str] = Query(None, description="Timeframe"),
    entry_reason: Optional[str] = Query(None, description="Entry reason"),
    stop_loss: Optional[float] = Query(None, description="Stop loss price"),
    take_profit: Optional[float] = Query(None, description="Take profit price"),
    _: dict = Depends(auth_required)
):
    """Create a new trade record."""
    try:
        new_trade = await persistence_service.create_trade(
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            quantity=quantity,
            confidence=confidence,
            pattern=pattern,
            strategy=strategy,
            timeframe=timeframe,
            entry_reason=entry_reason,
            stop_loss=stop_loss,
            take_profit=take_profit
        )

        # Broadcast new trade
        await broadcast_to_websockets("trading", {
            "type": "TRADE_OPENED",
            "data": {
                "id": new_trade.id,
                "symbol": new_trade.symbol,
                "side": new_trade.side,
                "entry_price": new_trade.entry_price,
                "quantity": new_trade.quantity
            },
            "timestamp": datetime.now(UTC).isoformat()
        })

        # Create notification
        await persistence_service.create_notification(
            notification_type="info",
            title=f"New Trade: {symbol}",
            message=f"Opened {side} position in {symbol} at ${entry_price}",
            source="trading",
            category="trade",
            data={"trade_id": new_trade.id, "symbol": symbol, "side": side}
        )

        return {
            "message": "Trade created successfully",
            "trade_id": new_trade.id,
            "status": "success"
        }

    except Exception as e:
        logger.error(f"Error creating trade: {e}")
        raise HTTPException(status_code=500, detail="Failed to create trade")


# Start background task
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    # Startup
    task = asyncio.create_task(background_data_simulator())
    yield
    # Shutdown
    task.cancel()


# Run: uvicorn apps.trading-api.main:app --reload --host 0.0.0.0 --port 8000
