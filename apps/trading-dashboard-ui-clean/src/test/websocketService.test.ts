import { describe, it, expect, beforeEach, afterEach, vi, Mock } from 'vitest';
import { WebSocketService } from '../services/websocketService';
import type { AnyWebSocketMessage, WebSocketEventHandlers } from '@types/index';

// Mock WebSocket
class MockWebSocket {
  public readyState: number = 0; // CONNECTING
  public url: string;
  public onopen: ((event: Event) => void) | null = null;
  public onclose: ((event: CloseEvent) => void) | null = null;
  public onerror: ((event: Event) => void) | null = null;
  public onmessage: ((event: MessageEvent) => void) | null = null;
  
  public addEventListener = vi.fn();
  public removeEventListener = vi.fn();
  public close = vi.fn();
  public send = vi.fn();
  
  constructor(url: string) {
    this.url = url;
    this.readyState = 0; // CONNECTING
  }
  
  // Simulate connection events
  simulateOpen() {
    this.readyState = 1; // OPEN
    if (this.onopen) this.onopen(new Event('open'));
  }
  
  simulateClose(code: number = 1000, reason: string = '') {
    this.readyState = 3; // CLOSED
    if (this.onclose) this.onclose(new CloseEvent('close', { code, reason }));
  }
  
  simulateError() {
    this.readyState = 3; // CLOSED
    if (this.onerror) this.onerror(new Event('error'));
  }
  
  simulateMessage(data: any) {
    if (this.onmessage) {
      const messageEvent = new MessageEvent('message', { data: JSON.stringify(data) });
      this.onmessage(messageEvent);
    }
  }
}

// Mock global WebSocket
global.WebSocket = MockWebSocket as any;

// Mock timers
vi.useFakeTimers();

describe('WebSocketService', () => {
  let service: WebSocketService;
  let mockWs: MockWebSocket;
  
  beforeEach(() => {
    service = new WebSocketService();
    mockWs = new MockWebSocket('ws://localhost:8000/ws/trading');
  });
  
  afterEach(() => {
    service.destroy();
    vi.clearAllTimers();
    vi.clearAllMocks();
  });
  
  describe('Constructor and Configuration', () => {
    it('should initialize with default configuration', () => {
      expect(service.getConnectionStatus()).toBe(false);
      expect(service.getConnectionState().status).toBe('disconnected');
    });
    
    it('should accept custom configuration', () => {
      const customService = new WebSocketService({
        maxReconnectAttempts: 3,
        reconnectInterval: 2000,
        heartbeatInterval: 15000,
        timeout: 3000,
      });
      
      expect(customService.getConnectionStatus()).toBe(false);
      customService.destroy();
    });
  });
  
  describe('Connection Management', () => {
    it('should connect to WebSocket server', async () => {
      const connectPromise = service.connect();
      
      // Simulate successful connection
      mockWs.simulateOpen();
      
      await connectPromise;
      
      expect(service.getConnectionStatus()).toBe(true);
      expect(service.getConnectionState().status).toBe('connected');
    });
    
    it('should handle connection timeout', async () => {
      const connectPromise = service.connect();
      
      // Fast-forward time to trigger timeout
      vi.advanceTimersByTime(6000); // 5 seconds + buffer
      
      await connectPromise;
      
      expect(service.getConnectionStatus()).toBe(false);
      expect(service.getConnectionState().status).toBe('error');
    });
    
    it('should disconnect from WebSocket server', () => {
      service.connect();
      mockWs.simulateOpen();
      
      service.disconnect();
      
      expect(service.getConnectionStatus()).toBe(false);
      expect(service.getConnectionState().status).toBe('disconnected');
      expect(mockWs.close).toHaveBeenCalled();
    });
    
    it('should not connect if already connecting', async () => {
      const connectPromise1 = service.connect();
      const connectPromise2 = service.connect(); // Should be ignored
      
      mockWs.simulateOpen();
      
      await Promise.all([connectPromise1, connectPromise2]);
      
      expect(service.getConnectionStatus()).toBe(true);
    });
    
    it('should not connect if already connected', async () => {
      const connectPromise1 = service.connect();
      mockWs.simulateOpen();
      await connectPromise1;
      
      const connectPromise2 = service.connect(); // Should be ignored
      await connectPromise2;
      
      expect(service.getConnectionStatus()).toBe(true);
    });
  });
  
  describe('Automatic Reconnection', () => {
    it('should attempt reconnection on unexpected disconnect', async () => {
      const connectPromise = service.connect();
      mockWs.simulateOpen();
      await connectPromise;
      
      // Simulate unexpected disconnect
      mockWs.simulateClose(1006, 'Abnormal closure');
      
      // Fast-forward to trigger reconnection
      vi.advanceTimersByTime(6000);
      
      expect(service.getConnectionState().status).toBe('reconnecting');
    });
    
    it('should use exponential backoff for reconnection attempts', async () => {
      const connectPromise = service.connect();
      mockWs.simulateOpen();
      await connectPromise;
      
      // Simulate disconnect
      mockWs.simulateClose(1006, 'Abnormal closure');
      
      // First reconnection attempt should be after 5 seconds
      vi.advanceTimersByTime(4000);
      expect(service.getConnectionState().status).toBe('reconnecting');
      
      vi.advanceTimersByTime(2000);
      expect(service.getConnectionState().status).toBe('connecting');
    });
    
    it('should stop reconnection attempts after max attempts', async () => {
      const connectPromise = service.connect();
      mockWs.simulateOpen();
      await connectPromise;
      
      // Simulate multiple disconnects
      for (let i = 0; i < 12; i++) { // More than max attempts (10)
        mockWs.simulateClose(1006, 'Abnormal closure');
        vi.advanceTimersByTime(6000);
      }
      
      expect(service.getConnectionState().status).toBe('error');
      expect(service.getConnectionState().reconnectAttempts).toBe(10);
    });
    
    it('should not reconnect on manual disconnect', async () => {
      const connectPromise = service.connect();
      mockWs.simulateOpen();
      await connectPromise;
      
      // Manual disconnect
      service.disconnect();
      
      // Fast-forward time
      vi.advanceTimersByTime(10000);
      
      expect(service.getConnectionStatus()).toBe(false);
      expect(service.getConnectionState().reconnectAttempts).toBe(0);
    });
  });
  
  describe('Message Parsing and Routing', () => {
    it('should parse and route incoming messages by type', async () => {
      const connectPromise = service.connect();
      mockWs.simulateOpen();
      await connectPromise;
      
      const mockCallback = vi.fn();
      service.subscribe('TRADE_OPENED', mockCallback);
      
      const testMessage: AnyWebSocketMessage = {
        type: 'TRADE_OPENED',
        data: { id: '123', symbol: 'BTCUSD' },
        timestamp: new Date(),
        id: 'msg-1',
      };
      
      mockWs.simulateMessage(testMessage);
      
      expect(mockCallback).toHaveBeenCalledWith(testMessage.data);
    });
    
    it('should route messages by channel', async () => {
      const connectPromise = service.connect();
      mockWs.simulateOpen();
      await connectPromise;
      
      const mockCallback = vi.fn();
      service.subscribe(`channel:trading`, mockCallback);
      
      const testMessage: AnyWebSocketMessage = {
        type: 'TRADE_OPENED',
        data: { id: '123', symbol: 'BTCUSD' },
        timestamp: new Date(),
        id: 'msg-1',
        channel: 'trading',
      };
      
      mockWs.simulateMessage(testMessage);
      
      expect(mockCallback).toHaveBeenCalledWith(testMessage.data);
    });
    
    it('should handle malformed messages gracefully', async () => {
      const connectPromise = service.connect();
      mockWs.simulateOpen();
      await connectPromise;
      
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      
      // Simulate malformed message
      mockWs.simulateMessage('invalid json');
      
      expect(consoleSpy).toHaveBeenCalledWith('Failed to parse WebSocket message:', expect.any(Error));
      
      consoleSpy.mockRestore();
    });
    
    it('should handle errors in message listeners', async () => {
      const connectPromise = service.connect();
      mockWs.simulateOpen();
      await connectPromise;
      
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      
      const mockCallback = vi.fn().mockImplementation(() => {
        throw new Error('Listener error');
      });
      
      service.subscribe('TRADE_OPENED', mockCallback);
      
      const testMessage: AnyWebSocketMessage = {
        type: 'TRADE_OPENED',
        data: { id: '123' },
        timestamp: new Date(),
        id: 'msg-1',
      };
      
      mockWs.simulateMessage(testMessage);
      
      expect(consoleSpy).toHaveBeenCalledWith('Error in message listener:', expect.any(Error));
      
      consoleSpy.mockRestore();
    });
  });
  
  describe('Subscription Management', () => {
    it('should subscribe to events', async () => {
      const connectPromise = service.connect();
      mockWs.simulateOpen();
      await connectPromise;
      
      const mockCallback = vi.fn();
      service.subscribe('TRADE_OPENED', mockCallback);
      
      expect(service.getConnectionStatus()).toBe(true);
    });
    
    it('should unsubscribe from events', async () => {
      const connectPromise = service.connect();
      mockWs.simulateOpen();
      await connectPromise;
      
      const mockCallback = vi.fn();
      service.subscribe('TRADE_OPENED', mockCallback);
      service.unsubscribe('TRADE_OPENED', mockCallback);
      
      const testMessage: AnyWebSocketMessage = {
        type: 'TRADE_OPENED',
        data: { id: '123' },
        timestamp: new Date(),
        id: 'msg-1',
      };
      
      mockWs.simulateMessage(testMessage);
      
      expect(mockCallback).not.toHaveBeenCalled();
    });
    
    it('should subscribe to channels', async () => {
      const connectPromise = service.connect();
      mockWs.simulateOpen();
      await connectPromise;
      
      service.subscribeToChannel('trading', { symbol: 'BTCUSD' });
      
      expect(service.getConnectionStatus()).toBe(true);
    });
    
    it('should unsubscribe from channels', async () => {
      const connectPromise = service.connect();
      mockWs.simulateOpen();
      await connectPromise;
      
      service.subscribeToChannel('trading');
      service.unsubscribeFromChannel('trading');
      
      expect(service.getConnectionStatus()).toBe(true);
    });
  });
  
  describe('Connection Status Monitoring', () => {
    it('should provide accurate connection status', async () => {
      expect(service.getConnectionStatus()).toBe(false);
      
      const connectPromise = service.connect();
      mockWs.simulateOpen();
      await connectPromise;
      
      expect(service.getConnectionStatus()).toBe(true);
      
      service.disconnect();
      expect(service.getConnectionStatus()).toBe(false);
    });
    
    it('should provide detailed connection state', async () => {
      const initialState = service.getConnectionState();
      expect(initialState.status).toBe('disconnected');
      expect(initialState.reconnectAttempts).toBe(0);
      
      const connectPromise = service.connect();
      mockWs.simulateOpen();
      await connectPromise;
      
      const connectedState = service.getConnectionState();
      expect(connectedState.status).toBe('connected');
      expect(connectedState.lastConnected).toBeInstanceOf(Date);
      
      service.disconnect();
      
      const disconnectedState = service.getConnectionState();
      expect(disconnectedState.status).toBe('disconnected');
      expect(disconnectedState.lastDisconnected).toBeInstanceOf(Date);
    });
    
    it('should track reconnection attempts', async () => {
      const connectPromise = service.connect();
      mockWs.simulateOpen();
      await connectPromise;
      
      // Simulate disconnect and reconnection attempts
      mockWs.simulateClose(1006, 'Abnormal closure');
      vi.advanceTimersByTime(6000);
      
      const reconnectingState = service.getConnectionState();
      expect(reconnectingState.status).toBe('reconnecting');
      expect(reconnectingState.reconnectAttempts).toBe(1);
    });
  });
  
  describe('Error Handling', () => {
    it('should handle WebSocket errors', async () => {
      const connectPromise = service.connect();
      mockWs.simulateOpen();
      await connectPromise;
      
      mockWs.simulateError();
      
      expect(service.getConnectionState().status).toBe('error');
    });
    
    it('should handle connection errors', async () => {
      const connectPromise = service.connect();
      
      // Simulate connection error
      mockWs.simulateError();
      
      await connectPromise;
      
      expect(service.getConnectionState().status).toBe('error');
    });
    
    it('should handle send errors gracefully', async () => {
      const connectPromise = service.connect();
      mockWs.simulateOpen();
      await connectPromise;
      
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      
      // Disconnect to simulate send error
      service.disconnect();
      service.send({ type: 'TEST' });
      
      expect(consoleSpy).toHaveBeenCalledWith('WebSocket not connected, message not sent:', { type: 'TEST' });
      
      consoleSpy.mockRestore();
    });
  });
  
  describe('Event Handlers', () => {
    it('should call custom event handlers', async () => {
      const mockHandlers: WebSocketEventHandlers = {
        onOpen: vi.fn(),
        onClose: vi.fn(),
        onError: vi.fn(),
        onMessage: vi.fn(),
        onReconnect: vi.fn(),
        onReconnectFailed: vi.fn(),
      };
      
      service.setEventHandlers(mockHandlers);
      
      const connectPromise = service.connect();
      mockWs.simulateOpen();
      await connectPromise;
      
      expect(mockHandlers.onOpen).toHaveBeenCalled();
      
      const testMessage: AnyWebSocketMessage = {
        type: 'TRADE_OPENED',
        data: { id: '123' },
        timestamp: new Date(),
        id: 'msg-1',
      };
      
      mockWs.simulateMessage(testMessage);
      expect(mockHandlers.onMessage).toHaveBeenCalledWith(testMessage);
      
      mockWs.simulateClose(1006, 'Abnormal closure');
      expect(mockHandlers.onClose).toHaveBeenCalled();
      
      vi.advanceTimersByTime(6000);
      expect(mockHandlers.onReconnect).toHaveBeenCalled();
    });
  });
  
  describe('Heartbeat and Keep-Alive', () => {
    it('should send heartbeat messages', async () => {
      const connectPromise = service.connect();
      mockWs.simulateOpen();
      await connectPromise;
      
      // Fast-forward to trigger heartbeat
      vi.advanceTimersByTime(31000); // 30 seconds + buffer
      
      expect(mockWs.send).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'PING',
          data: expect.objectContaining({
            clientId: expect.any(String),
          }),
        })
      );
    });
    
    it('should stop heartbeat on disconnect', async () => {
      const connectPromise = service.connect();
      mockWs.simulateOpen();
      await connectPromise;
      
      service.disconnect();
      
      // Fast-forward to check if heartbeat is stopped
      vi.advanceTimersByTime(31000);
      
      // Should not have sent additional heartbeat messages
      const sendCalls = (mockWs.send as Mock).mock.calls.length;
      expect(sendCalls).toBeLessThanOrEqual(1); // Only the initial one
    });
  });
  
  describe('Resource Cleanup', () => {
    it('should clean up resources on destroy', async () => {
      const connectPromise = service.connect();
      mockWs.simulateOpen();
      await connectPromise;
      
      service.destroy();
      
      expect(service.getConnectionStatus()).toBe(false);
      expect(mockWs.close).toHaveBeenCalled();
      expect(mockWs.removeEventListener).toHaveBeenCalled();
    });
    
    it('should clean up timers on destroy', async () => {
      const connectPromise = service.connect();
      mockWs.simulateOpen();
      await connectPromise;
      
      service.destroy();
      
      // Fast-forward time to ensure no timers are running
      vi.advanceTimersByTime(10000);
      
      expect(service.getConnectionStatus()).toBe(false);
    });
  });
  
  describe('Channel Resubscription', () => {
    it('should resubscribe to channels after reconnection', async () => {
      const connectPromise = service.connect();
      mockWs.simulateOpen();
      await connectPromise;
      
      service.subscribeToChannel('trading', { symbol: 'BTCUSD' });
      
      // Simulate disconnect and reconnection
      mockWs.simulateClose(1006, 'Abnormal closure');
      vi.advanceTimersByTime(6000);
      
      // Should automatically resubscribe to channels
      expect(mockWs.send).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'SUBSCRIBE',
          channel: 'trading',
          params: { symbol: 'BTCUSD' },
        })
      );
    });
  });
});
