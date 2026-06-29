export type MixiMessageRole = 'user' | 'assistant' | 'system'

export type MixiMessageKind = 'text' | 'task' | 'artifact'

export type MixiMessageStatus = 'pending' | 'streaming' | 'done' | 'error'

export type CapabilityId = string

export type TaskProposal<TDraft = Record<string, unknown>> = {
  id?: string
  capability: CapabilityId
  title: string
  description: string
  draft: TDraft
  missingFields: string[]
  confirmationRequired: boolean
  status?: 'proposed' | 'ready' | 'running' | 'done' | 'failed'
  type?: string
}

export type TaskArtifact<TPayload = Record<string, unknown>> = {
  id: string
  capability: CapabilityId
  artifactType: string
  title: string
  summary?: string
  payload: TPayload
}

export type MixiMessage = {
  id: string
  role: MixiMessageRole
  kind: MixiMessageKind
  status: MixiMessageStatus
  content?: string
  task?: TaskProposal
  artifact?: TaskArtifact
}

export function createUserTextMessage(id: string, content: string): MixiMessage {
  return {
    id,
    role: 'user',
    kind: 'text',
    status: 'done',
    content,
  }
}

export function createAssistantStreamingMessage(id: string): MixiMessage {
  return {
    id,
    role: 'assistant',
    kind: 'text',
    status: 'streaming',
    content: '',
  }
}
