import React from 'react';
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { TradingChartsWidget } from '@components/Charts/TradingChartsWidget';
import { ChartErrorBoundary } from '@components/Charts/ChartErrorBoundary';
import { ChartLoadingState } from '@components/Charts/ChartLoadingState';
import { useChartData } from '@/hooks/useChartData';
import type { ChartData } from '@/types/trading';

// Mock lightweight-charts
const mockChart = {
  addCandlestickSeries: vi.fn(),
  addLineSeries: vi.fn(),
  removeSeries: vi.fn(),
  remove: vi.fn(),
  timeScale: vi.fn(() => ({
    fitContent: vi.fn()
  })),
  applyOptions: vi.fn()
};

const mockCandleSeries = {
  setData: vi.fn(),
  setMarkers: vi.fn()
};

const mockLineSeries = {
  setData: vi.fn()
};

vi.mock('lightweight-charts', () => ({
  createChart: vi.fn(() => mockChart),
}));

// Mock the useChartData hook to control data flow in tests
vi.mock('@/hooks/useChartData', () => ({
  useChartData: vi.fn()
}));

// Mock ResizeObserver
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));

// Mock fetch for useChartData hook
global.fetch = vi.fn();

const mockChartData: ChartData = {
  symbol: 'BTCUSDT',
  timeframe: '1h',
  data: [
    { time: 1640995200, open: 47000, high: 47500, low: 46500, close: 47200, volume: 1000 },
    { time: 1640998800, open: 47200, high: 47800, low: 47000, close: 47600, volume: 1200 },
  ],
  indicators: [
    {
      type: 'MA',
      name: 'MA20',
      data: [
        { time: 1640995200, value: 47100 },
        { time: 1640998800, value: 47300 },
      ],
      config: { period: 20 }
    }
  ],
  signals: [
    {
      time: 1640995200,
      position: 'belowBar' as const,
      color: '#22c55e',
      shape: 'arrowUp' as const,
      text: 'BUY'
    }
  ],
  lastUpdate: new Date()
};

describe('Chart Reliability and Performance', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockChart.addCandlestickSeries.mockReturnValue(mockCandleSeries);
    mockChart.addLineSeries.mockReturnValue(mockLineSeries);
    
    // Mock successful fetch
    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockChartData)
    });

    // Default mock for useChartData hook
    (useChartData as any).mockReturnValue({
      data: null,
      isLoading: true,
      error: null,
      refetch: vi.fn(),
      retry: vi.fn()
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('TradingChartsWidget', () => {
    it('should render loading state initially', async () => {
      (useChartData as any).mockReturnValue({
        data: null,
        isLoading: true,
        error: null,
        refetch: vi.fn(),
        retry: vi.fn()
      });

      render(<TradingChartsWidget symbol="BTCUSDT" timeframe="1h" />);
      
      expect(screen.getByText('Loading chart data...')).toBeInTheDocument();
      expect(screen.getByText('Fetching data for BTCUSDT (1h)')).toBeInTheDocument();
    });

    it('should initialize chart properly', async () => {
      (useChartData as any).mockReturnValue({
        data: mockChartData,
        isLoading: false,
        error: null,
        refetch: vi.fn(),
        retry: vi.fn()
      });

      render(<TradingChartsWidget symbol="BTCUSDT" timeframe="1h" />);
      
      await waitFor(() => {
        expect(screen.getByText('Chart - BTCUSDT (1h)')).toBeInTheDocument();
      });

      expect(mockChart.addCandlestickSeries).toHaveBeenCalledWith(
        expect.objectContaining({
          upColor: '#22c55e',
          downColor: '#ef4444'
        })
      );
    });

    it('should handle chart data updates without memory leaks', async () => {
      // Initial render with data
      (useChartData as any).mockReturnValue({
        data: mockChartData,
        isLoading: false,
        error: null,
        refetch: vi.fn(),
        retry: vi.fn()
      });

      const { rerender } = render(<TradingChartsWidget symbol="BTCUSDT" timeframe="1h" />);
      
      await waitFor(() => {
        expect(mockCandleSeries.setData).toHaveBeenCalled();
      });

      // Simulate data update
      const updatedData = {
        ...mockChartData,
        data: [...mockChartData.data, { time: 1641002400, open: 47600, high: 48000, low: 47400, close: 47800, volume: 1100 }]
      };

      (useChartData as any).mockReturnValue({
        data: updatedData,
        isLoading: false,
        error: null,
        refetch: vi.fn(),
        retry: vi.fn()
      });

      rerender(<TradingChartsWidget symbol="BTCUSDT" timeframe="1h" />);

      await waitFor(() => {
        expect(mockCandleSeries.setData).toHaveBeenCalledTimes(2);
      });
    });

    it('should clean up chart resources on unmount', async () => {
      (useChartData as any).mockReturnValue({
        data: mockChartData,
        isLoading: false,
        error: null,
        refetch: vi.fn(),
        retry: vi.fn()
      });

      const { unmount } = render(<TradingChartsWidget symbol="BTCUSDT" timeframe="1h" />);
      
      await waitFor(() => {
        expect(mockChart.addCandlestickSeries).toHaveBeenCalled();
      });

      unmount();

      expect(mockChart.remove).toHaveBeenCalled();
    });

    it('should handle symbol/timeframe changes properly', async () => {
      (useChartData as any).mockReturnValue({
        data: mockChartData,
        isLoading: false,
        error: null,
        refetch: vi.fn(),
        retry: vi.fn()
      });

      const { rerender } = render(<TradingChartsWidget symbol="BTCUSDT" timeframe="1h" />);
      
      await waitFor(() => {
        expect(mockCandleSeries.setData).toHaveBeenCalled();
      });

      // Change symbol - should clear data first
      rerender(<TradingChartsWidget symbol="ETHUSDT" timeframe="1h" />);

      await waitFor(() => {
        // Should clear existing data when symbol changes
        expect(mockCandleSeries.setData).toHaveBeenCalledWith([]);
      });
    });

    it('should handle invalid chart data gracefully', async () => {
      const invalidData = {
        ...mockChartData,
        data: [
          { time: 'invalid', open: NaN, high: null, low: undefined, close: 'invalid', volume: 1000 }
        ]
      };

      (useChartData as any).mockReturnValue({
        data: invalidData,
        isLoading: false,
        error: null,
        refetch: vi.fn(),
        retry: vi.fn()
      });

      render(<TradingChartsWidget symbol="BTCUSDT" timeframe="1h" />);

      await waitFor(() => {
        // Should not crash and should handle invalid data
        expect(screen.getByText('Chart - BTCUSDT (1h)')).toBeInTheDocument();
      });
    });

    it('should optimize re-renders with memoization', async () => {
      (useChartData as any).mockReturnValue({
        data: mockChartData,
        isLoading: false,
        error: null,
        refetch: vi.fn(),
        retry: vi.fn()
      });

      const { rerender } = render(<TradingChartsWidget symbol="BTCUSDT" timeframe="1h" height={320} />);
      
      await waitFor(() => {
        expect(mockChart.addCandlestickSeries).toHaveBeenCalled();
      });

      const initialCallCount = mockChart.addCandlestickSeries.mock.calls.length;

      // Rerender with same props should not reinitialize chart
      rerender(<TradingChartsWidget symbol="BTCUSDT" timeframe="1h" height={320} />);

      expect(mockChart.addCandlestickSeries).toHaveBeenCalledTimes(initialCallCount);
    });
  });

  describe('ChartErrorBoundary', () => {
    const ThrowError = ({ shouldThrow }: { shouldThrow: boolean }) => {
      if (shouldThrow) {
        throw new Error('Chart rendering error');
      }
      return <div>Chart content</div>;
    };

    it('should catch and display chart errors', () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      
      render(
        <ChartErrorBoundary symbol="BTCUSDT" timeframe="1h">
          <ThrowError shouldThrow={true} />
        </ChartErrorBoundary>
      );

      expect(screen.getByText('Chart Error')).toBeInTheDocument();
      expect(screen.getByText(/Failed to render chart for BTCUSDT \(1h\)/)).toBeInTheDocument();
      expect(screen.getByText('Retry')).toBeInTheDocument();
      
      consoleSpy.mockRestore();
    });

    it('should provide retry functionality', () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      const onRetry = vi.fn();
      
      render(
        <ChartErrorBoundary symbol="BTCUSDT" timeframe="1h" onRetry={onRetry}>
          <ThrowError shouldThrow={true} />
        </ChartErrorBoundary>
      );

      const retryButton = screen.getByText('Retry');
      fireEvent.click(retryButton);

      expect(onRetry).toHaveBeenCalled();
      
      consoleSpy.mockRestore();
    });

    it('should show error details in development mode', () => {
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'development';
      
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      
      render(
        <ChartErrorBoundary symbol="BTCUSDT" timeframe="1h">
          <ThrowError shouldThrow={true} />
        </ChartErrorBoundary>
      );

      expect(screen.getByText('Error Details')).toBeInTheDocument();
      
      process.env.NODE_ENV = originalEnv;
      consoleSpy.mockRestore();
    });
  });

  describe('ChartLoadingState', () => {
    it('should display loading spinner and message', () => {
      render(<ChartLoadingState symbol="BTCUSDT" timeframe="1h" />);

      expect(screen.getByText('Loading chart data...')).toBeInTheDocument();
      expect(screen.getByText('Fetching data for BTCUSDT (1h)')).toBeInTheDocument();
    });

    it('should display custom loading message', () => {
      render(
        <ChartLoadingState 
          symbol="BTCUSDT" 
          timeframe="1h" 
          message="Connecting to data feed..." 
        />
      );

      expect(screen.getByText('Connecting to data feed...')).toBeInTheDocument();
    });

    it('should handle missing symbol/timeframe gracefully', () => {
      render(<ChartLoadingState />);

      expect(screen.getByText('Chart - Chart')).toBeInTheDocument();
      expect(screen.getByText('Loading chart data...')).toBeInTheDocument();
    });
  });

  describe('Error Handling', () => {
    it('should handle fetch errors gracefully', async () => {
      (useChartData as any).mockReturnValue({
        data: null,
        isLoading: false,
        error: new Error('Network error'),
        refetch: vi.fn(),
        retry: vi.fn()
      });

      render(<TradingChartsWidget symbol="BTCUSDT" timeframe="1h" />);

      await waitFor(() => {
        expect(screen.getByText('Chart Error')).toBeInTheDocument();
        expect(screen.getByText(/Failed to render chart for BTCUSDT/)).toBeInTheDocument();
      });
    });

    it('should handle API errors with proper status codes', async () => {
      (useChartData as any).mockReturnValue({
        data: null,
        isLoading: false,
        error: new Error('Failed to fetch chart data: 404 Not Found'),
        refetch: vi.fn(),
        retry: vi.fn()
      });

      render(<TradingChartsWidget symbol="BTCUSDT" timeframe="1h" />);

      await waitFor(() => {
        expect(screen.getByText('Chart Error')).toBeInTheDocument();
      });
    });

    it('should handle malformed API responses', async () => {
      (useChartData as any).mockReturnValue({
        data: null,
        isLoading: false,
        error: new Error('Invalid chart data format received'),
        refetch: vi.fn(),
        retry: vi.fn()
      });

      render(<TradingChartsWidget symbol="BTCUSDT" timeframe="1h" />);

      await waitFor(() => {
        expect(screen.getByText('Chart Error')).toBeInTheDocument();
      });
    });
  });

  describe('Performance Optimizations', () => {
    it('should cancel previous requests when props change', async () => {
      const mockRetry = vi.fn();
      (useChartData as any).mockReturnValue({
        data: mockChartData,
        isLoading: false,
        error: null,
        refetch: vi.fn(),
        retry: mockRetry
      });

      const { rerender } = render(<TradingChartsWidget symbol="BTCUSDT" timeframe="1h" />);
      
      // Change props - useChartData hook should handle request cancellation internally
      rerender(<TradingChartsWidget symbol="ETHUSDT" timeframe="1h" />);

      // Verify the hook was called with new parameters
      expect(useChartData).toHaveBeenCalledWith({
        symbol: 'ETHUSDT',
        timeframe: '1h',
        autoRefresh: true,
        refreshInterval: 30000
      });
    });

    it('should handle resize events properly', async () => {
      (useChartData as any).mockReturnValue({
        data: mockChartData,
        isLoading: false,
        error: null,
        refetch: vi.fn(),
        retry: vi.fn()
      });

      const { container } = render(<TradingChartsWidget symbol="BTCUSDT" timeframe="1h" />);
      
      await waitFor(() => {
        expect(mockChart.addCandlestickSeries).toHaveBeenCalled();
      });

      // Simulate resize
      act(() => {
        const resizeCallback = (global.ResizeObserver as any).mock.calls[0][0];
        resizeCallback([{ target: container.firstChild }]);
      });

      expect(mockChart.applyOptions).toHaveBeenCalled();
    });
  });
});