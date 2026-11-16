import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'

const SCOTT_BURNS_ID = '9061ac2c-7579-5904-be6d-d485f014edec'
const IRON_MAIDEN_ID = '194dcb6d-8bc6-5684-a399-04e8a1a975bc'
const KILLERS_ID = '5a6db9b8-13ac-5193-97af-f8d8bbd26c05'

type RouteCase = {
  name: string
  path: string
  ready: (page: Page) => Promise<void>
}

const ROUTES: RouteCase[] = [
  {
    name: 'band index',
    path: '/bands',
    ready: async (page) => {
      await expect(page.locator('.result-count')).toHaveText('14 bands')
    },
  },
  {
    name: 'band detail',
    path: `/bands/${IRON_MAIDEN_ID}`,
    ready: async (page) => {
      await expect(page.getByTestId('band-graph')).toBeVisible()
    },
  },
  {
    name: 'album index',
    path: '/albums',
    ready: async (page) => {
      await expect(page.locator('.result-count')).toHaveText('41 albums')
    },
  },
  {
    name: 'album detail',
    path: `/albums/${KILLERS_ID}`,
    ready: async (page) => {
      await expect(page.getByRole('table', { name: 'Credits for Killers' })).toBeVisible()
    },
  },
  {
    name: 'producer index',
    path: '/producers',
    ready: async (page) => {
      await expect(page.locator('.result-count')).toHaveText('37 producers')
    },
  },
  {
    name: 'producer detail',
    path: `/producers/${SCOTT_BURNS_ID}`,
    ready: async (page) => {
      await expect(page.getByRole('table', { name: 'Albums by Scott Burns' })).toBeVisible()
    },
  },
  {
    name: 'ego graph',
    path: `/producers/${SCOTT_BURNS_ID}/graph`,
    ready: async (page) => {
      await expect(page.getByTestId('producer-graph-canvas')).toBeVisible()
    },
  },
  {
    name: 'overview graph',
    path: '/graph',
    ready: async (page) => {
      await expect(page.getByTestId('producer-graph-canvas')).toBeVisible()
    },
  },
  {
    name: 'search',
    path: '/search?q=Iron',
    ready: async (page) => {
      await expect(page.getByRole('region', { name: 'Bands' })).toContainText('Iron Maiden')
    },
  },
]

for (const routeCase of ROUTES) {
  test(`axe: ${routeCase.name}`, async ({ page }) => {
    await page.goto(routeCase.path)
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
    await routeCase.ready(page)

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze()
    const blocking = results.violations.filter(
      (violation) => violation.impact === 'critical' || violation.impact === 'serious',
    )
    expect(blocking, JSON.stringify(blocking, null, 2)).toEqual([])
  })
}
