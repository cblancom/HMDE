import type { ElementDefinition } from 'cytoscape'

import type {
  ProducerGraphEdge,
  ProducerGraphNode,
  ProducerGraphResponse,
  ProducerGraphView,
} from '../api/producerGraph'

export type GraphRole = 'all' | 'producer' | 'co-producer'

export type GraphFilters = {
  role: GraphRole
  decade: string
  subgenre: string
}

export type GraphTableNode = {
  id: string
  label: string
  type: ProducerGraphNode['type']
  year: number | null
  detail: string
}

export type GraphTableEdge = {
  id: string
  source: string
  target: string
  sourceLabel: string
  targetLabel: string
  role: string
  support: string
  albumCount: number | null
}

export type AdaptedGraph = {
  elements: ElementDefinition[]
  nodes: ProducerGraphNode[]
  edges: ProducerGraphEdge[]
  tableNodes: GraphTableNode[]
  tableEdges: GraphTableEdge[]
  availableDecades: string[]
  availableSubgenres: string[]
  supportsDecade: boolean
  supportsSubgenre: boolean
}

const YEAR_COLORS: Array<[number, string]> = [
  [1960, '#440154'],
  [1970, '#414487'],
  [1980, '#2a788e'],
  [1990, '#22a884'],
  [2000, '#7ad151'],
  [2010, '#c7d64f'],
  [2020, '#fde725'],
]

export function adaptGraph(
  response: ProducerGraphResponse,
  view: ProducerGraphView,
  filters: GraphFilters,
  seedProducerId: string,
): AdaptedGraph {
  validateView(response, view)
  const supportsDecade = view === 'albums'
  const supportsSubgenre = view === 'albums'
  const activeDecade = supportsDecade ? filters.decade : ''
  const activeSubgenre = supportsSubgenre ? filters.subgenre : ''

  const nodeById = new Map(response.nodes.map((node) => [node.id, node]))
  const filteredEdges = response.edges.filter((edge) => {
    if (!matchesRole(edge, filters.role)) return false
    if (!activeDecade && !activeSubgenre) return true
    const target = nodeById.get(edge.target)
    if (!target || target.type !== 'album') return false
    if (activeDecade && decadeOf(target) !== activeDecade) return false
    if (activeSubgenre && !taxonomyCodesOf(target).includes(activeSubgenre)) return false
    return true
  })

  const visibleNodeIds = new Set<string>()
  for (const edge of filteredEdges) {
    visibleNodeIds.add(edge.source)
    visibleNodeIds.add(edge.target)
  }
  if (nodeById.has(seedProducerId)) {
    visibleNodeIds.add(seedProducerId)
  }
  const filteredNodes = response.nodes.filter((node) => visibleNodeIds.has(node.id))

  return {
    elements: [
      ...filteredNodes.map((node) => nodeElement(node)),
      ...filteredEdges.map((edge) => edgeElement(edge)),
    ],
    nodes: filteredNodes,
    edges: filteredEdges,
    tableNodes: filteredNodes.map((node) => tableNode(node)),
    tableEdges: filteredEdges.map((edge) => tableEdge(edge, nodeById)),
    availableDecades: uniqueDecades(response.nodes),
    availableSubgenres: uniqueSubgenres(response.nodes),
    supportsDecade,
    supportsSubgenre,
  }
}

export function yearColor(year: number | null): string {
  if (year === null) return '#66736d'
  if (year <= YEAR_COLORS[0][0]) return YEAR_COLORS[0][1]
  for (let index = 1; index < YEAR_COLORS.length; index += 1) {
    const [stopYear, stopColor] = YEAR_COLORS[index]
    if (year <= stopYear) {
      const [previousYear, previousColor] = YEAR_COLORS[index - 1]
      return interpolateColor(previousColor, stopColor, (year - previousYear) / (stopYear - previousYear))
    }
  }
  return YEAR_COLORS[YEAR_COLORS.length - 1][1]
}

export function nodeYear(node: ProducerGraphNode): number | null {
  const value = node.attributes.year
  return typeof value === 'number' ? value : null
}

export function nodeDetail(node: ProducerGraphNode): string {
  if (node.type === 'album') {
    return [attributeString(node, 'band_name'), nodeYear(node) ?? 'Year unknown'].filter(Boolean).join(', ')
  }
  if (node.type === 'band') return attributeString(node, 'band_type') || 'Artist'
  return attributeString(node, 'artist_type') || 'Producer'
}

function validateView(response: ProducerGraphResponse, view: ProducerGraphView): void {
  const types = new Set(response.nodes.map((node) => node.type))
  if (view === 'albums' && [...types].some((type) => type === 'band')) {
    throw new Error('Album graph contains band nodes')
  }
  if (view === 'bands' && [...types].some((type) => type === 'album')) {
    throw new Error('Band graph contains album nodes')
  }
}

function matchesRole(edge: ProducerGraphEdge, role: GraphRole): boolean {
  if (role === 'all') return true
  if (edge.role === role) return true
  const roleMix = edge.evidence?.role_mix
  return typeof roleMix === 'object' && roleMix !== null && role in roleMix
}

function nodeElement(node: ProducerGraphNode): ElementDefinition {
  const artistType = attributeString(node, 'artist_type')
  const selfProduced = node.attributes.self_produced_albums
  const year = nodeYear(node)
  return {
    group: 'nodes',
    data: {
      id: node.id,
      label: node.label,
      type: node.type,
      kind: node.type === 'producer' ? `producer-${artistType || 'unknown'}` : node.type,
      year,
      color: node.type === 'album' ? yearColor(year) : undefined,
      selfProduced: typeof selfProduced === 'number' && selfProduced > 0,
    },
    classes: [
      `node-${node.type}`,
      node.type === 'producer' ? `producer-${artistType || 'unknown'}` : '',
      node.type === 'album' && year === null ? 'missing-year' : '',
      node.type === 'producer' && typeof selfProduced === 'number' && selfProduced > 0 ? 'self-produced' : '',
    ].filter(Boolean).join(' '),
  }
}

function edgeElement(edge: ProducerGraphEdge): ElementDefinition {
  const support = edge.support_ratio === 1 ? 'full' : edge.support_ratio === null ? 'unknown' : 'partial'
  return {
    group: 'edges',
    data: {
      id: `${edge.source}->${edge.target}:${edge.role}`,
      source: edge.source,
      target: edge.target,
      label: edge.role === 'mixed' ? 'producer' : edge.role,
      role: edge.role,
      weight: edge.weight,
      supportRatio: edge.support_ratio,
      albumCount: edge.album_count,
      evidence: edge.evidence,
    },
    classes: [
      `role-${edge.role}`,
      `support-${support}`,
      edge.layer === 'producer_band' ? 'layer-bands' : 'layer-albums',
    ].join(' '),
  }
}

function tableNode(node: ProducerGraphNode): GraphTableNode {
  return {
    id: node.id,
    label: node.label,
    type: node.type,
    year: nodeYear(node),
    detail: nodeDetail(node),
  }
}

function tableEdge(edge: ProducerGraphEdge, nodeById: Map<string, ProducerGraphNode>): GraphTableEdge {
  const support = edge.support_ratio === null ? 'Unknown' : `${Math.round(edge.support_ratio * 100)}%`
  return {
    id: `${edge.source}->${edge.target}:${edge.role}`,
    source: edge.source,
    target: edge.target,
    sourceLabel: nodeById.get(edge.source)?.label ?? edge.source,
    targetLabel: nodeById.get(edge.target)?.label ?? edge.target,
    role: edge.role,
    support,
    albumCount: edge.album_count,
  }
}

function uniqueDecades(nodes: ProducerGraphNode[]): string[] {
  return [...new Set(nodes.map((node) => attributeString(node, 'decade')).filter(Boolean))].sort()
}

function uniqueSubgenres(nodes: ProducerGraphNode[]): string[] {
  const values = new Set<string>()
  for (const node of nodes) {
    const primary = attributeString(node, 'primary_code')
    if (primary) values.add(primary)
    const secondary = node.attributes.secondary_codes
    if (Array.isArray(secondary)) {
      for (const code of secondary) if (typeof code === 'string') values.add(code)
    }
  }
  return [...values].sort()
}

function decadeOf(node: ProducerGraphNode): string {
  return attributeString(node, 'decade')
}

function taxonomyCodesOf(node: ProducerGraphNode): string[] {
  const codes = [attributeString(node, 'primary_code')].filter(Boolean)
  const secondary = node.attributes.secondary_codes
  if (Array.isArray(secondary)) codes.push(...secondary.filter((code): code is string => typeof code === 'string'))
  return codes
}

function attributeString(node: ProducerGraphNode, key: string): string {
  const value = node.attributes[key]
  return typeof value === 'string' ? value : ''
}

function interpolateColor(from: string, to: string, ratio: number): string {
  const start = hexToRgb(from)
  const end = hexToRgb(to)
  const channel = (left: number, right: number) => Math.round(left + (right - left) * ratio)
  return `#${[channel(start[0], end[0]), channel(start[1], end[1]), channel(start[2], end[2])]
    .map((value) => value.toString(16).padStart(2, '0'))
    .join('')}`
}

function hexToRgb(value: string): [number, number, number] {
  return [
    Number.parseInt(value.slice(1, 3), 16),
    Number.parseInt(value.slice(3, 5), 16),
    Number.parseInt(value.slice(5, 7), 16),
  ]
}
