import { useState, useEffect } from 'react'
import { api, DashboardData } from '../api/client'
import LoadingSpinner from '../components/LoadingSpinner'
import { Activity, Cpu, DollarSign, TrendingUp, type LucideIcon } from 'lucide-react'

function StatCard({ icon: Icon, label, value, color }: { icon: LucideIcon; label: string; value: string | number; color: string }) {
  return (
    <div className="card flex items-center gap-4">
      <div className={`p-3 rounded-lg ${color}`}>
        <Icon size={22} />
      </div>
      <div>
        <p className="text-2xl font-bold">{value}</p>
        <p className="text-sm text-gray-400">{label}</p>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([
      api.get<DashboardData>('/analytics/dashboard').catch(() => null),
    ]).then(([dashboard]) => {
      setData(dashboard)
      setLoading(false)
    }).catch(() => {
      setError('Failed to load dashboard')
      setLoading(false)
    })
  }, [])

  if (loading) return <LoadingSpinner text="Loading dashboard..." />
  if (error) return <div className="text-red-400 text-center py-12">{error}</div>

  const summary = (data?.summary as Record<string, unknown>) || {}
  const activity = (data?.recent_activity as Record<string, unknown>[]) || []

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-gray-400 mt-1">AI Content Operating System overview</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={Activity} label="Total Operations" value={Number(summary.total_contents || 0)} color="bg-brand-600/20 text-brand-400" />
        <StatCard icon={Cpu} label="Active Agents" value={Number(summary.active_agents || 0)} color="bg-green-600/20 text-green-400" />
        <StatCard icon={DollarSign} label="Cost (24h)" value={`$${Number(summary.total_cost_24h || 0).toFixed(2)}`} color="bg-yellow-600/20 text-yellow-400" />
        <StatCard icon={TrendingUp} label="Brand Consistency" value={`${Number(summary.brand_consistency_avg || 0)}%`} color="bg-purple-600/20 text-purple-400" />
      </div>

      <div className="card">
        <h2 className="text-lg font-semibold mb-4">Recent Activity</h2>
        {activity.length === 0 ? (
          <p className="text-gray-500 text-sm">No recent activity</p>
        ) : (
          <div className="space-y-3">
            {activity.slice(0, 5).map((item, i) => (
              <div key={i} className="flex items-center justify-between py-2 border-b border-gray-800 last:border-0">
                <span className="text-sm">{String(item.action || 'Operation')}</span>
                <span className="text-xs text-gray-500">{String(item.timestamp || '')}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="card">
        <h2 className="text-lg font-semibold mb-4">Quick Actions</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: 'New Content', href: '/content', color: 'bg-brand-600' },
            { label: 'AI Chat', href: '/chat', color: 'bg-green-600' },
            { label: 'Run Workflow', href: '/workflows', color: 'bg-purple-600' },
            { label: 'View Analytics', href: '/analytics', color: 'bg-yellow-600' },
          ].map(a => (
            <a key={a.href} href={a.href} className={`${a.color} hover:opacity-90 text-white text-center py-3 rounded-lg font-medium text-sm transition-opacity`}>
              {a.label}
            </a>
          ))}
        </div>
      </div>
    </div>
  )
}
