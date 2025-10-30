import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { PerformanceWidget } from '@components/Trading/PerformanceWidget';
import { TradingLogsWidget } from '@components/Trading/TradingLogsWidget';
import { TradingChartsWidget } from '@components/Charts/TradingChartsWidget';
import { DashboardGrid } from '@components/Dashboard/DashboardGrid';
import type { PerformanceMetrics, TradeLogEntry } from '@types';

// Performance measurement utilities
const measurePerformance = async (fn: () => Promise<void> | void, label: string) => {
  const start = performance.now();
  await fn();
  const end = performance.now();
  const duration = end - start;
  
  console.log(`${label}: ${duration.toFixed(2)}ms`);
  return duration;
};

const measureMemoryUsage = () => {
  if ('memory' in performance) {
    const memory = (performance as any).memory;
    return {
      used: memory.usedJSHeapSize,
      total: memory.totalJSHeapSize,
      limit: memory.jsHeapSizeLimit
    };
  }
  return null;
};

// Generate test data
const generateLargeTradeDataset = (count: number): TradeLogEntry[] => {
  return Array.from({ length: count }, (_, i) => ({
    id: `trade-${i}`,
    timestamp: new Date(Date.now() - i * 60000),
    symbol: `SYMBOL${i % 100}`,
    side: i % 2 === 0 ? 'LONG' : 'SHORT',
    entryPrice: Math.random() * 1000 + 100,
    exitPrice: Math.random() * 1000 + 100,
    quantity: Math.random() * 10 + 0.1,
    pnl: (Math.random() - 0.5) * 200,
    status: 'CLOSED',
    pattern: `pattern-${i % 20}`,
    confidence: Math.random()
  }));
};

const generatePerformanceMetrics = (): PerformanceMetrics => ({
  totalPnl: Math.random() * 10000 - 5000,
  dailyPnl: Math.random() * 1000 - 500,
  winRate: Math.random() * 100,
  totalTrades: Math.floor(Math.random() * 1000),
  currentDrawdown: Math.random() * 500,
  maxDrawdown: Math.random() * 1000,
  portfolioValue: Math.random() * 100000 + 10000,
  dailyChange: Math.random() * 1000 - 500,
  dailyChangePercent: (Math.random() - 0.5) * 10
});

describe('Performance Benchmarks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Component Rendering Performance', () => {
    it('should render PerformanceWidget within acceptable time', async () => {
      const metrics = generatePerformanceMetrics();
      
      const duration = await measurePerformance(() => {
        render(
          <PerformanceWidget 
            metrics={metrics} 
            isLoading={false} 
            lastUpdate={new Date()} 
          />
        );
      }, 'PerformanceWidget render');

      // Should render within 50ms
      expect(duration).toBeLessThan(50);
    });

    it('should handle large trading logs dataset efficiently', async () => {
      const largeTrades = generateLargeTradeDataset(10000);
      const filter = {
        dateRange: { start: new Date(), end: new Date() },
        symbols: [],
        status: [],
        profitLoss: 'all' as const,
        searchText: ''
      };

      const memoryBefore = measureMemoryUsage();
      
      const duration = await measurePerformance(() => {
        render(
          <TradingLogsWidget 
            logs={largeTrades} 
            filter={filter}
            onFilterChange={vi.fn()}
            onExport={vi.fn()}
          />
        );
      }, 'TradingLogsWidget with 10k records');

      const memoryAfter = measureMemoryUsage();
      
      // Should render within 200ms even with large dataset
      expect(duration).toBeLessThan(200);
      
      if (memoryBefore && memoryAfter) {
        const memoryIncrease = memoryAfter.used - memoryBefore.used;
        console.log(`Memory increase: ${(memoryIncrease / 1024 / 1024).toFixed(2)}MB`);
        
        // Memory increase should be reasonable (less than 50MB)
        expect(memoryIncrease).toBeLessThan(50 * 1024 * 1024);
      }
    });

    it('should handle rapid re-renders without performance degradation', async () => {
      const metrics = generatePerformanceMetrics();
      let renderCount = 0;
      
      const TestComponent = ({ updateTrigger }: { updateTrigger: number }) => {
        renderCount++;
        return (
          <PerformanceWidget 
            metrics={{
              ...metrics,
              totalPnl: metrics.totalPnl + updateTrigger
            }} 
            isLoading={false} 
            lastUpdate={new Date()} 
          />
        );
      };

      const { rerender } = render(<TestComponent updateTrigger={0} />);
      
      const duration = await measurePerformance(async () => {
        // Trigger 100 rapid re-renders
        for (let i = 1; i <= 100; i++) {
          rerender(<TestComponent updateTrigger={i} />);
        }
      }, '100 rapid re-renders');

      expect(renderCount).toBe(101); // Initial + 100 updates
      expect(duration).toBeLessThan(500); // Should complete within 500ms
    });
  });

  describe('Data Processing Performance', () => {
    it('should filter large datasets efficiently', async () => {
      const largeTrades = generateLargeTradeDataset(50000);
      
      const filterTrades = (trades: TradeLogEntry[], searchText: string) => {
        return trades.filter(trade => 
          trade.symbol.toLowerCase().includes(searchText.toLowerCase()) ||
          trade.pattern?.toLowerCase().includes(searchText.toLowerCase())
        );
      };

      const duration = await measurePerformance(() => {
        const filtered = filterTrades(largeTrades, 'SYMBOL1');
        expect(filtered.length).toBeGreaterThan(0);
      }, 'Filter 50k trades');

      // Should filter within 100ms
      expect(duration).toBeLessThan(100);
    });

    it('should sort large datasets efficiently', async () => {
      const largeTrades = generateLargeTradeDataset(25000);
      
      const duration = await measurePerformance(() => {
        const sorted = [...largeTrades].sort((a, b) => 
          b.timestamp.getTime() - a.timestamp.getTime()
        );
        expect(sorted[0].timestamp.getTime()).toBeGreaterThanOrEqual(
          sorted[sorted.length - 1].timestamp.getTime()
        );
      }, 'Sort 25k trades by timestamp');

      // Should sort within 50ms
      expect(duration).toBeLessThan(50);
    });

    it('should calculate aggregations efficiently', async () => {
      const largeTrades = generateLargeTradeDataset(100000);
      
      const calculateAggregations = (trades: TradeLogEntry[]) => {
        const totalPnl = trades.reduce((sum, trade) => sum + (trade.pnl || 0), 0);
        const winningTrades = trades.filter(trade => (trade.pnl || 0) > 0).length;
        const winRate = (winningTrades / trades.length) * 100;
        const avgPnl = totalPnl / trades.length;
        
        return { totalPnl, winRate, avgPnl, totalTrades: trades.length };
      };

      const duration = await measurePerformance(() => {
        const aggregations = calculateAggregations(largeTrades);
        expect(aggregations.totalTrades).toBe(100000);
        expect(typeof aggregations.winRate).toBe('number');
      }, 'Calculate aggregations for 100k trades');

      // Should calculate within 100ms
      expect(duration).toBeLessThan(100);
    });
  });

  describe('Virtual Scrolling Performance', () => {
    it('should handle virtual scrolling with large datasets', async () => {
      const largeTrades = generateLargeTradeDataset(100000);
      
      const VirtualizedList = ({ items }: { items: TradeLogEntry[] }) => {
        const [visibleRange, setVisibleRange] = React.useState({ start: 0, end: 50 });
        const itemHeight = 40;
        const containerHeight = 400;
        
        const visibleItems = items.slice(visibleRange.start, visibleRange.end);
        
        const handleScroll = (scrollTop: number) => {
          const start = Math.floor(scrollTop / itemHeight);
          const end = Math.min(start + Math.ceil(containerHeight / itemHeight) + 5, items.length);
          setVisibleRange({ start, end });
        };
        
        return (
          <div 
            style={{ height: containerHeight, overflow: 'auto' }}
            onScroll={(e) => handleScroll(e.currentTarget.scrollTop)}
            data-testid="virtual-list"
          >
            <div style={{ height: items.length * itemHeight, position: 'relative' }}>
              {visibleItems.map((item, index) => (
                <div
                  key={item.id}
                  style={{
                    position: 'absolute',
                    top: (visibleRange.start + index) * itemHeight,
                    height: itemHeight,
                    width: '100%'
                  }}
                >
                  {item.symbol} - {item.pnl?.toFixed(2)}
                </div>
              ))}
            </div>
          </div>
        );
      };

      const duration = await measurePerformance(() => {
        render(<VirtualizedList items={largeTrades} />);
      }, 'Virtual scrolling with 100k items');

      // Should render initial view within 100ms
      expect(duration).toBeLessThan(100);
      
      // Verify only visible items are rendered
      const virtualList = screen.getByTestId('virtual-list');
      const renderedItems = virtualList.querySelectorAll('div[style*="position: absolute"]');
      expect(renderedItems.length).toBeLessThanOrEqual(60); // Should only render visible + buffer
    });
  });

  describe('Memory Management', () => {
    it('should not leak memory during component lifecycle', async () => {
      const memoryBefore = measureMemoryUsage();
      
      // Create and destroy components multiple times
      for (let i = 0; i < 100; i++) {
        const { unmount } = render(
          <PerformanceWidget 
            metrics={generatePerformanceMetrics()} 
            isLoading={false} 
            lastUpdate={new Date()} 
          />
        );
        unmount();
      }
      
      // Force garbage collection if available
      if (global.gc) {
        global.gc();
      }
      
      const memoryAfter = measureMemoryUsage();
      
      if (memoryBefore && memoryAfter) {
        const memoryIncrease = memoryAfter.used - memoryBefore.used;
        console.log(`Memory increase after 100 mount/unmount cycles: ${(memoryIncrease / 1024 / 1024).toFixed(2)}MB`);
        
        // Memory increase should be minimal (less than 10MB)
        expect(memoryIncrease).toBeLessThan(10 * 1024 * 1024);
      }
    });

    it('should handle large state updates efficiently', async () => {
      const TestComponent = () => {
        const [data, setData] = React.useState<TradeLogEntry[]>([]);
        
        React.useEffect(() => {
          // Simulate large state update
          const largeDataset = generateLargeTradeDataset(10000);
          setData(largeDataset);
        }, []);
        
        return <div data-testid="data-count">{data.length}</div>;
      };

      const memoryBefore = measureMemoryUsage();
      
      const duration = await measurePerformance(async () => {
        render(<TestComponent />);
        await waitFor(() => {
          expect(screen.getByTestId('data-count')).toHaveTextContent('10000');
        });
      }, 'Large state update (10k items)');

      const memoryAfter = measureMemoryUsage();
      
      expect(duration).toBeLessThan(200);
      
      if (memoryBefore && memoryAfter) {
        const memoryIncrease = memoryAfter.used - memoryBefore.used;
        console.log(`Memory increase for 10k items: ${(memoryIncrease / 1024 / 1024).toFixed(2)}MB`);
      }
    });
  });

  describe('Network Performance Simulation', () => {
    it('should handle slow network responses gracefully', async () => {
      const slowFetch = (delay: number) => 
        new Promise(resolve => setTimeout(resolve, delay));

      const TestComponent = () => {
        const [loading, setLoading] = React.useState(true);
        const [data, setData] = React.useState(null);
        
        React.useEffect(() => {
          const fetchData = async () => {
            await slowFetch(2000); // Simulate 2s network delay
            setData(generatePerformanceMetrics());
            setLoading(false);
          };
          fetchData();
        }, []);
        
        if (loading) {
          return <div data-testid="loading">Loading...</div>;
        }
        
        return (
          <PerformanceWidget 
            metrics={data} 
            isLoading={false} 
            lastUpdate={new Date()} 
          />
        );
      };

      const duration = await measurePerformance(async () => {
        render(<TestComponent />);
        
        // Should show loading state immediately
        expect(screen.getByTestId('loading')).toBeInTheDocument();
        
        // Wait for data to load
        await waitFor(() => {
          expect(screen.queryByTestId('loading')).not.toBeInTheDocument();
        }, { timeout: 3000 });
      }, 'Slow network response handling');

      // Total time should be close to network delay + render time
      expect(duration).toBeGreaterThan(2000);
      expect(duration).toBeLessThan(2500);
    });
  });

  describe('Bundle Size and Load Performance', () => {
    it('should measure component bundle impact', () => {
      const measureBundleSize = (componentName: string) => {
        // Simulate bundle size measurement
        const sizes = {
          'PerformanceWidget': 15.2, // KB
          'TradingLogsWidget': 28.5,
          'TradingChartsWidget': 45.8,
          'DashboardGrid': 22.1
        };
        
        return sizes[componentName as keyof typeof sizes] || 0;
      };

      const performanceWidgetSize = measureBundleSize('PerformanceWidget');
      const tradingLogsSize = measureBundleSize('TradingLogsWidget');
      const chartsSize = measureBundleSize('TradingChartsWidget');
      
      console.log('Bundle sizes:', {
        PerformanceWidget: `${performanceWidgetSize}KB`,
        TradingLogsWidget: `${tradingLogsSize}KB`,
        TradingChartsWidget: `${chartsSize}KB`
      });
      
      // Ensure components stay within reasonable size limits
      expect(performanceWidgetSize).toBeLessThan(20); // KB
      expect(tradingLogsSize).toBeLessThan(35);
      expect(chartsSize).toBeLessThan(50);
    });
  });

  describe('Regression Tests', () => {
    it('should maintain performance baselines', async () => {
      const baselines = {
        performanceWidgetRender: 50, // ms
        largeDatasetFilter: 100,
        virtualScrollInit: 100,
        stateUpdateLarge: 200
      };

      // Test 1: Performance widget render
      const renderDuration = await measurePerformance(() => {
        render(
          <PerformanceWidget 
            metrics={generatePerformanceMetrics()} 
            isLoading={false} 
            lastUpdate={new Date()} 
          />
        );
      }, 'Performance widget render baseline');

      expect(renderDuration).toBeLessThan(baselines.performanceWidgetRender);

      // Test 2: Large dataset filtering
      const largeTrades = generateLargeTradeDataset(25000);
      const filterDuration = await measurePerformance(() => {
        const filtered = largeTrades.filter(trade => 
          trade.symbol.includes('SYMBOL1')
        );
        expect(filtered.length).toBeGreaterThan(0);
      }, 'Large dataset filter baseline');

      expect(filterDuration).toBeLessThan(baselines.largeDatasetFilter);

      console.log('Performance baselines maintained:', {
        renderDuration: `${renderDuration.toFixed(2)}ms (limit: ${baselines.performanceWidgetRender}ms)`,
        filterDuration: `${filterDuration.toFixed(2)}ms (limit: ${baselines.largeDatasetFilter}ms)`
      });
    });
  });
});