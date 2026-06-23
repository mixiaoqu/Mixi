import { useEffect, useState } from 'react'

import { Icon } from '../components/Icon'
import WorklogPreview from '../components/mixi/WorklogPreview'
import { getRun, listRuns, type RunDetail, type RunStatus, type RunSummary } from '../lib/runs'

export default function RunsPage() {
  const [runs, setRuns] = useState<RunSummary[]>([])
  const [selectedRunId, setSelectedRunId] = useState('')
  const [selectedRun, setSelectedRun] = useState<RunDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [copied, setCopied] = useState(false)

  async function refreshRuns() {
    setLoading(true)
    setError('')
    try {
      const page = await listRuns()
      setRuns(page.items)
      setSelectedRunId((current) => page.items.some((run) => run.id === current) ? current : page.items[0]?.id || '')
      if (page.items.length === 0) setSelectedRun(null)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : '无法读取运行记录。')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let active = true
    listRuns()
      .then((page) => {
        if (!active) return
        setRuns(page.items)
        setSelectedRunId(page.items[0]?.id || '')
      })
      .catch((caught) => {
        if (active) setError(caught instanceof Error ? caught.message : '无法读取运行记录。')
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    if (!selectedRunId) return

    let active = true
    let timer: number | undefined

    async function loadDetail() {
      try {
        const detail = await getRun(selectedRunId)
        if (!active) return
        setSelectedRun(detail)
        setRuns((current) => current.map((run) => run.id === detail.id ? { ...run, ...detail } : run))
        if (detail.status === 'queued' || detail.status === 'running') {
          timer = window.setTimeout(loadDetail, 2000)
        }
      } catch (caught) {
        if (active) setError(caught instanceof Error ? caught.message : '无法读取运行详情。')
      }
    }

    void loadDetail()
    return () => {
      active = false
      window.clearTimeout(timer)
    }
  }, [selectedRunId])

  const markdown = typeof selectedRun?.output_payload.markdown === 'string'
    ? selectedRun.output_payload.markdown
    : ''

  async function copyResult() {
    if (!markdown) return
    await navigator.clipboard.writeText(markdown)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1600)
  }

  return (
    <section className="min-h-[calc(100vh-4rem)] bg-slate-50 p-4 sm:p-6 lg:p-8">
      <div className="mx-auto max-w-7xl">
        <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-indigo-600">Execution history</p>
            <h1 className="mt-2 text-2xl font-bold tracking-tight text-slate-950">运行记录</h1>
            <p className="mt-1 text-sm text-slate-500">重新打开任务，查看执行步骤和生成结果。</p>
          </div>
          <button
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-sm font-bold text-slate-700 transition hover:bg-slate-50"
            onClick={() => void refreshRuns()}
            type="button"
          >
            <Icon className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} name="refresh" />
            刷新
          </button>
        </header>

        {error ? <p className="mb-4 rounded-xl bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700" role="alert">{error}</p> : null}

        {loading && runs.length === 0 ? (
          <div className="flex min-h-80 items-center justify-center rounded-2xl border border-slate-200 bg-white text-sm font-semibold text-slate-500">
            <Icon className="mr-2 h-4 w-4 animate-spin" name="loader" />
            正在读取运行记录
          </div>
        ) : runs.length === 0 ? (
          <div className="flex min-h-80 flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center">
            <Icon className="h-8 w-8 text-slate-300" name="terminal" />
            <h2 className="mt-4 text-base font-bold text-slate-900">还没有运行记录</h2>
            <p className="mt-1 text-sm text-slate-500">通过 Mixi 执行任务后，记录会出现在这里。</p>
          </div>
        ) : (
          <div className="grid gap-5 lg:grid-cols-[20rem_minmax(0,1fr)]">
            <aside className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
              <div className="border-b border-slate-100 px-4 py-3 text-xs font-bold text-slate-500">最近运行</div>
              <div className="max-h-[calc(100vh-13rem)] overflow-y-auto p-2">
                {runs.map((run) => (
                  <button
                    className={`w-full rounded-xl px-3 py-3 text-left transition ${selectedRunId === run.id ? 'bg-indigo-50 ring-1 ring-indigo-100' : 'hover:bg-slate-50'}`}
                    key={run.id}
                    onClick={() => setSelectedRunId(run.id)}
                    type="button"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <span className="text-sm font-bold text-slate-900">{templateLabel(run.template_key)}</span>
                      <StatusBadge status={run.status} />
                    </div>
                    <p className="mt-2 text-xs text-slate-500">{formatDate(run.created_at)}</p>
                    <p className="mt-1 font-mono text-[11px] text-slate-400">{run.id.slice(0, 8)}</p>
                  </button>
                ))}
              </div>
            </aside>

            <main className="min-w-0 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
              {selectedRun ? (
                <>
                  <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 px-5 py-4">
                    <div>
                      <div className="flex items-center gap-2">
                        <h2 className="text-base font-bold text-slate-950">{templateLabel(selectedRun.template_key)}</h2>
                        <StatusBadge status={selectedRun.status} />
                      </div>
                      <p className="mt-1 text-xs text-slate-500">运行编号 {selectedRun.id}</p>
                    </div>
                    {markdown ? (
                      <button className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-xs font-bold text-slate-700 hover:bg-slate-50" onClick={() => void copyResult()} type="button">
                        <Icon className="h-3.5 w-3.5" name={copied ? 'check' : 'copy'} />
                        {copied ? '已复制' : '复制结果'}
                      </button>
                    ) : null}
                  </div>

                  <div className="border-b border-slate-100 px-5 py-4">
                    <h3 className="text-xs font-bold uppercase tracking-wide text-slate-500">执行步骤</h3>
                    <div className="mt-3 grid gap-2 sm:grid-cols-2">
                      {selectedRun.steps.map((step) => (
                        <div className="flex items-center gap-2 rounded-lg bg-slate-50 px-3 py-2 text-xs" key={step.id}>
                          <StepIcon status={step.status} />
                          <span className="font-semibold text-slate-700">{step.step_name}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {selectedRun.status === 'failed' ? (
                    <p className="m-5 rounded-xl bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">{selectedRun.error_message || '任务执行失败。'}</p>
                  ) : markdown ? (
                    <WorklogPreview markdown={markdown} />
                  ) : (
                    <div className="flex min-h-64 items-center justify-center p-8 text-sm font-semibold text-slate-500">
                      {selectedRun.status === 'running' || selectedRun.status === 'queued' ? '任务仍在执行，详情将自动刷新。' : '本次运行没有可预览的文本结果。'}
                    </div>
                  )}
                </>
              ) : (
                <div className="flex min-h-80 items-center justify-center text-sm font-semibold text-slate-500">正在读取运行详情…</div>
              )}
            </main>
          </div>
        )}
      </div>
    </section>
  )
}

function templateLabel(templateKey: string) {
  return templateKey === 'agent.worklog.generate' ? '工作日志生成' : templateKey
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

function StatusBadge({ status }: { status: RunStatus }) {
  const labels: Record<RunStatus, string> = {
    queued: '等待中',
    running: '运行中',
    succeeded: '已完成',
    failed: '失败',
    cancelled: '已取消',
  }
  const classes: Record<RunStatus, string> = {
    queued: 'bg-slate-100 text-slate-600',
    running: 'bg-indigo-50 text-indigo-700',
    succeeded: 'bg-emerald-50 text-emerald-700',
    failed: 'bg-rose-50 text-rose-700',
    cancelled: 'bg-slate-100 text-slate-500',
  }
  return <span className={`shrink-0 rounded-full px-2 py-1 text-[11px] font-bold ${classes[status]}`}>{labels[status]}</span>
}

function StepIcon({ status }: { status: RunStatus }) {
  if (status === 'running') return <Icon className="h-3.5 w-3.5 animate-spin text-indigo-600" name="loader" />
  if (status === 'succeeded') return <Icon className="h-3.5 w-3.5 text-emerald-600" name="check" />
  if (status === 'failed') return <Icon className="h-3.5 w-3.5 text-rose-600" name="x" />
  return <span className="h-2 w-2 rounded-full bg-slate-300" />
}
