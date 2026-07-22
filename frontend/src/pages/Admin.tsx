import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, User, AdminStats } from '../api/client'
import { useAuth } from '../hooks/useAuth'
import { useToast } from '../hooks/useToast'
import DataTable, { Column } from '../components/DataTable'
import { Spinner } from '../components/LoadingStates'
import {
  Users, FileText, Zap, Clock, Shield, ChevronDown,
} from 'lucide-react'

interface AuditLog {
  id: string
  user_id: string
  user_email: string
  action: string
  resource: string
  timestamp: string
  details: string
}

export default function Admin() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const { toast } = useToast()
  const [stats, setStats] = useState<AdminStats | null>(null)
  const [users, setUsers] = useState<User[]>([])
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'users' | 'audit'>('users')

  useEffect(() => {
    if (user && user.role !== 'admin') {
      navigate('/', { replace: true })
    }
  }, [user, navigate])

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const [statsRes, usersRes, logsRes] = await Promise.allSettled([
        api.get<AdminStats>('/admin/stats'),
        api.get<{ items: User[] }>('/admin/users'),
        api.get<{ items: AuditLog[] }>('/admin/audit-log'),
      ])
      if (statsRes.status === 'fulfilled') setStats(statsRes.value)
      if (usersRes.status === 'fulfilled') setUsers(usersRes.value.items || [])
      if (logsRes.status === 'fulfilled') setAuditLogs(logsRes.value.items || [])
    } catch {
      toast.error('Failed to load admin data')
    } finally {
      setLoading(false)
    }
  }, [toast])

  useEffect(() => { loadData() }, [loadData])

  const handleRoleChange = async (userId: string, newRole: string) => {
    try {
      await api.put(`/admin/users/${userId}`, { role: newRole })
      toast.success('User role updated')
      setUsers(prev => prev.map(u => u.id === userId ? { ...u, role: newRole } : u))
    } catch {
      toast.error('Failed to update role')
    }
  }

  const handleToggleActive = async (userId: string, isActive: boolean) => {
    try {
      await api.put(`/admin/users/${userId}`, { is_active: !isActive })
      toast.success(`User ${!isActive ? 'activated' : 'deactivated'}`)
      setUsers(prev => prev.map(u => u.id === userId ? { ...u, is_active: !isActive } : u))
    } catch {
      toast.error('Failed to update user')
    }
  }

  if (user?.role !== 'admin') return null

  const userColumns: Column<User>[] = [
    {
      key: 'name',
      header: 'User',
      sortable: true,
      render: u => (
        <div>
          <p className="font-medium text-gray-100">{u.name}</p>
          <p className="text-xs text-gray-500">{u.email}</p>
        </div>
      ),
    },
    {
      key: 'role',
      header: 'Role',
      sortable: true,
      render: u => (
        <div className="relative">
          <select
            value={u.role}
            onChange={e => handleRoleChange(u.id, e.target.value)}
            className="appearance-none bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm text-gray-200 cursor-pointer pr-6 focus:ring-1 focus:ring-brand-500 focus:outline-none"
          >
            <option value="user">User</option>
            <option value="admin">Admin</option>
          </select>
          <ChevronDown className="absolute right-1.5 top-1/2 -translate-y-1/2 pointer-events-none text-gray-500" size={12} />
        </div>
      ),
    },
    {
      key: 'is_active',
      header: 'Status',
      render: u => (
        <button
          onClick={() => handleToggleActive(u.id, u.is_active)}
          className={`badge cursor-pointer ${u.is_active ? 'badge-green' : 'badge-red'}`}
        >
          {u.is_active ? 'Active' : 'Inactive'}
        </button>
      ),
    },
    {
      key: 'created_at',
      header: 'Joined',
      sortable: true,
      className: 'text-gray-400 text-sm',
    },
  ]

  const statCards = stats
    ? [
        { icon: Users, label: 'Total Users', value: stats.total_users, color: 'bg-brand-600/20 text-brand-400' },
        { icon: FileText, label: 'Total Content', value: stats.total_content, color: 'bg-green-600/20 text-green-400' },
        { icon: Zap, label: 'API Calls Today', value: stats.api_calls_today, color: 'bg-yellow-600/20 text-yellow-400' },
        { icon: Clock, label: 'Uptime (hours)', value: stats.uptime_hours, color: 'bg-purple-600/20 text-purple-400' },
      ]
    : []

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Shield className="text-brand-400" size={28} />
        <div>
          <h1 className="text-3xl font-bold">Admin</h1>
          <p className="text-gray-400 mt-0.5">System management and overview</p>
        </div>
      </div>

      {loading ? (
        <Spinner />
      ) : (
        <>
          {stats && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {statCards.map(s => (
                <div key={s.label} className="card flex items-center gap-4">
                  <div className={`p-3 rounded-lg ${s.color}`}>
                    <s.icon size={22} />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{s.value}</p>
                    <p className="text-sm text-gray-400">{s.label}</p>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="flex gap-1 border-b border-gray-800">
            {(['users', 'audit'] as const).map(tab => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab
                    ? 'border-brand-500 text-brand-400'
                    : 'border-transparent text-gray-400 hover:text-gray-200'
                }`}
              >
                {tab === 'users' ? 'User Management' : 'Audit Log'}
              </button>
            ))}
          </div>

          {activeTab === 'users' && (
            <DataTable
              columns={userColumns}
              data={users}
              keyExtractor={u => u.id}
              emptyMessage="No users found"
            />
          )}

          {activeTab === 'audit' && (
            <div className="card">
              {auditLogs.length === 0 ? (
                <p className="text-gray-500 text-center py-8">No audit logs found</p>
              ) : (
                <div className="space-y-3">
                  {auditLogs.map(log => (
                    <div key={log.id} className="flex items-start justify-between py-3 border-b border-gray-800 last:border-0 gap-4">
                      <div className="min-w-0">
                        <p className="text-sm">
                          <span className="font-medium text-gray-200">{log.user_email}</span>
                          {' '}{log.action}{' '}
                          <span className="text-brand-400">{log.resource}</span>
                        </p>
                        {log.details && (
                          <p className="text-xs text-gray-500 mt-1 truncate">{log.details}</p>
                        )}
                      </div>
                      <span className="text-xs text-gray-500 whitespace-nowrap flex-shrink-0">
                        {log.timestamp}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}
