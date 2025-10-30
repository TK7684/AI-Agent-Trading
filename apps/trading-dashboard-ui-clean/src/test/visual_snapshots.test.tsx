import { render } from '@testing-library/react';
import Dashboard from '@components/Dashboard/Dashboard';
import { DashboardLayout } from '@components/Dashboard/Layout/DashboardLayout';

describe('Visual snapshots', () => {
	it('Dashboard renders consistently', () => {
		const { asFragment } = render(
			<DashboardLayout>
				<Dashboard />
			</DashboardLayout>
		);
		expect(asFragment()).toMatchSnapshot();
	});
});
