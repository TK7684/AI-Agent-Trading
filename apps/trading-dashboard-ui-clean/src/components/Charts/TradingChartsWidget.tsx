import React, { useEffect, useRef, useCallback, useMemo } from 'react';
import { 
  createChart, 
  IChartApi, 
  ISeriesApi, 
  CandlestickSeriesOptions, 
  LineData, 
  CandlestickData as LWCCandle,
  DeepPartial,
  ChartOptions,
  SeriesMarker
} from 'lightweight-charts';
import { Card } from '@components/Common/Card';
import ChartErrorBoundary from './ChartErrorBoundary';
import ChartLoadingState from './ChartLoadingState';
import { useChartData } from '@/hooks/useChartData';
import type { ChartData, SignalMarker, IndicatorData } from '@/types/trading';

interface TradingChartsWidgetProps {
  symbol: string;
  timeframe: string;
  autoRefresh?: boolean;
  refreshInterval?: number;
  height?: number;
}

interface ChartRefs {
  chart: IChartApi | null;
  candleSeries: ISeriesApi<'Candlestick'> | null;
  maSeries: Record<string, ISeriesApi<'Line'>>;
}

const DEFAULT_CHART_OPTIONS: DeepPartial<ChartOptions> = {
  layout: { 
    background: { color: '#ffffff' }, 
    textColor: '#111827' 
  },
  grid: { 
    vertLines: { color: '#e5e7eb' }, 
    horzLines: { color: '#e5e7eb' } 
  },
  crosshair: {
    mode: 1, // Normal crosshair mode
  },
  timeScale: {
    timeVisible: true,
    secondsVisible: false,
  },
  handleScroll: {
    mouseWheel: true,
    pressedMouseMove: true,
  },
  handleScale: {
    axisPressedMouseMove: true,
    mouseWheel: true,
    pinch: true,
  },
};

const INDICATOR_COLORS = {
  MA: '#2563eb',
  RSI: '#dc2626',
  MACD: '#059669',
  BOLLINGER: '#7c3aed',
} as const;

const TradingChartsWidgetComponent: React.FC<TradingChartsWidgetProps> = ({ 
  symbol, 
  timeframe, 
  autoRefresh = true,
  refreshInterval = 30000,
  height = 320
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRefsRef = useRef<ChartRefs>({
    chart: null,
    candleSeries: null,
    maSeries: {}
  });
  const resizeObserverRef = useRef<ResizeObserver | null>(null);
  const isInitializedRef = useRef(false);
  const updateTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const { data, isLoading, error, retry } = useChartData({
    symbol,
    timeframe,
    autoRefresh,
    refreshInterval
  });

  // Memoize chart options to prevent unnecessary re-renders
  const chartOptions = useMemo(() => ({
    ...DEFAULT_CHART_OPTIONS,
    height
  }), [height]);

  // Initialize chart
  const initializeChart = useCallback(() => {
    if (!containerRef.current || isInitializedRef.current) return;

    try {
      const chart = createChart(containerRef.current, chartOptions);
      const candleSeries = chart.addCandlestickSeries({
        upColor: '#22c55e',
        downColor: '#ef4444',
        borderUpColor: '#22c55e',
        borderDownColor: '#ef4444',
        wickUpColor: '#22c55e',
        wickDownColor: '#ef4444',
      } as CandlestickSeriesOptions);

      chartRefsRef.current = {
        chart,
        candleSeries,
        maSeries: {}
      };

      // Setup resize observer for responsive behavior
      if (typeof ResizeObserver !== 'undefined') {
        resizeObserverRef.current = new ResizeObserver(() => {
          if (chartRefsRef.current.chart && containerRef.current) {
            chartRefsRef.current.chart.applyOptions({
              width: containerRef.current.clientWidth,
              height: height
            });
          }
        });

        resizeObserverRef.current.observe(containerRef.current);
      }
      isInitializedRef.current = true;

    } catch (error) {
      console.error('Failed to initialize chart:', error);
      throw error;
    }
  }, [chartOptions, height]);

  // Clean up chart resources
  const cleanupChart = useCallback(() => {
    try {
      // Clear any pending updates
      if (updateTimeoutRef.current) {
        clearTimeout(updateTimeoutRef.current);
        updateTimeoutRef.current = null;
      }

      // Remove resize observer
      if (resizeObserverRef.current && typeof resizeObserverRef.current.disconnect === 'function') {
        resizeObserverRef.current.disconnect();
        resizeObserverRef.current = null;
      }

      // Clean up chart instance
      if (chartRefsRef.current.chart && typeof chartRefsRef.current.chart.remove === 'function') {
        chartRefsRef.current.chart.remove();
      }

      // Reset refs
      chartRefsRef.current = {
        chart: null,
        candleSeries: null,
        maSeries: {}
      };
      
      isInitializedRef.current = false;
    } catch (error) {
      console.error('Error during chart cleanup:', error);
    }
  }, []);

  // Optimized chart data update with batching
  const updateChartData = useCallback((chartData: ChartData) => {
    if (!chartRefsRef.current.chart || !chartRefsRef.current.candleSeries) return;

    // Clear any pending updates
    if (updateTimeoutRef.current) {
      clearTimeout(updateTimeoutRef.current);
    }

    // Batch updates to prevent excessive re-renders
    updateTimeoutRef.current = setTimeout(() => {
      try {
        // Validate and transform candlestick data
        if (!Array.isArray(chartData.data) || chartData.data.length === 0) {
          console.warn('No chart data available');
          return;
        }

        const lwcCandles: LWCCandle[] = chartData.data
          .filter(candle => candle && typeof candle.time === 'number')
          .map((candle) => ({
            time: candle.time as any,
            open: Number(candle.open),
            high: Number(candle.high),
            low: Number(candle.low),
            close: Number(candle.close),
          }))
          .filter(candle => 
            !isNaN(candle.open) && 
            !isNaN(candle.high) && 
            !isNaN(candle.low) && 
            !isNaN(candle.close)
          );

        if (lwcCandles.length === 0) {
          console.warn('No valid candlestick data after filtering');
          return;
        }

        // Batch all chart updates
        chartRefsRef.current.candleSeries.setData(lwcCandles);
        updateIndicators(chartData.indicators);
        updateSignals(chartData.signals);
        
        // Fit content only if data significantly changed
        if (lwcCandles.length > 10) {
          chartRefsRef.current.chart.timeScale().fitContent();
        }

      } catch (error) {
        console.error('Error updating chart data:', error);
        throw error;
      }
    }, 16); // ~60fps batching
  }, []);

  // Update indicators
  const updateIndicators = useCallback((indicators: IndicatorData[]) => {
    if (!chartRefsRef.current.chart) return;

    try {
      // Clean up existing indicator series that are no longer needed
      const currentIndicatorIds = indicators.map(ind => ind.name);
      Object.keys(chartRefsRef.current.maSeries).forEach(id => {
        if (!currentIndicatorIds.includes(id)) {
          chartRefsRef.current.chart?.removeSeries(chartRefsRef.current.maSeries[id]);
          delete chartRefsRef.current.maSeries[id];
        }
      });

      // Add or update indicators
      indicators.forEach(indicator => {
        if (indicator.type === 'MA') {
          const id = indicator.name;
          
          if (!chartRefsRef.current.maSeries[id]) {
            chartRefsRef.current.maSeries[id] = chartRefsRef.current.chart!.addLineSeries({
              color: INDICATOR_COLORS[indicator.type] || '#2563eb',
              lineWidth: 2,
              title: indicator.name,
            });
          }

          const lineData: LineData[] = indicator.data
            .filter(point => point && typeof point.time === 'number' && typeof point.value === 'number')
            .map(point => ({
              time: point.time as any,
              value: Number(point.value)
            }))
            .filter(point => !isNaN(point.value));

          if (lineData.length > 0) {
            chartRefsRef.current.maSeries[id].setData(lineData);
          }
        }
      });
    } catch (error) {
      console.error('Error updating indicators:', error);
    }
  }, []);

  // Update signal markers
  const updateSignals = useCallback((signals: SignalMarker[]) => {
    if (!chartRefsRef.current.candleSeries || !Array.isArray(signals)) return;

    try {
      const markers: SeriesMarker<any>[] = signals
        .filter(signal => signal && typeof signal.time === 'number')
        .map((signal) => ({
          time: signal.time as any,
          position: signal.position,
          color: signal.color,
          shape: signal.shape,
          text: signal.text,
        }));

      chartRefsRef.current.candleSeries.setMarkers(markers);
    } catch (error) {
      console.error('Error updating signals:', error);
    }
  }, []);

  // Initialize chart on mount
  useEffect(() => {
    initializeChart();
    return cleanupChart;
  }, [initializeChart, cleanupChart]);

  // Update chart when data changes
  useEffect(() => {
    if (data && isInitializedRef.current) {
      updateChartData(data);
    }
  }, [data, updateChartData]);

  // Handle symbol/timeframe changes
  useEffect(() => {
    if (isInitializedRef.current) {
      // Clear existing data when symbol/timeframe changes
      if (chartRefsRef.current.candleSeries) {
        chartRefsRef.current.candleSeries.setData([]);
      }
      Object.values(chartRefsRef.current.maSeries).forEach(series => {
        series.setData([]);
      });
    }
  }, [symbol, timeframe]);

  const handleRetry = useCallback(() => {
    retry();
  }, [retry]);

  if (error) {
    return (
      <ChartErrorBoundary symbol={symbol} timeframe={timeframe} onRetry={handleRetry}>
        <div>Chart Error</div>
      </ChartErrorBoundary>
    );
  }

  if (isLoading) {
    return <ChartLoadingState symbol={symbol} timeframe={timeframe} />;
  }

  return (
    <ChartErrorBoundary symbol={symbol} timeframe={timeframe} onRetry={handleRetry}>
      <Card header={<h3 className="text-sm font-semibold">Chart - {symbol} ({timeframe})</h3>}>
        <div 
          ref={containerRef} 
          className="w-full"
          style={{ height: `${height}px` }}
        />
      </Card>
    </ChartErrorBoundary>
  );
};

// Memoized component with optimized comparison
export const TradingChartsWidget = React.memo(TradingChartsWidgetComponent, (prevProps, nextProps) => {
  return (
    prevProps.symbol === nextProps.symbol &&
    prevProps.timeframe === nextProps.timeframe &&
    prevProps.autoRefresh === nextProps.autoRefresh &&
    prevProps.refreshInterval === nextProps.refreshInterval &&
    prevProps.height === nextProps.height
  );
});

TradingChartsWidget.displayName = 'TradingChartsWidget';

export default TradingChartsWidget;
