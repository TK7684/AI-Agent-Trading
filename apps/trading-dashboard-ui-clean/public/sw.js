// Service Worker for Trading Dashboard
// Provides offline functionality, caching, and background sync

const CACHE_NAME = 'trading-dashboard-v1';
const STATIC_CACHE_NAME = 'trading-dashboard-static-v1';
const API_CACHE_NAME = 'trading-dashboard-api-v1';

// Static assets to cache
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/favicon.ico',
  // Add other static assets as needed
];

// API endpoints to cache
const CACHEABLE_API_PATTERNS = [
  /\/api\/trading\/history/,
  /\/api\/system\/config/,
  /\/api\/trading\/symbols/,
];

// Critical API endpoints that should be cached longer
const CRITICAL_API_PATTERNS = [
  /\/api\/auth\/user/,
  /\/api\/system\/status/,
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker');
  
  event.waitUntil(
    Promise.all([
      // Cache static assets
      caches.open(STATIC_CACHE_NAME).then((cache) => {
        console.log('[SW] Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      }),
      // Skip waiting to activate immediately
      self.skipWaiting()
    ])
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating service worker');
  
  event.waitUntil(
    Promise.all([
      // Clean up old caches
      caches.keys().then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => {
            if (cacheName !== CACHE_NAME && 
                cacheName !== STATIC_CACHE_NAME && 
                cacheName !== API_CACHE_NAME) {
              console.log('[SW] Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      }),
      // Claim all clients
      self.clients.claim()
    ])
  );
});

// Fetch event - handle network requests
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Handle different types of requests
  if (request.method === 'GET') {
    if (isStaticAsset(url)) {
      event.respondWith(handleStaticAsset(request));
    } else if (isApiRequest(url)) {
      event.respondWith(handleApiRequest(request));
    } else {
      event.respondWith(handleOtherRequest(request));
    }
  } else if (request.method === 'POST' || request.method === 'PUT') {
    // Handle write operations with background sync
    event.respondWith(handleWriteRequest(request));
  }
});

// Background sync for queued actions
self.addEventListener('sync', (event) => {
  console.log('[SW] Background sync triggered:', event.tag);
  
  if (event.tag === 'trading-actions') {
    event.waitUntil(syncTradingActions());
  } else if (event.tag === 'system-updates') {
    event.waitUntil(syncSystemUpdates());
  }
});

// Message handling for communication with main thread
self.addEventListener('message', (event) => {
  const { type, data } = event.data;
  
  switch (type) {
    case 'SKIP_WAITING':
      self.skipWaiting();
      break;
    case 'CACHE_API_RESPONSE':
      cacheApiResponse(data.url, data.response);
      break;
    case 'CLEAR_CACHE':
      clearCache(data.cacheName);
      break;
    case 'GET_CACHE_STATUS':
      getCacheStatus().then(status => {
        event.ports[0].postMessage({ type: 'CACHE_STATUS', data: status });
      });
      break;
  }
});

// Helper functions

function isStaticAsset(url) {
  return url.pathname.match(/\.(js|css|png|jpg|jpeg|gif|svg|ico|woff|woff2|ttf|eot)$/) ||
         url.pathname === '/' ||
         url.pathname === '/index.html';
}

function isApiRequest(url) {
  return url.pathname.startsWith('/api/') || url.pathname.startsWith('/ws/');
}

function isCacheableApi(url) {
  return CACHEABLE_API_PATTERNS.some(pattern => pattern.test(url.pathname)) ||
         CRITICAL_API_PATTERNS.some(pattern => pattern.test(url.pathname));
}

function isCriticalApi(url) {
  return CRITICAL_API_PATTERNS.some(pattern => pattern.test(url.pathname));
}

async function handleStaticAsset(request) {
  try {
    // Try cache first, then network
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }

    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(STATIC_CACHE_NAME);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    console.error('[SW] Static asset fetch failed:', error);
    // Return cached version if available
    return caches.match(request) || new Response('Offline', { status: 503 });
  }
}

async function handleApiRequest(request) {
  const url = new URL(request.url);
  
  try {
    // For critical APIs, try cache first when offline
    if (isCriticalApi(url)) {
      const networkResponse = await Promise.race([
        fetch(request),
        new Promise((_, reject) => setTimeout(() => reject(new Error('Timeout')), 3000))
      ]);
      
      if (networkResponse.ok && isCacheableApi(url)) {
        const cache = await caches.open(API_CACHE_NAME);
        cache.put(request, networkResponse.clone());
      }
      return networkResponse;
    }

    // For other APIs, network first, then cache
    const networkResponse = await fetch(request);
    
    if (networkResponse.ok && isCacheableApi(url)) {
      const cache = await caches.open(API_CACHE_NAME);
      cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
  } catch (error) {
    console.log('[SW] Network request failed, trying cache:', request.url);
    
    // Try to serve from cache
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      // Add offline indicator header
      const response = cachedResponse.clone();
      response.headers.set('X-Served-From-Cache', 'true');
      return response;
    }
    
    // Return offline response for API requests
    return new Response(
      JSON.stringify({
        error: 'Offline',
        message: 'This request is not available offline',
        offline: true
      }),
      {
        status: 503,
        headers: {
          'Content-Type': 'application/json',
          'X-Offline': 'true'
        }
      }
    );
  }
}

async function handleOtherRequest(request) {
  try {
    return await fetch(request);
  } catch (error) {
    console.error('[SW] Request failed:', error);
    return new Response('Offline', { status: 503 });
  }
}

async function handleWriteRequest(request) {
  try {
    // Try to send the request immediately
    const response = await fetch(request);
    return response;
  } catch (error) {
    console.log('[SW] Write request failed, queuing for background sync');
    
    // Queue the request for background sync
    await queueRequest(request);
    
    // Register background sync
    await self.registration.sync.register('trading-actions');
    
    // Return a response indicating the request was queued
    return new Response(
      JSON.stringify({
        success: false,
        queued: true,
        message: 'Request queued for when connection is restored'
      }),
      {
        status: 202,
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
}

async function queueRequest(request) {
  const requestData = {
    url: request.url,
    method: request.method,
    headers: Object.fromEntries(request.headers.entries()),
    body: request.method !== 'GET' ? await request.text() : null,
    timestamp: Date.now()
  };
  
  // Store in IndexedDB
  const db = await openDB();
  const transaction = db.transaction(['requests'], 'readwrite');
  const store = transaction.objectStore('requests');
  await store.add(requestData);
}

async function syncTradingActions() {
  console.log('[SW] Syncing trading actions');
  
  try {
    const db = await openDB();
    const transaction = db.transaction(['requests'], 'readwrite');
    const store = transaction.objectStore('requests');
    const requests = await store.getAll();
    
    for (const requestData of requests) {
      try {
        const response = await fetch(requestData.url, {
          method: requestData.method,
          headers: requestData.headers,
          body: requestData.body
        });
        
        if (response.ok) {
          // Remove from queue on success
          await store.delete(requestData.id);
          console.log('[SW] Successfully synced request:', requestData.url);
        }
      } catch (error) {
        console.error('[SW] Failed to sync request:', requestData.url, error);
      }
    }
  } catch (error) {
    console.error('[SW] Background sync failed:', error);
  }
}

async function syncSystemUpdates() {
  console.log('[SW] Syncing system updates');
  // Implementation for system-specific sync operations
}

async function openDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('TradingDashboardDB', 1);
    
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
    
    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      
      // Create object stores
      if (!db.objectStoreNames.contains('requests')) {
        const requestStore = db.createObjectStore('requests', { 
          keyPath: 'id', 
          autoIncrement: true 
        });
        requestStore.createIndex('timestamp', 'timestamp');
      }
      
      if (!db.objectStoreNames.contains('cache')) {
        const cacheStore = db.createObjectStore('cache', { keyPath: 'key' });
        cacheStore.createIndex('timestamp', 'timestamp');
      }
      
      if (!db.objectStoreNames.contains('state')) {
        db.createObjectStore('state', { keyPath: 'key' });
      }
    };
  });
}

async function cacheApiResponse(url, response) {
  try {
    const cache = await caches.open(API_CACHE_NAME);
    await cache.put(url, new Response(JSON.stringify(response)));
  } catch (error) {
    console.error('[SW] Failed to cache API response:', error);
  }
}

async function clearCache(cacheName) {
  try {
    if (cacheName) {
      await caches.delete(cacheName);
    } else {
      const cacheNames = await caches.keys();
      await Promise.all(cacheNames.map(name => caches.delete(name)));
    }
    console.log('[SW] Cache cleared:', cacheName || 'all');
  } catch (error) {
    console.error('[SW] Failed to clear cache:', error);
  }
}

async function getCacheStatus() {
  try {
    const cacheNames = await caches.keys();
    const status = {};
    
    for (const cacheName of cacheNames) {
      const cache = await caches.open(cacheName);
      const keys = await cache.keys();
      status[cacheName] = keys.length;
    }
    
    return status;
  } catch (error) {
    console.error('[SW] Failed to get cache status:', error);
    return {};
  }
}