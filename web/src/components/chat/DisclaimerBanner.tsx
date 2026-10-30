import React from 'react'
import { ShieldAlert } from 'lucide-react'

export const DisclaimerBanner: React.FC = () => {
  return (
    <div
      data-testid="disclaimer-banner"
      className="flex items-center gap-3 border-b border-amber-200 bg-amber-50/90 px-4 py-2.5 text-xs text-amber-900 shadow-2xs"
    >
      <ShieldAlert className="h-4 w-4 shrink-0 text-amber-600" />
      <div className="flex-1 leading-snug">
        <span className="font-bold">Medical Safety Notice: </span>
        MediMatch AI does not provide clinical diagnosis, prescriptions, or emergency triage. For severe or life-threatening symptoms, call{' '}
        <a href="tel:999" className="font-bold underline hover:text-red-700">
          999 (National Emergency)
        </a>{' '}
        immediately.
      </div>
    </div>
  )
}

