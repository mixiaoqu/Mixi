import { useEffect, useState } from 'react'

import { Icon } from '../components/Icon'
import { listGitDataSources } from '../lib/gitDataSources'

type AgentsPageProps = {
  onOpenDataSources: () => void
  onHandOffWorklog: () => void
}

type AgentTab = 'system' | 'custom'

const workflowSteps = [
  { title: '读取 Git 活动', description: '按数据源、分支和时间范围读取提交记录。' },
  { title: '合并工作事项', description: '整理代码成果和手动补充的非代码任务。' },
  { title: '生成日志草稿', description: '输出结构化、可编辑的 Markdown 工作日志。' },
]

export default function AgentsPage({ onOpenDataSources, onHandOffWorklog }: AgentsPageProps) {
  const [activeTab, setActiveTab] = useState<AgentTab>('system')
  const [detailsOpen, setDetailsOpen] = useState(false)
  const [sourceCount, setSourceCount] = useState<number | null>(null)
  const [sourceError, setSourceError] = useState(false)

  useEffect(() => {
    let active = true

    listGitDataSources()
      .then((sources) => {
        if (active) setSourceCount(sources.length)
      })
      .catch(() => {
        if (active) setSourceError(true)
      })

    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    if (!detailsOpen) return

    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') setDetailsOpen(false)
    }

    document.addEventListener('keydown', closeOnEscape)
    return () => {
      document.body.style.overflow = previousOverflow
      document.removeEventListener('keydown', closeOnEscape)
    }
  }, [detailsOpen])

  const hasDataSource = Boolean(sourceCount && sourceCount > 0)

  function handlePrimaryAction() {
    setDetailsOpen(false)
    onHandOffWorklog()
  }

  return (
    <section className="min-h-screen bg-slate-100">
      <header className="border-b border-slate-200/80 bg-slate-100/95 px-4 py-8 sm:px-6 lg:px-10">
        <div className="mx-auto max-w-7xl">
          <h1 className="text-2xl font-bold tracking-tight text-slate-950">智能体</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
            直接使用平台维护的固定流程，或管理你为特定任务配置的智能体。
          </p>

          <div className="mt-6 inline-flex rounded-xl bg-slate-200/70 p-1" role="tablist" aria-label="智能体类型">
            <button
              aria-selected={activeTab === 'system'}
              className={`inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-bold transition duration-200 ${
                activeTab === 'system' ? 'bg-white text-indigo-700 shadow-sm' : 'text-slate-600 hover:text-slate-950'
              }`}
              onClick={() => setActiveTab('system')}
              role="tab"
              type="button"
            >
              <Icon className="h-4 w-4" name="spark" />
              系统智能体
            </button>
            <button
              aria-selected={activeTab === 'custom'}
              className={`inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-bold transition duration-200 ${
                activeTab === 'custom' ? 'bg-white text-indigo-700 shadow-sm' : 'text-slate-600 hover:text-slate-950'
              }`}
              onClick={() => setActiveTab('custom')}
              role="tab"
              type="button"
            >
              <Icon className="h-4 w-4" name="users" />
              我的智能体
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-10">
        {activeTab === 'system' ? (
          <div role="tabpanel">
            <div className="mb-4 flex items-end justify-between gap-4">
              <div>
                <h2 className="text-sm font-bold text-slate-950">平台内置</h2>
                <p className="mt-1 text-xs leading-5 text-slate-500">流程、工具和权限边界由平台维护。</p>
              </div>
              <span className="text-xs font-semibold text-slate-500">1 个智能体</span>
            </div>

            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              <button
                className="group flex min-h-56 flex-col rounded-2xl border border-slate-200 bg-white p-5 text-left transition duration-200 hover:-translate-y-0.5 hover:border-indigo-200 hover:shadow-sm"
                onClick={() => setDetailsOpen(true)}
                type="button"
              >
                <div className="flex items-start justify-between gap-4">
                  <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-indigo-50 text-indigo-700">
                    <Icon className="h-5 w-5" name="file" />
                  </span>
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-bold text-emerald-700">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                    可用
                  </span>
                </div>

                <div className="mt-5 flex items-center gap-2">
                  <h3 className="text-lg font-bold text-slate-950">工作日志 Agent</h3>
                  <Icon className="h-4 w-4 text-indigo-600" name="check" />
                </div>
                <p className="mt-2 text-sm leading-6 text-slate-600">
                  汇总 Git 提交和非代码工作，生成可确认、可编辑的每日工作日志。
                </p>

                <div className="mt-auto flex items-center justify-between border-t border-slate-100 pt-4">
                  <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500">
                    <Icon className="h-3.5 w-3.5" name="git-branch" />
                    Git 只读工具
                  </span>
                  <span className="inline-flex items-center gap-1 text-sm font-bold text-indigo-700">
                    查看详情
                    <Icon className="h-4 w-4 transition-transform group-hover:translate-x-0.5" name="arrow" />
                  </span>
                </div>
              </button>
            </div>
          </div>
        ) : (
          <div className="flex min-h-72 flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-white px-6 text-center" role="tabpanel">
            <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-slate-100 text-slate-500">
              <Icon className="h-5 w-5" name="users" />
            </span>
            <h2 className="mt-4 text-base font-bold text-slate-950">还没有自建智能体</h2>
            <p className="mt-2 max-w-md text-sm leading-6 text-slate-500">
              自建智能体用于配置角色、提示词和可用工具。流程编排能力会与系统智能体保持区分。
            </p>
            <span className="mt-4 rounded-full bg-slate-100 px-3 py-1.5 text-xs font-bold text-slate-500">创建功能准备中</span>
          </div>
        )}
      </div>

      <div
        aria-hidden={!detailsOpen}
        className={`fixed inset-0 z-40 bg-slate-950/25 transition-opacity duration-200 ${detailsOpen ? 'opacity-100' : 'pointer-events-none opacity-0'}`}
        onMouseDown={() => setDetailsOpen(false)}
      />

      <aside
        aria-label="工作日志 Agent 详情"
        aria-modal="true"
        className={`fixed inset-y-0 right-0 z-50 flex w-full max-w-[31rem] flex-col bg-white shadow-xl transition-transform duration-300 ease-out ${
          detailsOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
        role="dialog"
      >
        <header className="flex items-start justify-between gap-4 border-b border-slate-100 bg-slate-50 px-5 py-5 sm:px-7">
          <div className="flex min-w-0 items-start gap-3">
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-700">
              <Icon className="h-5 w-5" name="file" />
            </span>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="font-bold text-slate-950">工作日志 Agent</h2>
                <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-[11px] font-bold text-indigo-700">官方</span>
              </div>
              <p className="mt-1 text-xs font-medium text-slate-500">agent.worklog.generate</p>
            </div>
          </div>
          <button
            aria-label="关闭详情"
            className="rounded-lg p-2 text-slate-400 transition hover:bg-slate-200 hover:text-slate-700"
            onClick={() => setDetailsOpen(false)}
            type="button"
          >
            <Icon className="h-4 w-4" name="x" />
          </button>
        </header>

        <div className="flex-1 overflow-y-auto px-5 py-6 sm:px-7">
          <section>
            <h3 className="flex items-center gap-2 text-sm font-bold text-slate-900">
              <Icon className="h-4 w-4 text-indigo-600" name="spark" />
              能力与执行规则
            </h3>
            <p className="mt-3 text-sm leading-6 text-slate-600">
              读取本次授权范围内的工作记录，先生成草稿，再由用户确认。不会修改仓库、推送代码或自动发布日志。
            </p>

            <ol className="mt-5 space-y-4">
              {workflowSteps.map((step, index) => (
                <li key={step.title} className="flex gap-3">
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-indigo-50 text-xs font-black text-indigo-700">
                    {index + 1}
                  </span>
                  <div>
                    <h4 className="text-sm font-bold text-slate-900">{step.title}</h4>
                    <p className="mt-1 text-xs leading-5 text-slate-500">{step.description}</p>
                  </div>
                </li>
              ))}
            </ol>
          </section>

          <section className="mt-8 border-t border-slate-100 pt-6">
            <h3 className="flex items-center gap-2 text-sm font-bold text-slate-900">
              <Icon className="h-4 w-4 text-indigo-600" name="grid" />
              工具与数据源
            </h3>

            <div className="mt-4 flex items-start gap-3 rounded-xl bg-slate-50 p-4">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-white text-slate-700 ring-1 ring-slate-200">
                <Icon className="h-4 w-4" name="git-branch" />
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-bold text-slate-900">Git 仓库读取</p>
                  <span className="text-xs font-bold text-emerald-700">只读</span>
                </div>
                <p className="mt-1 text-xs leading-5 text-slate-500">执行前选择仓库、分支和时间范围，每次运行单独授权。</p>
              </div>
            </div>

            <p className="mt-3 flex items-center gap-2 text-xs font-semibold text-slate-600">
              {sourceCount === null && !sourceError ? (
                <><Icon className="h-3.5 w-3.5 animate-spin" name="loader" />正在检查数据源</>
              ) : sourceError ? (
                <><Icon className="h-3.5 w-3.5 text-amber-600" name="sync" />暂时无法读取连接状态</>
              ) : hasDataSource ? (
                <><Icon className="h-3.5 w-3.5 text-emerald-600" name="check" />已连接 {sourceCount} 个数据源</>
              ) : (
                <><Icon className="h-3.5 w-3.5 text-amber-600" name="database" />还没有可用数据源</>
              )}
            </p>
          </section>

          <section className="mt-8 border-t border-slate-100 pt-6">
            <h3 className="flex items-center gap-2 text-sm font-bold text-slate-900">
              <Icon className="h-4 w-4 text-indigo-600" name="settings" />
              运行配置
            </h3>
            <dl className="mt-4 grid grid-cols-2 gap-3">
              <div className="rounded-xl bg-slate-50 p-3">
                <dt className="text-xs font-semibold text-slate-500">执行引擎</dt>
                <dd className="mt-1 text-sm font-bold text-slate-800">LangGraph</dd>
              </div>
              <div className="rounded-xl bg-slate-50 p-3">
                <dt className="text-xs font-semibold text-slate-500">输出格式</dt>
                <dd className="mt-1 text-sm font-bold text-slate-800">Markdown 草稿</dd>
              </div>
            </dl>
          </section>
        </div>

        <footer className="flex flex-col-reverse gap-2 border-t border-slate-100 bg-white px-5 py-4 sm:flex-row sm:justify-end sm:px-7">
          <button
            className="rounded-xl px-4 py-2.5 text-sm font-bold text-slate-600 transition hover:bg-slate-100 hover:text-slate-900"
            onClick={onOpenDataSources}
            type="button"
          >
            管理数据源
          </button>
          <button
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-bold text-white transition hover:bg-indigo-700 active:scale-[0.99]"
            onClick={handlePrimaryAction}
            type="button"
          >
            <Icon className="h-4 w-4" name="spark" />
            交给 Mixi
          </button>
        </footer>
      </aside>
    </section>
  )
}
