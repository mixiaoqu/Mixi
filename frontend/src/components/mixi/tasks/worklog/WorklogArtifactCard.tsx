import { useState } from 'react'

import type { TaskArtifact } from '../../../../features/mixi/types'
import { Icon } from '../../../Icon'
import WorklogPreview from './WorklogArtifactPreview'

type WorklogArtifactCardProps = {
  artifact: TaskArtifact
}

export default function WorklogArtifactCard({ artifact }: WorklogArtifactCardProps) {
  const [copied, setCopied] = useState(false)
  const markdown = typeof artifact.payload.markdown === 'string' ? artifact.payload.markdown : ''

  async function copyResult() {
    if (!markdown) return
    await navigator.clipboard.writeText(markdown)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1600)
  }

  return (
    <section className="overflow-hidden rounded-xl border border-emerald-200 bg-white">
      <header className="flex flex-wrap items-start justify-between gap-3 border-b border-emerald-100 bg-emerald-50 px-4 py-3">
        <div>
          <p className="flex items-center gap-2 text-sm font-bold text-emerald-900">
            <Icon className="h-4 w-4" name="check" />
            {artifact.title || '工作日志已生成'}
          </p>
          {artifact.summary ? <p className="mt-1 text-xs leading-5 text-emerald-800">{artifact.summary}</p> : null}
        </div>
        <button
          className="inline-flex items-center gap-1.5 rounded-lg bg-white px-3 py-2 text-xs font-bold text-slate-700 ring-1 ring-emerald-200 transition hover:bg-emerald-50 disabled:text-slate-400"
          disabled={!markdown}
          onClick={() => void copyResult()}
          type="button"
        >
          <Icon className="h-3.5 w-3.5" name={copied ? 'check' : 'copy'} />
          {copied ? '已复制' : '复制结果'}
        </button>
      </header>
      {markdown ? (
        <WorklogPreview markdown={markdown} />
      ) : (
        <p className="px-4 py-6 text-sm text-slate-500">产物已生成，但没有可预览的 Markdown 内容。</p>
      )}
    </section>
  )
}
