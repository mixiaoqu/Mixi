import { useEffect, useState, type FormEvent } from 'react'
import { Icon } from '../components/Icon'
import GoogleIcon from '../components/auth/GoogleIcon'
import LumiCompanion, { type AuthFocus } from '../components/auth/LumiCompanion'
import '../styles/auth.css'

type LoginPageProps = {
  onLogin: () => void
}

export default function LoginPage({ onLogin }: LoginPageProps) {
  const [focus, setFocus] = useState<AuthFocus>(null)
  const [showPassword, setShowPassword] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isLoginSuccess, setIsLoginSuccess] = useState(false)
  const [loginError, setLoginError] = useState<string | null>(null)
  const [mouse, setMouse] = useState({ x: 0, y: 0, movedAt: 0 })

  useEffect(() => {
    function handleMouseMove(event: MouseEvent) {
      setMouse({ x: event.clientX, y: event.clientY, movedAt: Date.now() })
    }

    window.addEventListener('mousemove', handleMouseMove)
    return () => window.removeEventListener('mousemove', handleMouseMove)
  }, [])

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setIsSubmitting(true)
    setIsLoginSuccess(false)
    setLoginError(null)

    window.setTimeout(() => {
      if (password.trim().length < 8) {
        setIsSubmitting(false)
        setFocus('password')
        setLoginError('登录失败，请检查邮箱和密码后重试。')
        return
      }

      setIsSubmitting(false)
      setIsLoginSuccess(true)

      window.setTimeout(() => {
        onLogin()
      }, 900)
    }, 850)
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
              <LumiCompanion
                focus={focus}
                showPassword={showPassword}
                passwordLength={password.length}
                isSubmitting={isSubmitting}
                isLoginSuccess={isLoginSuccess}
                isLoginError={Boolean(loginError)}
                mouse={mouse}
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
              <h2 className="text-3xl font-bold tracking-tight text-slate-950">欢迎回来</h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">登录 Agent 工作台，继续管理智能体、工具与任务。</p>
            </div>

            <form autoComplete="off" className="space-y-4" onSubmit={handleSubmit}>
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
                <span className="mb-2 flex items-center justify-between text-sm font-bold text-slate-700">
                  登录密码
                  <a className="text-sm font-semibold text-indigo-700 hover:text-indigo-800" href="#">
                    忘记密码？
                  </a>
                </span>
                <span className={`flex h-11 items-center rounded-xl bg-white px-3 transition ${loginError ? 'border border-rose-300' : 'border border-slate-200'}`}>
                  <Icon name="lock" className="h-5 w-5 text-slate-400" />
                  <input
                    autoComplete="new-password"
                    className="ml-3 w-full border-0 bg-transparent text-sm font-medium text-slate-900 outline-none placeholder:text-slate-500"
                    disabled={isSubmitting || isLoginSuccess}
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

              <div className="flex items-center justify-between text-sm">
                <label className="inline-flex items-center gap-2 font-semibold text-slate-600">
                  <input className="h-4 w-4 rounded border-slate-300 accent-indigo-600" type="checkbox" />
                  保持登录状态
                </label>
              </div>

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
                    重新登录
                    <Icon name="refresh" className="h-4 w-4" />
                  </>
                ) : (
                  <>
                    登录工作台
                    <Icon name="arrow" className="h-4 w-4" />
                  </>
                )}
              </button>

              {loginError ? <p className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm font-semibold text-rose-700">{loginError}</p> : null}
            </form>

            <div className="my-5 flex items-center gap-4">
              <span className="h-px flex-1 bg-slate-200" />
              <span className="text-xs font-semibold text-slate-500">或使用第三方账号</span>
              <span className="h-px flex-1 bg-slate-200" />
            </div>

            <button className="inline-flex h-11 w-full items-center justify-center gap-3 rounded-xl border border-slate-200 bg-white px-4 text-sm font-bold text-slate-700 transition hover:bg-slate-50" type="button">
              <GoogleIcon />
              使用 Google 登录
            </button>

            <p className="mt-6 text-center text-sm font-medium text-slate-500">
              还没有工作区？{' '}
              <a className="font-bold text-slate-950 hover:text-indigo-700" href="#">
                创建工作区
              </a>
            </p>
          </div>
        </section>
      </div>
    </main>
  )
}
