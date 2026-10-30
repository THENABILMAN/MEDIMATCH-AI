import React from 'react'
import { Link } from 'react-router-dom'
import {
  Activity,
  ArrowRight,
  Calendar,
  CheckCircle2,
  Clock,
  HeartPulse,
  MessageSquare,
  Search,
  ShieldCheck,
  Sparkles,
} from 'lucide-react'

export const HomePage: React.FC = () => {
  return (
    <div className="flex flex-col min-h-[calc(100vh-65px)] bg-slate-50">
      {/* Hero Section */}
      <section className="relative overflow-hidden pt-12 pb-20 sm:pt-20 sm:pb-28">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-indigo-200 bg-indigo-50/70 py-1.5 px-4 text-xs font-semibold text-indigo-700 shadow-2xs mb-6">
            <Sparkles className="h-4 w-4" />
            <span>AI-Powered Medical Specialist Matching in Bangladesh</span>
          </div>

          <h1 className="text-4xl font-extrabold tracking-tight text-slate-900 sm:text-5xl lg:text-6xl">
            Describe your symptoms. <br className="hidden sm:inline" />
            <span className="bg-linear-to-r from-indigo-600 to-violet-600 bg-clip-text text-transparent">
              Find the right verified doctor.
            </span>
          </h1>

          <p className="mx-auto mt-6 max-w-2xl text-base text-slate-600 sm:text-lg leading-relaxed">
            MediMatch AI guides you to appropriate medical specialists safely and transparently. We never diagnose or prescribe — we help you connect with qualified doctors across Dhaka, Chittagong, and Sylhet.
          </p>

          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              to="/chat"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-2xl bg-indigo-600 px-6 py-3.5 text-sm font-bold text-white shadow-md transition hover:bg-indigo-700 active:scale-95"
            >
              <MessageSquare className="h-4 w-4" />
              Start AI Symptom Consultation
              <ArrowRight className="h-4 w-4" />
            </Link>

            <Link
              to="/doctors"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-6 py-3.5 text-sm font-bold text-slate-700 shadow-xs transition hover:bg-slate-100"
            >
              <Search className="h-4 w-4" />
              Browse Verified Specialists
            </Link>
          </div>
        </div>
      </section>

      {/* Feature Value Props */}
      <section className="border-t border-slate-200/80 bg-white py-16">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 gap-8 sm:grid-cols-3">
            {/* Feature 1 */}
            <div className="rounded-3xl border border-slate-100 bg-slate-50/50 p-8 shadow-2xs">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-red-100 text-red-600 mb-6">
                <HeartPulse className="h-6 w-6" />
              </div>
              <h3 className="text-lg font-bold text-slate-900">Deterministic Safety First</h3>
              <p className="mt-2 text-xs leading-relaxed text-slate-600">
                Rule-based emergency detection in English and Bangla immediately routes critical symptoms to the 999 national helpline with zero delay.
              </p>
            </div>

            {/* Feature 2 */}
            <div className="rounded-3xl border border-slate-100 bg-slate-50/50 p-8 shadow-2xs">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-100 text-indigo-600 mb-6">
                <ShieldCheck className="h-6 w-6" />
              </div>
              <h3 className="text-lg font-bold text-slate-900">BMDC-Verified Specialists</h3>
              <p className="mt-2 text-xs leading-relaxed text-slate-600">
                Every doctor in our directory undergoes institutional credential validation. Only approved, verified profiles are ever searchable or bookable.
              </p>
            </div>

            {/* Feature 3 */}
            <div className="rounded-3xl border border-slate-100 bg-slate-50/50 p-8 shadow-2xs">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-100 text-emerald-600 mb-6">
                <Clock className="h-6 w-6" />
              </div>
              <h3 className="text-lg font-bold text-slate-900">Zero Double-Booking Guarantee</h3>
              <p className="mt-2 text-xs leading-relaxed text-slate-600">
                Database-level pessimistic row locking ensures you and other patients can never book the exact same slot concurrently.
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}

