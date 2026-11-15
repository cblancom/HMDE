import { describe, expect, it } from 'vitest'

import {
  DEFAULT_FORCE_ENGINE,
  coseOptions,
  d3ForceOptions,
  fcoseOptions,
  forceEngineOptions,
  isFiniteForceEngine,
  normalizeForceEngine,
} from './forceLayouts'

describe('normalizeForceEngine', () => {
  it('defaults to d3-force and rejects unknown values', () => {
    expect(DEFAULT_FORCE_ENGINE).toBe('d3-force')
    expect(normalizeForceEngine(null)).toBe('d3-force')
    expect(normalizeForceEngine(undefined)).toBe('d3-force')
    expect(normalizeForceEngine('')).toBe('d3-force')
    expect(normalizeForceEngine('nope')).toBe('d3-force')
    expect(normalizeForceEngine('cose')).toBe('cose')
    expect(normalizeForceEngine('fcose')).toBe('fcose')
  })

  it('marks CoSE and fCoSE as finite layouts', () => {
    expect(isFiniteForceEngine('d3-force')).toBe(false)
    expect(isFiniteForceEngine('cose')).toBe(true)
    expect(isFiniteForceEngine('fcose')).toBe(true)
  })
})

describe('force option builders', () => {
  it('keeps the d3-force overview preset', () => {
    const options = d3ForceOptions('overview', 398, 720)
    expect(options).toMatchObject({
      name: 'd3-force',
      infinite: true,
      animate: true,
      fit: false,
      randomize: false,
      manyBodyStrength: -45,
    })
    expect(options.linkDistance).toBeGreaterThanOrEqual(42)
    expect(options.collideRadius({ type: 'producer' })).toBe(8)
    expect(options.collideRadius({ type: 'band' })).toBe(10)
  })

  it('supports randomized reheats for d3-force', () => {
    expect(d3ForceOptions('overview', 100, 720, { randomize: true }).randomize).toBe(true)
  })

  it('builds bounded built-in CoSE options', () => {
    expect(coseOptions()).toMatchObject({
      name: 'cose',
      animate: true,
      fit: false,
      randomize: false,
    })
    expect(coseOptions({ reducedMotion: true }).animate).toBe(false)
    expect(coseOptions({ randomize: true }).randomize).toBe(true)
  })

  it('builds bounded fCoSE options with the required proof quality', () => {
    expect(fcoseOptions()).toMatchObject({
      name: 'fcose',
      animate: true,
      fit: false,
      randomize: false,
      quality: 'proof',
      packComponents: false,
    })
    expect(fcoseOptions({ randomize: true })).toMatchObject({
      randomize: true,
      quality: 'default',
    })
    expect(fcoseOptions({ reducedMotion: true }).animate).toBe(false)
  })

  it('dispatches to the selected engine', () => {
    expect(forceEngineOptions('d3-force', 'overview', 10, 720)).toMatchObject({
      name: 'd3-force',
    })
    expect(forceEngineOptions('cose', 'overview', 10, 720)).toMatchObject({ name: 'cose' })
    expect(forceEngineOptions('fcose', 'overview', 10, 720)).toMatchObject({ name: 'fcose' })
  })
})
