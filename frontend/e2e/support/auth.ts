import { expect, type BrowserContext, type Page } from '@playwright/test'

export const LEGACY_TOKEN_KEY = 'movie_ranking_token'
export const SESSION_COOKIE = 'session'
export const CSRF_COOKIE = 'csrf_token'
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

/** The session cookie as the browser stores it, or undefined when absent. */
export async function getSessionCookie(context: BrowserContext) {
  const cookies = await context.cookies()
  return cookies.find((c) => c.name === SESSION_COOKIE)
}

/**
 * Assert the session lives in an httpOnly cookie that page scripts cannot read
 * (ADR-0013): present in the cookie jar, absent from `document.cookie`, and no
 * token in localStorage.
 */
export async function expectHttpOnlySession(page: Page) {
  const session = await getSessionCookie(page.context())
  expect(session, 'session cookie should exist').toBeDefined()
  expect(session?.httpOnly).toBe(true)

  const visible = await page.evaluate(() => document.cookie)
  expect(visible).not.toContain(`${SESSION_COOKIE}=`)
  expect(visible).not.toContain(session?.value ?? 'unreachable')

  const legacy = await page.evaluate((key) => localStorage.getItem(key), LEGACY_TOKEN_KEY)
  expect(legacy).toBeNull()
}
