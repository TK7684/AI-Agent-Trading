import React, { useState } from 'react';
import Input from '@components/Common/Input';
import Button from '@components/Common/Button';
import { useAuthStore } from '@/stores/authStore';
import { backendIntegration } from '@/services/BackendIntegration';

export const Login: React.FC = () => {
	const { setSession } = useAuthStore();
	const [email, setEmail] = useState('');
	const [password, setPassword] = useState('');
	const [error, setError] = useState<string | null>(null);

	const onSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		setError(null);
		try {
			if (!email || !password) throw new Error('Missing credentials');
			
			// Initialize backend integration if not already done
			await backendIntegration.initialize();
			
			// Authenticate with backend
			const authResult = await backendIntegration.authenticate({ username: email, password });
			
			// Set session in store
			setSession(
				authResult.token, 
				authResult.refreshToken, 
				3600, // 1 hour expiry
				{ 
					id: 'u1', 
					email, 
					name: email.split('@')[0], 
					roles: ['user'] 
				}
			);
		} catch (err: any) {
			setError(err.message || 'Login failed');
		}
	};

	return (
		<div className="mx-auto mt-20 max-w-sm rounded border p-4">
			<h1 className="mb-3 text-lg font-semibold">Login</h1>
			<form onSubmit={onSubmit} className="flex flex-col gap-3">
				<Input label="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
				<Input label="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
				{error && <div className="text-sm text-red-600">{error}</div>}
				<Button type="submit">Sign In</Button>
			</form>
		</div>
	);
};

export default Login;
