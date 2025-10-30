# 🚀 One‑Click Docker Trading Dashboard

This guide explains how to start the full web dashboard (UI + API + DB + Redis) with a single click, have it wait for health checks, and automatically open your browser. It also shows how to enable optional monitoring (Prometheus + Grafana).

The one‑click launcher referenced below is designed for Windows.

---

## What you get

The one‑click launcher:
- Builds and starts the stack via Docker Compose
- Ensures a `.env` exists with a secure `POSTGRES_PASSWORD`
- Waits for API/UI health checks to pass
- Opens the dashboard and API docs in your default browser
- Optional: starts Prometheus + Grafana when monitoring is enabled

Services started by default:
- trading-dashboard (UI) on http://localhost
- trading-api (FastAPI backend) on http://localhost:8000
- postgres on port 5432 (local)
- redis on port 6379 (local)

Optional monitoring profile (ENABLE_MONITORING=1):
- prometheus on http://localhost:9090
- grafana on http://localhost:3001

All services are defined in:
- docker-compose.trading-dashboard.yml

---

## Prerequisites

- Windows with Docker Desktop (WSL2 backend recommended)
- Ports available:
  - 80 (UI), 8000 (API), 5432 (Postgres), 6379 (Redis)
  - 3001 (Grafana) and 9090 (Prometheus) if monitoring is enabled
- Internet access to download images on first run

---

## Quick Start (1‑Click)

1) Double‑click:
   - LAUNCH_DOCKER_DASHBOARD.bat

2) The launcher will:
   - Create `.env` if missing and generate a secure `POSTGRES_PASSWORD`
   - Build and start all containers
   - Wait for:
     - API health: http://localhost:8000/health
     - UI health: http://localhost/health
   - Open your browser to:
     - Dashboard UI: http://localhost
     - API docs: http://localhost:8000/docs

3) You’re live.

Notes:
- The first build can take several minutes depending on network speed.
- Windows Firewall may prompt to allow Docker/Hyper-V/WSL networking; allow access.
- The launcher will not start monitoring unless you set ENABLE_MONITORING=1.

---

## Enable Monitoring (Prometheus + Grafana)

Monitoring is optional and disabled by default to save resources.

Enable it in two ways:

- From a terminal (temporary for this session):
  - set ENABLE_MONITORING=1 && LAUNCH_DOCKER_DASHBOARD.bat

- Persistently (for double‑click usage):
  - Create a small wrapper `.bat` that sets `ENABLE_MONITORING=1` and then calls the launcher
  - Or set system/user environment variable `ENABLE_MONITORING=1`

When enabled, the launcher also opens:
- Grafana: http://localhost:3001
- Prometheus: http://localhost:9090

Grafana default admin password is set via `.env` (the launcher creates one if missing).

---

## URLs and Health Checks

- UI:
  - Dashboard: http://localhost
  - Health: http://localhost/health

- API:
  - Docs (Swagger): http://localhost:8000/docs
  - Health: http://localhost:8000/health

- Monitoring (if enabled):
  - Grafana: http://localhost:3001
  - Prometheus: http://localhost:9090

---

## Verifying Real Actions (API Examples)

Many dashboard actions call the backend API. You can verify these endpoints with curl or any REST client.

1) Login (get JWT):
- Endpoint: POST /auth/login
- Body: { "email": "test@example.com", "password": "password123" }
- Note: The sample backend accepts any email with password "password123" for demo purposes.

Example (PowerShell):
```
$token = (Invoke-RestMethod -Method POST -Uri "http://localhost:8000/auth/login" -ContentType "application/json" -Body '{"email":"test@example.com","password":"password123"}').token
$headers = @{ "Authorization" = "Bearer $token" }
Invoke-RestMethod -Method GET -Uri "http://localhost:8000/trading/performance" -Headers $headers
```

2) Get performance:
- Endpoint: GET /trading/performance
- Header: Authorization: Bearer <token>

3) Control agent:
- Endpoint: POST /system/agents/{agent_id}/control
- Body: { "action": "start" } (actions: start, stop, pause, resume)
- Header: Authorization: Bearer <token>

4) Get trades (paginated, filtered):
- Endpoint: GET /trading/trades?page=1&pageSize=20
- Header: Authorization: Bearer <token>

These endpoints provide concrete, verifiable responses confirming that actions are live.

---

## Data flow diagram

```mermaid
graph TD
    subgraph "Launcher"
        A[LAUNCH_DOCKER_DASHBOARD.bat]
        A --> B[Docker Compose up]
        B --> C[Wait health: /health]
        C --> D[Open browser: UI + API docs]
    end

    subgraph "Backend stack (Docker)"
        UI[Nginx + React UI] -->|80
        API[FastAPI] -->|8000
        DB[(PostgreSQL)] -->|5432
        CACHE[(Redis)] -->|6379
        UI -.->|API
        API -.->|WS{/ws/trading, /ws/system, /ws/notifications}
        API -.->|DB
        API -.->|CACHE
    end

    subgraph "Desktop UI (Tkinter)"
        DESKTOP[trading_dashboard.py]
        DESKTOP --> |HTTP</br>API(http://localhost:8000)
        DESKTOP --> |WS</br>TRADING
        DESKTOP --> |WS</br>SYSTEM
        DESKTOP --> |WS</br>NOTIFICATIONS
        DESKTOP -.->|Settings/Account</br>JSON
    end

    API -.->|Background Simulator</br>(real‑time events)
    WS -.->|Desktop UI (Live updates)
```

---

## Environment variables

The launcher writes a `.env` file with:
- POSTGRES_PASSWORD=<randomly_generated>
- GRAFANA_PASSWORD=admin (you can change this)

Additional variables used in docker-compose.trading-dashboard.yml:
- ENVIRONMENT (default: production)
- LOG_LEVEL (default: INFO)
- DATABASE_URL (auto‑wired through POSTGRES_PASSWORD)
- REDIS_URL (default wired to local service)
- SECRET_KEY (default provided; replace for production)
- CORS_ORIGINS (default: http://localhost,http://127.0.0.1)

You can customize them by editing `.env`.

---

## Data persistence

Named volumes:
- postgres_data
- redis_data
- prometheus_data (if monitoring)
- grafana_data (if monitoring)

Logs:
- logs/nginx, logs/nginx-proxy (mounted from compose)

---

## Start, Stop, Logs (Manual)

The launcher uses Docker Compose under the hood. You can manage the stack manually if you prefer:

Start (without monitoring):
```
docker compose -f docker-compose.trading-dashboard.yml up -d --build
```

Start (with monitoring):
```
docker compose -f docker-compose.trading-dashboard.yml up -d --build --profile monitoring
```

Stop:
```
docker compose -f docker-compose.trading-dashboard.yml down
```

Stop and remove volumes (danger: deletes DB/cache data):
```
docker compose -f docker-compose.trading-dashboard.yml down -v
```

View logs:
```
docker compose -f docker-compose.trading-dashboard.yml logs -f
docker compose -f docker-compose.trading-dashboard.yml logs -f trading-api
docker compose -f docker-compose.trading-dashboard.yml logs -f trading-dashboard
```

---

## Troubleshooting

- Docker not found:
  - Install Docker Desktop and ensure it’s in PATH.
  - Restart your terminal/command prompt after installation.

- Ports in use (80/8000/3001/9090/5432/6379):
  - Stop conflicting services or change port mappings in docker-compose.trading-dashboard.yml.

- UI/API not opening automatically:
  - The launcher tries to open http://localhost and http://localhost:8000/docs after health checks.
  - You can open these URLs manually if needed.

- API 401 Unauthorized:
  - You must login and pass a valid Bearer token for protected endpoints.

- Slow first run:
  - Image downloads and builds can take time. Subsequent starts are faster.

- WSL2 resource limits:
  - If containers get killed or fail to start, increase memory/CPU in Docker Desktop > Settings > Resources.

---

## Quick usage examples

```bash
# Full stack with monitoring (Windows cmd)
set ENABLE_MONITORING=1 && LAUNCH_DOCKER_DASHBOARD.bat

# Start desktop UI with local backend (no Docker)
LAUNCH_DASHBOARD.bat

# Open only browser windows (UI + API docs)
OPEN_DASHBOARD.bat
```


## Production notes (advanced)

- Change `SECRET_KEY` and all default passwords before exposing publicly.
- Consider enabling the `nginx-proxy` service (profile: production) for TLS termination and hardened reverse proxy settings.
- Lock down CORS, rate limits, and firewall rules based on your deployment environment.

---

## Table of Contents
- [One‑click launch](#-one-click-launch)
- [Architecture overview](#architecture-overview)
- [Data flow diagram](#data-flow-diagram)
- [Prerequisites](#prerequisites)
- [Quick start](#quick-start-1-click)
- [Enable monitoring](#enable-monitoring-optional)
- [URLs and health checks](#urls-and-health-checks)
- [Verification steps](#verification-steps-api-examples)
- [Environment variables](#environment-variables)
- [Data persistence](#data-persistence)
- [Manual Docker commands](#manual-docker-commands)
- [Troubleshooting](#troubleshooting)
- [Production notes](#production-notes-advanced)
- [One‑click launchers for key actions](#one-click-launchers-for-key-actions-windows)

## One‑click launchers for key actions (Windows)

For convenience, there are ready‑to‑run `.bat` files that wrap common tasks so you don’t need to remember commands.

### Quick stack launch
- LAUNCH_DOCKER_DASHBOARD.bat
  - Starts full web stack, waits for health, opens browser.

### Desktop UI with backend (dev mode)
- LAUNCH_DASHBOARD.bat
  - Starts Tkinter UI; optionally starts FastAPI dev server via the Quick Start modal.

### Open Web Dashboard (only browsers)
- OPEN_DASHBOARD.bat
  - Opens http://localhost and http://localhost:8000/docs directly.

#### File contents (quick reference)

**LAUNCH_DASHBOARD.bat**
```batch
@echo off
cd /d "%~dp0"
poetry run python trading_dashboard.py
pause
```

**OPEN_DASHBOARD.bat**
```batch
@echo off
start "" "http://localhost"
start "" "http://localhost:8000/docs"
```

---

You’re ready to go. Double‑click the launcher, let it build, and your browser will open on a modern, fully‑wired trading dashboard. Enjoy!