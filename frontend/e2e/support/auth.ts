import { expect, type Page } from '@playwright/test'

export const TOKEN_KEY = 'movie_ranking_token'
export const PASSWORD = 'e2e-password-123'

/** Unique address so specs never depend on each other's accounts. */
export function uniqueEmail(prefix: string): string {
  const suffix = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
  return `${prefix}-${suffix}@example.com`
}

/** Create an account through the public registration form. */
export async function registerViaUi(page: Page, email: string, password = PASSWORD) {
  await page.goto('/register')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password', { exact: true }).fill(password)
  await page.getByLabel('Confirm Password').fill(password)
  await page.getByRole('button', { name: 'Create Account' }).click()
  await expect(page.getByRole('heading', { name: /My Rankings/ })).toBeVisible()
}

export async function readToken(page: Page): Promise<string | null> {
  return page.evaluate((key) => localStorage.getItem(key), TOKEN_KEY)
}
