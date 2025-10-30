/**
 * Environment configuration for the trading dashboard
 */

export interface EnvironmentConfig {
  // API Configuration
  apiBaseUrl: string;
  wsBaseUrl: string;
  
  // Environment
  environment: 'development' | 'staging' | 'production';
  isDevelopment: boolean;
  isProduction: boolean;
  
  // Features
  authEnabled: boolean;
  debugMode: boolean;
  
  // App Info
  appName: string;
  appVersion: string;
}

/**
 * Get environment configuration from Vite environment variables
 */
function getEnvironmentConfig(): EnvironmentConfig {
  const environment = (import.meta.env.VITE_ENVIRONMENT || 'development') as EnvironmentConfig['environment'];
  
  return {
    // API Configuration
    apiBaseUrl: import.meta.env.VITE_BACKEND_API_URL || import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
    wsBaseUrl: import.meta.env.VITE_BACKEND_WS_URL || import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000',
    
    // Environment
    environment,
    isDevelopment: environment === 'development',
    isProduction: environment === 'production',
    
    // Features
    authEnabled: import.meta.env.VITE_AUTH_ENABLED === 'true',
    debugMode: import.meta.env.VITE_DEBUG_MODE === 'true',
    
    // App Info
    appName: import.meta.env.VITE_APP_NAME || 'Trading Dashboard',
    appVersion: import.meta.env.VITE_APP_VERSION || '1.0.0',
  };
}

export const env = getEnvironmentConfig();

// Log configuration in development
if (env.isDevelopment && env.debugMode) {
  console.log('Environment Configuration:', env);
}