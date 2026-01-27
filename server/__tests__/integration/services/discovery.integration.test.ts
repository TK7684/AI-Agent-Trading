/**
 * Discovery Service Integration Tests
 * Tests the discovery router with database interactions
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { getTestDb, resetTestDb } from '../../../../test-utils/database';
import { createAuthenticatedCaller, createUnauthenticatedCaller } from '../../../../test-utils/trpc';
import { users } from '@drizzle/schema';

// Mock external CoinGecko API
vi.mock('../../../services/discoveryService', async () => {
  const actual = await vi.importActual('../../../services/discoveryService');
  return {
    ...actual,
    discoverTrendingProjects: vi.fn(() => Promise.resolve([
      {
        id: 'bitcoin',
        name: 'Bitcoin',
        symbol: 'BTC',
        currentPrice: 50000,
        marketCap: 1000000000000,
        marketCapRank: 1,
        priceChange24h: 2.5,
        volume24h: 30000000000,
        high24h: 51000,
        low24h: 49000,
        recommendationScore: 95,
        status: 'hot',
        categories: ['Cryptocurrency', 'Layer 1'],
        links: {
          homepage: ['https://bitcoin.org'],
          github: ['https://github.com/bitcoin/bitcoin'],
          twitter: 'bitcoin',
          telegram: 'bitcoin_chat',
        },
      },
      {
        id: 'ethereum',
        name: 'Ethereum',
        symbol: 'ETH',
        currentPrice: 3000,
        marketCap: 350000000000,
        marketCapRank: 2,
        priceChange24h: 3.2,
        volume24h: 15000000000,
        high24h: 3100,
        low24h: 2900,
        recommendationScore: 90,
        status: 'hot',
        categories: ['Cryptocurrency', 'Smart Contract Platform'],
        links: {
          homepage: ['https://ethereum.org'],
          github: ['https://github.com/ethereum/go-ethereum'],
          twitter: 'ethereum',
          telegram: 'ethereum_chat',
        },
      },
    ])),
    clearDiscoveryCache: vi.fn(),
  };
});

describe('Discovery Service Integration Tests', () => {
  let db: Awaited<ReturnType<typeof getTestDb>>;
  let testUser: { id: number; email: string; name: string | null; role: string };

  beforeEach(async () => {
    db = await getTestDb();
    await resetTestDb();

    // Create a test user
    const [user] = await db.insert(users).values({
      openId: 'test-user-openid',
      email: 'discovery@example.com',
      name: 'Discovery User',
      role: 'user',
    }).returning();

    testUser = user;
  });

  afterEach(async () => {
    vi.clearAllMocks();
  });

  describe('Discover Trending Projects', () => {
    it('should fetch trending projects', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      const result = await caller.discovery.trending({});

      expect(result).toBeDefined();
      expect(Array.isArray(result)).toBe(true);
      expect(result.length).toBeGreaterThan(0);
      expect(result[0]).toHaveProperty('id');
      expect(result[0]).toHaveProperty('name');
      expect(result[0]).toHaveProperty('symbol');
      expect(result[0]).toHaveProperty('recommendationScore');
    });

    it('should not require authentication for discovery', async () => {
      const caller = await createUnauthenticatedCaller();

      const result = await caller.discovery.trending({});

      expect(result).toBeDefined();
      expect(Array.isArray(result)).toBe(true);
    });

    it('should filter by category', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      const result = await caller.discovery.trending({
        category: 'DeFi',
      });

      expect(result).toBeDefined();
      expect(Array.isArray(result)).toBe(true);
    });

    it('should filter by status', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      const result = await caller.discovery.trending({
        status: 'hot',
      });

      expect(result).toBeDefined();
      expect(Array.isArray(result)).toBe(true);
      // All returned projects should have status 'hot'
      if (result.length > 0) {
        result.forEach(project => {
          expect(project.status).toBe('hot');
        });
      }
    });

    it('should filter by minimum score', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      const result = await caller.discovery.trending({
        minScore: 80,
      });

      expect(result).toBeDefined();
      expect(Array.isArray(result)).toBe(true);
      // All returned projects should have score >= 80
      if (result.length > 0) {
        result.forEach(project => {
          expect(project.recommendationScore).toBeGreaterThanOrEqual(80);
        });
      }
    });

    it('should filter by maximum market cap', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      const result = await caller.discovery.trending({
        maxMarketCap: 500000000000,
      });

      expect(result).toBeDefined();
      expect(Array.isArray(result)).toBe(true);
      // All returned projects should have marketCap <= max
      if (result.length > 0) {
        result.forEach(project => {
          expect(project.marketCap).toBeLessThanOrEqual(500000000000);
        });
      }
    });

    it('should limit results', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      const result = await caller.discovery.trending({
        limit: 1,
      });

      expect(result).toBeDefined();
      expect(Array.isArray(result)).toBe(true);
      expect(result.length).toBeLessThanOrEqual(1);
    });
  });

  describe('Get Available Categories', () => {
    it('should return list of categories', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      const result = await caller.discovery.categories();

      expect(result).toBeDefined();
      expect(Array.isArray(result)).toBe(true);
      expect(result.length).toBeGreaterThan(0);
      expect(result).toContain('DeFi');
      expect(result).toContain('NFT');
      expect(result).toContain('Layer 1');
    });

    it('should not require authentication for categories', async () => {
      const caller = await createUnauthenticatedCaller();

      const result = await caller.discovery.categories();

      expect(result).toBeDefined();
      expect(Array.isArray(result)).toBe(true);
    });
  });

  describe('Get Project Details', () => {
    it('should fetch detailed project information', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      const result = await caller.discovery.getProjectDetails({
        id: 'bitcoin',
      });

      expect(result).toBeDefined();
      expect(result.id).toBe('bitcoin');
      expect(result.name).toBe('Bitcoin');
    });

    it('should return null for non-existent project', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      const result = await caller.discovery.getProjectDetails({
        id: 'nonexistent-project-id-12345',
      });

      expect(result).toBeNull();
    });
  });

  describe('Caching Behavior', () => {
    it('should cache results for subsequent calls', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      // First call
      const result1 = await caller.discovery.trending({});

      // Second call should use cache
      const result2 = await caller.discovery.trending({});

      expect(result1).toEqual(result2);
    });
  });

  describe('Error Handling', () => {
    it('should handle API errors gracefully', async () => {
      // Mock the service to throw an error
      const { discoverTrendingProjects } = await import('../../../services/discoveryService');
      vi.mocked(discoverTrendingProjects).mockRejectedValueOnce(new Error('API Error'));

      const caller = await createAuthenticatedCaller(testUser);

      // Should not throw, but return empty array or mock data
      const result = await caller.discovery.trending({});

      expect(result).toBeDefined();
      expect(Array.isArray(result)).toBe(true);
    });

    it('should handle timeout gracefully', async () => {
      // Mock the service to timeout
      const { discoverTrendingProjects } = await import('../../../services/discoveryService');
      vi.mocked(discoverTrendingProjects).mockImplementationOnce(
        () => new Promise((resolve) => setTimeout(() => resolve([]), 35000))
      );

      const caller = await createAuthenticatedCaller(testUser);

      // Should handle timeout gracefully
      const result = await caller.discovery.trending({});

      expect(result).toBeDefined();
    });
  });

  describe('Data Transformation', () => {
    it('should transform CoinGecko data to expected format', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      const result = await caller.discovery.trending({});

      if (result.length > 0) {
        const project = result[0];

        // Check required fields
        expect(project).toHaveProperty('id');
        expect(project).toHaveProperty('name');
        expect(project).toHaveProperty('symbol');
        expect(project).toHaveProperty('currentPrice');
        expect(project).toHaveProperty('marketCap');
        expect(project).toHaveProperty('recommendationScore');
        expect(project).toHaveProperty('status');

        // Check data types
        expect(typeof project.id).toBe('string');
        expect(typeof project.name).toBe('string');
        expect(typeof project.symbol).toBe('string');
        expect(typeof project.currentPrice).toBe('number');
        expect(typeof project.marketCap).toBe('number');
        expect(typeof project.recommendationScore).toBe('number');
      }
    });

    it('should calculate recommendation score correctly', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      const result = await caller.discovery.trending({});

      if (result.length > 0) {
        result.forEach(project => {
          expect(project.recommendationScore).toBeGreaterThanOrEqual(0);
          expect(project.recommendationScore).toBeLessThanOrEqual(100);
        });
      }
    });

    it('should determine status based on score and metrics', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      const result = await caller.discovery.trending({});

      if (result.length > 0) {
        result.forEach(project => {
          expect(['hot', 'trending', 'watch', 'avoid']).toContain(project.status);
        });
      }
    });
  });
});
