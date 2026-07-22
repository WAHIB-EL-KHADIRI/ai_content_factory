import { useState, useEffect } from 'react'
import { api } from '../api/client'
import LoadingSpinner from '../components/LoadingSpinner'
import { BarChart3, TrendingUp, DollarSign, Clock } from 'lucide-react'

interface CostBreakdown {
  total_cost: number
  by_model: Record<string, number>
  by_task: Record<string, number>
}

interface PerformanceReport {
  total_calls: number
  avg_latency_ms: number
  total_tokens: number
}

export default function Analytics() {
  const [dashboard, setDashboard] = useState<Record<string, unknown> | null>(null)
  const [costs, setCosts] = useState<CostBreakdown | null>(null)
  const [performance, setPerformance] = useState<PerformanceReport | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      api.get('/analytics/dashboard').catch(() => null),
      api.get('/analytics/costs').catch(() => null),
      api.get('/analytics/performance').catch(() => null),
    ]).then(([d, c, p]) => {
      setDashboard(d as Record<string, unknown>)
      setCosts(c as CostBreakdown)
      setPerformance(p as PerformanceReport)
    }).finally(() => setLoading(false))
  }, [])

  if (loading) return <LoadingSpinner text="Loading analytics..." />

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Analytics</h1>
        <p className="text-gray-400 mt-1">Monitor usage, costs, and performance</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="card flex items-center gap-4">
          <div className="p-3 rounded-lg bg-brand-600/20 text-brand-400">
            <BarChart3 size={22} />
          </div>
          <div>
            <p className="text-2xl font-bold">{performance?.total_calls || 0}</p>
            <p className="text-sm text-gray-400">Total API Calls</p>
          </div>
        </div>
        <div className="card flex items-center gap-4">
          <div className="p-3 rounded-lg bg-green-600/20 text-green-400">
            <DollarSign size={22} />
          </div>
          <div>
            <p className="text-2xl font-bold">${(costs?.total_cost || 0).toFixed(3)}</p>
            <p className="text-sm text-gray-400">Total Cost</p>
          </div>
        </div>
        <div className="card flex items-center gap-4">
          <div className="p-3 rounded-lg bg-yellow-600/20 text-yellow-400">
            <Clock size={22} />
          </div>
          <div>
            <p className="text-2xl font-bold">{(performance?.avg_latency_ms || 0).toFixed(0)}ms</p>
            <p className="text-sm text-gray-400">Avg Latency</p>
          </div>
        </div>
        <div className="card flex items-center gap-4">
          <div className="p-3 rounded-lg bg-purple-600/20 text-purple-400">
            <TrendingUp size={22} />
          </div>
          <div>
            <p className="text-2xl font-bold">{performance?.total_tokens || 0}</p>
            <p className="text-sm text-gray-400">Total Tokens</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Cost by Model</h2>
          <div className="space-y-3">
            {costs?.by_model && Object.entries(costs.by_model).length > 0 ? (
              Object.entries(costs.by_model).map(([model, cost]) => (
                <div key={model} className="flex items-center justify-between">
                  <span className="text-sm">{model}</span>
                  <div className="flex items-center gap-3">
                    <div className="w-32 bg-gray-800 rounded-full h-2">
                      <div className="bg-brand-500 h-2 rounded-full" style={{ width: `${Math.min(100, (cost / (costs.total_cost || 1)) * 100)}%` }} />
                    </div>
                    <span className="text-sm text-gray-400 w-16 text-right">${cost.toFixed(4)}</span>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-sm text-gray-500">No cost data yet</p>
            )}
          </div>
        </div>

        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Usage by Task</h2>
          <div className="space-y-3">
            {costs?.by_task && Object.entries(costs.by_task).length > 0 ? (
              Object.entries(costs.by_task).map(([task, cost]) => (
                <div key={task} className="flex items-center justify-between">
                  <span className="text-sm capitalize">{task.replace(/_/g, ' ')}</span>
                  <span className="text-sm text-gray-400">${cost.toFixed(4)}</span>
                </div>
              ))
            ) : (
              <p className="text-sm text-gray-500">No task data yet</p>
            )}
          </div>
        </div>
      </div>

      <div className="card">
        <h2 className="text-lg font-semibold mb-4">Recent Activity</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800">
                <th className="text-left py-3 text-gray-400 font-medium">Action</th>
                <th className="text-left py-3 text-gray-400 font-medium">User</th>
                <th className="text-left py-3 text-gray-400 font-medium">Model</th>
                <th className="text-left py-3 text-gray-400 font-medium">Cost</th>
                <th className="text-left py-3 text-gray-400 font-medium">Time</th>
              </tr>
            </thead>
            <tbody>
              {(dashboard?.recent_activity as Record<string, unknown>[])?.slice(0, 10).map((row, i) => (
                <tr key={i} className="border-b border-gray-800/50">
                  <td className="py-3">{String(row.action || '-')}</td>
                  <td className="py-3 text-gray-400">{String(row.user_id || '-')}</td>
                  <td className="py-3 text-gray-400">{String(row.model || '-')}</td>
                  <td className="py-3 text-gray-400">${Number(row.cost || 0).toFixed(4)}</td>
                  <td className="py-3 text-gray-500 text-xs">{String(row.timestamp || '-')}</td>
                </tr>
              )) || (
                <tr><td colSpan={5} className="py-6 text-center text-gray-500">No activity yet</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
