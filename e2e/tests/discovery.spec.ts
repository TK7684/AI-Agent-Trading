import { test, expect } from '@playwright/test';

test.describe('Project Discovery Workflow', () => {
  test.beforeEach(async ({ page }) => {
    // Visit the discovery page
    await page.goto('/discover');
  });

  test('should display trending projects', async ({ page }) => {
    // Check if discovery page loads correctly
    await expect(page.locator('[data-testid=discovery-page]')).toBeVisible();
    await expect(page.locator('[data-testid=projects-grid]')).toBeVisible();

    // Check if project cards are displayed
    await expect(page.locator('[data-testid=project-card]').first()).toBeVisible();
    
    // Check for project details in cards
    await expect(page.locator('[data-testid=project-card]').first().locator('[data-testid=project-name]')).toBeVisible();
    await expect(page.locator('[data-testid=project-card]').first().locator('[data-testid=project-symbol]')).toBeVisible();
    await expect(page.locator('[data-testid=project-card]').first().locator('[data-testid=project-price]')).toBeVisible();
  });

  test('should filter projects by category', async ({ page }) => {
    // Wait for projects to load
    await page.locator('[data-testid=project-card]').first().waitFor();

    // Open category filter
    await page.click('[data-testid=category-filter]');
    
    // Select DeFi category
    await page.click('[data-testid=category-defi]');

    // Should filter projects
    await page.waitForTimeout(2000); // Wait for filter to apply
    
    // Verify filtered results
    const projectCards = page.locator('[data-testid=project-card]');
    const count = await projectCards.count();
    
    if (count > 0) {
      // Check if all visible projects are DeFi
      for (let i = 0; i < count; i++) {
        const category = await projectCards.nth(i).locator('[data-testid=project-category]').textContent();
        expect(category).toContain('DeFi');
      }
    }
  });

  test('should filter projects by status', async ({ page }) => {
    // Wait for projects to load
    await page.locator('[data-testid=project-card]').first().waitFor();

    // Open status filter
    await page.click('[data-testid=status-filter]');
    
    // Select trending status
    await page.click('[data-testid=status-trending]');

    // Should filter projects
    await page.waitForTimeout(2000); // Wait for filter to apply
    
    // Verify filtered results
    const projectCards = page.locator('[data-testid=project-card]');
    const count = await projectCards.count();
    
    if (count > 0) {
      // Check if all visible projects are trending
      for (let i = 0; i < count; i++) {
        const status = await projectCards.nth(i).locator('[data-testid=project-status]').textContent();
        expect(status).toContain('trending');
      }
    }
  });

  test('should sort projects by market cap', async ({ page }) => {
    // Wait for projects to load
    await page.locator('[data-testid=project-card]').first().waitFor();

    // Open sort dropdown
    await page.click('[data-testid=sort-dropdown]');
    
    // Select market cap descending
    await page.click('[data-testid=sort-market-cap-desc]');

    // Wait for sort to apply
    await page.waitForTimeout(2000);

    // Verify sorting
    const projectCards = page.locator('[data-testid=project-card]');
    const count = await projectCards.count();
    
    if (count >= 2) {
      const firstProjectCap = await projectCards.first().locator('[data-testid=project-market-cap]').textContent();
      const secondProjectCap = await projectCards.nth(1).locator('[data-testid=project-market-cap]').textContent();
      
      // Extract numeric values and compare
      const firstCap = parseFloat(firstProjectCap?.replace(/[^0-9.]/g, '') || '0');
      const secondCap = parseFloat(secondProjectCap?.replace(/[^0-9.]/g, '') || '0');
      
      expect(firstCap).toBeGreaterThanOrEqual(secondCap);
    }
  });

  test('should search for specific project', async ({ page }) => {
    // Wait for projects to load
    await page.locator('[data-testid=project-card]').first().waitFor();

    // Search for Bitcoin
    await page.fill('[data-testid=search-input]', 'Bitcoin');
    await page.press('[data-testid=search-input]', 'Enter');

    // Wait for search results
    await page.waitForTimeout(2000);

    // Verify search results
    const projectCards = page.locator('[data-testid=project-card]');
    const count = await projectCards.count();
    
    if (count > 0) {
      // Check if results contain Bitcoin
      for (let i = 0; i < count; i++) {
        const name = await projectCards.nth(i).locator('[data-testid=project-name]').textContent();
        const symbol = await projectCards.nth(i).locator('[data-testid=project-symbol]').textContent();
        
        expect(
          name?.toLowerCase().includes('bitcoin') || 
          symbol?.toLowerCase().includes('btc')
        ).toBeTruthy();
      }
    }
  });

  test('should navigate to project details', async ({ page }) => {
    // Wait for projects to load
    await page.locator('[data-testid=project-card]').first().waitFor();

    // Click on first project
    await page.locator('[data-testid=project-card]').first().click();

    // Should navigate to project details
    await expect(page).toHaveURL(/\/discover\/.+/);
    await expect(page.locator('[data-testid=project-details]')).toBeVisible();
    await expect(page.locator('[data-testid=project-name]')).toBeVisible();
    await expect(page.locator('[data-testid=project-description]')).toBeVisible();
  });

  test('should audit a discovered project', async ({ page }) => {
    // Wait for projects to load
    await page.locator('[data-testid=project-card]').first().waitFor();

    // Click audit button on first project
    await page.locator('[data-testid=project-card]').first().locator('[data-testid=audit-button]').click();

    // Should navigate to new audit page with pre-filled data
    await expect(page).toHaveURL('/new-audit');
    await expect(page.locator('[data-testid=project-name]')).toBeVisible();
    await expect(page.locator('[data-testid=github-url]')).toBeVisible();
    
    // Check if some fields are pre-filled from discovery data
    const projectName = await page.locator('[data-testid=project-name]').inputValue();
    expect(projectName).not.toBe('');
  });

  test('should add discovered project to watchlist', async ({ page }) => {
    // Wait for projects to load
    await page.locator('[data-testid=project-card]').first().waitFor();

    // Click watchlist button on first project
    await page.locator('[data-testid=project-card]').first().locator('[data-testid=watchlist-button]').click();

    // Should show success message
    await expect(page.locator('[data-testid=watchlist-success-toast]')).toBeVisible();
    await expect(page.locator('[data-testid=watchlist-success-toast]')).toContainText('Added to watchlist');

    // Navigate to watchlist
    await page.click('[data-testid=watchlist-tab]');
    await expect(page).toHaveURL('/watchlist');

    // Verify project is in watchlist
    await expect(page.locator('[data-testid=watchlist-item]')).toBeVisible();
  });

  test('should handle empty search results', async ({ page }) => {
    // Wait for projects to load
    await page.locator('[data-testid=project-card]').first().waitFor();

    // Search for non-existent project
    await page.fill('[data-testid=search-input]', 'NonExistentProject123456');
    await page.press('[data-testid=search-input]', 'Enter');

    // Wait for search to complete
    await page.waitForTimeout(2000);

    // Verify empty state
    await expect(page.locator('[data-testid=no-results]')).toBeVisible();
    await expect(page.locator('[data-testid=no-results]')).toContainText('No projects found');
    await expect(page.locator('[data-testid=no-results]')).toContainText('Try adjusting your filters');
  });

  test('should load more projects on scroll', async ({ page }) => {
    // Wait for initial projects to load
    await page.locator('[data-testid=project-card]').first().waitFor();

    // Get initial project count
    const initialCount = await page.locator('[data-testid=project-card]').count();

    // Scroll to bottom of page
    await page.evaluate(() => {
      window.scrollTo(0, document.body.scrollHeight);
    });

    // Wait for more projects to load
    await page.waitForTimeout(3000);

    // Check if more projects were loaded
    const newCount = await page.locator('[data-testid=project-card]').count();
    expect(newCount).toBeGreaterThan(initialCount);
  });

  test('should display project categories', async ({ page }) => {
    // Check if category filter is available
    await expect(page.locator('[data-testid=category-filter]')).toBeVisible();

    // Click category filter to see options
    await page.click('[data-testid=category-filter]');

    // Verify common categories are available
    await expect(page.locator('[data-testid=category-all]')).toBeVisible();
    await expect(page.locator('[data-testid=category-defi]')).toBeVisible();
    await expect(page.locator('[data-testid=category-layer1]')).toBeVisible();
    await expect(page.locator('[data-testid=category-layer2]')).toBeVisible();
    await expect(page.locator('[data-testid=category-nft]')).toBeVisible();
    await expect(page.locator('[data-testid=category-gaming]')).toBeVisible();
    await expect(page.locator('[data-testid=category-ai]')).toBeVisible();
  });

  test('should display project price changes', async ({ page }) => {
    // Wait for projects to load
    await page.locator('[data-testid=project-card]').first().waitFor();

    // Check if price change is displayed
    const priceChange = page.locator('[data-testid=project-card]').first().locator('[data-testid=price-change]');
    
    if (await priceChange.isVisible()) {
      const priceChangeText = await priceChange.textContent();
      expect(priceChangeText).toMatch(/([+-]?\d+\.?\d*%)/); // Should match percentage format
    }
  });
});