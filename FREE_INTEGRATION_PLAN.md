# FREE Integration Plan: AI Agent Trading + Investment Auditor

## 100% Free Stack (except Gemini API) + TradingView Subscription

---

## Executive Summary

This integration plan uses **ZERO paid services** except for the Gemini API key you already have. All other infrastructure will use self-hosted or free-tier alternatives.

---

## 1. Free Technology Stack

### 1.1 Complete Stack (All Free)

| Component | Free Solution | Notes |
|-----------|---------------|-------|
| **Database** | PostgreSQL (self-hosted) | Free, open-source |
| **Cache** | Redis (self-hosted) | Free, open-source |
| **Auth** | NextAuth.js / Custom JWT | 100% free, no external service needed |
| **AI/LLM** | Gemini API (you have) | Your only paid service |
| **Charts** | TradingView Widget (your sub) | You already pay for this |
| **Market Data** | CoinGecko Free API | 100 calls/minute free |
| **GitHub API** | GitHub Free Tier | 5,000 requests/hour |
| **Blockchain Data** | Public RPC endpoints | Free (etherscan, bscscan, etc.) |
| **File Storage** | Local filesystem | Free |
| **Email** | Resend (100 emails/day free) | Or skip email, use in-app notifications |
| **Monitoring** | Prometheus + Grafana | Self-hosted, free |
| **Hosting** | Docker Compose locally | Free |
| **Deployment** | Railway/Render/Clever Free | Or self-host on your own server |

---

## 2. Updated Architecture (100% Free)

```
┌─────────────────────────────────────────────────────────────────────┐
│              CRYPTO INTELLIGENCE PLATFORM (FREE STACK)               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │  PROJECT AUDIT   │  │  SIGNAL ENGINE   │  │  ALERT SYSTEM    │  │
│  │  (Free APIs)     │  │  (Gemini AI)     │  │  (TradingView)   │  │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘  │
│           │                     │                     │             │
│           └─────────────────────┼─────────────────────┘             │
│                                 │                                   │
│                    ┌────────────▼────────────┐                      │
│                    │   LOCAL API GATEWAY    │                      │
│                    │   (Express + tRPC)     │                      │
│                    │   FREE - Self-hosted   │                      │
│                    └────────────┬────────────┘                      │
│                                 │                                   │
│                    ┌────────────▼────────────┐                      │
│                    │   LOCAL DATABASE       │                      │
│                    │   PostgreSQL (Free)    │                      │
│                    └─────────────────────────┘                      │
│                                                                       │
│  All services run locally via Docker Compose - $0/month             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Free API Alternatives

### 3.1 Market Data Sources (All Free)

| Data | Free Source | Limits |
|------|-------------|--------|
| **Price Data** | CoinGecko API | 100 calls/min free |
| **OHLCV** | Binance Public API | No rate limit for public data |
| **GitHub Stats** | GitHub REST API | 5,000 requests/hour |
| **Contract Data** | Public RPC nodes | Free (infura/alchemy free tier) |
| **Tokenomics** | Etherscan/BscScan Free | 5 calls/sec free |
| **Social Data** | Twitter API Free | 500k tweets/month (free tier) |
| **News** | CryptoCompare Free | 100,000 calls/month free |

### 3.2 Replacing Paid Services

#### Before (Paid) → After (Free)

```bash
# PAID - Replace these:
❌ Manus OAuth        → ✅ NextAuth.js (free) or Custom JWT
❌ OpenAI API         → ✅ Gemini API (you have)
❌ AWS S3             → ✅ Local filesystem
❌ Auth0/ Clerk       → ✅ NextAuth.js
❌ SendGrid           → ✅ Resend (100/day free) or skip email
❌ Datadog/New Relic  → ✅ Prometheus + Grafana (self-hosted)
❌ Managed DB         → ✅ PostgreSQL (self-hosted)
❌ ElasticCache       → ✅ Redis (self-hosted)
```

---

## 4. Authentication (100% Free)

### 4.1 Using NextAuth.js (Recommended)

```bash
# Install NextAuth
pnpm add next-auth @auth/core

# Or use simple JWT-based auth with your own system
```

```typescript
// server/_core/auth.ts - FREE authentication
import jwt from 'jsonwebtoken';

const JWT_SECRET = process.env.JWT_SECRET || 'your-local-secret-key';
const JWT_EXPIRY = '7d';

// Generate JWT token (FREE)
export function generateToken(userId: number, email: string) {
  return jwt.sign(
    { userId, email },
    JWT_SECRET,
    { expiresIn: JWT_EXPIRY }
  );
}

// Verify JWT token (FREE)
export function verifyToken(token: string) {
  try {
    return jwt.verify(token, JWT_SECRET);
  } catch {
    return null;
  }
}

// Simple email/password auth (FREE)
export async function authenticateUser(email: string, password: string) {
  // Check against local database
  const user = await db.query.users.findFirst({
    where: eq(users.email, email)
  });

  if (!user) return null;

  // Simple password check (use bcrypt in production)
  const isValid = await verifyPassword(password, user.passwordHash);
  if (!isValid) return null;

  return user;
}
```

### 4.2 Or Use Social Login (Free Providers)

```typescript
// Free OAuth providers
export const authConfig = {
  providers: [
    GoogleProvider({    // FREE
      clientId: process.env.GOOGLE_CLIENT_ID,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET,
    }),
    GitHubProvider({   // FREE
      clientId: process.env.GITHUB_CLIENT_ID,
      clientSecret: process.env.GITHUB_CLIENT_SECRET,
    }),
    DiscordProvider({  // FREE
      clientId: process.env.DISCORD_CLIENT_ID,
      clientSecret: process.env.DISCORD_CLIENT_SECRET,
    }),
  ],
};
```

---

## 5. TradingView Integration

### 5.1 Using Your TradingView Subscription

```typescript
// client/src/components/Trading/TradingViewChart.tsx
import { useEffect, useRef } from 'react';

interface TradingViewChartProps {
  symbol: string;
  theme?: 'light' | 'dark';
}

export function TradingViewChart({ symbol, theme = 'dark' }: TradingViewChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    // Load TradingView Widget (FREE with your subscription)
    const script = document.createElement('script');
    script.src = 'https://s3.tradingview.com/tv.js';
    script.async = true;

    script.onload = () => {
      // @ts-ignore - TradingView global
      new TradingView.widget({
        autosize: true,
        symbol: `BINANCE:${symbol}`,
        interval: '15',
        timezone: 'Etc/UTC',
        theme: theme,
        style: '1',
        locale: 'en',
        toolbar_bg: '#f1f3f6',
        enable_publishing: false,
        allow_symbol_change: true,
        container_id: containerRef.current.id,
        studies: [
          'RSI@tv-basicstudies',
          'MACD@tv-basicstudies',
        ],
        // Your subscription features
        hide_side_toolbar: false,
      });
    };

    containerRef.current.appendChild(script);

    return () => {
      if (containerRef.current && script.parentNode) {
        script.parentNode.removeChild(script);
      }
    };
  }, [symbol, theme]);

  return (
    <div
      ref={containerRef}
      id={`tradingview_${symbol}`}
      className="w-full h-[600px]"
    />
  );
}
```

### 5.2 TradingView Alerts → Webhook → Your App

```typescript
// server/routers/tradingview.ts - Webhook receiver
import { router, publicProcedure } from '../_core/trpc';
import { z } from 'zod';

const TradingViewAlertSchema = z.object({
  symbol: z.string(),
  exchange: z.string(),
  price: z.number(),
  action: z.enum(['BUY', 'SELL', 'HOLD']),
  indicators: z.object({
    rsi: z.number().optional(),
    macd: z.number().optional(),
  }),
  message: z.string(),
  timestamp: z.number(),
});

export const tradingviewRouter = router({
  // Webhook endpoint for TradingView alerts (FREE)
  receiveAlert: publicProcedure
    .input(TradingViewAlertSchema)
    .mutation(async ({ input, ctx }) => {
      const { symbol, action, price, indicators } = input;

      // Store alert in database
      await db.insert(tradingViewAlerts).values({
        symbol,
        action,
        price,
        indicators: JSON.stringify(indicators),
        timestamp: new Date(input.timestamp * 1000),
      });

      // If action is BUY/SELL, create trading signal
      if (action !== 'HOLD') {
        // Cross-reference with audit data
        const project = await db.query.projects.findFirst({
          where: eq/projects.symbol, symbol),
        });

        if (project) {
          const auditReport = await db.query.auditReports.findFirst({
            where: eq(auditReports.projectId, project.id),
          });

          // Combine TradingView signal with audit score
          const signal = generateCombinedSignal({
            tradingViewAction: action,
            auditScore: auditReport?.overallScore || 50,
            riskLevel: auditReport?.riskLevel || 'medium',
          });

          // Create notification
          await db.insert(notifications).values({
            userId: ctx.user?.id || 1,
            type: action === 'BUY' ? 'info' : 'warning',
            title: `TradingView Alert: ${symbol}`,
            message: `${action} signal at $${price}. Combined score: ${signal.confidence}%`,
            data: JSON.stringify(signal),
          });

          return { success: true, signal };
        }
      }

      return { success: true };
    }),
});
```

---

## 6. Free Database Setup (PostgreSQL)

### 6.1 Docker Compose for Local Database

```yaml
# docker-compose.yml
version: '3.8'

services:
  # PostgreSQL (FREE, self-hosted)
  postgres:
    image: postgres:16-alpine
    container_name: crypto_platform_db
    environment:
      POSTGRES_USER: crypto_user
      POSTGRES_PASSWORD: crypto_pass_2024
      POSTGRES_DB: crypto_platform
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init-db.sql:/docker-entrypoint-initdb.d/init-db.sql
    restart: unless-stopped
    healthcheck:
      test: ['CMD-SHELL', 'pg_isready -U crypto_user']
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis (FREE, self-hosted)
  redis:
    image: redis:7-alpine
    container_name: crypto_platform_redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    command: redis-server --appendonly yes
    healthcheck:
      test: ['CMD', 'redis-cli', 'ping']
      interval: 10s
      timeout: 5s
      retries: 5

  # pgAdmin (FREE database management UI)
  pgadmin:
    image: dpage/pgadmin4:latest
    container_name: crypto_platform_pgadmin
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@crypto.local
      PGADMIN_DEFAULT_PASSWORD: admin
      PGADMIN_CONFIG_SERVER_MODE: 'False'
    ports:
      - "5050:80"
    volumes:
      - pgadmin_data:/var/lib/pgadmin
    restart: unless-stopped

  # Prometheus (FREE monitoring)
  prometheus:
    image: prom/prometheus:latest
    container_name: crypto_platform_prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    restart: unless-stopped

  # Grafana (FREE dashboards)
  grafana:
    image: grafana/grafana:latest
    container_name: crypto_platform_grafana
    ports:
      - "3001:3000"
    environment:
      GF_SECURITY_ADMIN_USER: admin
      GF_SECURITY_ADMIN_PASSWORD: admin
      GF_USERS_ALLOW_SIGN_UP: 'false'
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  pgadmin_data:
  prometheus_data:
  grafana_data:
```

### 6.2 Free Hosting Options

| Platform | Free Tier | Limitations |
|----------|-----------|-------------|
| **Railway** | $5 credit/month | 512MB RAM, 1GB storage |
| **Render** | Free tier | 512MB RAM, sleeps after inactivity |
| **Clever Cloud** | Free tier | 256MB RAM |
| **Fly.io** | Free allowance | 3 small VMs, 3GB bandwidth |
| **Self-hosted** | $0 | Your own hardware/VPS |

---

## 7. Free API Services Implementation

### 7.1 Market Data Service (All Free)

```typescript
// server/services/marketData.ts - FREE market data aggregation
import axios from 'axios';

class FreeMarketDataService {
  private coinGeckoBaseUrl = 'https://api.coingecko.com/api/v3';
  private binanceBaseUrl = 'https://api.binance.com/api/v3';

  // Get price from CoinGecko (FREE - 100 calls/min)
  async getPrice(symbol: string) {
    try {
      const response = await axios.get(
        `${this.coinGeckoBaseUrl}/simple/price`,
        {
          params: {
            ids: this.getCoinGeckoId(symbol),
            vs_currencies: 'usd',
            include_24hr_change: true,
            include_market_cap: true,
          },
        }
      );
      return response.data;
    } catch (error) {
      console.error('CoinGecko error:', error);
      return null;
    }
  }

  // Get OHLCV from Binance (FREE - no rate limit)
  async getOHLCV(symbol: string, interval: string = '15m') {
    try {
      const response = await axios.get(
        `${this.binanceBaseUrl}/klines`,
        {
          params: {
            symbol: symbol.replace('/', ''), // e.g., BTCUSDT
            interval,
            limit: 100,
          },
        }
      );

      return response.data.map((k: any) => ({
        timestamp: k[0],
        open: parseFloat(k[1]),
        high: parseFloat(k[2]),
        low: parseFloat(k[3]),
        close: parseFloat(k[4]),
        volume: parseFloat(k[5]),
      }));
    } catch (error) {
      console.error('Binance error:', error);
      return null;
    }
  }

  // Get ticker data from Binance (FREE)
  async getTicker24h(symbol: string) {
    try {
      const response = await axios.get(
        `${this.binanceBaseUrl}/ticker/24hr`,
        {
          params: { symbol: symbol.replace('/', '') },
        }
      );
      return {
        priceChange: parseFloat(response.data.priceChange),
        priceChangePercent: parseFloat(response.data.priceChangePercent),
        highPrice: parseFloat(response.data.highPrice),
        lowPrice: parseFloat(response.data.lowPrice),
        volume: parseFloat(response.data.volume),
      };
    } catch (error) {
      return null;
    }
  }

  private getCoinGeckoId(symbol: string): string {
    const ids: Record<string, string> = {
      'BTC': 'bitcoin',
      'ETH': 'ethereum',
      'BNB': 'binancecoin',
      'ADA': 'cardano',
      'SOL': 'solana',
      'DOT': 'polkadot',
      'MATIC': 'matic-network',
      'AVAX': 'avalanche-2',
      'LINK': 'chainlink',
      'UNI': 'uniswap',
    };
    return ids[symbol] || symbol.toLowerCase();
  }
}

export const marketDataService = new FreeMarketDataService();
```

### 7.2 GitHub Analysis (Free)

```typescript
// server/services/githubAnalyzer.ts - FREE GitHub API
import axios from 'axios';

class FreeGitHubAnalyzer {
  private baseUrl = 'https://api.github.com';

  async analyzeRepository(repoUrl: string) {
    // Extract owner/repo from URL
    const match = repoUrl.match(/github\.com\/([^\/]+)\/([^\/]+)/);
    if (!match) return null;

    const [, owner, repo] = match;

    try {
      // Get repo data (FREE - 5000 requests/hour)
      const repoResponse = await axios.get(
        `${this.baseUrl}/repos/${owner}/${repo}`
      );

      // Get contributors (FREE)
      const contributorsResponse = await axios.get(
        `${this.baseUrl}/repos/${owner}/${repo}/contributors`,
        { params: { per_page: 10 } }
      );

      // Get commits (FREE)
      const commitsResponse = await axios.get(
        `${this.baseUrl}/repos/${owner}/${repo}/commits`,
        { params: { per_page: 30 } }
      );

      // Get issues (FREE)
      const issuesResponse = await axios.get(
        `${this.baseUrl}/repos/${owner}/${repo}/issues`,
        { params: { state: 'all', per_page: 100 } }
      );

      // Calculate scores
      const score = this.calculateScore({
        stars: repoResponse.data.stargazers_count,
        forks: repoResponse.data.forks_count,
        contributors: contributorsResponse.data.length,
        recentCommits: this.getRecentCommits(commitsResponse.data),
        openIssues: issuesResponse.data.filter((i: any) => i.state === 'open').length,
      });

      return {
        score,
        data: {
          stars: repoResponse.data.stargazers_count,
          forks: repoResponse.data.forks_count,
          contributors: contributorsResponse.data.length,
          openIssues: issuesResponse.data.filter((i: any) => i.state === 'open').length,
          lastCommit: commitsResponse.data[0]?.commit.author.date,
        },
      };
    } catch (error) {
      console.error('GitHub API error:', error);
      return null;
    }
  }

  private calculateScore(data: any): number {
    let score = 0;

    // Stars (max 30 points)
    score += Math.min(30, data.stars / 100);

    // Forks (max 20 points)
    score += Math.min(20, data.forks / 50);

    // Contributors (max 25 points)
    score += Math.min(25, data.contributors * 2);

    // Recent activity (max 25 points)
    const recentCommits = data.recentCommits; // Last 30 days
    score += Math.min(25, recentCommits / 2);

    return Math.round(score);
  }

  private getRecentCommits(commits: any[]): number {
    const thirtyDaysAgo = Date.now() - 30 * 24 * 60 * 60 * 1000;
    return commits.filter((c: any) => {
      const commitDate = new Date(c.commit.author.date).getTime();
      return commitDate > thirtyDaysAgo;
    }).length;
  }
}

export const githubAnalyzer = new FreeGitHubAnalyzer();
```

### 7.3 Gemini AI Integration (Your Only Paid Service)

```typescript
// server/services/aiAnalyzer.ts - Using Gemini API
import { GoogleGenerativeAI } from '@google/generative-ai';

class GeminiAnalyzer {
  private genAI: GoogleGenerativeAI;
  private model: any;

  constructor() {
    this.genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY!);
    this.model = this.genAI.getGenerativeModel({ model: 'gemini-pro' });
  }

  async analyzeProject(projectData: any, auditData: any) {
    const prompt = `
You are a cryptocurrency investment analyst. Analyze this project:

PROJECT: ${projectData.name}
Symbol: ${projectData.symbol}

AUDIT SCORES:
- GitHub Score: ${auditData.githubScore}/100
- Tokenomics Score: ${auditData.tokenomicsScore}/100
- Contract Risk Score: ${auditData.contractRiskScore}/100
- Social Media Score: ${auditData.socialScore}/100
- Overall Score: ${auditData.overallScore}/100
- Risk Level: ${auditData.riskLevel}

Provide:
1. Investment recommendation (STRONG_BUY, BUY, HOLD, WAIT, AVOID)
2. Key strengths (2-3 points)
3. Key risks (2-3 points)
4. Suggested entry price (if applicable)
5. Suggested stop loss percentage
6. Suggested take profit levels
7. Overall confidence score (0-100)

Format as JSON.
    `;

    try {
      const result = await this.model.generateContent(prompt);
      const response = await result.response;
      const text = response.text();

      // Parse JSON response
      const analysis = JSON.parse(text);

      return {
        recommendation: analysis.recommendation,
        strengths: analysis.strengths,
        risks: analysis.risks,
        entryPrice: analysis.entryPrice,
        stopLoss: analysis.stopLoss,
        takeProfit: analysis.takeProfit,
        confidence: analysis.confidence,
      };
    } catch (error) {
      console.error('Gemini API error:', error);
      return null;
    }
  }

  async generateTradingSignal(auditScore: number, marketData: any) {
    const prompt = `
Generate a trading signal based on:
- Audit Score: ${auditScore}/100
- Current Price: $${marketData.price}
- 24h Change: ${marketData.change24h}%
- Volume: ${marketData.volume}

Provide signal as JSON: { action: "BUY"|"SELL"|"HOLD", confidence: 0-100, reasoning: string }
    `;

    try {
      const result = await this.model.generateContent(prompt);
      const response = await result.response;
      return JSON.parse(response.text());
    } catch (error) {
      return null;
    }
  }
}

export const geminiAnalyzer = new GeminiAnalyzer();
```

---

## 8. Updated .env File (All Free Except Gemini)

```bash
# .env - FREE configuration

# Database (Self-hosted, FREE)
DATABASE_URL=postgresql://crypto_user:crypto_pass@localhost:5432/crypto_platform

# Redis (Self-hosted, FREE)
REDIS_URL=redis://localhost:6379

# Gemini API (Your only paid service)
GEMINI_API_KEY=your_gemini_api_key_here

# JWT Auth (Self-hosted, FREE)
JWT_SECRET=your-secret-key-change-in-production
JWT_EXPIRY=7d

# GitHub API (FREE - 5000/hour)
GITHUB_TOKEN=your_github_token_optional

# CoinGecko API (FREE - 100/min)
COINGECKO_API_KEY=not_required_for_free_tier

# TradingView (Your subscription)
TRADINGVIEW_WIDGET_URL=https://s3.tradingview.com/tv.js

# Email (Resend - 100/day FREE)
RESEND_API_KEY=your_resend_key_optional

# Server (Self-hosted, FREE)
PORT=3000
NODE_ENV=development

# File Storage (Local filesystem, FREE)
UPLOAD_DIR=./uploads

# Frontend (Local, FREE)
VITE_FRONTEND_URL=http://localhost:3000

# Monitoring (Self-hosted, FREE)
PROMETHEUS_PORT=9090
GRAFANA_PORT=3001

# Logs (Local filesystem, FREE)
LOG_DIR=./logs
```

---

## 9. Free Deployment Options

### 9.1 Local Development (Recommended)

```bash
# Start all services locally
docker-compose up -d

# Run your app
pnpm dev

# Total cost: $0/month
```

### 9.2 Free Cloud Hosting

```yaml
# Option 1: Railway (has $5 free credit)
# - PostgreSQL: Free
# - Redis: Free
# - App: Free with credit
# Total: $0 (until credit used)

# Option 2: Self-hosted on VPS
# - Hetzner: $3.50/month for CX22
# - DigitalOcean: $4/month
# - Or use your own hardware
```

### 9.3 Free CI/CD

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3  # FREE

      - uses: actions/setup-node@v3  # FREE
        with:
          node-version: '20'

      - run: pnpm install  # FREE
      - run: pnpm build    # FREE

      # Deploy to Railway (FREE tier)
      - uses: railwayapp/cli@latest
        with:
          railway_token: ${{ secrets.RAILWAY_TOKEN }}
```

---

## 10. Cost Summary

### 10.1 Monthly Cost Breakdown

| Service | Cost | Notes |
|---------|------|-------|
| PostgreSQL | $0 | Self-hosted |
| Redis | $0 | Self-hosted |
| Auth (JWT/NextAuth) | $0 | Self-hosted |
| Gemini API | ~$2-20 | Your only cost (varies by usage) |
| Market Data APIs | $0 | Free tiers |
| GitHub API | $0 | Free tier |
| TradingView | $0 | You already subscribe |
| File Storage | $0 | Local filesystem |
| Monitoring | $0 | Self-hosted |
| Email | $0 | Resend free tier or skip |
| **TOTAL** | **~$2-20/month** | Only Gemini API! |

### 10.2 vs Paid Solutions

| Component | Paid Option | Free Option | Savings |
|-----------|-------------|-------------|---------|
| Database | Supabase Pro ($25) | Self-hosted PG | $25/month |
| Auth | Auth0 ($25) | NextAuth/JWT | $25/month |
| AI | OpenAI ($100+) | Gemini ($2-20) | $80+/month |
| Storage | AWS S3 ($20) | Local filesystem | $20/month |
| Monitoring | Datadog ($50+) | Prometheus/Grafana | $50+/month |
| Email | SendGrid ($20) | Resend free | $20/month |
| **Total Savings** | | | **~$220+/month** |

---

## 11. Integration Tasks (Updated for Free Stack)

### Phase 1: Setup (Day 1-2)

- [ ] Set up Docker Compose with PostgreSQL, Redis
- [ ] Configure NextAuth.js or custom JWT auth
- [ ] Set up Gemini API integration
- [ ] Install free monitoring (Prometheus/Grafana)

### Phase 2: Backend (Day 3-7)

- [ ] Implement free market data service
- [ ] Implement free GitHub analyzer
- [ ] Implement Gemini AI analyzer
- [ ] Create TradingView webhook endpoint
- [ ] Build combined signal generator

### Phase 3: Frontend (Day 8-12)

- [ ] Integrate TradingView charts
- [ ] Build trading dashboard
- [ ] Connect audit data with trading signals
- [ ] Create alerts system

### Phase 4: Testing (Day 13-14)

- [ ] Test all free APIs
- [ ] Test TradingView integration
- [ ] Load testing
- [ ] Documentation

---

## 12. Key Implementation Files

### Free Service Architecture

```
crypto-intelligence-platform/
├── docker-compose.yml          # FREE local stack
├── .env                        # FREE config (Gemini only)
├── server/
│   ├── services/
│   │   ├── marketData.ts       # FREE APIs (CoinGecko, Binance)
│   │   ├── githubAnalyzer.ts   # FREE GitHub API
│   │   ├── geminiAnalyzer.ts   # Your Gemini API
│   │   └── signalGenerator.ts  # Combined signals
│   ├── routers/
│   │   ├── tradingview.ts      # Webhook receiver
│   │   └── signals.ts          # Signal endpoints
│   └── _core/
│       └── auth.ts             # FREE JWT auth
└── client/
    └── src/
        └── components/
            ├── Trading/
            │   └── TradingViewChart.tsx
            └── Dashboard/
                └── SignalDashboard.tsx
```

---

## Summary: Your 100% Free Stack

| What You Need | Cost |
|---------------|------|
| ✅ Gemini API key | ~$2-20/month (you have) |
| ✅ TradingView sub | $0 (you already pay) |
| ✅ Everything else | **$0** (self-hosted) |

**Total Monthly Cost: $2-20** (only Gemini API)

All other services are:
- Open-source (PostgreSQL, Redis, Prometheus, Grafana)
- Free tiers (CoinGecko, GitHub, Binance APIs)
- Self-hosted (Auth, file storage, monitoring)

---

*Updated for 100% Free Stack*
*Document Version: 2.0*
*Last Updated: 2026-01-22*
