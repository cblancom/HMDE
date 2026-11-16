import { expect, test } from '@playwright/test'

import { trackConsoleErrors } from './support/console'

const SCOTT_BURNS_ID = '9061ac2c-7579-5904-be6d-d485f014edec'
const IRON_MAIDEN_ID = '194dcb6d-8bc6-5684-a399-04e8a1a975bc'
const KILLERS_ID = '5a6db9b8-13ac-5193-97af-f8d8bbd26c05'

test('overview views, panels and accessible tables', async ({ page }) => {
  const errors = trackConsoleErrors(page)
  await page.goto('/graph')

  await expect(page.getByRole('heading', { name: 'Producer network', level: 1 })).toBeVisible()
  await expect(page.locator('.overview-toolbar .graph-meta')).toContainText('42 nodes · 30 edges · 28 producers')
  await expect(page.getByRole('group', { name: 'Graph view' }).getByRole('button', { name: 'Bands' })).toHaveAttribute('aria-pressed', 'true')
  await expect(page.getByTestId('producer-graph-canvas')).toBeVisible()
  await expect(page.getByRole('complementary', { name: 'Network index' })).toBeVisible()
  await expect(page.getByRole('complementary', { name: 'Graph details' })).toContainText('Select a producer, band, album or edge')

  await page.getByText('View the network as tables').click()
  await expect(page.getByRole('table', { name: 'Loaded graph nodes' })).toContainText('Iron Maiden')
  await expect(page.getByRole('table', { name: 'Loaded graph edges' })).toContainText('Scott Burns')

  await page.getByRole('button', { name: 'Index' }).click()
  await expect(page.getByRole('complementary', { name: 'Network index' })).toHaveCount(0)
  await page.getByRole('button', { name: 'Index' }).click()
  await expect(page.getByRole('complementary', { name: 'Network index' })).toBeVisible()

  await page.getByRole('group', { name: 'Graph view' }).getByRole('button', { name: 'Albums' }).click()
  await expect(page).toHaveURL(/view=albums/)
  await expect(page.locator('.overview-toolbar .graph-meta')).toContainText('77 nodes · 59 edges · 37 producers')
  await expect(page.getByRole('button', { name: 'Albums' })).toHaveAttribute('aria-pressed', 'true')

  expect(errors).toEqual([])
})

test('overview filters, layouts and engines', async ({ page }) => {
  const errors = trackConsoleErrors(page)
  await page.goto('/graph')
  const meta = page.locator('.overview-toolbar .graph-meta')

  await page.locator('#overview-producers').selectOption('10')
  await expect(page).toHaveURL(/producers=10/)
  await expect(meta).toContainText('16 nodes · 9 edges · 8 producers')

  await page.getByLabel('Highlight producer').fill('Scott')
  await expect(page.getByText('1 producer matches the highlight.')).toBeVisible()

  await page.locator('#overview-sort').selectOption('name')
  await expect(page).toHaveURL(/sort=name/)
  await expect(meta).toContainText('17 nodes · 10 edges')
  await page.locator('#overview-order').selectOption('asc')
  await expect(page).toHaveURL(/order=asc/)
  await expect(meta).toContainText('15 nodes · 8 edges')

  const isolatedToggle = page.getByLabel('Show isolated producers')
  await isolatedToggle.click()
  await expect(isolatedToggle).not.toBeChecked()
  await expect(page).toHaveURL(/isolated=0/)
  await expect(meta).toContainText('1 isolated producer hidden')

  await page.getByRole('button', { name: 'Reset filters' }).click()
  await expect(page).toHaveURL(/\/graph$/)
  await expect(meta).toContainText('42 nodes · 30 edges · 28 producers')

  await page.locator('#decade-filter').selectOption('1990s')
  await expect(page).toHaveURL(/decade=1990s/)
  await expect(meta).toContainText('20 nodes · 13 edges')
  await page.getByRole('button', { name: 'Reset filters' }).click()
  await expect(meta).toContainText('42 nodes · 30 edges')

  await page.getByRole('group', { name: 'Force engine' }).getByRole('button', { name: 'CoSE', exact: true }).click()
  await expect(page).toHaveURL(/engine=cose/)
  await expect(page.getByTestId('producer-graph-canvas')).toBeVisible()
  await page.getByRole('group', { name: 'Force engine' }).getByRole('button', { name: 'fCoSE', exact: true }).click()
  await expect(page).toHaveURL(/engine=fcose/)
  await expect(page.getByTestId('producer-graph-canvas')).toBeVisible()

  await page.locator('#overview-layout').selectOption('bipartite')
  await expect(page).toHaveURL(/layout=bipartite/)
  await expect(page.locator('.producer-graph .graph-meta')).toContainText('Static layout.')
  await expect(page.getByRole('group', { name: 'Force engine' }).getByRole('button', { name: 'CoSE', exact: true })).toBeDisabled()

  await page.locator('#overview-layout').selectOption('community')
  await expect(page).toHaveURL(/layout=community/)
  await expect(page.locator('.producer-graph .graph-meta')).toContainText('Static layout.')

  await page.locator('#overview-layout').selectOption('force')
  await page.getByRole('group', { name: 'Force engine' }).getByRole('button', { name: 'd3-force', exact: true }).click()
  await expect(page.locator('.producer-graph .graph-meta')).toContainText('d3-force')

  expect(errors).toEqual([])
})

test('overview subgenre filter reflects the seeded corpus', async ({ page }) => {
  const errors = trackConsoleErrors(page)
  await page.goto('/graph')
  await expect(page.getByRole('heading', { name: 'Producer network', level: 1 })).toBeVisible()

  await page.locator('#taxonomy-filter').selectOption('heavy-metal')
  await expect(page).toHaveURL(/subgenre=heavy-metal/)
  await expect(page.getByText('No producers match these filters.')).toBeVisible()

  await page.goto('/graph')
  await expect(page.locator('.overview-toolbar .graph-meta')).toContainText('42 nodes · 30 edges')

  expect(errors).toEqual([])
})

test('overview details for producer, band and album selections', async ({ page }) => {
  const errors = trackConsoleErrors(page)
  await page.goto(`/graph?selected=${SCOTT_BURNS_ID}`)
  const details = page.getByRole('complementary', { name: 'Graph details' })
  await expect(details.getByRole('heading', { name: 'Scott Burns' })).toBeVisible()
  await expect(details.getByText('Producer', { exact: true })).toBeVisible()
  await expect(details.getByRole('link', { name: 'Open producer details' })).toBeVisible()
  await expect(details.getByRole('link', { name: 'Open ego graph' })).toBeVisible()
  await expect(details.getByRole('heading', { name: 'Bands' })).toBeVisible()
  await expect(details.getByRole('link', { name: 'Cannibal Corpse' })).toBeVisible()

  await page.goto(`/graph?selected=${IRON_MAIDEN_ID}`)
  await expect(details.getByRole('heading', { name: 'Iron Maiden' })).toBeVisible()
  await expect(details.getByText('Band', { exact: true })).toBeVisible()
  await expect(details.getByRole('link', { name: 'Killers (1981)' })).toBeVisible()
  await expect(details.getByRole('link', { name: 'Open band details' })).toBeVisible()

  await page.goto(`/graph?view=albums&selected=${KILLERS_ID}`)
  await expect(details.getByRole('heading', { name: 'Killers' })).toBeVisible()
  await expect(details.getByText('Album', { exact: true })).toBeVisible()
  await expect(details.locator('dl').getByText('1981', { exact: true })).toBeVisible()
  await expect(details.locator('dl').getByText('Iron Maiden', { exact: true })).toBeVisible()
  await expect(details.getByRole('link', { name: 'Open album details' })).toBeVisible()
  await expect(details.getByRole('link', { name: 'Open band details' })).toBeVisible()

  expect(errors).toEqual([])
})

test('producer ego graph views, filters, tables and physics controls', async ({ page }) => {
  const errors = trackConsoleErrors(page)
  await page.goto(`/producers/${SCOTT_BURNS_ID}/graph`)

  await expect(page.getByRole('heading', { name: 'Scott Burns', level: 1 })).toBeVisible()
  await expect(page.getByText('Producer bands', { exact: true })).toBeVisible()
  await expect(page.locator('.graph-page > .graph-meta')).toContainText('3 nodes · 2 edges')
  await expect(page.getByTestId('producer-graph-canvas')).toBeVisible()
  await expect(page.locator('.producer-graph .graph-meta')).toContainText('d3-force')
  await expect(page.getByRole('complementary', { name: 'Graph details' })).toContainText('Select a node or edge')

  await page.getByText('View the network as tables').click()
  await expect(page.getByRole('table', { name: 'Loaded graph nodes' })).toContainText('Cannibal Corpse')
  await expect(page.getByRole('table', { name: 'Loaded graph edges' })).toContainText('Scott Burns')

  await page.locator('#graph-limit').selectOption('50')
  await expect(page).toHaveURL(/limit=50/)
  await page.getByRole('group', { name: 'Graph view' }).getByRole('button', { name: 'Albums' }).click()
  await expect(page).toHaveURL(/view=albums/)
  await expect(page.getByText('Producer albums', { exact: true })).toBeVisible()
  await expect(page.locator('.graph-page > .graph-meta')).toContainText('5 nodes · 4 edges')
  await expect(page.locator('#graph-decade')).toBeEnabled()
  await expect(page.locator('#graph-subgenre')).toBeEnabled()
  await page.locator('#graph-role').selectOption('co-producer')
  await expect(page.getByText('No edges match these filters.')).toBeVisible()
  await page.getByRole('button', { name: 'Clear graph filters' }).click()
  await expect(page.locator('.graph-page > .graph-meta')).toContainText('5 nodes · 4 edges')

  await page.getByRole('group', { name: 'Graph view' }).getByRole('button', { name: 'Bands' }).click()
  await expect(page.locator('#graph-decade')).toBeDisabled()
  await expect(page.locator('#graph-subgenre')).toBeDisabled()
  await page.locator('#graph-depth').selectOption('2')
  await expect(page).toHaveURL(/depth=2/)
  await expect(page.locator('.graph-page > .graph-meta')).toContainText('6 nodes · 5 edges')

  await page.getByRole('button', { name: 'Freeze layout' }).click()
  await expect(page.locator('.producer-graph .graph-meta')).toContainText('Layout frozen')
  await expect(page.getByRole('button', { name: 'Resume physics' })).toBeEnabled()
  await page.getByRole('button', { name: 'Resume physics' }).click()
  await expect(page.locator('.producer-graph .graph-meta')).toContainText('Physics running')
  await page.getByRole('button', { name: 'Reheat' }).click()
  await expect(page.locator('.producer-graph .graph-meta')).toContainText('Physics running')

  expect(errors).toEqual([])
})
