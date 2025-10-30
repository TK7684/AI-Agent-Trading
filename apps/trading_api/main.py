import asyncio
from datetime import datetime, timedelta
from typing import Any, Optional

import jwt
from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

# Integrations with existing components
from libs.trading_models.monitoring import get_metrics_collector
from libs.trading_models.orchestrator import OrchestrationConfig, TradingOrchestrator

SECRET = "dev-secret-change"
ALGO = "HS256"
ACCESS_EXPIRE_MIN = 60

app = FastAPI(title="Trading API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()


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
    connections: dict[str, bool]
    lastUpdate: datetime


class AgentControlRequest(BaseModel):
    action: str  # start|stop|pause (pause is noop for now)


def create_token(sub: str, minutes: int = ACCESS_EXPIRE_MIN) -> str:
    now = datetime.utcnow()
    payload = {"sub": sub, "iat": int(now.timestamp()), "exp": int((now + timedelta(minutes=minutes)).timestamp())}
    return jwt.encode(payload, SECRET, algorithm=ALGO)


def verify_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET, algorithms=[ALGO])
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def auth_required(creds: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    return verify_token(creds.credentials)


# Global orchestrator
_orchestrator: Optional[TradingOrchestrator] = None
_ws_clients: set[WebSocket] = set()
_broadcast_task: Optional[asyncio.Task] = None


@app.on_event("startup")
async def startup() -> None:
    global _orchestrator, _broadcast_task

    print("🚀 Starting Trading API Server...")
    print("=" * 50)

    # Comprehensive database validation and setup
    await _initialize_database()

    # Initialize orchestrator with defaults
    if _orchestrator is None:
        _orchestrator = TradingOrchestrator(OrchestrationConfig())

    # Start periodic broadcaster for WS updates
    if _broadcast_task is None:
        _broadcast_task = asyncio.create_task(_broadcast_loop())

    print("✅ Trading API Server started successfully")
    print("=" * 50)


async def _initialize_database() -> None:
    """Initialize and validate database connection with comprehensive error handling."""
    import os

    from libs.trading_models.config_manager import ConfigurationManager
    from libs.trading_models.db_validator import DatabaseValidator
    from libs.trading_models.fallback_mode import get_fallback_mode

    print("🔍 Initializing database connection...")

    fallback_mode = get_fallback_mode()

    # Load configuration
    try:
        config_manager = ConfigurationManager()
        database_url = config_manager.get_database_url()
    except Exception as e:
        print(f"⚠️  Configuration error: {e}")
        database_url = os.getenv('DATABASE_URL')

    if not database_url:
        print("❌ DATABASE_URL not configured")
        print("\n📋 Setup Instructions:")
        print("   1. Run: .\\scripts\\Setup-Database.ps1")
        print("   2. Or manually update .env.local with DATABASE_URL")
        print("   3. See: QUICK-FIX-DATABASE.md for help")
        print("\n⚠️  Starting in FALLBACK MODE - limited functionality")
        fallback_mode.enable("DATABASE_URL not configured")
        return

    # Validate database connection
    validator = DatabaseValidator()
    print("   Testing connection...")

    result = validator.test_connection(database_url)

    if result.success:
        print("✅ Database connected successfully")
        print(f"   Connection time: {result.connection_time_ms:.2f}ms")
        if result.database_version:
            print(f"   PostgreSQL version: {result.database_version.split(',')[0]}")

        # Validate schema
        print("   Validating schema...")
        schema_validation = validator.validate_schema(database_url)

        if schema_validation.valid:
            print("✅ Database schema validated")
            print(f"   Tables found: {len(schema_validation.tables_found)}")
            if schema_validation.tables_found:
                print(f"   Available: {', '.join(schema_validation.tables_found)}")
        else:
            print("⚠️  Database schema incomplete")
            print(f"   Missing tables: {', '.join(schema_validation.tables_missing)}")
            print("\n📋 Schema Fix:")
            print("   Run: .\\scripts\\Create-DatabaseTables.ps1")
            print("   Or: .\\scripts\\Setup-Database.ps1")

            # Don't enable fallback mode for missing tables - system can still function
            # The persistence layer will handle missing tables gracefully

        # Test service status for informational purposes
        service_status = validator.test_service_running()
        if service_status.running:
            print(f"✅ PostgreSQL service running ({service_status.service_name or 'detected'})")

    else:
        print("❌ Database connection failed")
        print(f"   Error: {result.error_message}")
        print(f"   Type: {result.error_type}")

        # Provide specific guidance based on error type
        if result.error_type == "auth":
            print("\n🔧 Authentication Fix:")
            print("   1. Run: .\\scripts\\Setup-Database.ps1")
            print("   2. Or check your password in .env.local")
            print("   3. Or reset password: .\\scripts\\Reset-PostgreSQL-Password.ps1")
        elif result.error_type == "service":
            print("\n🔧 Service Fix:")
            print("   1. Start PostgreSQL: Start-Service postgresql-x64-17")
            print("   2. Or use Services.msc to start PostgreSQL")
            print("   3. Check Windows Event Logs for errors")
        elif result.error_type == "network":
            print("\n🔧 Network Fix:")
            print("   1. Verify PostgreSQL is running on localhost:5432")
            print("   2. Check firewall settings")
            print("   3. Test with: telnet localhost 5432")
        else:
            print("\n🔧 General Fix:")
            print(f"   {result.suggested_fix}")

        print("\n⚠️  Starting in FALLBACK MODE - limited functionality")
        fallback_mode.enable(f"Database {result.error_type} error: {result.error_message}")

    # Display fallback mode status if enabled
    if fallback_mode.is_enabled():
        print("\n" + "🔄 FALLBACK MODE ACTIVE".center(50, "="))
        status = fallback_mode.get_status()
        print("   System running with limited functionality")
        print("   • No data persistence")
        print("   • Mock data only")
        print("   • Some features disabled")
        print("   • Database will be checked periodically")
        print("=" * 50)
    else:
        print("✅ Database fully operational")


@app.on_event("shutdown")
async def shutdown() -> None:
    global _broadcast_task
    if _broadcast_task:
        _broadcast_task.cancel()
        _broadcast_task = None


async def _broadcast_loop() -> None:
    """Periodically broadcast performance and system health over WS."""
    while True:
        try:
            await asyncio.sleep(2)
            mc = get_metrics_collector()
            trading_summary = mc.get_trading_summary()
            system_summary = mc.get_system_summary()

            pnl_msg = {
                "type": "PNL_UPDATE",
                "data": {
                    "totalPnl": trading_summary.get("net_pnl", 0.0),
                    "dailyPnl": 0.0,
                    "winRate": trading_summary.get("win_rate", 0.0),
                    "totalTrades": trading_summary.get("total_trades", 0),
                    "currentDrawdown": trading_summary.get("current_drawdown", 0.0),
                    "maxDrawdown": trading_summary.get("max_drawdown", 0.0),
                    "portfolioValue": 0.0,
                    "dailyChange": 0.0,
                    "dailyChangePercent": 0.0,
                    "lastUpdate": datetime.utcnow().isoformat(),
                },
                "timestamp": datetime.utcnow().isoformat(),
                "id": f"pnl_{int(datetime.utcnow().timestamp())}",
            }
            health_msg = {
                "type": "HEALTH_CHECK",
                "data": {
                    "cpu": system_summary.get("cpu_usage_percent", 0.0),
                    "memory": system_summary.get("memory_usage_mb", 0.0),
                    "diskUsage": 0.0,
                    "networkLatency": system_summary.get("scan_latency_p95", 0.0),
                    "errorRate": 0.0,
                    "uptime": int((datetime.utcnow() - datetime.utcfromtimestamp(0)).total_seconds()),
                    "connections": {"database": True, "broker": True, "llm": True, "websocket": True},
                    "lastUpdate": datetime.utcnow().isoformat(),
                },
                "timestamp": datetime.utcnow().isoformat(),
                "id": f"health_{int(datetime.utcnow().timestamp())}",
            }
            # Broadcast to clients
            for ws in list(_ws_clients):
                try:
                    await ws.send_json(pnl_msg)
                    await ws.send_json(health_msg)
                except Exception:
                    try:
                        await ws.close()
                    except Exception:
                        pass
                    _ws_clients.discard(ws)
        except asyncio.CancelledError:
            break
        except Exception:
            # keep looping even if errors occur
            continue


@app.post("/auth/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    if not req.email or not req.password:
        raise HTTPException(status_code=400, detail="Missing credentials")
    return {"token": create_token(req.email), "refreshToken": create_token(req.email, minutes=60 * 24)}


@app.post("/auth/refresh", response_model=TokenResponse)
async def refresh(creds: HTTPAuthorizationCredentials = Depends(security)):
    payload = verify_token(creds.credentials)
    sub = payload.get("sub")
    return {"token": create_token(sub), "refreshToken": create_token(sub, minutes=60 * 24)}


@app.get("/trading/performance", response_model=Performance)
async def get_performance(_: dict = Depends(auth_required)):
    mc = get_metrics_collector()
    t = mc.get_trading_summary()
    now = datetime.utcnow()
    return Performance(
        totalPnl=float(t.get("net_pnl", 0.0)),
        dailyPnl=0.0,
        winRate=float(t.get("win_rate", 0.0)),
        totalTrades=int(t.get("total_trades", 0)),
        currentDrawdown=float(t.get("current_drawdown", 0.0)),
        maxDrawdown=float(t.get("max_drawdown", 0.0)),
        portfolioValue=0.0,
        dailyChange=0.0,
        dailyChangePercent=0.0,
        lastUpdate=now,
    )


@app.get("/system/agents", response_model=AgentStatus)
async def get_agent_status(_: dict = Depends(auth_required)):
    # minimal status based on orchestrator
    state = "running" if _orchestrator and _orchestrator.state.value == "running" else "stopped"
    return AgentStatus(state=state, uptime=0, lastAction=datetime.utcnow(), activePositions=0, dailyTrades=0, version="1.0.0")


@app.get("/system/health", response_model=SystemHealth)
async def get_system_health(_: dict = Depends(auth_required)):
    import os

    from libs.trading_models.config_manager import ConfigurationManager
    from libs.trading_models.fallback_mode import get_fallback_mode

    mc = get_metrics_collector()
    s = mc.get_system_summary()

    # Check database connection status with detailed validation
    database_connected = False
    try:
        config_manager = ConfigurationManager()
        database_url = config_manager.get_database_url()

        if database_url:
            from libs.trading_models.db_validator import DatabaseValidator
            validator = DatabaseValidator()
            result = validator.test_connection(database_url)
            database_connected = result.success
    except Exception:
        # Fallback to environment variable
        database_url = os.getenv('DATABASE_URL')
        if database_url:
            try:
                from libs.trading_models.db_validator import DatabaseValidator
                validator = DatabaseValidator()
                result = validator.test_connection(database_url)
                database_connected = result.success
            except Exception:
                database_connected = False

    # Check if in fallback mode (overrides database status)
    fallback_mode = get_fallback_mode()
    if fallback_mode.is_enabled():
        database_connected = False

    return SystemHealth(
        cpu=float(s.get("cpu_usage_percent", 0.0)),
        memory=float(s.get("memory_usage_mb", 0.0)),
        diskUsage=0.0,
        networkLatency=float(s.get("scan_latency_p95", 0.0)),
        errorRate=0.0,
        uptime=int(s.get("uptime_hours", 0.0) * 3600),
        connections={"database": database_connected, "broker": True, "llm": True, "websocket": True},
        lastUpdate=datetime.utcnow(),
    )


@app.post("/system/agents/{agent_id}/control")
async def control_agent(agent_id: str, body: AgentControlRequest, _: dict = Depends(auth_required)) -> dict[str, Any]:
    if body.action == "start":
        asyncio.create_task(_orchestrator.start())  # fire and forget for demo
        return {"status": "starting"}
    if body.action == "stop":
        await _orchestrator.stop()
        return {"status": "stopping"}
    if body.action == "pause":
        return {"status": "paused"}
    raise HTTPException(status_code=400, detail="Unknown action")


@app.get("/system/database/diagnostics")
async def get_database_diagnostics(_: dict = Depends(auth_required)) -> dict[str, Any]:
    """Get comprehensive database diagnostics."""

    from libs.trading_models.config_manager import ConfigurationManager
    from libs.trading_models.db_validator import DatabaseValidator
    from libs.trading_models.fallback_mode import get_fallback_mode

    try:
        # Get configuration
        config_manager = ConfigurationManager()
        database_url = config_manager.get_database_url()

        # Get comprehensive diagnostics
        validator = DatabaseValidator()
        diagnostics = validator.get_connection_diagnostics(database_url)

        # Add fallback mode status
        fallback_mode = get_fallback_mode()
        diagnostics["fallback_mode"] = fallback_mode.get_status()

        # Add configuration status
        config_issues = config_manager.validate_config()
        diagnostics["configuration"] = {
            "issues": config_issues,
            "valid": len([i for i in config_issues if i["severity"] == "error"]) == 0
        }

        return diagnostics

    except Exception as e:
        return {
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
            "fallback_mode": get_fallback_mode().get_status()
        }


@app.post("/system/database/reconnect")
async def reconnect_database(_: dict = Depends(auth_required)) -> dict[str, Any]:
    """Attempt to reconnect to database and disable fallback mode if successful."""
    from libs.trading_models.config_manager import ConfigurationManager
    from libs.trading_models.db_validator import DatabaseValidator
    from libs.trading_models.fallback_mode import get_fallback_mode

    try:
        config_manager = ConfigurationManager()
        database_url = config_manager.get_database_url()

        if not database_url:
            return {
                "success": False,
                "error": "DATABASE_URL not configured",
                "suggested_fix": "Run: .\\scripts\\Setup-Database.ps1"
            }

        validator = DatabaseValidator()
        result = validator.test_connection(database_url)

        if result.success:
            # Disable fallback mode
            fallback_mode = get_fallback_mode()
            fallback_mode.disable()

            return {
                "success": True,
                "message": "Database reconnected successfully",
                "connection_time_ms": result.connection_time_ms,
                "fallback_mode_disabled": True
            }
        else:
            return {
                "success": False,
                "error": result.error_message,
                "error_type": result.error_type,
                "suggested_fix": result.suggested_fix
            }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "suggested_fix": "Check logs and run Setup-Database.ps1"
        }


@app.websocket("/ws/trading")
async def ws_trading(ws: WebSocket):
    await ws.accept()
    _ws_clients.add(ws)
    try:
        while True:
            await ws.receive_text()  # ignore client messages
    except WebSocketDisconnect:
        _ws_clients.discard(ws)


# Run: uvicorn apps.trading_api.main:app --reload

