import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { useMyDoctorProfile, useUpdateDoctorProfile } from '../../api/hooks'
import {
  ClinicalFields,
  PracticeFields,
  toProfileInput,
  useDoctorProfileForm,
  type DoctorProfileValues,
} from '../../components/domain/doctor-profile-form'
import { VerificationBadge } from '../../components/domain/verification-badge'
import { PageHeader } from '../../components/layout/page-header'
import { Banner } from '../../components/ui/banner'
import { Button } from '../../components/ui/button'
import { ErrorState } from '../../components/ui/query-state'
import { Skeleton } from '../../components/ui/skeleton'
import { useToast } from '../../components/ui/toast'
import { errorMessage } from '../../lib/errors'

export default function DoctorProfilePage() {
  const { t } = useTranslation()
  const { toast } = useToast()
  const profile = useMyDoctorProfile()
  const save = useUpdateDoctorProfile()
  const form = useDoctorProfileForm(profile.data)
  const { isDirty } = form.formState

  useEffect(() => {
    if (!isDirty) return
    const warn = (event: BeforeUnloadEvent) => event.preventDefault()
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [isDirty])

  async function onSubmit(values: DoctorProfileValues) {
    try {
      await save.mutateAsync(toProfileInput(values))
      toast(t('profile.saved'))
    } catch (error) {
      toast(errorMessage(error, t), 'error')
    }
  }

  if (profile.isPending) {
    return (
      <div className="page-gutter py-8" role="status">
        <span className="sr-only">{t('common.loading')}</span>
        <Skeleton className="h-10 w-64" />
        <Skeleton className="mt-6 h-96 max-w-2xl" />
      </div>
    )
  }
  if (profile.isError) {
    return (
      <div className="page-gutter py-8">
        <ErrorState error={profile.error} onRetry={() => void profile.refetch()} />
      </div>
    )
  }

  const status = profile.data.verification_status

  return (
    <div className="page-gutter py-6 md:py-8">
      <PageHeader title={t('profile.title')} actions={<VerificationBadge status={status} />} />
      <form
        onSubmit={(event) => void form.handleSubmit(onSubmit)(event)}
        noValidate
        className="flex max-w-2xl flex-col gap-6"
      >
        {status === 'approved' && <Banner tone="warning">{t('profile.reviewWarning')}</Banner>}
        {status === 'suspended' && (
          <Banner tone="warning">
            {t('profile.suspended')}{' '}
            <Link to="/doctor/verification" className="underline underline-offset-4">
              {t('nav.verification')}
            </Link>
          </Banner>
        )}
        <PracticeFields form={form} />
        <ClinicalFields form={form} />
        <div>
          <Button type="submit" loading={save.isPending} disabled={status === 'suspended'}>
            {t('profile.save')}
          </Button>
        </div>
      </form>
    </div>
  )
}
