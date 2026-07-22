const API_BASE = '/api/v1'

interface RequestOptions extends RequestInit {
  token?: string
}

class ApiClient {
  private getToken: (() => string | null) | null = null

  setTokenGetter(getter: () => string | null) {
    this.getToken = getter
  }

  private async request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const { token, ...fetchOptions } = options

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...((options.headers as Record<string, string>) || {}),
    }

    const authToken = token || this.getToken?.()
    if (authToken) {
      headers['Authorization'] = `Bearer ${authToken}`
    }

    const response = await fetch(`${API_BASE}${path}`, {
      ...fetchOptions,
      headers,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }))
      throw new Error(error.detail || `HTTP ${response.status}`)
    }

    return response.json()
  }

  get<T>(path: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(path, { ...options, method: 'GET' })
  }

  post<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>(path, {
      ...options,
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
    })
  }

  put<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>(path, {
      ...options,
      method: 'PUT',
      body: body ? JSON.stringify(body) : undefined,
    })
  }

  delete<T>(path: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(path, { ...options, method: 'DELETE' })
  }

  async stream(path: string, body: unknown, onChunk: (data: Record<string, unknown>) => void): Promise<void> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    const token = this.getToken?.()
    if (token) headers['Authorization'] = `Bearer ${token}`

    const response = await fetch(`${API_BASE}${path}`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    })

    if (!response.ok) throw new Error(`HTTP ${response.status}`)

    const reader = response.body?.getReader()
    if (!reader) return

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            onChunk(data)
          } catch { /* ignore */ }
        }
      }
    }
  }

  // ── Webhook methods ──────────────────────────────────────────

  listWebhooks(params?: string): Promise<{ items: Webhook[]; total: number }> {
    const q = params ? `?${params}` : ''
    return this.get(`/webhooks${q}`)
  }

  getWebhook(id: string): Promise<Webhook> {
    return this.get(`/webhooks/${id}`)
  }

  createWebhook(data: Partial<Webhook>): Promise<Webhook> {
    return this.post('/webhooks', data)
  }

  updateWebhook(id: string, data: Partial<Webhook>): Promise<Webhook> {
    return this.put(`/webhooks/${id}`, data)
  }

  deleteWebhook(id: string): Promise<void> {
    return this.delete(`/webhooks/${id}`)
  }

  // ── Admin methods ────────────────────────────────────────────

  getAdminStats(): Promise<AdminStats> {
    return this.get('/admin/stats')
  }

  listAdminUsers(params?: string): Promise<{ items: User[]; total: number }> {
    const q = params ? `?${params}` : ''
    return this.get(`/admin/users${q}`)
  }

  updateAdminUser(userId: string, data: { role?: string; is_active?: boolean }): Promise<User> {
    return this.put(`/admin/users/${userId}`, data)
  }

  listAuditLog(params?: string): Promise<{ items: AuditLogEntry[]; total: number }> {
    const q = params ? `?${params}` : ''
    return this.get(`/admin/audit-log${q}`)
  }

  // ── Project methods ──────────────────────────────────────────

  listProjects(params?: string): Promise<{ items: Project[]; total: number; pages: number }> {
    const q = params ? `?${params}` : ''
    return this.get(`/projects${q}`)
  }

  getProject(id: string): Promise<Project> {
    return this.get(`/projects/${id}`)
  }

  createProject(data: Partial<Project>): Promise<Project> {
    return this.post('/projects', data)
  }

  updateProject(id: string, data: Partial<Project>): Promise<Project> {
    return this.put(`/projects/${id}`, data)
  }

  deleteProject(id: string): Promise<void> {
    return this.delete(`/projects/${id}`)
  }

  // ── Template methods ─────────────────────────────────────────

  listTemplates(): Promise<{ items: ContentTemplate[] }> {
    return this.get('/templates')
  }

  getTemplate(id: string): Promise<ContentTemplate> {
    return this.get(`/templates/${id}`)
  }

  createFromTemplate(id: string, data: Record<string, unknown>): Promise<{ id: string }> {
    return this.post(`/templates/${id}/create`, data)
  }
}

export const api = new ApiClient()

export interface User {
  id: string
  email: string
  name: string
  role: string
  is_active: boolean
  created_at: string | null
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: User
}

export interface ModelInfo {
  provider: string
  model: string
  tier: string
  cost_per_1k_input: number
  cost_per_1k_output: number
  max_tokens: number
  supports_vision: boolean
  quality_rating: number
  latency_rating: number
}

export interface Agent {
  name: string
  role: string
  description: string
}

export interface Content {
  id: string
  project_id: string
  title: string
  content: string
  content_type: string
  status: string
  language: string
  created_at: string
}

export interface Brand {
  id: string
  name: string
  description: string
  voice_tone: string
  keywords: string[]
}

export interface Memory {
  id: string
  content: string
  memory_type: string
  relevance: number
  created_at: string
}

export interface DashboardData {
  summary: Record<string, unknown>
  recent_activity: Record<string, unknown>[]
}

export interface Webhook {
  id: string
  name: string
  url: string
  events: string[]
  secret: string
  is_active: boolean
  last_triggered: string | null
  created_at: string
}

export interface AdminStats {
  total_users: number
  total_content: number
  api_calls_today: number
  uptime_hours: number
}

export interface AuditLogEntry {
  id: string
  user_id: string
  user_email: string
  action: string
  resource: string
  timestamp: string
  details: string
}

export interface Project {
  id: string
  name: string
  description: string
  status: 'active' | 'archived' | 'draft'
  content_count: number
  created_at: string
}

export interface ContentTemplate {
  id: string
  name: string
  description: string
  content_type: string
  prompt_template: string
}
