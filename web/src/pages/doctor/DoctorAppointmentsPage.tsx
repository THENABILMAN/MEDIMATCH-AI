import React, { useEffect, useState } from 'react'
import {
  Calendar,
  CheckCircle2,
  Clock,
  Mail,
  Phone,
  User,
  XCircle,
} from 'lucide-react'
import { api } from '../../api/client'
import { Alert } from '../../components/common/Alert'
import { LoadingSpinner } from '../../components/common/LoadingSpinner'
import type { Appointment } from '../../types'

export const DoctorAppointmentsPage: React.FC = () => {
  const [appointments, setAppointments] = useState<Appointment[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    loadAppointments()
  }, [])

  const loadAppointments = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await api.appointments.getMy()
      setAppointments(data)
    } catch (err: any) {
      setError(err.message || 'Failed to load scheduled appointments')
    } finally {
      setIsLoading(false)
    }
  }

  const handleComplete = async (id: string) => {
    setError(null)
    try {
      const updated = await api.appointments.complete(id)
      setAppointments((prev) => prev.map((a) => (a.id === id ? updated : a)))
      setSuccess('Appointment marked as completed.')
    } catch (err: any) {
      setError(err.message || 'Failed to complete appointment')
    }
  }

  const handleCancel = async (id: string) => {
    const reason = prompt('Please enter a cancellation reason:')
    if (reason === null) return

    setError(null)
    try {
      const updated = await api.appointments.cancel(id, reason || undefined)
      setAppointments((prev) => prev.map((a) => (a.id === id ? updated : a)))
      setSuccess('Appointment cancelled and slot freed.')
    } catch (err: any) {
      setError(err.message || 'Failed to cancel appointment')
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl">
            Patient Appointments
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Review consultations scheduled with your profile and mark completion.
          </p>
        </div>
      </div>

      {error && <Alert type="error" message={error} onClose={() => setError(null)} className="mb-6" />}
      {success && <Alert type="success" message={success} onClose={() => setSuccess(null)} className="mb-6" />}

      {isLoading ? (
        <LoadingSpinner message="Loading appointments..." className="py-20" />
      ) : appointments.length === 0 ? (
        <div className="rounded-3xl border border-dashed border-slate-300 p-12 text-center bg-white">
          <Calendar className="mx-auto h-10 w-10 text-slate-300" />
          <h3 className="mt-4 text-base font-bold text-slate-900">No scheduled appointments</h3>
          <p className="mt-1 text-xs text-slate-500">
            Patients who book your open availability slots will appear here.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {appointments.map((app) => {
            const startDt = app.start_time ? new Date(app.start_time) : null

            return (
              <div
                key={app.id}
                className="flex flex-col sm:flex-row sm:items-center sm:justify-between rounded-2xl border border-slate-200 bg-white p-5 shadow-xs gap-4"
              >
                <div className="flex items-start gap-4">
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-700 font-bold">
                    <User className="h-5 w-5" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-base font-bold text-slate-900">
                        {app.patient?.full_name || 'Patient'}
                      </h3>
                      <span
                        className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                          app.status === 'booked'
                            ? 'bg-emerald-100 text-emerald-800'
                            : app.status === 'completed'
                            ? 'bg-sky-100 text-sky-800'
                            : 'bg-slate-100 text-slate-600'
                        }`}
                      >
                        {app.status}
                      </span>
                    </div>

                    <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-600">
                      {startDt && (
                        <div className="flex items-center gap-1 font-medium text-slate-800">
                          <Clock className="h-3.5 w-3.5 text-slate-400" />
                          <span>
                            {startDt.toLocaleDateString(undefined, {
                              weekday: 'short',
                              month: 'short',
                              day: 'numeric',
                            })}{' '}
                            at {startDt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>
                      )}
                      {app.patient?.phone && (
                        <div className="flex items-center gap-1">
                          <Phone className="h-3.5 w-3.5 text-slate-400" />
                          <span>{app.patient.phone}</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between sm:justify-end gap-2 pt-3 sm:pt-0 border-t sm:border-0 border-slate-100">
                  {app.status === 'booked' && (
                    <>
                      <button
                        onClick={() => handleComplete(app.id)}
                        className="inline-flex items-center gap-1 rounded-xl bg-emerald-600 px-3.5 py-2 text-xs font-bold text-white shadow-xs hover:bg-emerald-700 transition"
                      >
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        Complete
                      </button>
                      <button
                        onClick={() => handleCancel(app.id)}
                        className="rounded-xl border border-red-200 bg-red-50 px-3.5 py-2 text-xs font-bold text-red-700 hover:bg-red-100 transition"
                      >
                        Cancel
                      </button>
                    </>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

