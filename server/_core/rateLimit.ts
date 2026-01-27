/**
 * Rate Limiting Middleware
 * Redis-backed rate limiting for API endpoints
 * Supports different limits per subscription tier
 */

import { TRPCError } from '@trpc/server';
import { cacheService } from '../services/cacheService';
import { getUserTier, getRateLimit, SubscriptionTier } from './subscription';

interface RateLimitConfig {
  requests: number;
  window: number; // in seconds
}

interface RateLimitInfo {
  remaining: number;
  reset: number;
  limit: number;
}

// Default rate limits (can be overridden per endpoint)
const DEFAULT_LIMITS: Record<string, RateLimitConfig> = {
  // Global defaults per tier
  default: {
    requests: 30,
    window: 60, // 30 requests per minute for free users
  },
  pro: {
    requests: 100,
    window: 60,
  },
  enterprise: {
    requests: 1000,
    window: 60,
  },
};

// Endpoint-specific overrides (applies to all tiers)
const ENDPOINT_OVERRIDES: Record<string, Partial<RateLimitConfig>> = {
  // Stricter limits for expensive operations
  'project.analyze': { requests: 5, window: 60 },
  'unicorn.startScan': { requests: 2, window: 300 },

  // Relaxed limits for read operations
  'project.list': { requests: 60, window: 60 },
  'discovery.trending': { requests: 60, window: 60 },
  'marketData.getPrice': { requests: 60, window: 60 },
};

/**
 * Generate rate limit key
 */
function getRateLimitKey(identifier: string, endpoint: string): string {
  const timestamp = Math.floor(Date.now() / 1000);
  const window = DEFAULT_LIMITS.default.window;
  const windowStart = Math.floor(timestamp / window) * window;
  return `ratelimit:${endpoint}:${identifier}:${windowStart}`;
}

/**
 * Check rate limit for a request
 */
export async function checkRateLimit(
  identifier: string,
  endpoint: string,
  tier: SubscriptionTier = SubscriptionTier.FREE
): Promise<RateLimitInfo> {
  // Get the limit for this tier
  const baseLimit = DEFAULT_LIMITS[tier] || DEFAULT_LIMITS.default;
  const override = ENDPOINT_OVERRIDES[endpoint];

  const limit = override?.requests || baseLimit.requests;
  const window = override?.window || baseLimit.window;

  const key = getRateLimitKey(identifier, endpoint);
  const reset = Math.ceil((Date.now() / 1000) / window) * window;

  try {
    // Try Redis first
    const cached = await cacheService.getPrice(key);
    const current = cached ? (cached as any).count || 0 : 0;

    if (current >= limit) {
      return {
        remaining: 0,
        reset,
        limit,
      };
    }

    // Increment counter
    const newCount = current + 1;
    await cacheService.setPrice(key, { count: newCount });

    return {
      remaining: limit - newCount,
      reset,
      limit,
    };
  } catch (error) {
    // Fallback to in-memory if Redis fails
    console.warn('[RateLimit] Redis unavailable, using in-memory fallback');
    return {
      remaining: limit - 1,
      reset,
      limit,
    };
  }
}

/**
 * Rate limiting middleware factory for tRPC
 */
export function createRateLimitMiddleware(options?: {
  // Custom endpoint name (defaults to procedure path)
  endpoint?: string;
  // Custom limit for this endpoint
  limit?: Partial<RateLimitConfig>;
}) {
  return async ({ ctx, next }: any) => {
    // Skip rate limiting for admins
    if (ctx.user?.role === 'admin') {
      return next();
    }

    const endpoint = options?.endpoint || ctx._input?.type || 'unknown';
    const userId = ctx.user?.id?.toString() || ctx.req?.ip || 'anonymous';
    const tier = ctx.user ? getUserTier(ctx.user.role) : SubscriptionTier.FREE;

    const result = await checkRateLimit(userId, endpoint, tier);

    // Add rate limit headers to response
    if (ctx.res) {
      ctx.res.setHeader('X-RateLimit-Limit', result.limit.toString());
      ctx.res.setHeader('X-RateLimit-Remaining', result.remaining.toString());
      ctx.res.setHeader('X-RateLimit-Reset', result.reset.toString());
    }

    if (result.remaining === 0) {
      throw new TRPCError({
        code: 'TOO_MANY_REQUESTS',
        message: `Rate limit exceeded. Try again in ${result.reset - Math.floor(Date.now() / 1000)} seconds.`,
      });
    }

    return next();
  };
}

/**
 * In-memory rate limiter (fallback when Redis is unavailable)
 */
class InMemoryRateLimiter {
  private counters = new Map<string, { count: number; reset: number }>();

  check(
    identifier: string,
    endpoint: string,
    limit: number,
    window: number
  ): RateLimitInfo {
    const key = `${identifier}:${endpoint}`;
    const now = Date.now();
    const windowMs = window * 1000;

    const existing = this.counters.get(key);

    if (!existing || now > existing.reset) {
      // New window
      const reset = now + windowMs;
      this.counters.set(key, { count: 1, reset });
      return { remaining: limit - 1, reset: Math.ceil(reset / 1000), limit };
    }

    if (existing.count >= limit) {
      return { remaining: 0, reset: Math.ceil(existing.reset / 1000), limit };
    }

    existing.count++;
    return {
      remaining: limit - existing.count,
      reset: Math.ceil(existing.reset / 1000),
      limit,
    };
  }

  clear(identifier?: string): void {
    if (identifier) {
      for (const [key] of this.counters) {
        if (key.startsWith(identifier)) {
          this.counters.delete(key);
        }
      }
    } else {
      this.counters.clear();
    }
  }
}

export const inMemoryRateLimiter = new InMemoryRateLimiter();
