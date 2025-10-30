/**
 * Backend Connection Test Component
 * Tests all aspects of frontend-backend integration
 */

import React, { useState, useEffect } from 'react';
import { backendIntegration } from '../services/BackendIntegration';
import { env } from '../config/environment';

interface TestResult {
  name: string;
  status: 'pending' | 'success' | 'error';
  message?: string;
  data?: any;
}

export const BackendConnectionTest: React.FC = () => {
  const [tests, setTests] = useState<TestResult[]>([
    { name: 'Backend Integration Initialization', status: 'pending' },
    { name: 'API Connection Test', status: 'pending' },
    { name: 'WebSocket Connection Test', status: 'pending' },
    { name: 'Authentication Test', status: 'pending' },
    { name: 'Performance Metrics API', status: 'pending' },
    { name: 'Agent Status API', status: 'pending' },
    { name: 'System Health API', status: 'pending' },
    { name: 'Real-time Data Flow', status: 'pending' },
  ]);
  
  const [isRunning, setIsRunning] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState({ api: false, websocket: false });

  const updateTest = (index: number, status: TestResult['status'], message?: string, data?: any) => {
    setTests(prev => prev.map((test, i) => 
      i === index ? { ...test, status, message, data } : test
    ));
  };

  const runTests = async () => {
    setIsRunning(true);
    
    try {
      // Test 1: Backend Integration Initialization
      updateTest(0, 'pending', 'Initializing backend integration...');
      await backendIntegration.initialize();
      updateTest(0, 'success', 'Backend integration initialized successfully');
      
      // Test 2: API Connection Test
      updateTest(1, 'pending', 'Testing API connection...');
      try {
        const apiService = backendIntegration.getApiService();
        const healthResponse = await apiService.get('/system/health');
        if (healthResponse.success) {
          updateTest(1, 'success', 'API connection successful', healthResponse.data);
        } else {
          updateTest(1, 'error', `API connection failed: ${healthResponse.error?.message}`);
        }
      } catch (error) {
        updateTest(1, 'error', `API connection error: ${error}`);
      }
      
      // Test 3: WebSocket Connection Test
      updateTest(2, 'pending', 'Testing WebSocket connection...');
      const wsService = backendIntegration.getWebSocketService();
      const wsConnected = wsService.getConnectionStatus();
      if (wsConnected) {
        updateTest(2, 'success', 'WebSocket connected successfully');
      } else {
        updateTest(2, 'error', 'WebSocket connection failed');
      }
      
      // Test 4: Authentication Test
      updateTest(3, 'pending', 'Testing authentication...');
      let authSuccessful = false;
      try {
        const authResult = await backendIntegration.authenticate({
          username: 'test@example.com',
          password: 'password123'
        });
        authSuccessful = true;
        updateTest(3, 'success', 'Authentication successful', { token: authResult.token ? 'Present' : 'Missing' });
      } catch (error) {
        updateTest(3, 'error', `Authentication failed: ${error}`);
      }
      
      // Only test authenticated endpoints if auth was successful
      if (authSuccessful) {
        // Test 5: Performance Metrics API
        updateTest(4, 'pending', 'Testing performance metrics API...');
        try {
          const performance = await backendIntegration.getPerformanceMetrics();
          updateTest(4, 'success', 'Performance metrics retrieved', performance);
        } catch (error) {
          updateTest(4, 'error', `Performance metrics failed: ${error}`);
        }
        
        // Test 6: Agent Status API
        updateTest(5, 'pending', 'Testing agent status API...');
        try {
          const agentStatus = await backendIntegration.getAgentStatus();
          updateTest(5, 'success', 'Agent status retrieved', agentStatus);
        } catch (error) {
          updateTest(5, 'error', `Agent status failed: ${error}`);
        }
        
        // Test 7: System Health API
        updateTest(6, 'pending', 'Testing system health API...');
        try {
          const systemHealth = await backendIntegration.getSystemHealth();
          updateTest(6, 'success', 'System health retrieved', systemHealth);
        } catch (error) {
          updateTest(6, 'error', `System health failed: ${error}`);
        }
      } else {
        // Skip authenticated tests if auth failed
        updateTest(4, 'error', 'Skipped - Authentication required');
        updateTest(5, 'error', 'Skipped - Authentication required');
        updateTest(6, 'error', 'Skipped - Authentication required');
      }
      
      // Test 8: Real-time Data Flow
      updateTest(7, 'pending', 'Testing real-time data flow...');
      let dataReceived = false;
      
      const testCallback = (data: any) => {
        dataReceived = true;
        updateTest(7, 'success', 'Real-time data received', data);
      };
      
      // Subscribe to updates
      backendIntegration.subscribeToTradingUpdates(testCallback);
      backendIntegration.subscribeToSystemUpdates(testCallback);
      backendIntegration.subscribeToAgentUpdates(testCallback);
      
      // Wait for data or timeout
      setTimeout(() => {
        if (!dataReceived) {
          updateTest(7, 'error', 'No real-time data received within timeout');
        }
      }, 5000);
      
    } catch (error) {
      console.error('Test execution error:', error);
    } finally {
      setIsRunning(false);
    }
  };

  // Update connection status periodically
  useEffect(() => {
    const interval = setInterval(() => {
      const status = backendIntegration.getConnectionStatus();
      setConnectionStatus(status);
    }, 1000);
    
    return () => clearInterval(interval);
  }, []);

  const getStatusIcon = (status: TestResult['status']) => {
    switch (status) {
      case 'pending': return '⏳';
      case 'success': return '✅';
      case 'error': return '❌';
      default: return '⚪';
    }
  };

  const getStatusColor = (status: TestResult['status']) => {
    switch (status) {
      case 'pending': return '#FFA500';
      case 'success': return '#00C851';
      case 'error': return '#FF4444';
      default: return '#666';
    }
  };

  return (
    <div style={{ padding: '20px', fontFamily: 'monospace' }}>
      <h2>Backend Connection Test</h2>
      
      <div style={{ marginBottom: '20px' }}>
        <h3>Environment Configuration</h3>
        <div style={{ background: '#f5f5f5', padding: '10px', borderRadius: '4px' }}>
          <div>API Base URL: {env.apiBaseUrl}</div>
          <div>WebSocket Base URL: {env.wsBaseUrl}</div>
          <div>Environment: {env.environment}</div>
          <div>Auth Enabled: {env.authEnabled ? 'Yes' : 'No'}</div>
          <div>Debug Mode: {env.debugMode ? 'Yes' : 'No'}</div>
        </div>
      </div>

      <div style={{ marginBottom: '20px' }}>
        <h3>Connection Status</h3>
        <div style={{ background: '#f5f5f5', padding: '10px', borderRadius: '4px' }}>
          <div>API: {connectionStatus.api ? '🟢 Connected' : '🔴 Disconnected'}</div>
          <div>WebSocket: {connectionStatus.websocket ? '🟢 Connected' : '🔴 Disconnected'}</div>
        </div>
      </div>

      <div style={{ marginBottom: '20px' }}>
        <button 
          onClick={runTests} 
          disabled={isRunning}
          style={{
            padding: '10px 20px',
            backgroundColor: isRunning ? '#ccc' : '#007bff',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: isRunning ? 'not-allowed' : 'pointer'
          }}
        >
          {isRunning ? 'Running Tests...' : 'Run Connection Tests'}
        </button>
      </div>

      <div>
        <h3>Test Results</h3>
        {tests.map((test, index) => (
          <div 
            key={index} 
            style={{ 
              marginBottom: '10px', 
              padding: '10px', 
              border: '1px solid #ddd', 
              borderRadius: '4px',
              borderLeft: `4px solid ${getStatusColor(test.status)}`
            }}
          >
            <div style={{ fontWeight: 'bold' }}>
              {getStatusIcon(test.status)} {test.name}
            </div>
            {test.message && (
              <div style={{ marginTop: '5px', fontSize: '14px', color: '#666' }}>
                {test.message}
              </div>
            )}
            {test.data && (
              <details style={{ marginTop: '5px' }}>
                <summary style={{ cursor: 'pointer', fontSize: '12px' }}>View Data</summary>
                <pre style={{ 
                  background: '#f8f8f8', 
                  padding: '10px', 
                  borderRadius: '4px', 
                  fontSize: '11px',
                  overflow: 'auto',
                  maxHeight: '200px'
                }}>
                  {JSON.stringify(test.data, null, 2)}
                </pre>
              </details>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default BackendConnectionTest;