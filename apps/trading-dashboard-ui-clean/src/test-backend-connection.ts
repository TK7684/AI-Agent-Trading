/**
 * Test script to verify backend connection
 */

import { backendIntegration } from './services/BackendIntegration';

async function testBackendConnection() {
  console.log('Testing backend connection...');
  
  try {
    // Initialize backend integration
    await backendIntegration.initialize();
    console.log('✅ Backend integration initialized successfully');
    
    // Test authentication
    const authResult = await backendIntegration.authenticate({
      username: 'test@example.com',
      password: 'password123'
    });
    console.log('✅ Authentication successful:', authResult);
    
    // Test API endpoints
    const performance = await backendIntegration.getPerformanceMetrics();
    console.log('✅ Performance metrics:', performance);
    
    const agentStatus = await backendIntegration.getAgentStatus();
    console.log('✅ Agent status:', agentStatus);
    
    const systemHealth = await backendIntegration.getSystemHealth();
    console.log('✅ System health:', systemHealth);
    
    // Test WebSocket connection
    const connectionStatus = backendIntegration.getConnectionStatus();
    console.log('✅ Connection status:', connectionStatus);
    
    console.log('🎉 All backend connection tests passed!');
    
  } catch (error) {
    console.error('❌ Backend connection test failed:', error);
  }
}

// Run the test
testBackendConnection();