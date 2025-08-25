import { test, expect } from '@playwright/test'

test('homepage loads correctly', async ({ page }) => {
  await page.goto('/')

  // Should redirect to /projects
  await expect(page).toHaveURL('/projects')

  // Should have the app title
  await expect(page.locator('h4')).toContainText('Projects')

  // Should have the navigation
  await expect(page.locator('nav')).toBeVisible()
})
