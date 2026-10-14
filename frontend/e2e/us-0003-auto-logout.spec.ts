import { expect, test } from '@playwright/test'
import { PASSWORD, TOKEN_KEY, readToken, registerViaUi, uniqueEmail } from './support/auth'

// A structurally valid JWT whose exp is in the past. The backend rejects it
// with 401 (its signature does not verify either), which is exactly what the
// client sees for an expired session.
const EXPIRED_TOKEN =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.' +
  'eyJzdWIiOiIwMDAwMDAwMC0wMDAwLTAwMDAtMDAwMC0wMDAwMDAwMDAwMDAiLCJleHAiOjk0NjY4NDgwMH0.' +
  'ZXhwaXJlZC1zaWduYXR1cmU'

test.describe('US-0003: Automatically log out on expired session', () => {
  test('Scenario: Expired token redirects to login', async ({ page }) => {
    // Given Casey has an expired token stored in the browser
    await page.addInitScript(
      ([key, token]) => localStorage.setItem(key, token),
      [TOKEN_KEY, EXPIRED_TOKEN],
    )

    // When Casey opens the rankings page and an API call returns 401
    const unauthorized = page.waitForResponse(
      (res) => res.url().includes('/api/v1/rankings') && res.status() === 401,
    )
    await page.goto('/')
    await unauthorized

    // Then Casey is redirected to "/login"
    await expect(page).toHaveURL(/\/login$/)
    await expect(page.getByRole('heading', { name: 'Welcome Back' })).toBeVisible()

    // And the token is removed from localStorage
    expect(await readToken(page)).toBeNull()
  })

  test('Scenario: Failed login still shows an error', async ({ page }) => {
    // Given an account exists and Casey is on the login page
    const email = uniqueEmail('us0003')
    await registerViaUi(page, email)
    await page.getByRole('button', { name: 'Logout' }).click()
    await expect(page).toHaveURL(/\/login$/)

    // When Casey submits invalid credentials and the API returns 401
    await page.getByLabel('Email').fill(email)
    await page.getByLabel('Password').fill(`${PASSWORD}-wrong`)
    const unauthorized = page.waitForResponse(
      (res) => res.url().includes('/api/v1/auth/login') && res.status() === 401,
    )
    await page.getByRole('button', { name: 'Sign In', exact: true }).click()
    await unauthorized

    // Then an error message is shown on the login form
    await expect(page.getByRole('alert')).toContainText('Invalid email or password')
    await expect(page).toHaveURL(/\/login$/)
  })
})
