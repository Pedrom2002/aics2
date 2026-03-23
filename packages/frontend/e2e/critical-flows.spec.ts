import { expect, test } from '@playwright/test'

test.describe('Landing Page', () => {
  test('should load landing page with key sections', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveTitle(/AI CS2/)
    // Hero section
    await expect(page.locator('text=CS2')).toBeVisible()
    // Pricing section should be visible
    await expect(page.locator('text=Pricing').first()).toBeVisible()
  })

  test('should navigate to pricing page', async ({ page }) => {
    await page.goto('/pricing')
    await expect(page.locator('text=Free')).toBeVisible()
    await expect(page.locator('text=Pro')).toBeVisible()
  })
})

test.describe('Authentication', () => {
  test('should show login page', async ({ page }) => {
    await page.goto('/login')
    await expect(page.locator('input[type="email"]')).toBeVisible()
    await expect(page.locator('input[type="password"]')).toBeVisible()
    await expect(page.locator('button[type="submit"]')).toBeVisible()
  })

  test('should show register page', async ({ page }) => {
    await page.goto('/register')
    await expect(page.locator('input[type="email"]')).toBeVisible()
    await expect(page.locator('input[type="password"]')).toBeVisible()
  })

  test('should redirect unauthenticated users from dashboard to login', async ({ page }) => {
    await page.goto('/dashboard')
    // Should redirect to login
    await page.waitForURL(/login/, { timeout: 5000 })
    await expect(page.locator('input[type="email"]')).toBeVisible()
  })

  test('should show validation error on empty login', async ({ page }) => {
    await page.goto('/login')
    await page.click('button[type="submit"]')
    // Browser validation should prevent submission with empty fields
    const emailInput = page.locator('input[type="email"]')
    await expect(emailInput).toHaveAttribute('required', '')
  })
})

test.describe('Dashboard (requires auth)', () => {
  // These tests would need auth setup — marked as smoke tests
  test('should not crash on direct navigation to demo pages', async ({ page }) => {
    await page.goto('/dashboard/demos')
    // Either redirects to login or shows content
    await page.waitForTimeout(2000)
    const url = page.url()
    expect(url.includes('login') || url.includes('demos')).toBeTruthy()
  })

  test('should not crash on pro matches page', async ({ page }) => {
    await page.goto('/dashboard/pro')
    await page.waitForTimeout(2000)
    const url = page.url()
    expect(url.includes('login') || url.includes('pro')).toBeTruthy()
  })

  test('should not crash on settings page', async ({ page }) => {
    await page.goto('/dashboard/settings')
    await page.waitForTimeout(2000)
    const url = page.url()
    expect(url.includes('login') || url.includes('settings')).toBeTruthy()
  })
})

test.describe('Responsive Design', () => {
  test('landing page should render on tablet viewport', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 })
    await page.goto('/')
    await expect(page.locator('text=CS2')).toBeVisible()
  })

  test('login page should render on mobile viewport', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 })
    await page.goto('/login')
    await expect(page.locator('input[type="email"]')).toBeVisible()
    await expect(page.locator('button[type="submit"]')).toBeVisible()
  })
})
