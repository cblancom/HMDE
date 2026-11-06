import type { HealthResponse } from '../types/health'
import { getJson } from './client'

export function getHealth(): Promise<HealthResponse> {
  return getJson<HealthResponse>('/health')
}
