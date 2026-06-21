import type { IconName } from '../../components/Icon'

export type WorkflowRunStatus = 'idle' | 'running' | 'completed' | 'failed'

export type WorkflowInput = {
  id: string
  label: string
  placeholder: string
  demoValue: string
  rows?: number
}

export type WorkflowNode = {
  id: string
  name: string
  description: string
}

export type WorkflowTemplate = {
  id: string
  title: string
  description: string
  icon: IconName
  category: string
  uses: string
  tags: string[]
  tone: 'blue' | 'indigo' | 'rose' | 'emerald'
  inputs: WorkflowInput[]
  nodes: WorkflowNode[]
}

export type KnowledgeBase = {
  id: number
  name: string
  docCount: number
  size: string
  updated: string
  status: 'ready' | 'syncing'
}
