import { useEffect, useRef, useState } from 'react'

import { Icon } from './components/Icon'
import MixiTaskConsole from './components/mixi/MixiTaskConsole'
import WorkspaceSidebar from './components/navigation/WorkspaceSidebar'
import {
  createAssistantStreamingMessage,
  createUserTextMessage,
  type MixiMessage,
} from './features/mixi/types'
import { knowledgeBases } from './features/workflows/data'
import { logout, restoreSession, type AuthUser } from './lib/auth'
import { streamMixiReply, type MixiHistoryItem } from './lib/mixi'
import DataSourcesPage from './pages/DataSourcesPage'
import AgentsPage from './pages/AgentsPage'
import KnowledgePage from './pages/KnowledgePage'
import LoginPage from './pages/LoginPage'
import SettingsPage from './pages/SettingsPage'

type View = 'home' | 'agents' | 'knowledge' | 'dataSources' | 'settings'
type PrimaryView = 'home' | 'agents' | 'knowledge' | 'dataSources'

function primaryViewFor(view: View): PrimaryView | null {
  if (view === 'home' || view === 'agents' || view === 'knowledge' || view === 'dataSources') return view
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
  const [mixiMessages, setMixiMessages] = useState<MixiMessage[]>([])
  const [mixiStreaming, setMixiStreaming] = useState(false)

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

  async function handleLogout() {
    setAccountMenuOpen(false)

    try {
      await logout()
    } finally {
      setCurrentUser(null)
      setAuthState('guest')
    }
  }

  function openWorkflowCenter() {
    setActiveView('agents')
  }

  function handOffWorklogToMixi() {
    setActiveView('home')
    void handleMixiTask('帮我生成今天的工作日志')
  }

  function handleNewConversation() {
    setActiveView('home')
    setMixiMessages([])
    setMixiStreaming(false)
    setAccountMenuOpen(false)
  }

  async function handleMixiTask(prompt: string) {
    const trimmedPrompt = prompt.trim()
    if (!trimmedPrompt || mixiStreaming) return
    const history: MixiHistoryItem[] = mixiMessages
      .filter((message) => message.kind === 'text' && message.content?.trim())
      .slice(-8)
      .map((message) => ({
        role: message.role === 'assistant' ? 'assistant' : 'user',
        content: message.content!.trim(),
      }))

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
        onWidget: (widget) => {
          setMixiMessages((current) =>
            current.map((message) =>
              message.id === assistantMessageId
                ? { ...message, kind: 'widget', widget, content: undefined, status: 'done' }
                : message,
            ),
          )
        },
      }, history)
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
              onGenerateWorkLog={handOffWorklogToMixi}
              onOpenDataSources={() => setActiveView('dataSources')}
              onSubmit={handleMixiTask}
              userInitial={currentUser?.display_name?.charAt(0).toUpperCase() || 'U'}
            />
          )}

          {activeView === 'agents' && (
            <AgentsPage
              onHandOffWorklog={handOffWorklogToMixi}
              onOpenDataSources={() => setActiveView('dataSources')}
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
