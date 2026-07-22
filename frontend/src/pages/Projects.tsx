import { useState, useEffect, useCallback } from 'react'
import { api, Project } from '../api/client'
import { useToast } from '../hooks/useToast'
import DataTable, { Column } from '../components/DataTable'
import Pagination from '../components/Pagination'
import SearchBar from '../components/SearchBar'
import { Spinner } from '../components/LoadingStates'
import {
  Folder, Plus, X, Pencil, Trash2, Archive, RotateCcw,
} from 'lucide-react'

interface ProjectFormData {
  name: string
  description: string
  status: 'active' | 'archived' | 'draft'
}

const emptyForm: ProjectFormData = { name: '', description: '', status: 'active' }

export default function Projects() {
  const { toast } = useToast()
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [total, setTotal] = useState(0)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingProject, setEditingProject] = useState<Project | null>(null)
  const [form, setForm] = useState<ProjectFormData>(emptyForm)
  const [saving, setSaving] = useState(false)

  const loadProjects = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ page: String(page), limit: '10' })
      if (search) params.set('search', search)
      if (statusFilter) params.set('status', statusFilter)
      const res = await api.get<{ items: Project[]; total: number; pages: number }>(
        `/projects?${params.toString()}`
      )
      setProjects(res.items || [])
      setTotal(res.total || 0)
      setTotalPages(res.pages || 1)
    } catch {
      toast.error('Failed to load projects')
    } finally {
      setLoading(false)
    }
  }, [page, search, statusFilter, toast])

  useEffect(() => { loadProjects() }, [loadProjects])

  useEffect(() => { setPage(1) }, [search, statusFilter])

  const openCreate = () => {
    setEditingProject(null)
    setForm(emptyForm)
    setModalOpen(true)
  }

  const openEdit = (p: Project) => {
    setEditingProject(p)
    setForm({ name: p.name, description: p.description, status: p.status })
    setModalOpen(true)
  }

  const handleSave = async () => {
    if (!form.name.trim()) {
      toast.warning('Project name is required')
      return
    }
    setSaving(true)
    try {
      if (editingProject) {
        await api.put(`/projects/${editingProject.id}`, form)
        toast.success('Project updated')
      } else {
        await api.post('/projects', form)
        toast.success('Project created')
      }
      setModalOpen(false)
      loadProjects()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to save project')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (p: Project) => {
    if (!window.confirm(`Delete project "${p.name}"?`)) return
    try {
      await api.delete(`/projects/${p.id}`)
      toast.success('Project deleted')
      loadProjects()
    } catch {
      toast.error('Failed to delete project')
    }
  }

  const handleArchive = async (p: Project) => {
    try {
      const newStatus = p.status === 'archived' ? 'active' : 'archived'
      await api.put(`/projects/${p.id}`, { status: newStatus })
      toast.success(`Project ${newStatus === 'archived' ? 'archived' : 'restored'}`)
      loadProjects()
    } catch {
      toast.error('Failed to update project')
    }
  }

  const statusBadge = (status: string) => {
    const map: Record<string, string> = {
      active: 'badge-green',
      archived: 'badge-yellow',
      draft: 'badge-blue',
    }
    return <span className={`badge ${map[status] || 'badge-blue'}`}>{status}</span>
  }

  const columns: Column<Project>[] = [
    {
      key: 'name',
      header: 'Name',
      sortable: true,
      render: p => (
        <div className="flex items-center gap-2">
          <Folder size={16} className="text-brand-400" />
          <span className="font-medium text-gray-100">{p.name}</span>
        </div>
      ),
    },
    {
      key: 'description',
      header: 'Description',
      render: p => <span className="text-gray-400 line-clamp-1">{p.description || '—'}</span>,
    },
    { key: 'status', header: 'Status', sortable: true, render: p => statusBadge(p.status) },
    {
      key: 'content_count',
      header: 'Content',
      sortable: true,
      className: 'text-gray-400',
    },
    {
      key: 'actions',
      header: '',
      className: 'text-right',
      render: p => (
        <div className="flex items-center justify-end gap-1">
          <button onClick={e => { e.stopPropagation(); openEdit(p) }} className="p-1.5 rounded hover:bg-gray-700 text-gray-400 hover:text-gray-200 transition-colors" title="Edit">
            <Pencil size={15} />
          </button>
          <button onClick={e => { e.stopPropagation(); handleArchive(p) }} className="p-1.5 rounded hover:bg-gray-700 text-gray-400 hover:text-gray-200 transition-colors" title={p.status === 'archived' ? 'Restore' : 'Archive'}>
            {p.status === 'archived' ? <RotateCcw size={15} /> : <Archive size={15} />}
          </button>
          <button onClick={e => { e.stopPropagation(); handleDelete(p) }} className="p-1.5 rounded hover:bg-gray-700 text-red-400 hover:text-red-300 transition-colors" title="Delete">
            <Trash2 size={15} />
          </button>
        </div>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Projects</h1>
          <p className="text-gray-400 mt-1">Manage your content projects</p>
        </div>
        <button onClick={openCreate} className="btn-primary flex items-center gap-2">
          <Plus size={18} /> New Project
        </button>
      </div>

      <SearchBar
        value={search}
        onChange={setSearch}
        placeholder="Search projects..."
        filters={[{
          key: 'status',
          label: 'All Statuses',
          options: [
            { label: 'Active', value: 'active' },
            { label: 'Draft', value: 'draft' },
            { label: 'Archived', value: 'archived' },
          ],
          value: statusFilter,
          onChange: setStatusFilter,
        }]}
      />

      {loading ? (
        <Spinner />
      ) : (
        <>
          <DataTable
            columns={columns}
            data={projects}
            onRowClick={openEdit}
            keyExtractor={p => p.id}
            emptyMessage="No projects found"
          />
          <Pagination page={page} totalPages={totalPages} total={total} onPageChange={setPage} />
        </>
      )}

      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="card w-full max-w-lg mx-4 space-y-5">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold">{editingProject ? 'Edit Project' : 'New Project'}</h2>
              <button onClick={() => setModalOpen(false)} className="p-1.5 rounded hover:bg-gray-700 text-gray-400">
                <X size={18} />
              </button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-1">Name</label>
                <input
                  className="input"
                  value={form.name}
                  onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                  placeholder="Project name"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-1">Description</label>
                <textarea
                  className="input resize-none"
                  rows={3}
                  value={form.description}
                  onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                  placeholder="Brief description"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-1">Status</label>
                <select
                  className="input"
                  value={form.status}
                  onChange={e => setForm(f => ({ ...f, status: e.target.value as ProjectFormData['status'] }))}
                >
                  <option value="active">Active</option>
                  <option value="draft">Draft</option>
                  <option value="archived">Archived</option>
                </select>
              </div>
            </div>
            <div className="flex justify-end gap-3">
              <button onClick={() => setModalOpen(false)} className="btn-secondary">Cancel</button>
              <button onClick={handleSave} disabled={saving} className="btn-primary">
                {saving ? 'Saving...' : editingProject ? 'Update' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
