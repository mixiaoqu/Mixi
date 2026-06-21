import { useEffect, useMemo, useState } from 'react'

import type { WorkflowRunStatus, WorkflowTemplate } from './types'

export function useWorkflowPreview(selectedTemplate: WorkflowTemplate) {
  const [status, setStatus] = useState<WorkflowRunStatus>('idle')
  const [currentStep, setCurrentStep] = useState(-1)
  const [output, setOutput] = useState('')
  const [formData, setFormData] = useState<Record<string, string>>({})
  const [logs, setLogs] = useState<string[]>([])

  useEffect(() => {
    let timer: number | undefined
    let subTimer: number | undefined

    if (status === 'running') {
      if (currentStep < selectedTemplate.nodes.length) {
        const node = selectedTemplate.nodes[currentStep]

        subTimer = window.setTimeout(() => {
          setLogs((prev) => [...prev, `[system] booting agent node: ${node.name}`, `> executing: ${node.name}`, `> task: ${node.description}`])
        }, 100)

        timer = window.setTimeout(() => {
          setLogs((prev) => [...prev, `[success] ${node.name} completed`])
          setCurrentStep((prev) => prev + 1)
        }, 1300)
      } else {
        timer = window.setTimeout(() => {
          setStatus('completed')
          setOutput(
            [
              '工作流执行完成。',
              '',
              `已根据「${selectedTemplate.title}」模板完成本次预览，共经过 ${selectedTemplate.nodes.length} 个节点。`,
              '当前版本仍是本地预览运行器，后续可以替换成真实的 FastAPI + LangGraph 事件流。',
              '',
              '建议下一步：保留本次输入参数、保存运行记录，并在节点详情中展示输入、输出和错误信息。',
            ].join('\n'),
          )
        }, 100)
      }
    }

    return () => {
      window.clearTimeout(timer)
      window.clearTimeout(subTimer)
    }
  }, [currentStep, selectedTemplate, status])

  const requiredInputFilled = useMemo(
    () => Boolean(formData[selectedTemplate.inputs[0]?.id]),
    [formData, selectedTemplate.inputs],
  )

  function resetRun(clearForm = false) {
    setStatus('idle')
    setCurrentStep(-1)
    setOutput('')
    setLogs([])
    if (clearForm) setFormData({})
  }

  function fillDemoData() {
    setFormData(Object.fromEntries(selectedTemplate.inputs.map((input) => [input.id, input.demoValue])))
  }

  function startRun() {
    if (!requiredInputFilled || status === 'running') return
    setStatus('running')
    setCurrentStep(0)
    setOutput('')
    setLogs(['[ok] initializing Agent Platform runtime', `[ok] selected workflow: ${selectedTemplate.id}`])
  }

  function failRunForPreview() {
    if (status !== 'running') return
    setStatus('failed')
    setLogs((prev) => [...prev, '[error] current node returned an empty response', '[hint] retry this node after checking inputs'])
  }

  return {
    status,
    currentStep,
    output,
    formData,
    logs,
    requiredInputFilled,
    setFormData,
    resetRun,
    fillDemoData,
    startRun,
    failRunForPreview,
  }
}
