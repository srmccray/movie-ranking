import { expect, test } from '@playwright/test'
import { PASSWORD, expectHttpOnlySession, getSessionCookie, registerViaUi, uniqueEmail } from './support/auth'

// Smoke coverage for the authentication journey. No TMDB access is needed.
test.describe('Smoke: authentication journey', () => {
  test('anonymous visitor to a protected route is sent to login', async ({ page }) => {
    await page.goto('/analytics')
    await expect(page).toHaveURL(/\/login$/)
    await expect(page.getByRole('heading', { name: 'Welcome Back' })).toBeVisible()
  })

  test('register lands in the app, logout returns to login, login returns to the app', async ({
    page,
  }) => {
    const email = uniqueEmail('smoke')

    await registerViaUi(page, email)
    await expect(page).toHaveURL(/\/$/)
    await expectHttpOnlySession(page)

    await page.getByRole('button', { name: 'Logout' }).click()
    await expect(page).toHaveURL(/\/login$/)
    expect(await getSessionCookie(page.context())).toBeUndefined()

    await page.getByLabel('Email').fill(email)
    await page.getByLabel('Password').fill(PASSWORD)
    await page.getByRole('button', { name: 'Sign In', exact: true }).click()
    await expect(page.getByRole('heading', { name: /My Rankings/ })).toBeVisible()
  })
})
