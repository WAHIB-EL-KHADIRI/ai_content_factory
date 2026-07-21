import { useState, useEffect } from 'react'
import { api, type Content } from '../api/client'
import LoadingSpinner from '../components/LoadingSpinner'
import { FileText, Plus } from 'lucide-react'

export default function ContentPage() {
  const [contents, setContents] = useState<Content[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({ project_id: '', topic: '', content_type: 'article', language: 'en', word_count: 1500 })
  const [creating, setCreating] = useState(false)
  const [selected, setSelected] = useState<Content | null>(null)

  useEffect(() => {
    loadContents()
  }, [])

  const loadContents = async () => {
    setLoading(true)
    try {
      const data = await api.get<{ contents: Content[] }>('/content?project_id=default').catch(() => ({ contents: [] }))
      setContents(data.contents || [])
    } catch { /* ignore */ }
    setLoading(false)
  }

  const handleCreate = async () => {
    if (!form.topic.trim()) return
    setCreating(true)
    try {
      const result = await api.post<Content>('/content', {
        ...form,
        project_id: form.project_id || 'default',
      })
      setContents(prev => [result, ...prev])
      setShowCreate(false)
      setForm({ project_id: '', topic: '', content_type: 'article', language: 'en', word_count: 1500 })
    } catch { /* ignore */ }
    setCreating(false)
  }

  const statusBadge = (status: string) => {
    const colors: Record<string, string> = {
      draft: 'badge-yellow', published: 'badge-green', review: 'badge-blue', archived: 'badge-red',
    }
    return <span className={colors[status] || 'badge-yellow'}>{status}</span>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Content</h1>
          <p className="text-gray-400 mt-1">Manage your AI-generated content</p>
        </div>
        <button onClick={() => setShowCreate(!showCreate)} className="btn-primary flex items-center gap-2">
          <Plus size={18} /> New Content
        </button>
      </div>

      {showCreate && (
        <div className="card space-y-4">
          <h2 className="text-lg font-semibold">Create New Content</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <input placeholder="Topic" className="input" value={form.topic} onChange={e => setForm({ ...form, topic: e.target.value })} />
            <select className="input" value={form.content_type} onChange={e => setForm({ ...form, content_type: e.target.value })}>
              <option value="article">Article</option>
              <option value="blog_post">Blog Post</option>
              <option value="social_media">Social Media</option>
              <option value="email">Email</option>
              <option value="video_script">Video Script</option>
            </select>
            <select className="input" value={form.language} onChange={e => setForm({ ...form, language: e.target.value })}>
              <option value="en">English</option>
              <option value="ar">Arabic</option>
              <option value="fr">French</option>
              <option value="es">Spanish</option>
            </select>
            <input type="number" placeholder="Word count" className="input" value={form.word_count} onChange={e => setForm({ ...form, word_count: parseInt(e.target.value) || 1500 })} />
          </div>
          <div className="flex gap-3">
            <button onClick={handleCreate} disabled={creating || !form.topic.trim()} className="btn-primary">
              {creating ? 'Creating...' : 'Generate Content'}
            </button>
            <button onClick={() => setShowCreate(false)} className="btn-secondary">Cancel</button>
          </div>
        </div>
      )}

      {loading ? <LoadingSpinner text="Loading content..." /> : (
        <div className="space-y-3">
          {contents.length === 0 ? (
            <div className="card text-center py-12 text-gray-500">
              <FileText size={48} className="mx-auto mb-3 opacity-50" />
              <p>No content yet. Create your first piece.</p>
            </div>
          ) : contents.map(c => (
            <div key={c.id} className="card cursor-pointer hover:border-gray-700 transition-colors" onClick={() => setSelected(selected?.id === c.id ? null : c)}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <FileText size={20} className="text-gray-400" />
                  <div>
                    <h3 className="font-medium">{c.title || 'Untitled'}</h3>
                    <p className="text-sm text-gray-500">{c.content_type} &middot; {c.language}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {statusBadge(c.status)}
                  <span className="text-xs text-gray-500">{c.created_at?.slice(0, 10)}</span>
                </div>
              </div>
              {selected?.id === c.id && (
                <div className="mt-4 pt-4 border-t border-gray-800">
                  <p className="text-sm text-gray-300 whitespace-pre-wrap max-h-64 overflow-y-auto">{c.content}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
