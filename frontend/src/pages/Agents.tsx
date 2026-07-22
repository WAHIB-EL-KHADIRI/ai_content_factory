import { useState, useEffect } from 'react'
import { api, Agent } from '../api/client'
import LoadingSpinner from '../components/LoadingSpinner'
import { getErrorMessage } from '../lib/errors'
import { Bot, Play, ChevronDown, ChevronUp } from 'lucide-react'

export default function Agents() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<string | null>(null)
  const [taskInput, setTaskInput] = useState('')
  const [running, setRunning] = useState<string | null>(null)
  const [results, setResults] = useState<Record<string, string>>({})

  useEffect(() => {
    api.get<{ agents: Agent[] }>('/agents')
      .then(data => setAgents(data.agents || []))
      .catch(() => setAgents([]))
      .finally(() => setLoading(false))
  }, [])

  const runAgent = async (role: string) => {
    if (!taskInput.trim()) return
    setRunning(role)
    try {
      const result = await api.post<{ output: string }>('/agents/run', {
        agent_role: role,
        task: { instruction: taskInput },
      })
      setResults(prev => ({ ...prev, [role]: result.output || 'No output' }))
    } catch (err) {
      setResults(prev => ({ ...prev, [role]: `Error: ${getErrorMessage(err)}` }))
    }
    setRunning(null)
  }

  if (loading) return <LoadingSpinner text="Loading agents..." />

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Agents</h1>
        <p className="text-gray-400 mt-1">Multi-agent system for content creation</p>
      </div>

      <div className="card">
        <h2 className="text-lg font-semibold mb-3">Run Agent Task</h2>
        <div className="flex gap-3">
          <input
            className="input flex-1"
            placeholder="Describe the task..."
            value={taskInput}
            onChange={e => setTaskInput(e.target.value)}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {agents.map(agent => (
          <div key={agent.role} className="card">
            <div
              className="flex items-center justify-between cursor-pointer"
              onClick={() => setExpanded(expanded === agent.role ? null : agent.role)}
            >
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-brand-600/20">
                  <Bot size={20} className="text-brand-400" />
                </div>
                <div>
                  <h3 className="font-medium">{agent.name}</h3>
                  <p className="text-sm text-gray-400">{agent.description}</p>
                </div>
              </div>
              {expanded === agent.role ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
            </div>

            {expanded === agent.role && (
              <div className="mt-4 pt-4 border-t border-gray-800 space-y-3">
                <button
                  onClick={() => runAgent(agent.role)}
                  disabled={running === agent.role || !taskInput.trim()}
                  className="btn-primary flex items-center gap-2 text-sm"
                >
                  {running === agent.role ? (
                    <>Running...</>
                  ) : (
                    <><Play size={16} /> Run Task</>
                  )}
                </button>
                {results[agent.role] && (
                  <div className="bg-gray-800 rounded-lg p-4">
                    <p className="text-sm text-gray-300 whitespace-pre-wrap">{results[agent.role]}</p>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
