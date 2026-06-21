import { useEffect, useState, type FormEvent } from 'react'

import { Icon } from '../components/Icon'
import {
  createGitDataSource,
  deleteGitDataSource,
  listGitDataSources,
  testGitConnection,
  type GitAuthType,
  type GitConnectionTestResult,
  type GitDataSource,
} from '../lib/gitDataSources'

const authOptions: Array<{ id: GitAuthType; label: string; icon: 'globe' | 'lock' | 'file' }> = [
  { id: 'public', label: '无需认证', icon: 'globe' },
  { id: 'token', label: 'Access Token', icon: 'lock' },
  { id: 'ssh', label: 'SSH Key', icon: 'file' },
]

export default function DataSourcesPage() {
  const [sources, setSources] = useState<GitDataSource[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [adding, setAdding] = useState(false)

  useEffect(() => {
    let active = true
    listGitDataSources()
      .then((items) => {
        if (active) setSources(items)
      })
      .catch((error: unknown) => {
        if (active) setLoadError(error instanceof Error ? error.message : '无法读取数据源。')
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  async function removeSource(source: GitDataSource) {
    await deleteGitDataSource(source.id)
    setSources((current) => current.filter((item) => item.id !== source.id))
  }

  return (
    <section className="mx-auto max-w-5xl px-4 py-10 sm:px-6 lg:py-14">
      <div className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
        <div className="max-w-2xl">
          <h1 className="text-3xl font-bold tracking-tight text-slate-950">数据源</h1>
          <p className="mt-3 text-sm leading-6 text-slate-600 sm:text-base">
            连接 Git 仓库后，工作日志智能体可以读取提交记录和代码差异。
          </p>
        </div>
        <button
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-bold text-white transition hover:bg-slate-800"
          onClick={() => setAdding(true)}
          type="button"
        >
          <Icon name="plus" className="h-4 w-4" />
          添加 Git 数据源
        </button>
      </div>

      <div className="mt-8">
        {loading ? (
          <div className="flex min-h-44 items-center justify-center text-sm font-semibold text-slate-500">
            <Icon name="loader" className="mr-2 h-4 w-4 animate-spin" />
            正在加载数据源
          </div>
        ) : loadError ? (
          <div className="rounded-xl bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">{loadError}</div>
        ) : sources.length === 0 ? (
          <div className="flex min-h-64 flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-white px-6 text-center">
            <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-slate-100 text-slate-500">
              <Icon name="terminal" className="h-5 w-5" />
            </span>
            <h2 className="mt-4 text-base font-bold text-slate-900">还没有 Git 数据源</h2>
            <p className="mt-2 max-w-md text-sm leading-6 text-slate-500">添加公开或私有仓库，并选择智能体默认读取的分支。</p>
          </div>
        ) : (
          <div className="space-y-3">
            {sources.map((source) => (
              <article key={source.id} className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-5 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex min-w-0 items-start gap-4">
                  <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-slate-950 text-white">
                    <Icon name="terminal" className="h-5 w-5" />
                  </span>
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="truncate font-bold text-slate-950">{source.name}</h2>
                      <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">已连接</span>
                    </div>
                    <p className="mt-1 truncate text-sm text-slate-500">{source.repository_url}</p>
                    <p className="mt-2 flex items-center gap-1.5 text-xs font-semibold text-slate-500">
                      <Icon name="git-branch" className="h-3.5 w-3.5" />
                      {source.default_branch}
                      <span className="text-slate-300">·</span>
                      {authLabel(source.auth_type)}
                    </p>
                  </div>
                </div>
                <button
                  aria-label={`删除 ${source.name}`}
                  className="self-end rounded-lg p-2 text-slate-400 transition hover:bg-rose-50 hover:text-rose-700 sm:self-auto"
                  onClick={() => void removeSource(source)}
                  type="button"
                >
                  <Icon name="trash" className="h-4 w-4" />
                </button>
              </article>
            ))}
          </div>
        )}
      </div>

      {adding && <GitSourceDialog onClose={() => setAdding(false)} onCreated={(source) => { setSources((current) => [source, ...current]); setAdding(false) }} />}
    </section>
  )
}

function GitSourceDialog({ onClose, onCreated }: { onClose: () => void; onCreated: (source: GitDataSource) => void }) {
  const [repositoryUrl, setRepositoryUrl] = useState('')
  const [authType, setAuthType] = useState<GitAuthType>('public')
  const [credential, setCredential] = useState('')
  const [testResult, setTestResult] = useState<GitConnectionTestResult | null>(null)
  const [defaultBranch, setDefaultBranch] = useState('')
  const [status, setStatus] = useState<'idle' | 'testing' | 'saving'>('idle')
  const [error, setError] = useState('')

  useEffect(() => {
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    document.addEventListener('keydown', closeOnEscape)
    return () => {
      document.body.style.overflow = previousOverflow
      document.removeEventListener('keydown', closeOnEscape)
    }
  }, [onClose])

  function resetTest() {
    setTestResult(null)
    setDefaultBranch('')
    setError('')
  }

  const connectionInput = {
    repository_url: repositoryUrl.trim(),
    auth_type: authType,
    ...(authType === 'public' ? {} : { credential }),
  }
  const canTest = Boolean(connectionInput.repository_url && (authType === 'public' || credential.trim()))

  async function handleTest() {
    if (!canTest) return
    setStatus('testing')
    setError('')
    try {
      const result = await testGitConnection(connectionInput)
      setTestResult(result)
      setDefaultBranch(result.default_branch)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : '连接测试失败。')
    } finally {
      setStatus('idle')
    }
  }

  async function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!testResult || !defaultBranch) return
    setStatus('saving')
    setError('')
    try {
      onCreated(await createGitDataSource({ ...connectionInput, default_branch: defaultBranch }))
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : '保存数据源失败。')
      setStatus('idle')
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/35 p-4" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}>
      <form className="max-h-[calc(100vh-2rem)] w-full max-w-xl overflow-y-auto rounded-2xl bg-white" onSubmit={handleSave}>
        <div className="sticky top-0 z-10 flex items-start justify-between border-b border-slate-100 bg-white px-5 py-4 sm:px-6">
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-950 text-white">
              <Icon name="terminal" className="h-5 w-5" />
            </span>
            <div>
              <h2 className="font-bold text-slate-950">添加 Git 数据源</h2>
              <p className="mt-0.5 text-xs font-medium text-slate-500">验证仓库权限并选择默认分支</p>
            </div>
          </div>
          <button aria-label="关闭" className="rounded-lg p-2 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700" onClick={onClose} type="button">
            <Icon name="x" className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-6 p-5 sm:p-6">
          <label className="block">
            <span className="mb-2 block text-sm font-bold text-slate-700">仓库地址</span>
            <input
              autoFocus
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition placeholder:text-slate-500 focus:border-cyan-400 focus:bg-white focus:ring-4 focus:ring-cyan-100"
              onChange={(event) => { setRepositoryUrl(event.target.value); resetTest() }}
              placeholder="https://git.example.com/owner/repository.git"
              type="url"
              value={repositoryUrl}
            />
          </label>

          <fieldset>
            <legend className="mb-2 text-sm font-bold text-slate-700">认证方式</legend>
            <div className="grid gap-2 rounded-xl bg-slate-100 p-1 sm:grid-cols-3">
              {authOptions.map((option) => (
                <button
                  key={option.id}
                  aria-pressed={authType === option.id}
                  className={`flex items-center justify-center gap-2 rounded-lg px-3 py-2.5 text-xs font-bold transition ${
                    authType === option.id ? 'bg-white text-slate-950 shadow-sm' : 'text-slate-500 hover:text-slate-800'
                  }`}
                  onClick={() => { setAuthType(option.id); setCredential(''); resetTest() }}
                  type="button"
                >
                  <Icon name={option.icon} className="h-3.5 w-3.5" />
                  {option.label}
                </button>
              ))}
            </div>
          </fieldset>

          {authType === 'token' && (
            <label className="block">
              <span className="mb-2 block text-sm font-bold text-slate-700">Access Token</span>
              <input
                autoComplete="off"
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition placeholder:text-slate-500 focus:border-cyan-400 focus:bg-white focus:ring-4 focus:ring-cyan-100"
                onChange={(event) => { setCredential(event.target.value); resetTest() }}
                placeholder="输入只读访问令牌"
                type="password"
                value={credential}
              />
            </label>
          )}

          {authType === 'ssh' && (
            <label className="block">
              <span className="mb-2 block text-sm font-bold text-slate-700">SSH 私钥</span>
              <textarea
                className="min-h-28 w-full resize-y rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 font-mono text-xs leading-5 text-slate-900 outline-none transition placeholder:text-slate-500 focus:border-cyan-400 focus:bg-white focus:ring-4 focus:ring-cyan-100"
                onChange={(event) => { setCredential(event.target.value); resetTest() }}
                placeholder="-----BEGIN OPENSSH PRIVATE KEY-----"
                value={credential}
              />
            </label>
          )}

          {!testResult && (
            <button
              className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-slate-100 px-4 py-3 text-sm font-bold text-slate-700 transition hover:bg-slate-200 disabled:cursor-not-allowed disabled:text-slate-400"
              disabled={!canTest || status === 'testing'}
              onClick={() => void handleTest()}
              type="button"
            >
              <Icon name={status === 'testing' ? 'loader' : 'sync'} className={`h-4 w-4 ${status === 'testing' ? 'animate-spin' : ''}`} />
              {status === 'testing' ? '正在验证连接' : '测试连接'}
            </button>
          )}

          {error && <p className="rounded-xl bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700" role="alert">{error}</p>}

          {testResult && (
            <div className="space-y-4 rounded-xl bg-emerald-50 p-4">
              <p className="flex items-center gap-2 text-sm font-bold text-emerald-800">
                <Icon name="check" className="h-4 w-4" />
                已连接到 {testResult.repository_name}
              </p>
              <label className="block">
                <span className="mb-2 flex items-center gap-2 text-sm font-bold text-slate-700">
                  <Icon name="git-branch" className="h-4 w-4 text-emerald-700" />
                  默认分支
                </span>
                <select
                  className="w-full rounded-lg border border-emerald-200 bg-white px-3 py-2.5 text-sm font-semibold text-slate-900 outline-none focus:border-cyan-400 focus:ring-4 focus:ring-cyan-100"
                  onChange={(event) => setDefaultBranch(event.target.value)}
                  value={defaultBranch}
                >
                  {testResult.branches.map((branch) => (
                    <option key={branch}>{branch}</option>
                  ))}
                </select>
              </label>
            </div>
          )}
        </div>

        <div className="sticky bottom-0 flex justify-end gap-3 border-t border-slate-100 bg-white px-5 py-4 sm:px-6">
          <button className="rounded-xl px-4 py-2.5 text-sm font-bold text-slate-600 transition hover:bg-slate-100" onClick={onClose} type="button">
            取消
          </button>
          <button
            className="inline-flex items-center gap-2 rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-bold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400"
            disabled={!testResult || status === 'saving'}
            type="submit"
          >
            {status === 'saving' && <Icon name="loader" className="h-4 w-4 animate-spin" />}
            保存数据源
          </button>
        </div>
      </form>
    </div>
  )
}

function authLabel(authType: GitAuthType) {
  return authOptions.find((option) => option.id === authType)?.label ?? authType
}
