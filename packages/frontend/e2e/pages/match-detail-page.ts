import type { Locator, Page } from '@playwright/test'

/**
 * POM for /dashboard/matches/[id] and its tab subpages.
 *
 * Tab navigation may be implemented as either Radix tabs (role="tab") or
 * Next.js child routes (/economy, /tactics, /errors). Both are exposed.
 */
export class MatchDetailPage {
  readonly page: Page
  readonly overviewTab: Locator
  readonly economyTab: Locator
  readonly tacticsTab: Locator
  readonly errorsTab: Locator

  constructor(page: Page) {
    this.page = page
    this.overviewTab = page.getByRole('tab', { name: /overview/i }).or(
      page.getByRole('link', { name: /overview/i }),
    )
    this.economyTab = page.getByRole('tab', { name: /economy/i }).or(
      page.getByRole('link', { name: /economy/i }),
    )
    this.tacticsTab = page.getByRole('tab', { name: /tactics/i }).or(
      page.getByRole('link', { name: /tactics/i }),
    )
    this.errorsTab = page.getByRole('tab', { name: /errors/i }).or(
      page.getByRole('link', { name: /errors/i }),
    )
  }

  async goto(matchId: string): Promise<void> {
    await this.page.goto(`/dashboard/matches/${matchId}`)
  }

  async openTab(tab: 'overview' | 'economy' | 'tactics' | 'errors'): Promise<void> {
    const map = {
      overview: this.overviewTab,
      economy: this.economyTab,
      tactics: this.tacticsTab,
      errors: this.errorsTab,
    }
    await map[tab].first().click()
  }
}
