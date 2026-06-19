import { useEffect, useRef, useState } from 'react'
import { Icon, type IconName } from '../Icon'

export type AuthFocus = 'email' | 'password' | null

type LumiCompanionProps = {
  focus: AuthFocus
  showPassword: boolean
  passwordLength: number
  isSubmitting: boolean
  isLoginSuccess: boolean
  isLoginError: boolean
  mouse: { x: number; y: number; movedAt: number }
}

const POKE_DURATION_MS = 1200
const IDLE_GLANCE_MIN_MS = 7000
const IDLE_GLANCE_VARIANCE_MS = 5000
const IDLE_GLANCE_DURATION_MS = 900

export default function LumiCompanion({ focus, showPassword, passwordLength, isSubmitting, isLoginSuccess, isLoginError, mouse }: LumiCompanionProps) {
  const bodyRef = useRef<HTMLButtonElement>(null)
  const pokeTimerRef = useRef<number | undefined>(undefined)
  const [isBlinking, setIsBlinking] = useState(false)
  const [isPoked, setIsPoked] = useState(false)
  const [idleGlance, setIdleGlance] = useState<{ x: number; y: number } | null>(null)

  useEffect(() => {
    let blinkTimer: number | undefined

    function scheduleBlink() {
      blinkTimer = window.setTimeout(() => {
        setIsBlinking(true)
        window.setTimeout(() => setIsBlinking(false), 130)
        scheduleBlink()
      }, 2600 + Math.random() * 3200)
    }

    scheduleBlink()

    return () => {
      window.clearTimeout(blinkTimer)
      window.clearTimeout(pokeTimerRef.current)
    }
  }, [])

  useEffect(() => {
    if (focus || isSubmitting || isLoginSuccess || isLoginError || isPoked) {
      setIdleGlance(null)
      return
    }

    let glanceStartTimer: number | undefined
    let glanceEndTimer: number | undefined

    function scheduleIdleGlance() {
      const waitMs = IDLE_GLANCE_MIN_MS + Math.random() * IDLE_GLANCE_VARIANCE_MS

      glanceStartTimer = window.setTimeout(() => {
        if (Date.now() - mouse.movedAt < waitMs - 1200) {
          scheduleIdleGlance()
          return
        }

        setIdleGlance(Math.random() > 0.5 ? { x: 5, y: -1 } : { x: -5, y: 1 })

        glanceEndTimer = window.setTimeout(() => {
          setIdleGlance(null)
          scheduleIdleGlance()
        }, IDLE_GLANCE_DURATION_MS)
      }, waitMs)
    }

    scheduleIdleGlance()

    return () => {
      window.clearTimeout(glanceStartTimer)
      window.clearTimeout(glanceEndTimer)
    }
  }, [focus, isSubmitting, isLoginSuccess, isLoginError, isPoked, mouse.movedAt])

  function handlePoke() {
    if (isSubmitting || isLoginSuccess) return
    window.clearTimeout(pokeTimerRef.current)
    setIdleGlance(null)
    setIsPoked(true)
    pokeTimerRef.current = window.setTimeout(() => setIsPoked(false), POKE_DURATION_MS)
  }

  function eyeOffset() {
    if (isLoginSuccess) return { x: 0, y: -2 }
    if (isLoginError) return { x: 0, y: 2 }
    if (isPoked) return { x: 0, y: -1 }
    if (idleGlance) return idleGlance
    if (showPassword) return { x: -10, y: -7 }
    if (focus === 'password' && passwordLength > 0) return { x: 5, y: 4 }
    if (focus === 'password') return { x: 0, y: -2 }
    if (focus === 'email') return { x: 8, y: 6 }

    const rect = bodyRef.current?.getBoundingClientRect()
    if (!rect) return { x: 0, y: 0 }

    const dx = mouse.x - (rect.left + rect.width / 2)
    const dy = mouse.y - (rect.top + rect.height / 2)
    const angle = Math.atan2(dy, dx)
    const distance = Math.min(7, Math.hypot(dx, dy) / 42)

    return {
      x: Math.cos(angle) * distance,
      y: Math.sin(angle) * distance,
    }
  }

  const offset = eyeOffset()
  const isPeeking = focus === 'password' && passwordLength > 0 && !showPassword && !isPoked && !isLoginSuccess && !isLoginError
  const eyeClass = isBlinking && !isPeeking && !isPoked && !isLoginSuccess && !isLoginError ? 'h-1.5 w-7' : 'h-10 w-5'
  const leftEyeClass = isLoginSuccess ? 'h-9 w-5' : isLoginError ? 'h-7 w-4' : isPoked ? 'h-9 w-6' : isPeeking ? 'h-2 w-8' : eyeClass
  const rightEyeClass = isLoginSuccess ? 'h-9 w-5' : isLoginError ? 'h-7 w-4' : isPoked ? 'h-9 w-6' : isPeeking ? 'h-6 w-6' : eyeClass
  const status = isLoginSuccess
    ? '已连接工作台'
    : isLoginError
      ? '验证失败，请重试'
    : isPoked
      ? '哎呀！被戳中了 ヾ(≧▽≦*)o'
      : showPassword
      ? 'Lumi 已保护输入'
      : isPeeking
        ? '正在检查输入安全'
        : isSubmitting
          ? '正在登录工作台'
          : focus === 'email'
            ? '正在确认工作邮箱'
            : 'Lumi 已就绪'

  const abilities: Array<{ icon: IconName; label: string; className: string }> = [
    { icon: 'database', label: '记忆', className: 'lumi-stream-memory' },
    { icon: 'book', label: '知识', className: 'lumi-stream-knowledge' },
    { icon: 'bolt', label: '推理', className: 'lumi-stream-reasoning' },
    { icon: 'grid', label: '工具', className: 'lumi-stream-tools' },
  ]

  const indicatorClass = isLoginSuccess ? 'bg-emerald-400' : isLoginError ? 'bg-rose-400' : isPoked ? 'bg-cyan-400' : showPassword ? 'bg-sky-400' : isPeeking ? 'bg-indigo-400' : 'bg-emerald-400'

  return (
    <div className="lumi-wrap">
      <div className="lumi-data-stream" aria-hidden="true">
        {abilities.map((ability) => (
          <div key={ability.label} className={`lumi-stream-lane ${ability.className}`}>
            <div className="lumi-ability-card">
              <Icon name={ability.icon} className="h-4 w-4" />
              <span>{ability.label}</span>
            </div>
          </div>
        ))}
        <span className="lumi-particle lumi-particle-a" />
        <span className="lumi-particle lumi-particle-b" />
        <span className="lumi-particle lumi-particle-c" />
        <span className="lumi-particle lumi-particle-d" />
      </div>

      <div className="lumi-orbit" aria-hidden="true">
        <div className="lumi-ring lumi-ring-one" />
      </div>

      <button
        ref={bodyRef}
        aria-label="与 Lumi 互动"
        className={`lumi-body ${isPoked ? 'lumi-body-poked' : ''} ${isLoginSuccess ? 'lumi-body-success' : ''} ${isLoginError ? 'lumi-body-error' : ''}`}
        onClick={handlePoke}
        type="button"
      >
        <div className="lumi-antenna">
          <span className={indicatorClass} />
        </div>
        <div className="lumi-face">
          <span className={`lumi-eye ${isPoked ? 'lumi-eye-poked' : ''} ${isLoginSuccess ? 'lumi-eye-success' : ''} ${isLoginError ? 'lumi-eye-error' : ''} ${leftEyeClass}`} style={{ transform: `translate(${offset.x}px, ${offset.y}px)` }} />
          <span className={`lumi-eye ${isPoked ? 'lumi-eye-poked' : ''} ${isLoginSuccess ? 'lumi-eye-success' : ''} ${isLoginError ? 'lumi-eye-error' : ''} ${rightEyeClass}`} style={{ transform: `translate(${offset.x}px, ${offset.y}px)` }} />
        </div>
        <span className={`lumi-hand lumi-hand-left ${isPeeking ? 'lumi-hand-peek-left' : ''} ${isPoked ? 'lumi-hand-cheer-left' : ''} ${isLoginSuccess ? 'lumi-hand-rest-left' : ''}`} />
        <span className={`lumi-hand lumi-hand-right ${isPeeking ? 'lumi-hand-peek-right' : ''} ${isPoked ? 'lumi-hand-cheer-right' : ''} ${isLoginSuccess ? 'lumi-hand-rest-right' : ''}`} />
      </button>

      <div className={`lumi-status ${isPoked ? 'lumi-status-poked' : ''} ${isLoginSuccess ? 'lumi-status-success' : ''} ${isLoginError ? 'lumi-status-error' : ''}`}>
        <span className={indicatorClass} />
        {status}
      </div>
    </div>
  )
}
