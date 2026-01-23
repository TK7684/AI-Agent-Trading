# Unicorn Hunter - Implementation & Testing Plan

## Overview
Complete testing guide for the Unicorn Hunter CrewAI multi-agent system integration.

## Prerequisites Checklist

- [ ] Node.js installed (v18+)
- [ ] Python 3.10+ installed
- [ ] MySQL database running
- [ ] Git repository initialized

---

## Step 1: Database Migration

Run the database migration to create the new unicorn tables:

```bash
cd "Investment Auditor"
pnpm db:push
```

**Expected output**: New tables `unicornScans` and `unicornCandidates` created in MySQL.

**Verification**: Connect to MySQL and verify tables exist:
```sql
SHOW TABLES LIKE 'unicorn%';
-- Should show: unicornScans, unicornCandidates
```

---

## Step 2: Python Service Setup

### 2.1 Install Python Dependencies

```bash
cd unicorn-hunter
pip install -r unicorn_hunter/requirements.txt
```

**Note**: If using poetry instead of pip:
```bash
poetry install
```

### 2.2 Configure Environment

```bash
cd unicorn-hunter/unicorn_hunter
cp .env.example .env
```

Edit `.env` file (optional for testing - works without API keys):

```env
# Binance API (optional - public API works for testing)
BINANCE_API_KEY=
BINANCE_API_SECRET=

# GitHub API (optional)
GITHUB_TOKEN=

# Server (defaults work for local)
HOST=0.0.0.0
PORT=8000
DEBUG=true

# CORS (matches Node.js dev server)
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# Node.js URL
NODE_JS_URL=http://localhost:3000
```

### 2.3 Start Python Service

```bash
cd unicorn-hunter
python -m unicorn_hunter.main
```

**Expected output**:
```
Starting Unicorn Hunter API...
Uvicorn running on http://0.0.0.0:8000
```

---

## Step 3: Node.js Server Setup

### 3.1 Add Environment Variable

Add to your `.env` file in the root directory:

```env
UNICORN_HUNTER_API_URL=http://localhost:8000
```

### 3.2 Start Node.js Server

```bash
cd "Investment Auditor"
pnpm dev
```

**Expected output**: Server running on http://localhost:3000 (or next available port)

---

## Step 4: Testing - Health Check

### 4.1 Test Python Service Directly

Open a new terminal and run:

```bash
curl http://localhost:8000/health
```

**Expected response**:
```json
{
  "status": "ok",
  "service": "unicorn-hunter"
}
```

### 4.2 Test Health via tRPC

Use the tRPC playground or call from frontend:

```typescript
const health = await trpc.unicorn.health.query();
console.log(health);
// { healthy: true, service: "unicorn-hunter" }
```

---

## Step 5: Testing - Unicorn Scan

### 5.1 Start a Scan via tRPC

```typescript
const result = await trpc.unicorn.startScan.mutate({
  scanType: "crypto",
  minMarketCap: 10000000,      // $10M minimum
  maxMarketCap: 100000000,     // $100M maximum
  minPriceDrop: 80,            // 80% down from ATH
  minVolumeSpike: 300,         // 300% volume spike
});

console.log(result);
// { scanId: 1, pythonScanId: "uuid-here", status: "completed", candidatesFound: 3 }
```

**Expected behavior**:
1. Scan record created in database
2. Python service processes scan (takes 30-60 seconds)
3. Results saved to `unicornCandidates` table
4. Returns scan ID and candidate count

### 5.2 Get Scan Results

```typescript
const scanData = await trpc.unicorn.getScan.query({
  scanId: 1,
});

console.log(scanData);
// {
//   scan: { id: 1, userId: 1, scanType: "crypto", status: "completed", ... },
//   candidates: [
//     {
//       symbol: "UNIUSDT",
//       unicornScore: 85,
//       recommendation: "BUY",
//       entryPrice: "4.59",
//       stopLoss: "4.20",
//       takeProfit: "5.80",
//       ...
//     }
//   ]
// }
```

### 5.3 List All Scans

```typescript
const scans = await trpc.unicorn.listScans.query();

console.log(scans);
// Array of scan objects with metadata
```

---

## Step 6: Database Verification

Connect to MySQL and verify data:

```sql
-- Check scans
SELECT * FROM unicornScans ORDER BY createdAt DESC LIMIT 5;

-- Check candidates with unicorn scores
SELECT
  scanId,
  symbol,
  unicornScore,
  recommendation,
  entryPrice,
  stopLoss,
  takeProfit
FROM unicornCandidates
WHERE unicornScore >= 70
ORDER BY unicornScore DESC;

-- Count candidates by recommendation
SELECT recommendation, COUNT(*) as count
FROM unicornCandidates
GROUP BY recommendation;
```

---

## Step 7: Troubleshooting

### Issue: Python Service Won't Start

**Error**: `ModuleNotFoundError: No module named 'unicorn_hunter'`

**Solution**: Run from the correct directory:
```bash
cd unicorn-hunter
python -m unicorn_hunter.main
```

### Issue: Import Errors for pydantic-settings

**Error**: `ModuleNotFoundError: No module named 'pydantic_settings'`

**Solution**: Update requirements.txt or install manually:
```bash
pip install pydantic-settings
```

### Issue: Binance API Connection Error

**Error**: `ccxt base error: connection timeout`

**Solution**:
- Check internet connection
- Try without API keys (public access works)
- Binance public API may be rate-limited

### Issue: tRPC Returns "Unicorn Hunter API error"

**Error**: `Failed to start unicorn scan. Is the Python service running?`

**Solution**:
1. Verify Python service is running: `curl http://localhost:8000/health`
2. Check UNICORN_HUNTER_API_URL in Node.js `.env`
3. Check CORS settings in Python `.env`

### Issue: Scan Times Out

**Error**: `Scan timed out` after 5 minutes

**Solution**:
- The scan polls for 60 iterations x 5 seconds = 5 minutes max
- Increase timeout in `unicornHunter.ts` if needed
- Check Python service logs for errors

---

## Step 8: Production Deployment

### 8.1 Python Service (Recommended: Docker)

Create `unicorn-hunter/Dockerfile`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY unicorn_hunter/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY unicorn_hunter/ ./unicorn_hunter/

EXPOSE 8000

CMD ["uvicorn", "unicorn_hunter.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t unicorn-hunter .
docker run -p 8000:8000 --env-file .env unicorn-hunter
```

### 8.2 Environment Variables for Production

**Python (.env)**:
```env
HOST=0.0.0.0
PORT=8000
DEBUG=false
CORS_ORIGINS=https://your-domain.com
```

**Node.js (.env)**:
```env
UNICORN_HUNTER_API_URL=https://unicorn-hunter.your-domain.com
```

---

## Step 9: Performance Optimization

### Current Limitations
- Synchronous polling (blocks Node.js thread)
- No job queue (BullMQ recommended for production)
- No caching of API results

### Recommended Improvements

1. **Add Job Queue**:
   ```bash
   pnpm add bullmq
   ```
   Move scan processing to background job

2. **Add Redis Caching**:
   ```bash
   pnpm add ioredis
   ```
   Cache Binance API responses for 1-5 minutes

3. **Add Webhook Support**:
   Python service calls Node.js webhook when scan completes

---

## Step 10: Monitoring & Logging

### Python Service Logs

Add to `main.py`:
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Node.js Service Logs

Already integrated with existing logger. Add:
```typescript
console.log(`[UnicornHunter] Scan ${scanId} started`);
```

---

## Verification Checklist

- [ ] Python service starts without errors
- [ ] Health check returns `{"status": "ok"}`
- [ ] Database tables created (`unicornScans`, `unicornCandidates`)
- [ ] tRPC `unicorn.health` returns `{healthy: true}`
- [ ] Can start a scan via `unicorn.startScan`
- [ ] Scan completes and returns candidates
- [ ] Candidates saved to database
- [ ] Can retrieve results via `unicorn.getScan`
- [ ] Can list scans via `unicorn.listScans`

---

## API Reference

### tRPC Endpoints

| Endpoint | Type | Description |
|----------|------|-------------|
| `unicorn.health` | Query | Check Python service status |
| `unicorn.startScan` | Mutation | Start new unicorn hunt |
| `unicorn.getScan` | Query | Get scan results by ID |
| `unicorn.listScans` | Query | List user's scans |

### Python HTTP Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/analyze` | POST | Start scan |
| `/status/{scan_id}` | GET | Get scan status |
| `/results/{scan_id}` | GET | Get scan results |

---

## Next Steps After Testing

1. **Frontend Integration** - Create UI for unicorn hunting
2. **Alert System** - Notify users when new unicorns found
3. **Backtesting** - Test strategy on historical data
4. **Stock Market** - Expand to equities using yfinance
5. **Multi-chain** - Add Solana, BSC, Polygon support
