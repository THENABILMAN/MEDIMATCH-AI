import React, { useEffect, useState } from 'react'
import {
  AlertCircle,
  Award,
  CheckCircle2,
  Clock,
  FileText,
  Save,
  ShieldAlert,
  Upload,
} from 'lucide-react'
import { api } from '../../api/client'
import { Alert } from '../../components/common/Alert'
import { LoadingSpinner } from '../../components/common/LoadingSpinner'
import type { DoctorProfile, Specialty } from '../../types'

export const DoctorProfilePage: React.FC = () => {
  const [profile, setProfile] = useState<DoctorProfile | null>(null)
  const [specialties, setSpecialties] = useState<Specialty[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  // Form states
  const [bio, setBio] = useState('')
  const [qualificationsText, setQualificationsText] = useState('')
  const [yearsExperience, setYearsExperience] = useState<number>(0)
  const [consultationFee, setConsultationFee] = useState<number>(0)
  const [clinicName, setClinicName] = useState('')
  const [city, setCity] = useState('Dhaka')
  const [selectedSpecialtyIds, setSelectedSpecialtyIds] = useState<string[]>([])

  // Credential upload state
  const [docType, setDocType] = useState('bmdc_license')
  const [file, setFile] = useState<File | null>(null)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const [profData, specData] = await Promise.all([
        api.doctors.getMyProfile(),
        api.specialties.list(),
      ])
      setProfile(profData)
      setSpecialties(specData)

      setBio(profData.bio || '')
      setQualificationsText(profData.qualifications?.join(', ') || '')
      setYearsExperience(profData.years_experience || 0)
      setConsultationFee(profData.consultation_fee || 0)
      setClinicName(profData.clinic_name || '')
      setCity(profData.city || 'Dhaka')
      setSelectedSpecialtyIds(profData.specialties?.map((s) => s.id) || [])
    } catch (err: any) {
      setError(err.message || 'Failed to load profile')
    } finally {
      setIsLoading(false)
    }
  }

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSaving(true)
    setError(null)
    setSuccess(null)

    try {
      const quals = qualificationsText
        .split(',')
        .map((q) => q.trim())
        .filter(Boolean)

      const updated = await api.doctors.updateMyProfile({
        bio,
        qualifications: quals,
        years_experience: yearsExperience,
        consultation_fee: consultationFee,
        clinic_name: clinicName || undefined,
        city,
        specialty_ids: selectedSpecialtyIds,
      })

      setProfile(updated)
      setSuccess(
        'Profile updated! Note: material modifications automatically reset status to pending for administrative re-verification.'
      )
    } catch (err: any) {
      setError(err.message || 'Failed to update profile')
    } finally {
      setIsSaving(false)
    }
  }

  const handleUploadCredential = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file) return

    setIsUploading(true)
    setError(null)
    try {
      const fd = new FormData()
      fd.append('document_type', docType)
      fd.append('file', file)

      await api.doctors.uploadCredential(fd)
      setSuccess(`Credential document (${docType}) successfully uploaded for admin review.`)
      setFile(null)
    } catch (err: any) {
      setError(err.message || 'Failed to upload credential document')
    } finally {
      setIsUploading(false)
    }
  }

  const toggleSpecialty = (id: string) => {
    setSelectedSpecialtyIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    )
  }

  if (isLoading) {
    return <LoadingSpinner message="Loading doctor profile & credentials..." className="py-20" />
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
      {/* Header & Verification Status Badge */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl">
            Doctor Profile & Verification
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Manage your public professional profile, degrees, and BMDC licensing documents.
          </p>
        </div>

        {profile && (
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-slate-500">Status:</span>
            <span
              className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-bold uppercase tracking-wider ${
                profile.verification_status === 'approved'
                  ? 'bg-emerald-100 text-emerald-800'
                  : profile.verification_status === 'pending'
                  ? 'bg-amber-100 text-amber-800'
                  : profile.verification_status === 'suspended'
                  ? 'bg-rose-100 text-rose-800'
                  : 'bg-red-100 text-red-800'
              }`}
            >
              {profile.verification_status === 'approved' && <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />}
              {profile.verification_status === 'pending' && <Clock className="h-3.5 w-3.5 text-amber-600" />}
              {profile.verification_status}
            </span>
          </div>
        )}
      </div>

      {error && <Alert type="error" message={error} onClose={() => setError(null)} className="mb-6" />}
      {success && <Alert type="success" message={success} onClose={() => setSuccess(null)} className="mb-6" />}

      {profile?.verification_status === 'pending' && (
        <Alert
          type="warning"
          title="Account Pending Verification"
          message="Your doctor profile is under review by MediMatch administrators. You will be searchable by patients once approved."
          className="mb-6"
        />
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left 2 Cols: Profile Form */}
        <div className="lg:col-span-2 rounded-3xl border border-slate-200 bg-white p-6 sm:p-8 shadow-xs">
          <h2 className="text-base font-bold text-slate-900 mb-4 pb-3 border-b border-slate-100">
            Profile Details
          </h2>

          <form onSubmit={handleSaveProfile} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700">Years of Experience</label>
                <input
                  type="number"
                  min="0"
                  value={yearsExperience}
                  onChange={(e) => setYearsExperience(Number(e.target.value))}
                  className="mt-1 w-full rounded-xl border border-slate-200 py-2.5 px-3 text-sm text-slate-900 focus:border-indigo-600 focus:outline-hidden"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700">Consultation Fee (BDT)</label>
                <input
                  type="number"
                  min="0"
                  step="50"
                  value={consultationFee}
                  onChange={(e) => setConsultationFee(Number(e.target.value))}
                  className="mt-1 w-full rounded-xl border border-slate-200 py-2.5 px-3 text-sm text-slate-900 focus:border-indigo-600 focus:outline-hidden"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700">Clinic / Hospital Name</label>
                <input
                  type="text"
                  value={clinicName}
                  onChange={(e) => setClinicName(e.target.value)}
                  placeholder="e.g. Square Hospital, Dhaka"
                  className="mt-1 w-full rounded-xl border border-slate-200 py-2.5 px-3 text-sm text-slate-900 focus:border-indigo-600 focus:outline-hidden"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700">City</label>
                <select
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-slate-200 bg-white py-2.5 px-3 text-sm text-slate-900 focus:border-indigo-600 focus:outline-hidden"
                >
                  <option value="Dhaka">Dhaka</option>
                  <option value="Chittagong">Chittagong</option>
                  <option value="Sylhet">Sylhet</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700">
                Degrees & Qualifications (Comma Separated)
              </label>
              <input
                type="text"
                value={qualificationsText}
                onChange={(e) => setQualificationsText(e.target.value)}
                placeholder="MBBS, FCPS (Neurology), MD"
                className="mt-1 w-full rounded-xl border border-slate-200 py-2.5 px-3 text-sm text-slate-900 focus:border-indigo-600 focus:outline-hidden"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700">
                Specialties (Select all that apply)
              </label>
              <div className="mt-2 flex flex-wrap gap-2">
                {specialties.map((s) => {
                  const isChecked = selectedSpecialtyIds.includes(s.id)
                  return (
                    <button
                      type="button"
                      key={s.id}
                      onClick={() => toggleSpecialty(s.id)}
                      className={`rounded-xl px-3 py-1.5 text-xs font-semibold transition ${
                        isChecked
                          ? 'bg-indigo-600 text-white shadow-xs'
                          : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                      }`}
                    >
                      {s.name}
                    </button>
                  )
                })}
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700">Clinical Bio & Scope of Practice</label>
              <textarea
                rows={4}
                value={bio}
                onChange={(e) => setBio(e.target.value)}
                placeholder="Describe clinical interests, specialized procedures, and patient care philosophy..."
                className="mt-1 w-full rounded-xl border border-slate-200 p-3 text-sm text-slate-900 focus:border-indigo-600 focus:outline-hidden leading-relaxed"
              />
            </div>

            <div className="pt-4 border-t border-slate-100 flex items-center justify-between">
              <span className="text-[11px] text-slate-400">
                Changes will be synced to search index upon approval.
              </span>
              <button
                type="submit"
                disabled={isSaving}
                className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-xs font-bold text-white shadow-xs hover:bg-indigo-700 transition disabled:opacity-50"
              >
                <Save className="h-4 w-4" />
                {isSaving ? 'Saving Changes...' : 'Save Profile'}
              </button>
            </div>
          </form>
        </div>

        {/* Right Col: Credential Upload */}
        <div className="space-y-6">
          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-xs">
            <h2 className="text-base font-bold text-slate-900 mb-2 pb-3 border-b border-slate-100">
              Upload Verification Credentials
            </h2>
            <p className="text-xs text-slate-500 leading-relaxed mb-4">
              Upload your BMDC registration certificate or postgraduate diploma. Stored in a private, secure storage bucket.
            </p>

            <form onSubmit={handleUploadCredential} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700">Document Type</label>
                <select
                  value={docType}
                  onChange={(e) => setDocType(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-slate-200 bg-white py-2 px-3 text-xs text-slate-800 focus:border-indigo-600 focus:outline-hidden"
                >
                  <option value="bmdc_license">BMDC Medical License</option>
                  <option value="mbbs_degree">MBBS Degree Certificate</option>
                  <option value="postgraduate_degree">Postgraduate Fellowship (FCPS/MD)</option>
                  <option value="institutional_id">Hospital Affiliation ID</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700">File (PDF, PNG, JPG)</label>
                <input
                  type="file"
                  required
                  accept=".pdf,image/png,image/jpeg"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  className="mt-1 block w-full text-xs text-slate-500 file:mr-4 file:py-2 file:px-3 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 cursor-pointer"
                />
              </div>

              <button
                type="submit"
                disabled={!file || isUploading}
                className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-slate-900 py-2.5 text-xs font-bold text-white shadow-xs hover:bg-slate-800 transition disabled:opacity-50"
              >
                <Upload className="h-4 w-4" />
                {isUploading ? 'Uploading...' : 'Upload Document'}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}

