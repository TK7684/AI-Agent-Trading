import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type { SystemHealth } from '@/types';

interface SystemState {
  // System health metrics
  systemHealth: SystemHealth | null;
  
  // Connection status
  isConnected: boolean;
  connectionStatus: {
    websocket: boolean;
    api: boolean;
    database: boolean;
    broker: boolean;
    llm: boolean;
  };
  
  // Loading states
  isLoadingHealth: boolean;
  
  // Actions
  setSystemHealth: (health: SystemHealth) => void;
  setConnectionStatus: (status: Partial<SystemState['connectionStatus']>) => void;
  setIsConnected: (connected: boolean) => void;
  setLoadingHealth: (loading: boolean) => void;
  
  // Computed values
  getOverallHealthScore: () => number;
  getCriticalIssues: () => string[];
}

export const useSystemStore = create<SystemState>()(
  devtools(
    (set, get) => ({
      // Initial state
      systemHealth: null,
      isConnected: false,
      connectionStatus: {
        websocket: false,
        api: false,
        database: false,
        broker: false,
        llm: false,
      },
      isLoadingHealth: false,
      
      // Actions
      setSystemHealth: (health) =>
        set({ systemHealth: health }, false, 'setSystemHealth'),
      
      setConnectionStatus: (status) =>
        set(
          (state) => ({
            connectionStatus: { ...state.connectionStatus, ...status },
          }),
          false,
          'setConnectionStatus'
        ),
      
      setIsConnected: (connected) =>
        set({ isConnected: connected }, false, 'setIsConnected'),
      
      setLoadingHealth: (loading) =>
        set({ isLoadingHealth: loading }, false, 'setLoadingHealth'),
      
      // Computed values
      getOverallHealthScore: () => {
        const { systemHealth } = get();
        if (!systemHealth) return 0;
        
        const metrics = [
          100 - systemHealth.cpu,
          100 - systemHealth.memory,
          100 - systemHealth.diskUsage,
          Math.max(0, 100 - systemHealth.networkLatency),
          Math.max(0, 100 - systemHealth.errorRate * 10),
        ];
        
        return metrics.reduce((sum, metric) => sum + metric, 0) / metrics.length;
      },
      
      getCriticalIssues: () => {
        const { systemHealth, connectionStatus } = get();
        const issues: string[] = [];
        
        if (systemHealth) {
          if (systemHealth.cpu > 90) issues.push('High CPU usage');
          if (systemHealth.memory > 90) issues.push('High memory usage');
          if (systemHealth.diskUsage > 90) issues.push('Low disk space');
          if (systemHealth.networkLatency > 1000) issues.push('High network latency');
          if (systemHealth.errorRate > 5) issues.push('High error rate');
        }
        
        if (!connectionStatus.database) issues.push('Database connection lost');
        if (!connectionStatus.broker) issues.push('Broker connection lost');
        if (!connectionStatus.llm) issues.push('LLM service unavailable');
        
        return issues;
      },
    }),
    {
      name: 'system-store',
    }
  )
);