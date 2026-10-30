import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Calendar,
  Clock,
  MapPin,
  MessageSquare,
} from 'lucide-react'
import { api } from '../../api/client'
import { Alert } from '../../components/common/Alert'
import { LoadingSpinner } from '../../components/common/LoadingSpinner'
import type { Appointment } from '../../types'

export const MyAppointmentsPage: React.FC = () => {
  const [appointments, setAppointments] = useState<Appointment[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionSuccess, setActionSuccess] = useState<string | null>(null)

  // Cancel Modal state
  const [cancellingAppId, setCancellingAppId] = useState<string | null>(null)
  const [cancelReason, setCancelReason] = useState('')
  const [isSubmittingCancel, setIsSubmittingCancel] = useState(false)

  const loadAppointments = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await api.appointments.getMy()
      setAppointments(data)
    } catch (err: any) {
      setError(err.message || 'Failed to load your appointments')
    } finally {
      setIsLoading(false)
    }

  }

  useEffect(() => {
    loadAppointments()
  }, [])

  const handleCancelAppointment = async () => {
    if (!cancellingAppId) return

    setIsSubmittingCancel(true)
    setError(null)
    try {
      const updated = await api.appointments.cancel(cancellingAppId, cancelReason)
      setAppointments((prev) =>
        prev.map((a) => (a.id === cancellingAppId ? updated : a))
      )
      setActionSuccess('Appointment was successfully cancelled and the slot has been freed.')
      setCancellingAppId(null)
      setCancelReason('')
    } catch (err: any) {
      setError(err.message || 'Failed to cancel appointment')
    } finally {
      setIsSubmittingCancel(false)
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl">
            My Appointments
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            View scheduled consultations with medical specialists and manage cancellations.
          </p>
        </div>
        <Link
          to="/doctors"
          className="inline-flex items-center gap-1.5 rounded-xl bg-indigo-600 px-4 py-2.5 text-xs font-bold text-white shadow-xs hover:bg-indigo-700 transition"
        >
          <Calendar className="h-4 w-4" />
          Book New Appointment
        </Link>
      </div>

      {error && <Alert type="error" message={error} onClose={() => setError(null)} className="mb-6" />}
      {actionSuccess && (
        <Alert
          type="success"
          message={actionSuccess}
          onClose={() => setActionSuccess(null)}
          className="mb-6"
        />
      )}

      {isLoading ? (
        <LoadingSpinner message="Loading your appointments..." className="py-20" />
      ) : appointments.length === 0 ? (
        <div className="rounded-3xl border border-dashed border-slate-300 p-12 text-center bg-white">
          <Calendar className="mx-auto h-10 w-10 text-slate-300" />
          <h3 className="mt-4 text-base font-bold text-slate-900">No appointments scheduled</h3>
          <p className="mt-1 text-xs text-slate-500">
            You don't have any upcoming or past medical appointments yet.
          </p>
          <div className="mt-6 flex justify-center gap-3">
            <Link
              to="/chat"
              className="inline-flex items-center gap-1.5 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-bold text-white shadow-xs hover:bg-indigo-700 transition"
            >
              <MessageSquare className="h-4 w-4" />
              Chat with AI Assistant
            </Link>
            <Link
              to="/doctors"
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition"
            >
              Browse Specialists
            </Link>
          </div>
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
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-700 font-bold text-base">
                    <Calendar className="h-5 w-5" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-base font-bold text-slate-900">
                        {app.doctor?.full_name || 'Medical Specialist'}
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

                    {app.doctor?.specialties && app.doctor.specialties.length > 0 && (
                      <div className="mt-1 flex flex-wrap gap-1">
                        {app.doctor.specialties.map((s, idx) => (
                          <span
                            key={idx}
                            className="rounded-md bg-indigo-50 px-2 py-0.5 text-[11px] font-semibold text-indigo-700"
                          >
                            {s}
                          </span>
                        ))}
                      </div>
                    )}

                    <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500">
                      {startDt && (
                        <div className="flex items-center gap-1 font-medium text-slate-700">
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
                      {app.doctor?.city && (
                        <div className="flex items-center gap-1">
                          <MapPin className="h-3.5 w-3.5 text-slate-400" />
                          <span>
                            {app.doctor.clinic_name ? `${app.doctor.clinic_name}, ` : ''}
                            {app.doctor.city}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between sm:justify-end gap-3 pt-3 sm:pt-0 border-t sm:border-0 border-slate-100">
                  {app.doctor?.consultation_fee !== undefined && (
                    <div className="text-right sm:mr-4">
                      <div className="text-[10px] uppercase font-bold text-slate-400">Fee</div>
                      <div className="text-xs font-bold text-slate-800">
                        {app.doctor.consultation_fee > 0 ? `৳${app.doctor.consultation_fee}` : 'Free'}
                      </div>
                    </div>
                  )}

                  {app.status === 'booked' && (
                    <button
                      onClick={() => {
                        setCancellingAppId(app.id)
                        setCancelReason('')
                      }}
                      className="rounded-xl border border-red-200 bg-red-50 px-3.5 py-2 text-xs font-bold text-red-700 transition hover:bg-red-100"
                    >
                      Cancel
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Cancellation Modal Dialog */}
      {cancellingAppId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-3xl border border-slate-200 bg-white p-6 shadow-xl">
            <h3 className="text-base font-bold text-slate-900">Cancel Appointment?</h3>
            <p className="mt-1 text-xs text-slate-500 leading-relaxed">
              Cancelling will free this availability slot for other patients to book.
            </p>

            <div className="mt-4">
              <label className="block text-xs font-semibold text-slate-700">
                Cancellation Reason (Optional)
              </label>
              <textarea
                rows={3}
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
                placeholder="e.g. Personal schedule conflict, symptom resolved..."
                className="mt-1 w-full rounded-xl border border-slate-200 p-3 text-xs text-slate-800 focus:border-red-500 focus:outline-hidden"
              />
            </div>

            <div className="mt-6 flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setCancellingAppId(null)}
                disabled={isSubmittingCancel}
                className="rounded-xl border border-slate-200 px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-50"
              >
                Keep Appointment
              </button>
              <button
                type="button"
                onClick={handleCancelAppointment}
                disabled={isSubmittingCancel}
                className="rounded-xl bg-red-600 px-4 py-2 text-xs font-bold text-white shadow-xs hover:bg-red-700 transition disabled:opacity-50"
              >
                {isSubmittingCancel ? 'Cancelling...' : 'Confirm Cancellation'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
