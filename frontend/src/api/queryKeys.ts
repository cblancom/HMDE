export const queryKeys = {
  health: ['health'] as const,
  taxonomy: ['taxonomy'] as const,
  bands: (params: Record<string, unknown>) => ['bands', params] as const,
  band: (id: string) => ['band', id] as const,
  bandGraph: (id: string) => ['band-graph', id] as const,
  albums: (params: Record<string, unknown>) => ['albums', params] as const,
  album: (id: string) => ['album', id] as const,
  artists: (id: string) => ['artist', id] as const,
  producers: (params: Record<string, unknown>) => ['producers', params] as const,
  producer: (id: string) => ['producer', id] as const,
  search: (q: string, limit: number) => ['search', q, limit] as const,
}
