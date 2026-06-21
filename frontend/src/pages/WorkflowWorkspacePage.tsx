import { Icon } from '../components/Icon'
import type { WorkflowRunStatus, WorkflowTemplate } from '../features/workflows/types'

type WorkflowWorkspacePageProps = {
  selectedTemplate: WorkflowTemplate
  status: WorkflowRunStatus
  currentStep: number
  output: string
  formData: Record<string, string>
  logs: string[]
  requiredInputFilled: boolean
  onBack: () => void
  onFormDataChange: (next: Record<string, string>) => void
  onFillDemoData: () => void
  onStartRun: () => void
  onResetRun: () => void
  onFailRunForPreview: () => void
}

export default function WorkflowWorkspacePage({
  selectedTemplate,
  status,
  currentStep,
  output,
  formData,
  logs,
  requiredInputFilled,
  onBack,
  onFormDataChange,
  onFillDemoData,
  onStartRun,
  onResetRun,
  onFailRunForPreview,
}: WorkflowWorkspacePageProps) {
  return (
    <section className="flex min-h-[calc(100vh-4rem)] flex-col">
      <div className="sticky top-16 z-20 flex h-14 items-center justify-between border-b border-slate-200 bg-white/90 px-4 backdrop-blur sm:px-6">
        <div className="flex min-w-0 items-center gap-2 text-sm font-semibold">
          <button className="inline-flex items-center gap-1 text-slate-500 transition hover:text-slate-900" onClick={onBack} type="button">
            <Icon name="back" className="h-4 w-4" />
            模板
          </button>
          <span className="text-slate-300">/</span>
          <span className="inline-flex min-w-0 items-center gap-2 truncate text-slate-900">
            <Icon name={selectedTemplate.icon} className="h-4 w-4 text-indigo-600" />
            {selectedTemplate.title}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {status === 'running' && (
            <button className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-1.5 text-sm font-bold text-rose-700 transition hover:bg-rose-100" onClick={onFailRunForPreview} type="button">
              模拟失败
            </button>
          )}
          {status !== 'idle' && (
            <button className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-bold text-slate-700 transition hover:bg-slate-50" onClick={onResetRun} type="button">
              清除结果
            </button>
          )}
        </div>
      </div>

      <div className="mx-auto grid w-full max-w-[1440px] flex-1 gap-6 p-4 sm:p-6 lg:grid-cols-[400px_minmax(0,1fr)]">
        <aside className="flex flex-col gap-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="mb-6 flex items-start justify-between gap-4">
              <div>
                <h2 className="flex items-center gap-2 text-base font-bold text-slate-950">
                  <Icon name="database" className="h-5 w-5 text-indigo-600" />
                  任务参数
                </h2>
                <p className="mt-1 text-sm text-slate-500">填写输入后即可启动工作流预览。</p>
              </div>
              <button className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-50 px-3 py-1.5 text-xs font-bold text-indigo-700 transition hover:bg-indigo-100" onClick={onFillDemoData} type="button">
                <Icon name="wand" className="h-3.5 w-3.5" />
                示例数据
              </button>
            </div>

            <div className="space-y-5">
              {selectedTemplate.inputs.map((input) => (
                <label key={input.id} className="block">
                  <span className="mb-2 block text-sm font-bold text-slate-700">{input.label}</span>
                  <textarea
                    className="w-full resize-none rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm leading-6 text-slate-900 outline-none transition placeholder:text-slate-500 focus:border-indigo-400 focus:bg-white focus:ring-4 focus:ring-indigo-100"
                    onChange={(event) => onFormDataChange({ ...formData, [input.id]: event.target.value })}
                    placeholder={input.placeholder}
                    rows={input.rows ?? 3}
                    value={formData[input.id] ?? ''}
                  />
                </label>
              ))}
            </div>

            <div className="mt-6 border-t border-slate-100 pt-5">
              <button
                className={`inline-flex w-full items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-bold transition ${
                  status === 'running' || !requiredInputFilled
                    ? 'cursor-not-allowed border border-slate-200 bg-slate-100 text-slate-400'
                    : 'bg-slate-950 text-white hover:bg-slate-800 active:scale-[0.99]'
                }`}
                disabled={status === 'running' || !requiredInputFilled}
                onClick={onStartRun}
                type="button"
              >
                <Icon name={status === 'running' ? 'loader' : 'play'} className={`h-4 w-4 ${status === 'running' ? 'animate-spin' : ''}`} />
                {status === 'running' ? '工作流运行中' : '开始运行'}
              </button>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h3 className="mb-3 text-sm font-bold text-slate-950">模板信息</h3>
            <p className="text-sm leading-6 text-slate-600">{selectedTemplate.description}</p>
            <div className="mt-4 flex flex-wrap gap-2">
              {selectedTemplate.tags.map((tag) => (
                <span key={tag} className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600">
                  {tag}
                </span>
              ))}
            </div>
          </div>
        </aside>

        <section className="flex min-w-0 flex-col gap-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="mb-5 flex items-center justify-between">
              <h2 className="text-sm font-bold text-slate-950">执行链路</h2>
              <span className={statusBadgeClass(status)}>{statusLabel(status)}</span>
            </div>

            <div className="relative overflow-x-auto pb-1">
              <div className="absolute left-7 right-7 top-4 h-1 rounded-full bg-slate-100" />
              <div className="relative z-10 flex min-w-max justify-between gap-8">
                {selectedTemplate.nodes.map((node, index) => {
                  const isCompleted = currentStep > index || status === 'completed'
                  const isCurrent = status === 'running' && currentStep === index
                  const isFailed = status === 'failed' && currentStep === index

                  return (
                    <div key={node.id} className="flex w-32 flex-col items-center text-center">
                      <span
                        className={`flex h-9 w-9 items-center justify-center rounded-full border-2 bg-white text-xs font-black ring-4 ring-white ${
                          isFailed
                            ? 'border-rose-500 text-rose-600'
                            : isCompleted
                              ? 'border-emerald-500 text-emerald-600'
                              : isCurrent
                                ? 'border-indigo-600 text-indigo-700'
                                : 'border-slate-200 text-slate-300'
                        }`}
                      >
                        {isCompleted ? <Icon name="check" className="h-4 w-4" /> : isCurrent ? <Icon name="loader" className="h-4 w-4 animate-spin" /> : index + 1}
                      </span>
                      <span className="mt-3 text-xs font-bold text-slate-800">{node.name}</span>
                      <span className="mt-1 text-xs leading-5 text-slate-500">{node.description}</span>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>

          <div className="flex min-h-[440px] flex-1 flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
            {status === 'idle' && (
              <div className="flex flex-1 flex-col items-center justify-center p-8 text-center">
                <span className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-100 text-slate-400">
                  <Icon name="terminal" className="h-7 w-7" />
                </span>
                <h3 className="text-base font-bold text-slate-900">等待运行指令</h3>
                <p className="mt-2 max-w-sm text-sm leading-6 text-slate-500">填写左侧参数后开始运行，这里会显示节点日志、失败提示和最终结果。</p>
              </div>
            )}

            {(status === 'running' || status === 'failed') && (
              <div className="flex flex-1 flex-col bg-slate-950 p-5 font-mono text-sm text-slate-300">
                <div className="mb-5 flex items-center justify-between border-b border-slate-800 pb-4">
                  <div className="flex items-center gap-2 text-indigo-300">
                    <Icon name="terminal" className="h-5 w-5" />
                    <span className="font-semibold">System output logs</span>
                  </div>
                  {status === 'failed' && (
                    <button className="inline-flex items-center gap-1 rounded-lg bg-white/10 px-3 py-1.5 text-xs font-bold text-white transition hover:bg-white/15" onClick={onStartRun} type="button">
                      <Icon name="refresh" className="h-3.5 w-3.5" />
                      重试
                    </button>
                  )}
                </div>

                <div className="space-y-3 overflow-y-auto">
                  {logs.map((log, index) => (
                    <div key={`${index}-${log}`} className={logLineClass(log)}>
                      {log}
                    </div>
                  ))}
                  {status === 'running' && (
                    <div className="flex items-center gap-2 pt-2 text-xs text-amber-300">
                      <Icon name="loader" className="h-4 w-4 animate-spin" />
                      Awaiting LangGraph execution event...
                    </div>
                  )}
                </div>
              </div>
            )}

            {status === 'completed' && (
              <div className="flex-1 overflow-y-auto p-6">
                <div className="mb-6 flex flex-col gap-3 border-b border-slate-100 pb-5 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-center gap-3">
                    <span className="flex h-9 w-9 items-center justify-center rounded-full bg-emerald-50 text-emerald-600">
                      <Icon name="check" className="h-5 w-5" />
                    </span>
                    <div>
                      <h2 className="text-lg font-bold text-slate-950">生成结果</h2>
                      <p className="text-sm text-slate-500">当前仍是本地预览输出，后续可以替换成真实运行结果。</p>
                    </div>
                  </div>

                  <div className="flex gap-2">
                    <button className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-bold text-slate-700 transition hover:bg-slate-50" type="button">
                      <Icon name="copy" className="h-4 w-4" />
                      复制
                    </button>
                    <button className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-bold text-white transition hover:bg-indigo-700" type="button">
                      <Icon name="file" className="h-4 w-4" />
                      导出
                    </button>
                  </div>
                </div>

                <p className="whitespace-pre-line text-sm leading-7 text-slate-700">{output}</p>

                <dl className="mt-8 grid gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4 sm:grid-cols-3">
                  <Metric label="Tokens Used" value="3,402" />
                  <Metric label="Duration" value="6.5s" />
                  <Metric label="Engine" value="Local Mock" />
                </dl>
              </div>
            )}
          </div>
        </section>
      </div>
    </section>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-bold uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="mt-1 font-mono text-sm font-bold text-slate-950">{value}</dd>
    </div>
  )
}

function statusLabel(status: WorkflowRunStatus) {
  const labels: Record<WorkflowRunStatus, string> = {
    idle: '等待运行',
    running: '运行中',
    completed: '已完成',
    failed: '运行失败',
  }
  return labels[status]
}

function statusBadgeClass(status: WorkflowRunStatus) {
  const classes: Record<WorkflowRunStatus, string> = {
    idle: 'rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-600',
    running: 'rounded-full bg-indigo-50 px-3 py-1 text-xs font-bold text-indigo-700',
    completed: 'rounded-full bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-700',
    failed: 'rounded-full bg-rose-50 px-3 py-1 text-xs font-bold text-rose-700',
  }
  return classes[status]
}

function logLineClass(log: string) {
  if (log.startsWith('[ok]') || log.startsWith('[success]')) return 'text-emerald-300'
  if (log.startsWith('[error]')) return 'text-rose-300'
  if (log.startsWith('[hint]')) return 'text-amber-300'
  if (log.startsWith('>')) return 'border-l border-slate-700 pl-3 text-slate-400'
  return 'font-semibold text-slate-200'
}
