import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type { PerformanceMetrics, TradeLogEntry, AgentStatus } from '@/types';

interface TradingState {
  // Performance metrics
  performanceMetrics: PerformanceMetrics | null;
  
  // Trading logs
  tradingLogs: TradeLogEntry[];
  
  // Agent status
  agentStatus: AgentStatus | null;
  
  // Loading states
  isLoadingMetrics: boolean;
  isLoadingLogs: boolean;
  isLoadingStatus: boolean;
  
  // Actions
  setPerformanceMetrics: (metrics: PerformanceMetrics) => void;
  setTradingLogs: (logs: TradeLogEntry[]) => void;
  addTradingLog: (log: TradeLogEntry) => void;
  updateTradingLog: (id: string, updates: Partial<TradeLogEntry>) => void;
  setAgentStatus: (status: AgentStatus) => void;
  setLoadingMetrics: (loading: boolean) => void;
  setLoadingLogs: (loading: boolean) => void;
  setLoadingStatus: (loading: boolean) => void;
  
  // Computed values
  getTotalPnL: () => number;
  getWinRate: () => number;
  getActivePositions: () => TradeLogEntry[];
}

export const useTradingStore = create<TradingState>()(
  devtools(
    (set, get) => ({
      // Initial state
      performanceMetrics: null,
      tradingLogs: [],
      agentStatus: null,
      isLoadingMetrics: false,
      isLoadingLogs: false,
      isLoadingStatus: false,
      
      // Actions
      setPerformanceMetrics: (metrics) =>
        set({ performanceMetrics: metrics }, false, 'setPerformanceMetrics'),
      
      setTradingLogs: (logs) =>
        set({ tradingLogs: logs }, false, 'setTradingLogs'),
      
      addTradingLog: (log) =>
        set(
          (state) => ({ tradingLogs: [log, ...state.tradingLogs] }),
          false,
          'addTradingLog'
        ),
      
      updateTradingLog: (id, updates) =>
        set(
          (state) => ({
            tradingLogs: state.tradingLogs.map((log) =>
              log.id === id ? { ...log, ...updates } : log
            ),
          }),
          false,
          'updateTradingLog'
        ),
      
      setAgentStatus: (status) =>
        set({ agentStatus: status }, false, 'setAgentStatus'),
      
      setLoadingMetrics: (loading) =>
        set({ isLoadingMetrics: loading }, false, 'setLoadingMetrics'),
      
      setLoadingLogs: (loading) =>
        set({ isLoadingLogs: loading }, false, 'setLoadingLogs'),
      
      setLoadingStatus: (loading) =>
        set({ isLoadingStatus: loading }, false, 'setLoadingStatus'),
      
      // Computed values
      getTotalPnL: () => {
        const { tradingLogs } = get();
        return tradingLogs
          .filter((log) => log.status === 'CLOSED' && log.pnl !== undefined)
          .reduce((total, log) => total + (log.pnl || 0), 0);
      },
      
      getWinRate: () => {
        const { tradingLogs } = get();
        const closedTrades = tradingLogs.filter((log) => log.status === 'CLOSED');
        if (closedTrades.length === 0) return 0;
        
        const winningTrades = closedTrades.filter((log) => (log.pnl || 0) > 0);
        return (winningTrades.length / closedTrades.length) * 100;
      },
      
      getActivePositions: () => {
        const { tradingLogs } = get();
        return tradingLogs.filter((log) => log.status === 'OPEN');
      },
    }),
    {
      name: 'trading-store',
    }
  )
);