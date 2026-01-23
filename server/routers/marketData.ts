/**
 * Market Data Router - FREE APIs
 * Exposes CoinGecko, Binance, and other free market data
 */

import { z } from "zod";
import { publicProcedure, router } from "../_core/trpc";
import {
  marketDataService,
  getCachedMarketData,
  updateMarketDataCache,
} from "../services/marketData";

export const marketDataRouter = router({
  // Get current price data for a symbol
  getPrice: publicProcedure
    .input(z.object({
      symbol: z.string(),
      useCache: z.boolean().optional().default(true),
    }))
    .query(async ({ input }) => {
      const { symbol, useCache } = input;

      if (useCache) {
        return getCachedMarketData(symbol);
      }

      return marketDataService.getDetailedMarketData(symbol);
    }),

  // Get OHLCV (candlestick) data
  getOHLCV: publicProcedure
    .input(z.object({
      symbol: z.string(),
      interval: z.enum(['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1M']).optional().default('15m'),
      limit: z.number().min(1).max(1000).optional().default(100),
    }))
    .query(async ({ input }) => {
      return marketDataService.getOHLCV(input.symbol, input.interval, input.limit);
    }),

  // Get 24h ticker data
  getTicker24h: publicProcedure
    .input(z.object({
      symbol: z.string(),
    }))
    .query(async ({ input }) => {
      return marketDataService.getTicker24h(input.symbol);
    }),

  // Get top coins by market cap
  getTopCoins: publicProcedure
    .input(z.object({
      limit: z.number().min(1).max(250).optional().default(50),
      currency: z.enum(['usd', 'eur', 'gbp', 'jpy', 'btc', 'eth']).optional().default('usd'),
    }))
    .query(async ({ input }) => {
      return marketDataService.getTopCoins(input.limit, input.currency);
    }),

  // Search for coins
  searchCoins: publicProcedure
    .input(z.object({
      query: z.string().min(1),
    }))
    .query(async ({ input }) => {
      return marketDataService.searchCoins(input.query);
    }),

  // Get market categories
  getCategories: publicProcedure
    .query(async () => {
      return marketDataService.getCategories();
    }),

  // Get trending coins
  getTrending: publicProcedure
    .query(async () => {
      return marketDataService.getTrending();
    }),

  // Get multiple prices at once (batch request)
  getBatchPrices: publicProcedure
    .input(z.object({
      symbols: z.array(z.string()).min(1).max(100),
    }))
    .query(async ({ input }) => {
      const results = await Promise.allSettled(
        input.symbols.map(symbol => marketDataService.getDetailedMarketData(symbol))
      );

      return input.symbols.map((symbol, index) => ({
        symbol,
        data: results[index].status === 'fulfilled' ? results[index].value : null,
        error: results[index].status === 'rejected' ? results[index].reason : null,
      }));
    }),

  // Get supported IDs
  getSupportedIds: publicProcedure
    .query(async () => {
      return marketDataService.getSupportedIds();
    }),

  // Admin: Trigger cache update
  updateCache: publicProcedure
    .input(z.object({
      symbols: z.array(z.string()).optional(),
    }))
    .mutation(async ({ input }) => {
      const symbols = input.symbols || Object.keys(marketDataService.getSupportedIds());
      await updateMarketDataCache(symbols);
      return { success: true, count: symbols.length };
    }),
});
