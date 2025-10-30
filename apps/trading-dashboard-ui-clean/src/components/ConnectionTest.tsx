import React, { useState } from 'react';
import { useBackendIntegration } from '@/hooks/useBackendIntegration';
import { env } from '@/config/environment';

// interface ConnectionStatus {
//   api: 'connecting' | 'connected' | 'error' | 'disconnected';
//   websocket: 'connecting' | 'connected' | 'error' | 'disconnected';
//   apiError?: string;
//   wsError?: string;
// }

export const ConnectionTest: React.FC = () => {
  const {
    isConnected,
    isConnecting,
    isAuthenticated,
    error,
    authenticate,
    logout,
    fetchPerformanceMetrics,
    fetchAgentStatus,
    fetchSystemHealth,
    fetchTradingHistory,
    controlAgent,
    apiService,
    wsService,
  } = useBackendIntegration();

  const [testResults, setTestResults] = useState<string[]>([]);

  const addTestResult = (message: string) => {
    setTestResults(prev => [...prev, `${new Date().toLocaleTimeString()}: ${message}`]);
  };

  const testApiConnection = async () => {
    addTestResult('Testing API connection...');
    
    try {
      // Test login first
      await authenticate({
        username: 'test@example.com',
        password: 'password123'
      });

      addTestResult('✅ API login successful');

      // Test authenticated endpoints
      try {
        await fetchPerformanceMetrics();
        addTestResult('✅ Performance data retrieved');
      } catch (error) {
        addTestResult('❌ Failed to get performance data');
      }

      try {
        await fetchSystemHealth();
        addTestResult('✅ System health data retrieved');
      } catch (error) {
        addTestResult('❌ Failed to get system health');
      }

      try {
        await fetchAgentStatus();
        addTestResult('✅ Agent status retrieved');
      } catch (error) {
        addTestResult('❌ Failed to get agent status');
      }

      try {
        await fetchTradingHistory();
        addTestResult('✅ Trading history retrieved');
      } catch (error) {
        addTestResult('❌ Failed to get trading history');
      }

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      addTestResult(`❌ API connection failed: ${errorMessage}`);
    }
  };

  const testWebSocketConnection = async () => {
    addTestResult('Testing WebSocket connection...');

    try {
      if (wsService.getConnectionStatus()) {
        addTestResult('✅ WebSocket already connected');
      } else {
        addTestResult('❌ WebSocket not connected');
      }

      // Test WebSocket subscriptions
      wsService.subscribeToChannel('trading');
      wsService.subscribeToChannel('system');
      addTestResult('✅ WebSocket subscriptions set up');

      // Send a test message
      wsService.send({
        type: 'TEST',
        data: { message: 'Connection test' },
        timestamp: new Date().toISOString(),
      });
      addTestResult('✅ Test message sent');

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      addTestResult(`❌ WebSocket test failed: ${errorMessage}`);
    }
  };

  const testAgentControl = async () => {
    addTestResult('Testing agent control...');
    
    try {
      await controlAgent('pause');
      addTestResult('✅ Agent paused successfully');
      
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      await controlAgent('start');
      addTestResult('✅ Agent started successfully');
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      addTestResult(`❌ Agent control failed: ${errorMessage}`);
    }
  };

  const testLogout = async () => {
    addTestResult('Testing logout...');
    
    try {
      await logout();
      addTestResult('✅ Logout successful');
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      addTestResult(`❌ Logout failed: ${errorMessage}`);
    }
  };

  const clearResults = () => {
    setTestResults([]);
  };

  const getStatusColor = (connected: boolean, connecting: boolean, hasError: boolean) => {
    if (hasError) return '#FF4444';
    if (connecting) return '#FF8800';
    if (connected) return '#00C851';
    return '#666666';
  };

  const getStatusText = (connected: boolean, connecting: boolean, hasError: boolean) => {
    if (hasError) return 'ERROR';
    if (connecting) return 'CONNECTING';
    if (connected) return 'CONNECTED';
    return 'DISCONNECTED';
  };

  return (
    <div style={{ padding: '20px', fontFamily: 'monospace' }}>
      <h2>Backend Connection Test</h2>
      
      <div style={{ marginBottom: '20px' }}>
        <h3>Connection Status</h3>
        <div style={{ display: 'flex', gap: '20px', marginBottom: '10px' }}>
          <div>
            <strong>Backend:</strong>{' '}
            <span style={{ color: getStatusColor(isConnected, isConnecting, !!error) }}>
              {getStatusText(isConnected, isConnecting, !!error)}
            </span>
            {error && <div style={{ color: '#FF4444', fontSize: '12px' }}>{error}</div>}
          </div>
          <div>
            <strong>Authentication:</strong>{' '}
            <span style={{ color: isAuthenticated ? '#00C851' : '#666666' }}>
              {isAuthenticated ? 'AUTHENTICATED' : 'NOT AUTHENTICATED'}
            </span>
          </div>
          <div>
            <strong>WebSocket:</strong>{' '}
            <span style={{ color: wsService.getConnectionStatus() ? '#00C851' : '#666666' }}>
              {wsService.getConnectionStatus() ? 'CONNECTED' : 'DISCONNECTED'}
            </span>
          </div>
        </div>
      </div>

      <div style={{ marginBottom: '20px' }}>
        <h3>Test Controls</h3>
        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          <button 
            onClick={testApiConnection}
            disabled={isConnecting}
            style={{ padding: '8px 16px', backgroundColor: '#007bff', color: 'white', border: 'none', borderRadius: '4px' }}
          >
            Test API & Authentication
          </button>
          <button 
            onClick={testWebSocketConnection}
            disabled={!isConnected}
            style={{ padding: '8px 16px', backgroundColor: '#28a745', color: 'white', border: 'none', borderRadius: '4px' }}
          >
            Test WebSocket
          </button>
          <button 
            onClick={testAgentControl}
            disabled={!isAuthenticated}
            style={{ padding: '8px 16px', backgroundColor: '#17a2b8', color: 'white', border: 'none', borderRadius: '4px' }}
          >
            Test Agent Control
          </button>
          <button 
            onClick={testLogout}
            disabled={!isAuthenticated}
            style={{ padding: '8px 16px', backgroundColor: '#dc3545', color: 'white', border: 'none', borderRadius: '4px' }}
          >
            Test Logout
          </button>
          <button 
            onClick={clearResults}
            style={{ padding: '8px 16px', backgroundColor: '#6c757d', color: 'white', border: 'none', borderRadius: '4px' }}
          >
            Clear Results
          </button>
        </div>
      </div>

      <div>
        <h3>Test Results</h3>
        <div 
          style={{ 
            backgroundColor: '#1e1e1e', 
            color: '#ffffff', 
            padding: '10px', 
            borderRadius: '4px', 
            height: '300px', 
            overflowY: 'auto',
            fontSize: '12px',
            lineHeight: '1.4'
          }}
        >
          {testResults.length === 0 ? (
            <div style={{ color: '#666666' }}>No test results yet. Click the test buttons above.</div>
          ) : (
            testResults.map((result, index) => (
              <div key={index} style={{ marginBottom: '4px' }}>
                {result}
              </div>
            ))
          )}
        </div>
      </div>

      <div style={{ marginTop: '20px', fontSize: '12px', color: '#666666' }}>
        <p><strong>Backend API URL:</strong> {env.apiBaseUrl}</p>
        <p><strong>WebSocket URL:</strong> {env.wsBaseUrl}</p>
        <p><strong>Environment:</strong> {env.environment}</p>
        <p><strong>Auth Enabled:</strong> {env.authEnabled ? 'Yes' : 'No'}</p>
        <p><strong>Debug Mode:</strong> {env.debugMode ? 'Yes' : 'No'}</p>
        <p><strong>Auth Token:</strong> {apiService.getAuthToken() ? `${apiService.getAuthToken()?.substring(0, 20)}...` : 'None'}</p>
      </div>
    </div>
  );
};