# Investment Auditor API Documentation

## Overview

The Investment Auditor API provides comprehensive cryptocurrency project analysis, security scanning, and market data services. All endpoints are available via tRPC for type-safe integration.

**Base URL:** `https://api.investor-auditor.com/api`

**Authentication:** Bearer JWT token (set via HTTP-only cookie)

---

## Table of Contents

- [Authentication](#authentication)
- [Projects](#projects)
- [Discovery](#discovery)
- [Market Data](#market-data)
- [Security Analysis](#security-analysis)
- [AI Chat Bot](#ai-chat-bot)
- [Watchlist](#watchlist)
- [Alerts](#alerts)
- [Notifications](#notifications)
- [Subscription](#subscription)
- [Rate Limiting](#rate-limiting)

---

## Authentication

All protected endpoints require a valid JWT token. The token is automatically sent via HTTP-only cookie after login.

### Login

```typescript
mutation {
  auth: {
    login(input: { email: string, password: string })
  }
}
```

**Response:**
```typescript
{
  success: true,
  user: {
    id: number,
    email: string,
    name: string,
    role: 'user' | 'pro' | 'enterprise' | 'admin'
  }
}
```

### Register

```typescript
mutation {
  auth: {
    register(input: { email: string, password: string, name?: string })
  }
}
```

---

## Projects

### Create Project

`project.create`

Creates a new project for analysis.

**Input:**
```typescript
{
  name: string,           // Project name
  description?: string,   // Project description
  githubUrl?: string,     // GitHub repository URL
  contractAddress?: string, // Contract address (0x...)
  chain?: string,         // Blockchain (ethereum, bsc, polygon, etc.)
  websiteUrl?: string,    // Website URL
  twitterUrl?: string,    // Twitter URL
  telegramUrl?: string,   // Telegram URL
  discordUrl?: string     // Discord URL
}
```

**Response:**
```typescript
{
  projectId: number,
  reportId: number
}
```

### List Projects

`project.list`

Get all projects for the authenticated user.

**Response:** Array of project objects with audit reports.

### Get Project Details

`project.getById`

Get detailed information about a specific project.

**Input:**
```typescript
{ id: number }
```

**Response:**
```typescript
{
  project: Project,
  report: AuditReport
}
```

### Analyze Project

`project.analyze`

Start comprehensive analysis of a project.

**Input:**
```typescript
{ projectId: number }
```

**Response:**
```typescript
{
  success: boolean,
  overallScore: number,    // 0-100
  riskLevel: 'low' | 'medium' | 'high' | 'critical',
  scores: {
    github: number,
    tokenomics: number,
    contractRisk: number,
    twitter: number,
    telegram: number,
    discord: number
  }
}
```

---

## Discovery

### Trending Projects

`discovery.trending`

Discover trending and new cryptocurrency projects.

**Input (optional):**
```typescript
{
  category?: string,      // Filter by category
  status?: 'trending' | 'new' | 'hot' | 'established',
  minScore?: number,      // Minimum recommendation score (0-100)
  maxMarketCap?: number   // Maximum market cap
}
```

**Response:** Array of `DiscoveredProject`

### Get Categories

`discovery.getCategories`

Get all available project categories.

**Response:** Array of category strings.

---

## Market Data

### Get Price

`marketData.getPrice`

Get current price data for a cryptocurrency.

**Input:**
```typescript
{
  symbol: string,       // e.g., "BTC", "ETH"
  useCache?: boolean    // Default: true
}
```

**Response:**
```typescript
{
  symbol: string,
  price: number,
  change24h: number,
  marketCap: number,
  volume24h: number,
  high24h: number,
  low24h: number,
  ath: number,
  athChange: number
}
```

### Get OHLCV Data

`marketData.getOHLCV`

Get candlestick data for charting.

**Input:**
```typescript
{
  symbol: string,
  interval?: '1m' | '3m' | '5m' | '15m' | '30m' | '1h' | '2h' | '4h' | '1d' | '1w',
  limit?: number         // Default: 100, Max: 1000
}
```

**Response:** Array of OHLCV data points.

### Get 24h Ticker

`marketData.getTicker24h`

Get 24-hour ticker statistics.

**Input:**
```typescript
{ symbol: string }
```

### Get Top Coins

`marketData.getTopCoins`

Get top cryptocurrencies by market cap.

**Input (optional):**
```typescript
{
  limit?: number,        // Default: 50, Max: 250
  currency?: 'usd' | 'eur' | 'btc' | 'eth'
}
```

### Search Coins

`marketData.searchCoins`

Search for cryptocurrencies by name or symbol.

**Input:**
```typescript
{ query: string }
```

---

## Security Analysis

### Honeypot Check

`security.honeypotCheck`

Quick check if a token is a honeypot.

**Input:**
```typescript
{
  contractAddress: string,  // 0x...
  chain?: string            // Default: "ethereum"
}
```

**Response:**
```typescript
{
  isHoneypot: boolean,
  confidence: number,
  riskScore: number,        // 0-100
  details?: SecurityAnalysis
}
```

### Enhanced Tokenomics

`security.tokenomicsEnhanced`

Comprehensive tokenomics analysis with GoPlus Security integration.

**Input:**
```typescript
{
  contractAddress: string,
  chain?: string
}
```

### Enhanced Contract Risk

`security.contractRiskEnhanced`

Comprehensive contract risk analysis.

**Input:**
```typescript
{
  contractAddress: string,
  chain?: string
}
```

**Response:**
```typescript
{
  score: number,
  data: ContractData,
  analysis: string,
  risks: string[],
  safetyFeatures: string[],
  goPlusSecurity?: SecurityAnalysis,
  honeypotDetected: boolean,
  overallRiskLevel: 'low' | 'medium' | 'high' | 'critical'
}
```

### Security Report

`security.securityReport`

Comprehensive security report combining all analysis.

**Input:**
```typescript
{
  contractAddress: string,
  chain?: string
}
```

**Response:**
```typescript
{
  overall: {
    riskLevel: string,
    riskScore: number,
    honeypotDetected: boolean,
    recommendation: string
  },
  goPlusSecurity?: SecurityAnalysis,
  contractRisk?: EnhancedContractRiskResult,
  tokenomics?: EnhancedTokenomicsResult
}
```

### Batch Analyze

`security.batchAnalyze`

Analyze multiple contracts at once (up to 20).

**Input:**
```typescript
{
  contracts: Array<{
    address: string,
    chain?: string
  }>
}
```

---

## AI Chat Bot

### Chat

`chat.chat`

Send a message to the AI assistant.

**Input:**
```typescript
{
  message: string,      // 1-2000 characters
  projectId?: number,   // Optional: for project-specific questions
  conversationId?: string
}
```

**Response:**
```typescript
{
  response: string,
  sources?: string[],
  confidence?: number
}
```

### Get History

`chat.getHistory`

Get conversation history.

**Input (optional):**
```typescript
{ conversationId?: string }
```

### Clear History

`chat.clearHistory`

Clear conversation history.

**Input (optional):**
```typescript
{ conversationId?: string }
```

### Suggested Questions

`chat.suggestedQuestions`

Get suggested questions for a project.

**Input (optional):**
```typescript
{ projectId?: number }
```

---

## Watchlist

### Add to Watchlist

`watchlist.add`

Add a project to your watchlist.

**Input:**
```typescript
{
  projectId: number,
  notes?: string
}
```

### Remove from Watchlist

`watchlist.remove`

Remove a project from your watchlist.

**Input:**
```typescript
{ projectId: number }
```

### List Watchlist

`watchlist.list`

Get all watchlist items.

**Response:** Array of watchlist items with project details.

### Check in Watchlist

`watchlist.isInWatchlist`

Check if a project is in your watchlist.

**Input:**
```typescript
{ projectId: number }
```

---

## Alerts

### Create Alert

`alerts.create`

Create a price or score change alert.

**Input:**
```typescript
{
  projectId: number,
  priceChangePercent?: number,  // Alert when price changes by X%
  scoreChangePoints?: number    // Alert when score changes by X points
}
```

### List Alerts

`alerts.list`

Get all active alerts.

### Delete Alert

`alerts.delete`

Delete an alert.

**Input:**
```typescript
{ alertId: number }
```

### Monitor Status

`alerts.monitorStatus`

Get the alert monitor status (admin).

**Response:**
```typescript
{
  isRunning: boolean,
  lastCheckTime: number,
  trackedProjects: number
}
```

---

## Notifications

### List Notifications

`notifications.list`

Get user notifications.

**Input (optional):**
```typescript
{
  unreadOnly?: boolean,   // Default: false
  limit?: number          // Default: 50
}
```

### Mark as Read

`notifications.markRead`

Mark a notification as read.

**Input:**
```typescript
{ notificationId: number }
```

### Mark All as Read

`notifications.markAllRead`

### Delete Notification

`notifications.delete`

**Input:**
```typescript
{ notificationId: number }
```

### Unread Count

`notifications.unreadCount`

Get count of unread notifications.

---

## Subscription

### Get Current Subscription

`subscription.getCurrent`

Get current subscription details.

**Response:**
```typescript
{
  tier: 'free' | 'pro' | 'enterprise',
  role: string,
  limits: {
    auditsPerMonth: number,
    watchlistLimit: number,
    alertsLimit: number,
    apiRateLimit: number
  },
  features: string[],
  pricing: {
    monthly: number,
    yearly: number
  }
}
```

### Get Tiers

`subscription.getTiers`

Get available subscription tiers with pricing.

### Check Feature Access

`subscription.checkFeature`

Check if user has access to a specific feature.

**Input:**
```typescript
{ feature: string }
```

### Upgrade Subscription

`subscription.upgrade`

Upgrade to a paid tier.

**Input:**
```typescript
{
  tier: 'pro' | 'enterprise',
  billingPeriod: 'monthly' | 'yearly'
}
```

### Get Usage

`subscription.getUsage`

Get current usage statistics.

**Response:**
```typescript
{
  auditsThisMonth: number,
  auditsLimit: number,
  watchlistCount: number,
  watchlistLimit: number,
  alertsCount: number,
  alertsLimit: number,
  apiCallsThisMinute: number,
  apiRateLimit: number
}
```

---

## Rate Limiting

API requests are rate limited based on your subscription tier:

| Tier | Requests/Minute | Burst |
|------|-----------------|-------|
| Free | 30 | 60 |
| Pro | 100 | 200 |
| Enterprise | 1000 | 2000 |

Rate limit headers are included in all responses:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

When rate limited, the API returns `429 Too Many Requests` with a retry-after time.

---

## Error Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 429 | Too Many Requests |
| 500 | Internal Server Error |

---

## TypeScript Types

All endpoints are fully typed. Import types from the API:

```typescript
import type { AppRouter } from '@investor-auditor/api';

type ProjectCreateInput = inferAsyncInput<AppRouter['project']['create']>;
type DiscoveredProject = inferAsyncOutput<AppRouter['discovery']['trending']>[number];
```

---

## WebSocket Support

Real-time updates are available via WebSocket for:

- Market price updates
- Alert notifications
- Analysis progress

Connect to: `wss://api.investor-auditor.com/ws`

---

## SDKs

Official SDKs are available:

- **JavaScript/TypeScript**: `npm install @investor-auditor/sdk`
- **Python**: `pip install investor-auditor`
- **Go**: `go get github.com/investor-auditor/go-sdk`

---

## Support

- Documentation: https://docs.investor-auditor.com
- GitHub: https://github.com/investor-auditor/api
- Support Email: support@investor-auditor.com
- Discord: https://discord.gg/investor-auditor
