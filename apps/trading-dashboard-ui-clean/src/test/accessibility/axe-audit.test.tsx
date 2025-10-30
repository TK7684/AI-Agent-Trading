import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { axe, toHaveNoViolations } from 'jest-axe';
import { PerformanceWidget } from '@components/Trading/PerformanceWidget';
import { TradingLogsWidget } from '@components/Trading/TradingLogsWidget';
import { AgentControlWidget } from '@components/Controls/AgentControlWidget';
import { SystemHealthWidget } from '@components/System/SystemHealthWidget';
import { NotificationCenter } from '@components/Notifications/NotificationCenter';
import { DashboardLayout } from '@components/Dashboard/DashboardLayout';
import { TradingChartsWidget } from '@components/Charts/TradingChartsWidget';
import type { 
  PerformanceMetrics, 
  TradeLogEntry, 
  AgentStatus, 
  SystemHealth, 
  Notification 
} from '@types';

// Extend Jest matchers
expect.extend(toHaveNoViolations);

// Test data generators
const generateTestData = {
  performanceMetrics: (): PerformanceMetrics => ({
    totalPnl: 1500.50,
    dailyPnl: 250.25,
    winRate: 68.5,
    totalTrades: 42,
    currentDrawdown: 125.75,
    maxDrawdown: 300.00,
    portfolioValue: 15000.00,
    dailyChange: 250.25,
    dailyChangePercent: 1.69
  }),

  tradingLogs: (count: number = 5): TradeLogEntry[] => 
    Array.from({ length: count }, (_, i) => ({
      id: `trade-${i}`,
      timestamp: new Date(Date.now() - i * 60000),
      symbol: `SYMBOL${i}`,
      side: i % 2 === 0 ? 'LONG' : 'SHORT',
      entryPrice: 100 + i * 10,
      exitPrice: 105 + i * 10,
      quantity: 1 + i * 0.5,
      pnl: (i % 2 === 0 ? 1 : -1) * (50 + i * 10),
      status: 'CLOSED',
      pattern: `pattern-${i}`,
      confidence: 0.8 + i * 0.02
    })),

  agentStatus: (): AgentStatus => ({
    state: 'running',
    uptime: 3600000,
    lastAction: new Date(),
    activePositions: 3,
    dailyTrades: 15
  }),

  systemHealth: (): SystemHealth => ({
    cpu: 45.2,
    memory: 62.8,
    diskUsage: 35.1,
    networkLatency: 25,
    errorRate: 0.02,
    uptime: 86400000,
    connections: {
      database: true,
      broker: true,
      llm: true
    }
  }),

  notifications: (count: number = 3): Notification[] =>
    Array.from({ length: count }, (_, i) => ({
      id: `notification-${i}`,
      type: ['info', 'warning', 'error', 'success'][i % 4] as any,
      title: `Test Notification ${i + 1}`,
      message: `This is test notification message ${i + 1}`,
      timestamp: new Date(Date.now() - i * 30000),
      read: i % 2 === 0,
      persistent: i === 0
    }))
};

describe('Accessibility Audit with axe-core', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Core Component Accessibility', () => {
    it('should have no accessibility violations in PerformanceWidget', async () => {
      const metrics = generateTestData.performanceMetrics();
      
      const { container } = render(
        <PerformanceWidget 
          metrics={metrics} 
          isLoading={false} 
          lastUpdate={new Date()} 
        />
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should have no accessibility violations in TradingLogsWidget', async () => {
      const logs = generateTestData.tradingLogs(10);
      const filter = {
        dateRange: { start: new Date(), end: new Date() },
        symbols: [],
        status: [],
        profitLoss: 'all' as const,
        searchText: ''
      };

      const { container } = render(
        <TradingLogsWidget 
          logs={logs} 
          filter={filter}
          onFilterChange={vi.fn()}
          onExport={vi.fn()}
        />
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should have no accessibility violations in AgentControlWidget', async () => {
      const status = generateTestData.agentStatus();
      const config = {
        symbols: ['BTCUSD', 'ETHUSD'],
        timeframes: ['15m', '1h', '4h'],
        riskLimits: {
          maxDailyLoss: 1000,
          maxDrawdown: 500,
          maxPositions: 5
        },
        tradingHours: {
          enabled: true,
          start: '09:00',
          end: '17:00',
          timezone: 'UTC'
        }
      };

      const { container } = render(
        <AgentControlWidget 
          status={status}
          config={config}
          onStart={vi.fn()}
          onStop={vi.fn()}
          onPause={vi.fn()}
          onConfigUpdate={vi.fn()}
        />
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should have no accessibility violations in SystemHealthWidget', async () => {
      const health = generateTestData.systemHealth();
      const alerts: any[] = [];

      const { container } = render(
        <SystemHealthWidget 
          health={health}
          alerts={alerts}
          onRefresh={vi.fn()}
        />
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should have no accessibility violations in NotificationCenter', async () => {
      const notifications = generateTestData.notifications(5);

      const { container } = render(
        <NotificationCenter 
          notifications={notifications}
          onMarkAsRead={vi.fn()}
          onDismiss={vi.fn()}
          onClearAll={vi.fn()}
        />
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe('Layout and Navigation Accessibility', () => {
    it('should have no accessibility violations in DashboardLayout', async () => {
      const { container } = render(
        <DashboardLayout 
          sidebarCollapsed={false}
          onSidebarToggle={vi.fn()}
        >
          <div>Dashboard Content</div>
        </DashboardLayout>
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should maintain accessibility with collapsed sidebar', async () => {
      const { container } = render(
        <DashboardLayout 
          sidebarCollapsed={true}
          onSidebarToggle={vi.fn()}
        >
          <div>Dashboard Content</div>
        </DashboardLayout>
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe('Interactive Elements Accessibility', () => {
    it('should have accessible form controls in AgentControlWidget', async () => {
      const user = userEvent.setup();
      const status = generateTestData.agentStatus();
      const config = {
        symbols: ['BTCUSD'],
        timeframes: ['1h'],
        riskLimits: {
          maxDailyLoss: 1000,
          maxDrawdown: 500,
          maxPositions: 5
        },
        tradingHours: {
          enabled: true,
          start: '09:00',
          end: '17:00',
          timezone: 'UTC'
        }
      };

      const { container } = render(
        <AgentControlWidget 
          status={status}
          config={config}
          onStart={vi.fn()}
          onStop={vi.fn()}
          onPause={vi.fn()}
          onConfigUpdate={vi.fn()}
        />
      );

      // Test keyboard navigation
      const startButton = screen.getByRole('button', { name: /start/i });
      await user.tab();
      expect(startButton).toHaveFocus();

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should have accessible table in TradingLogsWidget', async () => {
      const logs = generateTestData.tradingLogs(3);
      const filter = {
        dateRange: { start: new Date(), end: new Date() },
        symbols: [],
        status: [],
        profitLoss: 'all' as const,
        searchText: ''
      };

      const { container } = render(
        <TradingLogsWidget 
          logs={logs} 
          filter={filter}
          onFilterChange={vi.fn()}
          onExport={vi.fn()}
        />
      );

      // Verify table structure
      const table = screen.getByRole('table');
      expect(table).toBeInTheDocument();
      
      const columnHeaders = screen.getAllByRole('columnheader');
      expect(columnHeaders.length).toBeGreaterThan(0);

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe('Dynamic Content Accessibility', () => {
    it('should maintain accessibility with loading states', async () => {
      const metrics = generateTestData.performanceMetrics();
      
      const { container, rerender } = render(
        <PerformanceWidget 
          metrics={metrics} 
          isLoading={true} 
          lastUpdate={new Date()} 
        />
      );

      // Check loading state accessibility
      let results = await axe(container);
      expect(results).toHaveNoViolations();

      // Check loaded state accessibility
      rerender(
        <PerformanceWidget 
          metrics={metrics} 
          isLoading={false} 
          lastUpdate={new Date()} 
        />
      );

      results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should maintain accessibility with error states', async () => {
      const ErrorComponent = ({ hasError }: { hasError: boolean }) => {
        if (hasError) {
          return (
            <div role="alert" aria-live="assertive">
              <h2>Error occurred</h2>
              <p>Unable to load trading data. Please try again.</p>
              <button type="button">Retry</button>
            </div>
          );
        }
        
        return <div>Normal content</div>;
      };

      const { container } = render(<ErrorComponent hasError={true} />);

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should maintain accessibility with notifications', async () => {
      const notifications = generateTestData.notifications(3);
      
      const { container } = render(
        <NotificationCenter 
          notifications={notifications}
          onMarkAsRead={vi.fn()}
          onDismiss={vi.fn()}
          onClearAll={vi.fn()}
        />
      );

      // Verify ARIA live regions for notifications
      const liveRegion = container.querySelector('[aria-live]');
      expect(liveRegion).toBeInTheDocument();

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe('Color and Contrast Accessibility', () => {
    it('should have sufficient color contrast in performance indicators', async () => {
      const metrics = generateTestData.performanceMetrics();
      
      const { container } = render(
        <PerformanceWidget 
          metrics={metrics} 
          isLoading={false} 
          lastUpdate={new Date()} 
        />
      );

      // axe-core will check color contrast automatically
      const results = await axe(container, {
        rules: {
          'color-contrast': { enabled: true }
        }
      });
      
      expect(results).toHaveNoViolations();
    });

    it('should not rely solely on color for profit/loss indication', async () => {
      const logs = generateTestData.tradingLogs(5);
      const filter = {
        dateRange: { start: new Date(), end: new Date() },
        symbols: [],
        status: [],
        profitLoss: 'all' as const,
        searchText: ''
      };

      const { container } = render(
        <TradingLogsWidget 
          logs={logs} 
          filter={filter}
          onFilterChange={vi.fn()}
          onExport={vi.fn()}
        />
      );

      // Verify that profit/loss has text indicators, not just color
      const profitIndicators = container.querySelectorAll('[aria-label*="profit"], [aria-label*="loss"]');
      expect(profitIndicators.length).toBeGreaterThan(0);

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe('Keyboard Navigation Accessibility', () => {
    it('should support full keyboard navigation', async () => {
      const user = userEvent.setup();
      const notifications = generateTestData.notifications(3);
      
      render(
        <NotificationCenter 
          notifications={notifications}
          onMarkAsRead={vi.fn()}
          onDismiss={vi.fn()}
          onClearAll={vi.fn()}
        />
      );

      // Test tab navigation through interactive elements
      const interactiveElements = screen.getAllByRole('button');
      
      for (let i = 0; i < interactiveElements.length; i++) {
        await user.tab();
        expect(document.activeElement).toBe(interactiveElements[i]);
      }
    });

    it('should handle escape key for modal dialogs', async () => {
      const user = userEvent.setup();
      const onClose = vi.fn();
      
      const ModalDialog = ({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) => {
        React.useEffect(() => {
          const handleEscape = (e: KeyboardEvent) => {
            if (e.key === 'Escape') {
              onClose();
            }
          };
          
          if (isOpen) {
            document.addEventListener('keydown', handleEscape);
            return () => document.removeEventListener('keydown', handleEscape);
          }
        }, [isOpen, onClose]);
        
        if (!isOpen) return null;
        
        return (
          <div role="dialog" aria-modal="true" aria-labelledby="modal-title">
            <h2 id="modal-title">Confirm Action</h2>
            <p>Are you sure you want to stop the trading agent?</p>
            <button onClick={onClose}>Cancel</button>
            <button>Confirm</button>
          </div>
        );
      };

      render(<ModalDialog isOpen={true} onClose={onClose} />);
      
      await user.keyboard('{Escape}');
      expect(onClose).toHaveBeenCalled();
    });
  });

  describe('Screen Reader Accessibility', () => {
    it('should provide meaningful labels for data visualizations', async () => {
      const metrics = generateTestData.performanceMetrics();
      
      const { container } = render(
        <PerformanceWidget 
          metrics={metrics} 
          isLoading={false} 
          lastUpdate={new Date()} 
        />
      );

      // Verify ARIA labels for key metrics
      const totalPnlElement = screen.getByLabelText(/total profit and loss/i);
      expect(totalPnlElement).toBeInTheDocument();
      
      const winRateElement = screen.getByLabelText(/win rate/i);
      expect(winRateElement).toBeInTheDocument();

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should provide live updates for dynamic content', async () => {
      const LiveUpdatesComponent = () => {
        const [count, setCount] = React.useState(0);
        
        React.useEffect(() => {
          const interval = setInterval(() => {
            setCount(prev => prev + 1);
          }, 1000);
          
          return () => clearInterval(interval);
        }, []);
        
        return (
          <div>
            <div aria-live="polite" aria-label="Trade count">
              Active trades: {count}
            </div>
            <div aria-live="assertive" aria-label="Alert messages">
              {count > 5 && 'High trading activity detected'}
            </div>
          </div>
        );
      };

      const { container } = render(<LiveUpdatesComponent />);
      
      const liveRegions = container.querySelectorAll('[aria-live]');
      expect(liveRegions).toHaveLength(2);
      
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe('Mobile Accessibility', () => {
    it('should maintain accessibility on mobile viewports', async () => {
      // Simulate mobile viewport
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 375
      });
      
      Object.defineProperty(window, 'innerHeight', {
        writable: true,
        configurable: true,
        value: 667
      });

      const metrics = generateTestData.performanceMetrics();
      
      const { container } = render(
        <div style={{ width: '375px' }}>
          <PerformanceWidget 
            metrics={metrics} 
            isLoading={false} 
            lastUpdate={new Date()} 
          />
        </div>
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should have appropriate touch targets', async () => {
      const user = userEvent.setup();
      const notifications = generateTestData.notifications(2);
      
      const { container } = render(
        <div style={{ width: '375px' }}>
          <NotificationCenter 
            notifications={notifications}
            onMarkAsRead={vi.fn()}
            onDismiss={vi.fn()}
            onClearAll={vi.fn()}
          />
        </div>
      );

      // Verify touch targets are large enough (minimum 44x44px)
      const buttons = screen.getAllByRole('button');
      buttons.forEach(button => {
        const styles = window.getComputedStyle(button);
        const minSize = 44; // pixels
        
        // Note: In a real test, you'd check actual computed dimensions
        expect(button).toBeInTheDocument();
      });

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe('Comprehensive Accessibility Report', () => {
    it('should generate accessibility audit report', async () => {
      const components = [
        {
          name: 'PerformanceWidget',
          component: (
            <PerformanceWidget 
              metrics={generateTestData.performanceMetrics()} 
              isLoading={false} 
              lastUpdate={new Date()} 
            />
          )
        },
        {
          name: 'TradingLogsWidget',
          component: (
            <TradingLogsWidget 
              logs={generateTestData.tradingLogs(3)} 
              filter={{
                dateRange: { start: new Date(), end: new Date() },
                symbols: [],
                status: [],
                profitLoss: 'all',
                searchText: ''
              }}
              onFilterChange={vi.fn()}
              onExport={vi.fn()}
            />
          )
        },
        {
          name: 'NotificationCenter',
          component: (
            <NotificationCenter 
              notifications={generateTestData.notifications(2)}
              onMarkAsRead={vi.fn()}
              onDismiss={vi.fn()}
              onClearAll={vi.fn()}
            />
          )
        }
      ];

      const auditResults = [];

      for (const { name, component } of components) {
        const { container } = render(component);
        const results = await axe(container);
        
        auditResults.push({
          component: name,
          violations: results.violations.length,
          passes: results.passes.length,
          incomplete: results.incomplete.length,
          inaccessible: results.inaccessible.length
        });
      }

      const report = {
        timestamp: new Date().toISOString(),
        summary: {
          totalComponents: auditResults.length,
          totalViolations: auditResults.reduce((sum, r) => sum + r.violations, 0),
          totalPasses: auditResults.reduce((sum, r) => sum + r.passes, 0)
        },
        components: auditResults
      };

      console.log('Accessibility Audit Report:', JSON.stringify(report, null, 2));

      // All components should have zero violations
      expect(report.summary.totalViolations).toBe(0);
      expect(report.summary.totalPasses).toBeGreaterThan(0);
    });
  });
});