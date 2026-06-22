import { apiFetch } from './auth'

export type MixiHistoryItem = {
  role: 'user' | 'assistant'
  content: string
}

export type WorklogWidgetDraft = {
  data_source_id: string | null
  branch: string | null
  start_at: string | null
  end_at: string | null
  user_prompt: string | null
  non_code_notes: string[]
  missing_fields: string[]
  auto_run: boolean
}

type MixiStreamHandlers = {
  onChunk: (delta: string) => void
  onCompleted?: (message: string) => void
  onWidget?: (widget: WorklogWidget) => void
}

export type WorklogWidget = {
  type: 'worklog_form'
  title: string
  description: string
  draft: WorklogWidgetDraft
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
  handlers: MixiStreamHandlers,
  history: MixiHistoryItem[] = [],
): Promise<void> {
  const response = await apiFetch('/mixi/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, history }),
  })

  if (!response.ok || !response.body) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null
    throw new Error(body?.detail || '请求失败，请稍后重试。')
  }

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
      const payload = JSON.parse(parsed.data) as {
        delta?: string
        message?: string
        detail?: string
        type?: string
        title?: string
        description?: string
        draft?: WorklogWidgetDraft
      }

      if (parsed.event === 'chunk' && payload.delta) {
        handlers.onChunk(payload.delta)
      } else if (parsed.event === 'completed') {
        handlers.onCompleted?.(payload.message ?? '')
      } else if (parsed.event === 'widget' && payload.type === 'worklog_form') {
        handlers.onWidget?.({
          type: 'worklog_form',
          title: payload.title ?? '生成工作日志',
          description: payload.description ?? '补充运行参数后生成工作日志草稿。',
          draft: payload.draft ?? {
            data_source_id: null,
            branch: null,
            start_at: null,
            end_at: null,
            user_prompt: null,
            non_code_notes: [],
            missing_fields: [],
            auto_run: false,
          },
        })
      } else if (parsed.event === 'error') {
        throw new Error(payload.detail || 'Mixi 流式输出失败。')
      }
    }

    if (done) break
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
