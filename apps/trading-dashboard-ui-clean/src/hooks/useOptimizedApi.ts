import { useState, useCallback, useRef, useEffect } from 'react';
import { apiService } from '@/services';
import { debounce, RequestDeduplicator } from '@/utils/performance';
import type { ApiResponse, PaginatedResponse } from '@/types';

interface UseOptimizedApiOptions {
  debounceMs?: number;
  cacheTimeout?: number;
  enableDeduplication?: boolean;
}

interface UseOptimizedApiResult<T> {
  data: T | null;
  isLoading: boolean;
  error: string | null;
  search: (query: string) => void;
  filter: (filters: any) => void;
  refresh: () => void;
  clearCache: () => void;
}

export function useOptimizedApi<T>(
  endpoint: string,
  options: UseOptimizedApiOptions = {}
): UseOptimizedApiResult<T> {
  const {
    debounceMs = 300,
    cacheTimeout = 5000,
    enableDeduplication = true,
  } = options;

  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const currentRequestRef = useRef<AbortController | null>(null);
  const deduplicatorRef = useRef<RequestDeduplicator>(new RequestDeduplicator(cacheTimeout));
  const lastParamsRef = useRef<any>(null);

  // Debounced search function
  const debouncedSearch = useRef(
    debounce(async (query: string, filters: any = {}) => {
      await performRequest({ search: query, ...filters });
    }, debounceMs, { trailing: true })
  ).current;

  // Debounced filter function
  const debouncedFilter = useRef(
    debounce(async (filters: any) => {
      await performRequest(filters);
    }, debounceMs / 2, { trailing: true })
  ).current;

  // Core request function with optimization
  const performRequest = useCallback(async (params: any = {}) => {
    // Cancel previous request
    if (currentRequestRef.current) {
      currentRequestRef.current.abort();
    }

    // Create new abort controller
    currentRequestRef.current = new AbortController();

    try {
      setIsLoading(true);
      setError(null);

      const requestKey = `${endpoint}:${JSON.stringify(params)}`;
      
      let response: ApiResponse<T>;

      if (enableDeduplication) {
        response = await deduplicatorRef.current.dedupe(
          requestKey,
          () => apiService.get<T>(endpoint, params),
          cacheTimeout
        );
      } else {
        response = await apiService.get<T>(endpoint, params);
      }

      // Check if request was aborted
      if (currentRequestRef.current?.signal.aborted) {
        return;
      }

      if (response.success && response.data) {
        setData(response.data);
        lastParamsRef.current = params;
      } else {
        setError(response.error?.message || 'Request failed');
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        setError(err.message || 'Network error');
      }
    } finally {
      setIsLoading(false);
      currentRequestRef.current = null;
    }
  }, [endpoint, enableDeduplication, cacheTimeout]);

  // Public API functions
  const search = useCallback((query: string) => {
    debouncedSearch.cancel();
    debouncedSearch(query, lastParamsRef.current);
  }, [debouncedSearch]);

  const filter = useCallback((filters: any) => {
    debouncedFilter.cancel();
    debouncedFilter(filters);
  }, [debouncedFilter]);

  const refresh = useCallback(() => {
    debouncedSearch.cancel();
    debouncedFilter.cancel();
    performRequest(lastParamsRef.current);
  }, [performRequest]);

  const clearCache = useCallback(() => {
    deduplicatorRef.current.clearCache();
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (currentRequestRef.current) {
        currentRequestRef.current.abort();
      }
      debouncedSearch.cancel();
      debouncedFilter.cancel();
    };
  }, [debouncedSearch, debouncedFilter]);

  return {
    data,
    isLoading,
    error,
    search,
    filter,
    refresh,
    clearCache,
  };
}

// Specialized hook for trading logs with optimizations
export function useOptimizedTradingLogs() {
  const [filters, setFilters] = useState({
    status: 'all',
    symbol: 'all',
    pnlFilter: 'all',
  });

  const api = useOptimizedApi<PaginatedResponse<any>>('/trading/trades', {
    debounceMs: 300,
    cacheTimeout: 3000,
    enableDeduplication: true,
  });

  const updateFilters = useCallback((newFilters: Partial<typeof filters>) => {
    const updatedFilters = { ...filters, ...newFilters };
    setFilters(updatedFilters);
    api.filter(updatedFilters);
  }, [filters, api]);

  const searchLogs = useCallback((query: string) => {
    api.search(query);
  }, [api]);

  return {
    ...api,
    filters,
    updateFilters,
    searchLogs,
  };
}

// Hook for batch API requests with optimization
export function useBatchApi<T>(requests: Array<{ endpoint: string; params?: any }>) {
  const [data, setData] = useState<T[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const execute = useCallback(async () => {
    if (requests.length === 0) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await apiService.batchOptimizedRequests<T>(requests);
      
      if (response.success && response.data) {
        setData(response.data);
      } else {
        setError(response.error?.message || 'Batch request failed');
      }
    } catch (err: any) {
      setError(err.message || 'Network error');
    } finally {
      setIsLoading(false);
    }
  }, [requests]);

  useEffect(() => {
    execute();
  }, [execute]);

  return {
    data,
    isLoading,
    error,
    retry: execute,
  };
}

// Hook for optimized real-time data with throttling
export function useOptimizedRealTimeData<T>(
  initialData: T,
  updateInterval: number = 1000
) {
  const [data, setData] = useState<T>(initialData);
  const updateQueueRef = useRef<T[]>([]);
  const isProcessingRef = useRef(false);

  // Throttled update function
  const throttledUpdate = useRef(
    debounce(() => {
      if (updateQueueRef.current.length === 0 || isProcessingRef.current) return;

      isProcessingRef.current = true;
      
      // Process all queued updates
      const latestUpdate = updateQueueRef.current[updateQueueRef.current.length - 1];
      updateQueueRef.current = [];
      
      setData(latestUpdate);
      
      // Use requestAnimationFrame for smooth updates
      requestAnimationFrame(() => {
        isProcessingRef.current = false;
      });
    }, updateInterval, { leading: false, trailing: true })
  ).current;

  const updateData = useCallback((newData: T) => {
    updateQueueRef.current.push(newData);
    throttledUpdate();
  }, [throttledUpdate]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      throttledUpdate.cancel();
    };
  }, [throttledUpdate]);

  return {
    data,
    updateData,
  };
}