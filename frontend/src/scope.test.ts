import { describe, expect, it } from 'vitest'

const SOURCES = import.meta.glob('/src/**/*.{ts,tsx}', {
  query: '?raw',
  import: 'default',
  eager: true,
}) as Record<string, string>
const PACKAGE_JSON = import.meta.glob('/package.json', {
  query: '?raw',
  import: 'default',
  eager: true,
}) as Record<string, string>

function sourceText(): string {
  return Object.entries(SOURCES)
    .filter(([path]) =>
      !path.endsWith('.test.ts') &&
      !path.endsWith('.test.tsx') &&
      !path.endsWith('schema.d.ts'),
    )
    .map(([, text]) => text)
    .join('\n')
}

describe('E9 scope guards', () => {
  it('does not add Tailwind, Plotly or a component library', () => {
    const packageJson = JSON.parse(Object.values(PACKAGE_JSON)[0]) as {
      dependencies?: Record<string, string>
      devDependencies?: Record<string, string>
    }
    const dependencies = { ...packageJson.dependencies, ...packageJson.devDependencies }
    expect(
      Object.keys(dependencies).filter((name) => /tailwind|plotly|mui|chakra|antd|react-force-graph/i.test(name)),
    ).toEqual([])
    expect(dependencies['cytoscape-d3-force']).toBeDefined()
  })

  it('does not hardcode taxonomy options', () => {
    const text = sourceText()
    expect(text).not.toContain('SUBGENRES')
    expect(text).not.toMatch(/heavy-metal|thrash-metal|death-metal/)
  })

  it('keeps generated types as the API response source', () => {
    for (const [path, text] of Object.entries(SOURCES)) {
      if (path.endsWith('.test.ts') || path.endsWith('.test.tsx')) continue
      if (!path.startsWith('/src/api/') || path.endsWith('schema.d.ts')) continue
      if (/\/(client|queryKeys|health|bands)\.ts$/.test(path)) continue
      expect(text).toContain("from './schema'")
    }
  })
})
