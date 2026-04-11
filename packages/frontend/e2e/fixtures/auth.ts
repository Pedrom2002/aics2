import { test as base, expect, type Page, type APIRequestContext } from '@playwright/test'

/**
 * Auth fixtures for E2E tests.
 *
 * Two strategies are exposed:
 *
 * 1. `registerUser` / `loginUser` — UI-driven helpers for tests that
 *    explicitly exercise the auth flow.
 *
 * 2. `authenticatedPage` fixture — registers a fresh user via the backend API
 *    (faster, no UI interaction) and seeds localStorage / cookies so tests
 *    that just need an authenticated session can skip the login UI.
 *
 * The API base URL defaults to http://localhost:8000 and can be overridden
 * via PLAYWRIGHT_API_BASE_URL.
 */

export const API_BASE_URL = process.env.PLAYWRIGHT_API_BASE_URL ?? 'http://localhost:8000'

export interface TestUser {
  email: string
  password: string
  displayName: string
  orgName: string
  accessToken?: string
  refreshToken?: string
}

export function makeTestUser(prefix = 'e2e'): TestUser {
  const stamp = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
  return {
    email: `${prefix}+${stamp}@example.test`,
    password: 'TestPassword123!',
    displayName: `E2E ${stamp}`,
    orgName: `E2E Org ${stamp}`,
  }
}

/** Register a user via the backend API and return tokens. */
export async function apiRegister(request: APIRequestContext, user: TestUser): Promise<TestUser> {
  const res = await request.post(`${API_BASE_URL}/api/v1/auth/register`, {
    data: {
      org_name: user.orgName,
      email: user.email,
      password: user.password,
      display_name: user.displayName,
    },
  })
  if (!res.ok()) {
    throw new Error(`Backend register failed: ${res.status()} ${await res.text()}`)
  }
  const body = await res.json()
  return {
    ...user,
    accessToken: body.access_token,
    refreshToken: body.refresh_token,
  }
}

/** Drive the register form via the UI. */
export async function uiRegister(page: Page, user: TestUser): Promise<void> {
  await page.goto('/register')
  await page.locator('input[type="email"]').fill(user.email)
  await page.locator('input[type="password"]').first().fill(user.password)
  // Optional fields — fill if present
  const orgInput = page.locator('input[name="org_name"], input[name="orgName"]')
  if (await orgInput.count()) await orgInput.first().fill(user.orgName)
  const nameInput = page.locator('input[name="display_name"], input[name="displayName"]')
  if (await nameInput.count()) await nameInput.first().fill(user.displayName)
  await page.locator('button[type="submit"]').click()
}

/** Drive the login form via the UI. */
export async function uiLogin(page: Page, user: TestUser): Promise<void> {
  await page.goto('/login')
  await page.locator('input[type="email"]').fill(user.email)
  await page.locator('input[type="password"]').fill(user.password)
  await page.locator('button[type="submit"]').click()
}

/**
 * Inject auth tokens into the browser context so the next navigation is
 * already authenticated. The exact storage keys depend on the frontend
 * api-client; we set the most common ones to be defensive across refactors.
 */
export async function seedAuthStorage(page: Page, user: TestUser): Promise<void> {
  if (!user.accessToken) throw new Error('seedAuthStorage requires accessToken')
  await page.addInitScript(
    ([access, refresh]) => {
      try {
        window.localStorage.setItem('access_token', access)
        window.localStorage.setItem('refresh_token', refresh ?? '')
        window.localStorage.setItem('auth.access_token', access)
        window.localStorage.setItem('auth.refresh_token', refresh ?? '')
      } catch {
        /* ignore */
      }
    },
    [user.accessToken, user.refreshToken ?? ''],
  )
}

interface AuthFixtures {
  testUser: TestUser
  authenticatedPage: Page
}

/**
 * Extended Playwright test with auth fixtures. Use as:
 *
 *   import { test, expect } from '../fixtures/auth'
 *   test('foo', async ({ authenticatedPage }) => { ... })
 */
export const test = base.extend<AuthFixtures>({
  testUser: async ({ request }, use, testInfo) => {
    const user = makeTestUser(testInfo.project.name)
    try {
      const registered = await apiRegister(request, user)
      await use(registered)
    } catch (err) {
      // Surface the error but still let the test see the un-registered user
      // so it can decide to skip itself with a clear reason.
      ;(user as TestUser & { registrationError?: string }).registrationError = String(err)
      await use(user)
    }
  },
  authenticatedPage: async ({ page, testUser }, use) => {
    if (!testUser.accessToken) {
      // Backend was unreachable; let the consuming test decide what to do.
      await use(page)
      return
    }
    await seedAuthStorage(page, testUser)
    await use(page)
  },
})

export { expect }
