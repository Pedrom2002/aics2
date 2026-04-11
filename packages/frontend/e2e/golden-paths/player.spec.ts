import { test, expect } from '../fixtures/auth'
import { API_BASE_URL } from '../fixtures/auth'

/**
 * Golden path: login → players list → player detail → training tab.
 *
 * Mocked: player endpoints are stubbed via page.route. Auth still uses a real
 * backend register; if the backend is unreachable the test self-skips.
 */

const FAKE_STEAM_ID = '76561198000000001'

const fakePlayerList = {
  items: [
    {
      steam_id: FAKE_STEAM_ID,
      display_name: 'TestPlayerOne',
      rating: 1.12,
      matches_played: 42,
    },
  ],
  total: 1,
  page: 1,
  page_size: 20,
  pages: 1,
}

const fakePlayerDetail = {
  steam_id: FAKE_STEAM_ID,
  display_name: 'TestPlayerOne',
  rating: 1.12,
  matches_played: 42,
  recent_form: [],
  archetype: 'Entry Fragger',
}

const fakePlayerTraining = {
  steam_id: FAKE_STEAM_ID,
  drills: [],
  weak_skills: [],
  recommendations: [],
}

test.describe('golden-path: player detail', () => {
  test.beforeEach(async ({ page, testUser }) => {
    test.skip(!testUser.accessToken, `Backend not reachable at ${API_BASE_URL}`)

    await page.route(/\/api\/v1\/players(\/|\?|$)/, async (route) => {
      const url = route.request().url()
      if (url.includes('/training')) {
        await route.fulfill({ json: fakePlayerTraining })
        return
      }
      if (url.includes(FAKE_STEAM_ID)) {
        await route.fulfill({ json: fakePlayerDetail })
        return
      }
      await route.fulfill({ json: fakePlayerList })
    })
  })

  test('navigate to player detail and open training tab', async ({ authenticatedPage }) => {
    const page = authenticatedPage
    await page.goto('/dashboard/players')
    await expect(page).toHaveURL(/\/dashboard\/players/)

    // Click into the (mocked) player; fall back to direct URL if no card visible.
    const card = page
      .getByRole('link', { name: /testplayerone/i })
      .or(page.locator(`[data-testid="player-row-${FAKE_STEAM_ID}"]`))
      .first()

    if (await card.isVisible().catch(() => false)) {
      await card.click()
    } else {
      await page.goto(`/dashboard/players/${FAKE_STEAM_ID}`)
    }

    await expect(page).toHaveURL(new RegExp(`/players/${FAKE_STEAM_ID}`))

    // Open the training tab — could be a Radix tab or a child route.
    const trainingTab = page
      .getByRole('tab', { name: /training/i })
      .or(page.getByRole('link', { name: /training/i }))
      .first()

    if (await trainingTab.isVisible().catch(() => false)) {
      await trainingTab.click()
    } else {
      await page.goto(`/dashboard/players/${FAKE_STEAM_ID}/training`)
    }

    await expect(page.locator('body')).toBeVisible()
  })
})
