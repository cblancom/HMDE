import type cytoscape from 'cytoscape'

export type GraphVariant = 'ego' | 'overview'
export type ForceEngine = 'd3-force' | 'cose' | 'fcose'

export const DEFAULT_FORCE_ENGINE: ForceEngine = 'd3-force'

export const FORCE_ENGINES: ReadonlyArray<{ value: ForceEngine; label: string }> = [
  { value: 'd3-force', label: 'd3-force' },
  { value: 'cose', label: 'CoSE' },
  { value: 'fcose', label: 'fCoSE' },
]

export function normalizeForceEngine(value: string | null | undefined): ForceEngine {
  return value === 'cose' || value === 'fcose' ? value : DEFAULT_FORCE_ENGINE
}

export function isFiniteForceEngine(engine: ForceEngine): boolean {
  return engine !== 'd3-force'
}

type ForceLayoutSettings = {
  randomize?: boolean
  reducedMotion?: boolean
}

function collideRadiusFor(
  variant: GraphVariant,
  node: { type?: string },
): number {
  if (variant === 'overview') {
    if (node.type === 'band') return 10
    if (node.type === 'album') return 7
    return 8
  }
  if (node.type === 'band') return 34
  if (node.type === 'album') return 28
  return 22
}

function linkDistanceFor(
  variant: GraphVariant,
  nodeCount: number,
  canvasHeight: number,
): number {
  if (variant === 'overview') {
    const desired = Math.max(42, Math.min(90, 44 + nodeCount / 40))
    return Math.max(30, Math.min(desired, canvasHeight / 6))
  }
  const desired = Math.max(180, Math.min(300, 70 + nodeCount * 11))
  return Math.max(120, Math.min(desired, canvasHeight / 2 - 60))
}

export function d3ForceOptions(
  variant: GraphVariant,
  nodeCount: number,
  canvasHeight: number,
  { randomize = false }: ForceLayoutSettings = {},
) {
  const shared = {
    name: 'd3-force',
    infinite: true,
    fixedAfterDragging: false,
    ungrabifyWhileSimulating: false,
    animate: true,
    fit: false,
    padding: 40,
    randomize,
    alpha: 1,
    alphaMin: 0.001,
    linkId: (node: { id: string }) => node.id,
    linkDistance: linkDistanceFor(variant, nodeCount, canvasHeight),
    collideRadius: (node: { type?: string }) => collideRadiusFor(variant, node),
  }
  if (variant === 'overview') {
    return {
      ...shared,
      alphaDecay: 0.035,
      velocityDecay: 0.55,
      collideStrength: 0.6,
      collideIterations: 1,
      manyBodyStrength: -45,
      manyBodyTheta: 0.9,
      manyBodyDistanceMin: 8,
    }
  }
  return {
    ...shared,
    alphaDecay: 0.0228,
    velocityDecay: 0.4,
    collideStrength: 0.9,
    collideIterations: 2,
    manyBodyStrength: -320,
  }
}

export function coseOptions({
  randomize = false,
  reducedMotion = false,
}: ForceLayoutSettings = {}) {
  return {
    name: 'cose',
    animate: !reducedMotion,
    fit: false,
    padding: 40,
    randomize,
    nodeRepulsion: 4500,
    idealEdgeLength: 50,
    edgeElasticity: 32,
    nestingFactor: 0.1,
    gravity: 0.25,
    numIter: 1000,
  }
}

export function fcoseOptions({
  randomize = false,
  reducedMotion = false,
}: ForceLayoutSettings = {}) {
  return {
    name: 'fcose',
    animate: !reducedMotion,
    fit: false,
    padding: 40,
    randomize,
    quality: randomize ? 'default' : 'proof',
    nodeRepulsion: 4500,
    idealEdgeLength: 50,
    edgeElasticity: 0.45,
    nestingFactor: 0.1,
    gravity: 0.25,
    numIter: 2500,
    packComponents: false,
  }
}

export function forceEngineOptions(
  engine: ForceEngine,
  variant: GraphVariant,
  nodeCount: number,
  canvasHeight: number,
  settings: ForceLayoutSettings = {},
): cytoscape.LayoutOptions {
  if (engine === 'cose') {
    return coseOptions(settings) as unknown as cytoscape.LayoutOptions
  }
  if (engine === 'fcose') {
    return fcoseOptions(settings) as unknown as cytoscape.LayoutOptions
  }
  return d3ForceOptions(variant, nodeCount, canvasHeight, settings) as unknown as cytoscape.LayoutOptions
}
