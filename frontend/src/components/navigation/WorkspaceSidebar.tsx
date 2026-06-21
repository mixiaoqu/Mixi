import { Icon, type IconName } from '../Icon'

type SidebarItemId = 'home' | 'agents' | 'knowledge'

type SidebarItem = {
  id: SidebarItemId
  label: string
  icon: IconName
}

type WorkspaceSidebarProps = {
  activeId: SidebarItemId | null
  onChange: (id: SidebarItemId) => void
  onNewConversation: () => void
  onOpenSettings: () => void
  onOpenAccountMenu: () => void
  userInitial: string
}

const items: SidebarItem[] = [
  { id: 'home', label: '对话', icon: 'message-square' },
  { id: 'agents', label: '智能体', icon: 'compass' },
  { id: 'knowledge', label: '知识库', icon: 'book' },
]

export default function WorkspaceSidebar({
  activeId,
  onChange,
  onNewConversation,
  onOpenSettings,
  onOpenAccountMenu,
  userInitial,
}: WorkspaceSidebarProps) {
  return (
    <>
      <aside className="hidden h-screen w-24 shrink-0 border-r border-slate-200/70 bg-white/68 py-6 backdrop-blur-xl md:flex md:flex-col md:items-center">
        <div className="flex flex-col items-center">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-slate-950 text-white shadow-sm">
            <Icon className="h-5 w-5" name="spark" />
          </div>
          <span className="mt-3 text-[11px] font-bold uppercase tracking-[0.18em] text-slate-400">Mixi</span>
        </div>

        <div className="mt-7 flex flex-col items-center gap-4">
          <div className="group relative">
            <button
              className="flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-600 text-white shadow-md shadow-blue-500/20 transition hover:scale-[1.03] hover:bg-blue-700"
              onClick={onNewConversation}
              type="button"
            >
              <Icon className="h-5 w-5" name="plus" />
            </button>

            <div className="pointer-events-none absolute left-16 top-1/2 -translate-y-1/2 whitespace-nowrap rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-medium text-white opacity-0 shadow-md transition-opacity delay-150 group-hover:opacity-100">
              新建对话
            </div>
          </div>
        </div>

        <nav aria-label="工作区入口" className="mt-8 flex flex-1 flex-col items-center gap-4">
          {items.map((item) => {
            const active = item.id === activeId

            return (
              <div key={item.id} className="group relative">
                <button
                  className={`flex h-12 w-12 items-center justify-center rounded-2xl transition ${
                    active
                      ? 'bg-blue-50 text-blue-600 ring-1 ring-blue-100'
                      : 'text-slate-400 hover:bg-slate-100 hover:text-slate-700'
                  }`}
                  onClick={() => onChange(item.id)}
                  type="button"
                >
                  <Icon className="h-5 w-5" name={item.icon} />
                </button>

                <div className="pointer-events-none absolute left-16 top-1/2 -translate-y-1/2 whitespace-nowrap rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-medium text-white opacity-0 shadow-md transition-opacity delay-150 group-hover:opacity-100">
                  {item.label}
                </div>
              </div>
            )
          })}
        </nav>

        <div className="mt-auto flex flex-col items-center gap-4">
          <div className="group relative">
            <button
              className="flex h-12 w-12 items-center justify-center rounded-2xl text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
              onClick={onOpenSettings}
              type="button"
            >
              <Icon className="h-5 w-5" name="settings" />
            </button>

            <div className="pointer-events-none absolute left-16 top-1/2 -translate-y-1/2 whitespace-nowrap rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-medium text-white opacity-0 shadow-md transition-opacity delay-150 group-hover:opacity-100">
              设置
            </div>
          </div>

          <button
            className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-950 text-sm font-bold text-white shadow-sm transition hover:shadow-md"
            onClick={onOpenAccountMenu}
            title="打开账户菜单"
            type="button"
          >
            {userInitial}
          </button>
        </div>
      </aside>

      <div className="border-b border-slate-200/70 bg-white/72 px-4 py-3 backdrop-blur md:hidden">
        <div className="flex items-center gap-2 overflow-x-auto">
          <button
            className="inline-flex shrink-0 items-center gap-2 rounded-full bg-blue-600 px-3 py-2 text-sm font-semibold text-white shadow-sm"
            onClick={onNewConversation}
            type="button"
          >
            <Icon className="h-4 w-4" name="plus" />
            新建对话
          </button>

          <nav aria-label="移动端工作区入口" className="flex items-center gap-2">
            {items.map((item) => {
              const active = item.id === activeId

              return (
                <button
                  key={item.id}
                  className={`inline-flex shrink-0 items-center gap-2 rounded-full px-3 py-2 text-sm font-semibold transition ${
                    active
                      ? 'bg-slate-950 text-white shadow-sm'
                      : 'bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50 hover:text-slate-950'
                  }`}
                  onClick={() => onChange(item.id)}
                  type="button"
                >
                  <Icon className="h-4 w-4" name={item.icon} />
                  {item.label}
                </button>
              )
            })}
          </nav>
        </div>
      </div>
    </>
  )
}
