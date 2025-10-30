import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type { Notification } from '@/types';

interface NotificationState {
  // Notifications
  notifications: Notification[];
  
  // Settings
  soundEnabled: boolean;
  maxNotifications: number;
  
  // Actions
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) => void;
  removeNotification: (id: string) => void;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  clearAll: () => void;
  setSoundEnabled: (enabled: boolean) => void;
  setMaxNotifications: (max: number) => void;
  
  // Computed values
  getUnreadCount: () => number;
  getNotificationsByType: (type: Notification['type']) => Notification[];
}

export const useNotificationStore = create<NotificationState>()(
  devtools(
    (set, get) => ({
      // Initial state
      notifications: [],
      soundEnabled: true,
      maxNotifications: 100,
      
      // Actions
      addNotification: (notificationData) => {
        const notification: Notification = {
          ...notificationData,
          id: `notification-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          timestamp: new Date(),
          read: false,
        };
        
        set(
          (state) => {
            const newNotifications = [notification, ...state.notifications];
            
            // Limit the number of notifications
            if (newNotifications.length > state.maxNotifications) {
              newNotifications.splice(state.maxNotifications);
            }
            
            return { notifications: newNotifications };
          },
          false,
          'addNotification'
        );
        
        // Play sound if enabled and notification is important
        const { soundEnabled } = get();
        if (soundEnabled && (notification.type === 'error' || notification.type === 'warning')) {
          // Note: Sound playing will be implemented in the notification service
          console.log('🔊 Notification sound would play here');
        }
      },
      
      removeNotification: (id) =>
        set(
          (state) => ({
            notifications: state.notifications.filter((n) => n.id !== id),
          }),
          false,
          'removeNotification'
        ),
      
      markAsRead: (id) =>
        set(
          (state) => ({
            notifications: state.notifications.map((n) =>
              n.id === id ? { ...n, read: true } : n
            ),
          }),
          false,
          'markAsRead'
        ),
      
      markAllAsRead: () =>
        set(
          (state) => ({
            notifications: state.notifications.map((n) => ({ ...n, read: true })),
          }),
          false,
          'markAllAsRead'
        ),
      
      clearAll: () =>
        set({ notifications: [] }, false, 'clearAll'),
      
      setSoundEnabled: (enabled) =>
        set({ soundEnabled: enabled }, false, 'setSoundEnabled'),
      
      setMaxNotifications: (max) =>
        set({ maxNotifications: max }, false, 'setMaxNotifications'),
      
      // Computed values
      getUnreadCount: () => {
        const { notifications } = get();
        return notifications.filter((n) => !n.read).length;
      },
      
      getNotificationsByType: (type) => {
        const { notifications } = get();
        return notifications.filter((n) => n.type === type);
      },
    }),
    {
      name: 'notification-store',
    }
  )
);