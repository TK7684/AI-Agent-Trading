/**
 * Redis Caching Service for Market Data
 * Provides caching layer for CoinGecko, Binance, and other external APIs
 */

import { createClient, RedisClientType } from 'redis';

// Types for cached data
export interface CachedPriceData {
  symbol: string;
  price: number;
  change24h: number;
  marketCap: number;
  volume24h: number;
  high24h: number;
  low24h: number;
  ath: number;
  athChange: number;
  lastUpdate: string;
}

export interface CachedOHLCVData {
  symbol: string;
  interval: string;
  data: Array<{
    timestamp: number;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
  }>;
  lastUpdate: string;
}

export interface CachedTickerData {
  symbol: string;
  priceChange: number;
  priceChangePercent: number;
  highPrice: number;
  lowPrice: number;
  volume: number;
  quoteVolume: number;
  lastUpdate: string;
}

class CacheService {
  private client: RedisClientType | null = null;
  private isConnected = false;
  private readonly DEFAULT_TTL = 60; // 60 seconds
  private readonly SHORT_TTL = 30; // 30 seconds for real-time data
  private readonly LONG_TTL = 300; // 5 minutes for historical data

  constructor() {
    this.connect();
  }

  private async connect() {
    try {
      if (!process.env.REDIS_URL) {
        console.warn('[Cache] REDIS_URL not configured, caching disabled');
        return;
      }

      this.client = createClient({
        url: process.env.REDIS_URL,
        socket: {
          connectTimeout: 5000,
          lazyConnect: true,
        },
        // Retry strategy
        retryDelayOnFailover: 100,
        retryDelayOnClusterDown: 300,
        maxRetriesPerRequest: 3,
      });

      await this.client.connect();
      this.isConnected = true;
      console.log('[Cache] Connected to Redis');
    } catch (error) {
      console.error('[Cache] Failed to connect to Redis:', error);
      this.isConnected = false;
    }
  }

  private async ensureConnection() {
    if (!this.isConnected || !this.client) {
      await this.connect();
    }
  }

  private getKey(prefix: string, identifier: string): string {
    return `crypto:${prefix}:${identifier}`;
  }

  // Price data caching
  async getPrice(symbol: string): Promise<CachedPriceData | null> {
    await this.ensureConnection();
    if (!this.client) return null;

    try {
      const cached = await this.client.get(this.getKey('price', symbol));
      return cached ? JSON.parse(cached) : null;
    } catch (error) {
      console.error(`[Cache] Error getting price for ${symbol}:`, error);
      return null;
    }
  }

  async setPrice(symbol: string, data: Omit<CachedPriceData, 'lastUpdate'>): Promise<void> {
    await this.ensureConnection();
    if (!this.client) return;

    try {
      const dataWithTimestamp = {
        ...data,
        lastUpdate: new Date().toISOString(),
      };
      await this.client.setEx(
        this.getKey('price', symbol),
        JSON.stringify(dataWithTimestamp),
        this.DEFAULT_TTL
      );
    } catch (error) {
      console.error(`[Cache] Error setting price for ${symbol}:`, error);
    }
  }

  // OHLCV data caching
  async getOHLCV(symbol: string, interval: string): Promise<CachedOHLCVData | null> {
    await this.ensureConnection();
    if (!this.client) return null;

    try {
      const cached = await this.client.get(this.getKey('ohlcv', `${symbol}:${interval}`));
      return cached ? JSON.parse(cached) : null;
    } catch (error) {
      console.error(`[Cache] Error getting OHLCV for ${symbol}:`, error);
      return null;
    }
  }

  async setOHLCV(symbol: string, interval: string, data: Array<any>): Promise<void> {
    await this.ensureConnection();
    if (!this.client) return;

    try {
      const dataWithTimestamp = {
        symbol,
        interval,
        data,
        lastUpdate: new Date().toISOString(),
      };
      await this.client.setEx(
        this.getKey('ohlcv', `${symbol}:${interval}`),
        JSON.stringify(dataWithTimestamp),
        this.SHORT_TTL
      );
    } catch (error) {
      console.error(`[Cache] Error setting OHLCV for ${symbol}:`, error);
    }
  }

  // Ticker data caching
  async getTicker(symbol: string): Promise<CachedTickerData | null> {
    await this.ensureConnection();
    if (!this.client) return null;

    try {
      const cached = await this.client.get(this.getKey('ticker', symbol));
      return cached ? JSON.parse(cached) : null;
    } catch (error) {
      console.error(`[Cache] Error getting ticker for ${symbol}:`, error);
      return null;
    }
  }

  async setTicker(symbol: string, data: Omit<CachedTickerData, 'lastUpdate'>): Promise<void> {
    await this.ensureConnection();
    if (!this.client) return;

    try {
      const dataWithTimestamp = {
        ...data,
        lastUpdate: new Date().toISOString(),
      };
      await this.client.setEx(
        this.getKey('ticker', symbol),
        JSON.stringify(dataWithTimestamp),
        this.SHORT_TTL
      );
    } catch (error) {
      console.error(`[Cache] Error setting ticker for ${symbol}:`, error);
    }
  }

  // Trending coins caching
  async getTrendingCoins(): Promise<any[] | null> {
    await this.ensureConnection();
    if (!this.client) return null;

    try {
      const cached = await this.client.get(this.getKey('trending', 'coins'));
      return cached ? JSON.parse(cached) : null;
    } catch (error) {
      console.error('[Cache] Error getting trending coins:', error);
      return null;
    }
  }

  async setTrendingCoins(coins: any[]): Promise<void> {
    await this.ensureConnection();
    if (!this.client) return;

    try {
      const dataWithTimestamp = {
        coins,
        lastUpdate: new Date().toISOString(),
      };
      await this.client.setEx(
        this.getKey('trending', 'coins'),
        JSON.stringify(dataWithTimestamp),
        this.DEFAULT_TTL
      );
    } catch (error) {
      console.error('[Cache] Error setting trending coins:', error);
    }
  }

  // Gainers and losers caching
  async getGainersLosers(): Promise<{ gainers: any[], losers: any[] } | null> {
    await this.ensureConnection();
    if (!this.client) return null;

    try {
      const cached = await this.client.get(this.getKey('market', 'movers'));
      return cached ? JSON.parse(cached) : null;
    } catch (error) {
      console.error('[Cache] Error getting gainers/losers:', error);
      return null;
    }
  }

  async setGainersLosers(data: { gainers: any[], losers: any[] }): Promise<void> {
    await this.ensureConnection();
    if (!this.client) return;

    try {
      const dataWithTimestamp = {
        ...data,
        lastUpdate: new Date().toISOString(),
      };
      await this.client.setEx(
        this.getKey('market', 'movers'),
        JSON.stringify(dataWithTimestamp),
        this.SHORT_TTL
      );
    } catch (error) {
      console.error('[Cache] Error setting gainers/losers:', error);
    }
  }

  // Cache invalidation
  async invalidateSymbol(symbol: string): Promise<void> {
    await this.ensureConnection();
    if (!this.client) return;

    try {
      const pattern = this.getKey('*', symbol);
      const keys = await this.client.keys(pattern);
      if (keys.length > 0) {
        await this.client.del(keys);
        console.log(`[Cache] Invalidated ${keys.length} cache entries for ${symbol}`);
      }
    } catch (error) {
      console.error(`[Cache] Error invalidating cache for ${symbol}:`, error);
    }
  }

  async invalidatePattern(pattern: string): Promise<void> {
    await this.ensureConnection();
    if (!this.client) return;

    try {
      const keys = await this.client.keys(pattern);
      if (keys.length > 0) {
        await this.client.del(keys);
        console.log(`[Cache] Invalidated ${keys.length} cache entries for pattern ${pattern}`);
      }
    } catch (error) {
      console.error(`[Cache] Error invalidating cache for pattern ${pattern}:`, error);
    }
  }

  // Health check
  async healthCheck(): Promise<{ connected: boolean; error?: string }> {
    try {
      if (!this.client) {
        return { connected: false, error: 'Redis client not initialized' };
      }

      await this.client.ping();
      return { connected: true };
    } catch (error) {
      return { connected: false, error: error instanceof Error ? error.message : 'Unknown error' };
    }
  }

  // Disconnect
  async disconnect(): Promise<void> {
    if (this.client && this.isConnected) {
      try {
        await this.client.quit();
        this.isConnected = false;
        console.log('[Cache] Disconnected from Redis');
      } catch (error) {
        console.error('[Cache] Error disconnecting from Redis:', error);
      }
    }
  }
}

// Export singleton instance
export const cacheService = new CacheService();

// Graceful shutdown
process.on('SIGINT', async () => {
  await cacheService.disconnect();
});

process.on('SIGTERM', async () => {
  await cacheService.disconnect();
});