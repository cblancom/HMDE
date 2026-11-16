import { expect, test } from '@playwright/test'

import { trackConsoleErrors } from './support/console'

test('band list, search and filters', async ({ page }) => {
  const errors = trackConsoleErrors(page)
  await page.goto('/bands')

  await expect(page.getByRole('heading', { name: 'Bands', level: 1 })).toBeVisible()
  await expect(page.locator('.result-count')).toHaveText('14 bands')
  await expect(page.getByRole('link', { name: 'Iron Maiden' })).toBeVisible()

  await page.getByLabel('Search bands').fill('Iron')
  await page.locator('form.filters').getByRole('button', { name: 'Search' }).click()
  await expect(page.locator('.result-count')).toHaveText('1 band')
  await expect(page).toHaveURL(/q=Iron/)

  await page.getByRole('button', { name: 'Clear filters' }).click()
  await expect(page.locator('.result-count')).toHaveText('14 bands')
  await page.locator('#taxonomy-filter').selectOption('heavy-metal')
  await expect(page.locator('.result-count')).toHaveText('2 bands')
  await expect(page.getByRole('link', { name: 'Judas Priest' })).toBeVisible()

  await page.getByRole('button', { name: 'Clear filters' }).click()
  await expect(page.locator('.result-count')).toHaveText('14 bands')
  await page.locator('#decade-filter').selectOption('1990s')
  await expect(page.locator('.result-count')).toHaveText('8 bands')
  await expect(page.getByRole('link', { name: 'Mayhem' })).toBeVisible()

  expect(errors).toEqual([])
})

test('band detail and producer graph section', async ({ page }) => {
  const errors = trackConsoleErrors(page)
  await page.goto('/bands')
  await page.getByRole('link', { name: 'Iron Maiden' }).click()

  await expect(page.getByRole('heading', { name: 'Iron Maiden', level: 1 })).toBeVisible()
  await expect(page.getByText('GB', { exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Albums', level: 2 })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Killers' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Producer graph', level: 2 })).toBeVisible()
  await expect(page.getByTestId('band-graph')).toBeVisible()

  expect(errors).toEqual([])
})

test('album list, album detail and producer credits', async ({ page }) => {
  const errors = trackConsoleErrors(page)
  await page.goto('/albums')

  await expect(page.getByRole('heading', { name: 'Albums', level: 1 })).toBeVisible()
  await expect(page.locator('.result-count')).toHaveText('41 albums')
  await page.getByRole('link', { name: 'Killers' }).click()

  await expect(page.getByRole('heading', { name: 'Killers', level: 1 })).toBeVisible()
  await expect(page.locator('dl').getByRole('link', { name: 'Iron Maiden' })).toBeVisible()
  await expect(page.getByRole('table', { name: 'Credits for Killers' })).toBeVisible()
  await page.getByRole('link', { name: 'Martin Birch' }).click()

  await expect(page.getByRole('heading', { name: 'Martin Birch', level: 1 })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Albums', level: 2 })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Bands', level: 2 })).toBeVisible()

  expect(errors).toEqual([])
})

test('producer list, search and detail', async ({ page }) => {
  const errors = trackConsoleErrors(page)
  await page.goto('/producers')

  await expect(page.getByRole('heading', { name: 'Producers', level: 1 })).toBeVisible()
  await expect(page.locator('.result-count')).toHaveText('37 producers')

  await page.getByLabel('Search producers').fill('Scott Burns')
  await page.locator('form.filters').getByRole('button', { name: 'Search' }).click()
  await expect(page.locator('.result-count')).toHaveText('1 producer')
  await page.getByRole('link', { name: 'Scott Burns' }).click()

  await expect(page.getByRole('heading', { name: 'Scott Burns', level: 1 })).toBeVisible()
  await expect(page.getByRole('table', { name: 'Albums by Scott Burns' })).toBeVisible()
  await expect(page.getByRole('table', { name: 'Bands by Scott Burns' })).toBeVisible()

  expect(errors).toEqual([])
})

test('cross-entity search', async ({ page }) => {
  const errors = trackConsoleErrors(page)
  await page.goto('/bands')
  await page.getByLabel('Search the archive').fill('Iron')
  await page.getByLabel('Search the archive').press('Enter')

  await expect(page).toHaveURL(/\/search\?q=Iron/)
  await expect(page.getByRole('heading', { name: 'Search', level: 1 })).toBeVisible()
  await expect(page.getByRole('region', { name: 'Bands' })).toContainText('Iron Maiden')
  await expect(page.getByRole('region', { name: 'Albums' })).toContainText('Iron Maiden')
  await expect(page.getByRole('region', { name: 'Producers' })).toContainText('Iron Maiden')

  expect(errors).toEqual([])
})
