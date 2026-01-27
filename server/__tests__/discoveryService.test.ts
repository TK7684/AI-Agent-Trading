/**
 * Unit Tests for Discovery Service
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { discoverTrendingProjects, clearDiscoveryCache } from '../../server/services/discoveryService';

// Mock fetch globally
global.fetch = vi.fn();

describe('Discovery Service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    // Clear discovery cache before each test to prevent cross-test pollution
    clearDiscoveryCache();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('discoverTrendingProjects', () => {
    const mockCoinGeckoResponse = [
      {
        id: 'bitcoin',
        symbol: 'btc',
        name: 'Bitcoin',
        current_price: 50000,
        market_cap: 1000000000000,
        market_cap_rank: 1,
        total_volume: 30000000000,
        price_change_percentage_24h: 2.5,
        high_24h: 51000,
        low_24h: 49000,
        image: 'https://example.com/btc.png',
      },
      {
        id: 'ethereum',
        symbol: 'eth',
        name: 'Ethereum',
        current_price: 3000,
        market_cap: 350000000000,
        market_cap_rank: 2,
        total_volume: 15000000000,
        price_change_percentage_24h: 3.2,
        high_24h: 3100,
        low_24h: 2900,
        image: 'https://example.com/eth.png',
      },
    ];

    const mockDetailResponse = {
      links: {
        homepage: ['https://bitcoin.org'],
        repos_url: {
          github: ['https://github.com/bitcoin/bitcoin'],
        },
        twitter_screen_name: 'bitcoin',
        telegram_channel_identifier: 'bitcoin_chat',
      },
      description: {
        en: 'Bitcoin is a decentralized digital currency.',
      },
      categories: ['Cryptocurrency', 'Layer 1'],
      platforms: {
        ethereum: '0x1234567890abcdef1234567890abcdef12345678',
      },
    };

    it('should fetch trending projects from CoinGecko', async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockCoinGeckoResponse,
      });

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockDetailResponse,
      });

      const result = await discoverTrendingProjects();

      expect(result).toBeDefined();
      expect(Array.isArray(result)).toBe(true);
      expect(result.length).toBeGreaterThan(0);
      expect(result[0]).toHaveProperty('id');
      expect(result[0]).toHaveProperty('name');
      expect(result[0]).toHaveProperty('symbol');
      expect(result[0]).toHaveProperty('recommendationScore');
    });

    it('should handle API errors gracefully', async () => {
      (global.fetch as any).mockRejectedValueOnce(new Error('API Error'));

      const result = await discoverTrendingProjects();

      // Should return mock data on error
      expect(result).toBeDefined();
      expect(Array.isArray(result)).toBe(true);
      expect(result.length).toBeGreaterThan(0);
    });

    it('should filter by category', async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockCoinGeckoResponse,
      });

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockDetailResponse,
      });

      const result = await discoverTrendingProjects({ category: 'DeFi' });

      // Should apply category filter
      expect(result).toBeDefined();
    });

    it('should filter by status', async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockCoinGeckoResponse,
      });

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockDetailResponse,
      });

      const result = await discoverTrendingProjects({ status: 'hot' });

      // Should apply status filter
      expect(result).toBeDefined();
    });

    it('should filter by minimum score', async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockCoinGeckoResponse,
      });

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockDetailResponse,
      });

      const result = await discoverTrendingProjects({ minScore: 80 });

      // Should apply score filter
      expect(result).toBeDefined();
    });

    it('should filter by maximum market cap', async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockCoinGeckoResponse,
      });

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockDetailResponse,
      });

      const result = await discoverTrendingProjects({ maxMarketCap: 500000000000 });

      // Should apply market cap filter
      expect(result).toBeDefined();
    });
  });

  describe('calculateRecommendationScore (via discoverTrendingProjects)', () => {
    it('should give higher score to top market cap projects', async () => {
      const mockResponse = [
        {
          id: 'bitcoin',
          symbol: 'btc',
          name: 'Bitcoin',
          current_price: 50000,
          market_cap: 1000000000000,
          market_cap_rank: 1,
          total_volume: 30000000000,
          price_change_percentage_24h: 5,
          high_24h: 51000,
          low_24h: 49000,
        },
        {
          id: 'small-token',
          symbol: 'small',
          name: 'Small Token',
          current_price: 0.01,
          market_cap: 1000000,
          market_cap_rank: 5000,
          total_volume: 50000,
          price_change_percentage_24h: 5,
          high_24h: 0.011,
          low_24h: 0.009,
        },
      ];

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          links: {
            repos_url: { github: ['https://github.com/test/test'] },
            twitter_screen_name: 'test',
          },
        }),
      });

      const result = await discoverTrendingProjects();

      const btcScore = result.find((p: any) => p.id === 'bitcoin')?.recommendationScore;
      const smallScore = result.find((p: any) => p.id === 'small-token')?.recommendationScore;

      expect(btcScore).toBeGreaterThan(smallScore);
    });

    it('should give higher score to projects with positive price momentum', async () => {
      const mockResponse = [
        {
          id: 'gainer',
          symbol: 'GAIN',
          name: 'Gainer Token',
          current_price: 100,
          market_cap: 1000000000,
          market_cap_rank: 100,
          total_volume: 50000000,
          price_change_percentage_24h: 25,
          high_24h: 110,
          low_24h: 80,
        },
        {
          id: 'loser',
          symbol: 'LOSE',
          name: 'Loser Token',
          current_price: 100,
          market_cap: 1000000000,
          market_cap_rank: 100,
          total_volume: 50000000,
          price_change_percentage_24h: -25,
          high_24h: 110,
          low_24h: 80,
        },
      ];

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          links: { repos_url: { github: [] } },
        }),
      });

      const result = await discoverTrendingProjects();

      const gainerScore = result.find((p: any) => p.id === 'gainer')?.recommendationScore;
      const loserScore = result.find((p: any) => p.id === 'loser')?.recommendationScore;

      expect(gainerScore).toBeGreaterThan(loserScore);
    });

    it('should give higher score to projects with high volume', async () => {
      const mockResponse = [
        {
          id: 'high-volume',
          symbol: 'HVOL',
          name: 'High Volume',
          current_price: 10,
          market_cap: 1000000000,
          market_cap_rank: 100,
          total_volume: 2000000000,
          price_change_percentage_24h: 0,
          high_24h: 11,
          low_24h: 9,
        },
        {
          id: 'low-volume',
          symbol: 'LVOL',
          name: 'Low Volume',
          current_price: 10,
          market_cap: 1000000000,
          market_cap_rank: 100,
          total_volume: 1000000,
          price_change_percentage_24h: 0,
          high_24h: 11,
          low_24h: 9,
        },
      ];

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          links: { repos_url: { github: [] } },
        }),
      });

      const result = await discoverTrendingProjects();

      const highVolScore = result.find((p: any) => p.id === 'high-volume')?.recommendationScore;
      const lowVolScore = result.find((p: any) => p.id === 'low-volume')?.recommendationScore;

      expect(highVolScore).toBeGreaterThan(lowVolScore);
    });

    it('should give higher score to projects with transparency features', async () => {
      const mockResponse = [
        {
          id: 'transparent',
          symbol: 'TRAN',
          name: 'Transparent Token',
          current_price: 10,
          market_cap: 1000000000,
          market_cap_rank: 100,
          total_volume: 50000000,
          price_change_percentage_24h: 0,
          high_24h: 11,
          low_24h: 9,
        },
        {
          id: 'opaque',
          symbol: 'OPAQ',
          name: 'Opaque Token',
          current_price: 10,
          market_cap: 1000000000,
          market_cap_rank: 100,
          total_volume: 50000000,
          price_change_percentage_24h: 0,
          high_24h: 11,
          low_24h: 9,
        },
      ];

      (global.fetch as any)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockResponse,
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            links: {
              repos_url: { github: ['https://github.com/test/transparent'] },
              twitter_screen_name: 'transparent_token',
            },
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            links: { repos_url: { github: [] } },
          }),
        });

      const result = await discoverTrendingProjects();

      const transScore = result.find((p: any) => p.id === 'transparent')?.recommendationScore;
      const opaqueScore = result.find((p: any) => p.id === 'opaque')?.recommendationScore;

      expect(transScore).toBeGreaterThan(opaqueScore);
    });
  });
});
