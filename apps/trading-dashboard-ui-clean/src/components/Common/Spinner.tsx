import React from 'react';

export const Spinner: React.FC<{ size?: number }> = ({ size = 20 }) => (
	<svg width={size} height={size} viewBox="0 0 24 24" className="animate-spin text-gray-600">
		<circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" opacity="0.2" />
		<path d="M22 12a10 10 0 0 1-10 10" stroke="currentColor" strokeWidth="4" fill="none" />
	</svg>
);

export default Spinner;
