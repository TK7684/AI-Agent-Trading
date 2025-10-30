import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { LOCAL_STORAGE_KEYS } from '@/utils/constants';

interface WidgetConfig {
  id: string;
  type: 'performance' | 'chart' | 'logs' | 'controls' | 'system';
  position: { x: number; y: number; w: number; h: number };
  visible: boolean;
  config: Record<string, any>;
}

interface UIState {
  // Layout and widgets
  widgets: WidgetConfig[];
  sidebarCollapsed: boolean;
  
  // Theme and preferences
  theme: 'light' | 'dark';
  compactMode: boolean;
  
  // Dashboard settings
  refreshInterval: number;
  autoRefresh: boolean;
  
  // Modal and overlay states
  activeModal: string | null;
  
  // Actions
  setWidgets: (widgets: WidgetConfig[]) => void;
  updateWidget: (id: string, updates: Partial<WidgetConfig>) => void;
  addWidget: (widget: WidgetConfig) => void;
  removeWidget: (id: string) => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setTheme: (theme: 'light' | 'dark') => void;
  setCompactMode: (compact: boolean) => void;
  setRefreshInterval: (interval: number) => void;
  setAutoRefresh: (enabled: boolean) => void;
  setActiveModal: (modal: string | null) => void;
  resetLayout: () => void;
  
  // Computed values
  getVisibleWidgets: () => WidgetConfig[];
  getWidgetById: (id: string) => WidgetConfig | undefined;
}

const defaultWidgets: WidgetConfig[] = [
  {
    id: 'performance',
    type: 'performance',
    position: { x: 0, y: 0, w: 6, h: 4 },
    visible: true,
    config: {},
  },
  {
    id: 'chart',
    type: 'chart',
    position: { x: 6, y: 0, w: 6, h: 8 },
    visible: true,
    config: { symbol: 'BTCUSDT', timeframe: '1h' },
  },
  {
    id: 'logs',
    type: 'logs',
    position: { x: 0, y: 4, w: 6, h: 4 },
    visible: true,
    config: { pageSize: 20 },
  },
  {
    id: 'controls',
    type: 'controls',
    position: { x: 0, y: 8, w: 4, h: 4 },
    visible: true,
    config: {},
  },
  {
    id: 'system',
    type: 'system',
    position: { x: 4, y: 8, w: 4, h: 4 },
    visible: true,
    config: {},
  },
];

export const useUIStore = create<UIState>()(
  devtools(
    persist(
      (set, get) => ({
        // Initial state
        widgets: defaultWidgets,
        sidebarCollapsed: false,
        theme: 'light',
        compactMode: false,
        refreshInterval: 5000,
        autoRefresh: true,
        activeModal: null,
        
        // Actions
        setWidgets: (widgets) =>
          set({ widgets }, false, 'setWidgets'),
        
        updateWidget: (id, updates) =>
          set(
            (state) => ({
              widgets: state.widgets.map((widget) =>
                widget.id === id ? { ...widget, ...updates } : widget
              ),
            }),
            false,
            'updateWidget'
          ),
        
        addWidget: (widget) =>
          set(
            (state) => ({ widgets: [...state.widgets, widget] }),
            false,
            'addWidget'
          ),
        
        removeWidget: (id) =>
          set(
            (state) => ({
              widgets: state.widgets.filter((widget) => widget.id !== id),
            }),
            false,
            'removeWidget'
          ),
        
        setSidebarCollapsed: (collapsed) =>
          set({ sidebarCollapsed: collapsed }, false, 'setSidebarCollapsed'),
        
        setTheme: (theme) =>
          set({ theme }, false, 'setTheme'),
        
        setCompactMode: (compact) =>
          set({ compactMode: compact }, false, 'setCompactMode'),
        
        setRefreshInterval: (interval) =>
          set({ refreshInterval: interval }, false, 'setRefreshInterval'),
        
        setAutoRefresh: (enabled) =>
          set({ autoRefresh: enabled }, false, 'setAutoRefresh'),
        
        setActiveModal: (modal) =>
          set({ activeModal: modal }, false, 'setActiveModal'),
        
        resetLayout: () =>
          set({ widgets: defaultWidgets }, false, 'resetLayout'),
        
        // Computed values
        getVisibleWidgets: () => {
          const { widgets } = get();
          return widgets.filter((widget) => widget.visible);
        },
        
        getWidgetById: (id) => {
          const { widgets } = get();
          return widgets.find((widget) => widget.id === id);
        },
      }),
      {
        name: LOCAL_STORAGE_KEYS.DASHBOARD_LAYOUT,
        partialize: (state) => ({
          widgets: state.widgets,
          sidebarCollapsed: state.sidebarCollapsed,
          theme: state.theme,
          compactMode: state.compactMode,
          refreshInterval: state.refreshInterval,
          autoRefresh: state.autoRefresh,
        }),
      }
    ),
    {
      name: 'ui-store',
    }
  )
);