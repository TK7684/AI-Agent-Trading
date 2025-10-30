// Local storage management service

import { LOCAL_STORAGE_KEYS } from '@/utils/constants';

export class StorageService {
  // Get item from localStorage with JSON parsing
  static getItem<T>(key: string, defaultValue?: T): T | null {
    try {
      const item = localStorage.getItem(key);
      if (item === null) {
        return defaultValue || null;
      }
      return JSON.parse(item);
    } catch (error) {
      console.error(`Error getting item from localStorage: ${key}`, error);
      return defaultValue || null;
    }
  }
  
  // Set item in localStorage with JSON stringification
  static setItem<T>(key: string, value: T): void {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
      console.error(`Error setting item in localStorage: ${key}`, error);
    }
  }
  
  // Remove item from localStorage
  static removeItem(key: string): void {
    try {
      localStorage.removeItem(key);
    } catch (error) {
      console.error(`Error removing item from localStorage: ${key}`, error);
    }
  }
  
  // Clear all localStorage
  static clear(): void {
    try {
      localStorage.clear();
    } catch (error) {
      console.error('Error clearing localStorage', error);
    }
  }
  
  // Check if localStorage is available
  static isAvailable(): boolean {
    try {
      const test = '__localStorage_test__';
      localStorage.setItem(test, test);
      localStorage.removeItem(test);
      return true;
    } catch {
      return false;
    }
  }
  
  // Get dashboard layout
  static getDashboardLayout() {
    return this.getItem(LOCAL_STORAGE_KEYS.DASHBOARD_LAYOUT);
  }
  
  // Set dashboard layout
  static setDashboardLayout(layout: any): void {
    this.setItem(LOCAL_STORAGE_KEYS.DASHBOARD_LAYOUT, layout);
  }
  
  // Get user preferences
  static getUserPreferences() {
    return this.getItem(LOCAL_STORAGE_KEYS.USER_PREFERENCES, {
      theme: 'light',
      compactMode: false,
      soundEnabled: true,
    });
  }
  
  // Set user preferences
  static setUserPreferences(preferences: any): void {
    this.setItem(LOCAL_STORAGE_KEYS.USER_PREFERENCES, preferences);
  }
  
  // Get notification settings
  static getNotificationSettings() {
    return this.getItem(LOCAL_STORAGE_KEYS.NOTIFICATION_SETTINGS, {
      soundEnabled: true,
      browserNotifications: false,
      maxNotifications: 100,
    });
  }
  
  // Set notification settings
  static setNotificationSettings(settings: any): void {
    this.setItem(LOCAL_STORAGE_KEYS.NOTIFICATION_SETTINGS, settings);
  }
}