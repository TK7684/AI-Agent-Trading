import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Visit the login page
    await page.goto('/login');
  });

  test('should display login form', async ({ page }) => {
    // Check if login form elements are visible
    await expect(page.locator('[data-testid=email-input]')).toBeVisible();
    await expect(page.locator('[data-testid=password-input]')).toBeVisible();
    await expect(page.locator('[data-testid=login-button]')).toBeVisible();
    await expect(page.locator('[data-testid=signup-link]')).toBeVisible();
  });

  test('should show validation errors for empty fields', async ({ page }) => {
    // Try to login without filling the form
    await page.click('[data-testid=login-button]');

    // Check for validation errors
    await expect(page.locator('[data-testid=email-error]')).toBeVisible();
    await expect(page.locator('[data-testid=password-error]')).toBeVisible();
    await expect(page.locator('[data-testid=email-error]')).toContainText('Email is required');
    await expect(page.locator('[data-testid=password-error]')).toContainText('Password is required');
  });

  test('should show validation error for invalid email', async ({ page }) => {
    // Fill form with invalid email
    await page.fill('[data-testid=email-input]', 'invalid-email');
    await page.fill('[data-testid=password-input]', 'password123');
    await page.click('[data-testid=login-button]');

    // Check for email validation error
    await expect(page.locator('[data-testid=email-error]')).toBeVisible();
    await expect(page.locator('[data-testid=email-error]')).toContainText('Please enter a valid email');
  });

  test('should show validation error for short password', async ({ page }) => {
    // Fill form with short password
    await page.fill('[data-testid=email-input]', 'test@example.com');
    await page.fill('[data-testid=password-input]', '123');
    await page.click('[data-testid=login-button]');

    // Check for password validation error
    await expect(page.locator('[data-testid=password-error]')).toBeVisible();
    await expect(page.locator('[data-testid=password-error]')).toContainText('Password must be at least 8 characters');
  });

  test('should login with valid credentials', async ({ page }) => {
    // Fill form with valid credentials
    await page.fill('[data-testid=email-input]', 'test@example.com');
    await page.fill('[data-testid=password-input]', 'password123');
    await page.click('[data-testid=login-button]');

    // Should redirect to dashboard
    await expect(page).toHaveURL('/dashboard');
    
    // Check if user is logged in
    await expect(page.locator('[data-testid=user-menu]')).toBeVisible();
    await expect(page.locator('[data-testid=user-name]')).toContainText('Test User');
  });

  test('should show error message for invalid credentials', async ({ page }) => {
    // Fill form with invalid credentials
    await page.fill('[data-testid=email-input]', 'test@example.com');
    await page.fill('[data-testid=password-input]', 'wrongpassword');
    await page.click('[data-testid=login-button]');

    // Check for error message
    await expect(page.locator('[data-testid=login-error]')).toBeVisible();
    await expect(page.locator('[data-testid=login-error]')).toContainText('Invalid email or password');
  });

  test('should navigate to signup page', async ({ page }) => {
    // Click signup link
    await page.click('[data-testid=signup-link]');

    // Should navigate to signup page
    await expect(page).toHaveURL('/signup');
    await expect(page.locator('[data-testid=signup-form]')).toBeVisible();
  });

  test('should toggle password visibility', async ({ page }) => {
    const passwordInput = page.locator('[data-testid=password-input]');
    const toggleButton = page.locator('[data-testid=password-toggle]');

    // Initially password should be hidden
    await expect(passwordInput).toHaveAttribute('type', 'password');

    // Click to show password
    await toggleButton.click();
    await expect(passwordInput).toHaveAttribute('type', 'text');

    // Click to hide password
    await toggleButton.click();
    await expect(passwordInput).toHaveAttribute('type', 'password');
  });

  test('should remember login preference', async ({ page, context }) => {
    // Enable remember me
    await page.check('[data-testid=remember-me]');

    // Fill form and login
    await page.fill('[data-testid=email-input]', 'test@example.com');
    await page.fill('[data-testid=password-input]', 'password123');
    await page.click('[data-testid=login-button]');

    // Check if cookie is set
    const cookies = await context.cookies();
    const sessionCookie = cookies.find(cookie => cookie.name === 'auth-session');
    expect(sessionCookie).toBeDefined();
    expect(sessionCookie?.expires).toBeGreaterThan(Date.now() / 1000);
  });

  test('should logout successfully', async ({ page }) => {
    // First login
    await page.fill('[data-testid=email-input]', 'test@example.com');
    await page.fill('[data-testid=password-input]', 'password123');
    await page.click('[data-testid=login-button]');

    // Wait for dashboard to load
    await page.waitForURL('/dashboard');

    // Click logout
    await page.click('[data-testid=user-menu]');
    await page.click('[data-testid=logout-button]');

    // Should redirect to login page
    await expect(page).toHaveURL('/login');
    
    // Check if session is cleared
    const cookies = await page.context().cookies();
    const sessionCookie = cookies.find(cookie => cookie.name === 'auth-session');
    expect(sessionCookie).toBeUndefined();
  });
});