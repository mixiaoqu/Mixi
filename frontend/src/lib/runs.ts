import { apiFetch } from './auth'

export type RunStatus = 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled'

export type RunSummary = {
  id: string
  workspace_id: string
  agent_id: string | null
  template_key: string
  trigger_source: string
  status: RunStatus
  error_message: string | null
  started_at: string | null
  finished_at: string | null
  created_at: string
}

export type RunStep = {
  id: string
  sequence_no: number
  step_key: string
  step_name: string
  status: RunStatus
  output_payload: Record<string, unknown>
  error_message: string | null
  started_at: string | null
  finished_at: string | null
}

export type RunDetail = RunSummary & {
  input_payload: Record<string, unknown>
  output_payload: Record<string, unknown>
  steps: RunStep[]
}

type RunPage = {
  items: RunSummary[]
  total: number
  limit: number
  offset: number
}

export async function listRuns(limit = 50): Promise<RunPage> {
  const response = await apiFetch(`/runs?limit=${limit}`)
  if (response.ok) return response.json() as Promise<RunPage>
  throw new Error('无法读取运行记录。')
}

export async function getRun(runId: string): Promise<RunDetail> {
  const response = await apiFetch(`/runs/${runId}`)
  if (response.ok) return response.json() as Promise<RunDetail>
  throw new Error('无法读取运行详情。')
}
