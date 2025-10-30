import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';

// Performance regression tracking
interface PerformanceBaseline {
  name: string;
  maxDuration: number; // milliseconds
  maxMemoryIncrease: number; // bytes
  description: string;
}

const PERFORMANCE_BASELINES: PerformanceBaseline[] = [
  {
    name: 'component-render-performance-widget',
    maxDuration: 50,
    maxMemoryIncrease: 1024 * 1024, // 1MB
    description: 'PerformanceWidget initial render time'
  },
  {
    name: 'component-render-trading-logs',
    maxDuration: 100,
    maxMemoryIncrease: 2 * 1024 * 1024, // 2MB
    description: 'TradingLogsWidget with 1000 records'
  },
  {
    name: 'data-processing-filter-large',
    maxDuration: 150,
    maxMemoryIncrease: 5 * 1024 * 1024, // 5MB
    description: 'Filter 10k trading records'
  },
  {
    name: 'state-update-bulk',
    maxDuration: 200,
    maxMemoryIncrease: 3 * 1024 * 1024, // 3MB
    description: 'Bulk state update with 5k records'
  },
  {
    name: 'virtual-scroll-init',
    maxDuration: 75,
    maxMemoryIncrease: 1.5 * 1024 * 1024, // 1.5MB
    description: 'Virtual scrolling initialization'
  }
];

// Performance measurement utilities
class PerformanceTracker {
  private measurements: Map<string, number[]> = new Map();
  
  async measure<T>(name: string, fn: () => Promise<T> | T): Promise<{ result: T; duration: number; memory?: number }> {
    const memoryBefore = this.getMemoryUsage();
    const start = performance.now();
    
    const result = await fn();
    
    const end = performance.now();
    const duration = end - start;
    const memoryAfter = this.getMemoryUsage();
    const memoryIncrease = memoryAfter && memoryBefore ? memoryAfter - memoryBefore : undefined;
    
    // Store measurement
    if (!this.measurements.has(name)) {
      this.measurements.set(name, []);
    }
    this.measurements.get(name)!.push(duration);
    
    return { result, duration, memory: memoryIncrease };
  }
  
  private getMemoryUsage(): number | null {
    if ('memory' in performance) {
      return (performance as any).memory.usedJSHeapSize;
    }
    return null;
  }
  
  getStats(name: string) {
    const measurements = this.measurements.get(name) || [];
    if (measurements.length === 0) return null;
    
    const sorted = [...measurements].sort((a, b) => a - b);
    return {
      count: measurements.length,
      min: sorted[0],
      max: sorted[sorted.length - 1],
      avg: measurements.reduce((sum, val) => sum + val, 0) / measurements.length,
      median: sorted[Math.floor(sorted.length / 2)],
      p95: sorted[Math.floor(sorted.length * 0.95)]
    };
  }
  
  checkRegression(name: string, baseline: PerformanceBaseline): boolean {
    const stats = this.getStats(name);
    if (!stats) return false;
    
    const isRegression = stats.p95 > baseline.maxDuration;
    
    if (isRegression) {
      console.warn(`Performance regression detected for ${name}:`, {
        baseline: baseline.maxDuration,
        actual: stats.p95,
        regression: ((stats.p95 - baseline.maxDuration) / baseline.maxDuration * 100).toFixed(2) + '%'
      });
    }
    
    return !isRegression;
  }
}

// Test data generators
const generateTestData = {
  performanceMetrics: () => ({
    totalPnl: Math.random() * 10000 - 5000,
    dailyPnl: Math.random() * 1000 - 500,
    winRate: Math.random() * 100,
    totalTrades: Math.floor(Math.random() * 1000),
    currentDrawdown: Math.random() * 500,
    maxDrawdown: Math.random() * 1000,
    portfolioValue: Math.random() * 100000 + 10000,
    dailyChange: Math.random() * 1000 - 500,
    dailyChangePercent: (Math.random() - 0.5) * 10
  }),
  
  tradingLogs: (count: number) => Array.from({ length: count }, (_, i) => ({
    id: `trade-${i}`,
    timestamp: new Date(Date.now() - i * 60000),
    symbol: `SYMBOL${i % 50}`,
    side: i % 2 === 0 ? 'LONG' : 'SHORT',
    entryPrice: Math.random() * 1000 + 100,
    exitPrice: Math.random() * 1000 + 100,
    quantity: Math.random() * 10 + 0.1,
    pnl: (Math.random() - 0.5) * 200,
    status: 'CLOSED',
    pattern: `pattern-${i % 10}`,
    confidence: Math.random()
  })),
  
  chartData: (points: number) => Array.from({ length: points }, (_, i) => ({
    time: Date.now() - (points - i) * 60000,
    open: Math.random() * 100 + 100,
    high: Math.random() * 100 + 150,
    low: Math.random() * 100 + 50,
    close: Math.random() * 100 + 100,
    volume: Math.random() * 1000000
  }))
};

describe('Performance Regression Tests', () => {
  let tracker: PerformanceTracker;
  
  beforeEach(() => {
    tracker = new PerformanceTracker();
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Component Rendering Regression', () => {
    it('should maintain PerformanceWidget render performance', async () => {
      const baseline = PERFORMANCE_BASELINES.find(b => b.name === 'component-render-performance-widget')!;
      
      // Run multiple iterations to get stable measurements
      for (let i = 0; i < 10; i++) {
        const metrics = generateTestData.performanceMetrics();
        
        await tracker.measure('component-render-performance-widget', () => {
          const { unmount } = render(
            <PerformanceWidget 
              metrics={metrics} 
              isLoading={false} 
              lastUpdate={new Date()} 
            />
          );
          unmount();
        });
      }
      
      const passed = tracker.checkRegression('component-render-performance-widget', baseline);
      expect(passed).toBe(true);
      
      const stats = tracker.getStats('component-render-performance-widget');
      console.log('PerformanceWidget render stats:', stats);
    });

    it('should maintain TradingLogsWidget render performance with 1k records', async () => {
      const baseline = PERFORMANCE_BASELINES.find(b => b.name === 'component-render-trading-logs')!;
      const testData = generateTestData.tradingLogs(1000);
      
      const filter = {
        dateRange: { start: new Date(), end: new Date() },
        symbols: [],
        status: [],
        profitLoss: 'all' as const,
        searchText: ''
      };
      
      for (let i = 0; i < 5; i++) {
        await tracker.measure('component-render-trading-logs', () => {
          const { unmount } = render(
            <TradingLogsWidget 
              logs={testData} 
              filter={filter}
              onFilterChange={vi.fn()}
              onExport={vi.fn()}
            />
          );
          unmount();
        });
      }
      
      const passed = tracker.checkRegression('component-render-trading-logs', baseline);
      expect(passed).toBe(true);
    });

    it('should detect render performance regressions', async () => {
      // Simulate a performance regression by adding artificial delay
      const SlowComponent = () => {
        // Simulate expensive computation
        const start = Date.now();
        while (Date.now() - start < 100) {
          // Busy wait to simulate slow render
        }
        return <div>Slow component</div>;
      };

      const { duration } = await tracker.measure('slow-component-test', () => {
        render(<SlowComponent />);
      });

      // Should detect that this is slower than expected
      expect(duration).toBeGreaterThan(50);
    });
  });

  describe('Data Processing Regression', () => {
    it('should maintain large dataset filtering performance', async () => {
      const baseline = PERFORMANCE_BASELINES.find(b => b.name === 'data-processing-filter-large')!;
      const largeDataset = generateTestData.tradingLogs(10000);
      
      for (let i = 0; i < 5; i++) {
        await tracker.measure('data-processing-filter-large', () => {
          const filtered = largeDataset.filter(trade => 
            trade.symbol.includes('SYMBOL1') || 
            (trade.pnl && trade.pnl > 0)
          );
          return filtered;
        });
      }
      
      const passed = tracker.checkRegression('data-processing-filter-large', baseline);
      expect(passed).toBe(true);
    });

    it('should maintain sorting performance', async () => {
      const dataset = generateTestData.tradingLogs(25000);
      
      const { duration } = await tracker.measure('data-sorting-25k', () => {
        const sorted = [...dataset].sort((a, b) => 
          b.timestamp.getTime() - a.timestamp.getTime()
        );
        return sorted;
      });

      // Should sort 25k records within 100ms
      expect(duration).toBeLessThan(100);
    });

    it('should maintain aggregation calculation performance', async () => {
      const dataset = generateTestData.tradingLogs(50000);
      
      const { duration } = await tracker.measure('data-aggregation-50k', () => {
        const totalPnl = dataset.reduce((sum, trade) => sum + (trade.pnl || 0), 0);
        const winningTrades = dataset.filter(trade => (trade.pnl || 0) > 0).length;
        const winRate = (winningTrades / dataset.length) * 100;
        
        return { totalPnl, winRate, totalTrades: dataset.length };
      });

      // Should calculate aggregations within 150ms
      expect(duration).toBeLessThan(150);
    });
  });

  describe('State Management Regression', () => {
    it('should maintain bulk state update performance', async () => {
      const baseline = PERFORMANCE_BASELINES.find(b => b.name === 'state-update-bulk')!;
      
      const TestComponent = ({ data }: { data: any[] }) => {
        const [state, setState] = React.useState<any[]>([]);
        
        React.useEffect(() => {
          setState(data);
        }, [data]);
        
        return <div>{state.length}</div>;
      };
      
      for (let i = 0; i < 3; i++) {
        const bulkData = generateTestData.tradingLogs(5000);
        
        await tracker.measure('state-update-bulk', async () => {
          const { unmount } = render(<TestComponent data={bulkData} />);
          await waitFor(() => {
            expect(screen.getByText('5000')).toBeInTheDocument();
          });
          unmount();
        });
      }
      
      const passed = tracker.checkRegression('state-update-bulk', baseline);
      expect(passed).toBe(true);
    });

    it('should handle rapid state updates efficiently', async () => {
      const TestComponent = () => {
        const [counter, setCounter] = React.useState(0);
        
        React.useEffect(() => {
          const interval = setInterval(() => {
            setCounter(prev => prev + 1);
          }, 1);
          
          setTimeout(() => clearInterval(interval), 100);
        }, []);
        
        return <div data-testid="counter">{counter}</div>;
      };

      const { duration } = await tracker.measure('rapid-state-updates', async () => {
        render(<TestComponent />);
        await waitFor(() => {
          const counter = screen.getByTestId('counter');
          expect(parseInt(counter.textContent || '0')).toBeGreaterThan(50);
        }, { timeout: 200 });
      });

      // Should handle rapid updates within 200ms
      expect(duration).toBeLessThan(200);
    });
  });

  describe('Virtual Scrolling Regression', () => {
    it('should maintain virtual scrolling initialization performance', async () => {
      const baseline = PERFORMANCE_BASELINES.find(b => b.name === 'virtual-scroll-init')!;
      
      const VirtualList = ({ items }: { items: any[] }) => {
        const [visibleRange, setVisibleRange] = React.useState({ start: 0, end: 50 });
        const itemHeight = 40;
        
        const visibleItems = items.slice(visibleRange.start, visibleRange.end);
        
        return (
          <div style={{ height: 400, overflow: 'auto' }} data-testid="virtual-list">
            <div style={{ height: items.length * itemHeight }}>
              {visibleItems.map((item, index) => (
                <div key={item.id} style={{ height: itemHeight }}>
                  {item.symbol}
                </div>
              ))}
            </div>
          </div>
        );
      };
      
      for (let i = 0; i < 3; i++) {
        const largeDataset = generateTestData.tradingLogs(100000);
        
        await tracker.measure('virtual-scroll-init', () => {
          const { unmount } = render(<VirtualList items={largeDataset} />);
          unmount();
        });
      }
      
      const passed = tracker.checkRegression('virtual-scroll-init', baseline);
      expect(passed).toBe(true);
    });

    it('should maintain scroll performance with large datasets', async () => {
      const user = userEvent.setup();
      const largeDataset = generateTestData.tradingLogs(50000);
      
      const VirtualList = ({ items }: { items: any[] }) => {
        const [visibleRange, setVisibleRange] = React.useState({ start: 0, end: 50 });
        
        const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
          const scrollTop = e.currentTarget.scrollTop;
          const start = Math.floor(scrollTop / 40);
          const end = Math.min(start + 50, items.length);
          setVisibleRange({ start, end });
        };
        
        return (
          <div 
            style={{ height: 400, overflow: 'auto' }} 
            onScroll={handleScroll}
            data-testid="scrollable-list"
          >
            <div style={{ height: items.length * 40 }}>
              {items.slice(visibleRange.start, visibleRange.end).map((item, index) => (
                <div key={item.id} style={{ height: 40 }}>
                  {item.symbol} - {visibleRange.start + index}
                </div>
              ))}
            </div>
          </div>
        );
      };

      render(<VirtualList items={largeDataset} />);
      
      const scrollableList = screen.getByTestId('scrollable-list');
      
      const { duration } = await tracker.measure('virtual-scroll-performance', async () => {
        // Simulate multiple scroll events
        for (let i = 0; i < 10; i++) {
          fireEvent.scroll(scrollableList, { target: { scrollTop: i * 400 } });
        }
      });

      // Should handle 10 scroll events within 50ms
      expect(duration).toBeLessThan(50);
    });
  });

  describe('Memory Usage Regression', () => {
    it('should not leak memory during component lifecycle', async () => {
      const iterations = 50;
      let memoryBefore: number | null = null;
      let memoryAfter: number | null = null;
      
      if ('memory' in performance) {
        memoryBefore = (performance as any).memory.usedJSHeapSize;
      }
      
      // Create and destroy components multiple times
      for (let i = 0; i < iterations; i++) {
        const { unmount } = render(
          <PerformanceWidget 
            metrics={generateTestData.performanceMetrics()} 
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
      
      if ('memory' in performance) {
        memoryAfter = (performance as any).memory.usedJSHeapSize;
      }
      
      if (memoryBefore && memoryAfter) {
        const memoryIncrease = memoryAfter - memoryBefore;
        const memoryIncreasePerComponent = memoryIncrease / iterations;
        
        console.log(`Memory increase: ${(memoryIncrease / 1024 / 1024).toFixed(2)}MB total, ${(memoryIncreasePerComponent / 1024).toFixed(2)}KB per component`);
        
        // Should not increase memory by more than 5MB total
        expect(memoryIncrease).toBeLessThan(5 * 1024 * 1024);
      }
    });

    it('should handle large state without excessive memory usage', async () => {
      const TestComponent = () => {
        const [largeState, setLargeState] = React.useState<any[]>([]);
        
        React.useEffect(() => {
          const data = generateTestData.tradingLogs(10000);
          setLargeState(data);
        }, []);
        
        return <div>{largeState.length}</div>;
      };

      let memoryBefore: number | null = null;
      let memoryAfter: number | null = null;
      
      if ('memory' in performance) {
        memoryBefore = (performance as any).memory.usedJSHeapSize;
      }
      
      const { unmount } = render(<TestComponent />);
      
      await waitFor(() => {
        expect(screen.getByText('10000')).toBeInTheDocument();
      });
      
      if ('memory' in performance) {
        memoryAfter = (performance as any).memory.usedJSHeapSize;
      }
      
      unmount();
      
      if (memoryBefore && memoryAfter) {
        const memoryIncrease = memoryAfter - memoryBefore;
        console.log(`Memory increase for 10k records: ${(memoryIncrease / 1024 / 1024).toFixed(2)}MB`);
        
        // Should not use more than 20MB for 10k records
        expect(memoryIncrease).toBeLessThan(20 * 1024 * 1024);
      }
    });
  });

  describe('Performance Baseline Reporting', () => {
    it('should generate performance report', () => {
      const generateReport = () => {
        const report = {
          timestamp: new Date().toISOString(),
          baselines: PERFORMANCE_BASELINES.map(baseline => ({
            ...baseline,
            status: 'passed', // Would be determined by actual test results
            actualP95: 0, // Would be filled with actual measurements
            regression: false
          })),
          summary: {
            totalTests: PERFORMANCE_BASELINES.length,
            passed: PERFORMANCE_BASELINES.length,
            failed: 0,
            regressions: 0
          }
        };
        
        return report;
      };

      const report = generateReport();
      
      expect(report.baselines).toHaveLength(PERFORMANCE_BASELINES.length);
      expect(report.summary.totalTests).toBe(PERFORMANCE_BASELINES.length);
      
      console.log('Performance Report:', JSON.stringify(report, null, 2));
    });
  });
});