/**
 * State optimization utilities for React components
 */

import { useRef, useCallback, useMemo } from 'react';
import { shallowEqual, BatchUpdater } from './performance';

// Optimized state selector hook
export function useSelector<T, R>(
  state: T,
  selector: (state: T) => R,
  equalityFn: (a: R, b: R) => boolean = shallowEqual
): R {
  const selectedStateRef = useRef<R>();
  const selectorRef = useRef(selector);
  const equalityFnRef = useRef(equalityFn);

  // Update refs if functions change
  selectorRef.current = selector;
  equalityFnRef.current = equalityFn;

  return useMemo(() => {
    const newSelectedState = selectorRef.current(state);
    
    if (
      selectedStateRef.current === undefined ||
      !equalityFnRef.current(selectedStateRef.current, newSelectedState)
    ) {
      selectedStateRef.current = newSelectedState;
    }
    
    return selectedStateRef.current;
  }, [state]);
}

// Optimized callback with dependency tracking
export function useOptimizedCallback<T extends (...args: any[]) => any>(
  callback: T,
  deps: React.DependencyList
): T {
  const callbackRef = useRef(callback);
  const depsRef = useRef(deps);

  // Only update if dependencies actually changed
  const depsChanged = useMemo(() => {
    if (depsRef.current.length !== deps.length) return true;
    return deps.some((dep, index) => dep !== depsRef.current[index]);
  }, [deps]);

  if (depsChanged) {
    callbackRef.current = callback;
    depsRef.current = deps;
  }

  return useCallback(callbackRef.current, deps);
}

// Batch state updates for better performance
export function useBatchedUpdates<T>(
  initialState: T,
  applyUpdates: (state: T, updates: Array<(state: T) => T>) => T
) {
  const batchUpdaterRef = useRef<BatchUpdater<T>>();
  
  if (!batchUpdaterRef.current) {
    batchUpdaterRef.current = new BatchUpdater<T>((updates) => {
      applyUpdates(initialState, updates);
    });
  }

  const addUpdate = useCallback((updateFn: (state: T) => T) => {
    batchUpdaterRef.current?.addUpdate(updateFn);
  }, []);

  const cancelUpdates = useCallback(() => {
    batchUpdaterRef.current?.cancel();
  }, []);

  return { addUpdate, cancelUpdates };
}

// Memoized component factory with custom comparison
export function createMemoizedComponent<P extends object>(
  Component: React.ComponentType<P>,
  areEqual?: (prevProps: P, nextProps: P) => boolean
) {
  const MemoizedComponent = React.memo(Component, areEqual);
  MemoizedComponent.displayName = `Memoized(${Component.displayName || Component.name})`;
  return MemoizedComponent;
}

// Optimized event handler factory
export function createOptimizedEventHandler<T extends Event>(
  handler: (event: T) => void,
  options: {
    preventDefault?: boolean;
    stopPropagation?: boolean;
    throttle?: number;
    debounce?: number;
  } = {}
) {
  const { preventDefault = false, stopPropagation = false, throttle, debounce } = options;

  let optimizedHandler = (event: T) => {
    if (preventDefault) event.preventDefault();
    if (stopPropagation) event.stopPropagation();
    handler(event);
  };

  if (throttle) {
    const { throttle: throttleFn } = require('./performance');
    optimizedHandler = throttleFn(optimizedHandler, throttle);
  } else if (debounce) {
    const { debounce: debounceFn } = require('./performance');
    optimizedHandler = debounceFn(optimizedHandler, debounce);
  }

  return optimizedHandler;
}

// Virtual list optimization utilities
export interface VirtualListItem {
  id: string | number;
  height?: number;
  data: any;
}

export interface VirtualListState {
  scrollTop: number;
  containerHeight: number;
  itemHeight: number;
  overscan: number;
}

export function calculateVirtualListRange(
  items: VirtualListItem[],
  state: VirtualListState
): {
  startIndex: number;
  endIndex: number;
  offsetY: number;
  totalHeight: number;
  visibleItems: VirtualListItem[];
} {
  const { scrollTop, containerHeight, itemHeight, overscan } = state;
  
  let totalHeight = 0;
  let startIndex = 0;
  let endIndex = 0;
  let offsetY = 0;

  // Calculate dynamic heights if items have different heights
  const itemHeights = items.map(item => item.height || itemHeight);
  const cumulativeHeights = itemHeights.reduce((acc, height, index) => {
    acc[index] = (acc[index - 1] || 0) + height;
    return acc;
  }, [] as number[]);

  totalHeight = cumulativeHeights[cumulativeHeights.length - 1] || 0;

  // Find start index
  for (let i = 0; i < cumulativeHeights.length; i++) {
    if (cumulativeHeights[i] > scrollTop) {
      startIndex = Math.max(0, i - overscan);
      offsetY = startIndex > 0 ? cumulativeHeights[startIndex - 1] : 0;
      break;
    }
  }

  // Find end index
  const visibleBottom = scrollTop + containerHeight;
  for (let i = startIndex; i < cumulativeHeights.length; i++) {
    if (cumulativeHeights[i] > visibleBottom) {
      endIndex = Math.min(items.length - 1, i + overscan);
      break;
    }
  }

  const visibleItems = items.slice(startIndex, endIndex + 1);

  return {
    startIndex,
    endIndex,
    offsetY,
    totalHeight,
    visibleItems,
  };
}

// Performance monitoring utilities
export class PerformanceMonitor {
  private metrics: Map<string, number[]> = new Map();
  private observers: Map<string, PerformanceObserver> = new Map();

  startTiming(label: string): () => void {
    const startTime = performance.now();
    
    return () => {
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      if (!this.metrics.has(label)) {
        this.metrics.set(label, []);
      }
      
      this.metrics.get(label)!.push(duration);
      
      // Keep only last 100 measurements
      const measurements = this.metrics.get(label)!;
      if (measurements.length > 100) {
        measurements.shift();
      }
    };
  }

  getAverageTime(label: string): number {
    const measurements = this.metrics.get(label);
    if (!measurements || measurements.length === 0) return 0;
    
    return measurements.reduce((sum, time) => sum + time, 0) / measurements.length;
  }

  getMetrics(label: string): { avg: number; min: number; max: number; count: number } {
    const measurements = this.metrics.get(label) || [];
    
    if (measurements.length === 0) {
      return { avg: 0, min: 0, max: 0, count: 0 };
    }

    return {
      avg: measurements.reduce((sum, time) => sum + time, 0) / measurements.length,
      min: Math.min(...measurements),
      max: Math.max(...measurements),
      count: measurements.length,
    };
  }

  observeRenderTimes(componentName: string): void {
    if (typeof PerformanceObserver === 'undefined') return;

    const observer = new PerformanceObserver((list) => {
      const entries = list.getEntries();
      entries.forEach((entry) => {
        if (entry.name.includes(componentName)) {
          if (!this.metrics.has(componentName)) {
            this.metrics.set(componentName, []);
          }
          this.metrics.get(componentName)!.push(entry.duration);
        }
      });
    });

    observer.observe({ entryTypes: ['measure'] });
    this.observers.set(componentName, observer);
  }

  stopObserving(componentName: string): void {
    const observer = this.observers.get(componentName);
    if (observer) {
      observer.disconnect();
      this.observers.delete(componentName);
    }
  }

  clearMetrics(label?: string): void {
    if (label) {
      this.metrics.delete(label);
    } else {
      this.metrics.clear();
    }
  }

  getAllMetrics(): Record<string, { avg: number; min: number; max: number; count: number }> {
    const result: Record<string, any> = {};
    
    for (const [label] of this.metrics) {
      result[label] = this.getMetrics(label);
    }
    
    return result;
  }
}

// Global performance monitor instance
export const performanceMonitor = new PerformanceMonitor();

// React hook for performance monitoring
export function usePerformanceMonitor(componentName: string) {
  const startTiming = useCallback(() => {
    return performanceMonitor.startTiming(componentName);
  }, [componentName]);

  const getMetrics = useCallback(() => {
    return performanceMonitor.getMetrics(componentName);
  }, [componentName]);

  return { startTiming, getMetrics };
}