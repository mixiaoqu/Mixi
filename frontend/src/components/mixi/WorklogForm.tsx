import { useEffect, useEffectEvent, useMemo, useRef, useState, type FormEvent } from 'react'

import type { WorklogWidgetDraft } from '../../lib/mixi'
import { generateWorklog, type WorklogGenerateResult } from '../../lib/mixi'
import { listGitDataSources, type GitDataSource } from '../../lib/gitDataSources'
import { Icon } from '../Icon'

type WorklogFormProps = {
  title?: string
  description: string
  draft?: WorklogWidgetDraft
  onOpenDataSources: () => void
}

function localDateValue(date = new Date()) {
  const offset = date.getTimezoneOffset() * 60_000
  return new Date(date.getTime() - offset).toISOString().slice(0, 10)
}

function dateValueFromIso(value: string | null | undefined) {
  if (!value) return localDateValue()
  return value.slice(0, 10)
}

function notesValueFromDraft(draft?: WorklogWidgetDraft) {
  return draft?.non_code_notes?.join('\n') ?? ''
}

export default function WorklogForm({ title, description, draft, onOpenDataSources }: WorklogFormProps) {
  const [sources, setSources] = useState<GitDataSource[]>([])
  const [sourceId, setSourceId] = useState(draft?.data_source_id ?? '')
  const [date, setDate] = useState(dateValueFromIso(draft?.start_at))
  const [notes, setNotes] = useState(notesValueFromDraft(draft))
  const [status, setStatus] = useState<'loading' | 'idle' | 'running' | 'done'>('loading')
  const [error, setError] = useState('')
  const [result, setResult] = useState<WorklogGenerateResult | null>(null)
  const [draftMarkdown, setDraftMarkdown] = useState('')
  const [copied, setCopied] = useState(false)
  const autoSubmittedRef = useRef(false)

  useEffect(() => {
    let active = true
    listGitDataSources()
      .then((items) => {
        if (!active) return
        setSources(items)
        setSourceId((current) => current || items[0]?.id || '')
        setStatus('idle')
      })
      .catch((caught) => {
        if (!active) return
        setError(caught instanceof Error ? caught.message : '无法读取 Git 数据源。')
        setStatus('idle')
      })
    return () => {
      active = false
    }
  }, [])

  const selectedSource = useMemo(() => sources.find((source) => source.id === sourceId), [sourceId, sources])

  async function runWorklog() {
    if (!selectedSource || status === 'running') return

    setStatus('running')
    setError('')

    const start = draft?.start_at ? new Date(draft.start_at) : new Date(`${date}T00:00:00`)
    const end = draft?.end_at
      ? new Date(draft.end_at)
      : date === localDateValue()
        ? new Date()
        : new Date(`${date}T23:59:59`)

    try {
      const response = await generateWorklog({
        data_source_id: selectedSource.id,
        start_at: start.toISOString(),
        end_at: end.toISOString(),
        branch: draft?.branch ?? selectedSource.default_branch,
        commit_limit: 50,
        user_prompt: draft?.user_prompt ?? `整理 ${date} 的工作进展`,
        non_code_notes: notes.split('\n').map((note) => note.trim()).filter(Boolean),
      })
      setResult(response)
      setDraftMarkdown(response.markdown)
      setStatus('done')
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : '工作日志生成失败，请稍后重试。')
      setStatus('idle')
    }
  }

  const triggerAutoRun = useEffectEvent(() => {
    autoSubmittedRef.current = true
    void runWorklog()
  })

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    await runWorklog()
  }

  useEffect(() => {
    if (!draft?.auto_run || autoSubmittedRef.current || status !== 'idle' || !selectedSource) return
    if (draft.missing_fields.length > 0) return
    const frame = window.requestAnimationFrame(() => {
      triggerAutoRun()
    })
    return () => window.cancelAnimationFrame(frame)
  }, [draft, selectedSource, status])

  async function copyDraft() {
    await navigator.clipboard.writeText(draftMarkdown)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1600)
  }

  if (result) {
    return (
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 bg-emerald-50/60 px-4 py-3">
          <div>
            <p className="flex items-center gap-2 text-sm font-bold text-emerald-800">
              <Icon className="h-4 w-4" name="check" />
              工作日志已生成
            </p>
            <p className="mt-1 text-xs text-emerald-700">读取 {result.commit_count} 条提交，分支 {result.branch}</p>
          </div>
          <button
            className="inline-flex items-center gap-1.5 rounded-lg bg-white px-3 py-2 text-xs font-bold text-slate-700 ring-1 ring-slate-200 transition hover:bg-slate-50"
            onClick={() => void copyDraft()}
            type="button"
          >
            <Icon className="h-3.5 w-3.5" name={copied ? 'check' : 'copy'} />
            {copied ? '已复制' : '复制日志'}
          </button>
        </div>
        <textarea
          aria-label="工作日志草稿"
          className="min-h-80 w-full resize-y bg-white p-4 font-mono text-sm leading-6 text-slate-700 outline-none focus:bg-slate-50"
          onChange={(event) => setDraftMarkdown(event.target.value)}
          value={draftMarkdown}
        />
      </div>
    )
  }

  return (
    <form className="rounded-2xl border border-slate-200 bg-slate-50 p-4" onSubmit={(event) => void handleSubmit(event)}>
      <div className="flex items-start gap-3">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-700">
          <Icon className="h-4 w-4" name="file" />
        </span>
        <div>
          <p className="text-sm font-bold text-slate-950">{title ?? '生成工作日志'}</p>
          <p className="mt-1 text-xs leading-5 text-slate-600">{description}</p>
        </div>
      </div>

      {status === 'loading' ? (
        <div className="mt-5 flex items-center gap-2 py-4 text-sm font-semibold text-slate-500">
          <Icon className="h-4 w-4 animate-spin" name="loader" />
          正在读取可用数据源
        </div>
      ) : sources.length === 0 ? (
        <div className="mt-5 rounded-xl bg-white p-4 ring-1 ring-slate-200">
          <p className="text-sm font-bold text-slate-900">需要先连接 Git 数据源</p>
          <p className="mt-1 text-xs leading-5 text-slate-500">连接后，Mixi 只会把本次选择的仓库授权给工作日志 Agent。</p>
          <button
            className="mt-3 inline-flex items-center gap-2 rounded-lg bg-slate-950 px-3 py-2 text-xs font-bold text-white transition hover:bg-slate-800"
            onClick={onOpenDataSources}
            type="button"
          >
            <Icon className="h-3.5 w-3.5" name="plus" />
            连接 Git 数据源
          </button>
        </div>
      ) : (
        <div className="mt-5 grid gap-4">
          <label>
            <span className="mb-2 block text-xs font-bold text-slate-700">Git 数据源</span>
            <select
              className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm font-semibold text-slate-900 outline-none focus:border-indigo-400 focus:ring-4 focus:ring-indigo-100"
              onChange={(event) => setSourceId(event.target.value)}
              value={sourceId}
            >
              {sources.map((source) => (
                <option key={source.id} value={source.id}>{source.name} · {source.default_branch}</option>
              ))}
            </select>
          </label>

          <label>
            <span className="mb-2 block text-xs font-bold text-slate-700">日志日期</span>
            <input
              className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm font-semibold text-slate-900 outline-none focus:border-indigo-400 focus:ring-4 focus:ring-indigo-100"
              max={localDateValue()}
              onChange={(event) => setDate(event.target.value)}
              type="date"
              value={date}
            />
          </label>

          <label>
            <span className="mb-2 block text-xs font-bold text-slate-700">非代码工作（选填，每行一项）</span>
            <textarea
              className="min-h-24 w-full resize-y rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm leading-6 text-slate-900 outline-none placeholder:text-slate-500 focus:border-indigo-400 focus:ring-4 focus:ring-indigo-100"
              onChange={(event) => setNotes(event.target.value)}
              placeholder="例如：参加需求评审并确认接口范围"
              value={notes}
            />
          </label>

          {error ? <p className="rounded-lg bg-rose-50 px-3 py-2 text-xs font-semibold text-rose-700" role="alert">{error}</p> : null}

          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 pt-4">
            <p className="text-xs font-semibold text-slate-500">运行前仅授权所选仓库与日期范围</p>
            <button
              className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-bold text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-slate-300"
              disabled={!date || status === 'running'}
              type="submit"
            >
              <Icon className={`h-4 w-4 ${status === 'running' ? 'animate-spin' : ''}`} name={status === 'running' ? 'loader' : 'spark'} />
              {status === 'running' ? 'Agent 正在生成' : draft?.auto_run ? '重新生成' : '确认并生成'}
            </button>
          </div>
        </div>
      )}

      {error && sources.length === 0 ? <p className="mt-3 text-xs font-semibold text-rose-700" role="alert">{error}</p> : null}
    </form>
  )
}
