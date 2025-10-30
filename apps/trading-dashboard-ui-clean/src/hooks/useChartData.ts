import { useState, useEffect, useCallback, useRef } from 'react';
import type { ChartData } from '@/types/trading';

interface UseChartDataOptions {
  symbol: string;
  timeframe: string;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

interface UseChartDataReturn {
  data: ChartData | null;
  isLoading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
  retry: () => void;
}

export const useChartData = ({
  symbol,
  timeframe,
  autoRefresh = false,
  refreshInterval = 30000
}: UseChartDataOptions): UseChartDataReturn => {
  const [data, setData] = useState<ChartData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const refreshTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const fetchChartData = useCallback(async (): Promise<void> => {
    try {
      setIsLoading(true);
      setError(null);

      // Cancel previous request if still pending
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      abortControllerRef.current = new AbortController();

      // Simulate API call - replace with actual API endpoint
      const response = await fetch(`/api/charts/${symbol}/${timeframe}`, {
        signal: abortControllerRef.current.signal,
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch chart data: ${response.status} ${response.statusText}`);
      }

      const chartData: ChartData = await response.json();
      
      // Validate chart data structure
      if (!chartData || !Array.isArray(chartData.data)) {
        throw new Error('Invalid chart data format received');
      }

      setData(chartData);
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        // Request was cancelled, don't set error
        return;
      }
      
      const error = err instanceof Error ? err : new Error('Unknown error occurred');
      setError(error);
      console.error('Chart data fetch error:', error);
    } finally {
      setIsLoading(false);
    }
  }, [symbol, timeframe]);

  const retry = useCallback(() => {
    setError(null);
    fetchChartData();
  }, [fetchChartData]);

  // Initial fetch and setup auto-refresh
  useEffect(() => {
    fetchChartData();

    if (autoRefresh) {
      const setupRefresh = () => {
        if (refreshTimeoutRef.current) {
          clearTimeout(refreshTimeoutRef.current);
        }
        
        refreshTimeoutRef.current = setTimeout(() => {
          fetchChartData();
          setupRefresh(); // Schedule next refresh
        }, refreshInterval);
      };

      setupRefresh();
    }

    return () => {
      // Cleanup on unmount or dependency change
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      if (refreshTimeoutRef.current) {
        clearTimeout(refreshTimeoutRef.current);
      }
    };
  }, [fetchChartData, autoRefresh, refreshInterval]);

  return {
    data,
    isLoading,
    error,
    refetch: fetchChartData,
    retry
  };
};