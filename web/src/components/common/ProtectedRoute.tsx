import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import type { UserRole } from '../../types'
import { Button } from '../ui/button'
import { EmptyState } from '../ui/empty-state'
import { Skeleton } from '../ui/skeleton'

export const ROLE_HOME: Record<UserRole, string> = {
  patient: '/chat',
  doctor: '/doctor/appointments',
  admin: '/admin/queue',
}

interface ProtectedRouteProps {
  children: ReactNode
  allowedRoles?: UserRole[]
}

export function ProtectedRoute({ children, allowedRoles }: ProtectedRouteProps) {
  const { t } = useTranslation()
  const { user, role, isLoading, refreshProfile } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return (
      <div className="page-gutter py-8" role="status">
        <span className="sr-only">{t('common.verifyingSession')}</span>
        <Skeleton className="h-10 w-64" />
        <Skeleton className="mt-4 h-40" />
      </div>
    )
  }

  if (!user) return <Navigate to="/login" state={{ from: location }} replace />

  // Signed in but the profile did not load: don't guess a role
  if (!role) {
    return (
      <div className="page-gutter py-8">
        <EmptyState
          title={t('errors.loadTitle')}
          description={t('errors.profileBody')}
          action={
            <Button variant="secondary" onClick={() => void refreshProfile()}>
              {t('common.tryAgain')}
            </Button>
          }
        />
      </div>
    )
  }

  if (allowedRoles && !allowedRoles.includes(role)) return <Navigate to={ROLE_HOME[role]} replace />

  return <>{children}</>
}
