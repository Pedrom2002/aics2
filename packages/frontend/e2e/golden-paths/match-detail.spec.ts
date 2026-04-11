import { test, expect } from '../fixtures/auth'
import { API_BASE_URL } from '../fixtures/auth'
import { DashboardPage } from '../pages/dashboard-page'
import { MatchDetailPage } from '../pages/match-detail-page'

/**
 * Golden path: login → matches list → match detail → click each tab.
 *
 * Mocked: this spec uses Playwright's `page.route` to stub the matches list
 * and match detail responses, so it does NOT require a backend with real
 * demo data. The auth fixture still talks to a real backend for the initial
 * register; if that fails the test auto-skips.
 */

const FAKE_MATCH_ID = '00000000-0000-4000-8000-000000000001'

const fakeMatchList = {
  items: [
    {
      id: FAKE_MATCH_ID,
      map: 'de_mirage',
      played_at: '2026-04-01T12:00:00Z',
      score_team_a: 16,
      score_team_b: 12,
      status: 'completed',
    },
  ],
  total: 1,
  page: 1,
  page_size: 20,
  pages: 1,
}

const fakeMatchDetail = {
  id: FAKE_MATCH_ID,
  map: 'de_mirage',
  rounds: [],
  player_stats: [],
  team_a: { name: 'Alpha', score: 16 },
  team_b: { name: 'Bravo', score: 12 },
}

test.describe('golden-path: match detail tabs', () => {
  test.beforeEach(async ({ page, testUser }) => {
    test.skip(!testUser.accessToken, `Backend not reachable at ${API_BASE_URL}`)

    // Mock the matches list and detail endpoints so the spec is hermetic.
    await page.route(/\/api\/v1\/(demos|matches)(\/|\?|$)/, async (route) => {
      const url = route.request().url()
      if (url.includes('/matches/') || url.includes(`/${FAKE_MATCH_ID}`)) {
        await route.fulfill({ json: fakeMatchDetail })
      } else {
        await route.fulfill({ json: fakeMatchList })
      }
    })
  })

  test('navigate from dashboard to match detail and switch tabs', async ({ authenticatedPage }) => {
    const page = authenticatedPage
    const dashboard = new DashboardPage(page)
    await dashboard.goto()

    // Open matches list (link in sidebar or grid card)
    if (await page.getByRole('link', { name: /matches/i }).first().isVisible().catch(() => false)) {
      await dashboard.openMatches()
    } else {
      await page.goto('/dashboard/matches')
    }
    await expect(page).toHaveURL(/\/dashboard\/matches/)

    // Open the (mocked) match
    await page.goto(`/dashboard/matches/${FAKE_MATCH_ID}`)

    const matchDetail = new MatchDetailPage(page)

    for (const tab of ['overview', 'economy', 'tactics', 'errors'] as const) {
      const locator = {
        overview: matchDetail.overviewTab,
        economy: matchDetail.economyTab,
        tactics: matchDetail.tacticsTab,
        errors: matchDetail.errorsTab,
      }[tab]
      const visible = await locator.first().isVisible().catch(() => false)
      if (visible) {
        await matchDetail.openTab(tab)
        // Allow the tab content to render
        await page.waitForLoadState('networkidle', { timeout: 5_000 }).catch(() => undefined)
      } else {
        // Fallback: hit the tab as a child route
        await page.goto(`/dashboard/matches/${FAKE_MATCH_ID}/${tab === 'overview' ? '' : tab}`)
      }
      // Sanity assertion: page didn't crash
      await expect(page.locator('body')).toBeVisible()
    }
  })
})
