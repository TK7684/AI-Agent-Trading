import React from 'react';
import { render, screen } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { TradingChartsWidget } from '@components/Charts/TradingChartsWidget';
import { ChartErrorBoundary } from '@components/Charts/ChartErrorBoundary';
import { ChartLoadingState } from '@components/Charts/ChartLoadingState';

// Mock lightweight-charts
vi.mock('lightweight-charts', () => ({
  createChart: vi.fn(() => ({
    addCandlestickSeries: vi.fn(() => ({
      setData: vi.fn(),
      setMarkers: vi.fn()
    })),
    addLineSeries: vi.fn(() => ({
      setData: vi.fn()
    })),
    removeSeries: vi.fn(),
    remove: vi.fn(),
    timeScale: vi.fn(() => ({
      fitContent: vi.fn()
    })),
    applyOptions: vi.fn()
  }))
}));

// Mock useChartData hook
vi.mock('@/hooks/useChartData', () => ({
  useChartData: vi.fn(() => ({
    data: null,
    isLoading: true,
    error: null,
    refetch: vi.fn(),
    retry: vi.fn()
  }))
}));

// Mock ResizeObserver
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));

describe('Chart Integration Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('ChartLoadingState', () => {
    it('should render loading state correctly', () => {
      render(<ChartLoadingState symbol="BTCUSDT" timeframe="1h" />);
      
      expect(screen.getByText('Loading chart data...')).toBeInTheDocument();
      expect(screen.getByText('Chart - BTCUSDT (1h)')).toBeInTheDocument();
    });

    it('should handle missing props gracefully', () => {
      render(<ChartLoadingState />);
      
      expect(screen.getByText('Loading chart data...')).toBeInTheDocument();
      expect(screen.getByText('Chart - Chart')).toBeInTheDocument();
    });
  });

  describe('ChartErrorBoundary', () => {
    const ThrowError = ({ shouldThrow }: { shouldThrow: boolean }) => {
      if (shouldThrow) {
        throw new Error('Test error');
      }
      return <div>Chart content</div>;
    };

    it('should catch errors and display fallback UI', () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      
      render(
        <ChartErrorBoundary symbol="BTCUSDT" timeframe="1h">
          <ThrowError shouldThrow={true} />
        </ChartErrorBoundary>
      );

      expect(screen.getByText('Chart Error')).toBeInTheDocument();
      expect(screen.getByText('Retry')).toBeInTheDocument();
      
      consoleSpy.mockRestore();
    });

    it('should render children when no error occurs', () => {
      render(
        <ChartErrorBoundary symbol="BTCUSDT" timeframe="1h">
          <ThrowError shouldThrow={false} />
        </ChartErrorBoundary>
      );

      expect(screen.getByText('Chart content')).toBeInTheDocument();
    });
  });

  describe('TradingChartsWidget', () => {
    it('should render without crashing', () => {
      render(<TradingChartsWidget symbol="BTCUSDT" timeframe="1h" />);
      
      // Should show loading state initially
      expect(screen.getByText('Loading chart data...')).toBeInTheDocument();
    });

    it('should accept all required props', () => {
      const { container } = render(
        <TradingChartsWidget 
          symbol="ETHUSDT" 
          timeframe="4h" 
          autoRefresh={false}
          refreshInterval={60000}
          height={400}
        />
      );
      
      expect(container.firstChild).toBeInTheDocument();
    });
  });
});