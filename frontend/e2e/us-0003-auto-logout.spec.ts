import { expect, test } from '@playwright/test'
import { PASSWORD, getSessionCookie, registerViaUi, uniqueEmail } from './support/auth'

// An httpOnly session cookie whose value is not a valid JWT. The backend rejects
// it with 401, which is exactly what the client sees for an expired session.
const EXPIRED_SESSION = 'expired-or-invalid'

test.describe('US-0003: Automatically log out on expired session', () => {
  test('Scenario: Expired session redirects to login', async ({ page }) => {
    // Given Casey has an expired session cookie in the browser
    await page.context().addCookies([
      {
        name: 'session',
        value: EXPIRED_SESSION,
        domain: 'localhost',
        path: '/api',
        httpOnly: true,
        secure: false,
        sameSite: 'Lax',
      },
    ])
    expect(await getSessionCookie(page.context())).toBeDefined()

    // When Casey opens the rankings page and the session check returns 401
    const unauthorized = page.waitForResponse(
      (res) => res.url().includes('/api/v1/auth/me/') && res.status() === 401,
    )
    await page.goto('/')
    await unauthorized

    // Then Casey is redirected to "/login"
    await expect(page).toHaveURL(/\/login$/)
    await expect(page.getByRole('heading', { name: 'Welcome Back' })).toBeVisible()

    // And the session cookie is gone (the server expired it)
    await expect.poll(async () => getSessionCookie(page.context())).toBeUndefined()
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
