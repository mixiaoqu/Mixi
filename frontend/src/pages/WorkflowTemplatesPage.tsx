import { Icon } from '../components/Icon'
import type { WorkflowTemplate } from '../features/workflows/types'

type WorkflowTemplatesPageProps = {
  categories: string[]
  activeCategory: string
  searchQuery: string
  templates: WorkflowTemplate[]
  onSelectCategory: (category: string) => void
  onSearchChange: (value: string) => void
  onOpenTemplate: (template: WorkflowTemplate) => void
}

const toneStyles: Record<WorkflowTemplate['tone'], string> = {
  blue: 'bg-blue-50 text-blue-700 border-blue-100',
  indigo: 'bg-indigo-50 text-indigo-700 border-indigo-100',
  rose: 'bg-rose-50 text-rose-700 border-rose-100',
  emerald: 'bg-emerald-50 text-emerald-700 border-emerald-100',
}

export default function WorkflowTemplatesPage({
  categories,
  activeCategory,
  searchQuery,
  templates,
  onSelectCategory,
  onSearchChange,
  onOpenTemplate,
}: WorkflowTemplatesPageProps) {
  return (
    <section className="min-h-[calc(100vh-4rem)] bg-slate-100 px-4 py-10 sm:px-6 lg:py-14">
      <div className="mx-auto max-w-7xl">
        <div className="mb-8 flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-950">智能体模板</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
              选择一个模板开始配置输入，预览 Agent 的执行过程和输出结果。
            </p>
          </div>

          <label className="flex w-full items-center rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm transition focus-within:border-indigo-300 focus-within:ring-4 focus-within:ring-indigo-100 lg:max-w-sm">
            <Icon name="search" className="h-4 w-4 text-slate-400" />
            <input
              className="ml-3 w-full border-0 bg-transparent text-sm font-medium text-slate-900 outline-none placeholder:text-slate-400"
              onChange={(event) => onSearchChange(event.target.value)}
              placeholder="搜索模板、分类或标签"
              type="search"
              value={searchQuery}
            />
          </label>
        </div>

        <div className="mb-8 flex flex-wrap gap-2">
          {categories.map((category) => {
            const active = category === activeCategory
            return (
              <button
                key={category}
                className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
                  active ? 'bg-slate-950 text-white' : 'bg-white text-slate-600 hover:bg-slate-200 hover:text-slate-950'
                }`}
                onClick={() => onSelectCategory(category)}
                type="button"
              >
                {category}
              </button>
            )
          })}
        </div>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {templates.map((template) => (
            <button
              key={template.id}
              className="group rounded-3xl border border-slate-200 bg-white p-5 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-slate-300 hover:shadow-md"
              onClick={() => onOpenTemplate(template)}
              type="button"
            >
              <div className="flex items-start justify-between gap-4">
                <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-slate-950 text-white">
                  <Icon name={template.icon} className="h-5 w-5" />
                </span>
                <span className={`rounded-full border px-2.5 py-1 text-xs font-bold ${toneStyles[template.tone]}`}>{template.uses}</span>
              </div>

              <h2 className="mt-5 text-lg font-bold text-slate-950">{template.title}</h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">{template.description}</p>

              <div className="mt-5 flex flex-wrap gap-2">
                {template.tags.map((tag) => (
                  <span key={tag} className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600">
                    {tag}
                  </span>
                ))}
              </div>

              <div className="mt-5 flex items-center justify-between border-t border-slate-100 pt-4">
                <span className="text-xs font-bold text-slate-500">{template.category}</span>
                <span className="inline-flex items-center gap-1 text-sm font-bold text-indigo-700 opacity-80 transition group-hover:opacity-100">
                  打开
                  <Icon name="arrow" className="h-4 w-4" />
                </span>
              </div>
            </button>
          ))}
        </div>
      </div>
    </section>
  )
}
