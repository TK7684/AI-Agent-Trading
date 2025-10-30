/**
 * Simple Node.js script to test backend connection
 */

import fetch from 'node-fetch';

const API_BASE = 'http://127.0.0.1:8000';

async function testConnection() {
  console.log('Testing backend connection...');
  
  try {
    // Test 1: Health endpoint (no auth required)
    console.log('\n1. Testing health endpoint...');
    const healthResponse = await fetch(`${API_BASE}/system/health`);
    const healthData = await healthResponse.json();
    console.log('✅ Health check:', healthResponse.status, healthData);
    
    // Test 2: Login
    console.log('\n2. Testing authentication...');
    const loginResponse = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: 'test@example.com',
        password: 'password123'
      })
    });
    const loginData = await loginResponse.json();
    console.log('✅ Login:', loginResponse.status, loginData);
    
    if (loginResponse.ok && loginData.token) {
      const token = loginData.token;
      
      // Test 3: Authenticated endpoints
      console.log('\n3. Testing authenticated endpoints...');
      
      // Performance metrics
      const perfResponse = await fetch(`${API_BASE}/trading/performance`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const perfData = await perfResponse.json();
      console.log('✅ Performance:', perfResponse.status, perfData);
      
      // Agent status
      const agentResponse = await fetch(`${API_BASE}/system/agents`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const agentData = await agentResponse.json();
      console.log('✅ Agent status:', agentResponse.status, agentData);
      
      // Trading trades
      const tradesResponse = await fetch(`${API_BASE}/trading/trades`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const tradesData = await tradesResponse.json();
      console.log('✅ Trading trades:', tradesResponse.status, tradesData);
      
    } else {
      console.log('❌ Authentication failed, skipping authenticated tests');
    }
    
    console.log('\n🎉 All tests completed!');
    
  } catch (error) {
    console.error('❌ Test failed:', error.message);
  }
}

testConnection();