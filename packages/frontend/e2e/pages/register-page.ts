import type { Locator, Page } from '@playwright/test'

export class RegisterPage {
  readonly page: Page
  readonly emailInput: Locator
  readonly passwordInput: Locator
  readonly orgNameInput: Locator
  readonly displayNameInput: Locator
  readonly submitButton: Locator

  constructor(page: Page) {
    this.page = page
    this.emailInput = page.locator('input[type="email"]')
    this.passwordInput = page.locator('input[type="password"]').first()
    this.orgNameInput = page.locator('input[name="org_name"], input[name="orgName"]')
    this.displayNameInput = page.locator('input[name="display_name"], input[name="displayName"]')
    this.submitButton = page.locator('button[type="submit"]')
  }

  async goto(): Promise<void> {
    await this.page.goto('/register')
  }

  async register(opts: {
    email: string
    password: string
    orgName?: string
    displayName?: string
  }): Promise<void> {
    await this.emailInput.fill(opts.email)
    await this.passwordInput.fill(opts.password)
    if (opts.orgName && (await this.orgNameInput.count())) {
      await this.orgNameInput.first().fill(opts.orgName)
    }
    if (opts.displayName && (await this.displayNameInput.count())) {
      await this.displayNameInput.first().fill(opts.displayName)
    }
    await this.submitButton.click()
  }
}
