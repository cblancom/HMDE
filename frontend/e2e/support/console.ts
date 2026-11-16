import type { Page } from '@playwright/test'

export function trackConsoleErrors(page: Page): string[] {
  const errors: string[] = []
  page.on('console', (message) => {
    if (message.type() !== 'error') return
    if (message.text().includes('favicon') || message.location().url.includes('favicon')) return
    errors.push(message.text())
  })
  return errors
}
