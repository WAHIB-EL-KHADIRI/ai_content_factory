import { useState, useEffect } from 'react'
import { api } from '../api/client'
import LoadingSpinner from '../components/LoadingSpinner'
import { Puzzle } from 'lucide-react'

interface Plugin {
  name: string
  version: string
  description: string
  type: string
}

interface PluginInfo {
  version?: string
  description?: string
  type?: string
}

export default function Plugins() {
  const [plugins, setPlugins] = useState<Plugin[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get<{ plugins: Record<string, unknown> }>('/plugins')
      .then(data => {
        const list = Object.entries(data.plugins || {}).map(([name, raw]) => {
          const info = raw as PluginInfo
          return {
            name,
            version: info.version || '1.0.0',
            description: info.description || 'No description',
            type: info.type || 'unknown',
          }
        })
        setPlugins(list)
      })
      .catch(() => setPlugins([]))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <LoadingSpinner text="Loading plugins..." />

  const typeBadge = (type: string) => {
    switch (type) {
      case 'integration': return 'badge-blue'
      case 'tool': return 'badge-green'
      case 'agent': return 'badge-yellow'
      default: return 'badge-blue'
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Plugins</h1>
        <p className="text-gray-400 mt-1">Extend AI Content OS with plugins</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {plugins.map(plugin => (
          <div key={plugin.name} className="card">
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-gray-800">
                  <Puzzle size={20} className="text-brand-400" />
                </div>
                <div>
                  <h3 className="font-medium">{plugin.name}</h3>
                  <p className="text-xs text-gray-500">v{plugin.version}</p>
                </div>
              </div>
              <span className={typeBadge(plugin.type)}>{plugin.type}</span>
            </div>
            <p className="text-sm text-gray-400 mb-3">{plugin.description}</p>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-green-400"></div>
              <span className="text-xs text-green-400">Active</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
