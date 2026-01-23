# Integration Plan: AI Agent Trading + Investment Auditor

## Executive Summary

This document outlines the comprehensive integration strategy for merging **AI Agent Trading** (autonomous cryptocurrency trading platform) with **Investment Auditor** (crypto project analysis and risk assessment platform) into a unified **Crypto Investment Intelligence Platform**.

---

## 1. Project Analysis Summary

### 1.1 Investment Auditor (Current Project)

| Aspect | Details |
|--------|---------|
| **Purpose** | Crypto project analysis, risk assessment, and audit scoring |
| **Stack** | React 19, TypeScript, tRPC, Express, Drizzle ORM, MySQL |
| **Database** | MySQL with Drizzle ORM |
| **Auth** | Manus OAuth (JWT-based) |
| **Key Features** | GitHub analysis, tokenomics analysis, contract risk, social sentiment, AI summaries, watchlist, comparisons |

### 1.2 AI Agent Trading (Target Project)

| Aspect | Details |
|--------|---------|
| **Purpose** | Autonomous cryptocurrency trading with AI-powered signals |
| **Stack** | Python FastAPI backend, React 18 frontend, PostgreSQL, Redis, Docker |
| **Database** | PostgreSQL with SQLAlchemy |
| **Auth** | JWT-based (custom) |
| **Key Features** | Automated trading, signal generation, pattern recognition, paper trading, live trading, performance analytics |

---

## 2. Integration Vision

### 2.1 Unified Platform Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CRYPTO INVESTMENT INTELLIGENCE PLATFORM          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │  PROJECT AUDIT   │  │  TRADING ENGINE  │  │  PORTFOLIO MGMT  │  │
│  │  & ANALYSIS      │  │  & EXECUTION     │  │  & TRACKING      │  │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘  │
│           │                     │                     │             │
│           └─────────────────────┼─────────────────────┘             │
│                                 │                                   │
│                    ┌────────────▼────────────┐                      │
│                    │   SHARED SERVICES LAYER │                      │
│                    │  - AI/LLM Integration   │                      │
│                    │  - Market Data APIs     │                      │
│                    │  - Notifications        │                      │
│                    │  - Analytics/Reporting  │                      │
│                    └────────────┬────────────┘                      │
│                                 │                                   │
│                    ┌────────────▼────────────┐                      │
│                    │   UNIFIED DATABASE      │                      │
│                    │   - Projects            │                      │
│                    │   - Trades/Positions    │                      │
│                    │   - Users/Auth          │                      │
│                    │   - Analytics           │                      │
│                    └─────────────────────────┘                      │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 User Journey Flow

```
DISCOVER → AUDIT/ANALYZE → SCORE → ADD TO WATCHLIST → CONFIGURE ALERTS
                                                        │
                                                        ▼
                                     [Trading Signal Generated]
                                                        │
                                    ┌───────────────────┴───────────────────┐
                                    ▼                                       ▼
                              PAPER TRADING                          LIVE TRADING
                                    │                                       │
                                    └───────────────────┬───────────────────┘
                                                        │
                                                        ▼
                                          TRACK PERFORMANCE & OPTIMIZE
```

---

## 3. Technical Architecture Decisions

### 3.1 Backend Architecture

#### Decision: Hybrid Microservices with Unified Frontend

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **Frontend** | React 19 + TypeScript (from Investment Auditor) | Modern, already has shadcn/ui, better DX |
| **API Gateway** | Express + tRPC (from Investment Auditor) | Type-safe end-to-end, easier migration |
| **Trading Service** | Python FastAPI (from AI Trading) | Keep Python ML/AI capabilities |
| **Database** | PostgreSQL (from AI Trading) | Better for trading data, supports JSON columns |
| **ORM** | Drizzle with PostgreSQL adapter | Keep type-safe queries from Investment Auditor |

#### Communication Pattern

```
┌─────────────┐       tRPC      ┌─────────────────┐       HTTP       ┌──────────────┐
│  React      │ ───────────────► │  Express API    │ ───────────────► │ FastAPI      │
│  Frontend   │   (Type-safe)   │  (Node.js)      │   (REST/gRPC)   │ (Python)     │
│             │                 │                 │                 │  Trading     │
└─────────────┘                 └─────────────────┘                 └──────────────┘
        │                                │
        │                                │ SQL
        ▼                                ▼
┌─────────────────┐           ┌─────────────────┐
│  tRPC Client    │           │  PostgreSQL     │
│  (Direct)       │           │  Database       │
└─────────────────┘           └─────────────────┘
```

### 3.2 Database Unification Strategy

#### Target Schema (PostgreSQL)

```sql
-- Users (merged)
users (id, openId, name, email, role, trading_enabled, api_keys)

-- Projects (from Investment Auditor)
projects (id, userId, name, symbol, contract_address, audit_status, audit_data)

-- Audit Reports (from Investment Auditor)
audit_reports (id, projectId, github_score, tokenomics_score,
               contract_risk_score, social_score, overall_score, ai_analysis)

-- Trading Tables (from AI Agent Trading)
trades (id, userId, projectId, symbol, side, entry_price, exit_price,
        quantity, pnl, status, strategy, confidence)

trading_sessions (id, userId, status, config, start_time, end_time,
                  total_pnl, trades_count)

positions (id, userId, symbol, side, size, entry_price, current_price,
          unrealized_pnl, stop_loss, take_profit)

-- Signals (new unified)
trading_signals (id, projectId, symbol, type, confidence, pattern,
                 entry_price, targets, stop_loss, timeframe, source)

-- Watchlist (enhanced)
watchlist (id, userId, projectId, symbol, notes, alert_config,
           auto_trade_enabled)

-- Analytics (unified)
performance_snapshots (id, userId, timestamp, portfolio_value, pnl,
                       drawdown, win_rate, sharpe_ratio)

-- Notifications (unified)
notifications (id, userId, type, title, message, data, read, created_at)

-- Risk Management (from AI Trading)
risk_settings (id, userId, max_position_size, max_daily_loss,
               max_portfolio_exposure, leverage_limits)
```

---

## 4. Integration Phases

### Phase 1: Foundation (Week 1-2)

**Goal:** Set up unified infrastructure without breaking existing features.

| Task | Effort | Priority |
|------|--------|----------|
| 1.1 Set up PostgreSQL database | 2 days | High |
| 1.2 Configure Drizzle with PostgreSQL | 1 day | High |
| 1.3 Create database migration scripts from MySQL | 3 days | High |
| 1.4 Set up FastAPI service alongside Express | 2 days | High |
| 1.5 Configure service-to-service communication | 2 days | Medium |
| 1.6 Unified authentication flow | 2 days | High |

**Deliverables:**
- Running PostgreSQL with migrated Investment Auditor data
- FastAPI trading service accessible
- Single sign-on across both services

### Phase 2: Database Migration (Week 3)

**Goal:** Unify data models and establish single source of truth.

| Task | Effort | Priority |
|------|--------|----------|
| 2.1 Create unified schema migrations | 3 days | High |
| 2.2 Migrate MySQL data to PostgreSQL | 2 days | High |
| 2.3 Migrate AI Trading SQLite data | 1 day | High |
| 2.4 Establish foreign key relationships | 2 days | Medium |
| 2.5 Data validation and cleanup | 2 days | High |
| 2.6 Update Drizzle schema definitions | 2 days | High |

**Deliverables:**
- Unified PostgreSQL database
- All historical data migrated
- Data integrity validated

### Phase 3: Frontend Integration (Week 4-5)

**Goal:** Merge UI components into cohesive dashboard.

| Task | Effort | Priority |
|------|--------|----------|
| 3.1 Audit component libraries compatibility | 1 day | High |
| 3.2 Migrate trading dashboard components | 3 days | High |
| 3.3 Create unified navigation/routing | 2 days | High |
| 3.4 Integrate shadcn/ui with trading charts | 2 days | Medium |
| 3.5 Responsive design unification | 2 days | Medium |
| 3.6 Dark mode consistency | 1 day | Low |
| 3.7 Create unified dashboard layout | 3 days | High |

**New Component Structure:**
```
client/src/
├── components/
│   ├── audit/          # Project audit components
│   ├── trading/        # Trading components (from AI Trading)
│   ├── portfolio/      # Portfolio management
│   ├── shared/         # Shared UI components
│   └── layouts/        # Layout components
├── pages/
│   ├── AuditDetail.tsx
│   ├── TradingDashboard.tsx      # NEW
│   ├── PortfolioOverview.tsx     # NEW
│   └── SignalCenter.tsx          # NEW
```

### Phase 4: Service Integration (Week 6-7)

**Goal:** Connect audit analysis with trading execution.

| Task | Effort | Priority |
|------|--------|----------|
| 4.1 Create unified API gateway | 3 days | High |
| 4.2 Implement signal generation from audit scores | 3 days | High |
| 4.3 Connect watchlist to trading execution | 2 days | High |
| 4.4 Implement auto-trade from alerts | 3 days | Medium |
| 4.5 Position synchronization | 2 days | Medium |
| 4.6 Performance tracking integration | 2 days | High |

**Key Integration Points:**

```typescript
// Signal generation from audit
interface AuditToTradingSignal {
  projectId: number;
  overallScore: number;      // From audit
  riskLevel: string;         // From audit
  symbol: string;            // From project
  contractAddress: string;   // From project

  // Derived trading parameters
  signalType: 'BUY' | 'SELL' | 'HOLD';
  confidence: number;        // Based on audit scores
  positionSize: number;      // Based on risk settings
  stopLoss: number;
  takeProfit: number[];
}
```

### Phase 5: Risk & Analytics (Week 8)

**Goal:** Unified risk management and analytics.

| Task | Effort | Priority |
|------|--------|----------|
| 5.1 Implement unified risk engine | 3 days | High |
| 5.2 Portfolio analytics dashboard | 3 days | High |
| 5.3 P&L attribution by project | 2 days | Medium |
| 5.4 Performance reports | 2 days | Medium |
| 5.5 Risk alerts and notifications | 2 days | High |

### Phase 6: Testing & Deployment (Week 9-10)

| Task | Effort | Priority |
|------|--------|----------|
| 6.1 Integration testing | 3 days | High |
| 6.2 E2E testing | 2 days | High |
| 6.3 Performance testing | 2 days | Medium |
| 6.4 Security audit | 2 days | High |
| 6.5 Documentation | 2 days | Medium |
| 6.6 Deployment pipeline setup | 2 days | High |
| 6.7 Production migration | 2 days | High |

---

## 5. Key Integration Points

### 5.1 Audit Score → Trading Signal

```typescript
// server/services/signalGenerator.ts
export function generateTradingSignal(auditReport: AuditReport): TradingSignal {
  const { overallScore, riskLevel, tokenomicsScore, contractRiskScore } = auditReport;

  // Signal logic
  let signalType: 'BUY' | 'SELL' | 'HOLD' = 'HOLD';
  let confidence = 0;

  if (overallScore >= 75 && riskLevel !== 'critical') {
    signalType = 'BUY';
    confidence = Math.min(95, overallScore + (tokenomicsScore > 70 ? 5 : 0));
  } else if (overallScore < 40 || riskLevel === 'critical') {
    signalType = 'SELL';
    confidence = overallScore < 30 ? 80 : 60;
  }

  // Position sizing based on risk
  const basePositionSize = 0.02; // 2% of portfolio
  const riskMultiplier = riskLevel === 'low' ? 1.5 : riskLevel === 'medium' ? 1 : 0.5;

  return {
    type: signalType,
    confidence,
    positionSize: basePositionSize * riskMultiplier * (confidence / 100),
    stopLoss: overallScore > 70 ? 0.05 : 0.03, // 5% or 3% SL
    takeProfit: overallScore > 70 ? [0.10, 0.20] : [0.05, 0.10],
    reason: `Based on audit score: ${overallScore}/100, Risk: ${riskLevel}`,
    source: 'audit_analysis',
  };
}
```

### 5.2 Watchlist Auto-Trading

```typescript
// Enhanced watchlist with trading integration
interface WatchlistItem {
  projectId: number;
  symbol: string;
  autoTrade: boolean;
  tradeConfig: {
    enabled: boolean;
    minScore: number;        // Minimum audit score to trigger buy
    maxRiskLevel: string;    // Maximum acceptable risk
    positionSize: number;    // % of portfolio
    stopLoss: number;        // %
    takeProfit: number[];    // Array of profit targets
  };
}
```

### 5.3 Unified Portfolio View

```typescript
// Portfolio combining audit insights and trading performance
interface UnifiedPortfolio {
  holdings: PortfolioHolding[];
  analytics: {
    totalValue: number;
    totalPnl: number;
    todayPnl: number;
    winRate: number;
    sharpeRatio: number;
  };
  byAuditScore: {
    highScore: { count: number; pnl: number; value: number };
    mediumScore: { count: number; pnl: number; value: number };
    lowScore: { count: number; pnl: number; value: number };
  };
}

interface PortfolioHolding {
  symbol: string;
  quantity: number;
  avgEntryPrice: number;
  currentPrice: number;
  unrealizedPnl: number;

  // Audit linkage
  projectId?: number;
  auditScore?: number;
  riskLevel?: string;
  lastAuditDate?: Date;
}
```

---

## 6. Configuration & Environment

### 6.1 Unified .env Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/crypto_platform
DATABASE_POOL_SIZE=10

# Services
FRONTEND_URL=http://localhost:3000
API_PORT=3000
TRADING_SERVICE_URL=http://localhost:8000

# Authentication
MANUS_CLIENT_ID=your_client_id
MANUS_CLIENT_SECRET=your_client_secret
JWT_SECRET=your_jwt_secret

# AI/LLM
OPENAI_API_KEY=your_openai_key
GEMINI_API_KEY=your_gemini_key

# Trading APIs
BINANCE_API_KEY=your_binance_key
BINANCE_API_SECRET=your_binance_secret
# Add other exchange APIs

# Market Data
COINGECKO_API_KEY=your_coingecko_key
GLASSNODE_API_KEY=your_glassnode_key

# Redis (for caching and sessions)
REDIS_URL=redis://localhost:6379

# S3 (for file storage)
AWS_S3_BUCKET=your_bucket
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key

# Monitoring
PROMETHEUS_PORT=9090
GRAFANA_URL=http://localhost:3001
```

### 6.2 Docker Compose Configuration

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: crypto_platform
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  api:
    build: .
    ports:
      - "3000:3000"
    depends_on:
      - postgres
      - redis
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/crypto_platform

  trading-service:
    build: ./services/trading
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis

  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana
    ports:
      - "3001:3000"

volumes:
  postgres_data:
```

---

## 7. Risk Considerations

### 7.1 Technical Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Data migration loss | High | Full backup, validation scripts, rollback plan |
| API breaking changes | Medium | Versioned APIs, feature flags |
| Performance degradation | Medium | Load testing, caching strategy |
| Authentication issues | High | Unified auth service, token refresh logic |
| Trading execution errors | Critical | Paper trading mode, circuit breakers |

### 7.2 Business Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| User confusion with new features | Medium | Gradual rollout, tutorials, tooltips |
| Trading losses from integration | Critical | Paper trading first, risk limits |
| Compliance issues | High | Legal review of trading features |
| Increased infrastructure costs | Medium | Right-sizing, monitoring |

---

## 8. Success Metrics

### 8.1 Technical Metrics

- [ ] Zero data loss during migration
- [ ] API response time < 200ms (p95)
- [ ] 99.9% uptime during migration
- [ ] Zero critical bugs in production

### 8.2 User Metrics

- [ ] DAU increase by 20% post-launch
- [ ] Feature adoption rate > 30%
- [ ] User session length increase
- [ ] Support tickets decrease

### 8.3 Trading Metrics

- [ ] Signal accuracy > 60%
- [ ] Average holding period optimization
- [ ] Risk-adjusted returns improvement

---

## 9. Rollback Plan

### Scenarios

1. **Data Migration Issues**
   - Stop migration
   - Restore from backup
   - Investigate and fix
   - Retry migration

2. **API Integration Failures**
   - Disable trading features
   - Keep audit features running
   - Fix integration issues
   - Gradual re-enable

3. **Performance Issues**
   - Scale infrastructure
   - Implement caching
   - Optimize queries
   - Add rate limiting

---

## 10. Next Steps

1. **Review this plan** with stakeholders
2. **Set up infrastructure** (PostgreSQL, Docker)
3. **Create detailed task breakdown** for Phase 1
4. **Establish communication channels** between teams
5. **Set up monitoring and alerts**
6. **Begin Phase 1 implementation**

---

## Appendix A: File Structure Comparison

### Investment Auditor (Current)
```
investment-auditor/
├── client/              # React frontend
│   └── src/
│       ├── components/
│       ├── pages/
│       └── lib/
├── server/             # Express + tRPC backend
│   ├── _core/
│   └── services/
├── drizzle/            # Database schema
└── shared/             # Shared types
```

### AI Agent Trading (Target)
```
ai-agent-trading/
├── apps/
│   ├── trading-api/    # FastAPI backend
│   └── trading-dashboard-ui-clean/  # React frontend
├── libs/
│   └── trading_models/ # Core trading logic
└── config/
```

### Merged Structure (Proposed)
```
crypto-intelligence-platform/
├── client/                    # Unified React frontend
│   └── src/
│       ├── components/
│       │   ├── audit/        # Audit components
│       │   ├── trading/      # Trading components
│       │   ├── portfolio/    # Portfolio components
│       │   └── shared/       # Shared UI
│       ├── pages/
│       └── lib/
├── server/                   # Express + tRPC API gateway
│   ├── _core/
│   ├── services/
│   │   ├── audit/
│   │   ├── trading/         # Trading service integration
│   │   └── portfolio/
│   └── routers/
├── services/
│   └── trading-engine/       # Python FastAPI service
│       ├── api/
│       ├── core/
│       └── models/
├── drizzle/                  # Unified database schema
├── shared/                   # Shared types
└── docker-compose.yml
```

---

## Appendix B: Technology Stack Summary

| Layer | Technology | Notes |
|-------|------------|-------|
| Frontend | React 19, TypeScript, TailwindCSS, shadcn/ui, Wouter, tRPC | From Investment Auditor |
| API Gateway | Express.js, tRPC, Drizzle ORM | From Investment Auditor |
| Trading Service | Python FastAPI, SQLAlchemy | From AI Agent Trading |
| Database | PostgreSQL 16 | Migrated from MySQL + SQLite |
| Cache | Redis 7 | From AI Agent Trading |
| Auth | Manus OAuth, JWT | From Investment Auditor |
| Charts | Lightweight Charts | From AI Agent Trading |
| Monitoring | Prometheus, Grafana | From AI Agent Trading |
| Deployment | Docker, Docker Compose | From AI Agent Trading |

---

*Document Version: 1.0*
*Last Updated: 2026-01-22*
*Author: Claude Code Integration Planning*
