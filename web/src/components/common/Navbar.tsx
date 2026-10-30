import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Activity,
  Calendar,
  CheckCircle,
  Clock,
  FileText,
  LogOut,
  Menu,
  MessageSquare,
  Search,
  Shield,
  User,
  X,
} from 'lucide-react'
import { useAuth } from '../../contexts/AuthContext'

export const Navbar: React.FC = () => {
  const { user, profile, role, logout } = useAuth()
  const navigate = useNavigate()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  return (
    <nav className="sticky top-0 z-50 border-b border-slate-200 bg-white/95 backdrop-blur shadow-xs">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6 lg:px-8">
        {/* Brand */}
        <Link to="/" className="flex items-center gap-2.5 transition hover:opacity-90">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-linear-to-tr from-indigo-600 to-violet-500 text-white shadow-xs">
            <Activity className="h-5 w-5" />
          </div>
          <div>
            <span className="text-lg font-bold tracking-tight text-slate-900">MediMatch</span>
            <span className="text-lg font-bold text-indigo-600"> AI</span>
          </div>
        </Link>

        {/* Desktop Navigation */}
        <div className="hidden md:flex md:items-center md:gap-1">
          {/* Patient Links */}
          {(!role || role === 'patient') && (
            <>
              <Link
                to="/chat"
                className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 hover:text-indigo-600"
              >
                <MessageSquare className="h-4 w-4" />
                AI Assistant
              </Link>
              <Link
                to="/doctors"
                className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 hover:text-indigo-600"
              >
                <Search className="h-4 w-4" />
                Find Doctors
              </Link>
              {user && (
                <Link
                  to="/appointments"
                  className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 hover:text-indigo-600"
                >
                  <Calendar className="h-4 w-4" />
                  My Appointments
                </Link>
              )}
            </>
          )}

          {/* Doctor Links */}
          {role === 'doctor' && (
            <>
              <Link
                to="/doctor/profile"
                className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 hover:text-indigo-600"
              >
                <User className="h-4 w-4" />
                Profile & Credentials
              </Link>
              <Link
                to="/doctor/availability"
                className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 hover:text-indigo-600"
              >
                <Clock className="h-4 w-4" />
                Manage Slots
              </Link>
              <Link
                to="/doctor/appointments"
                className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 hover:text-indigo-600"
              >
                <Calendar className="h-4 w-4" />
                Appointments
              </Link>
            </>
          )}

          {/* Admin Links */}
          {role === 'admin' && (
            <>
              <Link
                to="/admin/doctors"
                className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 hover:text-indigo-600"
              >
                <CheckCircle className="h-4 w-4" />
                Doctor Approvals
              </Link>
              <Link
                to="/admin/specialties"
                className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 hover:text-indigo-600"
              >
                <Activity className="h-4 w-4" />
                Specialties
              </Link>
              <Link
                to="/admin/audit-logs"
                className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 hover:text-indigo-600"
              >
                <FileText className="h-4 w-4" />
                Audit Logs
              </Link>
            </>
          )}
        </div>

        {/* User Auth Controls */}
        <div className="hidden md:flex md:items-center md:gap-3">
          {user ? (
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 py-1 pl-3 pr-2 shadow-2xs">
                <span className="text-xs font-semibold text-slate-800">
                  {profile?.full_name || user.email}
                </span>
                <span
                  className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                    role === 'admin'
                      ? 'bg-amber-100 text-amber-800'
                      : role === 'doctor'
                      ? 'bg-sky-100 text-sky-800'
                      : 'bg-emerald-100 text-emerald-800'
                  }`}
                >
                  {role || 'patient'}
                </span>
              </div>
              <button
                onClick={handleLogout}
                className="flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:border-red-200 hover:bg-red-50 hover:text-red-600"
                title="Log out"
              >
                <LogOut className="h-3.5 w-3.5" />
                Logout
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Link
                to="/login"
                className="rounded-lg px-3.5 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
              >
                Log In
              </Link>
              <Link
                to="/register"
                className="rounded-lg bg-indigo-600 px-3.5 py-1.5 text-sm font-semibold text-white shadow-xs transition hover:bg-indigo-700"
              >
                Register
              </Link>
            </div>
          )}
        </div>

        {/* Mobile menu button */}
        <div className="md:hidden">
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="rounded-lg p-2 text-slate-600 hover:bg-slate-100"
          >
            {mobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="border-t border-slate-200 bg-white px-4 pt-2 pb-4 md:hidden">
          <div className="flex flex-col gap-1">
            {(!role || role === 'patient') && (
              <>
                <Link
                  to="/chat"
                  onClick={() => setMobileMenuOpen(false)}
                  className="rounded-md px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
                >
                  AI Symptom Chat
                </Link>
                <Link
                  to="/doctors"
                  onClick={() => setMobileMenuOpen(false)}
                  className="rounded-md px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
                >
                  Find Doctors
                </Link>
                {user && (
                  <Link
                    to="/appointments"
                    onClick={() => setMobileMenuOpen(false)}
                    className="rounded-md px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
                  >
                    My Appointments
                  </Link>
                )}
              </>
            )}

            {role === 'doctor' && (
              <>
                <Link
                  to="/doctor/profile"
                  onClick={() => setMobileMenuOpen(false)}
                  className="rounded-md px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
                >
                  Profile & Credentials
                </Link>
                <Link
                  to="/doctor/availability"
                  onClick={() => setMobileMenuOpen(false)}
                  className="rounded-md px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
                >
                  Manage Availability Slots
                </Link>
                <Link
                  to="/doctor/appointments"
                  onClick={() => setMobileMenuOpen(false)}
                  className="rounded-md px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
                >
                  Scheduled Appointments
                </Link>
              </>
            )}

            {role === 'admin' && (
              <>
                <Link
                  to="/admin/doctors"
                  onClick={() => setMobileMenuOpen(false)}
                  className="rounded-md px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
                >
                  Doctor Approvals
                </Link>
                <Link
                  to="/admin/specialties"
                  onClick={() => setMobileMenuOpen(false)}
                  className="rounded-md px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
                >
                  Manage Specialties
                </Link>
                <Link
                  to="/admin/audit-logs"
                  onClick={() => setMobileMenuOpen(false)}
                  className="rounded-md px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
                >
                  Audit Logs
                </Link>
              </>
            )}

            <div className="mt-2 border-t border-slate-100 pt-2">
              {user ? (
                <button
                  onClick={() => {
                    setMobileMenuOpen(false)
                    handleLogout()
                  }}
                  className="w-full text-left rounded-md px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50"
                >
                  Log Out
                </button>
              ) : (
                <div className="flex flex-col gap-2">
                  <Link
                    to="/login"
                    onClick={() => setMobileMenuOpen(false)}
                    className="text-center rounded-md border border-slate-200 py-2 text-sm font-medium text-slate-700"
                  >
                    Log In
                  </Link>
                  <Link
                    to="/register"
                    onClick={() => setMobileMenuOpen(false)}
                    className="text-center rounded-md bg-indigo-600 py-2 text-sm font-semibold text-white"
                  >
                    Register
                  </Link>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </nav>
  )
}

