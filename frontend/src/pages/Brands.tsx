import { useState, useEffect } from 'react'
import { api, Brand } from '../api/client'
import LoadingSpinner from '../components/LoadingSpinner'
import { Palette, Plus } from 'lucide-react'

export default function Brands() {
  const [brands, setBrands] = useState<Brand[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({ name: '', description: '', voice_tone: 'professional', target_audience: '', keywords: '' })
  const [selectedBrand, setSelectedBrand] = useState<Brand | null>(null)
  const [consistency, setConsistency] = useState<Record<string, unknown> | null>(null)

  useEffect(() => {
    api.get<{ brands: Brand[] }>('/brands/project/default')
      .then(data => setBrands(data.brands || []))
      .catch(() => setBrands([]))
      .finally(() => setLoading(false))
  }, [])

  const handleCreate = async () => {
    if (!form.name.trim()) return
    try {
      const brand = await api.post<Brand>('/brands', {
        project_id: 'default',
        name: form.name,
        description: form.description,
        voice_tone: form.voice_tone,
        target_audience: form.target_audience,
        keywords: form.keywords.split(',').map(k => k.trim()).filter(Boolean),
      })
      setBrands(prev => [...prev, brand])
      setShowCreate(false)
      setForm({ name: '', description: '', voice_tone: 'professional', target_audience: '', keywords: '' })
    } catch { /* ignore */ }
  }

  const analyzeBrand = async (brandId: string) => {
    try {
      const result = await api.post<Record<string, unknown>>(`/brands/${brandId}/analyze`, { content: 'Sample content for analysis' })
      setConsistency(result)
    } catch { /* ignore */ }
  }

  if (loading) return <LoadingSpinner text="Loading brands..." />

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Brand Center</h1>
          <p className="text-gray-400 mt-1">Manage brand identities and voice consistency</p>
        </div>
        <button onClick={() => setShowCreate(!showCreate)} className="btn-primary flex items-center gap-2">
          <Plus size={18} /> New Brand
        </button>
      </div>

      {showCreate && (
        <div className="card space-y-4">
          <h2 className="text-lg font-semibold">Create Brand</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <input placeholder="Brand name" className="input" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
            <select className="input" value={form.voice_tone} onChange={e => setForm({ ...form, voice_tone: e.target.value })}>
              <option value="professional">Professional</option>
              <option value="casual">Casual</option>
              <option value="friendly">Friendly</option>
              <option value="authoritative">Authoritative</option>
              <option value="playful">Playful</option>
            </select>
            <input placeholder="Description" className="input" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} />
            <input placeholder="Target audience" className="input" value={form.target_audience} onChange={e => setForm({ ...form, target_audience: e.target.value })} />
            <input placeholder="Keywords (comma-separated)" className="input md:col-span-2" value={form.keywords} onChange={e => setForm({ ...form, keywords: e.target.value })} />
          </div>
          <div className="flex gap-3">
            <button onClick={handleCreate} disabled={!form.name.trim()} className="btn-primary">Create Brand</button>
            <button onClick={() => setShowCreate(false)} className="btn-secondary">Cancel</button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {brands.map(brand => (
          <div key={brand.id} className="card">
            <div className="flex items-center gap-3 mb-3">
              <Palette size={20} className="text-purple-400" />
              <h3 className="font-medium">{brand.name}</h3>
            </div>
            <p className="text-sm text-gray-400 mb-2">{brand.description || 'No description'}</p>
            <div className="flex flex-wrap gap-2 mb-3">
              <span className="badge-blue">{brand.voice_tone}</span>
              {brand.keywords?.slice(0, 3).map(k => <span key={k} className="badge bg-gray-800 text-gray-400">{k}</span>)}
            </div>
            <button onClick={() => { setSelectedBrand(brand); analyzeBrand(brand.id) }} className="btn-secondary text-sm">
              Analyze Consistency
            </button>
          </div>
        ))}
        {brands.length === 0 && (
          <div className="card text-center py-12 text-gray-500 md:col-span-2">
            <Palette size={48} className="mx-auto mb-3 opacity-50" />
            <p>No brands yet. Create your first brand identity.</p>
          </div>
        )}
      </div>

      {consistency && selectedBrand && (
        <div className="card">
          <h2 className="text-lg font-semibold mb-3">Brand Consistency Analysis - {selectedBrand.name}</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(consistency).map(([key, value]) => (
              <div key={key} className="text-center">
                <p className="text-2xl font-bold">{typeof value === 'number' ? `${value}%` : String(value)}</p>
                <p className="text-sm text-gray-400 capitalize">{key.replace(/_/g, ' ')}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
