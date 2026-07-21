import { useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { api } from '../api/client'
import { Key, Shield, User } from 'lucide-react'

export default function Settings() {
  const { user } = useAuth()
  const [passwordForm, setPasswordForm] = useState({ current_password: '', new_password: '' })
  const [apiKeyName, setApiKeyName] = useState('')
  const [newApiKey, setNewApiKey] = useState<string | null>(null)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const changePassword = async () => {
    setError('')
    setMessage('')
    try {
      await api.post('/auth/change-password', passwordForm)
      setMessage('Password changed successfully')
      setPasswordForm({ current_password: '', new_password: '' })
    } catch (err: any) {
      setError(err.message)
    }
  }

  const createApiKey = async () => {
    if (!apiKeyName.trim()) return
    setError('')
    try {
      const result = await api.post<{ key: string; name: string }>('/api-keys', { name: apiKeyName })
      setNewApiKey(result.key)
      setApiKeyName('')
    } catch (err: any) {
      setError(err.message)
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Settings</h1>
        <p className="text-gray-400 mt-1">Manage your account and API keys</p>
      </div>

      {message && <div className="card bg-green-900/20 border-green-800 text-green-400">{message}</div>}
      {error && <div className="card bg-red-900/20 border-red-800 text-red-400">{error}</div>}

      {/* Profile */}
      <div className="card">
        <div className="flex items-center gap-3 mb-4">
          <User size={20} className="text-brand-400" />
          <h2 className="text-lg font-semibold">Profile</h2>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm text-gray-400">Name</label>
            <p className="font-medium">{user?.name}</p>
          </div>
          <div>
            <label className="text-sm text-gray-400">Email</label>
            <p className="font-medium">{user?.email}</p>
          </div>
          <div>
            <label className="text-sm text-gray-400">Role</label>
            <p className="font-medium capitalize">{user?.role}</p>
          </div>
          <div>
            <label className="text-sm text-gray-400">Member since</label>
            <p className="font-medium">{user?.created_at?.slice(0, 10) || 'N/A'}</p>
          </div>
        </div>
      </div>

      {/* Change Password */}
      <div className="card">
        <div className="flex items-center gap-3 mb-4">
          <Shield size={20} className="text-yellow-400" />
          <h2 className="text-lg font-semibold">Change Password</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <input type="password" className="input" placeholder="Current password" value={passwordForm.current_password} onChange={e => setPasswordForm({ ...passwordForm, current_password: e.target.value })} />
          <input type="password" className="input" placeholder="New password" value={passwordForm.new_password} onChange={e => setPasswordForm({ ...passwordForm, new_password: e.target.value })} />
        </div>
        <button onClick={changePassword} disabled={!passwordForm.current_password || !passwordForm.new_password} className="btn-primary mt-4">Update Password</button>
      </div>

      {/* API Keys */}
      <div className="card">
        <div className="flex items-center gap-3 mb-4">
          <Key size={20} className="text-green-400" />
          <h2 className="text-lg font-semibold">API Keys</h2>
        </div>
        <div className="flex gap-3 mb-4">
          <input className="input" placeholder="Key name" value={apiKeyName} onChange={e => setApiKeyName(e.target.value)} />
          <button onClick={createApiKey} disabled={!apiKeyName.trim()} className="btn-primary whitespace-nowrap">Generate Key</button>
        </div>
        {newApiKey && (
          <div className="bg-yellow-900/20 border border-yellow-800 rounded-lg p-4">
            <p className="text-sm text-yellow-400 mb-2">Save this key - it won't be shown again:</p>
            <code className="text-sm bg-gray-800 px-3 py-2 rounded block break-all">{newApiKey}</code>
          </div>
        )}
      </div>

      {/* System Info */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4">System</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
          <div>
            <p className="text-lg font-bold">1.0.0</p>
            <p className="text-sm text-gray-400">Version</p>
          </div>
          <div>
            <p className="text-lg font-bold">6</p>
            <p className="text-sm text-gray-400">Models</p>
          </div>
          <div>
            <p className="text-lg font-bold">8</p>
            <p className="text-sm text-gray-400">Agents</p>
          </div>
          <div>
            <p className="text-lg font-bold">12</p>
            <p className="text-sm text-gray-400">DB Tables</p>
          </div>
        </div>
      </div>
    </div>
  )
}
