/**
 * Notification system TypeScript interfaces
 */

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  timestamp: Date;
  read: boolean;
  persistent: boolean;
  priority: NotificationPriority;
  category: NotificationCategory;
  actions?: NotificationAction[];
  metadata?: Record<string, any>;
  expiresAt?: Date;
}

export interface NotificationAction {
  id: string;
  label: string;
  action: () => void | Promise<void>;
  style: 'primary' | 'secondary' | 'danger' | 'success';
  disabled?: boolean;
}

export interface NotificationPreferences {
  soundEnabled: boolean;
  desktopNotifications: boolean;
  emailNotifications: boolean;
  categories: Record<NotificationCategory, boolean>;
  priorities: Record<NotificationPriority, boolean>;
  quietHours: {
    enabled: boolean;
    start: string; // HH:MM format
    end: string; // HH:MM format
  };
}

export interface NotificationFilter {
  categories: NotificationCategory[];
  priorities: NotificationPriority[];
  types: NotificationType[];
  dateRange: {
    start: Date;
    end: Date;
  };
  readStatus: 'all' | 'read' | 'unread';
  searchText: string;
}

export interface NotificationStats {
  total: number;
  unread: number;
  byCategory: Record<NotificationCategory, number>;
  byPriority: Record<NotificationPriority, number>;
  byType: Record<NotificationType, number>;
}

export interface ToastNotification {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  duration?: number; // Auto-dismiss duration in ms, undefined for persistent
  actions?: NotificationAction[];
}

export interface SystemNotification extends Notification {
  source: 'trading' | 'system' | 'agent' | 'user';
  correlationId?: string; // For grouping related notifications
  acknowledged: boolean;
  acknowledgedBy?: string;
  acknowledgedAt?: Date;
}

export type NotificationType = 
  | 'info' 
  | 'success' 
  | 'warning' 
  | 'error' 
  | 'trade' 
  | 'system' 
  | 'agent';

export type NotificationPriority = 
  | 'low' 
  | 'normal' 
  | 'high' 
  | 'critical';

export type NotificationCategory = 
  | 'trading' 
  | 'system' 
  | 'performance' 
  | 'security' 
  | 'configuration' 
  | 'maintenance' 
  | 'user';

export type NotificationSound = 
  | 'default' 
  | 'success' 
  | 'warning' 
  | 'error' 
  | 'trade' 
  | 'none';

// Predefined notification templates
export interface NotificationTemplate {
  id: string;
  name: string;
  type: NotificationType;
  priority: NotificationPriority;
  category: NotificationCategory;
  titleTemplate: string;
  messageTemplate: string;
  soundEnabled: boolean;
  sound: NotificationSound;
}

// Common notification creators
export interface NotificationCreators {
  tradeOpened: (trade: any) => Notification;
  tradeClosed: (trade: any) => Notification;
  stopLossTriggered: (trade: any) => Notification;
  dailyLimitReached: (limit: number, current: number) => Notification;
  systemError: (error: string, source: string) => Notification;
  connectionLost: (service: string) => Notification;
  connectionRestored: (service: string) => Notification;
  agentStatusChanged: (oldStatus: string, newStatus: string) => Notification;
}