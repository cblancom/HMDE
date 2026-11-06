export type HealthStatus = 'ok' | 'degraded'
export type DatabaseStatus = 'ok' | 'unavailable'

export interface HealthResponse {
  status: HealthStatus
  database: DatabaseStatus
}
