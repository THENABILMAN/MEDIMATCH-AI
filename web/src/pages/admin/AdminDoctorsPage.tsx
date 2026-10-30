import React, { useEffect, useState } from 'react'
import {
  Check,
  FileText,
  Pause,
  Shield,
  X,
} from 'lucide-react'
import { api } from '../../api/client'
import { Alert } from '../../components/common/Alert'
import { LoadingSpinner } from '../../components/common/LoadingSpinner'
import type { DoctorCredential, DoctorProfile, VerificationStatus } from '../../types'

export const AdminDoctorsPage: React.FC = () => {
  const [doctors, setDoctors] = useState<(DoctorProfile & { credentials?: DoctorCredential[] })[]>([])
  const [statusFilter, setStatusFilter] = useState<VerificationStatus | ''>('pending')
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const loadDoctors = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await api.admin.listDoctors(
        statusFilter ? (statusFilter as VerificationStatus) : undefined
      )
      setDoctors(data.items)
    } catch (err: any) {
      setError(err.message || 'Failed to load doctors')
    } finally {
      setIsLoading(false)
    }

  }

  useEffect(() => {
    loadDoctors()
  }, [statusFilter])

  const handleApprove = async (docId: string) => {
    setError(null)
    try {
      await api.admin.approveDoctor(docId)
      setSuccess('Doctor approved! Vector sync has been triggered.')
      loadDoctors()
    } catch (err: any) {
      setError(err.message || 'Approval failed')
    }
  }

  const handleReject = async (docId: string) => {
    const reason = prompt('Enter rejection reason:')
    if (!reason) return

    setError(null)
    try {
      await api.admin.rejectDoctor(docId, reason)
      setSuccess('Doctor application rejected.')
      loadDoctors()
    } catch (err: any) {
      setError(err.message || 'Rejection failed')
    }
  }

  const handleSuspend = async (docId: string) => {
    const reason = prompt('Enter suspension reason:')
    if (!reason) return

    setError(null)
    try {
      await api.admin.suspendDoctor(docId, reason)
      setSuccess('Doctor profile suspended and vector purged from search index.')
      loadDoctors()
    } catch (err: any) {
      setError(err.message || 'Suspension failed')
    }
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl">
            Doctor Verification & Oversight
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Review credential documents, approve medical licenses, and manage suspension status.
          </p>
        </div>

        {/* Status Filter Tabs */}
        <div className="flex rounded-xl bg-slate-100 p-1 text-xs font-bold">
          {(['pending', 'approved', 'suspended', 'rejected', ''] as const).map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`rounded-lg px-3 py-1.5 capitalize transition ${
                statusFilter === s
                  ? 'bg-white text-indigo-700 shadow-2xs font-extrabold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              {s || 'All'}
            </button>
          ))}
        </div>
      </div>

      {error && <Alert type="error" message={error} onClose={() => setError(null)} className="mb-6" />}
      {success && <Alert type="success" message={success} onClose={() => setSuccess(null)} className="mb-6" />}

      {isLoading ? (
        <LoadingSpinner message="Loading doctor profiles..." className="py-20" />
      ) : doctors.length === 0 ? (
        <div className="rounded-3xl border border-dashed border-slate-300 p-12 text-center bg-white">
          <Shield className="mx-auto h-10 w-10 text-slate-300" />
          <h3 className="mt-4 text-base font-bold text-slate-900">No doctors in this queue</h3>
          <p className="mt-1 text-xs text-slate-500">
            No profiles currently match the selected verification status.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {doctors.map((doc) => (
            <div
              key={doc.id}
              className="flex flex-col rounded-2xl border border-slate-200 bg-white p-6 shadow-xs hover:border-slate-300 transition"
            >
              <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
                <div className="flex items-start gap-4">
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-700 font-bold text-lg">
                    {doc.full_name.replace(/^Dr\.\s*/i, '').charAt(0) || 'D'}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-base font-bold text-slate-900">{doc.full_name}</h3>
                      <span
                        className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                          doc.verification_status === 'approved'
                            ? 'bg-emerald-100 text-emerald-800'
                            : doc.verification_status === 'pending'
                            ? 'bg-amber-100 text-amber-800'
                            : doc.verification_status === 'suspended'
                            ? 'bg-rose-100 text-rose-800'
                            : 'bg-red-100 text-red-800'
                        }`}
                      >
                        {doc.verification_status}
                      </span>
                    </div>

                    <div className="mt-1 flex flex-wrap gap-1">
                      {doc.specialties?.map((s) => (
                        <span
                          key={s.id}
                          className="rounded-md bg-indigo-50 px-2 py-0.5 text-[11px] font-semibold text-indigo-700"
                        >
                          {s.name}
                        </span>
                      ))}
                    </div>

                    <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500">
                      <span>{doc.clinic_name ? `${doc.clinic_name}, ` : ''}{doc.city}</span>
                      <span>•</span>
                      <span>{doc.years_experience} yrs exp</span>
                      <span>•</span>
                      <span>Fee: ৳{doc.consultation_fee} BDT</span>
                    </div>

                    {doc.qualifications && doc.qualifications.length > 0 && (
                      <div className="mt-2 text-xs text-slate-600">
                        Degrees: <span className="font-semibold">{doc.qualifications.join(', ')}</span>
                      </div>
                    )}

                    {doc.bio && (
                      <p className="mt-2 text-xs text-slate-500 line-clamp-2 max-w-2xl">
                        {doc.bio}
                      </p>
                    )}
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex items-center gap-2 sm:self-start">
                  {doc.verification_status !== 'approved' && (
                    <button
                      onClick={() => handleApprove(doc.id)}
                      className="inline-flex items-center gap-1 rounded-xl bg-emerald-600 px-3.5 py-2 text-xs font-bold text-white shadow-xs hover:bg-emerald-700 transition"
                    >
                      <Check className="h-3.5 w-3.5" />
                      Approve
                    </button>
                  )}

                  {doc.verification_status !== 'rejected' && doc.verification_status === 'pending' && (
                    <button
                      onClick={() => handleReject(doc.id)}
                      className="inline-flex items-center gap-1 rounded-xl border border-red-200 bg-red-50 px-3.5 py-2 text-xs font-bold text-red-700 hover:bg-red-100 transition"
                    >
                      <X className="h-3.5 w-3.5" />
                      Reject
                    </button>
                  )}

                  {doc.verification_status === 'approved' && (
                    <button
                      onClick={() => handleSuspend(doc.id)}
                      className="inline-flex items-center gap-1 rounded-xl border border-amber-200 bg-amber-50 px-3.5 py-2 text-xs font-bold text-amber-800 hover:bg-amber-100 transition"
                    >
                      <Pause className="h-3.5 w-3.5" />
                      Suspend
                    </button>
                  )}
                </div>
              </div>

              {/* Uploaded Credentials Section */}
              {doc.credentials && doc.credentials.length > 0 && (
                <div className="mt-4 pt-3 border-t border-slate-100">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-2">
                    Submitted Verification Documents ({doc.credentials.length})
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {doc.credentials.map((cred) => (
                      <div
                        key={cred.id}
                        className="flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs text-slate-700"
                      >
                        <FileText className="h-3.5 w-3.5 text-indigo-600" />
                        <span className="font-semibold uppercase">{cred.document_type.replace('_', ' ')}</span>
                        <span className="text-slate-400 font-mono text-[10px] truncate max-w-xs">{cred.file_path}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
