import type { AuthUser } from '../lib/auth'

export default function SettingsPage({ user }: { user: AuthUser }) {
  return (
    <section className="mx-auto max-w-5xl px-4 py-10 sm:px-6 lg:py-14">
      <div className="max-w-2xl">
        <h1 className="text-3xl font-bold tracking-tight text-slate-950">设置</h1>
        <p className="mt-3 text-sm leading-6 text-slate-600 sm:text-base">查看个人账户信息和平台偏好。</p>
      </div>

      <div className="mt-8 max-w-2xl rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
        <h2 className="text-base font-bold text-slate-950">个人信息</h2>
        <dl className="mt-5 divide-y divide-slate-100">
          <div className="grid gap-1 py-4 sm:grid-cols-[9rem_1fr] sm:gap-4">
            <dt className="text-sm font-semibold text-slate-500">显示名称</dt>
            <dd className="text-sm font-semibold text-slate-900">{user.display_name}</dd>
          </div>
          <div className="grid gap-1 py-4 sm:grid-cols-[9rem_1fr] sm:gap-4">
            <dt className="text-sm font-semibold text-slate-500">邮箱</dt>
            <dd className="break-all text-sm font-semibold text-slate-900">{user.email}</dd>
          </div>
        </dl>
      </div>
    </section>
  )
}
