import { apiFetch } from './auth'

type MixiStreamHandlers = {
  onChunk: (delta: string) => void
  onCompleted?: (message: string) => void
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

export async function streamMixiReply(prompt: string, handlers: MixiStreamHandlers): Promise<void> {
  const response = await apiFetch('/mixi/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt }),
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
      const payload = JSON.parse(parsed.data) as { delta?: string; message?: string; detail?: string }

      if (parsed.event === 'chunk' && payload.delta) {
        handlers.onChunk(payload.delta)
      } else if (parsed.event === 'completed') {
        handlers.onCompleted?.(payload.message ?? '')
      } else if (parsed.event === 'error') {
        throw new Error(payload.detail || 'Mixi 流式输出失败。')
      }
    }

    if (done) break
  }
}
