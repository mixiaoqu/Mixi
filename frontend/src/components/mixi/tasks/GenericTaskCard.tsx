import type { TaskProposal } from '../../../features/mixi/types'
import { Icon } from '../../Icon'

type GenericTaskCardProps = {
  task: TaskProposal
}

function formatDraftValue(value: unknown): string {
  if (value == null || value === '') return '未设置'
  if (Array.isArray(value)) return value.length > 0 ? value.join(', ') : '未设置'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

export default function GenericTaskCard({ task }: GenericTaskCardProps) {
  const draftEntries = Object.entries(task.draft ?? {}).filter(([key]) => key !== 'missing_fields')

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="flex items-start gap-3">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-slate-950 text-white">
          <Icon className="h-4 w-4" name="command" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-bold text-slate-950">{task.title}</p>
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-bold text-slate-500">
              {task.capability}
            </span>
          </div>
          <p className="mt-1 text-xs leading-5 text-slate-600">{task.description}</p>
        </div>
      </div>

      {task.missingFields.length > 0 ? (
        <div className="mt-4 rounded-xl bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-800">
          需要补充：{task.missingFields.join('、')}
        </div>
      ) : null}

      {draftEntries.length > 0 ? (
        <dl className="mt-4 grid gap-2 rounded-xl bg-slate-50 p-3 text-xs sm:grid-cols-2">
          {draftEntries.map(([key, value]) => (
            <div key={key} className="min-w-0">
              <dt className="font-bold text-slate-500">{key}</dt>
              <dd className="mt-0.5 truncate font-semibold text-slate-800">{formatDraftValue(value)}</dd>
            </div>
          ))}
        </dl>
      ) : null}

      <div className="mt-4 flex justify-end border-t border-slate-100 pt-3">
        <button
          className="inline-flex items-center gap-2 rounded-xl bg-slate-950 px-3 py-2 text-xs font-bold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-200"
          disabled
          type="button"
        >
          <Icon className="h-3.5 w-3.5" name="spark" />
          等待能力卡片接入
        </button>
      </div>
    </div>
  )
}
