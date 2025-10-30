import { render, screen } from '@testing-library/react';
import ErrorBoundary from '@components/Common/ErrorBoundary';
import Skeleton from '@components/Common/Skeleton';
import Spinner from '@components/Common/Spinner';

function Boom() {
	throw new Error('boom');
}

describe('Error and Loading UI', () => {
	it('ErrorBoundary shows fallback on error', () => {
		render(
			<ErrorBoundary>
				<Boom />
			</ErrorBoundary>
		);
		expect(screen.getByText(/Something went wrong/i)).toBeInTheDocument();
	});

	it('renders skeleton and spinner components', () => {
		render(<div><Skeleton /><Spinner /></div>);
		expect(document.querySelector('.animate-pulse')).toBeTruthy();
		expect(document.querySelector('.animate-spin')).toBeTruthy();
	});
});
