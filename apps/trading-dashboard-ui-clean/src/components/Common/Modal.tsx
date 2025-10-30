import React from 'react';
import clsx from 'clsx';

interface ModalProps {
	open: boolean;
	title?: string;
	onClose: () => void;
	children: React.ReactNode;
	className?: string;
}

export const Modal: React.FC<ModalProps> = ({ open, title, onClose, children, className }) => {
	if (!open) return null;
	return (
		<div className="fixed inset-0 z-50 flex items-center justify-center">
			<div className="absolute inset-0 bg-black/50" onClick={onClose} />
			<div className={clsx('relative z-10 w-full max-w-lg rounded-lg bg-white shadow-lg', className)}>
				{title && (
					<div className="px-4 py-3 border-b border-gray-200 font-semibold">
						{title}
					</div>
				)}
				<div className="p-4">
					{children}
				</div>
			</div>
		</div>
	);
};

export default Modal;
