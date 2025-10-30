/**
 * Example of an optimized trading dashboard using all performance enhancements
 */

import React, { useState, useCallback, useMemo } from 'react';
import { TradingLogsWidget } from '@/components/Trading/TradingLogsWidget';
import { PerformanceWidget } from '@/components/Trading/PerformanceWidget';
import { TradingChartsWidget } from '@/components/Charts/TradingChartsWidget';
import { useOptimizedTradingLogs, useBatchApi } from '@/hooks/useOptimizedApi';
import { usePerformanceMonitor } from '@/utils/stateOptimization';
import type { TradeLogEntry } from '@/types/trading';

interface OptimizedTradingDashboardProps {
  symbol: string;
  timeframe: string;
}

// Memoized sub-components to prevent unnecessary re-renders
const MemoizedPerformanceWidget = React.memo(PerformanceWidget);
const MemoizedTradingChartsWidget = React.memo(TradingChartsWidget);

export const OptimizedTradingDashboard: React.FC<OptimizedTradingDashboardProps> = ({
  symbol,
  timeframe,
}) => {
  const { startTiming, getMetrics } = usePerformanceMonitor('OptimizedTradingDashboard');
  
  // Optimized trading logs with debounced search and filtering
  const {
    data: tradingLogsData,
    isLoading: logsLoading,
    error: logsError,
    searchLogs,
    updateFilters,
    filters,
  } = useOptimizedTradingLogs();

  // Batch API requests for dashboard data
  const {
    data: dashboardData,
    isLoading: dashboardLoading,
    error: dashboardError,
    retry: retryDashboard,
  } = useBatchApi([
    { endpoint: '/trading/positions' },
    { endpoint: '/trading/performance' },
    { endpoint: '/system/health' },
  ]);

  // Local state for UI interactions
  const [selectedTrade, setSelectedTrade] = useState<TradeLogEntry | null>(null);
  const [dashboardLayout, setDashboardLayout] = useState('grid');

  // Memoized handlers to prevent recreation on every render
  const handleTradeSearch = useCallback((query: string) => {
    const endTiming = startTiming();
    searchLogs(query);
    endTiming();
  }, [searchLogs, startTiming]);

  const handleFilterChange = useCallback((newFilters: any) => {
    const endTiming = startTiming();
    updateFilters(newFilters);
    endTiming();
  }, [updateFilters, startTiming]);

  const handleTradeSelect = useCallback((trade: TradeLogEntry) => {
    setSelectedTrade(trade);
  }, []);

  const handleLayoutChange = useCallback((layout: string) => {
    setDashboardLayout(layout);
  }, []);

  // Memoized computed values
  const trades = useMemo(() => {
    return tradingLogsData?.data || [];
  }, [tradingLogsData]);

  const performanceMetrics = useMemo(() => {
    return dashboardData?.[1] || null;
  }, [dashboardData]);

  const isLoading = useMemo(() => {
    return logsLoading || dashboardLoading;
  }, [logsLoading, dashboardLoading]);

  // Memoized error state
  const hasError = useMemo(() => {
    return !!(logsError || dashboardError);
  }, [logsError, dashboardError]);

  // Performance metrics display
  const renderPerformanceMetrics = useCallback(() => {
    const metrics = getMetrics();
    if (metrics.count === 0) return null;

    return (
      <div className="mb-4 p-2 bg-gray-100 rounded text-xs">
        <strong>Performance:</strong> Avg: {metrics.avg.toFixed(2)}ms, 
        Min: {metrics.min.toFixed(2)}ms, Max: {metrics.max.toFixed(2)}ms
      </div>
    );
  }, [getMetrics]);

  // Error boundary fallback
  if (hasError) {
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded">
        <h3 className="text-red-800 font-semibold">Dashboard Error</h3>
        <p className="text-red-600 text-sm mt-1">
          {logsError || dashboardError}
        </p>
        <button 
          onClick={retryDashboard}
          className="mt-2 px-3 py-1 bg-red-600 text-white rounded text-sm hover:bg-red-700"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="p-4 space-y-4">
      {/* Performance Metrics (Development only) */}
      {process.env.NODE_ENV === 'development' && renderPerformanceMetrics()}

      {/* Loading State */}
      {isLoading && (
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="ml-2 text-gray-600">Loading dashboard...</span>
        </div>
      )}

      {/* Dashboard Layout Controls */}
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold text-gray-900">
          Trading Dashboard - {symbol} ({timeframe})
        </h1>
        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-600">Layout:</label>
          <select 
            value={dashboardLayout}
            onChange={(e) => handleLayoutChange(e.target.value)}
            className="border border-gray-300 rounded px-2 py-1 text-sm"
          >
            <option value="grid">Grid</option>
            <option value="stack">Stack</option>
            <option value="compact">Compact</option>
          </select>
        </div>
      </div>

      {/* Dashboard Content */}
      <div className={`grid gap-4 ${
        dashboardLayout === 'grid' ? 'grid-cols-1 lg:grid-cols-2' :
        dashboardLayout === 'stack' ? 'grid-cols-1' :
        'grid-cols-1 md:grid-cols-3'
      }`}>
        
        {/* Performance Widget */}
        <div className={dashboardLayout === 'compact' ? 'col-span-1' : 'col-span-1'}>
          <MemoizedPerformanceWidget 
            compact={dashboardLayout === 'compact'}
          />
        </div>

        {/* Trading Chart */}
        <div className={dashboardLayout === 'grid' ? 'col-span-1' : 'col-span-1'}>
          <MemoizedTradingChartsWidget
            symbol={symbol}
            timeframe={timeframe}
            height={dashboardLayout === 'compact' ? 200 : 320}
            autoRefresh={true}
            refreshInterval={30000}
          />
        </div>

        {/* Trading Logs */}
        <div className={
          dashboardLayout === 'grid' ? 'col-span-2' :
          dashboardLayout === 'stack' ? 'col-span-1' :
          'col-span-3'
        }>
          <TradingLogsWidget
            trades={trades}
            onSearch={handleTradeSearch}
            onFilter={handleFilterChange}
            isLoading={logsLoading}
          />
        </div>
      </div>

      {/* Selected Trade Details Modal */}
      {selectedTrade && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">Trade Details</h3>
              <button 
                onClick={() => setSelectedTrade(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                ✕
              </button>
            </div>
            <div className="space-y-2 text-sm">
              <div><strong>Symbol:</strong> {selectedTrade.symbol}</div>
              <div><strong>Side:</strong> {selectedTrade.side}</div>
              <div><strong>Entry Price:</strong> ${selectedTrade.entryPrice}</div>
              <div><strong>Quantity:</strong> {selectedTrade.quantity}</div>
              <div><strong>Status:</strong> {selectedTrade.status}</div>
              {selectedTrade.pnl !== undefined && (
                <div className={`font-semibold ${
                  selectedTrade.pnl > 0 ? 'text-green-600' : 
                  selectedTrade.pnl < 0 ? 'text-red-600' : 'text-gray-600'
                }`}>
                  <strong>P&L:</strong> ${selectedTrade.pnl.toFixed(2)}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// Export memoized version for better performance
export default React.memo(OptimizedTradingDashboard, (prevProps, nextProps) => {
  return (
    prevProps.symbol === nextProps.symbol &&
    prevProps.timeframe === nextProps.timeframe
  );
});