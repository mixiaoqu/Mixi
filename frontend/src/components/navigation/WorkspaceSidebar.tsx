import { Icon, type IconName } from '../Icon'

type SidebarItemId = 'home' | 'agents' | 'knowledge' | 'dataSources'

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
  { id: 'home', label: '对话中心', icon: 'message-square' },
  { id: 'agents', label: '智能体', icon: 'cpu' },
  { id: 'knowledge', label: '知识库', icon: 'library' },
  { id: 'dataSources', label: '数据源', icon: 'database' },
]

function Tooltip({ children }: { children: string }) {
  return (
    <span
      className="pointer-events-none absolute left-[3.75rem] top-1/2 z-50 -translate-y-1/2 translate-x-1 whitespace-nowrap rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-medium text-white opacity-0 shadow-sm transition-[opacity,transform] duration-150 delay-200 group-hover:translate-x-0 group-hover:opacity-100 group-focus-within:translate-x-0 group-focus-within:opacity-100"
      role="tooltip"
    >
      {children}
    </span>
  )
}

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
      <aside className="sticky top-0 hidden h-screen w-[4.75rem] shrink-0 flex-col items-center border-r border-slate-200/70 bg-[#fafafa]/90 py-6 backdrop-blur-xl md:flex">
        <div className="group relative">
          <button
            aria-label="新建对话"
            className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-950 text-white shadow-sm transition duration-200 hover:scale-[1.04] hover:bg-slate-800 active:scale-[0.98]"
            onClick={onNewConversation}
            type="button"
          >
            <Icon className="h-5 w-5" name="spark" />
          </button>
          <Tooltip>新建对话</Tooltip>
        </div>

        <nav aria-label="主导航" className="mt-8 flex w-full flex-1 flex-col items-center gap-4 px-3">
          {items.map((item) => {
            const active = item.id === activeId

            return (
              <div key={item.id} className="group relative">
                <button
                  aria-current={active ? 'page' : undefined}
                  aria-label={item.label}
                  className={`flex h-12 w-12 items-center justify-center rounded-[0.875rem] transition duration-200 active:scale-[0.97] ${
                    active
                      ? 'bg-blue-600 text-white shadow-sm ring-1 ring-blue-600 ring-offset-2 ring-offset-[#fafafa]'
                      : 'text-slate-400 hover:bg-blue-50 hover:text-blue-600'
                  }`}
                  onClick={() => onChange(item.id)}
                  type="button"
                >
                  <Icon className="h-[1.375rem] w-[1.375rem]" name={item.icon} />
                </button>
                <Tooltip>{item.label}</Tooltip>
              </div>
            )
          })}
        </nav>

        <div className="mt-auto flex flex-col items-center gap-5">
          <div className="group relative">
            <button
              aria-label="设置"
              className="flex h-12 w-12 items-center justify-center rounded-[0.875rem] text-slate-400 transition duration-200 hover:bg-slate-100 hover:text-slate-700 active:scale-[0.97]"
              onClick={onOpenSettings}
              type="button"
            >
              <Icon className="h-[1.375rem] w-[1.375rem]" name="settings" />
            </button>
            <Tooltip>设置</Tooltip>
          </div>

          <div className="group relative">
            <button
              aria-label="打开账户菜单"
              className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-950 text-sm font-bold text-white shadow-sm transition duration-200 hover:bg-slate-800 hover:shadow-md active:scale-[0.97]"
              onClick={onOpenAccountMenu}
              type="button"
            >
              {userInitial}
            </button>
            <Tooltip>账户</Tooltip>
          </div>
        </div>
      </aside>

      <div className="border-b border-slate-200/70 bg-[#fafafa]/90 px-3 py-2.5 backdrop-blur-xl md:hidden">
        <div className="flex items-center gap-2 overflow-x-auto">
          <button
            aria-label="新建对话"
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-slate-950 text-white shadow-sm"
            onClick={onNewConversation}
            type="button"
          >
            <Icon className="h-4 w-4" name="spark" />
          </button>

          <nav aria-label="主导航" className="flex items-center gap-1.5">
            {items.map((item) => {
              const active = item.id === activeId

              return (
                <button
                  key={item.id}
                  aria-current={active ? 'page' : undefined}
                  className={`inline-flex shrink-0 items-center gap-2 rounded-xl px-3 py-2 text-sm font-semibold transition ${
                    active ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-500 hover:bg-slate-100 hover:text-slate-800'
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
