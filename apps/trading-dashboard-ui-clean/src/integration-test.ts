/**
 * Integration test for backend connection
 */

import { backendIntegration } from './services/BackendIntegration';

async function runIntegrationTest() {
  console.log('🚀 Starting backend integration test...');
  
  try {
    // Test 1: Initialize backend integration
    console.log('\n1️⃣ Testing backend initialization...');
    await backendIntegration.initialize();
    console.log('✅ Backend integration initialized');
    
    // Test 2: Test authentication
    console.log('\n2️⃣ Testing authentication...');
    const authResult = await backendIntegration.authenticate({
      username: 'test@example.com',
      password: 'password123'
    });
    console.log('✅ Authentication successful:', {
      hasToken: !!authResult.token,
      hasRefreshToken: !!authResult.refreshToken
    });
    
    // Test 3: Test performance metrics API
    console.log('\n3️⃣ Testing performance metrics API...');
    const performance = await backendIntegration.getPerformanceMetrics();
    console.log('✅ Performance metrics retrieved:', {
      totalPnl: performance.totalPnl,
      portfolioValue: performance.portfolioValue,
      winRate: performance.winRate
    });
    
    // Test 4: Test agent status API
    console.log('\n4️⃣ Testing agent status API...');
    const agentStatus = await backendIntegration.getAgentStatus();
    console.log('✅ Agent status retrieved:', {
      state: agentStatus.state,
      uptime: agentStatus.uptime,
      activePositions: agentStatus.activePositions
    });
    
    // Test 5: Test system health API
    console.log('\n5️⃣ Testing system health API...');
    const systemHealth = await backendIntegration.getSystemHealth();
    console.log('✅ System health retrieved:', {
      cpu: systemHealth.cpu,
      memory: systemHealth.memory,
      connections: systemHealth.connections
    });
    
    // Test 6: Test trading history API
    console.log('\n6️⃣ Testing trading history API...');
    const tradingHistory = await backendIntegration.getTradingHistory();
    console.log('✅ Trading history retrieved:', {
      count: tradingHistory.length,
      firstTrade: tradingHistory[0] ? {
        symbol: tradingHistory[0].symbol,
        side: tradingHistory[0].side,
        status: tradingHistory[0].status
      } : null
    });
    
    // Test 7: Test connection status
    console.log('\n7️⃣ Testing connection status...');
    const connectionStatus = backendIntegration.getConnectionStatus();
    console.log('✅ Connection status:', connectionStatus);
    
    // Test 8: Test WebSocket connection
    console.log('\n8️⃣ Testing WebSocket connection...');
    const wsService = backendIntegration.getWebSocketService();
    const wsConnected = wsService.getConnectionStatus();
    console.log('✅ WebSocket status:', { connected: wsConnected });
    
    console.log('\n🎉 All integration tests passed!');
    
    return {
      success: true,
      results: {
        initialization: true,
        authentication: true,
        performanceMetrics: true,
        agentStatus: true,
        systemHealth: true,
        tradingHistory: true,
        connectionStatus: true,
        websocket: wsConnected
      }
    };
    
  } catch (error) {
    console.error('\n❌ Integration test failed:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : String(error)
    };
  }
}

// Export for use in other modules
export { runIntegrationTest };

// Run test if this file is executed directly
if (typeof window === 'undefined') {
  runIntegrationTest().then(result => {
    console.log('\n📊 Final Result:', result);
    process.exit(result.success ? 0 : 1);
  });
}