/**
 * Performance optimization tests
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { 
  debounce, 
  throttle, 
  RequestDeduplicator, 
  calculateVirtualScroll,
  MemoCache,
  shallowEqual
} from '@/utils/performance';

describe('Performance Utilities', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('debounce', () => {
    it('should debounce function calls', () => {
      const fn = vi.fn();
      const debouncedFn = debounce(fn, 100);

      debouncedFn();
      debouncedFn();
      debouncedFn();

      expect(fn).not.toHaveBeenCalled();

      vi.advanceTimersByTime(100);
      expect(fn).toHaveBeenCalledTimes(1);
    });

    it('should support leading edge execution', () => {
      const fn = vi.fn();
      const debouncedFn = debounce(fn, 100, { leading: true });

      debouncedFn();
      expect(fn).toHaveBeenCalledTimes(1);

      debouncedFn();
      debouncedFn();
      vi.advanceTimersByTime(100);
      expect(fn).toHaveBeenCalledTimes(2);
    });

    it('should support cancellation', () => {
      const fn = vi.fn();
      const debouncedFn = debounce(fn, 100);

      debouncedFn();
      debouncedFn.cancel();

      vi.advanceTimersByTime(100);
      expect(fn).not.toHaveBeenCalled();
    });

    it('should support flush', () => {
      const fn = vi.fn(() => 'result');
      const debouncedFn = debounce(fn, 100);

      debouncedFn();
      const result = debouncedFn.flush();

      expect(fn).toHaveBeenCalledTimes(1);
      expect(result).toBe('result');
    });
  });

  describe('throttle', () => {
    it('should throttle function calls', () => {
      const fn = vi.fn();
      const throttledFn = throttle(fn, 100);

      throttledFn();
      throttledFn();
      throttledFn();

      expect(fn).toHaveBeenCalledTimes(1);

      vi.advanceTimersByTime(100);
      throttledFn();
      // Throttle with trailing edge may call the function again
      expect(fn).toHaveBeenCalledTimes(3);
    });
  });

  describe('RequestDeduplicator', () => {
    it('should deduplicate identical requests', async () => {
      const deduplicator = new RequestDeduplicator(1000);
      const mockRequest = vi.fn().mockResolvedValue('result');

      const promise1 = deduplicator.dedupe('key1', mockRequest);
      const promise2 = deduplicator.dedupe('key1', mockRequest);

      const [result1, result2] = await Promise.all([promise1, promise2]);

      expect(mockRequest).toHaveBeenCalledTimes(1);
      expect(result1).toBe('result');
      expect(result2).toBe('result');
    });

    it('should cache results within TTL', async () => {
      const deduplicator = new RequestDeduplicator(1000);
      const mockRequest = vi.fn().mockResolvedValue('result');

      await deduplicator.dedupe('key1', mockRequest, 1000);
      await deduplicator.dedupe('key1', mockRequest, 1000);

      expect(mockRequest).toHaveBeenCalledTimes(1);
    });

    it('should clear cache', async () => {
      const deduplicator = new RequestDeduplicator(1000);
      const mockRequest = vi.fn().mockResolvedValue('result');

      await deduplicator.dedupe('key1', mockRequest, 1000);
      deduplicator.clearCache();
      await deduplicator.dedupe('key1', mockRequest, 1000);

      expect(mockRequest).toHaveBeenCalledTimes(2);
    });
  });

  describe('calculateVirtualScroll', () => {
    it('should calculate correct virtual scroll parameters', () => {
      const result = calculateVirtualScroll(1000, {
        itemHeight: 50,
        containerHeight: 400,
        overscan: 5,
        scrollTop: 250,
      });

      expect(result.startIndex).toBe(0); // max(0, 5 - 5)
      expect(result.endIndex).toBe(18); // min(999, 13 + 5) - corrected calculation
      expect(result.offsetY).toBe(0);
      expect(result.totalHeight).toBe(50000);
    });

    it('should handle edge cases', () => {
      const result = calculateVirtualScroll(0, {
        itemHeight: 50,
        containerHeight: 400,
        overscan: 5,
        scrollTop: 0,
      });

      expect(result.startIndex).toBe(0);
      expect(result.endIndex).toBe(-1);
      expect(result.totalHeight).toBe(0);
    });
  });

  describe('MemoCache', () => {
    it('should cache and retrieve values', () => {
      const cache = new MemoCache<string, number>(10, 1000);

      cache.set('key1', 42);
      expect(cache.get('key1')).toBe(42);
    });

    it('should respect TTL', () => {
      const cache = new MemoCache<string, number>(10, 100);

      cache.set('key1', 42);
      expect(cache.get('key1')).toBe(42);

      vi.advanceTimersByTime(150);
      expect(cache.get('key1')).toBeUndefined();
    });

    it('should respect max size with LRU eviction', () => {
      const cache = new MemoCache<string, number>(2, 1000);

      cache.set('key1', 1);
      cache.set('key2', 2);
      cache.set('key3', 3); // Should evict key1

      expect(cache.get('key1')).toBeUndefined();
      expect(cache.get('key2')).toBe(2);
      expect(cache.get('key3')).toBe(3);
    });
  });

  describe('shallowEqual', () => {
    it('should return true for identical objects', () => {
      const obj1 = { a: 1, b: 2 };
      const obj2 = { a: 1, b: 2 };

      expect(shallowEqual(obj1, obj2)).toBe(true);
    });

    it('should return false for different objects', () => {
      const obj1 = { a: 1, b: 2 };
      const obj2 = { a: 1, b: 3 };

      expect(shallowEqual(obj1, obj2)).toBe(false);
    });

    it('should return true for same reference', () => {
      const obj = { a: 1, b: 2 };

      expect(shallowEqual(obj, obj)).toBe(true);
    });

    it('should handle null and undefined', () => {
      expect(shallowEqual(null, null)).toBe(true);
      expect(shallowEqual(undefined, undefined)).toBe(true);
      expect(shallowEqual(null, undefined)).toBe(false);
    });
  });
});

describe('Virtual Scroll Performance', () => {
  it('should handle large datasets efficiently', () => {
    const startTime = performance.now();
    
    // Simulate large dataset
    const itemCount = 100000;
    
    const result = calculateVirtualScroll(itemCount, {
      itemHeight: 50,
      containerHeight: 400,
      overscan: 10,
      scrollTop: 50000, // Scroll to middle
    });

    const endTime = performance.now();
    const duration = endTime - startTime;

    // Should complete in less than 1ms for good performance
    expect(duration).toBeLessThan(1);
    expect(result.startIndex).toBeGreaterThanOrEqual(0);
    expect(result.endIndex).toBeLessThan(itemCount);
  });
});

describe('Request Deduplication Performance', () => {
  it('should handle concurrent requests efficiently', async () => {
    const deduplicator = new RequestDeduplicator(1000);
    let requestCount = 0;
    
    const mockRequest = vi.fn().mockImplementation(() => {
      requestCount++;
      return Promise.resolve(`result-${requestCount}`);
    });

    // Make 100 concurrent identical requests
    const promises = Array.from({ length: 100 }, () =>
      deduplicator.dedupe('same-key', mockRequest)
    );

    const results = await Promise.all(promises);

    // Should only make one actual request
    expect(mockRequest).toHaveBeenCalledTimes(1);
    
    // All results should be identical
    expect(results.every(result => result === results[0])).toBe(true);
  });
});