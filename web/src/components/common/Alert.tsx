import React from 'react'
import { AlertCircle, AlertTriangle, CheckCircle2, Info, X } from 'lucide-react'

interface AlertProps {
  type?: 'error' | 'warning' | 'success' | 'info'
  title?: string
  message: string
  onClose?: () => void
  className?: string
}

export const Alert: React.FC<AlertProps> = ({
  type = 'info',
  title,
  message,
  onClose,
  className = '',
}) => {
  const styles = {
    error: {
      bg: 'bg-red-50 border-red-200 text-red-900',
      icon: <AlertCircle className="h-5 w-5 text-red-600 shrink-0" />,
      titleColor: 'text-red-900 font-semibold',
    },
    warning: {
      bg: 'bg-amber-50 border-amber-200 text-amber-900',
      icon: <AlertTriangle className="h-5 w-5 text-amber-600 shrink-0" />,
      titleColor: 'text-amber-900 font-semibold',
    },
    success: {
      bg: 'bg-emerald-50 border-emerald-200 text-emerald-900',
      icon: <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0" />,
      titleColor: 'text-emerald-900 font-semibold',
    },
    info: {
      bg: 'bg-sky-50 border-sky-200 text-sky-900',
      icon: <Info className="h-5 w-5 text-sky-600 shrink-0" />,
      titleColor: 'text-sky-900 font-semibold',
    },
  }[type]

  return (
    <div
      role="alert"
      className={`flex items-start gap-3 rounded-xl border p-4 shadow-2xs ${styles.bg} ${className}`}
    >
      {styles.icon}
      <div className="flex-1 text-sm leading-relaxed">
        {title && <div className={`mb-0.5 ${styles.titleColor}`}>{title}</div>}
        <div>{message}</div>
      </div>
      {onClose && (
        <button
          onClick={onClose}
          className="ml-auto -mr-1 -mt-1 rounded-md p-1 opacity-70 hover:opacity-100"
          aria-label="Close"
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  )
}

