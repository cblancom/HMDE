import { expect, test } from '@playwright/test'

const MISSING_ID = '00000000-0000-0000-0000-000000000000'
const SCOTT_BURNS_ID = '9061ac2c-7579-5904-be6d-d485f014edec'

test('empty states', async ({ page }) => {
  await page.goto('/bands?q=no-such-band')
  await expect(page.getByText('No bands match these filters.')).toBeVisible()

  await page.goto('/albums?q=no-such-album')
  await expect(page.getByText('No albums match these filters.')).toBeVisible()

  await page.goto('/producers?q=no-such-producer')
  await expect(page.getByText('No producers match these filters.')).toBeVisible()

  await page.goto('/search')
  await expect(page.getByText('Type a query to search the archive.')).toBeVisible()

  await page.goto('/search?q=no-such-entity')
  await expect(page.getByText('No matches for “no-such-entity”. Try a broader name.')).toBeVisible()
})

test('not-found states', async ({ page }) => {
  await page.goto(`/bands/${MISSING_ID}`)
  await expect(page.getByText('Band not found.')).toBeVisible()

  await page.goto(`/albums/${MISSING_ID}`)
  await expect(page.getByText('Album not found.')).toBeVisible()

  await page.goto(`/producers/${MISSING_ID}`)
  await expect(page.getByText('Producer not found.')).toBeVisible()

  await page.goto('/no-such-page')
  await expect(page.getByRole('heading', { name: 'Page not found', level: 1 })).toBeVisible()
})

test('API error state retries successfully', async ({ page }) => {
  let fail = true
  await page.route(/\/api\/v1\/bands\?/, async (route) => {
    if (fail) {
      await route.fulfill({ status: 500, contentType: 'application/json', body: '{"detail":"temporary"}' })
      return
    }
    await route.continue()
  })

  await page.goto('/bands')
  await expect(page.getByRole('alert')).toContainText('Could not load bands.')
  fail = false
  await page.getByRole('button', { name: 'Retry' }).click()
  await expect(page.locator('.result-count')).toHaveText('14 bands')
})

test('truncated graph states', async ({ page }) => {
  await page.route(/\/api\/v1\/graph\/producers\?/, async (route) => {
    const response = await route.fetch()
    const body = await response.json()
    body.meta.truncated = true
    await route.fulfill({
      status: response.status(),
      contentType: 'application/json',
      body: JSON.stringify(body),
    })
  })
  await page.route(/\/api\/v1\/producers\/[^/]+\/graph\?/, async (route) => {
    const response = await route.fetch()
    const body = await response.json()
    body.meta.truncated = true
    await route.fulfill({
      status: response.status(),
      contentType: 'application/json',
      body: JSON.stringify(body),
    })
  })

  await page.goto('/graph')
  await expect(page.getByText('This overview is truncated at the server limits. Filters apply only to the loaded network.')).toBeVisible()

  await page.goto(`/producers/${SCOTT_BURNS_ID}/graph`)
  await expect(page.getByText('This graph is truncated at the server limits. Filters apply only to the loaded network.')).toBeVisible()
})

test('reduced motion freezes force layouts', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' })

  await page.goto('/graph')
  await expect(page.locator('.producer-graph .graph-meta')).toContainText('Layout frozen · d3-force')
  await expect(page.getByRole('button', { name: 'Freeze layout' })).toBeDisabled()
  await expect(page.getByRole('button', { name: 'Resume physics' })).toBeEnabled()

  await page.goto(`/producers/${SCOTT_BURNS_ID}/graph`)
  await expect(page.locator('.producer-graph .graph-meta')).toContainText('Layout frozen · d3-force')
  await expect(page.getByRole('button', { name: 'Freeze layout' })).toBeDisabled()
  await expect(page.getByRole('button', { name: 'Resume physics' })).toBeEnabled()
})

test('keyboard navigation reaches navigation, filters, tabs, controls and tables', async ({ page }) => {
  await page.goto('/bands')
  const skipLink = page.getByRole('link', { name: 'Skip to content' })
  await skipLink.focus()
  await page.keyboard.press('Enter')
  await expect(page).toHaveURL(/#main-content$/)

  await page.getByRole('link', { name: 'Albums' }).focus()
  await page.keyboard.press('Enter')
  await expect(page).toHaveURL(/\/albums$/)

  await page.getByLabel('Search albums').focus()
  await page.keyboard.type('Killers')
  await page.keyboard.press('Enter')
  await expect(page.locator('.result-count')).toHaveText('1 album')

  await page.goto('/graph')
  await expect(page.getByTestId('producer-graph-canvas')).toBeVisible()
  await page.getByRole('group', { name: 'Graph view' }).getByRole('button', { name: 'Albums' }).focus()
  await page.keyboard.press('Enter')
  await expect(page).toHaveURL(/view=albums/)

  await page.getByRole('button', { name: 'Index' }).focus()
  await page.keyboard.press('Enter')
  await expect(page.getByRole('complementary', { name: 'Network index' })).toHaveCount(0)

  await page.getByRole('group', { name: 'Force engine' }).getByRole('button', { name: 'CoSE', exact: true }).focus()
  await page.keyboard.press('Enter')
  await expect(page).toHaveURL(/engine=cose/)

  const summary = page.getByText('View the network as tables')
  await summary.focus()
  await page.keyboard.press('Enter')
  await page.keyboard.press('Tab')
  await expect(page.locator('[aria-label="Graph nodes table"]')).toBeFocused()
  await expect(page.getByRole('table', { name: 'Loaded graph nodes' })).toBeVisible()
})
