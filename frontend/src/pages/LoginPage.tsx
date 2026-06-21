import { useEffect, useState, type FormEvent } from 'react'

import { Icon } from '../components/Icon'
import MixiCompanion, { type AuthFocus } from '../components/auth/MixiCompanion'
import { ApiError, login, register, type AuthUser } from '../lib/auth'
import '../styles/auth.css'

type LoginPageProps = {
  onLogin: (user: AuthUser) => void
}

export default function LoginPage({ onLogin }: LoginPageProps) {
  const [focus, setFocus] = useState<AuthFocus>(null)
  const [showPassword, setShowPassword] = useState(false)
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [displayName, setDisplayName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isLoginSuccess, setIsLoginSuccess] = useState(false)
  const [loginError, setLoginError] = useState<string | null>(null)
  const [registrationNotice, setRegistrationNotice] = useState<string | null>(null)
  const [mouse, setMouse] = useState({ x: 0, y: 0, movedAt: 0 })

  useEffect(() => {
    function handleMouseMove(event: MouseEvent) {
      setMouse({ x: event.clientX, y: event.clientY, movedAt: Date.now() })
    }

    window.addEventListener('mousemove', handleMouseMove)
    return () => window.removeEventListener('mousemove', handleMouseMove)
  }, [])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setIsSubmitting(true)
    setIsLoginSuccess(false)
    setLoginError(null)

    try {
      if (mode === 'register') {
        await register(email, displayName, password)
        setMode('login')
        setDisplayName('')
        setEmail('')
        setPassword('')
        setShowPassword(false)
        setIsSubmitting(false)
        setFocus(null)
        setRegistrationNotice('注册成功，请使用新账号登录。')
        return
      }

      const user = await login(email, password)
      setIsSubmitting(false)
      setIsLoginSuccess(true)
      window.setTimeout(() => {
        onLogin(user)
      }, 500)
    } catch (error) {
      setIsSubmitting(false)
      setFocus('password')
      setLoginError(
        error instanceof ApiError && error.status === 401
          ? '邮箱或密码不正确，请重新输入。'
          : error instanceof ApiError && error.status === 409
            ? '这个邮箱已经注册，请直接登录。'
            : error instanceof ApiError && error.status === 422
              ? '请输入有效邮箱，密码至少需要 8 个字符。'
              : '暂时无法连接，请确认后端服务已启动。',
      )
    }
  }

  return (
    <main className="min-h-screen overflow-hidden bg-[var(--color-bg)] text-slate-900">
      <div className="grid min-h-screen lg:grid-cols-[minmax(0,1fr)_minmax(460px,620px)]">
        <section className="relative hidden flex-col overflow-hidden px-12 py-10 lg:flex">
          <div className="absolute inset-0 auth-grid" />
          <div className="relative z-10 flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-950 text-white">
              <Icon name="spark" className="h-5 w-5" />
            </span>
            <span className="text-xl font-bold tracking-tight">
              Agent<span className="text-indigo-600">Platform</span>
            </span>
          </div>

          <div className="relative z-10 mx-auto flex w-full max-w-xl flex-1 flex-col justify-center pb-10 pt-4">
            <div className="flex justify-center">
              <MixiCompanion
                focus={focus}
                isLoginError={Boolean(loginError)}
                isLoginSuccess={isLoginSuccess}
                isSubmitting={isSubmitting}
                mouse={mouse}
                passwordLength={password.length}
                showPassword={showPassword}
              />
            </div>
          </div>
        </section>

        <section className="flex items-center justify-center px-5 py-8 sm:px-8 lg:justify-start">
          <div className="auth-card flex min-h-[610px] w-full max-w-[430px] flex-col justify-center rounded-[2.125rem] bg-white px-10 py-10 shadow-[0_30px_82px_rgba(15,23,42,0.16)] ring-1 ring-white/90">
            <div className="mb-10 flex items-center gap-3 lg:hidden">
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-950 text-white">
                <Icon name="spark" className="h-5 w-5" />
              </span>
              <span className="text-xl font-bold tracking-tight">
                Agent<span className="text-indigo-600">Platform</span>
              </span>
            </div>

            <div className="mb-6">
              <h2 className="text-3xl font-bold tracking-tight text-slate-950">{mode === 'login' ? '欢迎回来' : '创建开发者账号'}</h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                {mode === 'login' ? '登录 Agent 工作台，继续管理智能体、工具和任务。' : '注册后即可创建自己的 Agent 工作空间。'}
              </p>
            </div>

            <form autoComplete="off" className="space-y-4" key={mode} onSubmit={handleSubmit}>
              {mode === 'register' ? (
                <label className="block">
                  <span className="mb-2 block text-sm font-bold text-slate-700">显示名称</span>
                  <span className="flex h-11 items-center rounded-xl border border-slate-200 bg-white px-3 transition">
                    <Icon name="users" className="h-5 w-5 text-slate-400" />
                    <input
                      autoComplete="off"
                      className="ml-3 w-full border-0 bg-transparent text-sm font-medium text-slate-900 outline-none placeholder:text-slate-500"
                      disabled={isSubmitting || isLoginSuccess}
                      maxLength={120}
                      onChange={(event) => setDisplayName(event.target.value)}
                      placeholder="你的称呼"
                      required
                      value={displayName}
                    />
                  </span>
                </label>
              ) : null}

              <label className="block">
                <span className="mb-2 block text-sm font-bold text-slate-700">工作邮箱</span>
                <span className="flex h-11 items-center rounded-xl border border-slate-200 bg-white px-3 transition">
                  <Icon name="mail" className="h-5 w-5 text-slate-400" />
                  <input
                    autoComplete="off"
                    className="ml-3 w-full border-0 bg-transparent text-sm font-medium text-slate-900 outline-none placeholder:text-slate-500"
                    disabled={isSubmitting || isLoginSuccess}
                    onBlur={() => setFocus(null)}
                    onChange={(event) => {
                      setEmail(event.target.value)
                      if (loginError) setLoginError(null)
                      if (registrationNotice) setRegistrationNotice(null)
                    }}
                    onFocus={() => setFocus('email')}
                    placeholder="输入工作邮箱"
                    required
                    type="email"
                    value={email}
                  />
                </span>
              </label>

              <label className="block">
                <span className="mb-2 block text-sm font-bold text-slate-700">{mode === 'login' ? '登录密码' : '设置密码'}</span>
                <span className={`flex h-11 items-center rounded-xl bg-white px-3 transition ${loginError ? 'border border-rose-300' : 'border border-slate-200'}`}>
                  <Icon name="lock" className="h-5 w-5 text-slate-400" />
                  <input
                    autoComplete="new-password"
                    className="ml-3 w-full border-0 bg-transparent text-sm font-medium text-slate-900 outline-none placeholder:text-slate-500"
                    disabled={isSubmitting || isLoginSuccess}
                    minLength={mode === 'register' ? 8 : undefined}
                    onBlur={() => setFocus(null)}
                    onChange={(event) => {
                      setPassword(event.target.value)
                      if (loginError) setLoginError(null)
                    }}
                    onFocus={() => setFocus('password')}
                    placeholder="请输入密码"
                    required
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                  />
                  <button
                    aria-label={showPassword ? '隐藏密码' : '显示密码'}
                    className="rounded-lg p-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
                    disabled={isSubmitting || isLoginSuccess}
                    onClick={() => setShowPassword((current) => !current)}
                    onMouseDown={(event) => event.preventDefault()}
                    type="button"
                  >
                    <Icon name={showPassword ? 'eye-off' : 'eye'} className="h-5 w-5" />
                  </button>
                </span>
              </label>

              <button
                className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-slate-950 px-4 text-sm font-bold text-white transition hover:bg-slate-800 disabled:opacity-70"
                disabled={isSubmitting || isLoginSuccess}
                type="submit"
              >
                {isSubmitting ? (
                  <>
                    <Icon name="loader" className="h-4 w-4 animate-spin" />
                    正在连接
                  </>
                ) : isLoginSuccess ? (
                  <>
                    <Icon name="check" className="h-4 w-4" />
                    已连接工作台
                  </>
                ) : loginError ? (
                  <>
                    {mode === 'login' ? '重新登录' : '重新注册'}
                    <Icon name="refresh" className="h-4 w-4" />
                  </>
                ) : (
                  <>
                    {mode === 'login' ? '登录工作台' : '创建账号'}
                    <Icon name="arrow" className="h-4 w-4" />
                  </>
                )}
              </button>

              {loginError ? <p className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm font-semibold text-rose-700">{loginError}</p> : null}
              {registrationNotice ? (
                <p className="rounded-xl bg-emerald-50 px-3 py-2 text-sm font-semibold text-emerald-700" role="status">
                  {registrationNotice}
                </p>
              ) : null}
            </form>

            <p className="mt-6 text-center text-sm font-medium text-slate-500">
              {mode === 'login' ? '还没有账号？' : '已经有账号？'}{' '}
              <button
                className="font-bold text-slate-950 transition hover:text-indigo-700"
                onClick={() => {
                  setMode((current) => (current === 'login' ? 'register' : 'login'))
                  setDisplayName('')
                  setEmail('')
                  setPassword('')
                  setShowPassword(false)
                  setLoginError(null)
                  setRegistrationNotice(null)
                  setIsLoginSuccess(false)
                }}
                type="button"
              >
                {mode === 'login' ? '立即注册' : '返回登录'}
              </button>
            </p>
          </div>
        </section>
      </div>
    </main>
  )
}
