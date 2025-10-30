// OfflineBanner Component - Shows offline status banner
import React from 'react';
import { useOffline } from '@/hooks/useOffline';

interface OfflineBannerProps {
  className?: string;
}

export const OfflineBanner: React.FC<OfflineBannerProps> = ({
  className = '',
}) => {
  const { isOnline, isServiceWorkerRegistered } = useOffline();

  // Don't show banner if online
  if (isOnline) {
    return null;
  }

  const getBannerStyle = () => {
    if (isServiceWorkerRegistered) {
      return 'bg-yellow-100 border-yellow-200 text-yellow-800';
    }
    return 'bg-red-100 border-red-200 text-red-800';
  };

  const getBannerMessage = () => {
    if (isServiceWorkerRegistered) {
      return 'You are currently offline. Limited functionality is available.';
    }
    return 'You are currently offline. Only cached data is available.';
  };

  const getBannerIcon = () => {
    if (isServiceWorkerRegistered) {
      return (
        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
        </svg>
      );
    }
    
    return (
      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
      </svg>
    );
  };

  return (
    <div className={`border-b ${getBannerStyle()} ${className}`}>
      <div className="max-w-7xl mx-auto py-2 px-3 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between flex-wrap">
          <div className="w-0 flex-1 flex items-center">
            <span className="flex p-2 rounded-lg">
              {getBannerIcon()}
            </span>
            <p className="ml-3 font-medium text-sm">
              {getBannerMessage()}
            </p>
          </div>
          <div className="order-2 flex-shrink-0 sm:order-3 sm:ml-3">
            <button
              type="button"
              className="flex p-2 rounded-md hover:bg-opacity-75 focus:outline-none focus:ring-2 focus:ring-white"
              onClick={() => window.location.reload()}
            >
              <span className="sr-only">Retry connection</span>
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clipRule="evenodd" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default OfflineBanner;