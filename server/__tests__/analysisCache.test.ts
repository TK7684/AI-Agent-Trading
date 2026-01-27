/**
 * Unit Tests for Analysis Cache Service
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  getCachedGitHubAnalysis,
  setCachedGitHubAnalysis,
  getCachedContractAnalysis,
  setCachedContractAnalysis,
  invalidateAnalysisCache,
  getAnalysisCacheStats,
  clearAnalysisCache,
} from '../../server/services/analysisCache';

// Mock the cacheService - must be declared before imports that use it
vi.mock('../../server/services/cacheService', () => ({
  cacheService: {
    getPrice: vi.fn(),
    setPrice: vi.fn(),
    invalidatePattern: vi.fn(),
  },
}));

describe('Analysis Cache Service', () => {
  let cacheService: any;

  beforeEach(async () => {
    vi.clearAllMocks();
    clearAnalysisCache();
    // Get fresh cacheService mock reference
    const module = await import('../../server/services/cacheService');
    cacheService = module.cacheService;
  });

  describe('GitHub Analysis Cache', () => {
    const githubUrl = 'https://github.com/test/repo';
    const mockResult = {
      score: 85,
      data: { stars: 100 },
      analysis: 'Good repo',
      issues: [],
      strengths: ['Active'],
    };

    it('should set and get GitHub analysis cache', async () => {
      cacheService.getPrice.mockResolvedValueOnce(null);
      cacheService.setPrice.mockResolvedValueOnce(undefined);

      await setCachedGitHubAnalysis(githubUrl, mockResult);

      expect(cacheService.setPrice).toHaveBeenCalledWith(
        expect.stringContaining('github'),
        mockResult
      );
    });

    it('should return null on cache miss', async () => {
      const { cacheService } = await import('../../server/services/cacheService');
      cacheService.getPrice.mockResolvedValueOnce(null);

      const result = await getCachedGitHubAnalysis(githubUrl);

      expect(result).toBeNull();
    });

    it('should return cached data on cache hit', async () => {
      // Use a unique URL to avoid conflicts
      const uniqueUrl = 'https://github.com/cache-hit-test-' + Date.now() + '/repo';
      // Clear cache first to ensure clean state
      clearAnalysisCache();
      // Reset all mocks to ensure clean state
      cacheService.getPrice.mockReset();
      cacheService.setPrice.mockReset();
      // Mock Redis to return data (simulating a cache hit from Redis)
      cacheService.getPrice.mockResolvedValueOnce(mockResult);

      const result = await getCachedGitHubAnalysis(uniqueUrl);

      expect(result).toEqual(mockResult);
    });
  });

  describe('Contract Analysis Cache', () => {
    const address = '0x1234567890abcdef1234567890abcdef12345678';
    const chain = 'ethereum';
    const mockResult = {
      score: 90,
      data: { verified: true },
      analysis: 'Safe contract',
      risks: [],
      safetyFeatures: ['Verified'],
    };

    it('should set and get tokenomics cache', async () => {
      const { cacheService } = await import('../../server/services/cacheService');

      cacheService.getPrice.mockResolvedValueOnce(null);
      cacheService.setPrice.mockResolvedValueOnce(undefined);

      await setCachedContractAnalysis(address, chain, 'tokenomics', mockResult);

      expect(cacheService.setPrice).toHaveBeenCalledWith(
        expect.stringContaining('tokenomics'),
        mockResult
      );
    });

    it('should set and get contract risk cache', async () => {
      const { cacheService } = await import('../../server/services/cacheService');

      cacheService.getPrice.mockResolvedValueOnce(null);
      cacheService.setPrice.mockResolvedValueOnce(undefined);

      await setCachedContractAnalysis(address, chain, 'risk', mockResult);

      expect(cacheService.setPrice).toHaveBeenCalledWith(
        expect.stringContaining('risk'),
        mockResult
      );
    });

    it('should return null on cache miss', async () => {
      // Use a unique address that hasn't been used before
      const uniqueAddress = '0x' + Date.now().toString(16).padStart(40, '0');
      // Clear cache first to ensure clean state
      clearAnalysisCache();
      // Reset all mocks to ensure clean state
      cacheService.getPrice.mockReset();
      cacheService.setPrice.mockReset();
      // Mock Redis to return null (simulating a cache miss)
      cacheService.getPrice.mockResolvedValueOnce(null);

      const result = await getCachedContractAnalysis(uniqueAddress, chain, 'tokenomics');

      expect(result).toBeNull();
    });
  });

  describe('Cache Invalidation', () => {
    it('should invalidate cache by type', async () => {
      const { cacheService } = await import('../../server/services/cacheService');
      cacheService.invalidatePattern.mockResolvedValueOnce(undefined);

      await invalidateAnalysisCache('github', 'test');

      expect(cacheService.invalidatePattern).toHaveBeenCalledWith(
        expect.stringContaining('github')
      );
    });

    it('should clear in-memory cache', () => {
      // Set some in-memory cache first
      setCachedGitHubAnalysis('test', { score: 50 });
      expect(getAnalysisCacheStats().memoryCacheSize).toBeGreaterThan(0);

      clearAnalysisCache();
      expect(getAnalysisCacheStats().memoryCacheSize).toBe(0);
    });
  });

  describe('Cache Stats', () => {
    it('should return cache statistics', () => {
      const stats = getAnalysisCacheStats();

      expect(stats).toHaveProperty('memoryCacheSize');
      expect(stats).toHaveProperty('keys');
      expect(Array.isArray(stats.keys)).toBe(true);
      expect(typeof stats.memoryCacheSize).toBe('number');
    });
  });

  describe('Key Generation', () => {
    it('should generate different keys for different analysis types', async () => {
      const { cacheService } = await import('../../server/services/cacheService');

      const calls: string[] = [];
      cacheService.setPrice.mockImplementation((key: string) => {
        calls.push(key);
        return Promise.resolve();
      });

      await setCachedGitHubAnalysis('https://github.com/test/repo', { score: 50 });
      await setCachedContractAnalysis('0xtest', 'ethereum', 'tokenomics', { score: 50 });

      expect(calls[0]).toContain('github');
      expect(calls[1]).toContain('tokenomics');
      expect(calls[0]).not.toBe(calls[1]);
    });

    it('should generate same key for same input', async () => {
      const { cacheService } = await import('../../server/services/cacheService');

      const calls: string[] = [];
      cacheService.setPrice.mockImplementation((key: string) => {
        calls.push(key);
        return Promise.resolve();
      });

      await setCachedGitHubAnalysis('https://github.com/test/repo', { score: 50 });
      await setCachedGitHubAnalysis('https://github.com/test/repo', { score: 60 });

      expect(calls[0]).toBe(calls[1]);
    });
  });

  describe('Error Handling', () => {
    it('should handle Redis errors gracefully', async () => {
      const { cacheService } = await import('../../server/services/cacheService');

      cacheService.getPrice.mockRejectedValueOnce(new Error('Redis connection failed'));

      const result = await getCachedGitHubAnalysis('https://github.com/test/repo');

      // Should not throw, should return null
      expect(result).toBeNull();
    });

    it('should continue with in-memory cache on Redis error', async () => {
      const { cacheService } = await import('../../server/services/cacheService');

      cacheService.getPrice.mockRejectedValueOnce(new Error('Redis error'));
      cacheService.setPrice.mockRejectedValueOnce(new Error('Redis error'));

      // These should not throw
      await setCachedGitHubAnalysis('https://github.com/test/repo', { score: 50 });
      const stats = getAnalysisCacheStats();

      expect(stats.memoryCacheSize).toBe(1);
    });
  });
});
