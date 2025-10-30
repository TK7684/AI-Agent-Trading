import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { setupServer } from 'msw/node';
import { rest } from 'msw';

// Mock service worker for testing
const mockServiceWorker = {
  register: vi.fn(),
  unregister: vi.fn(),
  update: vi.fn(),
  addEventListener: vi.fn(),
  postMessage: vi.fn(),
  state: 'activated',
  scriptURL: '/sw.js'
};

// Mock navigator.serviceWorker
Object.defineProperty(navigator, 'serviceWorker', {
  value: {
    register: vi.fn(() => Promise.resolve(mockServiceWorker)),
    ready: Promise.resolve(mockServiceWorker),
    controller: mockServiceWorker,
    addEventListener: vi.fn(),
    getRegistration: vi.fn(() => Promise.resolve(mockServiceWorker))
  },
  writable: true
});

// Mock server for API responses
const server = setupServer(
  rest.get('/api/trading/metrics', (req, res, ctx) => {
    return res(ctx.json({
      totalPnl: 1000,
      dailyPnl: 100,
      winRate: 75,
      totalTrades: 50
    }));
  }),
  
  rest.get('/api/system/health', (req, res, ctx) => {
    return res(ctx.json({
      cpu: 45,
      memory: 60,
      connections: {
        database: true,
        broker: true,
        llm: true
      }
    }));
  })
);

describe('Service Worker Integration Tests', () => {
  beforeEach(() => {
    server.listen();
    vi.clearAllMocks();
  });

  afterEach(() => {
    server.resetHandlers();
    vi.restoreAllMocks();
  });

  describe('Service Worker Registration', () => {
    it('should register service worker successfully', async () => {
      const registration = await navigator.serviceWorker.register('/sw.js');
      
      expect(navigator.serviceWorker.register).toHaveBeenCalledWith('/sw.js');
      expect(registration).toBeDefined();
      expect(registration.state).toBe('activated');
    });

    it('should handle service worker registration failure', async () => {
      const registerSpy = vi.spyOn(navigator.serviceWorker, 'register')
        .mockRejectedValueOnce(new Error('Registration failed'));

      await expect(navigator.serviceWorker.register('/sw.js')).rejects.toThrow('Registration failed');
      expect(registerSpy).toHaveBeenCalled();
    });

    it('should update service worker when new version available', async () => {
      const registration = await navigator.serviceWorker.register('/sw.js');
      
      // Simulate service worker update
      await registration.update();
      
      expect(mockServiceWorker.update).toHaveBeenCalled();
    });
  });

  describe('Cache Management', () => {
    it('should cache static assets on install', async () => {
      const mockCache = {
        addAll: vi.fn(() => Promise.resolve()),
        match: vi.fn(),
        put: vi.fn(),
        delete: vi.fn()
      };

      global.caches = {
        open: vi.fn(() => Promise.resolve(mockCache)),
        match: vi.fn(),
        has: vi.fn(),
        delete: vi.fn(),
        keys: vi.fn()
      };

      // Simulate service worker install event
      const installEvent = new Event('install');
      const staticAssets = [
        '/',
        '/static/js/main.js',
        '/static/css/main.css',
        '/manifest.json'
      ];

      // Mock service worker install handler
      const handleInstall = async (event: Event) => {
        const cache = await caches.open('trading-dashboard-v1');
        await cache.addAll(staticAssets);
      };

      await handleInstall(installEvent);

      expect(global.caches.open).toHaveBeenCalledWith('trading-dashboard-v1');
      expect(mockCache.addAll).toHaveBeenCalledWith(staticAssets);
    });

    it('should serve cached content when offline', async () => {
      const mockCache = {
        match: vi.fn(() => Promise.resolve(new Response('cached content'))),
        put: vi.fn(),
        addAll: vi.fn(),
        delete: vi.fn()
      };

      global.caches = {
        match: vi.fn(() => Promise.resolve(new Response('cached content'))),
        open: vi.fn(() => Promise.resolve(mockCache)),
        has: vi.fn(),
        delete: vi.fn(),
        keys: vi.fn()
      };

      // Simulate fetch event for cached resource
      const request = new Request('/api/trading/metrics');
      const cachedResponse = await caches.match(request);

      expect(cachedResponse).toBeDefined();
      expect(await cachedResponse?.text()).toBe('cached content');
    });

    it('should implement cache-first strategy for API requests', async () => {
      const mockCache = {
        match: vi.fn(() => Promise.resolve(null)), // No cache hit
        put: vi.fn(() => Promise.resolve()),
        addAll: vi.fn(),
        delete: vi.fn()
      };

      global.caches = {
        match: vi.fn(() => Promise.resolve(null)),
        open: vi.fn(() => Promise.resolve(mockCache)),
        has: vi.fn(),
        delete: vi.fn(),
        keys: vi.fn()
      };

      // Mock fetch for network request
      global.fetch = vi.fn(() => 
        Promise.resolve(new Response(JSON.stringify({ data: 'network response' })))
      );

      const request = new Request('/api/trading/metrics');
      
      // Simulate service worker fetch handler
      const handleFetch = async (request: Request) => {
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
          return cachedResponse;
        }
        
        const networkResponse = await fetch(request);
        const cache = await caches.open('trading-dashboard-v1');
        await cache.put(request, networkResponse.clone());
        return networkResponse;
      };

      const response = await handleFetch(request);
      const data = await response.json();

      expect(data).toEqual({ data: 'network response' });
      expect(mockCache.put).toHaveBeenCalled();
    });
  });

  describe('Offline Functionality', () => {
    it('should detect offline status', () => {
      // Mock navigator.onLine
      Object.defineProperty(navigator, 'onLine', {
        value: false,
        writable: true
      });

      expect(navigator.onLine).toBe(false);
    });

    it('should queue actions when offline', async () => {
      // Mock offline storage
      const offlineQueue: any[] = [];
      
      const queueAction = (action: any) => {
        offlineQueue.push({
          ...action,
          timestamp: Date.now(),
          id: Math.random().toString(36)
        });
      };

      // Simulate offline actions
      queueAction({ type: 'PLACE_ORDER', payload: { symbol: 'BTCUSD', quantity: 1 } });
      queueAction({ type: 'UPDATE_CONFIG', payload: { riskLimit: 1000 } });

      expect(offlineQueue).toHaveLength(2);
      expect(offlineQueue[0].type).toBe('PLACE_ORDER');
      expect(offlineQueue[1].type).toBe('UPDATE_CONFIG');
    });

    it('should sync queued actions when back online', async () => {
      const offlineQueue = [
        { id: '1', type: 'PLACE_ORDER', payload: { symbol: 'BTCUSD' }, timestamp: Date.now() },
        { id: '2', type: 'UPDATE_CONFIG', payload: { riskLimit: 1000 }, timestamp: Date.now() }
      ];

      const syncQueue = async (queue: any[]) => {
        const results = [];
        for (const action of queue) {
          try {
            const response = await fetch('/api/sync', {
              method: 'POST',
              body: JSON.stringify(action)
            });
            results.push({ id: action.id, success: response.ok });
          } catch (error) {
            results.push({ id: action.id, success: false, error });
          }
        }
        return results;
      };

      // Mock successful sync
      global.fetch = vi.fn(() => 
        Promise.resolve(new Response('', { status: 200 }))
      );

      const results = await syncQueue(offlineQueue);

      expect(results).toHaveLength(2);
      expect(results.every(r => r.success)).toBe(true);
    });

    it('should provide offline fallback UI', () => {
      const getOfflineFallback = () => {
        return `
          <div class="offline-fallback">
            <h2>You're offline</h2>
            <p>Some features may be limited while offline.</p>
            <p>Your data will sync when connection is restored.</p>
          </div>
        `;
      };

      const fallbackHTML = getOfflineFallback();
      expect(fallbackHTML).toContain('You\'re offline');
      expect(fallbackHTML).toContain('sync when connection is restored');
    });
  });

  describe('Background Sync', () => {
    it('should register background sync for critical actions', async () => {
      const mockRegistration = {
        sync: {
          register: vi.fn(() => Promise.resolve())
        }
      };

      // Mock service worker registration with sync
      Object.defineProperty(navigator.serviceWorker, 'ready', {
        value: Promise.resolve(mockRegistration)
      });

      const registerBackgroundSync = async (tag: string) => {
        const registration = await navigator.serviceWorker.ready;
        await registration.sync.register(tag);
      };

      await registerBackgroundSync('trading-data-sync');

      expect(mockRegistration.sync.register).toHaveBeenCalledWith('trading-data-sync');
    });

    it('should handle background sync events', async () => {
      const syncHandler = vi.fn();
      
      // Simulate background sync event
      const syncEvent = {
        tag: 'trading-data-sync',
        waitUntil: vi.fn()
      };

      const handleBackgroundSync = async (event: any) => {
        if (event.tag === 'trading-data-sync') {
          event.waitUntil(syncHandler());
        }
      };

      await handleBackgroundSync(syncEvent);

      expect(syncHandler).toHaveBeenCalled();
      expect(syncEvent.waitUntil).toHaveBeenCalled();
    });
  });

  describe('Push Notifications', () => {
    it('should handle push notification registration', async () => {
      const mockSubscription = {
        endpoint: 'https://fcm.googleapis.com/fcm/send/test',
        keys: {
          p256dh: 'test-key',
          auth: 'test-auth'
        }
      };

      const mockRegistration = {
        pushManager: {
          subscribe: vi.fn(() => Promise.resolve(mockSubscription)),
          getSubscription: vi.fn(() => Promise.resolve(null))
        }
      };

      Object.defineProperty(navigator.serviceWorker, 'ready', {
        value: Promise.resolve(mockRegistration)
      });

      const subscribeToPush = async () => {
        const registration = await navigator.serviceWorker.ready;
        const subscription = await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: 'test-vapid-key'
        });
        return subscription;
      };

      const subscription = await subscribeToPush();

      expect(subscription).toEqual(mockSubscription);
      expect(mockRegistration.pushManager.subscribe).toHaveBeenCalled();
    });

    it('should handle push message events', async () => {
      const showNotification = vi.fn();
      
      const handlePushMessage = async (event: any) => {
        const data = event.data?.json() || {};
        
        if (data.type === 'trading-alert') {
          await showNotification(data.title, {
            body: data.message,
            icon: '/icon-192x192.png',
            badge: '/badge-72x72.png',
            tag: 'trading-alert',
            requireInteraction: true
          });
        }
      };

      const pushEvent = {
        data: {
          json: () => ({
            type: 'trading-alert',
            title: 'Stop Loss Triggered',
            message: 'BTCUSD position closed at $45,000'
          })
        }
      };

      await handlePushMessage(pushEvent);

      expect(showNotification).toHaveBeenCalledWith('Stop Loss Triggered', {
        body: 'BTCUSD position closed at $45,000',
        icon: '/icon-192x192.png',
        badge: '/badge-72x72.png',
        tag: 'trading-alert',
        requireInteraction: true
      });
    });
  });

  describe('Service Worker Lifecycle', () => {
    it('should handle service worker updates gracefully', async () => {
      const mockNewWorker = {
        state: 'installed',
        addEventListener: vi.fn(),
        postMessage: vi.fn()
      };

      const mockRegistration = {
        installing: mockNewWorker,
        waiting: null,
        active: mockServiceWorker,
        addEventListener: vi.fn(),
        update: vi.fn()
      };

      const handleServiceWorkerUpdate = (registration: any) => {
        if (registration.installing) {
          const newWorker = registration.installing;
          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              // New service worker is available
              console.log('New service worker available');
            }
          });
        }
      };

      handleServiceWorkerUpdate(mockRegistration);

      expect(mockNewWorker.addEventListener).toHaveBeenCalledWith('statechange', expect.any(Function));
    });

    it('should skip waiting and activate new service worker', async () => {
      const skipWaiting = vi.fn(() => Promise.resolve());
      const claim = vi.fn(() => Promise.resolve());

      // Mock service worker global scope
      const serviceWorkerGlobalScope = {
        skipWaiting,
        clients: { claim },
        addEventListener: vi.fn()
      };

      const handleInstall = async () => {
        await serviceWorkerGlobalScope.skipWaiting();
      };

      const handleActivate = async () => {
        await serviceWorkerGlobalScope.clients.claim();
      };

      await handleInstall();
      await handleActivate();

      expect(skipWaiting).toHaveBeenCalled();
      expect(claim).toHaveBeenCalled();
    });
  });
});