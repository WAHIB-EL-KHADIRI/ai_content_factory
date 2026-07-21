import { useState } from 'react'
import { api } from '../api/client'
import { GitBranch, Play, X } from 'lucide-react'

interface WorkflowRun {
  id: string
  status: string
  started_at: string
  completed_at: string | null
  duration_seconds: number
  error: string | null
}

const templates = [
  { name: 'Article Workflow', key: 'article', description: 'Research → Write → SEO → Edit → Publish' },
  { name: 'Video Workflow', key: 'video', description: 'Script → Visuals → Audio → Assemble' },
  { name: 'Social Media Batch', key: 'social', description: 'Create content for multiple platforms' },
]

export default function Workflows() {
  const [runs, setRuns] = useState<WorkflowRun[]>([])
  const [activeTemplate, setActiveTemplate] = useState<string | null>(null)
  const [topic, setTopic] = useState('')
  const [creating, setCreating] = useState(false)

  const createAndRun = async (template: string) => {
    if (!topic.trim()) return
    setCreating(true)
    try {
      const result = await api.post<{ id: string }>(`/workflows/templates/${template}`, undefined)
      const runResult = await api.post<WorkflowRun>('/workflows/run', {
        workflow_id: result.id,
        context: { topic: topic.trim() },
      })
      setRuns(prev => [runResult, ...prev])
      setActiveTemplate(null)
      setTopic('')
    } catch { /* ignore */ }
    setCreating(false)
  }

  const statusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'badge-green'
      case 'failed': return 'badge-red'
      case 'running': return 'badge-yellow'
      default: return 'badge-blue'
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Workflows</h1>
        <p className="text-gray-400 mt-1">Automated content creation pipelines</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {templates.map(t => (
          <div key={t.key} className="card cursor-pointer hover:border-brand-600/50 transition-colors" onClick={() => setActiveTemplate(activeTemplate === t.key ? null : t.key)}>
            <div className="flex items-center gap-3 mb-2">
              <GitBranch size={20} className="text-brand-400" />
              <h3 className="font-medium">{t.name}</h3>
            </div>
            <p className="text-sm text-gray-400">{t.description}</p>
            {activeTemplate === t.key && (
              <div className="mt-4 pt-4 border-t border-gray-800 space-y-3">
                <input className="input" placeholder="Enter topic..." value={topic} onChange={e => setTopic(e.target.value)} />
                <div className="flex gap-2">
                  <button onClick={(e) => { e.stopPropagation(); createAndRun(t.key) }} disabled={creating || !topic.trim()} className="btn-primary text-sm flex items-center gap-2">
                    <Play size={16} /> Run Workflow
                  </button>
                  <button onClick={(e) => { e.stopPropagation(); setActiveTemplate(null) }} className="btn-secondary text-sm">
                    <X size={16} />
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {runs.length > 0 && (
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Recent Runs</h2>
          <div className="space-y-3">
            {runs.map(run => (
              <div key={run.id} className="flex items-center justify-between py-3 border-b border-gray-800 last:border-0">
                <div>
                  <p className="text-sm font-medium">Run {run.id.slice(0, 8)}</p>
                  <p className="text-xs text-gray-500">{run.started_at?.slice(0, 19)?.replace('T', ' ')}</p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-gray-400">{run.duration_seconds?.toFixed(1)}s</span>
                  <span className={statusColor(run.status)}>{run.status}</span>
                </div>
                {run.error && <p className="text-xs text-red-400 mt-1">{run.error}</p>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
