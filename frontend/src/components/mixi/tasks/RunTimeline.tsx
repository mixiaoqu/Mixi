import type { RunStepEvent } from '../../../lib/mixi'
import { Icon } from '../../Icon'

type RunTimelineProps = {
  steps: RunStepEvent[]
  emptyLabel?: string
}

export default function RunTimeline({ steps, emptyLabel = '正在启动任务…' }: RunTimelineProps) {
  if (steps.length === 0) {
    return <p className="text-xs font-semibold text-slate-500">{emptyLabel}</p>
  }

  return (
    <>
      {steps.map((step) => (
        <div className="flex items-center gap-2 text-xs" key={step.step_key}>
          <Icon
            className={`h-3.5 w-3.5 ${
              step.status === 'running'
                ? 'animate-spin text-indigo-600'
                : step.status === 'failed'
                  ? 'text-rose-600'
                  : 'text-emerald-600'
            }`}
            name={step.status === 'running' ? 'loader' : step.status === 'failed' ? 'x' : 'check'}
          />
          <span className={step.status === 'running' ? 'font-bold text-slate-800' : 'font-semibold text-slate-600'}>
            {step.step_name}
          </span>
          {step.detail ? <span className="truncate text-slate-400">{step.detail}</span> : null}
        </div>
      ))}
    </>
  )
}
