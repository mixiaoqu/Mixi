import { useEffect, useMemo, useRef, useState } from 'react'

import { Icon } from './components/Icon'
import MixiTaskConsole from './components/mixi/MixiTaskConsole'
import WorkspaceSidebar from './components/navigation/WorkspaceSidebar'
import {
  createAssistantStreamingMessage,
  createUserTextMessage,
  type MixiMessage,
} from './features/mixi/types'
import { knowledgeBases, workflowCategories, workflowTemplates } from './features/workflows/data'
import { useWorkflowPreview } from './features/workflows/useWorkflowPreview'
import type { WorkflowTemplate } from './features/workflows/types'
import { logout, restoreSession, type AuthUser } from './lib/auth'
import { streamMixiReply } from './lib/mixi'
import DataSourcesPage from './pages/DataSourcesPage'
import KnowledgePage from './pages/KnowledgePage'
import LoginPage from './pages/LoginPage'
import SettingsPage from './pages/SettingsPage'
import WorkflowTemplatesPage from './pages/WorkflowTemplatesPage'
import WorkflowWorkspacePage from './pages/WorkflowWorkspacePage'

type View = 'home' | 'agents' | 'workspace' | 'knowledge' | 'dataSources' | 'settings'
type PrimaryView = 'home' | 'agents' | 'knowledge'

function primaryViewFor(view: View): PrimaryView | null {
  if (view === 'workspace') return 'agents'
  if (view === 'home' || view === 'agents' || view === 'knowledge') return view
  return null
}

function createMessageId() {
  return globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

export default function App() {
  const [authState, setAuthState] = useState<'loading' | 'authenticated' | 'guest'>('loading')
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null)
  const [accountMenuOpen, setAccountMenuOpen] = useState(false)
  const accountMenuRef = useRef<HTMLDivElement>(null)
  const [activeView, setActiveView] = useState<View>('home')
  const [selectedTemplate, setSelectedTemplate] = useState<WorkflowTemplate>(workflowTemplates[0])
  const [activeCategory, setActiveCategory] = useState('全部')
  const [searchQuery, setSearchQuery] = useState('')
  const [mixiMessages, setMixiMessages] = useState<MixiMessage[]>([])
  const [mixiStreaming, setMixiStreaming] = useState(false)

  const workflowPreview = useWorkflowPreview(selectedTemplate)

  useEffect(() => {
    let active = true

    restoreSession()
      .then((user) => {
        if (!active) return
        setCurrentUser(user)
        setAuthState(user ? 'authenticated' : 'guest')
      })
      .catch(() => {
        if (active) setAuthState('guest')
      })

    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    if (!accountMenuOpen) return

    function closeOnOutsideClick(event: PointerEvent) {
      if (!accountMenuRef.current?.contains(event.target as Node)) setAccountMenuOpen(false)
    }

    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') setAccountMenuOpen(false)
    }

    document.addEventListener('pointerdown', closeOnOutsideClick)
    document.addEventListener('keydown', closeOnEscape)

    return () => {
      document.removeEventListener('pointerdown', closeOnOutsideClick)
      document.removeEventListener('keydown', closeOnEscape)
    }
  }, [accountMenuOpen])

  const filteredTemplates = useMemo(() => {
    const query = searchQuery.trim().toLowerCase()

    return workflowTemplates.filter((template) => {
      const categoryMatch = activeCategory === '全部' || template.category === activeCategory
      const queryMatch =
        !query ||
        template.title.toLowerCase().includes(query) ||
        template.category.toLowerCase().includes(query) ||
        template.tags.some((tag) => tag.toLowerCase().includes(query))

      return categoryMatch && queryMatch
    })
  }, [activeCategory, searchQuery])

  async function handleLogout() {
    setAccountMenuOpen(false)

    try {
      await logout()
    } finally {
      setCurrentUser(null)
      setAuthState('guest')
    }
  }

  function openTemplate(template: WorkflowTemplate) {
    setSelectedTemplate(template)
    workflowPreview.resetRun(true)
    setActiveView('workspace')
  }

  function openWorkflowCenter() {
    setSearchQuery('')
    setActiveCategory('全部')
    setActiveView('agents')
  }

  function openWorkLog() {
    const workLog = workflowTemplates.find((template) => template.id === 'work-log')
    if (workLog) openTemplate(workLog)
  }

  function handleNewConversation() {
    setActiveView('home')
    setMixiMessages([])
    setMixiStreaming(false)
    setAccountMenuOpen(false)
  }

  async function handleMixiTask(prompt: string) {
    const trimmedPrompt = prompt.trim()
    if (!trimmedPrompt) return

    const userMessage = createUserTextMessage(createMessageId(), trimmedPrompt)
    const assistantMessageId = createMessageId()

    setMixiMessages((current) => [
      ...current,
      userMessage,
      createAssistantStreamingMessage(assistantMessageId),
    ])
    setMixiStreaming(true)

    try {
      await streamMixiReply(trimmedPrompt, {
        onChunk: (delta) => {
          setMixiMessages((current) =>
            current.map((message) =>
              message.id === assistantMessageId
                ? { ...message, content: `${message.content ?? ''}${delta}`, status: 'streaming' }
                : message,
            ),
          )
        },
        onCompleted: (message) => {
          setMixiMessages((current) =>
            current.map((item) =>
              item.id === assistantMessageId
                ? { ...item, content: message || item.content, status: 'done' }
                : item,
            ),
          )
        },
      })
    } catch (error) {
      const detail = error instanceof Error ? error.message : 'Mixi 暂时无法响应，请稍后重试。'

      setMixiMessages((current) =>
        current.map((message) =>
          message.id === assistantMessageId
            ? { ...message, content: detail, status: 'error' }
            : message,
        ),
      )
    } finally {
      setMixiStreaming(false)
    }
  }

  if (authState === 'loading') {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[var(--color-bg)] text-sm font-semibold text-slate-600">
        正在恢复登录状态…
      </main>
    )
  }

  if (authState === 'guest') {
    return (
      <LoginPage
        onLogin={(user) => {
          setCurrentUser(user)
          setAuthState('authenticated')
        }}
      />
    )
  }

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900">
      <div className="flex min-h-screen flex-col md:flex-row">
        <div className="relative">
          <WorkspaceSidebar
            activeId={primaryViewFor(activeView)}
            onChange={(view) => {
              setSearchQuery('')
              setActiveCategory('全部')
              setActiveView(view)
            }}
            onNewConversation={handleNewConversation}
            onOpenSettings={() => setActiveView('settings')}
            onOpenAccountMenu={() => setAccountMenuOpen((open) => !open)}
            userInitial={currentUser?.display_name?.charAt(0).toUpperCase() || 'U'}
          />

          {accountMenuOpen ? (
            <div
              ref={accountMenuRef}
              className="absolute bottom-4 left-24 z-40 hidden w-64 rounded-xl border border-slate-200 bg-white p-2 shadow-sm md:block"
              role="menu"
            >
              <div className="border-b border-slate-100 px-3 py-2.5">
                <p className="truncate text-sm font-bold text-slate-950">{currentUser?.display_name}</p>
                <p className="mt-0.5 truncate text-xs font-medium text-slate-500">{currentUser?.email}</p>
              </div>

              <div className="py-1">
                <button
                  className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm font-semibold text-slate-700 transition hover:bg-slate-100 hover:text-slate-950"
                  onClick={() => {
                    setActiveView('dataSources')
                    setAccountMenuOpen(false)
                  }}
                  role="menuitem"
                  type="button"
                >
                  <Icon className="h-4 w-4 text-slate-400" name="database" />
                  数据源
                </button>

                <button
                  className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm font-semibold text-slate-700 transition hover:bg-slate-100 hover:text-slate-950"
                  onClick={() => {
                    setActiveView('settings')
                    setAccountMenuOpen(false)
                  }}
                  role="menuitem"
                  type="button"
                >
                  <Icon className="h-4 w-4 text-slate-400" name="settings" />
                  设置
                </button>
              </div>

              <button
                className="flex w-full items-center gap-2.5 border-t border-slate-100 px-3 py-2.5 text-left text-sm font-semibold text-rose-700 transition hover:bg-rose-50"
                onClick={handleLogout}
                role="menuitem"
                type="button"
              >
                <Icon className="h-4 w-4" name="logout" />
                退出登录
              </button>
            </div>
          ) : null}
        </div>

        <main className="min-w-0 flex-1">
          <div className="flex items-center justify-end px-4 pt-4 md:hidden">
            <div className="relative" ref={accountMenuRef}>
              <button
                aria-expanded={accountMenuOpen}
                aria-haspopup="menu"
                aria-label="打开账户菜单"
                className="flex h-9 w-9 items-center justify-center rounded-full bg-indigo-50 text-sm font-bold text-indigo-700 ring-1 ring-indigo-100 transition hover:bg-indigo-100"
                onClick={() => setAccountMenuOpen((open) => !open)}
                title={currentUser?.display_name}
                type="button"
              >
                {currentUser?.display_name.charAt(0).toUpperCase() || 'U'}
              </button>

              {accountMenuOpen ? (
                <div className="absolute right-0 top-12 z-40 w-64 rounded-xl border border-slate-200 bg-white p-2 shadow-sm" role="menu">
                  <div className="border-b border-slate-100 px-3 py-2.5">
                    <p className="truncate text-sm font-bold text-slate-950">{currentUser?.display_name}</p>
                    <p className="mt-0.5 truncate text-xs font-medium text-slate-500">{currentUser?.email}</p>
                  </div>

                  <div className="py-1">
                    <button
                      className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm font-semibold text-slate-700 transition hover:bg-slate-100 hover:text-slate-950"
                      onClick={() => {
                        setActiveView('dataSources')
                        setAccountMenuOpen(false)
                      }}
                      role="menuitem"
                      type="button"
                    >
                      <Icon className="h-4 w-4 text-slate-400" name="database" />
                      数据源
                    </button>

                    <button
                      className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm font-semibold text-slate-700 transition hover:bg-slate-100 hover:text-slate-950"
                      onClick={() => {
                        setActiveView('settings')
                        setAccountMenuOpen(false)
                      }}
                      role="menuitem"
                      type="button"
                    >
                      <Icon className="h-4 w-4 text-slate-400" name="settings" />
                      设置
                    </button>
                  </div>

                  <button
                    className="flex w-full items-center gap-2.5 border-t border-slate-100 px-3 py-2.5 text-left text-sm font-semibold text-rose-700 transition hover:bg-rose-50"
                    onClick={handleLogout}
                    role="menuitem"
                    type="button"
                  >
                    <Icon className="h-4 w-4" name="logout" />
                    退出登录
                  </button>
                </div>
              ) : null}
            </div>
          </div>

          {activeView === 'home' && (
            <MixiTaskConsole
              isStreaming={mixiStreaming}
              messages={mixiMessages}
              onBrowseWorkflows={openWorkflowCenter}
              onGenerateWorkLog={openWorkLog}
              onSubmit={handleMixiTask}
              userInitial={currentUser?.display_name?.charAt(0).toUpperCase() || 'U'}
            />
          )}

          {activeView === 'agents' && (
            <WorkflowTemplatesPage
              activeCategory={activeCategory}
              categories={workflowCategories}
              onOpenTemplate={openTemplate}
              onSearchChange={setSearchQuery}
              onSelectCategory={setActiveCategory}
              searchQuery={searchQuery}
              templates={filteredTemplates}
            />
          )}

          {activeView === 'workspace' && (
            <WorkflowWorkspacePage
              currentStep={workflowPreview.currentStep}
              formData={workflowPreview.formData}
              logs={workflowPreview.logs}
              onBack={openWorkflowCenter}
              onFailRunForPreview={workflowPreview.failRunForPreview}
              onFillDemoData={workflowPreview.fillDemoData}
              onFormDataChange={workflowPreview.setFormData}
              onResetRun={() => workflowPreview.resetRun()}
              onStartRun={workflowPreview.startRun}
              output={workflowPreview.output}
              requiredInputFilled={workflowPreview.requiredInputFilled}
              selectedTemplate={selectedTemplate}
              status={workflowPreview.status}
            />
          )}

          {activeView === 'knowledge' && <KnowledgePage knowledgeBases={knowledgeBases} />}
          {activeView === 'dataSources' && <DataSourcesPage />}
          {activeView === 'settings' && currentUser && <SettingsPage user={currentUser} />}
        </main>
      </div>
    </div>
  )
}
