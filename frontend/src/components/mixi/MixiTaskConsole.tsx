import { useEffect, useEffectEvent, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'

import type { MixiMessage } from '../../features/mixi/types'
import { Icon } from '../Icon'
import WorklogForm from './WorklogForm'
import './mixi-task-console.css'

type MixiTaskConsoleProps = {
  onSubmit: (prompt: string) => void | Promise<void>
  onGenerateWorkLog: () => void
  onBrowseWorkflows: () => void
  onOpenDataSources: () => void
  messages: MixiMessage[]
  isStreaming: boolean
  presetPrompt: string
  presetPromptNonce: number
  userInitial: string
}

type SpeechRecognitionResultEvent = {
  results: { [index: number]: { [index: number]: { transcript: string } } }
}

type SpeechRecognitionInstance = {
  lang: string
  interimResults: boolean
  onresult: ((event: SpeechRecognitionResultEvent) => void) | null
  onend: (() => void) | null
  onerror: (() => void) | null
  start: () => void
}

type SpeechRecognitionConstructor = new () => SpeechRecognitionInstance

export default function MixiTaskConsole({
  onSubmit,
  onGenerateWorkLog,
  onBrowseWorkflows,
  onOpenDataSources,
  messages,
  isStreaming,
  presetPrompt,
  presetPromptNonce,
  userInitial,
}: MixiTaskConsoleProps) {
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const chatContainerRef = useRef<HTMLDivElement>(null)
  const [prompt, setPrompt] = useState('')
  const [focused, setFocused] = useState(false)
  const [attachments, setAttachments] = useState<string[]>([])
  const [listening, setListening] = useState(false)

  const sessionState = messages.length > 0 || isStreaming ? 'chatting' : 'idle'
  const conversationMode = sessionState === 'chatting'
  const groupedMessages = messages.reduce<Array<MixiMessage[]>>((groups, message) => {
    const lastGroup = groups[groups.length - 1]

    if (message.role === 'user' || !lastGroup) {
      groups.push([message])
      return groups
    }

    lastGroup.push(message)
    return groups
  }, [])

  useEffect(() => {
    if (!conversationMode) return
    window.requestAnimationFrame(() => inputRef.current?.focus())
  }, [conversationMode])

  useEffect(() => {
    const node = chatContainerRef.current
    if (!node) return
    node.scrollTo({ top: node.scrollHeight, behavior: 'smooth' })
  }, [messages])

  const applyPresetPrompt = useEffectEvent((value: string) => {
    setPrompt(value)
    setFocused(true)
    inputRef.current?.focus()
  })

  useEffect(() => {
    if (!presetPrompt) return
    const frame = window.requestAnimationFrame(() => {
      applyPresetPrompt(presetPrompt)
    })
    return () => window.cancelAnimationFrame(frame)
  }, [presetPrompt, presetPromptNonce])

  async function submitPrompt(task: string) {
    const trimmedTask = task.trim()
    if (!trimmedTask || isStreaming) return

    setPrompt('')
    setAttachments([])
    setFocused(false)
    await onSubmit(trimmedTask)
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    await submitPrompt(prompt)
  }

  function focusWithPrompt(value: string) {
    setPrompt(value)
    window.requestAnimationFrame(() => inputRef.current?.focus())
  }

  function insertToken(token: string) {
    const input = inputRef.current
    const cursor = input?.selectionStart ?? prompt.length
    setPrompt(`${prompt.slice(0, cursor)}${token}${prompt.slice(cursor)}`)

    window.requestAnimationFrame(() => {
      input?.focus()
      input?.setSelectionRange(cursor + token.length, cursor + token.length)
    })
  }

  function startVoiceInput() {
    const browserWindow = window as typeof window & {
      SpeechRecognition?: SpeechRecognitionConstructor
      webkitSpeechRecognition?: SpeechRecognitionConstructor
    }
    const Recognition = browserWindow.SpeechRecognition ?? browserWindow.webkitSpeechRecognition
    if (!Recognition) return

    const recognition = new Recognition()
    recognition.lang = 'zh-CN'
    recognition.interimResults = false
    recognition.onresult = (event) => {
      const transcript = event.results[0]?.[0]?.transcript?.trim()
      if (transcript) setPrompt((current) => `${current}${current ? ' ' : ''}${transcript}`)
    }
    recognition.onend = () => setListening(false)
    recognition.onerror = () => setListening(false)

    setListening(true)
    recognition.start()
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key !== 'Enter' || event.shiftKey) return
    event.preventDefault()
    void submitPrompt(prompt)
  }

  return (
    <section
      className={`mixi-stage relative min-h-[calc(100vh-4rem)] overflow-x-hidden bg-slate-50 px-4 py-8 sm:px-6 lg:px-8 ${
        conversationMode ? 'mixi-stage--conversation' : ''
      }`}
    >
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(99,102,241,0.12),transparent_30rem)]"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(rgba(148,163,184,0.34)_1px,transparent_1px)] [background-size:24px_24px] opacity-40 [mask-image:radial-gradient(ellipse_75%_85%_at_50%_40%,black,transparent)]"
      />

      <div className={`mixi-scene ${conversationMode ? 'mixi-scene--conversation' : ''}`}>
        <div className={`mixi-idle-shell ${conversationMode ? 'mixi-idle-shell--hidden' : ''}`}>
          <div className="mx-auto max-w-3xl text-center">
            <h1 className="text-balance text-4xl font-bold tracking-[-0.03em] text-slate-950 sm:text-5xl">
              Mixi，今天想完成什么？
            </h1>
            <p className="mx-auto mt-3 max-w-2xl text-sm leading-6 text-slate-500">
              直接输入目标，或从最近的工作流开始，Mixi 会先给出实时反馈。
            </p>
          </div>
        </div>

        <div ref={chatContainerRef} className={`mixi-chat-canvas ${conversationMode ? 'mixi-chat-canvas--visible' : ''}`}>
          <div className="mixi-chat-stack">
            {groupedMessages.map((group, groupIndex) => (
              <div key={group[0]?.id ?? groupIndex} className="mixi-message-group">
                {group.map((message) => (
                  <article
                    key={message.id}
                    className={`mixi-message-row ${message.role === 'user' ? 'mixi-message-row--user' : 'mixi-message-row--assistant'}`}
                  >
                    <div className={`mixi-message-avatar ${message.role === 'user' ? 'mixi-message-avatar--user' : 'mixi-message-avatar--assistant'}`}>
                      {message.role === 'user' ? (
                        <span>{userInitial}</span>
                      ) : (
                        <span className="mixi-message-avatar__bot">
                          <span className="mixi-message-avatar__bot-face">
                            <span className="mixi-message-avatar__bot-eye" />
                            <span className="mixi-message-avatar__bot-eye" />
                          </span>
                        </span>
                      )}
                    </div>

                    <div className={`mixi-message ${message.role === 'user' ? 'mixi-message--user' : 'mixi-message--assistant'}`}>
                      <div className="mixi-message__body">
                        {message.status === 'streaming' ? (
                          <div className="mb-2 inline-flex items-center gap-2 rounded-full bg-cyan-50 px-2.5 py-1 text-xs font-semibold text-cyan-700">
                            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-cyan-500" />
                            正在回复
                          </div>
                        ) : null}

                        {message.kind === 'widget' && message.widget ? (
                          <WorklogForm
                            title={message.widget.title}
                            description={message.widget.description}
                            draft={message.widget.draft}
                            onOpenDataSources={onOpenDataSources}
                          />
                        ) : message.status === 'error' ? (
                          <p className="rounded-xl bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">{message.content}</p>
                        ) : (
                          <p className="whitespace-pre-wrap text-[15px] leading-7 text-slate-700">
                            {message.content || 'Mixi 正在组织回复…'}
                          </p>
                        )}
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            ))}
          </div>
        </div>

        <div
          className={`mixi-composer-shell ${conversationMode ? 'mixi-composer-shell--docked' : ''} ${
            focused && !conversationMode ? 'mixi-composer-shell--focused' : ''
          }`}
        >
          <div className="relative mx-auto w-full max-w-3xl">
            <div className={`relative z-10 mb-2 ml-6 inline-flex transition-all duration-300 ${conversationMode ? 'opacity-0' : 'opacity-100'}`}>
              <button
                aria-label="聚焦 Mixi 输入框"
                className="mixi-console-character relative flex h-12 w-16 items-center justify-center rounded-xl border border-slate-200 bg-white shadow-sm focus:outline-none focus-visible:outline-none"
                data-active={focused}
                onClick={() => inputRef.current?.focus()}
                type="button"
              >
                <span className="absolute -top-3 left-1/2 h-3 w-0.5 -translate-x-1/2 bg-slate-300" />
                <span
                  className={`mixi-console-antenna absolute -top-4 left-1/2 h-2 w-2 -translate-x-1/2 rounded-full ${focused ? 'bg-cyan-400' : 'bg-slate-300'}`}
                />
                <span className="mixi-console-face flex h-7 w-12 items-center justify-center rounded-lg bg-slate-950">
                  <span className="mixi-console-eyes flex items-center justify-center gap-2">
                    <span
                      className={`mixi-console-eye rounded-full transition-all ${focused && prompt ? 'h-4 w-2 bg-cyan-300' : 'h-3 w-2 bg-cyan-200'}`}
                    />
                    <span
                      className={`mixi-console-eye rounded-full transition-all ${focused && prompt ? 'h-4 w-2 bg-cyan-300' : 'h-3 w-2 bg-cyan-200'}`}
                    />
                  </span>
                </span>
                <span className="mixi-console-hand mixi-console-hand-left" />
                <span className="mixi-console-hand mixi-console-hand-right" />
              </button>
            </div>

            <form
              className={`mixi-console-form overflow-hidden border bg-white ${conversationMode ? 'rounded-[24px]' : 'rounded-[32px]'}`}
              onSubmit={(event) => void handleSubmit(event)}
            >
              <textarea
                ref={inputRef}
                aria-label="告诉 Mixi 你想完成的任务"
                className={`mixi-console-input w-full resize-none bg-transparent px-5 pb-3 pt-5 text-base leading-7 text-slate-900 outline-none placeholder:text-slate-400 transition-[min-height] duration-200 ${
                  conversationMode ? 'min-h-[88px]' : focused ? 'min-h-[144px]' : 'min-h-[112px]'
                }`}
                onBlur={() => setFocused(false)}
                onChange={(event) => setPrompt(event.target.value)}
                onFocus={() => setFocused(true)}
                onKeyDown={handleKeyDown}
                placeholder={conversationMode ? '继续追问，或输入新的任务…' : '例如：帮我生成今天的工作日志'}
                value={prompt}
              />

              <div className="flex items-center justify-between px-3.5 py-2.5">
                <div className="flex items-center gap-1">
                  <input
                    ref={fileInputRef}
                    className="hidden"
                    multiple
                    onChange={(event) => setAttachments(Array.from(event.target.files ?? []).map((file) => file.name))}
                    type="file"
                  />
                  <button
                    aria-label="添加附件"
                    className="rounded-lg p-1.5 text-slate-400 transition hover:bg-cyan-50 hover:text-cyan-700"
                    onClick={() => fileInputRef.current?.click()}
                    type="button"
                  >
                    <Icon name="plus" className="h-4 w-4" />
                  </button>
                  {attachments.length > 0 && (
                    <span className="ml-1 text-xs font-semibold text-slate-500">已选择 {attachments.length} 个文件</span>
                  )}
                  <button
                    aria-label="提及智能体"
                    className="rounded-lg p-1.5 text-slate-400 transition hover:bg-indigo-50 hover:text-indigo-700"
                    onClick={() => insertToken('@')}
                    type="button"
                  >
                    <Icon name="at" className="h-4 w-4" />
                  </button>
                  <button
                    aria-label="输入快捷指令"
                    className="rounded-lg p-1.5 text-slate-400 transition hover:bg-amber-50 hover:text-amber-700"
                    onClick={() => insertToken('/')}
                    type="button"
                  >
                    <Icon name="command" className="h-4 w-4" />
                  </button>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    aria-label={listening ? '正在监听语音' : '开始语音输入'}
                    className={`rounded-lg p-1.5 transition ${listening ? 'bg-cyan-50 text-cyan-700' : 'text-slate-400 hover:bg-cyan-50 hover:text-cyan-700'}`}
                    onClick={startVoiceInput}
                    type="button"
                  >
                    <Icon name="mic" className={`h-4 w-4 ${listening ? 'animate-pulse' : ''}`} />
                  </button>
                  <button
                    className="ml-auto inline-flex items-center gap-1.5 rounded-xl bg-slate-950 px-4 py-2 text-sm font-bold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
                    disabled={!prompt.trim() || isStreaming}
                    type="submit"
                  >
                    {isStreaming ? '思考中' : '发送'}
                    <Icon name={isStreaming ? 'loader' : 'arrow'} className={`h-3.5 w-3.5 ${isStreaming ? 'animate-spin' : ''}`} />
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>

        <div
          aria-hidden={focused || conversationMode}
          className={`mixi-shortcuts-shell mx-auto w-full max-w-4xl overflow-hidden transition-all duration-500 ease-out ${
            focused || conversationMode ? 'pointer-events-none max-h-0 translate-y-8 opacity-0' : 'max-h-80 translate-y-0 opacity-100'
          }`}
        >
          <div className="mb-4 flex items-center justify-between px-1">
            <h2 className="flex items-center gap-2 text-sm font-bold text-slate-700">
              <Icon name="refresh" className="h-4 w-4 text-slate-400" />
              最近的工作流
            </h2>
            <button className="text-xs font-bold text-cyan-700 transition hover:text-cyan-800" onClick={onBrowseWorkflows} type="button">
              查看全部
            </button>
          </div>

          <div className="grid gap-3 md:grid-cols-3">
            <button
              className="group rounded-2xl border border-slate-200 bg-white p-4 text-left shadow-sm transition hover:border-cyan-200 hover:shadow-md"
              onClick={onGenerateWorkLog}
              type="button"
            >
              <span className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-50 text-cyan-700 transition group-hover:-translate-y-0.5">
                <Icon name="file" className="h-5 w-5" />
              </span>
              <span className="block text-sm font-bold text-slate-900">每日工作日志</span>
              <span className="mt-1 block text-xs leading-5 text-slate-500">
                汇总代码记录和非代码事项，生成今天的工作日志。
              </span>
            </button>

            <button
              className="group rounded-2xl border border-slate-200 bg-white p-4 text-left shadow-sm transition hover:border-violet-200 hover:shadow-md"
              onClick={() => focusWithPrompt('分析最近的 API 错误日志，并给出修复建议')}
              type="button"
            >
              <span className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-violet-50 text-violet-700 transition group-hover:-translate-y-0.5">
                <Icon name="terminal" className="h-5 w-5" />
              </span>
              <span className="block text-sm font-bold text-slate-900">API 错误分析</span>
              <span className="mt-1 block text-xs leading-5 text-slate-500">
                整理异常日志，定位原因，并生成修复建议。
              </span>
            </button>

            <button
              className="group flex min-h-36 flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-white/70 p-4 text-center transition hover:border-slate-400 hover:bg-white"
              onClick={onBrowseWorkflows}
              type="button"
            >
              <span className="mb-2 flex h-10 w-10 items-center justify-center rounded-xl bg-slate-100 text-slate-500 transition group-hover:text-slate-700">
                <Icon name="grid" className="h-5 w-5" />
              </span>
              <span className="text-sm font-bold text-slate-700">从模板创建工作流</span>
            </button>
          </div>
        </div>
      </div>
    </section>
  )
}
