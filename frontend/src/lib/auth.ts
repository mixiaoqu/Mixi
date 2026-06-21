const API_BASE = '/api/v1'

export type AuthUser = {
  id: string
  email: string
  display_name: string
  avatar_url: string | null
}

type AuthResponse = {
  access_token: string
  token_type: 'bearer'
  expires_in: number
  user: AuthUser
}

export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

let accessToken: string | null = null
let refreshRequest: Promise<AuthResponse> | null = null

async function readResponse<T>(response: Response): Promise<T> {
  if (response.ok) return response.json() as Promise<T>

  const body = (await response.json().catch(() => null)) as { detail?: unknown } | null
  const message = typeof body?.detail === 'string' ? body.detail : '请检查输入内容后重试。'
  throw new ApiError(message, response.status)
}

async function refreshAccessToken(): Promise<AuthResponse> {
  if (!refreshRequest) {
    refreshRequest = fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
    })
      .then(readResponse<AuthResponse>)
      .then((session) => {
        accessToken = session.access_token
        return session
      })
      .finally(() => {
        refreshRequest = null
      })
  }
  return refreshRequest
}

export async function login(email: string, password: string): Promise<AuthUser> {
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  const session = await readResponse<AuthResponse>(response)
  accessToken = session.access_token
  return session.user
}

export async function register(email: string, displayName: string, password: string): Promise<AuthUser> {
  const response = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, display_name: displayName, password }),
  })
  return readResponse<AuthUser>(response)
}

export async function restoreSession(): Promise<AuthUser | null> {
  try {
    return (await refreshAccessToken()).user
  } catch (error) {
    accessToken = null
    if (error instanceof ApiError && error.status === 401) return null
    throw error
  }
}

export async function logout(): Promise<void> {
  try {
    await fetch(`${API_BASE}/auth/logout`, {
      method: 'POST',
      credentials: 'include',
      headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined,
    })
  } finally {
    accessToken = null
  }
}

export async function apiFetch(path: string, init: RequestInit = {}, retry = true): Promise<Response> {
  const headers = new Headers(init.headers)
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`)
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers, credentials: 'include' })
  if (response.status !== 401 || !retry) return response

  await refreshAccessToken()
  return apiFetch(path, init, false)
}
