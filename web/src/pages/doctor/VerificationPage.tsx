import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { useMyDoctorProfile, useVerificationHistory } from '../../api/hooks'
import { StatusTimeline } from '../../components/domain/status-timeline'
import { PageHeader } from '../../components/layout/page-header'
import { Button } from '../../components/ui/button'
import { EmptyState } from '../../components/ui/empty-state'
import { ErrorState } from '../../components/ui/query-state'
import { Skeleton } from '../../components/ui/skeleton'

export default function VerificationPage() {
  const { t } = useTranslation()
  const profile = useMyDoctorProfile()
  const history = useVerificationHistory()

  return (
    <div className="page-gutter py-6 md:py-8">
      <PageHeader
        title={t('verification.title')}
      />
      {profile.isPending || history.isPending ? (
        <Skeleton className="h-40 max-w-2xl" />
      ) : profile.isError ? (
        <ErrorState error={profile.error} onRetry={() => void profile.refetch()} />
      ) : (
        <div className="grid gap-8 lg:grid-cols-12">
          <div className="lg:col-span-5">
            <h2 className="heading-3">{t(`verification.status.${profile.data.verification_status}`)}</h2>
            <p className="prose-width mt-3 body-7">{t(`verification.next.${profile.data.verification_status}`)}</p>
            <div className="mt-4 flex flex-wrap gap-2">
              {profile.data.verification_status === 'approved' ? (
                <Button asChild>
                  <Link to="/doctor/availability">{t('verification.setAvailability')}</Link>
                </Button>
              ) : profile.data.verification_status === 'suspended' ? null : (
                <>
                  {profile.data.verification_status === 'pending' && (
                    <Button asChild>
                      <Link to="/doctor/onboarding">{t('verification.continueSetup')}</Link>
                    </Button>
                  )}
                  <Button asChild variant="secondary">
                    <Link to="/doctor/profile">{t('verification.editProfile')}</Link>
                  </Button>
                  <Button asChild variant="secondary">
                    <Link to="/doctor/credentials">{t('nav.credentials')}</Link>
                  </Button>
                </>
              )}
            </div>
          </div>
          <div className="min-w-0 lg:col-span-7">
            <h2 className="mb-3 heading-5">{t('verification.history')}</h2>
            {history.isError ? (
              <ErrorState error={history.error} onRetry={() => void history.refetch()} />
            ) : history.data?.length ? (
              <StatusTimeline events={history.data} />
            ) : (
              <EmptyState title={t('verification.emptyTitle')} description={t('verification.emptyBody')} />
            )}
          </div>
        </div>
      )}
    </div>
  )
}
