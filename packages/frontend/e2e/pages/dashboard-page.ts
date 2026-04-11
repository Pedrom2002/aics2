import type { Locator, Page } from '@playwright/test'

export class DashboardPage {
  readonly page: Page
  readonly sidebar: Locator
  readonly logoutButton: Locator

  constructor(page: Page) {
    this.page = page
    this.sidebar = page.locator('[data-testid="sidebar"], nav[aria-label*="sidebar" i]').first()
    this.logoutButton = page
      .getByRole('button', { name: /log\s*out|sign\s*out/i })
      .or(page.locator('[data-testid="logout-button"]'))
  }

  async goto(): Promise<void> {
    await this.page.goto('/dashboard')
  }

  async openMatches(): Promise<void> {
    await this.page
      .getByRole('link', { name: /matches/i })
      .first()
      .click()
  }

  async openScout(): Promise<void> {
    await this.page
      .getByRole('link', { name: /scout/i })
      .first()
      .click()
  }

  async openPlayers(): Promise<void> {
    await this.page
      .getByRole('link', { name: /players/i })
      .first()
      .click()
  }

  async logout(): Promise<void> {
    await this.logoutButton.first().click()
  }
}
