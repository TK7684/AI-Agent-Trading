import { test, expect } from '@playwright/test';

test.describe('Project Audit Workflow', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/login');
    await page.fill('[data-testid=email-input]', 'test@example.com');
    await page.fill('[data-testid=password-input]', 'password123');
    await page.click('[data-testid=login-button]');
    await page.waitForURL('/dashboard');
  });

  test('should create a new project', async ({ page }) => {
    // Navigate to new project page
    await page.click('[data-testid=new-project-button]');
    await expect(page).toHaveURL('/new-audit');

    // Fill project details
    await page.fill('[data-testid=project-name]', 'Test E2E Project');
    await page.fill('[data-testid=project-description]', 'A test project for E2E testing');
    await page.fill('[data-testid=github-url]', 'https://github.com/user/test-repo');
    await page.fill('[data-testid=contract-address]', '0x1234567890123456789012345678901234567890');
    await page.selectOption('[data-testid=chain-select]', 'ethereum');
    await page.fill('[data-testid=website-url]', 'https://example.com');
    await page.fill('[data-testid=twitter-url]', 'https://twitter.com/testproject');
    await page.fill('[data-testid=telegram-url]', 'https://t.me/testproject');
    await page.fill('[data-testid=discord-url]', 'https://discord.gg/testproject');

    // Submit project
    await page.click('[data-testid=create-project-button]');

    // Should show success message
    await expect(page.locator('[data-testid=project-created-message]')).toBeVisible();
    
    // Should redirect to project details
    await expect(page.locator('[data-testid=project-details]')).toBeVisible();
    await expect(page.locator('[data-testid=project-name]')).toContainText('Test E2E Project');
  });

  test('should validate project form fields', async ({ page }) => {
    // Navigate to new project page
    await page.click('[data-testid=new-project-button]');

    // Try to submit empty form
    await page.click('[data-testid=create-project-button]');

    // Check for validation errors
    await expect(page.locator('[data-testid=project-name-error]')).toBeVisible();
    await expect(page.locator('[data-testid=project-name-error]')).toContainText('Project name is required');
  });

  test('should start project analysis', async ({ page }) => {
    // Create a project first
    await page.click('[data-testid=new-project-button]');
    await page.fill('[data-testid=project-name]', 'Project for Analysis');
    await page.fill('[data-testid=github-url]', 'https://github.com/user/test-repo');
    await page.fill('[data-testid=contract-address]', '0x1234567890123456789012345678901234567890');
    await page.selectOption('[data-testid=chain-select]', 'ethereum');
    await page.click('[data-testid=create-project-button]');
    await page.locator('[data-testid=project-created-message]').waitFor();

    // Start analysis
    await page.click('[data-testid=analyze-button]');

    // Should show analysis progress
    await expect(page.locator('[data-testid=analysis-progress]')).toBeVisible();
    await expect(page.locator('[data-testid=progress-bar]')).toBeVisible();
    await expect(page.locator('[data-testid=progress-text]')).toContainText('Analyzing project...');
  });

  test('should display analysis results', async ({ page }) => {
    // Create and analyze a project
    await page.click('[data-testid=new-project-button]');
    await page.fill('[data-testid=project-name]', 'Project for Results');
    await page.fill('[data-testid=github-url]', 'https://github.com/user/test-repo');
    await page.fill('[data-testid=contract-address]', '0x1234567890123456789012345678901234567890');
    await page.selectOption('[data-testid=chain-select]', 'ethereum');
    await page.click('[data-testid=create-project-button]');
    await page.locator('[data-testid=project-created-message]').waitFor();
    await page.click('[data-testid=analyze-button]');

    // Wait for analysis to complete (increase timeout for long-running analysis)
    await expect(page.locator('[data-testid=analysis-results]')).toBeVisible({ timeout: 60000 });

    // Check overall score and risk level
    await expect(page.locator('[data-testid=overall-score]')).toBeVisible();
    await expect(page.locator('[data-testid=risk-level]')).toBeVisible();

    // Check individual scores
    await expect(page.locator('[data-testid=github-score]')).toBeVisible();
    await expect(page.locator('[data-testid=tokenomics-score]')).toBeVisible();
    await expect(page.locator('[data-testid=contract-risk-score]')).toBeVisible();
    await expect(page.locator('[data-testid=social-score]')).toBeVisible();

    // Check AI analysis
    await expect(page.locator('[data-testid=ai-analysis]')).toBeVisible();
  });

  test('should export audit report as PDF', async ({ page }) => {
    // Create and analyze a project
    await page.click('[data-testid=new-project-button]');
    await page.fill('[data-testid=project-name]', 'Project for Export');
    await page.fill('[data-testid=github-url]', 'https://github.com/user/test-repo');
    await page.click('[data-testid=create-project-button]');
    await page.locator('[data-testid=project-created-message]').waitFor();
    await page.click('[data-testid=analyze-button]');
    await page.locator('[data-testid=analysis-results]').waitFor({ timeout: 60000 });

    // Export as PDF
    const downloadPromise = page.waitForEvent('download');
    await page.click('[data-testid=export-pdf-button]');
    const download = await downloadPromise;

    // Verify download
    expect(download.suggestedFilename()).toContain('Project-for-Export');
    expect(download.suggestedFilename()).toContain('.pdf');
  });

  test('should export audit report as JSON', async ({ page }) => {
    // Create and analyze a project
    await page.click('[data-testid=new-project-button]');
    await page.fill('[data-testid=project-name]', 'Project for JSON Export');
    await page.fill('[data-testid=github-url]', 'https://github.com/user/test-repo');
    await page.click('[data-testid=create-project-button]');
    await page.locator('[data-testid=project-created-message]').waitFor();
    await page.click('[data-testid=analyze-button]');
    await page.locator('[data-testid=analysis-results]').waitFor({ timeout: 60000 });

    // Export as JSON
    const downloadPromise = page.waitForEvent('download');
    await page.click('[data-testid=export-json-button]');
    const download = await downloadPromise;

    // Verify download
    expect(download.suggestedFilename()).toContain('Project-for-JSON-Export');
    expect(download.suggestedFilename()).toContain('.json');
  });

  test('should add project to watchlist', async ({ page }) => {
    // Create and analyze a project
    await page.click('[data-testid=new-project-button]');
    await page.fill('[data-testid=project-name]', 'Project for Watchlist');
    await page.fill('[data-testid=github-url]', 'https://github.com/user/test-repo');
    await page.click('[data-testid=create-project-button]');
    await page.locator('[data-testid=project-created-message]').waitFor();
    await page.click('[data-testid=analyze-button]');
    await page.locator('[data-testid=analysis-results]').waitFor({ timeout: 60000 });

    // Add to watchlist
    await page.click('[data-testid=add-to-watchlist-button]');
    await page.fill('[data-testid=watchlist-notes]', 'Interesting project, keep an eye on it');
    await page.click('[data-testid=save-to-watchlist-button]');

    // Verify success message
    await expect(page.locator('[data-testid=watchlist-success-message]')).toBeVisible();
    await expect(page.locator('[data-testid=watchlist-success-message]')).toContainText('Added to watchlist');

    // Navigate to watchlist
    await page.click('[data-testid=watchlist-tab]');
    await expect(page).toHaveURL('/watchlist');

    // Verify project is in watchlist
    await expect(page.locator('[data-testid=watchlist-item]')).toContainText('Project for Watchlist');
    await expect(page.locator('[data-testid=watchlist-item]')).toContainText('Interesting project, keep an eye on it');
  });

  test('should compare projects', async ({ page }) => {
    // Create two projects
    for (let i = 1; i <= 2; i++) {
      await page.click('[data-testid=new-project-button]');
      await page.fill('[data-testid=project-name]', `Project ${i} for Comparison`);
      await page.fill('[data-testid=github-url]', `https://github.com/user/test-repo-${i}`);
      await page.click('[data-testid=create-project-button]');
      await page.locator('[data-testid=project-created-message]').waitFor();
    }

    // Navigate to comparison page
    await page.click('[data-testid=comparison-tab]');
    await page.click('[data-testid=new-comparison-button]');

    // Select projects to compare
    await page.check('[data-testid=project-1-checkbox]');
    await page.check('[data-testid=project-2-checkbox]');
    await page.fill('[data-testid=comparison-name]', 'Test Comparison');
    await page.click('[data-testid=create-comparison-button]');

    // Verify comparison results
    await expect(page.locator('[data-testid=comparison-table]')).toBeVisible();
    await expect(page.locator('[data-testid=comparison-chart]')).toBeVisible();
    await expect(page.locator('[data-testid=comparison-table]')).toContainText('Project 1 for Comparison');
    await expect(page.locator('[data-testid=comparison-table]')).toContainText('Project 2 for Comparison');
  });

  test('should handle analysis errors gracefully', async ({ page }) => {
    // Create a project with invalid GitHub URL
    await page.click('[data-testid=new-project-button]');
    await page.fill('[data-testid=project-name]', 'Project with Invalid URL');
    await page.fill('[data-testid=github-url]', 'https://github.com/nonexistent/nonexistent-repo');
    await page.click('[data-testid=create-project-button]');
    await page.locator('[data-testid=project-created-message]').waitFor();
    await page.click('[data-testid=analyze-button]');

    // Should show error message
    await expect(page.locator('[data-testid=analysis-error]')).toBeVisible({ timeout: 30000 });
    await expect(page.locator('[data-testid=analysis-error]')).toContainText('Failed to analyze project');

    // Should update project status to failed
    await page.reload();
    await expect(page.locator('[data-testid=project-status]')).toContainText('failed');
  });
});