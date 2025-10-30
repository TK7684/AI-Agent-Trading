import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';

export const ProtectedRoute: React.FC<React.PropsWithChildren<{ roles?: string[] }>> = ({ roles, children }) => {
	const { authenticated, hasRole } = useAuthStore();
	if (!authenticated) return <Navigate to="/login" replace />;
	if (roles && roles.length > 0 && !roles.some((r) => hasRole(r))) return <Navigate to="/" replace />;
	return <>{children}</>;
};

export default ProtectedRoute;
