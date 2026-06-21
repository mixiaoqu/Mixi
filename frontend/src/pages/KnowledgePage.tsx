import { Icon } from '../components/Icon'
import type { KnowledgeBase } from '../features/workflows/types'

export default function KnowledgePage({ knowledgeBases }: { knowledgeBases: KnowledgeBase[] }) {
  return (
    <section className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:py-10">
      <div className="mb-8 flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="mb-2 text-sm font-semibold text-indigo-700">Knowledge Base</p>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950 sm:text-4xl">管理工作流知识源</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600 sm:text-base">
            上传文档并完成向量化处理，让智能体在执行时引用你的私有资料。
          </p>
        </div>
        <button className="inline-flex items-center justify-center gap-2 rounded-xl bg-slate-950 px-4 py-3 text-sm font-bold text-white transition hover:bg-slate-800" type="button">
          <Icon name="plus" className="h-4 w-4" />
          新建知识库
        </button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        <button className="flex min-h-60 flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-300 bg-white p-6 text-center transition hover:border-indigo-300 hover:bg-indigo-50/50" type="button">
          <span className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-slate-100 text-slate-500">
            <Icon name="upload" className="h-6 w-6" />
          </span>
          <span className="text-sm font-bold text-slate-800">拖拽或点击上传文件</span>
          <span className="mt-2 text-xs font-medium text-slate-500">支持 PDF、Word、Markdown、TXT</span>
        </button>

        {knowledgeBases.map((kb) => (
          <article key={kb.id} className="flex min-h-60 flex-col justify-between rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-slate-300 hover:shadow-md">
            <div>
              <div className="mb-5 flex items-start justify-between">
                <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-indigo-50 text-indigo-700">
                  <Icon name="database" className="h-5 w-5" />
                </span>
                <button aria-label={`删除 ${kb.name}`} className="rounded-lg p-2 text-slate-300 transition hover:bg-rose-50 hover:text-rose-600" type="button">
                  <Icon name="trash" className="h-4 w-4" />
                </button>
              </div>
              <h2 className="text-base font-bold leading-snug text-slate-950">{kb.name}</h2>
              <div className="mt-4 flex flex-wrap gap-3 text-sm font-semibold text-slate-500">
                <span className="inline-flex items-center gap-1.5">
                  <Icon name="file" className="h-4 w-4 text-slate-400" />
                  {kb.docCount} 个文件
                </span>
                <span>{kb.size}</span>
              </div>
            </div>

            <div className="mt-6 flex items-center justify-between border-t border-slate-100 pt-4">
              {kb.status === 'syncing' ? (
                <span className="inline-flex items-center gap-1.5 text-xs font-bold text-amber-700">
                  <Icon name="loader" className="h-3.5 w-3.5 animate-spin" />
                  向量化中
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 text-xs font-bold text-slate-500">
                  <Icon name="sync" className="h-3.5 w-3.5" />
                  {kb.updated}
                </span>
              )}
              <button className="inline-flex items-center gap-1 text-sm font-bold text-indigo-700 transition hover:text-indigo-800" type="button">
                配置
                <Icon name="arrow" className="h-3.5 w-3.5" />
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}
