/**
 * Data formatting utility functions
 */

// Currency formatting
export const formatCurrency = (
  amount: number,
  currency: string = 'USD',
  locale: string = 'en-US',
  minimumFractionDigits: number = 2,
  maximumFractionDigits: number = 2
): string => {
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    minimumFractionDigits,
    maximumFractionDigits,
  }).format(amount);
};

// Percentage formatting
export const formatPercentage = (
  value: number,
  locale: string = 'en-US',
  minimumFractionDigits: number = 2,
  maximumFractionDigits: number = 2
): string => {
  return new Intl.NumberFormat(locale, {
    style: 'percent',
    minimumFractionDigits,
    maximumFractionDigits,
  }).format(value / 100);
};

// Number formatting with abbreviations (K, M, B)
export const formatNumber = (
  num: number,
  locale: string = 'en-US',
  precision: number = 1
): string => {
  const absNum = Math.abs(num);
  const sign = num < 0 ? '-' : '';
  
  if (absNum >= 1e9) {
    return `${sign}${(absNum / 1e9).toFixed(precision)}B`;
  } else if (absNum >= 1e6) {
    return `${sign}${(absNum / 1e6).toFixed(precision)}M`;
  } else if (absNum >= 1e3) {
    return `${sign}${(absNum / 1e3).toFixed(precision)}K`;
  }
  
  return new Intl.NumberFormat(locale, {
    minimumFractionDigits: 0,
    maximumFractionDigits: precision,
  }).format(num);
};

// Date and time formatting
export const formatDate = (
  date: Date | string | number,
  locale: string = 'en-US',
  options: Intl.DateTimeFormatOptions = {}
): string => {
  const dateObj = new Date(date);
  const defaultOptions: Intl.DateTimeFormatOptions = {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  };
  
  return new Intl.DateTimeFormat(locale, { ...defaultOptions, ...options }).format(dateObj);
};

export const formatTime = (
  date: Date | string | number,
  locale: string = 'en-US',
  options: Intl.DateTimeFormatOptions = {}
): string => {
  const dateObj = new Date(date);
  const defaultOptions: Intl.DateTimeFormatOptions = {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  };
  
  return new Intl.DateTimeFormat(locale, { ...defaultOptions, ...options }).format(dateObj);
};

export const formatDateTime = (
  date: Date | string | number,
  locale: string = 'en-US',
  options: Intl.DateTimeFormatOptions = {}
): string => {
  const dateObj = new Date(date);
  const defaultOptions: Intl.DateTimeFormatOptions = {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  };
  
  return new Intl.DateTimeFormat(locale, { ...defaultOptions, ...options }).format(dateObj);
};

// Relative time formatting (e.g., "2 hours ago")
export const formatRelativeTime = (
  date: Date | string | number,
  locale: string = 'en-US'
): string => {
  const dateObj = new Date(date);
  const now = new Date();
  const diffInSeconds = Math.floor((now.getTime() - dateObj.getTime()) / 1000);
  
  const rtf = new Intl.RelativeTimeFormat(locale, { numeric: 'auto' });
  
  if (diffInSeconds < 60) {
    return rtf.format(-diffInSeconds, 'second');
  } else if (diffInSeconds < 3600) {
    return rtf.format(-Math.floor(diffInSeconds / 60), 'minute');
  } else if (diffInSeconds < 86400) {
    return rtf.format(-Math.floor(diffInSeconds / 3600), 'hour');
  } else if (diffInSeconds < 2592000) {
    return rtf.format(-Math.floor(diffInSeconds / 86400), 'day');
  } else if (diffInSeconds < 31536000) {
    return rtf.format(-Math.floor(diffInSeconds / 2592000), 'month');
  } else {
    return rtf.format(-Math.floor(diffInSeconds / 31536000), 'year');
  }
};

// Duration formatting (e.g., "2h 30m 15s")
export const formatDuration = (milliseconds: number): string => {
  const seconds = Math.floor(milliseconds / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);
  
  const parts: string[] = [];
  
  if (days > 0) parts.push(`${days}d`);
  if (hours % 24 > 0) parts.push(`${hours % 24}h`);
  if (minutes % 60 > 0) parts.push(`${minutes % 60}m`);
  if (seconds % 60 > 0) parts.push(`${seconds % 60}s`);
  
  return parts.length > 0 ? parts.join(' ') : '0s';
};

// Price formatting with appropriate decimal places
export const formatPrice = (
  price: number,
  _symbol?: string,
  locale: string = 'en-US'
): string => {
  // Determine decimal places based on price magnitude
  let decimals = 2;
  if (price < 0.01) decimals = 6;
  else if (price < 0.1) decimals = 4;
  else if (price < 1) decimals = 3;
  
  return new Intl.NumberFormat(locale, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(price);
};

// Volume formatting
export const formatVolume = (volume: number, locale: string = 'en-US'): string => {
  return formatNumber(volume, locale, 1);
};

// P&L formatting with color indication
export const formatPnL = (
  pnl: number,
  currency: string = 'USD',
  locale: string = 'en-US'
): { formatted: string; isPositive: boolean; isNegative: boolean; isZero: boolean } => {
  const formatted = formatCurrency(pnl, currency, locale);
  return {
    formatted,
    isPositive: pnl > 0,
    isNegative: pnl < 0,
    isZero: pnl === 0,
  };
};

// Win rate formatting
export const formatWinRate = (winRate: number, locale: string = 'en-US'): string => {
  return formatPercentage(winRate, locale, 1, 1);
};

// File size formatting
export const formatFileSize = (bytes: number, locale: string = 'en-US'): string => {
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let size = bytes;
  let unitIndex = 0;
  
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }
  
  return `${new Intl.NumberFormat(locale, {
    minimumFractionDigits: 0,
    maximumFractionDigits: unitIndex === 0 ? 0 : 1,
  }).format(size)} ${units[unitIndex]}`;
};

// Symbol formatting (e.g., "BTCUSDT" -> "BTC/USDT")
export const formatSymbol = (symbol: string): string => {
  // Common base currencies to split on
  const baseCurrencies = ['USDT', 'USD', 'BTC', 'ETH', 'BNB', 'BUSD'];
  
  for (const base of baseCurrencies) {
    if (symbol.endsWith(base)) {
      const quote = symbol.slice(0, -base.length);
      return `${quote}/${base}`;
    }
  }
  
  // If no match found, return as-is
  return symbol;
};

// Status formatting with appropriate styling
export const formatStatus = (status: string): { text: string; variant: 'success' | 'warning' | 'error' | 'info' } => {
  const statusMap: Record<string, { text: string; variant: 'success' | 'warning' | 'error' | 'info' }> = {
    OPEN: { text: 'Open', variant: 'info' },
    CLOSED: { text: 'Closed', variant: 'success' },
    CANCELLED: { text: 'Cancelled', variant: 'warning' },
    running: { text: 'Running', variant: 'success' },
    paused: { text: 'Paused', variant: 'warning' },
    stopped: { text: 'Stopped', variant: 'error' },
    error: { text: 'Error', variant: 'error' },
    healthy: { text: 'Healthy', variant: 'success' },
    warning: { text: 'Warning', variant: 'warning' },
    critical: { text: 'Critical', variant: 'error' },
  };
  
  return statusMap[status] || { text: status, variant: 'info' };
};

// Confidence score formatting
export const formatConfidence = (confidence: number): string => {
  return `${confidence.toFixed(1)}%`;
};

// Truncate text with ellipsis
export const truncateText = (text: string, maxLength: number): string => {
  if (text.length <= maxLength) return text;
  return `${text.slice(0, maxLength - 3)}...`;
};

// Format trading side with appropriate styling
export const formatTradeSide = (side: 'LONG' | 'SHORT'): { text: string; variant: 'success' | 'error' } => {
  return {
    text: side,
    variant: side === 'LONG' ? 'success' : 'error',
  };
};