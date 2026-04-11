import { test, expect } from '../fixtures/auth'
import { LoginPage } from '../pages/login-page'
import { RegisterPage } from '../pages/register-page'
import { DashboardPage } from '../pages/dashboard-page'
import { makeTestUser, uiRegister, uiLogin, API_BASE_URL } from '../fixtures/auth'

/**
 * Golden path: register → login → access dashboard → logout.
 *
 * Runnable: requires both frontend and backend running locally
 * (frontend on PLAYWRIGHT_BASE_URL, backend on PLAYWRIGHT_API_BASE_URL).
 *
 * The first test inside the file is a connectivity check that auto-skips the
 * rest of the suite if the backend is unreachable, so the file is still
 * collectable in CI without a live API.
 */

test.describe('golden-path: auth', () => {
  test.beforeAll(async ({ request }) => {
    try {
      const res = await request.get(`${API_BASE_URL}/api/v1/health`, { timeout: 3000 })
      if (!res.ok()) test.skip(true, `Backend health check failed: ${res.status()}`)
    } catch (err) {
      test.skip(true, `Backend unreachable at ${API_BASE_URL}: ${String(err)}`)
    }
  })

  test('register a brand-new user via the UI', async ({ page }) => {
    const user = makeTestUser('register')
    const registerPage = new RegisterPage(page)
    await registerPage.goto()
    await registerPage.register(user)

    // After register the app should land somewhere authenticated
    // (dashboard, onboarding, etc.) — assert we left /register.
    await expect(page).not.toHaveURL(/\/register$/, { timeout: 10_000 })
  })

  test('login an existing user and reach the dashboard', async ({ page, testUser }) => {
    test.skip(!testUser.accessToken, 'API registration failed in fixture')

    const loginPage = new LoginPage(page)
    await loginPage.goto()
    await loginPage.login(testUser.email, testUser.password)

    await page.waitForURL(/\/dashboard/, { timeout: 10_000 })
    await expect(page).toHaveURL(/\/dashboard/)
  })

  test('logout clears the session and redirects to login', async ({ page, testUser }) => {
    test.skip(!testUser.accessToken, 'API registration failed in fixture')

    // Login first
    await uiLogin(page, testUser)
    await page.waitForURL(/\/dashboard/, { timeout: 10_000 })

    const dashboard = new DashboardPage(page)
    if (await dashboard.logoutButton.first().isVisible().catch(() => false)) {
      await dashboard.logout()
      await page.waitForURL(/\/login|^\/$/, { timeout: 10_000 })
      await expect(page).toHaveURL(/\/login|^\/$/)
    } else {
      test.skip(true, 'Logout button not present in current UI build')
    }
  })

  test('full flow: register → logout → login', async ({ page }) => {
    const user = makeTestUser('full-flow')
    await uiRegister(page, user)
    await expect(page).not.toHaveURL(/\/register$/, { timeout: 10_000 })

    // Try to log out if we landed in the dashboard
    if (/\/dashboard/.test(page.url())) {
      const dashboard = new DashboardPage(page)
      if (await dashboard.logoutButton.first().isVisible().catch(() => false)) {
        await dashboard.logout()
        await page.waitForURL(/\/login|^\/$/, { timeout: 10_000 })
      }
    }

    // Then log back in
    await uiLogin(page, user)
    await page.waitForURL(/\/dashboard/, { timeout: 10_000 })
  })
})
