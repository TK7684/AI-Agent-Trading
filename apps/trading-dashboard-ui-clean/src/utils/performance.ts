/**
 * Performance optimization utilities
 */

// Enhanced debounce with immediate execution option and cancellation
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number,
  options: {
    leading?: boolean;
    trailing?: boolean;
    maxWait?: number;
  } = {}
): T & { cancel: () => void; flush: () => ReturnType<T> | undefined } {
  let timeout: NodeJS.Timeout | null = null;
  let maxTimeout: NodeJS.Timeout | null = null;
  let lastCallTime: number | null = null;
  let lastInvokeTime = 0;
  let lastArgs: Parameters<T> | null = null;
  let lastThis: any = null;
  let result: ReturnType<T> | undefined;

  const { leading = false, trailing = true, maxWait } = options;

  function invokeFunc(time: number): ReturnType<T> {
    const args = lastArgs!;
    const thisArg = lastThis;
    lastArgs = null;
    lastThis = null;
    lastInvokeTime = time;
    result = func.apply(thisArg, args);
    return result;
  }

  function leadingEdge(time: number): ReturnType<T> {
    lastInvokeTime = time;
    timeout = setTimeout(timerExpired, wait);
    return leading ? invokeFunc(time) : result!;
  }

  function remainingWait(time: number): number {
    const timeSinceLastCall = time - lastCallTime!;
    const timeSinceLastInvoke = time - lastInvokeTime;
    const timeWaiting = wait - timeSinceLastCall;

    return maxWait !== undefined
      ? Math.min(timeWaiting, maxWait - timeSinceLastInvoke)
      : timeWaiting;
  }

  function shouldInvoke(time: number): boolean {
    const timeSinceLastCall = time - lastCallTime!;
    const timeSinceLastInvoke = time - lastInvokeTime;

    return (
      lastCallTime === null ||
      timeSinceLastCall >= wait ||
      timeSinceLastCall < 0 ||
      (maxWait !== undefined && timeSinceLastInvoke >= maxWait)
    );
  }

  function timerExpired(): ReturnType<T> | undefined {
    const time = Date.now();
    if (shouldInvoke(time)) {
      return trailingEdge(time);
    }
    timeout = setTimeout(timerExpired, remainingWait(time));
    return undefined;
  }

  function trailingEdge(time: number): ReturnType<T> | undefined {
    timeout = null;

    if (trailing && lastArgs) {
      return invokeFunc(time);
    }
    lastArgs = null;
    lastThis = null;
    return result;
  }

  function cancel(): void {
    if (timeout !== null) {
      clearTimeout(timeout);
      timeout = null;
    }
    if (maxTimeout !== null) {
      clearTimeout(maxTimeout);
      maxTimeout = null;
    }
    lastInvokeTime = 0;
    lastCallTime = null;
    lastArgs = null;
    lastThis = null;
  }

  function flush(): ReturnType<T> | undefined {
    return timeout === null ? result : trailingEdge(Date.now());
  }

  function debounced(this: any, ...args: Parameters<T>): ReturnType<T> | undefined {
    const time = Date.now();
    const isInvoking = shouldInvoke(time);

    lastArgs = args;
    lastThis = this;
    lastCallTime = time;

    if (isInvoking) {
      if (timeout === null) {
        return leadingEdge(lastCallTime);
      }
      if (maxWait !== undefined) {
        timeout = setTimeout(timerExpired, wait);
        return invokeFunc(lastCallTime);
      }
    }
    if (timeout === null) {
      timeout = setTimeout(timerExpired, wait);
    }
    return result;
  }

  debounced.cancel = cancel;
  debounced.flush = flush;

  return debounced as T & { cancel: () => void; flush: () => ReturnType<T> | undefined };
}

// Enhanced throttle with leading and trailing options
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  wait: number,
  options: {
    leading?: boolean;
    trailing?: boolean;
  } = {}
): T & { cancel: () => void; flush: () => ReturnType<T> | undefined } {
  const { leading = true, trailing = true } = options;
  return debounce(func, wait, {
    leading,
    trailing,
    maxWait: wait,
  });
}

// Request deduplication utility
export class RequestDeduplicator {
  private inFlightRequests = new Map<string, Promise<any>>();
  private requestCache = new Map<string, { data: any; timestamp: number; ttl: number }>();

  constructor(private defaultTTL: number = 5000) {}

  // Generate cache key from request parameters
  private generateKey(url: string, params?: any): string {
    const paramStr = params ? JSON.stringify(params) : '';
    return `${url}:${paramStr}`;
  }

  // Check if cached data is still valid
  private isCacheValid(entry: { timestamp: number; ttl: number }): boolean {
    return Date.now() - entry.timestamp < entry.ttl;
  }

  // Deduplicate requests with caching
  async dedupe<T>(
    key: string,
    requestFn: () => Promise<T>,
    ttl: number = this.defaultTTL
  ): Promise<T> {
    // Check cache first
    const cached = this.requestCache.get(key);
    if (cached && this.isCacheValid(cached)) {
      return cached.data;
    }

    // Check if request is already in flight
    if (this.inFlightRequests.has(key)) {
      return this.inFlightRequests.get(key)!;
    }

    // Execute new request
    const promise = requestFn()
      .then((data) => {
        // Cache the result
        this.requestCache.set(key, {
          data,
          timestamp: Date.now(),
          ttl,
        });
        return data;
      })
      .finally(() => {
        // Remove from in-flight requests
        this.inFlightRequests.delete(key);
      });

    this.inFlightRequests.set(key, promise);
    return promise;
  }

  // Clear cache entries
  clearCache(pattern?: string): void {
    if (pattern) {
      const regex = new RegExp(pattern);
      for (const key of this.requestCache.keys()) {
        if (regex.test(key)) {
          this.requestCache.delete(key);
        }
      }
    } else {
      this.requestCache.clear();
    }
  }

  // Get cache statistics
  getCacheStats(): { size: number; inFlight: number } {
    return {
      size: this.requestCache.size,
      inFlight: this.inFlightRequests.size,
    };
  }
}

// Virtual scrolling utilities
export interface VirtualScrollOptions {
  itemHeight: number;
  containerHeight: number;
  overscan?: number;
  scrollTop: number;
}

export interface VirtualScrollResult {
  startIndex: number;
  endIndex: number;
  offsetY: number;
  totalHeight: number;
}

export function calculateVirtualScroll(
  itemCount: number,
  options: VirtualScrollOptions
): VirtualScrollResult {
  const { itemHeight, containerHeight, overscan = 5, scrollTop } = options;

  const totalHeight = itemCount * itemHeight;
  const visibleStart = Math.floor(scrollTop / itemHeight);
  const visibleEnd = Math.min(
    itemCount - 1,
    Math.ceil((scrollTop + containerHeight) / itemHeight)
  );

  const startIndex = Math.max(0, visibleStart - overscan);
  const endIndex = Math.min(itemCount - 1, visibleEnd + overscan);
  const offsetY = startIndex * itemHeight;

  return {
    startIndex,
    endIndex,
    offsetY,
    totalHeight,
  };
}

// Memoization utility with LRU cache
export class MemoCache<K, V> {
  private cache = new Map<K, { value: V; timestamp: number }>();
  private accessOrder: K[] = [];

  constructor(
    private maxSize: number = 100,
    private ttl: number = 60000 // 1 minute default
  ) {}

  get(key: K): V | undefined {
    const entry = this.cache.get(key);
    if (!entry) return undefined;

    // Check TTL
    if (Date.now() - entry.timestamp > this.ttl) {
      this.delete(key);
      return undefined;
    }

    // Update access order
    this.updateAccessOrder(key);
    return entry.value;
  }

  set(key: K, value: V): void {
    // Remove oldest entries if cache is full
    if (this.cache.size >= this.maxSize && !this.cache.has(key)) {
      const oldestKey = this.accessOrder.shift();
      if (oldestKey !== undefined) {
        this.cache.delete(oldestKey);
      }
    }

    this.cache.set(key, { value, timestamp: Date.now() });
    this.updateAccessOrder(key);
  }

  delete(key: K): boolean {
    const deleted = this.cache.delete(key);
    if (deleted) {
      const index = this.accessOrder.indexOf(key);
      if (index > -1) {
        this.accessOrder.splice(index, 1);
      }
    }
    return deleted;
  }

  clear(): void {
    this.cache.clear();
    this.accessOrder = [];
  }

  private updateAccessOrder(key: K): void {
    const index = this.accessOrder.indexOf(key);
    if (index > -1) {
      this.accessOrder.splice(index, 1);
    }
    this.accessOrder.push(key);
  }

  size(): number {
    return this.cache.size;
  }
}

// React component optimization utilities
export function shallowEqual(obj1: any, obj2: any): boolean {
  if (obj1 === obj2) return true;
  
  if (obj1 == null || obj2 == null) return false;
  
  if (typeof obj1 !== 'object' || typeof obj2 !== 'object') return false;

  const keys1 = Object.keys(obj1);
  const keys2 = Object.keys(obj2);

  if (keys1.length !== keys2.length) return false;

  for (const key of keys1) {
    if (obj1[key] !== obj2[key]) return false;
  }

  return true;
}

// Batch update utility for state management
export class BatchUpdater<T> {
  private pendingUpdates: Array<(state: T) => T> = [];
  private isScheduled = false;

  constructor(private applyUpdates: (updates: Array<(state: T) => T>) => void) {}

  addUpdate(updateFn: (state: T) => T): void {
    this.pendingUpdates.push(updateFn);
    this.scheduleFlush();
  }

  private scheduleFlush(): void {
    if (this.isScheduled) return;

    this.isScheduled = true;
    // Use MessageChannel for better performance than setTimeout
    if (typeof MessageChannel !== 'undefined') {
      const channel = new MessageChannel();
      channel.port2.onmessage = () => this.flush();
      channel.port1.postMessage(null);
    } else {
      setTimeout(() => this.flush(), 0);
    }
  }

  private flush(): void {
    if (this.pendingUpdates.length === 0) {
      this.isScheduled = false;
      return;
    }

    const updates = [...this.pendingUpdates];
    this.pendingUpdates = [];
    this.isScheduled = false;

    this.applyUpdates(updates);
  }

  cancel(): void {
    this.pendingUpdates = [];
    this.isScheduled = false;
  }
}