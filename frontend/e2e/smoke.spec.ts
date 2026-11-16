import { expect, test } from '@playwright/test'

test('page shell loads', async ({ page }) => {
  await page.goto('/bands')

  await expect(page.getByRole('heading', { name: 'Bands', level: 1 })).toBeVisible()
  await expect(page.getByRole('navigation', { name: 'Primary' })).toBeVisible()
})
