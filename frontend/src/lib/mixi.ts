import type { TaskProposal } from '../features/mixi/types'
import { apiFetch } from './auth'

export type MixiHistoryItem = {
  role: 'user' | 'assistant'
  content: string
}

export type MixiConversationState = {
  conversation_id: string
  timezone: string
  active_intent: string | null
  awaiting_confirmation: boolean
  missing_fields: string[]
  checkpoint_thread_id: string | null
}

export type WorklogTaskDraft = {
  data_source_id: string | null
  branch: string | null
  start_at: string | null
  end_at: string | null
  user_prompt: string | null
  non_code_notes: string[]
  missing_fields: string[]
  auto_run: boolean
}

export type WorklogTaskProposal = TaskProposal<WorklogTaskDraft> & {
  type: 'worklog'
  capability: 'worklog.generate'
}

export type WorklogGenerateInput = {
  data_source_id: string
  start_at: string
  end_at: string
  branch?: string
  commit_limit: number
  user_prompt?: string
  non_code_notes: string[]
}

export type WorklogGenerateResult = {
  workflow_run_id: string
  title: string
  summary: string
  markdown: string
  branch: string
  commit_count: number
}

export type RunStepEvent = {
  step_key: string
  step_name: string
  status: 'running' | 'succeeded' | 'failed'
  detail?: string
}

export type MixiStreamEvent =
  | { type: 'conversation.state'; state: MixiConversationState }
  | { type: 'message.delta'; delta: string }
  | { type: 'message.completed'; message: string }
  | { type: 'task.proposed'; task: WorklogTaskProposal }
  | { type: 'run.started'; run_id: string; capability: string }
  | { type: 'run.step'; step: RunStepEvent }
  | { type: 'artifact.created'; artifact: WorklogGenerateResult }
  | { type: 'run.failed'; run_id?: string; detail: string }

type StreamEventHandler = (event: MixiStreamEvent) => void

function parseSseEvent(block: string): { event: string; data: string } | null {
  const lines = block.split('\n').map((line) => line.trim()).filter(Boolean)
  if (lines.length === 0) return null

  const eventLine = lines.find((line) => line.startsWith('event:'))
  const dataLine = lines.find((line) => line.startsWith('data:'))
  if (!eventLine || !dataLine) return null

  return {
    event: eventLine.slice('event:'.length).trim(),
    data: dataLine.slice('data:'.length).trim(),
  }
}

export async function streamMixiReply(
  prompt: string,
  onEvent: StreamEventHandler,
  state: MixiConversationState,
  history: MixiHistoryItem[] = [],
): Promise<void> {
  const response = await apiFetch('/mixi/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, history, state }),
  })

  if (!response.ok || !response.body) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null
    throw new Error(body?.detail || '请求失败，请稍后重试。')
  }

  await consumeEventStream(response, onEvent)
}

export async function streamWorklogRun(input: WorklogGenerateInput, onEvent: StreamEventHandler): Promise<void> {
  const response = await apiFetch('/mixi/worklog/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })

  if (!response.ok || !response.body) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null
    throw new Error(body?.detail || '工作日志生成失败，请稍后重试。')
  }

  await consumeEventStream(response, onEvent)
}

async function consumeEventStream(response: Response, onEvent: StreamEventHandler): Promise<void> {
  if (!response.body) throw new Error('流式响应不可用。')

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done })

    const blocks = buffer.split('\n\n')
    buffer = blocks.pop() ?? ''

    for (const block of blocks) {
      const parsed = parseSseEvent(block)
      if (!parsed) continue
      const payload = JSON.parse(parsed.data) as Record<string, unknown>
      const event = toMixiStreamEvent(parsed.event, payload)
      onEvent(event)
    }

    if (done) break
  }
}

function toMixiStreamEvent(event: string, payload: Record<string, unknown>): MixiStreamEvent {
  if (event === 'conversation.state') return { type: event, state: payload as MixiConversationState }
  if (event === 'message.delta') return { type: event, delta: String(payload.delta ?? '') }
  if (event === 'message.completed') return { type: event, message: String(payload.message ?? '') }
  if (event === 'task.proposed') {
    const draft = (payload.draft ?? emptyWorklogDraft()) as WorklogTaskDraft
    return {
      type: event,
      task: {
        type: 'worklog',
        capability: 'worklog.generate',
        title: String(payload.title ?? '生成工作日志'),
        description: String(payload.description ?? '补充运行参数后生成工作日志草稿。'),
        draft,
        missingFields: draft.missing_fields,
        confirmationRequired: true,
        status: 'proposed',
      },
    }
  }
  if (event === 'run.started') {
    return {
      type: event,
      run_id: String(payload.run_id ?? ''),
      capability: String(payload.capability ?? ''),
    }
  }
  if (event === 'run.step') return { type: event, step: payload as RunStepEvent }
  if (event === 'artifact.created') {
    return { type: event, artifact: payload.artifact as WorklogGenerateResult }
  }
  if (event === 'run.failed' || event === 'stream.error') {
    return {
      type: 'run.failed',
      run_id: typeof payload.run_id === 'string' ? payload.run_id : undefined,
      detail: String(payload.detail ?? '任务执行失败，请稍后重试。'),
    }
  }
  throw new Error(`无法识别的流式事件：${event}`)
}

export function createMixiConversationState(): MixiConversationState {
  return {
    conversation_id: globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
    active_intent: null,
    awaiting_confirmation: false,
    missing_fields: [],
    checkpoint_thread_id: null,
  }
}

function emptyWorklogDraft(): WorklogTaskDraft {
  return {
    data_source_id: null,
    branch: null,
    start_at: null,
    end_at: null,
    user_prompt: null,
    non_code_notes: [],
    missing_fields: [],
    auto_run: false,
  }
}

export async function generateWorklog(input: WorklogGenerateInput): Promise<WorklogGenerateResult> {
  const response = await apiFetch('/mixi/worklog', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })

  if (response.ok) return response.json() as Promise<WorklogGenerateResult>

  const body = (await response.json().catch(() => null)) as { detail?: string } | null
  throw new Error(body?.detail || '工作日志生成失败，请稍后重试。')
}
