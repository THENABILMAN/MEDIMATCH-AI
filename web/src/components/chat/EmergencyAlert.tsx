import React from 'react'
import { AlertOctagon, PhoneCall } from 'lucide-react'

interface EmergencyAlertProps {
  message?: string
}

export const EmergencyAlert: React.FC<EmergencyAlertProps> = ({ message }) => {
  return (
    <div
      data-testid="emergency-alert"
      className="my-4 rounded-2xl border-2 border-red-500 bg-red-50 p-5 text-red-950 shadow-md animate-pulse"
    >
      <div className="flex items-start gap-3">
        <div className="rounded-xl bg-red-600 p-2 text-white">
          <AlertOctagon className="h-6 w-6" />
        </div>
        <div className="flex-1">
          <h3 className="text-base font-extrabold uppercase tracking-wide text-red-700">
            Immediate Medical Attention Required
          </h3>
          <p className="mt-1 text-sm font-medium leading-relaxed text-red-900">
            {message ||
              'Your described symptoms indicate a potentially life-threatening medical emergency. Please do not wait for an online doctor appointment.'}
          </p>

          <div className="mt-4 flex flex-wrap items-center gap-3">
            <a
              href="tel:999"
              className="inline-flex items-center gap-2 rounded-xl bg-red-600 px-5 py-2.5 text-sm font-bold text-white shadow-sm transition hover:bg-red-700 active:scale-95"
            >
              <PhoneCall className="h-4 w-4" />
              Call 999 Emergency Services
            </a>
            <span className="text-xs font-semibold text-red-700">
              Bangladesh National Emergency Helpline (Toll-Free)
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}

