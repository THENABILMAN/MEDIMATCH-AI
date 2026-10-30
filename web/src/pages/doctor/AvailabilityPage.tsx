import React, { useEffect, useState } from 'react'
import {
  Calendar,
  Plus,
  Trash2,
} from 'lucide-react'
import { api } from '../../api/client'
import { Alert } from '../../components/common/Alert'
import { LoadingSpinner } from '../../components/common/LoadingSpinner'
import type { AvailabilitySlot } from '../../types'

export const AvailabilityPage: React.FC = () => {
  const [slots, setSlots] = useState<AvailabilitySlot[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isCreating, setIsCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  // Form
  const [startDate, setStartDate] = useState('')
  const [startTime, setStartTime] = useState('')
  const [endTime, setEndTime] = useState('')

  const loadSlots = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await api.doctors.getMySlots(true)
      setSlots(data)
    } catch (err: any) {
      setError(err.message || 'Failed to load availability slots')
    } finally {
      setIsLoading(false)
    }

  }

  useEffect(() => {
    loadSlots()
  }, [])

  const handleCreateSlot = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!startDate || !startTime || !endTime) return

    setIsCreating(true)
    setError(null)
    setSuccess(null)

    try {
      const startDateTime = new Date(`${startDate}T${startTime}:00Z`).toISOString()
      const endDateTime = new Date(`${startDate}T${endTime}:00Z`).toISOString()

      const newSlot = await api.doctors.createSlot(startDateTime, endDateTime)
      setSlots((prev) => [newSlot, ...prev])
      setSuccess('Availability slot created successfully!')
      setStartTime('')
      setEndTime('')
    } catch (err: any) {
      setError(err.message || 'Failed to create slot')
    } finally {
      setIsCreating(false)
    }
  }

  const handleDeleteSlot = async (slotId: string) => {
    if (!confirm('Are you sure you want to delete this availability slot?')) return

    setError(null)
    try {
      await api.doctors.deleteSlot(slotId)
      setSlots((prev) => prev.filter((s) => s.id !== slotId))
      setSuccess('Slot removed successfully.')
    } catch (err: any) {
      setError(err.message || 'Failed to delete slot')
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-8">
        <h1 className="text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl">
          Manage Availability Slots
        </h1>
        <p className="mt-1 text-sm text-slate-600">
          Define upcoming consultation windows for patients to discover and book.
        </p>
      </div>

      {error && <Alert type="error" message={error} onClose={() => setError(null)} className="mb-6" />}
      {success && <Alert type="success" message={success} onClose={() => setSuccess(null)} className="mb-6" />}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left: Create Slot Form */}
        <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-xs h-fit">
          <div className="flex items-center gap-2 pb-3 mb-4 border-b border-slate-100 text-sm font-bold text-slate-900">
            <Plus className="h-4 w-4 text-indigo-600" />
            Add New Availability Slot
          </div>

          <form onSubmit={handleCreateSlot} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700">Date</label>
              <input
                type="date"
                required
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                min={new Date().toISOString().split('T')[0]}
                className="mt-1 w-full rounded-xl border border-slate-200 py-2 px-3 text-xs text-slate-900 focus:border-indigo-600 focus:outline-hidden"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700">Start Time (UTC)</label>
                <input
                  type="time"
                  required
                  value={startTime}
                  onChange={(e) => setStartTime(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-slate-200 py-2 px-3 text-xs text-slate-900 focus:border-indigo-600 focus:outline-hidden"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700">End Time (UTC)</label>
                <input
                  type="time"
                  required
                  value={endTime}
                  onChange={(e) => setEndTime(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-slate-200 py-2 px-3 text-xs text-slate-900 focus:border-indigo-600 focus:outline-hidden"
                />
              </div>
            </div>

            <p className="text-[10px] text-slate-400">
              * Minimum duration is 15 minutes. Overlapping slots will be automatically rejected.
            </p>

            <button
              type="submit"
              disabled={isCreating}
              className="w-full flex items-center justify-center gap-2 rounded-xl bg-indigo-600 py-2.5 text-xs font-bold text-white shadow-xs hover:bg-indigo-700 transition disabled:opacity-50"
            >
              {isCreating ? 'Creating Slot...' : 'Create Availability Slot'}
            </button>
          </form>
        </div>

        {/* Right: Slot Listing */}
        <div className="lg:col-span-2 rounded-3xl border border-slate-200 bg-white p-6 shadow-xs">
          <div className="flex items-center justify-between pb-3 mb-4 border-b border-slate-100">
            <div className="flex items-center gap-2 text-sm font-bold text-slate-900">
              <Calendar className="h-4 w-4 text-indigo-600" />
              Existing Slots ({slots.length})
            </div>
            <button
              onClick={loadSlots}
              className="text-xs font-semibold text-indigo-600 hover:underline"
            >
              Refresh
            </button>
          </div>

          {isLoading ? (
            <LoadingSpinner message="Loading slots..." />
          ) : slots.length === 0 ? (
            <div className="py-12 text-center text-xs text-slate-400">
              No slots scheduled. Use the form to add upcoming availability.
            </div>
          ) : (
            <div className="space-y-2.5 max-h-[500px] overflow-y-auto pr-1">
              {slots.map((slot) => {
                const sDt = new Date(slot.start_time)
                const eDt = new Date(slot.end_time)

                return (
                  <div
                    key={slot.id}
                    className="flex items-center justify-between rounded-xl border border-slate-200 p-3.5 hover:border-slate-300 transition"
                  >
                    <div>
                      <div className="text-xs font-bold text-slate-900">
                        {sDt.toLocaleDateString(undefined, {
                          weekday: 'short',
                          year: 'numeric',
                          month: 'short',
                          day: 'numeric',
                        })}
                      </div>
                      <div className="text-[11px] text-slate-500 mt-0.5">
                        {sDt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} –{' '}
                        {eDt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      <span
                        className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                          slot.is_booked
                            ? 'bg-amber-100 text-amber-800'
                            : 'bg-emerald-100 text-emerald-800'
                        }`}
                      >
                        {slot.is_booked ? 'Booked' : 'Open'}
                      </span>

                      {!slot.is_booked && (
                        <button
                          onClick={() => handleDeleteSlot(slot.id)}
                          className="rounded-lg p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600 transition"
                          title="Delete unbooked slot"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
