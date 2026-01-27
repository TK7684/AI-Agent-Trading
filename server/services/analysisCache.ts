/**
 * Analysis Cache Service
 * Caches expensive analysis results (GitHub, Contract, Social)
 * with configurable TTL and automatic invalidation
 */

import { cacheService } from './cacheService';

// Types for cached analysis
export interface CachedGitHubAnalysis {
  url: string;
  result: any;
  timestamp: number;
}

export interface CachedContractAnalysis {
  address: string;
  chain: string;
  result: any;
  timestamp: number;
}

export interface CachedSocialAnalysis {
  platform: string;
  url: string;
  result: any;
  timestamp: number;
}

// In-memory fallback cache
const analysisCache = new Map<string, { data: any; expiry: number }>();
const GITHUB_TTL = 3600000; // 1 hour - GitHub data doesn't change often
const CONTRACT_TTL = 1800000; // 30 minutes - contract data is stable
const SOCIAL_TTL = 900000; // 15 minutes - social data changes frequently

/**
 * Get from in-memory cache
 */
function getFromMemCache(key: string): any | null {
  const cached = analysisCache.get(key);
  if (cached && cached.expiry > Date.now()) {
    return cached.data;
  }
  if (cached) {
    analysisCache.delete(key);
  }
  return null;
}

/**
 * Set in-memory cache
 */
function setMemCache(key: string, data: any, ttl: number): void {
  analysisCache.set(key, {
    data,
    expiry: Date.now() + ttl,
  });
}

/**
 * Generate cache key for GitHub analysis
 */
function githubKey(url: string): string {
  return `analysis:github:${Buffer.from(url).toString('base64')}`;
}

/**
 * Generate cache key for contract analysis
 */
function contractKey(address: string, chain: string, type: string): string {
  return `analysis:contract:${chain}:${address}:${type}`;
}

/**
 * Generate cache key for social analysis
 */
function socialKey(platform: string, url: string): string {
  return `analysis:social:${platform}:${Buffer.from(url).toString('base64')}`;
}

/**
 * Get cached GitHub analysis
 */
export async function getCachedGitHubAnalysis(url: string): Promise<any | null> {
  const key = githubKey(url);

  // Try in-memory first (fastest)
  const memCached = getFromMemCache(key);
  if (memCached) {
    console.log(`[AnalysisCache] Memory hit for GitHub: ${url}`);
    return memCached;
  }

  // Try Redis
  try {
    const cached = await cacheService.getPrice(key); // Reuse price cache method
    if (cached) {
      console.log(`[AnalysisCache] Redis hit for GitHub: ${url}`);
      setMemCache(key, cached, GITHUB_TTL);
      return cached;
    }
  } catch (error) {
    console.warn('[AnalysisCache] Redis unavailable for GitHub');
  }

  return null;
}

/**
 * Set cached GitHub analysis
 */
export async function setCachedGitHubAnalysis(url: string, result: any): Promise<void> {
  const key = githubKey(url);

  // Set in-memory
  setMemCache(key, result, GITHUB_TTL);

  // Set in Redis
  try {
    await cacheService.setPrice(key, result);
  } catch (error) {
    console.warn('[AnalysisCache] Failed to cache GitHub in Redis');
  }
}

/**
 * Get cached contract analysis
 */
export async function getCachedContractAnalysis(
  address: string,
  chain: string,
  type: 'tokenomics' | 'risk'
): Promise<any | null> {
  const key = contractKey(address, chain, type);

  // Try in-memory first
  const memCached = getFromMemCache(key);
  if (memCached) {
    console.log(`[AnalysisCache] Memory hit for contract ${type}: ${address}`);
    return memCached;
  }

  // Try Redis
  try {
    const cached = await cacheService.getPrice(key);
    if (cached) {
      console.log(`[AnalysisCache] Redis hit for contract ${type}: ${address}`);
      setMemCache(key, cached, CONTRACT_TTL);
      return cached;
    }
  } catch (error) {
    console.warn('[AnalysisCache] Redis unavailable for contract');
  }

  return null;
}

/**
 * Set cached contract analysis
 */
export async function setCachedContractAnalysis(
  address: string,
  chain: string,
  type: 'tokenomics' | 'risk',
  result: any
): Promise<void> {
  const key = contractKey(address, chain, type);

  // Set in-memory
  setMemCache(key, result, CONTRACT_TTL);

  // Set in Redis
  try {
    await cacheService.setPrice(key, result);
  } catch (error) {
    console.warn('[AnalysisCache] Failed to cache contract in Redis');
  }
}

/**
 * Get cached social analysis
 */
export async function getCachedSocialAnalysis(
  platform: string,
  url: string
): Promise<any | null> {
  const key = socialKey(platform, url);

  // Try in-memory first
  const memCached = getFromMemCache(key);
  if (memCached) {
    console.log(`[AnalysisCache] Memory hit for social ${platform}: ${url}`);
    return memCached;
  }

  // Try Redis
  try {
    const cached = await cacheService.getPrice(key);
    if (cached) {
      console.log(`[AnalysisCache] Redis hit for social ${platform}: ${url}`);
      setMemCache(key, cached, SOCIAL_TTL);
      return cached;
    }
  } catch (error) {
    console.warn('[AnalysisCache] Redis unavailable for social');
  }

  return null;
}

/**
 * Set cached social analysis
 */
export async function setCachedSocialAnalysis(
  platform: string,
  url: string,
  result: any
): Promise<void> {
  const key = socialKey(platform, url);

  // Set in-memory
  setMemCache(key, result, SOCIAL_TTL);

  // Set in Redis
  try {
    await cacheService.setPrice(key, result);
  } catch (error) {
    console.warn('[AnalysisCache] Failed to cache social in Redis');
  }
}

/**
 * Invalidate all analysis cache for a specific target
 */
export async function invalidateAnalysisCache(type: 'github' | 'contract' | 'social', identifier: string): Promise<void> {
  // Clear from memory
  const pattern = `analysis:${type}:*`;
  for (const [key] of analysisCache) {
    if (key.startsWith(`analysis:${type}:`)) {
      analysisCache.delete(key);
    }
  }

  // Clear from Redis
  try {
    await cacheService.invalidatePattern(pattern);
  } catch (error) {
    console.warn('[AnalysisCache] Failed to invalidate cache in Redis');
  }
}

/**
 * Get cache statistics
 */
export function getAnalysisCacheStats(): {
  memoryCacheSize: number;
  keys: string[];
} {
  return {
    memoryCacheSize: analysisCache.size,
    keys: Array.from(analysisCache.keys()),
  };
}

/**
 * Clear all in-memory analysis cache
 */
export function clearAnalysisCache(): void {
  analysisCache.clear();
  console.log('[AnalysisCache] Cleared all in-memory cache');
}
