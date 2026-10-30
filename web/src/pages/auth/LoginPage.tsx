import React, { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Activity, ArrowRight, Lock, Mail } from 'lucide-react'
import { Alert } from '../../components/common/Alert'
import { useAuth } from '../../contexts/AuthContext'

export const LoginPage: React.FC = () => {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as any)?.from?.pathname || '/'

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setIsSubmitting(true)

    try {
      await login(email, password)
      navigate(from, { replace: true })
    } catch (err: any) {
      setError(err.message || 'Login failed. Please verify your credentials.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const fillDemoAccount = (demoEmail: string, demoPass: string) => {
    setEmail(demoEmail)
    setPassword(demoPass)
    setError(null)
  }

  return (
    <div className="flex min-h-[calc(100vh-65px)] items-center justify-center px-4 py-12 sm:px-6 lg:px-8">
      <div className="w-full max-w-md space-y-8 rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-600 text-white shadow-md">
            <Activity className="h-7 w-7" />
          </div>
          <h2 className="mt-4 text-2xl font-extrabold tracking-tight text-slate-900">
            Sign in to MediMatch AI
          </h2>
          <p className="mt-1.5 text-xs text-slate-600">
            Access verified specialist discovery and appointment management
          </p>
        </div>

        {error && <Alert type="error" message={error} onClose={() => setError(null)} />}

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700">Email Address</label>
            <div className="relative mt-1">
              <Mail className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-slate-400" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="w-full rounded-xl border border-slate-200 py-2.5 pl-10 pr-4 text-sm text-slate-900 transition focus:border-indigo-600 focus:outline-hidden focus:ring-1 focus:ring-indigo-600"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700">Password</label>
            <div className="relative mt-1">
              <Lock className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-slate-400" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full rounded-xl border border-slate-200 py-2.5 pl-10 pr-4 text-sm text-slate-900 transition focus:border-indigo-600 focus:outline-hidden focus:ring-1 focus:ring-indigo-600"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 py-2.5 text-sm font-bold text-white shadow-xs transition hover:bg-indigo-700 disabled:opacity-50"
          >
            {isSubmitting ? 'Signing in...' : 'Sign In'}
            <ArrowRight className="h-4 w-4" />
          </button>
        </form>

        {/* Demo Fast-Login Helpers */}
        <div className="mt-6 rounded-2xl border border-dashed border-indigo-200 bg-indigo-50/50 p-4">
          <p className="text-[11px] font-bold uppercase tracking-wider text-indigo-900">
            Demo Fast-Login Accounts
          </p>
          <div className="mt-2.5 grid grid-cols-3 gap-2">
            <button
              type="button"
              onClick={() => fillDemoAccount('patient@medimatch.test', 'Patient123!Safe')}
              className="rounded-lg border border-indigo-200 bg-white py-1.5 px-2 text-[11px] font-semibold text-indigo-700 hover:bg-indigo-50 transition"
            >
              👤 Patient
            </button>
            <button
              type="button"
              onClick={() => fillDemoAccount('doctor@medimatch.test', 'Doctor123!Safe')}
              className="rounded-lg border border-indigo-200 bg-white py-1.5 px-2 text-[11px] font-semibold text-indigo-700 hover:bg-indigo-50 transition"
            >
              🩺 Doctor
            </button>
            <button
              type="button"
              onClick={() => fillDemoAccount('admin@medimatch.test', 'Admin123!Safe')}
              className="rounded-lg border border-indigo-200 bg-white py-1.5 px-2 text-[11px] font-semibold text-indigo-700 hover:bg-indigo-50 transition"
            >
              🛡️ Admin
            </button>
          </div>
        </div>

        <div className="text-center text-xs text-slate-600">
          Don't have an account?{' '}
          <Link to="/register" className="font-bold text-indigo-600 hover:underline">
            Register here
          </Link>
        </div>
      </div>
    </div>
  )
}

