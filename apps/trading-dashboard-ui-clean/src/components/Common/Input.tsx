import React from 'react';
import clsx from 'clsx';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
	label?: string;
	error?: string;
}

export const Input: React.FC<InputProps> = ({ label, error, className, id, ...props }) => {
	const inputId = id || props.name || `input-${Math.random().toString(36).slice(2)}`;
	return (
		<div className={clsx('flex flex-col gap-1', className)}>
			{label && (
				<label htmlFor={inputId} className="text-sm text-gray-700">
					{label}
				</label>
			)}
			<input
				id={inputId}
				className={clsx(
					'rounded-md border px-3 py-2 outline-none transition-colors',
					error ? 'border-red-500 focus:border-red-600' : 'border-gray-300 focus:border-blue-600'
				)}
				{...props}
			/>
			{error && <span className="text-xs text-red-600">{error}</span>}
		</div>
	);
};

export default Input;
