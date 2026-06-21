export type MixiMessageRole = 'user' | 'assistant' | 'system'

export type MixiMessageKind = 'text' | 'widget'

export type MixiMessageStatus = 'pending' | 'streaming' | 'done' | 'error'

export type MixiWidgetType = 'worklog_form'

export type MixiMessageWidget =
  | {
      type: 'worklog_form'
      title: string
      description: string
    }

export type MixiMessage = {
  id: string
  role: MixiMessageRole
  kind: MixiMessageKind
  status: MixiMessageStatus
  content?: string
  widget?: MixiMessageWidget
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
