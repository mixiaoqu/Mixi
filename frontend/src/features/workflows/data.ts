import type { KnowledgeBase, WorkflowTemplate } from './types'

export const workflowTemplates: WorkflowTemplate[] = [
  {
    id: 'work-log',
    title: '工作日志生成',
    description: '汇总代码提交和非代码事项，整理成可确认、可复制的今日工作日志。',
    icon: 'file',
    category: '效率工具',
    uses: 'New',
    tags: ['Git', '日报'],
    tone: 'indigo',
    inputs: [
      {
        id: 'gitActivity',
        label: '代码工作记录',
        placeholder: '粘贴 commit、PR 摘要，后续也可以改成从 Git 数据源自动读取。',
        demoValue: '完成登录鉴权、注册流程和首页 Mixi 任务入口的整理。',
        rows: 4,
      },
      {
        id: 'manualTasks',
        label: '非代码事项',
        placeholder: '例如会议、需求分析、沟通、排障、学习记录。',
        demoValue: '梳理 Mixi 与工作日志 Agent 的职责边界，并确认数据源授权方式。',
        rows: 4,
      },
      {
        id: 'nextPlan',
        label: '下一步计划',
        placeholder: '补充明天或下个阶段准备推进的事项。',
        demoValue: '接入 Git 数据源并打通工作日志 Agent 的真实执行链路。',
        rows: 3,
      },
    ],
    nodes: [
      { id: 'collector', name: '记录采集', description: '读取并归并代码与非代码工作记录。' },
      { id: 'summarizer', name: '内容整理', description: '提炼成果、问题和下一步计划。' },
      { id: 'reviewer', name: '日志校对', description: '生成可确认和可编辑的日志草稿。' },
    ],
  },
  {
    id: 'study-helper',
    title: '错题解析与举一反三',
    description: '输入一道题目后，Agent 会拆解知识点、给出步骤，并生成同类练习。',
    icon: 'book',
    category: '学习辅导',
    uses: '45.2k',
    tags: ['理科', '讲解'],
    tone: 'blue',
    inputs: [
      {
        id: 'question',
        label: '题目内容',
        placeholder: '输入需要讲解的题目。',
        demoValue: '已知函数 f(x)=x^2-2x+1，求它在 [0,3] 区间内的最值。',
        rows: 4,
      },
      {
        id: 'subject',
        label: '所属学科',
        placeholder: '例如：高中数学。',
        demoValue: '高中数学',
      },
    ],
    nodes: [
      { id: 'parser', name: '题意识别', description: '识别题型、知识点和关键条件。' },
      { id: 'solver', name: '步骤讲解', description: '输出逐步推导过程。' },
      { id: 'generator', name: '同类练习', description: '给出可继续巩固的变式题。' },
    ],
  },
  {
    id: 'deep-writer',
    title: '长文内容草稿',
    description: '围绕主题组织结构、整理论点和素材，生成一版可继续打磨的长文草稿。',
    icon: 'bolt',
    category: '内容创作',
    uses: '12.8k',
    tags: ['长文', '写作'],
    tone: 'indigo',
    inputs: [
      {
        id: 'topic',
        label: '文章主题',
        placeholder: '例如：AI Agent 在企业自动化中的应用机会。',
        demoValue: 'AI Agent 在企业自动化流程中的应用机会与落地风险。',
        rows: 3,
      },
      {
        id: 'tone',
        label: '写作风格',
        placeholder: '例如：专业、克制、偏行业分析。',
        demoValue: '专业严谨，面向行业报告读者。',
      },
    ],
    nodes: [
      { id: 'planner', name: '结构规划', description: '生成文章主线和段落顺序。' },
      { id: 'researcher', name: '资料整理', description: '归纳背景资料与观点素材。' },
      { id: 'writer', name: '草稿生成', description: '输出一版结构完整的长文草稿。' },
    ],
  },
  {
    id: 'campaign-copy',
    title: '推广文案生成',
    description: '根据主题整理受众、卖点和发布版本，生成一组可直接改写的推广文案。',
    icon: 'megaphone',
    category: '营销推广',
    uses: '34.1k',
    tags: ['文案', 'A/B 测试'],
    tone: 'rose',
    inputs: [
      {
        id: 'product',
        label: '推广主题',
        placeholder: '例如：便携式咖啡机。',
        demoValue: '便携式意式咖啡机，面向经常出差的办公人群。',
        rows: 4,
      },
    ],
    nodes: [
      { id: 'trend', name: '受众拆解', description: '提炼目标用户和使用场景。' },
      { id: 'title', name: '标题生成', description: '输出多组可测试的标题方向。' },
      { id: 'content', name: '正文编排', description: '整理正文结构和行动引导。' },
    ],
  },
  {
    id: 'market-research',
    title: '竞品资料整理',
    description: '聚合公开信息，整理行业背景、核心玩家和机会判断。',
    icon: 'globe',
    category: '效率工具',
    uses: '8.4k',
    tags: ['研究', '分析'],
    tone: 'emerald',
    inputs: [
      {
        id: 'topic',
        label: '研究课题',
        placeholder: '例如：企业级 AI Agent 平台的差异化机会。',
        demoValue: '国内企业级 AI Agent 平台的主要产品形态和差异化机会。',
        rows: 4,
      },
    ],
    nodes: [
      { id: 'scraper', name: '资料收集', description: '聚合公开资讯和行业材料。' },
      { id: 'analyzer', name: '结构整理', description: '提取公司、时间线和重点判断。' },
      { id: 'reporter', name: '结论输出', description: '生成结构化研究笔记。' },
    ],
  },
]

export const knowledgeBases: KnowledgeBase[] = [
  { id: 1, name: '公司核心规章制度', docCount: 12, size: '2.4 MB', updated: '2 小时前', status: 'ready' },
  { id: 2, name: '2026 产品 FAQ 与销售话术', docCount: 5, size: '850 KB', updated: '1 天前', status: 'ready' },
  { id: 3, name: '行业竞品分析资料库', docCount: 28, size: '15.6 MB', updated: '正在向量化', status: 'syncing' },
]

export const workflowCategories = ['全部', ...Array.from(new Set(workflowTemplates.map((item) => item.category)))]
