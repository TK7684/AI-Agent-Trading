/**
 * FREE Market Data Service with Caching
 * Uses CoinGecko, Binance, and other free APIs with Redis caching
 * No paid services required!
 */

import axios from "axios";
import { cacheService } from "./cacheService";

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
  private readonly REQUEST_TIMEOUT = 10000; // 10 seconds

  /**
   * Get price data from cache or CoinGecko API
   */
  async getPrice(symbol: string): Promise<PriceData | null> {
    try {
      // Check cache first
      const cached = await cacheService.getPrice(symbol);
      if (cached) {
        console.log(`[MarketData] Cache hit for price: ${symbol}`);
        return cached;
      }

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
          timeout: this.REQUEST_TIMEOUT,
        }
      );

      const data = response.data[coinGeckoId];
      if (!data) {
        console.warn(`[MarketData] No data found for ${symbol}`);
        return null;
      }

      const priceData: PriceData = {
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

      // Cache the result
      await cacheService.setPrice(symbol, priceData);
      
      return priceData;
    } catch (error) {
      console.error(`[MarketData] CoinGecko error for ${symbol}:`, error);
      return null;
    }
  }

  /**
   * Get detailed market data from cache or CoinGecko API
   */
  async getDetailedMarketData(symbol: string): Promise<PriceData | null> {
    try {
      // Check cache first
      const cached = await cacheService.getPrice(symbol);
      if (cached) {
        console.log(`[MarketData] Cache hit for detailed market data: ${symbol}`);
        return cached;
      }

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
          timeout: this.REQUEST_TIMEOUT,
        }
      );

      const data = response.data;
      const marketData = data.market_data || {};

      const priceData: PriceData = {
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

      // Cache the result
      await cacheService.setPrice(symbol, priceData);
      
      return priceData;
    } catch (error) {
      console.error(`[MarketData] Detailed data error for ${symbol}:`, error);
      // Fallback to simple price
      return this.getPrice(symbol);
    }
  }

  /**
   * Get OHLCV data from cache or Binance API
   */
  async getOHLCV(symbol: string, interval: string = '15m', limit: number = 100): Promise<OHLCVData[]> {
    try {
      // Check cache first
      const cached = await cacheService.getOHLCV(symbol, interval);
      if (cached) {
        console.log(`[MarketData] Cache hit for OHLCV: ${symbol} ${interval}`);
        return cached.data;
      }

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
          timeout: this.REQUEST_TIMEOUT,
        }
      );

      const data = response.data.map((k: any[]) => ({
        timestamp: k[0],
        open: parseFloat(k[1]),
        high: parseFloat(k[2]),
        low: parseFloat(k[3]),
        close: parseFloat(k[4]),
        volume: parseFloat(k[5]),
      }));

      // Cache the result
      await cacheService.setOHLCV(symbol, interval, data);
      
      return data;
    } catch (error) {
      console.error(`[MarketData] Binance OHLCV error for ${symbol}:`, error);
      return [];
    }
  }

  /**
   * Get 24h ticker data from cache or Binance API
   */
  async getTicker24h(symbol: string): Promise<TickerData | null> {
    try {
      // Check cache first
      const cached = await cacheService.getTicker(symbol);
      if (cached) {
        console.log(`[MarketData] Cache hit for ticker: ${symbol}`);
        return cached;
      }

      const binanceSymbol = this.toBinanceSymbol(symbol);

      const response = await axios.get(
        `${this.binanceBaseUrl}/ticker/24hr`,
        {
          params: { symbol: binanceSymbol },
          timeout: this.REQUEST_TIMEOUT,
        }
      );

      const data = response.data;
      const tickerData: TickerData = {
        priceChange: parseFloat(data.priceChange),
        priceChangePercent: parseFloat(data.priceChangePercent),
        highPrice: parseFloat(data.highPrice),
        lowPrice: parseFloat(data.lowPrice),
        volume: parseFloat(data.volume),
        quoteVolume: parseFloat(data.quoteVolume),
      };

      // Cache the result
      await cacheService.setTicker(symbol, tickerData);
      
      return tickerData;
    } catch (error) {
      console.error(`[MarketData] Binance ticker error for ${symbol}:`, error);
      return null;
    }
  }

  /**
   * Get top cryptocurrencies by market cap from cache or CoinGecko API
   */
  async getTopCoins(limit: number = 50, currency: string = 'usd'): Promise<any[]> {
    try {
      // Check cache first
      const cached = await cacheService.getTrendingCoins();
      if (cached && cached.length >= limit) {
        console.log('[MarketData] Cache hit for top coins');
        return cached.slice(0, limit);
      }

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
          timeout: this.REQUEST_TIMEOUT,
        }
      );

      const coins = response.data.map((coin: any) => ({
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

      // Cache the result
      await cacheService.setTrendingCoins(coins);
      
      return coins;
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
          timeout: this.REQUEST_TIMEOUT,
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
        { timeout: this.REQUEST_TIMEOUT }
      );

      return response.data.map((cat: any) => cat.name);
    } catch (error) {
      console.error('[MarketData] Categories error:', error);
      return [];
    }
  }

  /**
   * Get trending coins (searched most by users) from cache or CoinGecko API
   */
  async getTrending(): Promise<any[]> {
    try {
      // Check cache first
      const cached = await cacheService.getTrendingCoins();
      if (cached && cached.length > 0) {
        console.log('[MarketData] Cache hit for trending coins');
        return cached;
      }

      const response = await axios.get(
        `${this.coinGeckoBaseUrl}/search/trending`,
        { timeout: this.REQUEST_TIMEOUT }
      );

      const coins = (response.data.coins || []).map((item: any) => ({
        symbol: item.item.symbol,
        name: item.item.name,
        marketCapRank: item.item.market_cap_rank,
        thumb: item.item.thumb,
        score: item.item.score,
      }));

      // Cache the result
      await cacheService.setTrendingCoins(coins);
      
      return coins;
    } catch (error) {
      console.error('[MarketData] Trending error:', error);
      return [];
    }
  }

  /**
   * Get gainers and losers from cache or CoinGecko API
   */
  async getGainersLosers(top: number = 50): Promise<{ gainers: any[], losers: any[] }> {
    try {
      // Check cache first
      const cached = await cacheService.getGainersLosers();
      if (cached) {
        console.log('[MarketData] Cache hit for gainers/losers');
        return cached;
      }

      const response = await axios.get(
        `${this.coinGeckoBaseUrl}/coins/markets`,
        {
          params: {
            vs_currency: 'usd',
            order: 'price_change_percentage_24h_desc',
            per_page: top * 2, // Get more to find both gainers and losers
            page: 1,
            sparkline: false,
          },
          timeout: this.REQUEST_TIMEOUT,
        }
      );

      const data = response.data;
      const gainers = data.filter((coin: any) => coin.price_change_percentage_24h > 0).slice(0, top);
      const losers = data.filter((coin: any) => coin.price_change_percentage_24h < 0).slice(0, top);

      const result = { gainers, losers };

      // Cache the result
      await cacheService.setGainersLosers(result);
      
      return result;
    } catch (error) {
      console.error('[MarketData] Gainers/losers error:', error);
      return { gainers: [], losers: [] };
    }
  }

  /**
   * Get multiple prices at once (batch request) with caching
   */
  async getBatchPrices(symbols: string[]): Promise<Array<{ symbol: string; data: any; error: any }>> {
    const results = await Promise.allSettled(
      symbols.map(async (symbol) => {
        try {
          const data = await this.getDetailedMarketData(symbol);
          return { symbol, data };
        } catch (error) {
          return { symbol, error };
        }
      })
    );

    return symbols.map((symbol, index) => ({
      symbol,
      data: results[index].status === 'fulfilled' ? results[index].value.data : null,
      error: results[index].status === 'rejected' ? results[index].reason : null,
    }));
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

  /**
   * Invalidate cache for a symbol
   */
  async invalidateSymbolCache(symbol: string): Promise<void> {
    await cacheService.invalidateSymbol(symbol);
  }

  /**
   * Health check for the service
   */
  async healthCheck(): Promise<{ status: string; cache: any; apis: any }> {
    const cacheHealth = await cacheService.healthCheck();
    
    // Check API health
    const apiHealth = {
      coingecko: await this.checkCoinGeckoHealth(),
      binance: await this.checkBinanceHealth(),
    };

    return {
      status: 'ok',
      cache: cacheHealth,
      apis: apiHealth,
    };
  }

  private async checkCoinGeckoHealth(): Promise<{ status: string; latency?: number }> {
    try {
      const start = Date.now();
      await axios.get(`${this.coinGeckoBaseUrl}/ping`, { timeout: 5000 });
      const latency = Date.now() - start;
      return { status: 'ok', latency };
    } catch (error) {
      return { status: 'error', latency: undefined };
    }
  }

  private async checkBinanceHealth(): Promise<{ status: string; latency?: number }> {
    try {
      const start = Date.now();
      await axios.get(`${this.binanceBaseUrl}/ping`, { timeout: 5000 });
      const latency = Date.now() - start;
      return { status: 'ok', latency };
    } catch (error) {
      return { status: 'error', latency: undefined };
    }
  }
}

// Export singleton instance
export const marketDataService = new FreeMarketDataService();

/**
 * Cached wrapper functions for backward compatibility
 */
export async function getCachedMarketData(symbol: string): Promise<PriceData | null> {
  return marketDataService.getDetailedMarketData(symbol);
}

/**
 * Background job to update market data cache
 */
export async function updateMarketDataCache(symbols: string[]): Promise<void> {
  console.log(`[MarketData] Updating cache for ${symbols.length} symbols...`);

  for (const symbol of symbols) {
    const data = await marketDataService.getDetailedMarketData(symbol);
    if (data) {
      console.log(`[MarketData] Updated cache for ${symbol}`);
    }
  }

  console.log('[MarketData] Cache update complete');
}