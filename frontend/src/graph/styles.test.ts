import { describe, expect, it } from 'vitest'

import { graphStyles } from './styles'

type StyleEntry = { selector: string; style: Record<string, unknown> }

const styles = graphStyles as unknown as StyleEntry[]

function styleFor(selector: string): Record<string, unknown> | undefined {
  return styles.find((entry) => entry.selector === selector)?.style
}

describe('graph styles', () => {
  it('shows album titles without requiring selection', () => {
    expect(styleFor('node')?.label).toBe('data(label)')
    expect(styleFor('node.node-album')?.label).toBe('data(label)')
    expect(styleFor('node.node-album')?.['text-background-opacity'] as number).toBeGreaterThan(0)
  })

  it('does not hide album labels when selected', () => {
    expect(styleFor('node.node-album:selected')?.label).not.toBe('')
  })

  it('sizes overview nodes by degree and declutters labels by zoom', () => {
    expect(styleFor('node.overview-node')?.width).toBe('data(size)')
    expect(styleFor('node.overview-node')?.height).toBe('data(size)')
    expect(styleFor('node.overview-node')?.['min-zoomed-font-size']).toBe(12)
    expect(styleFor('node.overview-node.node-band')?.['min-zoomed-font-size']).toBe(0)
    expect(styleFor('node.overview-node:selected')?.['min-zoomed-font-size']).toBe(0)
    expect(styleFor('node.overview-node.search-match')?.['min-zoomed-font-size']).toBe(0)
    expect(styleFor('node.overview-node.isolated-producer')?.opacity).toBe(0.45)
  })
})
