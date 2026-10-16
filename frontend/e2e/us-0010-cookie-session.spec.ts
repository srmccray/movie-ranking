import { expect, test } from '@playwright/test'
import {
  CSRF_COOKIE,
  LEGACY_TOKEN_KEY,
  expectHttpOnlySession,
  registerViaUi,
  uniqueEmail,
} from './support/auth'

// ADR-0013: the session is an httpOnly cookie plus a double-submit CSRF token.
test.describe('Cookie session (ADR-0013, US-0010)', () => {
  test('Scenario: The session token is not readable by page scripts', async ({ page }) => {
    // Given Casey signs in with email and password
    await registerViaUi(page, uniqueEmail('cookie'))

    // When Casey opens the browser console on the rankings page
    // Then document.cookie does not contain the session token, localStorage has
    // no "movie_ranking_token" entry, and the rankings page still loads
    await expectHttpOnlySession(page)
    await expect(page.getByRole('heading', { name: /My Rankings/ })).toBeVisible()

    // The CSRF token is the one cookie scripts are meant to read
    expect(await page.evaluate(() => document.cookie)).toContain(`${CSRF_COOKIE}=`)
  })

  test('the session survives a reload without any stored token', async ({ page }) => {
    await registerViaUi(page, uniqueEmail('reload'))

    await page.reload()

    await expect(page.getByRole('heading', { name: /My Rankings/ })).toBeVisible()
    await expectHttpOnlySession(page)
  })

  test('a stale token left by the old build is removed once', async ({ page }) => {
    await page.addInitScript((key) => {
      if (!sessionStorage.getItem('seeded')) {
        sessionStorage.setItem('seeded', '1')
        localStorage.setItem(key, 'stale-token-from-old-build')
      }
    }, LEGACY_TOKEN_KEY)

    await page.goto('/login')

    await expect(page.getByRole('heading', { name: 'Welcome Back' })).toBeVisible()
    expect(await page.evaluate((k) => localStorage.getItem(k), LEGACY_TOKEN_KEY)).toBeNull()
  })

  test('unsafe requests from the SPA carry X-CSRF-Token; without it the API returns 403', async ({
    page,
  }) => {
    await registerViaUi(page, uniqueEmail('csrf'))
    await page.goto('/settings')

    // When Casey clears all rankings through the UI
    await page.getByRole('button', { name: 'Clear All', exact: true }).click()
    const clearRequest = page.waitForRequest(
      (req) => req.url().endsWith('/api/v1/rankings/all/') && req.method() === 'DELETE',
    )
    const clearResponse = page.waitForResponse(
      (res) => res.url().endsWith('/api/v1/rankings/all/') && res.request().method() === 'DELETE',
    )
    await page.getByRole('button', { name: 'Clear All Rankings' }).click()

    // Then the request carries the CSRF header matching the cookie, and succeeds
    const request = await clearRequest
    const headers = request.headers()
    const cookies = await page.context().cookies()
    const csrf = cookies.find((c) => c.name === CSRF_COOKIE)?.value
    expect(csrf).toBeTruthy()
    expect(headers['x-csrf-token']).toBe(csrf)
    expect(headers['authorization']).toBeUndefined()
    expect((await clearResponse).status()).toBe(204)

    // And the same call without the header (a cross-site forgery) is rejected
    const forged = await page.context().request.delete('/api/v1/rankings/all/')
    expect(forged.status()).toBe(403)
  })

  test('Google sign-in UI never produces a URL containing token=', async ({ page }) => {
    // Given Casey has a session (as the backend callback sets before redirecting)
    await registerViaUi(page, uniqueEmail('google'))
    const urls: string[] = []
    page.on('framenavigated', (frame) => urls.push(frame.url()))
    page.on('request', (req) => urls.push(req.url()))

    // When the browser lands on the callback route the backend redirects to
    await page.goto('/auth/google/callback')

    // Then Casey ends on the rankings page and no URL ever contained a token
    await expect(page.getByRole('heading', { name: /My Rankings/ })).toBeVisible()
    await expect(page).toHaveURL(/\/$/)
    expect(urls.filter((u) => u.includes('token='))).toEqual([])
  })

  test('Google callback with no session shows the error UI, not a token prompt', async ({
    page,
  }) => {
    await page.goto('/auth/google/callback')

    await expect(page.getByText('Invalid Callback')).toBeVisible()
    expect(page.url()).not.toContain('token=')
  })
})
