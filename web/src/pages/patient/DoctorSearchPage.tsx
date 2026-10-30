import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Award, Calendar, CheckCircle2, Filter, MapPin, Search } from 'lucide-react'
import { api } from '../../api/client'
import { Alert } from '../../components/common/Alert'
import { LoadingSpinner } from '../../components/common/LoadingSpinner'
import type { DoctorProfile, Specialty } from '../../types'

export const DoctorSearchPage: React.FC = () => {
  const [doctors, setDoctors] = useState<DoctorProfile[]>([])
  const [specialties, setSpecialties] = useState<Specialty[]>([])
  const [total, setTotal] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Filters
  const [selectedSpecialty, setSelectedSpecialty] = useState('')
  const [selectedCity, setSelectedCity] = useState('')
  const [maxFee, setMaxFee] = useState<number | undefined>(undefined)
  const [minExp, setMinExp] = useState<number | undefined>(undefined)
  const [sortBy, setSortBy] = useState('fee_asc')
  const [page, setPage] = useState(1)

  useEffect(() => {
    // Load specialties for filter dropdown
    api.admin.listSpecialties().then(setSpecialties).catch(() => {})
  }, [])

  useEffect(() => {
    fetchDoctors()
  }, [selectedSpecialty, selectedCity, maxFee, minExp, sortBy, page])

  const fetchDoctors = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await api.doctors.search({
        specialty: selectedSpecialty || undefined,
        city: selectedCity || undefined,
        max_fee: maxFee || undefined,
        min_experience: minExp || undefined,
        sort_by: sortBy || undefined,
        page,
        page_size: 12,
      })
      setDoctors(data.items)
      setTotal(data.total)
    } catch (err: any) {
      setError(err.message || 'Failed to search doctors')
    } finally {
      setIsLoading(false)
    }
  }

  const handleResetFilters = () => {
    setSelectedSpecialty('')
    setSelectedCity('')
    setMaxFee(undefined)
    setMinExp(undefined)
    setSortBy('fee_asc')
    setPage(1)
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl">
          Find Verified Medical Specialists
        </h1>
        <p className="mt-1 text-sm text-slate-600">
          Browse verified doctors across Bangladesh. Only approved, verified profiles are shown.
        </p>
      </div>

      {error && <Alert type="error" message={error} onClose={() => setError(null)} className="mb-6" />}

      {/* Filter Bar */}
      <div className="mb-8 rounded-2xl border border-slate-200 bg-white p-5 shadow-xs">
        <div className="flex items-center gap-2 pb-4 text-xs font-bold uppercase tracking-wider text-slate-500 border-b border-slate-100">
          <Filter className="h-4 w-4" />
          Filter & Sort Options
        </div>

        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {/* Specialty */}
          <div>
            <label className="block text-xs font-semibold text-slate-700">Specialty</label>
            <select
              value={selectedSpecialty}
              onChange={(e) => setSelectedSpecialty(e.target.value)}
              className="mt-1 w-full rounded-xl border border-slate-200 bg-white py-2 px-3 text-xs text-slate-800 focus:border-indigo-600 focus:outline-hidden"
            >
              <option value="">All Specialties</option>
              {specialties.map((s) => (
                <option key={s.id} value={s.name}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>

          {/* City */}
          <div>
            <label className="block text-xs font-semibold text-slate-700">City</label>
            <select
              value={selectedCity}
              onChange={(e) => setSelectedCity(e.target.value)}
              className="mt-1 w-full rounded-xl border border-slate-200 bg-white py-2 px-3 text-xs text-slate-800 focus:border-indigo-600 focus:outline-hidden"
            >
              <option value="">All Cities</option>
              <option value="Dhaka">Dhaka</option>
              <option value="Chittagong">Chittagong</option>
              <option value="Sylhet">Sylhet</option>
            </select>
          </div>

          {/* Max Fee */}
          <div>
            <label className="block text-xs font-semibold text-slate-700">Max Fee (BDT)</label>
            <input
              type="number"
              min="0"
              step="100"
              placeholder="e.g. 2000"
              value={maxFee || ''}
              onChange={(e) => setMaxFee(e.target.value ? Number(e.target.value) : undefined)}
              className="mt-1 w-full rounded-xl border border-slate-200 py-2 px-3 text-xs text-slate-800 focus:border-indigo-600 focus:outline-hidden"
            />
          </div>

          {/* Min Experience */}
          <div>
            <label className="block text-xs font-semibold text-slate-700">Min Experience</label>
            <select
              value={minExp || ''}
              onChange={(e) => setMinExp(e.target.value ? Number(e.target.value) : undefined)}
              className="mt-1 w-full rounded-xl border border-slate-200 bg-white py-2 px-3 text-xs text-slate-800 focus:border-indigo-600 focus:outline-hidden"
            >
              <option value="">Any Experience</option>
              <option value="3">3+ Years</option>
              <option value="5">5+ Years</option>
              <option value="10">10+ Years</option>
            </select>
          </div>

          {/* Sort By */}
          <div>
            <label className="block text-xs font-semibold text-slate-700">Sort By</label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="mt-1 w-full rounded-xl border border-slate-200 bg-white py-2 px-3 text-xs text-slate-800 focus:border-indigo-600 focus:outline-hidden"
            >
              <option value="fee_asc">Fee: Low to High</option>
              <option value="fee_desc">Fee: High to Low</option>
              <option value="experience_desc">Most Experienced</option>
            </select>
          </div>
        </div>

        <div className="mt-4 flex items-center justify-between pt-2">
          <span className="text-xs text-slate-500 font-medium">
            Found <span className="font-bold text-slate-900">{total}</span> verified specialist(s)
          </span>
          <button
            onClick={handleResetFilters}
            className="text-xs font-semibold text-indigo-600 hover:underline"
          >
            Reset Filters
          </button>
        </div>
      </div>

      {/* Doctors Grid */}
      {isLoading ? (
        <LoadingSpinner message="Searching verified specialists..." />
      ) : doctors.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-300 p-12 text-center">
          <Search className="mx-auto h-8 w-8 text-slate-400" />
          <h3 className="mt-3 text-base font-bold text-slate-900">No doctors match your criteria</h3>
          <p className="mt-1 text-xs text-slate-500">
            Try adjusting your location, fee limit, or specialty filter.
          </p>
          <button
            onClick={handleResetFilters}
            className="mt-4 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-bold text-white shadow-xs hover:bg-indigo-700 transition"
          >
            Clear All Filters
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {doctors.map((doc) => (
            <div
              key={doc.id}
              className="flex flex-col justify-between rounded-2xl border border-slate-200 bg-white p-6 shadow-xs hover:border-indigo-300 hover:shadow-md transition"
            >
              <div>
                <div className="flex items-start gap-3">
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-indigo-600 font-bold text-white shadow-xs text-lg">
                    {doc.full_name.replace(/^Dr\.\s*/i, '').charAt(0) || 'D'}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5">
                      <h3 className="truncate text-base font-bold text-slate-900">{doc.full_name}</h3>
                      <span title="Verified Specialist">
                        <CheckCircle2 className="h-4 w-4 shrink-0 text-sky-500" />
                      </span>
                    </div>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {doc.specialties.map((s) => (
                        <span
                          key={s.id}
                          className="rounded-md bg-indigo-50 px-2 py-0.5 text-[11px] font-semibold text-indigo-700"
                        >
                          {s.name}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="mt-4 space-y-1.5 text-xs text-slate-600">
                  <div className="flex items-center gap-1.5">
                    <MapPin className="h-4 w-4 text-slate-400 shrink-0" />
                    <span className="truncate">
                      {doc.clinic_name ? `${doc.clinic_name}, ${doc.city}` : doc.city}
                    </span>
                  </div>
                  {doc.years_experience > 0 && (
                    <div className="flex items-center gap-1.5">
                      <Award className="h-4 w-4 text-slate-400 shrink-0" />
                      <span>{doc.years_experience} Years Clinical Experience</span>
                    </div>
                  )}
                </div>

                {doc.bio && (
                  <p className="mt-3 line-clamp-2 text-xs text-slate-500 leading-relaxed">
                    {doc.bio}
                  </p>
                )}
              </div>

              <div className="mt-6 flex items-center justify-between border-t border-slate-100 pt-4">
                <div>
                  <div className="text-[11px] text-slate-400 font-medium">Consultation Fee</div>
                  <div className="text-sm font-bold text-slate-900">
                    {doc.consultation_fee > 0 ? `৳${doc.consultation_fee} BDT` : 'Free'}
                  </div>
                </div>
                <Link
                  to={`/doctors/${doc.id}`}
                  className="inline-flex items-center gap-1.5 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-bold text-white shadow-xs hover:bg-indigo-700 transition"
                >
                  <Calendar className="h-3.5 w-3.5" />
                  Book Slot
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
