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
})
