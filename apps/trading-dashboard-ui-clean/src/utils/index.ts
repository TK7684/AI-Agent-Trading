/**
 * Main utils export file
 */

export * from './formatters';
export * from './calculations';
export * from './constants';

// Re-export commonly used functions with shorter names
export {
  formatCurrency as currency,
  formatPercentage as percentage,
  formatNumber as number,
  formatDate as date,
  formatTime as time,
  formatDateTime as dateTime,
  formatRelativeTime as relativeTime,
  formatDuration as duration,
  formatPrice as price,
  formatPnL as formatPnL,
  formatSymbol as symbol,
} from './formatters';

export {
  calculatePnL as calculatePnL,
  calculateUnrealizedPnL as unrealizedPnL,
  calculatePercentagePnL as percentagePnL,
  calculateWinRate as winRate,
  calculateMaxDrawdown as maxDrawdown,
  calculatePositionSize as positionSize,
  calculateRiskRewardRatio as riskReward,
} from './calculations';

// Common utility functions
export const debounce = <T extends (...args: any[]) => any>(
  func: T,
  wait: number
): ((...args: Parameters<T>) => void) => {
  let timeout: NodeJS.Timeout;
  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
};

export const throttle = <T extends (...args: any[]) => any>(
  func: T,
  limit: number
): ((...args: Parameters<T>) => void) => {
  let inThrottle: boolean;
  return (...args: Parameters<T>) => {
    if (!inThrottle) {
      func(...args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  };
};

export const generateId = (): string => {
  return crypto.randomUUID();
};

export const clamp = (value: number, min: number, max: number): number => {
  return Math.min(Math.max(value, min), max);
};

export const roundTo = (value: number, decimals: number): number => {
  return Math.round(value * Math.pow(10, decimals)) / Math.pow(10, decimals);
};

export const isNullOrUndefined = (value: any): value is null | undefined => {
  return value === null || value === undefined;
};

export const isEmpty = (value: any): boolean => {
  if (isNullOrUndefined(value)) return true;
  if (typeof value === 'string') return value.trim().length === 0;
  if (Array.isArray(value)) return value.length === 0;
  if (typeof value === 'object') return Object.keys(value).length === 0;
  return false;
};

export const deepClone = <T>(obj: T): T => {
  return JSON.parse(JSON.stringify(obj));
};

export const sleep = (ms: number): Promise<void> => {
  return new Promise(resolve => setTimeout(resolve, ms));
};

// Export performance optimization utilities
export * from './performance';
export * from './stateOptimization';