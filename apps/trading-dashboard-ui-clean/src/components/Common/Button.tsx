import React from 'react';
import clsx from 'clsx';

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';
type ButtonSize = 'sm' | 'md' | 'lg';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
	variant?: ButtonVariant;
	size?: ButtonSize;
	fullWidth?: boolean;
}

const base = 'inline-flex items-center justify-center rounded-md font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none';

const variantClasses: Record<ButtonVariant, string> = {
	primary: 'bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500',
	secondary: 'bg-gray-200 text-gray-900 hover:bg-gray-300 focus:ring-gray-400',
	ghost: 'bg-transparent text-gray-900 hover:bg-gray-100 focus:ring-gray-300',
	danger: 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500',
};

const sizeClasses: Record<ButtonSize, string> = {
	sm: 'h-8 px-3 text-sm',
	md: 'h-10 px-4 text-sm',
	lg: 'h-12 px-6 text-base',
};

export const Button: React.FC<ButtonProps> = ({
	variant = 'primary',
	size = 'md',
	fullWidth = false,
	className,
	children,
	...props
}) => {
	return (
		<button
			className={clsx(base, variantClasses[variant], sizeClasses[size], fullWidth && 'w-full', className)}
			{...props}
		>
			{children}
		</button>
	);
};

export default Button;
