import React from 'react'
import { Link } from 'react-router-dom'
import { Award, Calendar, CheckCircle2, Clock, MapPin, Sparkles } from 'lucide-react'
import type { DoctorRecommendation } from '../../types'

interface DoctorRecommendationCardProps {
  doctor: DoctorRecommendation
}

export const DoctorRecommendationCard: React.FC<DoctorRecommendationCardProps> = ({ doctor }) => {
  const matchPct = Math.min(100, Math.max(50, Math.round(doctor.score * 100)))

  return (
    <div
      data-testid="recommendation-card"
      className="group relative flex flex-col justify-between overflow-hidden rounded-2xl border border-slate-200 bg-white p-5 shadow-xs transition hover:border-indigo-300 hover:shadow-md"
    >
      <div>
        {/* Match Score Badge */}
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-bold text-emerald-700">
            <Sparkles className="h-3.5 w-3.5" />
            <span>{matchPct}% Clinical Match</span>
          </div>
          <span className="text-xs font-semibold text-slate-500">
            {doctor.consultation_fee > 0 ? `৳${doctor.consultation_fee} BDT` : 'Free Consultation'}
          </span>
        </div>

        {/* Doctor Header */}
        <div className="mt-3 flex items-start gap-3">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-linear-to-tr from-indigo-500 to-indigo-700 font-bold text-white shadow-xs text-lg">
            {doctor.full_name.replace(/^Dr\.\s*/i, '').charAt(0) || 'D'}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-1.5">
              <h4 className="truncate text-base font-bold text-slate-900 group-hover:text-indigo-600 transition">
                {doctor.full_name}
              </h4>
              <span title="Verified Specialist">
                <CheckCircle2 className="h-4 w-4 shrink-0 text-sky-500" />
              </span>
            </div>
            <div className="mt-0.5 flex flex-wrap gap-1">
              {doctor.specialties.map((s, idx) => (
                <span
                  key={idx}
                  className="rounded-md bg-indigo-50 px-2 py-0.5 text-[11px] font-semibold text-indigo-700"
                >
                  {s}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Location & Experience */}
        <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-600">
          <div className="flex items-center gap-1">
            <MapPin className="h-3.5 w-3.5 text-slate-400" />
            <span>{doctor.clinic_name ? `${doctor.clinic_name}, ${doctor.city}` : doctor.city}</span>
          </div>
          {doctor.years_experience > 0 && (
            <div className="flex items-center gap-1">
              <Award className="h-3.5 w-3.5 text-slate-400" />
              <span>{doctor.years_experience} yrs exp</span>
            </div>
          )}
        </div>

        {/* Match Explanation */}
        {doctor.match_explanation && (
          <div className="mt-3 rounded-xl bg-slate-50 p-2.5 text-xs italic leading-relaxed text-slate-700">
            "{doctor.match_explanation}"
          </div>
        )}
      </div>

      {/* CTA Button */}
      <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between gap-3">
        {doctor.next_available_slot && (
          <div className="flex items-center gap-1 text-[11px] font-medium text-emerald-700">
            <Clock className="h-3.5 w-3.5" />
            <span>Slots Available</span>
          </div>
        )}
        <Link
          to={`/doctors/${doctor.doctor_id}`}
          className="ml-auto inline-flex items-center gap-1.5 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-bold text-white shadow-xs transition hover:bg-indigo-700 active:scale-95"
        >
          <Calendar className="h-3.5 w-3.5" />
          View & Book Slot
        </Link>
      </div>
    </div>
  )
}
