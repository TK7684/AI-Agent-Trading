/**
 * Test script to verify API connection with the backend
 */

import { ApiService } from './services/apiService';

async function testApiConnection() {
  console.log('🔄 Testing API connection...');
  
  const apiService = new ApiService('http://127.0.0.1:8000');
  
  try {
    // Test 1: Login
    console.log('📝 Testing login...');
    const loginResponse = await apiService.login({
      username: 'test@example.com',
      password: 'password123'
    });
    
    if (loginResponse.success) {
      console.log('✅ Login successful:', loginResponse.data);
      
      // Test 2: Get performance data
      console.log('📊 Testing performance endpoint...');
      const performanceResponse = await apiService.getPerformance({ period: 'day' });
      
      if (performanceResponse.success) {
        console.log('✅ Performance data retrieved:', performanceResponse.data);
      } else {
        console.log('❌ Performance request failed:', performanceResponse.error);
      }
      
      // Test 3: Get agent status
      console.log('🤖 Testing agent status endpoint...');
      const agentResponse = await apiService.getAgentStatus();
      
      if (agentResponse.success) {
        console.log('✅ Agent status retrieved:', agentResponse.data);
      } else {
        console.log('❌ Agent status request failed:', agentResponse.error);
      }
      
      // Test 4: Get system health
      console.log('🏥 Testing system health endpoint...');
      const healthResponse = await apiService.getSystemHealth();
      
      if (healthResponse.success) {
        console.log('✅ System health retrieved:', healthResponse.data);
      } else {
        console.log('❌ System health request failed:', healthResponse.error);
      }
      
    } else {
      console.log('❌ Login failed:', loginResponse.error);
    }
    
  } catch (error) {
    console.error('💥 API connection test failed:', error);
  }
}

// Test WebSocket connection
async function testWebSocketConnection() {
  console.log('🔄 Testing WebSocket connection...');
  
  const { WebSocketService } = await import('./services/websocketService');
  
  const wsService = new WebSocketService({
    url: 'ws://127.0.0.1:8000'
  });
  
  wsService.setEventHandlers({
    onOpen: (_event) => {
      console.log('✅ WebSocket connected successfully');
      
      // Subscribe to trading updates
      wsService.subscribeToChannel('trading-updates');
      
      // Send a test message
      wsService.send({
        type: 'TEST',
        data: { message: 'Hello from frontend!' }
      });
    },
    onClose: (event) => {
      console.log('🔌 WebSocket disconnected:', event.code, event.reason);
    },
    onError: (event) => {
      console.error('❌ WebSocket error:', event);
    },
    onMessage: (message) => {
      console.log('📨 WebSocket message received:', message);
    }
  });
  
  try {
    await wsService.connect();
    
    // Keep connection open for a few seconds to test
    setTimeout(() => {
      wsService.disconnect();
      console.log('🔌 WebSocket test completed');
    }, 5000);
    
  } catch (error) {
    console.error('💥 WebSocket connection test failed:', error);
  }
}

// Run tests
export async function runConnectionTests() {
  console.log('🚀 Starting API and WebSocket connection tests...\n');
  
  await testApiConnection();
  console.log('\n');
  await testWebSocketConnection();
  
  console.log('\n✨ Connection tests completed!');
}

// Auto-run if this file is executed directly
if (import.meta.url === import.meta.resolve('./test-api-connection.ts')) {
  runConnectionTests();
}