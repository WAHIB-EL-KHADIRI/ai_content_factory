import { useState, useEffect } from 'react'
import { api, Memory } from '../api/client'
import LoadingSpinner from '../components/LoadingSpinner'
import { Search, Plus, Brain } from 'lucide-react'

export default function MemoryPage() {
  const [memories, setMemories] = useState<Memory[]>([])
  const [loading, setLoading] = useState(false)
  const [query, setQuery] = useState('')
  const [showStore, setShowStore] = useState(false)
  const [storeForm, setStoreForm] = useState({ content: '', memory_type: 'fact', importance: 0.5 })
  const [userContext, setUserContext] = useState<Record<string, unknown> | null>(null)

  const searchMemory = async () => {
    if (!query.trim()) return
    setLoading(true)
    try {
      const data = await api.post<{ memories: Memory[] }>('/memory/recall', {
        query: query.trim(),
        limit: 10,
      })
      setMemories(data.memories || [])
    } catch { /* ignore */ }
    setLoading(false)
  }

  const storeMemory = async () => {
    if (!storeForm.content.trim()) return
    try {
      await api.post('/memory/store', {
        content: storeForm.content,
        memory_type: storeForm.memory_type,
        importance: storeForm.importance,
      })
      setShowStore(false)
      setStoreForm({ content: '', memory_type: 'fact', importance: 0.5 })
      if (query.trim()) searchMemory()
    } catch { /* ignore */ }
  }

  const loadUserContext = async () => {
    try {
      const data = await api.get<Record<string, unknown>>('/memory/context/user/default')
      setUserContext(data)
    } catch { /* ignore */ }
  }

  useEffect(() => { loadUserContext() }, [])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Memory System</h1>
          <p className="text-gray-400 mt-1">Long-term memory for AI context</p>
        </div>
        <button onClick={() => setShowStore(!showStore)} className="btn-primary flex items-center gap-2">
          <Plus size={18} /> Store Memory
        </button>
      </div>

      {showStore && (
        <div className="card space-y-4">
          <h2 className="text-lg font-semibold">Store New Memory</h2>
          <textarea className="input resize-none" rows={3} placeholder="Memory content..." value={storeForm.content} onChange={e => setStoreForm({ ...storeForm, content: e.target.value })} />
          <div className="grid grid-cols-2 gap-4">
            <select className="input" value={storeForm.memory_type} onChange={e => setStoreForm({ ...storeForm, memory_type: e.target.value })}>
              <option value="fact">Fact</option>
              <option value="preference">Preference</option>
              <option value="context">Context</option>
              <option value="instruction">Instruction</option>
              <option value="experience">Experience</option>
              <option value="insight">Insight</option>
            </select>
            <div className="flex items-center gap-3">
              <label className="text-sm text-gray-400">Importance:</label>
              <input type="range" min="0" max="1" step="0.1" value={storeForm.importance} onChange={e => setStoreForm({ ...storeForm, importance: parseFloat(e.target.value) })} className="flex-1" />
              <span className="text-sm">{storeForm.importance}</span>
            </div>
          </div>
          <div className="flex gap-3">
            <button onClick={storeMemory} disabled={!storeForm.content.trim()} className="btn-primary">Store</button>
            <button onClick={() => setShowStore(false)} className="btn-secondary">Cancel</button>
          </div>
        </div>
      )}

      <div className="card">
        <div className="flex gap-3">
          <div className="relative flex-1">
            <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
            <input className="input pl-10" placeholder="Search memories..." value={query} onChange={e => setQuery(e.target.value)} onKeyDown={e => e.key === 'Enter' && searchMemory()} />
          </div>
          <button onClick={searchMemory} disabled={loading} className="btn-primary">
            {loading ? 'Searching...' : 'Search'}
          </button>
        </div>
      </div>

      {loading ? <LoadingSpinner text="Searching memories..." /> : (
        <div className="space-y-3">
          {memories.map(mem => (
            <div key={mem.id} className="card">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Brain size={16} className="text-purple-400" />
                  <span className="badge-blue">{mem.memory_type}</span>
                </div>
                <span className="text-xs text-gray-500">Relevance: {(mem.relevance * 100).toFixed(0)}%</span>
              </div>
              <p className="text-sm text-gray-300">{mem.content}</p>
            </div>
          ))}
          {memories.length === 0 && query && (
            <div className="card text-center py-8 text-gray-500">
              <p>No memories found for "{query}"</p>
            </div>
          )}
        </div>
      )}

      {userContext && (
        <div className="card">
          <h2 className="text-lg font-semibold mb-3">User Context</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(userContext).map(([key, value]) => (
              <div key={key} className="text-center">
                <p className="text-lg font-bold">{String(value)}</p>
                <p className="text-sm text-gray-400 capitalize">{key.replace(/_/g, ' ')}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
