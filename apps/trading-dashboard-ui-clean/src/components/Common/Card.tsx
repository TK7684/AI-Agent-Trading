import React from 'react';
import clsx from 'clsx';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
	header?: React.ReactNode;
	footer?: React.ReactNode;
}

export const Card: React.FC<CardProps> = ({ header, footer, className, children, ...props }) => {
	return (
		<div className={clsx('rounded-lg border border-gray-200 bg-white shadow-sm', className)} {...props}>
			{header && (
				<div className="px-4 py-3 border-b border-gray-200">
					{header}
				</div>
			)}
			<div className="p-4">
				{children}
			</div>
			{footer && (
				<div className="px-4 py-3 border-t border-gray-200">
					{footer}
				</div>
			)}
		</div>
	);
};

export default Card;
