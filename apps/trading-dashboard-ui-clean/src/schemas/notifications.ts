/**
 * Zod validation schemas for notification-related data
 */

import { z } from 'zod';

// Base schemas
export const NotificationTypeSchema = z.enum(['info', 'success', 'warning', 'error', 'trade', 'system', 'agent']);
export const NotificationPrioritySchema = z.enum(['low', 'normal', 'high', 'critical']);
export const NotificationCategorySchema = z.enum(['trading', 'system', 'performance', 'security', 'configuration', 'maintenance', 'user']);
export const NotificationSoundSchema = z.enum(['default', 'success', 'warning', 'error', 'trade', 'none']);

// Notification Action Schema
export const NotificationActionSchema = z.object({
  id: z.string().uuid(),
  label: z.string().min(1).max(50),
  style: z.enum(['primary', 'secondary', 'danger', 'success']),
  disabled: z.boolean().optional(),
});

// Base Notification Schema
export const NotificationSchema = z.object({
  id: z.string().uuid(),
  type: NotificationTypeSchema,
  title: z.string().min(1).max(200),
  message: z.string().min(1).max(1000),
  timestamp: z.date(),
  read: z.boolean(),
  persistent: z.boolean(),
  priority: NotificationPrioritySchema,
  category: NotificationCategorySchema,
  actions: z.array(NotificationActionSchema).optional(),
  metadata: z.record(z.string(), z.any()).optional(),
  expiresAt: z.date().optional(),
});

// System Notification Schema (extends base notification)
export const SystemNotificationSchema = NotificationSchema.extend({
  source: z.enum(['trading', 'system', 'agent', 'user']),
  correlationId: z.string().uuid().optional(),
  acknowledged: z.boolean(),
  acknowledgedBy: z.string().optional(),
  acknowledgedAt: z.date().optional(),
});

// Toast Notification Schema
export const ToastNotificationSchema = z.object({
  id: z.string().uuid(),
  type: NotificationTypeSchema,
  title: z.string().min(1).max(200),
  message: z.string().min(1).max(500),
  duration: z.number().int().positive().optional(),
  actions: z.array(NotificationActionSchema).optional(),
});

// Notification Preferences Schema
export const NotificationPreferencesSchema = z.object({
  soundEnabled: z.boolean(),
  desktopNotifications: z.boolean(),
  emailNotifications: z.boolean(),
  categories: z.record(NotificationCategorySchema, z.boolean()),
  priorities: z.record(NotificationPrioritySchema, z.boolean()),
  quietHours: z.object({
    enabled: z.boolean(),
    start: z.string().regex(/^([01]?[0-9]|2[0-3]):[0-5][0-9]$/, "Invalid time format (HH:MM)"),
    end: z.string().regex(/^([01]?[0-9]|2[0-3]):[0-5][0-9]$/, "Invalid time format (HH:MM)"),
  }),
});

// Notification Filter Schema
export const NotificationFilterSchema = z.object({
  categories: z.array(NotificationCategorySchema),
  priorities: z.array(NotificationPrioritySchema),
  types: z.array(NotificationTypeSchema),
  dateRange: z.object({
    start: z.date(),
    end: z.date(),
  }).refine(data => data.start <= data.end, {
    message: "Start date must be before or equal to end date",
  }),
  readStatus: z.enum(['all', 'read', 'unread']),
  searchText: z.string(),
});

// Notification Stats Schema
export const NotificationStatsSchema = z.object({
  total: z.number().int().min(0),
  unread: z.number().int().min(0),
  byCategory: z.record(NotificationCategorySchema, z.number().int().min(0)),
  byPriority: z.record(NotificationPrioritySchema, z.number().int().min(0)),
  byType: z.record(NotificationTypeSchema, z.number().int().min(0)),
});

// Notification Template Schema
export const NotificationTemplateSchema = z.object({
  id: z.string().uuid(),
  name: z.string().min(1).max(100),
  type: NotificationTypeSchema,
  priority: NotificationPrioritySchema,
  category: NotificationCategorySchema,
  titleTemplate: z.string().min(1).max(200),
  messageTemplate: z.string().min(1).max(1000),
  soundEnabled: z.boolean(),
  sound: NotificationSoundSchema,
});

// Bulk notification operations schema
export const BulkNotificationOperationSchema = z.object({
  ids: z.array(z.string().uuid()).min(1),
  action: z.enum(['mark_read', 'mark_unread', 'delete', 'acknowledge']),
});

// Validation helper functions
export const validateNotification = (data: unknown) => {
  return NotificationSchema.safeParse(data);
};

export const validateSystemNotification = (data: unknown) => {
  return SystemNotificationSchema.safeParse(data);
};

export const validateToastNotification = (data: unknown) => {
  return ToastNotificationSchema.safeParse(data);
};

export const validateNotificationPreferences = (data: unknown) => {
  return NotificationPreferencesSchema.safeParse(data);
};

export const validateNotificationFilter = (data: unknown) => {
  return NotificationFilterSchema.safeParse(data);
};

export const validateNotificationStats = (data: unknown) => {
  return NotificationStatsSchema.safeParse(data);
};

export const validateNotificationTemplate = (data: unknown) => {
  return NotificationTemplateSchema.safeParse(data);
};

export const validateBulkNotificationOperation = (data: unknown) => {
  return BulkNotificationOperationSchema.safeParse(data);
};

// Notification creation helpers with validation
export const createTradeNotification = (trade: any): z.SafeParseReturnType<any, any> => {
  const notification = {
    id: crypto.randomUUID(),
    type: 'trade' as const,
    title: `Trade ${trade.status === 'OPEN' ? 'Opened' : 'Closed'}`,
    message: `${trade.side} ${trade.symbol} at ${trade.entryPrice}${trade.pnl ? ` - P&L: ${trade.pnl}` : ''}`,
    timestamp: new Date(),
    read: false,
    persistent: false,
    priority: trade.pnl && trade.pnl < 0 ? 'high' as const : 'normal' as const,
    category: 'trading' as const,
  };
  return validateNotification(notification);
};

export const createSystemErrorNotification = (error: string, source: string): z.SafeParseReturnType<any, any> => {
  const notification = {
    id: crypto.randomUUID(),
    type: 'error' as const,
    title: 'System Error',
    message: `Error in ${source}: ${error}`,
    timestamp: new Date(),
    read: false,
    persistent: true,
    priority: 'critical' as const,
    category: 'system' as const,
  };
  return validateSystemNotification({
    ...notification,
    source: 'system',
    acknowledged: false,
  });
};

// Type inference from schemas
export type NotificationType = z.infer<typeof NotificationSchema>;
export type SystemNotificationType = z.infer<typeof SystemNotificationSchema>;
export type ToastNotificationType = z.infer<typeof ToastNotificationSchema>;
export type NotificationPreferencesType = z.infer<typeof NotificationPreferencesSchema>;
export type NotificationFilterType = z.infer<typeof NotificationFilterSchema>;
export type NotificationStatsType = z.infer<typeof NotificationStatsSchema>;
export type NotificationTemplateType = z.infer<typeof NotificationTemplateSchema>;