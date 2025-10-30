import React from 'react';
import clsx from 'clsx';

interface Option<T extends string | number = string> {
	label: string;
	value: T;
}

interface SelectProps<T extends string | number = string> extends React.SelectHTMLAttributes<HTMLSelectElement> {
	label?: string;
	error?: string;
	options: Option<T>[];
}

export function Select<T extends string | number = string>({ label, error, options, className, id, ...props }: SelectProps<T>) {
	const selectId = id || props.name || `select-${Math.random().toString(36).slice(2)}`;
	return (
		<div className={clsx('flex flex-col gap-1', className)}>
			{label && (
				<label htmlFor={selectId} className="text-sm text-gray-700">
					{label}
				</label>
			)}
			<select
				id={selectId}
				className={clsx(
					'rounded-md border px-3 py-2 outline-none transition-colors',
					error ? 'border-red-500 focus:border-red-600' : 'border-gray-300 focus:border-blue-600'
				)}
				{...props}
			>
				{options.map((opt) => (
					<option key={String(opt.value)} value={opt.value as any}>
						{opt.label}
					</option>
				))}
			</select>
			{error && <span className="text-xs text-red-600">{error}</span>}
		</div>
	);
}

export default Select;
