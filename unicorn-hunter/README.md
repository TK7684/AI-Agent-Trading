# Unicorn Hunter - CrewAI Multi-Agent System

A Python microservice that uses CrewAI to find high-potential crypto assets (unicorns) currently in accumulation phase.

## Architecture

The system uses three specialized agents:

1. **Scanner Agent (The Radar)** - Scans market for assets meeting "Bottom" criteria:
   - Market Cap: $10M - $100M
   - Price from ATH: Down >80%
   - Volume Spike: >300% of average

2. **Researcher Agent (The Detective)** - Validates fundamentals:
   - GitHub activity analysis
   - Technology assessment
   - Social sentiment tracking

3. **Sniper Agent (The Executor)** - Confirms technical entry:
   - RSI Bullish Divergence detection
   - Wyckoff Spring pattern detection
   - Entry/Stop-loss/Take-profit calculation

## Setup

### Prerequisites

- Python 3.10+
- pip or poetry

### Installation

```bash
cd unicorn-hunter

# Install dependencies
pip install -r unicorn_hunter/requirements.txt

# Or using poetry
poetry install
```

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp unicorn_hunter/.env.example unicorn_hunter/.env
```

Edit `.env` with your API keys:

```env
# Binance API (optional - for higher rate limits)
BINANCE_API_KEY=your_key_here
BINANCE_API_SECRET=your_secret_here

# GitHub API (optional - for private repos)
GITHUB_TOKEN=your_token_here

# OpenAI API (for CrewAI agents)
OPENAI_API_KEY=your_openai_key_here
```

## Running

### Development Mode

```bash
cd unicorn-hunter
python -m unicorn_hunter.main
```

The server will start on `http://localhost:8000`

### Production Mode

```bash
# Using uvicorn directly
uvicorn unicorn_hunter.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Endpoints

### Health Check

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "ok",
  "service": "unicorn-hunter"
}
```

### Start Scan

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "scan_type": "crypto",
    "min_market_cap": 10000000,
    "max_market_cap": 100000000,
    "min_price_drop": 80,
    "min_volume_spike": 300
  }'
```

Response:
```json
{
  "scan_id": "uuid-here",
  "status": "pending",
  "message": "Scan started with ID: uuid-here"
}
```

### Check Status

```bash
curl http://localhost:8000/status/{scan_id}
```

### Get Results

```bash
curl http://localhost:8000/results/{scan_id}
```

Response:
```json
{
  "scan_id": "uuid-here",
  "status": "completed",
  "candidates": [
    {
      "symbol": "UNIUSDT",
      "name": "UNI",
      "unicorn_score": 85,
      "recommendation": "BUY",
      "entry_price": 4.59,
      "stop_loss": 4.20,
      "take_profit": 5.80,
      "scanner_score": 88,
      "fundamental_score": 82,
      "technical_score": 85,
      "analysis_notes": [
        "✓ RSI Bullish Divergence detected",
        "✓ Wyckoff Spring pattern detected",
        "✓ Volume confirms reversal"
      ]
    }
  ],
  "summary": {
    "total_scanned": 150,
    "candidates_found": 3
  }
}
```

## Integration with Node.js Backend

The Node.js backend calls this Python service via HTTP:

1. `server/services/unicornHunter.ts` - Service layer
2. `server/db-unicorn.ts` - Database operations
3. `server/routers.ts` - tRPC endpoints (`unicorn.startScan`, `unicorn.getScan`, `unicorn.listScans`)

## Testing

### Test Python Service Directly

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test scan
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"scan_type": "crypto"}'
```

### Test via Node.js Backend

1. Start Node.js server: `pnpm dev`
2. Start Python server: `python -m unicorn-hunter/unicorn_hunter/main`
3. Call tRPC endpoint from frontend

## Troubleshooting

### Import Error

If you get import errors, ensure you're running from the correct directory:

```bash
cd unicorn-hunter
python -m unicorn_hunter.main
```

### Binance API Issues

The service works without Binance API keys but with lower rate limits. For production, get free API keys from [Binance](https://www.binance.com/en/my/settings/api-management).

### Database Connection

The Node.js backend handles database operations. The Python service only returns results via HTTP.

## Project Structure

```
unicorn-hunter/
├── unicorn_hunter/
│   ├── __init__.py
│   ├── main.py              # FastAPI server
│   ├── config.py            # Configuration
│   ├── requirements.txt     # Dependencies
│   ├── .env.example         # Environment template
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── scanner.py       # Scanner Agent
│   │   ├── researcher.py    # Researcher Agent
│   │   └── sniper.py        # Sniper Agent
│   └── tools/
│       ├── __init__.py
│       ├── market_tools.py  # Binance API
│       ├── github_tools.py  # GitHub API
│       └── social_tools.py  # Social sentiment
└── README.md
```

## License

MIT
