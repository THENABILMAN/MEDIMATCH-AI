import React, { useEffect, useState } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { api } from '../../api/client'
import { Alert } from '../../components/common/Alert'
import { LoadingSpinner } from '../../components/common/LoadingSpinner'
import type { AuditLog } from '../../types'

export const AdminAuditLogsPage: React.FC = () => {
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const limit = 20
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadAuditLogs = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const offset = (page - 1) * limit
      const data = await api.admin.listAuditLogs(limit, offset)
      setLogs(data.items)
      setTotal(data.total)
    } catch (err: any) {
      setError(err.message || 'Failed to load audit logs')
    } finally {
      setIsLoading(false)
    }

  }

  useEffect(() => {
    loadAuditLogs()
  }, [page])

  const totalPages = Math.ceil(total / limit) || 1

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-8">
        <h1 className="text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl">
          System Security & Audit Logs
        </h1>
        <p className="mt-1 text-sm text-slate-600">
          Immutable records of doctor approvals, profile updates, and appointment cancellations.
        </p>
      </div>

      {error && <Alert type="error" message={error} onClose={() => setError(null)} className="mb-6" />}

      <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-xs overflow-hidden">
        {isLoading ? (
          <LoadingSpinner message="Loading audit trail..." className="py-20" />
        ) : logs.length === 0 ? (
          <div className="py-12 text-center text-xs text-slate-400">
            No audit log entries found.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-100 text-[11px] font-bold uppercase tracking-wider text-slate-400">
                  <th className="py-3 px-4">Timestamp (UTC)</th>
                  <th className="py-3 px-4">Action</th>
                  <th className="py-3 px-4">Actor</th>
                  <th className="py-3 px-4">Target Type & ID</th>
                  <th className="py-3 px-4">Metadata</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono">
                {logs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-50 transition">
                    <td className="py-3 px-4 text-slate-600 whitespace-nowrap">
                      {new Date(log.created_at).toLocaleString()}
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">
                      <span className="rounded-md bg-indigo-50 px-2 py-0.5 text-[10px] font-bold text-indigo-700 font-sans uppercase">
                        {log.action}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-500 text-[11px] truncate max-w-[120px]">
                      {log.actor_id || 'system'}
                    </td>
                    <td className="py-3 px-4 text-slate-700 whitespace-nowrap">
                      <span className="font-sans font-semibold text-slate-900">{log.target_type}</span>{' '}
                      <span className="text-slate-400 text-[10px]">({log.target_id?.slice(0, 8)}...)</span>
                    </td>
                    <td className="py-3 px-4 text-slate-600 text-[11px] max-w-xs truncate">
                      {JSON.stringify(log.metadata)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Bar */}
        <div className="mt-6 flex items-center justify-between border-t border-slate-100 pt-4 text-xs text-slate-500">
          <span>
            Showing page <strong className="text-slate-900">{page}</strong> of{' '}
            <strong className="text-slate-900">{totalPages}</strong> ({total} total events)
          </span>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="rounded-lg border border-slate-200 p-1.5 hover:bg-slate-50 disabled:opacity-40"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="rounded-lg border border-slate-200 p-1.5 hover:bg-slate-50 disabled:opacity-40"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
