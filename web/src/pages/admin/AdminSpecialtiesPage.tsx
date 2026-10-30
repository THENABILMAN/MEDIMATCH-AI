import React, { useEffect, useState } from 'react'
import { Activity, Edit2, Plus, Trash2 } from 'lucide-react'
import { api } from '../../api/client'
import { Alert } from '../../components/common/Alert'
import { LoadingSpinner } from '../../components/common/LoadingSpinner'
import type { Specialty } from '../../types'

export const AdminSpecialtiesPage: React.FC = () => {
  const [specialties, setSpecialties] = useState<Specialty[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  // Form states
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    loadSpecialties()
  }, [])

  const loadSpecialties = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await api.admin.listSpecialties()
      setSpecialties(data)
    } catch (err: any) {
      setError(err.message || 'Failed to load specialties')
    } finally {
      setIsLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return

    setIsSubmitting(true)
    setError(null)
    setSuccess(null)

    try {
      if (editingId) {
        const updated = await api.admin.updateSpecialty(editingId, {
          name: name.trim(),
          description: description.trim() || undefined,
        })
        setSpecialties((prev) => prev.map((s) => (s.id === editingId ? updated : s)))
        setSuccess(`Specialty "${name}" updated successfully.`)
        setEditingId(null)
      } else {
        const created = await api.admin.createSpecialty({
          name: name.trim(),
          description: description.trim() || undefined,
        })
        setSpecialties((prev) => [...prev, created])
        setSuccess(`Specialty "${name}" created successfully.`)
      }
      setName('')
      setDescription('')
    } catch (err: any) {
      setError(err.message || 'Failed to save specialty')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleEdit = (s: Specialty) => {
    setEditingId(s.id)
    setName(s.name)
    setDescription(s.description || '')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const handleDelete = async (id: string, sName: string) => {
    if (!confirm(`Are you sure you want to delete specialty "${sName}"?`)) return

    setError(null)
    try {
      await api.admin.deleteSpecialty(id)
      setSpecialties((prev) => prev.filter((s) => s.id !== id))
      setSuccess(`Specialty "${sName}" deleted.`)
    } catch (err: any) {
      setError(err.message || 'Failed to delete specialty')
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-8">
        <h1 className="text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl">
          Medical Specialties Management
        </h1>
        <p className="mt-1 text-sm text-slate-600">
          Define approved clinical specialties used for triage classification and doctor profiles.
        </p>
      </div>

      {error && <Alert type="error" message={error} onClose={() => setError(null)} className="mb-6" />}
      {success && <Alert type="success" message={success} onClose={() => setSuccess(null)} className="mb-6" />}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left: Form */}
        <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-xs h-fit">
          <h2 className="text-sm font-bold text-slate-900 mb-4 pb-3 border-b border-slate-100 flex items-center gap-2">
            <Plus className="h-4 w-4 text-indigo-600" />
            {editingId ? 'Edit Specialty' : 'Add New Specialty'}
          </h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700">Specialty Name</label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Dermatology"
                className="mt-1 w-full rounded-xl border border-slate-200 py-2.5 px-3 text-sm text-slate-900 focus:border-indigo-600 focus:outline-hidden"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700">Description</label>
              <textarea
                rows={3}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Scope of practice, related organs/conditions..."
                className="mt-1 w-full rounded-xl border border-slate-200 p-3 text-xs text-slate-900 focus:border-indigo-600 focus:outline-hidden"
              />
            </div>

            <div className="flex items-center gap-2">
              <button
                type="submit"
                disabled={isSubmitting}
                className="flex-1 rounded-xl bg-indigo-600 py-2.5 text-xs font-bold text-white shadow-xs hover:bg-indigo-700 transition disabled:opacity-50"
              >
                {isSubmitting ? 'Saving...' : editingId ? 'Update Specialty' : 'Create Specialty'}
              </button>
              {editingId && (
                <button
                  type="button"
                  onClick={() => {
                    setEditingId(null)
                    setName('')
                    setDescription('')
                  }}
                  className="rounded-xl border border-slate-200 px-3 py-2.5 text-xs font-semibold text-slate-600 hover:bg-slate-50"
                >
                  Cancel
                </button>
              )}
            </div>
          </form>
        </div>

        {/* Right: List */}
        <div className="lg:col-span-2 rounded-3xl border border-slate-200 bg-white p-6 shadow-xs">
          <h2 className="text-sm font-bold text-slate-900 mb-4 pb-3 border-b border-slate-100 flex items-center gap-2">
            <Activity className="h-4 w-4 text-indigo-600" />
            Specialties in Registry ({specialties.length})
          </h2>

          {isLoading ? (
            <LoadingSpinner message="Loading specialties..." />
          ) : specialties.length === 0 ? (
            <div className="py-12 text-center text-xs text-slate-400">
              No specialties registered in database.
            </div>
          ) : (
            <div className="space-y-3">
              {specialties.map((s) => (
                <div
                  key={s.id}
                  className="flex items-center justify-between rounded-xl border border-slate-200 p-4 hover:border-slate-300 transition"
                >
                  <div className="pr-4">
                    <h3 className="text-sm font-bold text-slate-900">{s.name}</h3>
                    {s.description && (
                      <p className="mt-1 text-xs text-slate-500 leading-relaxed">
                        {s.description}
                      </p>
                    )}
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      onClick={() => handleEdit(s)}
                      className="rounded-lg p-1.5 text-slate-500 hover:bg-indigo-50 hover:text-indigo-600 transition"
                      title="Edit specialty"
                    >
                      <Edit2 className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(s.id, s.name)}
                      className="rounded-lg p-1.5 text-slate-500 hover:bg-red-50 hover:text-red-600 transition"
                      title="Delete specialty"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

