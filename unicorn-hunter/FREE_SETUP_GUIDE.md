# Unicorn Hunter - FREE Setup Guide

## **NO PAID SERVICES - Everything is FREE except Gemini API**

This guide shows how to set up the Unicorn Hunter using only free API services. The only API you may want to pay for is **Gemini API** (for AI analysis), but the system works without it too.

---

## Free API Sources (All Optional)

| Service | Free Tier | Credit Card Required? | Purpose |
|---------|-----------|----------------------|---------|
| **Binance (ccxt)** | Unlimited public API | No | Real-time price/volume data |
| **CoinGecko** | 50 calls/minute | No | Trending coins, market data |
| **TradingView** | Free widgets | No | Technical analysis charts |
| **Ethplorer** | No key required | No | Token holders, on-chain data |
| **Dune Analytics** | 1,000 requests/month | No | Custom on-chain queries |
| **Covalent** | 300,000 requests/month | No | Token transfers, holders |
| **Gemini** | Pay per use | Yes | AI analysis (optional) |

---

## Quick Start (Zero Configuration)

The system works with **NO API keys** for basic functionality:

```bash
cd unicorn-hunter/unicorn_hunter

# Install dependencies
pip install -r requirements.txt

# Copy minimal .env (no API keys needed!)
cat > .env << EOF
HOST=0.0.0.0
PORT=8000
DEBUG=true
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
ETHPLORER_API_KEY=freekey
EOF

# Run the service
cd ..
python -m unicorn_hunter.main
```

---

## Optional Free API Keys (For Better Performance)

### 1. CoinGecko (Optional but Recommended)

**Free tier:** 50 calls/minute, no credit card required

1. Go to https://www.coingecko.com/en/developers
2. Sign up for free account
3. Get your API key
4. Add to `.env`:
   ```
   COINGECKO_API_KEY=your_key_here
   ```

### 2. Dune Analytics (Optional)

**Free tier:** 1,000 requests/month, no credit card required

1. Go to https://app.dune.com/apikey
2. Connect with GitHub
3. Get your API key
4. Add to `.env`:
   ```
   DUNE_API_KEY=your_key_here
   ```

### 3. Covalent (Optional)

**Free tier:** 300,000 requests/month, no credit card required

1. Go to https://www.covalenthq.com/
2. Sign up for free account
3. Get your API key
4. Add to `.env`:
   ```
   COVALENT_API_KEY=your_key_here
   ```

### 4. Gemini API (Only Paid Option - Optional)

**For AI analysis features** - This is the only paid service. The system works without it, just without AI-powered summaries.

1. Go to https://ai.google.dev/
2. Create API key
3. Add to `.env`:
   ```
   GEMINI_API_KEY=your_key_here
   ```

---

## Configuration File

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env` with your optional API keys. The system works with **all fields empty** except for basic config.

---

## Data Sources Explained

### Completely FREE (No Key Required)

1. **Binance Public API** (via ccxt)
   - Real-time prices
   - Volume data
   - Market data
   - No rate limits for public endpoints

2. **TradingView Widgets** (HTML/JS)
   - Chart widgets for frontend
   - Technical indicators
   - Market screener
   - No API needed

3. **Ethplorer API**
   - Token holder count
   - Transfer history
   - Token info
   - Uses `apiKey=freekey` (built-in)

### Free Tiers (Optional Keys)

4. **CoinGecko** (Optional key)
   - Trending coins
   - Market data
   - Price history
   - Works without key (lower rate limit)

5. **Dune Analytics** (Free tier)
   - Custom SQL queries
   - On-chain metrics
   - 1,000 free queries/month

6. **Covalent** (Free tier)
   - Token transfers
   - Holder distribution
   - Multi-chain support
   - 300,000 free requests/month

---

## Usage Examples

### Basic Scan (No API Keys)

```python
POST http://localhost:8000/analyze
Content-Type: application/json

{
  "scan_type": "crypto",
  "min_market_cap": 10000000,
  "max_market_cap": 100000000,
  "min_price_drop": 80,
  "min_volume_spike": 300,
  "use_trending": false,
  "use_onchain": false
}
```

### Enhanced Scan (With Free APIs)

```python
POST http://localhost:8000/analyze
Content-Type: application/json

{
  "scan_type": "crypto",
  "min_market_cap": 10000000,
  "max_market_cap": 100000000,
  "min_price_drop": 80,
  "min_volume_spike": 300,
  "use_trending": true,
  "use_onchain": true
}
```

---

## API Rate Limits (Free Tiers)

| Service | Free Limit | What Happens When Exceeded |
|---------|-----------|---------------------------|
| Binance | No limit | None |
| CoinGecko (no key) | ~10-20 calls/min | Slower, but works |
| CoinGecko (with key) | 50 calls/min | Rate limit error |
| Ethplorer | ~150 requests/min | Rate limit error |
| Dune | 1,000 requests/month | Quota exceeded |
| Covalent | 300,000 requests/month | Quota exceeded |

---

## Troubleshooting

### Issue: "Rate limit exceeded"

**Solution:** Add free API keys for higher limits:
- CoinGecko: https://www.coingecko.com/en/developers
- Dune: https://app.dune.com/apikey

### Issue: "No token data"

**Solution:** Make sure `ETHPLORER_API_KEY=freekey` is in `.env`

### Issue: "Missing AI summaries"

**Solution:** Add Gemini API key (optional, paid):
```
GEMINI_API_KEY=your_key
```

---

## Cost Summary

| Feature | Cost |
|---------|------|
| Basic price scanning | **FREE** |
| Trending coins (CoinGecko) | **FREE** |
| Technical analysis (TradingView) | **FREE** |
| On-chain data (Ethplorer) | **FREE** |
| Custom queries (Dune) | **FREE** |
| AI summaries (Gemini) | **$0.001/1K tokens** (optional) |

**Total minimum cost: $0/month**

---

## Production Deployment

For production, consider:

1. **Use all free API keys** - Better rate limits
2. **Add caching** - Reduce API calls
3. **Implement rate limiting** - Stay within free tiers
4. **Monitor usage** - Track free tier quotas
5. **Add Gemini API** - For AI features ($1-5/month typical)

---

## Next Steps

1. Copy `.env.example` to `.env`
2. (Optional) Get free API keys from CoinGecko, Dune, Covalent
3. Run: `python -m unicorn_hunter.main`
4. Test: `curl http://localhost:8000/health`

---

## Support

For issues with free APIs:
- CoinGecko: https://www.coingecko.com/en/developers
- Dune: https://docs.dune.com/
- Covalent: https://www.covalenthq.com/docs/
- Ethplorer: https://github.com/EverexIO/Ethplorer/wiki/Ethplorer-API
