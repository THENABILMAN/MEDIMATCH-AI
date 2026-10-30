import React, { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  Award,
  Calendar,
  CheckCircle2,
  Clock,
  DollarSign,
  GraduationCap,
  MapPin,
  ShieldCheck,
} from 'lucide-react'
import { api } from '../../api/client'
import { Alert } from '../../components/common/Alert'
import { LoadingSpinner } from '../../components/common/LoadingSpinner'
import { useAuth } from '../../contexts/AuthContext'
import type { AvailabilitySlot, DoctorProfile } from '../../types'

export const DoctorDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const { user } = useAuth()
  const navigate = useNavigate()

  const [doctor, setDoctor] = useState<DoctorProfile | null>(null)
  const [slots, setSlots] = useState<AvailabilitySlot[]>([])
  const [selectedSlotId, setSelectedSlotId] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isBooking, setIsBooking] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [bookingSuccess, setBookingSuccess] = useState<string | null>(null)

  useEffect(() => {
    if (id) {
      loadDoctorAndSlots(id)
    }
  }, [id])

  const loadDoctorAndSlots = async (docId: string) => {
    setIsLoading(true)
    setError(null)
    try {
      const [docData, slotsData] = await Promise.all([
        api.doctors.getById(docId),
        api.doctors.getPublicSlots(docId),
      ])
      setDoctor(docData)
      setSlots(slotsData)
    } catch (err: any) {
      setError(err.message || 'Failed to load doctor profile')
    } finally {
      setIsLoading(false)
    }
  }

  const handleBookSlot = async () => {
    if (!user) {
      navigate('/login', { state: { from: { pathname: `/doctors/${id}` } } })
      return
    }

    if (!selectedSlotId) return

    setIsBooking(true)
    setError(null)
    setBookingSuccess(null)

    try {
      const appointment = await api.appointments.book(selectedSlotId)
      setBookingSuccess(
        `Appointment successfully booked for ${new Date(
          appointment.start_time || ''
        ).toLocaleString()}! You can view it under My Appointments.`
      )
      // Remove booked slot from available list
      setSlots((prev) => prev.filter((s) => s.id !== selectedSlotId))
      setSelectedSlotId(null)
    } catch (err: any) {
      setError(err.message || 'Booking failed. This slot may have just been taken.')
    } finally {
      setIsBooking(false)
    }
  }

  if (isLoading) {
    return <LoadingSpinner message="Loading specialist profile & schedule..." className="py-20" />
  }

  if (!doctor) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16 text-center">
        <h2 className="text-xl font-bold text-slate-900">Doctor Profile Not Found</h2>
        <p className="mt-2 text-sm text-slate-500">
          This doctor profile may be pending verification or has been removed.
        </p>
        <Link
          to="/doctors"
          className="mt-6 inline-block rounded-xl bg-indigo-600 px-5 py-2.5 text-xs font-bold text-white shadow-xs hover:bg-indigo-700"
        >
          Back to Doctor Search
        </Link>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6 lg:px-8">
      {error && <Alert type="error" message={error} onClose={() => setError(null)} className="mb-6" />}
      {bookingSuccess && (
        <Alert
          type="success"
          title="Booking Confirmed!"
          message={bookingSuccess}
          className="mb-6"
        />
      )}

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
        {/* Left 2 Cols: Doctor Info */}
        <div className="space-y-6 lg:col-span-2">
          {/* Main Profile Card */}
          <div className="rounded-3xl border border-slate-200 bg-white p-6 sm:p-8 shadow-xs">
            <div className="flex items-start gap-4">
              <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-indigo-600 text-2xl font-bold text-white shadow-md">
                {doctor.full_name.replace(/^Dr\.\s*/i, '').charAt(0) || 'D'}
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h1 className="text-xl font-extrabold text-slate-900 sm:text-2xl">
                    {doctor.full_name}
                  </h1>
                  <span className="flex items-center gap-1 rounded-full bg-sky-50 px-2 py-0.5 text-xs font-bold text-sky-700">
                    <CheckCircle2 className="h-3.5 w-3.5 text-sky-500" />
                    Verified
                  </span>
                </div>

                <div className="mt-2 flex flex-wrap gap-1.5">
                  {doctor.specialties.map((s) => (
                    <span
                      key={s.id}
                      className="rounded-lg bg-indigo-50 px-2.5 py-1 text-xs font-semibold text-indigo-700"
                    >
                      {s.name}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            <div className="mt-6 grid grid-cols-2 gap-4 border-y border-slate-100 py-4 sm:grid-cols-3">
              <div>
                <span className="text-[11px] font-semibold text-slate-400">Experience</span>
                <p className="mt-0.5 text-sm font-bold text-slate-800">
                  {doctor.years_experience} Years
                </p>
              </div>
              <div>
                <span className="text-[11px] font-semibold text-slate-400">City Location</span>
                <p className="mt-0.5 text-sm font-bold text-slate-800">{doctor.city}</p>
              </div>
              <div>
                <span className="text-[11px] font-semibold text-slate-400">Consultation Fee</span>
                <p className="mt-0.5 text-sm font-bold text-indigo-600">
                  {doctor.consultation_fee > 0 ? `৳${doctor.consultation_fee} BDT` : 'Free'}
                </p>
              </div>
            </div>

            {doctor.clinic_name && (
              <div className="mt-4 flex items-center gap-2 text-xs text-slate-600">
                <MapPin className="h-4 w-4 text-slate-400 shrink-0" />
                <span>Primary Clinic: <strong>{doctor.clinic_name}</strong></span>
              </div>
            )}

            {doctor.qualifications && doctor.qualifications.length > 0 && (
              <div className="mt-4 flex items-center gap-2 text-xs text-slate-600">
                <GraduationCap className="h-4 w-4 text-slate-400 shrink-0" />
                <span>Degrees & Credentials: <strong>{doctor.qualifications.join(', ')}</strong></span>
              </div>
            )}

            {doctor.bio && (
              <div className="mt-6 pt-6 border-t border-slate-100">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  Clinical Bio & Background
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-700 whitespace-pre-line">
                  {doctor.bio}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Right Col: Slot Booking */}
        <div className="space-y-6">
          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-xs">
            <div className="flex items-center gap-2 text-sm font-bold text-slate-900 border-b border-slate-100 pb-3">
              <Calendar className="h-4 w-4 text-indigo-600" />
              Available Appointment Slots
            </div>

            {slots.length === 0 ? (
              <div className="py-8 text-center text-xs text-slate-500">
                <Clock className="mx-auto h-6 w-6 text-slate-300 mb-2" />
                No future open slots currently scheduled for this doctor.
              </div>
            ) : (
              <div className="mt-4 max-h-72 overflow-y-auto space-y-2 pr-1">
                {slots.map((slot) => {
                  const startDt = new Date(slot.start_time)
                  const endDt = new Date(slot.end_time)
                  const isSelected = selectedSlotId === slot.id

                  return (
                    <button
                      key={slot.id}
                      onClick={() => setSelectedSlotId(slot.id)}
                      className={`w-full flex items-center justify-between rounded-xl border p-3 text-left transition ${
                        isSelected
                          ? 'border-indigo-600 bg-indigo-50 text-indigo-900 shadow-xs'
                          : 'border-slate-200 hover:border-indigo-200 hover:bg-slate-50 text-slate-700'
                      }`}
                    >
                      <div>
                        <div className="text-xs font-bold">
                          {startDt.toLocaleDateString(undefined, {
                            weekday: 'short',
                            month: 'short',
                            day: 'numeric',
                          })}
                        </div>
                        <div className="text-[11px] text-slate-500 mt-0.5">
                          {startDt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} –{' '}
                          {endDt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </div>
                      </div>
                      <div
                        className={`h-4 w-4 rounded-full border flex items-center justify-center ${
                          isSelected ? 'border-indigo-600 bg-indigo-600' : 'border-slate-300'
                        }`}
                      >
                        {isSelected && <div className="h-1.5 w-1.5 rounded-full bg-white" />}
                      </div>
                    </button>
                  )
                })}
              </div>
            )}

            <div className="mt-6 pt-4 border-t border-slate-100">
              <button
                onClick={handleBookSlot}
                disabled={!selectedSlotId || isBooking}
                className="w-full flex items-center justify-center gap-2 rounded-xl bg-indigo-600 py-3 text-xs font-bold text-white shadow-xs transition hover:bg-indigo-700 disabled:opacity-40 active:scale-95"
              >
                {isBooking ? (
                  'Confirming Booking...'
                ) : user ? (
                  'Confirm Appointment Booking'
                ) : (
                  'Sign In to Book This Slot'
                )}
              </button>
              <p className="mt-2 text-center text-[10px] text-slate-400">
                Guaranteed zero double-booking via database-level concurrency lock.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

