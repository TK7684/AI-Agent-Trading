/**
 * Main schemas export file
 */

// Trading schemas
export * from './trading';
export * from './system';
export * from './notifications';

// Re-export validation functions with shorter names
export {
  validatePerformanceMetrics as validateTradingPerformance,
  validateTradeLogEntry as validateTrade,
  validateTradingSignal as validateSignal,
  validatePortfolio,
  validateChartData,
} from './trading';

export {
  validateSystemHealth,
  validateAgentStatus,
  validateAgentConfig,
  validateSystemAlert,
} from './system';

export {
  validateNotification,
  validateNotificationPreferences,
  validateToastNotification,
} from './notifications';

// Common validation utilities
export const isValidUUID = (uuid: string): boolean => {
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
  return uuidRegex.test(uuid);
};

export const isValidEmail = (email: string): boolean => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};

export const isValidTimeFormat = (time: string): boolean => {
  const timeRegex = /^([01]?[0-9]|2[0-3]):[0-5][0-9]$/;
  return timeRegex.test(time);
};

export const isValidSymbol = (symbol: string): boolean => {
  return symbol.length >= 1 && symbol.length <= 20 && /^[A-Z0-9]+$/.test(symbol);
};

export const isValidPrice = (price: number): boolean => {
  return price > 0 && isFinite(price);
};

export const isValidPercentage = (percentage: number): boolean => {
  return percentage >= 0 && percentage <= 100 && isFinite(percentage);
};