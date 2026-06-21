import { apiFetch } from './auth'


export type GitAuthType = 'public' | 'token' | 'ssh'

export type GitDataSource = {
  id: string
  name: string
  repository_url: string
  auth_type: GitAuthType
  default_branch: string
  status: string
  created_at: string
}

export type GitConnectionInput = {
  repository_url: string
  auth_type: GitAuthType
  credential?: string
}

export type GitConnectionTestResult = {
  repository_name: string
  branches: string[]
  default_branch: string
}

async function readJson<T>(response: Response): Promise<T> {
  if (response.ok) return response.json() as Promise<T>
  const body = (await response.json().catch(() => null)) as { detail?: string } | null
  throw new Error(body?.detail || '请求失败，请稍后重试。')
}

export async function listGitDataSources(): Promise<GitDataSource[]> {
  return readJson<GitDataSource[]>(await apiFetch('/git-data-sources'))
}

export async function testGitConnection(input: GitConnectionInput): Promise<GitConnectionTestResult> {
  return readJson<GitConnectionTestResult>(await apiFetch('/git-data-sources/test', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  }))
}

export async function createGitDataSource(
  input: GitConnectionInput & { default_branch: string },
): Promise<GitDataSource> {
  return readJson<GitDataSource>(await apiFetch('/git-data-sources', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  }))
}

export async function deleteGitDataSource(id: string): Promise<void> {
  const response = await apiFetch(`/git-data-sources/${id}`, { method: 'DELETE' })
  if (!response.ok) await readJson(response)
}
