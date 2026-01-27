/**
 * FREE Market Data Service
 * Uses CoinGecko, Binance, and other free APIs
 * No paid services required!
 */

import axios from "axios";

// Types
export interface PriceData {
  symbol: string;
  price: number;
  change24h: number;
  marketCap: number;
  volume24h: number;
  high24h: number;
  low24h: number;
  ath: number;
  athChange: number;
}

export interface OHLCVData {
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface TickerData {
  priceChange: number;
  priceChangePercent: number;
  highPrice: number;
  lowPrice: number;
  volume: number;
  quoteVolume: number;
}

// CoinGecko ID mapping for common cryptocurrencies
const COINGECKO_IDS: Record<string, string> = {
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
  'XRP': 'ripple',
  'DOGE': 'dogecoin',
  'LTC': 'litecoin',
  'BCH': 'bitcoin-cash',
  'ATOM': 'cosmos',
  'FIL': 'filecoin',
  'TRX': 'tron',
  'ETC': 'ethereum-classic',
  'XLM': 'stellar',
  'ALGO': 'algorand',
  'VET': 'vechain',
  'NEAR': 'near',
  'AAVE': 'aave',
  'APT': 'aptos',
  'ARB': 'arbitrum',
  'OP': 'optimism',
  'SUI': 'sui',
};

class FreeMarketDataService {
  private coinGeckoBaseUrl = 'https://api.coingecko.com/api/v3';
  private binanceBaseUrl = 'https://api.binance.com/api/v3';

  /**
   * Get price data from CoinGecko (FREE - 100 calls/min)
   */
  async getPrice(symbol: string): Promise<PriceData | null> {
    try {
      const coinGeckoId = this.getCoinGeckoId(symbol);
      const response = await axios.get(
        `${this.coinGeckoBaseUrl}/simple/price`,
        {
          params: {
            ids: coinGeckoId,
            vs_currencies: 'usd',
            include_24hr_change: true,
            include_market_cap: true,
            include_24hr_vol: true,
            include_last_updated_at: true,
          },
          timeout: 10000,
        }
      );

      const data = response.data[coinGeckoId];
      if (!data) {
        console.warn(`[MarketData] No data found for ${symbol}`);
        return null;
      }

      return {
        symbol,
        price: data.usd || 0,
        change24h: data.usd_24h_change || 0,
        marketCap: data.usd_market_cap || 0,
        volume24h: data.usd_24h_vol || 0,
        high24h: 0, // Not available in simple price endpoint
        low24h: 0,
        ath: 0,
        athChange: 0,
      };
    } catch (error) {
      console.error(`[MarketData] CoinGecko error for ${symbol}:`, error);
      return null;
    }
  }

  /**
   * Get detailed market data from CoinGecko
   */
  async getDetailedMarketData(symbol: string): Promise<PriceData | null> {
    try {
      const coinGeckoId = this.getCoinGeckoId(symbol);
      const response = await axios.get(
        `${this.coinGeckoBaseUrl}/coins/${coinGeckoId}`,
        {
          params: {
            localization: false,
            tickers: false,
            market_data: true,
            community_data: false,
            developer_data: false,
          },
          timeout: 10000,
        }
      );

      const data = response.data;
      const marketData = data.market_data || {};

      return {
        symbol,
        price: marketData.current_price?.usd || 0,
        change24h: marketData.price_change_percentage_24h || 0,
        marketCap: marketData.market_cap?.usd || 0,
        volume24h: marketData.total_volume?.usd || 0,
        high24h: marketData.high_24h?.usd || 0,
        low24h: marketData.low_24h?.usd || 0,
        ath: marketData.ath?.usd || 0,
        athChange: marketData.ath_change_percentage?.usd || 0,
      };
    } catch (error) {
      console.error(`[MarketData] Detailed data error for ${symbol}:`, error);
      // Fallback to simple price
      return this.getPrice(symbol);
    }
  }

  /**
   * Get OHLCV data from Binance (FREE - no rate limit for public data)
   */
  async getOHLCV(symbol: string, interval: string = '15m', limit: number = 100): Promise<OHLCVData[]> {
    try {
      // Convert symbol to Binance format (e.g., BTC/USDT -> BTCUSDT)
      const binanceSymbol = this.toBinanceSymbol(symbol);

      const response = await axios.get(
        `${this.binanceBaseUrl}/klines`,
        {
          params: {
            symbol: binanceSymbol,
            interval,
            limit,
          },
          timeout: 10000,
        }
      );

      return response.data.map((k: any[]) => ({
        timestamp: k[0],
        open: parseFloat(k[1]),
        high: parseFloat(k[2]),
        low: parseFloat(k[3]),
        close: parseFloat(k[4]),
        volume: parseFloat(k[5]),
      }));
    } catch (error) {
      console.error(`[MarketData] Binance OHLCV error for ${symbol}:`, error);
      return [];
    }
  }

  /**
   * Get 24h ticker data from Binance (FREE)
   */
  async getTicker24h(symbol: string): Promise<TickerData | null> {
    try {
      const binanceSymbol = this.toBinanceSymbol(symbol);

      const response = await axios.get(
        `${this.binanceBaseUrl}/ticker/24hr`,
        {
          params: { symbol: binanceSymbol },
          timeout: 10000,
        }
      );

      const data = response.data;
      return {
        priceChange: parseFloat(data.priceChange),
        priceChangePercent: parseFloat(data.priceChangePercent),
        highPrice: parseFloat(data.highPrice),
        lowPrice: parseFloat(data.lowPrice),
        volume: parseFloat(data.volume),
        quoteVolume: parseFloat(data.quoteVolume),
      };
    } catch (error) {
      console.error(`[MarketData] Binance ticker error for ${symbol}:`, error);
      return null;
    }
  }

  /**
   * Get top cryptocurrencies by market cap from CoinGecko
   */
  async getTopCoins(limit: number = 50, currency: string = 'usd'): Promise<any[]> {
    try {
      const response = await axios.get(
        `${this.coinGeckoBaseUrl}/coins/markets`,
        {
          params: {
            vs_currency: currency,
            order: 'market_cap_desc',
            per_page: limit,
            page: 1,
            sparkline: false,
          },
          timeout: 15000,
        }
      );

      return response.data.map((coin: any) => ({
        symbol: coin.symbol.toUpperCase(),
        name: coin.name,
        id: coin.id,
        price: coin.current_price,
        change24h: coin.price_change_percentage_24h,
        marketCap: coin.market_cap,
        volume24h: coin.total_volume,
        high24h: coin.high_24h,
        low24h: coin.low_24h,
        image: coin.image,
      }));
    } catch (error) {
      console.error('[MarketData] Top coins error:', error);
      return [];
    }
  }

  /**
   * Search for coins by name/symbol
   */
  async searchCoins(query: string): Promise<any[]> {
    try {
      const response = await axios.get(
        `${this.coinGeckoBaseUrl}/search`,
        {
          params: { query },
          timeout: 10000,
        }
      );

      return (response.data.coins || []).slice(0, 10).map((coin: any) => ({
        symbol: coin.symbol.toUpperCase(),
        name: coin.name,
        id: coin.id,
        marketCapRank: coin.market_cap_rank,
        thumb: coin.thumb,
      }));
    } catch (error) {
      console.error('[MarketData] Search error:', error);
      return [];
    }
  }

  /**
   * Get market categories
   */
  async getCategories(): Promise<string[]> {
    try {
      const response = await axios.get(
        `${this.coinGeckoBaseUrl}/coins/categories/list`,
        { timeout: 10000 }
      );

      return response.data.map((cat: any) => cat.name);
    } catch (error) {
      console.error('[MarketData] Categories error:', error);
      return [];
    }
  }

  /**
   * Get trending coins (searched most by users)
   */
  async getTrending(): Promise<any[]> {
    try {
      const response = await axios.get(
        `${this.coinGeckoBaseUrl}/search/trending`,
        { timeout: 10000 }
      );

      return (response.data.coins || []).map((item: any) => ({
        symbol: item.item.symbol,
        name: item.item.name,
        marketCapRank: item.item.market_cap_rank,
        thumb: item.item.thumb,
        score: item.item.score,
      }));
    } catch (error) {
      console.error('[MarketData] Trending error:', error);
      return [];
    }
  }

  /**
   * Convert symbol to CoinGecko ID
   */
  private getCoinGeckoId(symbol: string): string {
    const upperSymbol = symbol.toUpperCase();
    return COINGECKO_IDS[upperSymbol] || symbol.toLowerCase();
  }

  /**
   * Convert symbol to Binance format (e.g., BTC/USDT -> BTCUSDT)
   */
  private toBinanceSymbol(symbol: string): string {
    // Remove slashes and convert to uppercase
    return symbol.replace('/', '').toUpperCase() + 'USDT';
  }

  /**
   * Add a custom CoinGecko ID mapping
   */
  addCoinGeckoId(symbol: string, id: string): void {
    COINGECKO_IDS[symbol.toUpperCase()] = id;
  }

  /**
   * Get all supported CoinGecko IDs
   */
  getSupportedIds(): Record<string, string> {
    return { ...COINGECKO_IDS };
  }
}

// Export singleton instance
export const marketDataService = new FreeMarketDataService();

/**
 * In-memory cache fallback when Redis is not available
 */
const inMemoryCache = new Map<string, { data: any; expiry: number }>();
const IN_MEMORY_TTL = 60000; // 60 seconds

function getFromInMemoryCache(key: string): any | null {
  const cached = inMemoryCache.get(key);
  if (cached && cached.expiry > Date.now()) {
    return cached.data;
  }
  if (cached) {
    inMemoryCache.delete(key);
  }
  return null;
}

function setInMemoryCache(key: string, data: any): void {
  inMemoryCache.set(key, {
    data,
    expiry: Date.now() + IN_MEMORY_TTL,
  });
}

/**
 * Cache market data using Redis or in-memory fallback
 * This prevents hitting API rate limits
 */
export async function getCachedMarketData(symbol: string): Promise<PriceData | null> {
  const cacheKey = `market:price:${symbol}`;

  // Try Redis first (imported dynamically to avoid circular deps)
  try {
    const { cacheService } = await import('./cacheService');
    const cached = await cacheService.getPrice(symbol);
    if (cached) {
      return cached;
    }
  } catch (error) {
    console.warn('[MarketData] Redis cache unavailable, using in-memory fallback');
  }

  // Fallback to in-memory cache
  const memCached = getFromInMemoryCache(cacheKey);
  if (memCached) {
    return memCached;
  }

  // Fetch fresh data
  const data = await marketDataService.getDetailedMarketData(symbol);
  if (data) {
    // Try to cache in Redis
    try {
      const { cacheService } = await import('./cacheService');
      await cacheService.setPrice(symbol, data);
    } catch {
      // Fallback to in-memory
      setInMemoryCache(cacheKey, data);
    }
  }

  return data;
}

/**
 * Background job to update market data cache
 */
export async function updateMarketDataCache(symbols: string[]): Promise<void> {
  console.log(`[MarketData] Updating cache for ${symbols.length} symbols...`);

  for (const symbol of symbols) {
    const data = await marketDataService.getDetailedMarketData(symbol);
    if (data) {
      try {
        const { cacheService } = await import('./cacheService');
        await cacheService.setPrice(symbol, data);
      } catch {
        setInMemoryCache(`market:price:${symbol}`, data);
      }
    }
  }

  console.log('[MarketData] Cache update complete');
}
