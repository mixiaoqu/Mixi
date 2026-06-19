import { useEffect, useMemo, useState } from 'react'
import { Icon, type IconName } from './components/Icon'
import LoginPage from './pages/LoginPage'
import './App.css'

type View = 'hub' | 'workspace' | 'knowledge'
type RunStatus = 'idle' | 'running' | 'completed' | 'failed'
type WorkflowInput = {
  id: string
  label: string
  placeholder: string
  demoValue: string
  rows?: number
}

type WorkflowNode = {
  id: string
  name: string
  desc: string
}

type WorkflowTemplate = {
  id: string
  title: string
  description: string
  icon: IconName
  category: string
  uses: string
  tags: string[]
  tone: 'blue' | 'indigo' | 'rose' | 'emerald'
  inputs: WorkflowInput[]
  nodes: WorkflowNode[]
}

type KnowledgeBase = {
  id: number
  name: string
  docCount: number
  size: string
  updated: string
  status: 'ready' | 'syncing'
}

const toneStyles: Record<WorkflowTemplate['tone'], string> = {
  blue: 'bg-blue-50 text-blue-700 border-blue-100',
  indigo: 'bg-indigo-50 text-indigo-700 border-indigo-100',
  rose: 'bg-rose-50 text-rose-700 border-rose-100',
  emerald: 'bg-emerald-50 text-emerald-700 border-emerald-100',
}

const workflowTemplates: WorkflowTemplate[] = [
  {
    id: 'study-helper',
    title: '错题解析与举一反三',
    description: '输入一道错题，AI 导师会拆解知识点、给出分步讲解，并生成同类练习。',
    icon: 'book',
    category: '学习辅导',
    uses: '45.2k',
    tags: ['理科', 'AI 导师'],
    tone: 'blue',
    inputs: [
      {
        id: 'question',
        label: '题目内容',
        placeholder: '输入需要讲解的题目',
        demoValue: '已知函数 f(x) = x^2 - 2x + 1，求其在 [0, 3] 区间的最值。',
        rows: 4,
      },
      {
        id: 'subject',
        label: '所属学科',
        placeholder: '例如：高中数学',
        demoValue: '高中数学',
      },
    ],
    nodes: [
      { id: 'parser', name: '意图识别', desc: '识别题型、知识点和关键条件' },
      { id: 'solver', name: '分步解析', desc: '生成引导式解题步骤' },
      { id: 'generator', name: '同类题生成', desc: '创建可巩固的变式练习' },
    ],
  },
  {
    id: 'deep-writer',
    title: '深度长文自动创作',
    description: '围绕主题自动规划大纲、检索资料、提炼论点并生成长文初稿。',
    icon: 'bolt',
    category: '创意写作',
    uses: '12.8k',
    tags: ['长文', '资料检索'],
    tone: 'indigo',
    inputs: [
      {
        id: 'topic',
        label: '文章主题',
        placeholder: '例如：AI Agent 在企业流程中的应用',
        demoValue: 'AI Agent 在企业自动化流程中的应用机会与落地风险',
        rows: 3,
      },
      {
        id: 'tone',
        label: '写作风格',
        placeholder: '例如：专业、克制、数据驱动',
        demoValue: '专业严谨，面向行业报告读者，减少口号式表达。',
      },
    ],
    nodes: [
      { id: 'planner', name: '大纲规划', desc: '生成文章结构和论点顺序' },
      { id: 'researcher', name: '资料检索', desc: '收集公开资料与背景信息' },
      { id: 'synthesizer', name: '信息提炼', desc: '清洗资料并归纳核心观点' },
      { id: 'writer', name: '初稿生成', desc: '输出结构完整的长文草稿' },
    ],
  },
  {
    id: 'campaign-copy',
    title: '社交媒体推广文案',
    description: '分析推广主题，生成标题、正文结构和多个可测试的发布版本。',
    icon: 'megaphone',
    category: '营销推广',
    uses: '34.1k',
    tags: ['文案', 'A/B 测试'],
    tone: 'rose',
    inputs: [
      {
        id: 'product',
        label: '推广主题',
        placeholder: '例如：便携式咖啡机',
        demoValue: '便携式意式咖啡机，面向经常出差的办公室人群。',
        rows: 4,
      },
    ],
    nodes: [
      { id: 'trend', name: '受众分析', desc: '提炼目标人群和使用场景' },
      { id: 'title', name: '标题生成', desc: '生成多组可测试标题' },
      { id: 'content', name: '正文排版', desc: '组织正文段落和行动按钮' },
    ],
  },
  {
    id: 'market-research',
    title: '行业竞品资料收集',
    description: '抓取公开资料，整理行业背景、关键玩家、时间线和机会判断。',
    icon: 'globe',
    category: '效率工具',
    uses: '8.4k',
    tags: ['研究', '聚合'],
    tone: 'emerald',
    inputs: [
      {
        id: 'topic',
        label: '研究课题',
        placeholder: '例如：新能源车电池回收行业',
        demoValue: '国内企业级 AI Agent 平台的主要产品形态和差异化机会。',
        rows: 4,
      },
    ],
    nodes: [
      { id: 'scraper', name: '资料采集', desc: '抓取公开资讯和行业页面' },
      { id: 'analyzer', name: '结构整理', desc: '提取公司、时间线和观点' },
      { id: 'reporter', name: '报告生成', desc: '输出结构化研究笔记' },
    ],
  },
]

const knowledgeBases: KnowledgeBase[] = [
  { id: 1, name: '公司核心规章制度', docCount: 12, size: '2.4 MB', updated: '2 小时前', status: 'ready' },
  { id: 2, name: '2026 产品 FAQ 与销售话术', docCount: 5, size: '850 KB', updated: '1 天前', status: 'ready' },
  { id: 3, name: '行业竞品分析报告库', docCount: 28, size: '15.6 MB', updated: '正在向量化', status: 'syncing' },
]

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [activeView, setActiveView] = useState<View>('hub')
  const [selectedTemplate, setSelectedTemplate] = useState<WorkflowTemplate>(workflowTemplates[0])
  const [status, setStatus] = useState<RunStatus>('idle')
  const [currentStep, setCurrentStep] = useState(-1)
  const [output, setOutput] = useState('')
  const [formData, setFormData] = useState<Record<string, string>>({})
  const [logs, setLogs] = useState<string[]>([])
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    let timer: number | undefined
    let subTimer: number | undefined

    if (status === 'running') {
      if (currentStep < selectedTemplate.nodes.length) {
        const node = selectedTemplate.nodes[currentStep]

        subTimer = window.setTimeout(() => {
          setLogs((prev) => [...prev, `[system] booting agent node: ${node.name}`, `> executing: ${node.name}`, `> task: ${node.desc}`])
        }, 100)

        timer = window.setTimeout(() => {
          setLogs((prev) => [...prev, `[success] ${node.name} completed`])
          setCurrentStep((prev) => prev + 1)
        }, 1300)
      } else {
        timer = window.setTimeout(() => {
          setStatus('completed')
          setOutput(
            [
              '工作流执行完成。',
              '',
              `已根据「${selectedTemplate.title}」模板完成任务，执行链路包含 ${selectedTemplate.nodes.length} 个节点。`,
              '当前版本使用本地模拟事件，后续可以替换为 FastAPI + LangGraph 的 SSE 或 WebSocket 事件流。',
              '',
              '建议下一步：保存本次运行记录，支持重新运行同一参数，并在节点详情中展示输入、输出和错误信息。',
            ].join('\n'),
          )
        }, 100)
      }
    }

    return () => {
      window.clearTimeout(timer)
      window.clearTimeout(subTimer)
    }
  }, [status, currentStep, selectedTemplate])

  const categories = useMemo(() => ['全部', ...Array.from(new Set(workflowTemplates.map((item) => item.category)))], [])
  const [activeCategory, setActiveCategory] = useState('全部')

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

  const requiredInputFilled = Boolean(formData[selectedTemplate.inputs[0]?.id])

  function resetRun(clearForm = false) {
    setStatus('idle')
    setCurrentStep(-1)
    setOutput('')
    setLogs([])
    if (clearForm) {
      setFormData({})
    }
  }

  function openWorkspace(template: WorkflowTemplate) {
    setSelectedTemplate(template)
    setFormData({})
    resetRun()
    setActiveView('workspace')
  }

  function fillDemoData() {
    setFormData(Object.fromEntries(selectedTemplate.inputs.map((input) => [input.id, input.demoValue])))
  }

  function startRun() {
    if (!requiredInputFilled || status === 'running') return

    setStatus('running')
    setCurrentStep(0)
    setOutput('')
    setLogs(['[ok] initializing Agent Platform runtime', `[ok] selected workflow: ${selectedTemplate.id}`])
  }

  function failRunForPreview() {
    if (status !== 'running') return

    setStatus('failed')
    setLogs((prev) => [...prev, '[error] current node returned an empty response', '[hint] retry this node after checking inputs'])
  }

  if (!isAuthenticated) {
    return <LoginPage onLogin={() => setIsAuthenticated(true)} />
  }

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900">
      <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-slate-200 bg-white px-4 sm:px-6">
        <button className="flex items-center gap-3" onClick={() => setActiveView('hub')} type="button">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-950 text-white">
            <Icon name="spark" className="h-5 w-5" />
          </span>
          <span className="text-lg font-bold tracking-tight">
            Agent<span className="text-indigo-600">Platform</span>
          </span>
        </button>

        <nav className="hidden items-center gap-1 md:flex">
          <NavButton active={activeView === 'hub'} label="工作流模板" onClick={() => setActiveView('hub')} />
          <NavButton active={activeView === 'workspace'} label="运行工作台" onClick={() => setActiveView('workspace')} />
          <NavButton active={activeView === 'knowledge'} label="知识库" onClick={() => setActiveView('knowledge')} />
        </nav>

        <div className="flex items-center gap-3">
          <button className="hidden rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 sm:inline-flex" type="button">
            API 设置
          </button>
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-indigo-50 text-sm font-bold text-indigo-700 ring-1 ring-indigo-100">
            M
          </div>
        </div>
      </header>

      <main className="min-h-[calc(100vh-4rem)]">
        {activeView === 'hub' && (
          <section className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:py-10">
            <div className="mb-8 flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <p className="mb-2 text-sm font-semibold text-indigo-700">Workflow Hub</p>
                <h1 className="text-3xl font-bold tracking-tight text-slate-950 sm:text-4xl">选择一个 Agent 工作流</h1>
                <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600 sm:text-base">
                  从预置模板开始，配置输入参数，观察节点执行过程，并把结果沉淀为可复用的运行记录。
                </p>
              </div>

              <label className="flex w-full items-center rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm transition focus-within:border-indigo-300 focus-within:ring-4 focus-within:ring-indigo-100 lg:w-96">
                <Icon name="search" className="h-4 w-4 text-slate-400" />
                <input
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                  className="ml-3 w-full border-0 bg-transparent text-sm text-slate-800 outline-none placeholder:text-slate-400"
                  placeholder="搜索名称、分类或标签"
                  type="search"
                />
              </label>
            </div>

            <div className="mb-6 flex gap-2 overflow-x-auto pb-1">
              {categories.map((category) => (
                <button
                  key={category}
                  type="button"
                  onClick={() => setActiveCategory(category)}
                  className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
                    activeCategory === category
                      ? 'bg-slate-950 text-white'
                      : 'border border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:text-slate-950'
                  }`}
                >
                  {category}
                </button>
              ))}
            </div>

            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {filteredTemplates.map((template) => (
                <button
                  key={template.id}
                  onClick={() => openWorkspace(template)}
                  type="button"
                  className="group flex min-h-72 flex-col rounded-2xl border border-slate-200 bg-white p-5 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-slate-300 hover:shadow-md"
                >
                  <div className="mb-5 flex items-start justify-between">
                    <span className={`flex h-12 w-12 items-center justify-center rounded-xl border ${toneStyles[template.tone]}`}>
                      <Icon name={template.icon} className="h-6 w-6" />
                    </span>
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-50 px-2.5 py-1 text-xs font-semibold text-slate-500 ring-1 ring-slate-200">
                      <Icon name="users" className="h-3 w-3" />
                      {template.uses}
                    </span>
                  </div>

                  <h2 className="text-lg font-bold text-slate-950 transition group-hover:text-indigo-700">{template.title}</h2>
                  <p className="mt-2 line-clamp-3 flex-1 text-sm leading-6 text-slate-600">{template.description}</p>

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
          </section>
        )}

        {activeView === 'workspace' && (
          <section className="flex min-h-[calc(100vh-4rem)] flex-col">
            <div className="sticky top-16 z-20 flex h-14 items-center justify-between border-b border-slate-200 bg-white/90 px-4 backdrop-blur sm:px-6">
              <div className="flex min-w-0 items-center gap-2 text-sm font-semibold">
                <button className="inline-flex items-center gap-1 text-slate-500 transition hover:text-slate-900" onClick={() => setActiveView('hub')} type="button">
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
                  <button className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-1.5 text-sm font-bold text-rose-700 transition hover:bg-rose-100" type="button" onClick={failRunForPreview}>
                    模拟失败
                  </button>
                )}
                {status !== 'idle' && (
                  <button className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-bold text-slate-700 transition hover:bg-slate-50" type="button" onClick={() => resetRun()}>
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
                      <p className="mt-1 text-sm text-slate-500">填写输入后启动工作流。</p>
                    </div>
                    <button className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-50 px-3 py-1.5 text-xs font-bold text-indigo-700 transition hover:bg-indigo-100" onClick={fillDemoData} type="button">
                      <Icon name="wand" className="h-3.5 w-3.5" />
                      示例数据
                    </button>
                  </div>

                  <div className="space-y-5">
                    {selectedTemplate.inputs.map((input) => (
                      <label key={input.id} className="block">
                        <span className="mb-2 block text-sm font-bold text-slate-700">{input.label}</span>
                        <textarea
                          rows={input.rows ?? 3}
                          value={formData[input.id] ?? ''}
                          onChange={(event) => setFormData((prev) => ({ ...prev, [input.id]: event.target.value }))}
                          placeholder={input.placeholder}
                          className="w-full resize-none rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm leading-6 text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-indigo-400 focus:bg-white focus:ring-4 focus:ring-indigo-100"
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
                      onClick={startRun}
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
                            <span className="mt-1 text-xs leading-5 text-slate-500">{node.desc}</span>
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
                      <p className="mt-2 max-w-sm text-sm leading-6 text-slate-500">填写左侧参数后开始运行。这里会显示节点日志、失败提示和最终结果。</p>
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
                          <button className="inline-flex items-center gap-1 rounded-lg bg-white/10 px-3 py-1.5 text-xs font-bold text-white transition hover:bg-white/15" onClick={startRun} type="button">
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
                            <p className="text-sm text-slate-500">本地模拟输出，可替换为真实运行产物。</p>
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
        )}

        {activeView === 'knowledge' && (
          <section className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:py-10">
            <div className="mb-8 flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="mb-2 text-sm font-semibold text-indigo-700">Knowledge Base</p>
                <h1 className="text-3xl font-bold tracking-tight text-slate-950 sm:text-4xl">管理工作流知识源</h1>
                <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600 sm:text-base">
                  上传文档并完成向量化处理，让工作流在执行时引用私有资料。
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
                      <button className="rounded-lg p-2 text-slate-300 transition hover:bg-rose-50 hover:text-rose-600" type="button" aria-label={`删除 ${kb.name}`}>
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
        )}
      </main>
    </div>
  )
}

function NavButton({ active, label, onClick }: { active: boolean; label: string; onClick: () => void }) {
  return (
    <button
      className={`rounded-lg px-4 py-2 text-sm font-semibold transition ${
        active ? 'bg-slate-100 text-slate-950' : 'text-slate-500 hover:bg-slate-50 hover:text-slate-950'
      }`}
      onClick={onClick}
      type="button"
    >
      {label}
    </button>
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

function statusLabel(status: RunStatus) {
  const labels: Record<RunStatus, string> = {
    idle: '等待运行',
    running: '运行中',
    completed: '已完成',
    failed: '运行失败',
  }

  return labels[status]
}

function statusBadgeClass(status: RunStatus) {
  const classes: Record<RunStatus, string> = {
    idle: 'rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-600',
    running: 'rounded-full bg-indigo-50 px-3 py-1 text-xs font-bold text-indigo-700',
    completed: 'rounded-full bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-700',
    failed: 'rounded-full bg-rose-50 px-3 py-1 text-xs font-bold text-rose-700',
  }

  return classes[status]
}

function logLineClass(log: string) {
  if (log.startsWith('[ok]') || log.startsWith('[success]')) {
    return 'text-emerald-300'
  }

  if (log.startsWith('[error]')) {
    return 'text-rose-300'
  }

  if (log.startsWith('[hint]')) {
    return 'text-amber-300'
  }

  if (log.startsWith('>')) {
    return 'border-l border-slate-700 pl-3 text-slate-400'
  }

  return 'font-semibold text-slate-200'
}

export default App
