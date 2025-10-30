// Debug API connection
import { apiService } from '@/services';

async function debugApiConnection() {
  console.log('Testing API connection...');
  console.log('Base URL:', apiService.getBaseUrl());
  
  try {
    // Test direct fetch first
    console.log('Testing direct fetch...');
    const directResponse = await fetch('http://localhost:8000/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email: 'test@example.com',
        password: 'password123'
      })
    });
    
    const directData = await directResponse.json();
    console.log('Direct fetch result:', directData);
    
    // Test API service
    console.log('Testing API service...');
    const serviceResponse = await apiService.login({
      username: 'test@example.com',
      password: 'password123'
    });
    
    console.log('API service result:', serviceResponse);
    
  } catch (error) {
    console.error('Error:', error);
  }
}

debugApiConnection();