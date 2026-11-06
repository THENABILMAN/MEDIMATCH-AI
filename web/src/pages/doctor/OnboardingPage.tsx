import { Check } from '@phosphor-icons/react'
import type { MouseEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { useMyCredentials, useMyDoctorProfile, useUpdateDoctorProfile } from '../../api/hooks'
import { CredentialUploader } from '../../components/domain/credential-uploader'
import { CredentialViewer } from '../../components/domain/credential-viewer'
import {
  ClinicalFields,
  CLINICAL_FIELDS,
  PRACTICE_FIELDS,
  PracticeFields,
  toProfileInput,
  useDoctorProfileForm,
} from '../../components/domain/doctor-profile-form'
import { PageHeader } from '../../components/layout/page-header'
import { Banner } from '../../components/ui/banner'
import { Button } from '../../components/ui/button'
import { ErrorState } from '../../components/ui/query-state'
import { Skeleton } from '../../components/ui/skeleton'
import { useToast } from '../../components/ui/toast'
import { errorMessage } from '../../lib/errors'
import { cn } from '../../lib/cn'
import { useUrlState } from '../../lib/url-state'
import type { DoctorProfile } from '../../types'

const STEPS = ['practice', 'clinical', 'documents'] as const
type Step = (typeof STEPS)[number]

function firstIncompleteStep(profile: DoctorProfile): Step {
  if (!profile.clinic_name || profile.consultation_fee <= 0) return 'practice'
  if (profile.specialties.length === 0 || !profile.bio) return 'clinical'
  return 'documents'
}

/** Leaving a field clears its error and moves the button, so a click could land on nothing. */
function keepFocus(event: MouseEvent) {
  event.preventDefault()
}

export default function OnboardingPage() {
  const { t } = useTranslation()
  const { toast } = useToast()
  const navigate = useNavigate()
  const { params, set } = useUrlState()
  const profile = useMyDoctorProfile()
  const credentials = useMyCredentials()
  const save = useUpdateDoctorProfile()
  const form = useDoctorProfileForm(profile.data)

  if (profile.isPending || credentials.isPending) {
    return (
      <div className="page-gutter py-8" role="status">
        <span className="sr-only">{t('common.loading')}</span>
        <Skeleton className="h-10 w-64" />
        <Skeleton className="mt-6 h-64 max-w-2xl" />
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

  const documents = credentials.data ?? []
  const requested = params.get('step') as Step | null
  const step = requested && STEPS.includes(requested) ? requested : firstIncompleteStep(profile.data)
  const index = STEPS.indexOf(step)

  async function saveAndContinue(nextStep: Step) {
    const fields = step === 'practice' ? PRACTICE_FIELDS : CLINICAL_FIELDS
    const valid = await form.trigger([...fields], { shouldFocus: true })
    if (!valid) return

    // The other step's fields may still be blank, so keep their saved values
    const values = form.getValues()
    const saved = profile.data
    try {
      await save.mutateAsync(
        toProfileInput({
          ...values,
          clinic_name: values.clinic_name || saved?.clinic_name || '',
          bio: values.bio || saved?.bio || '',
        })
      )
      toast(t('onboarding.saved'))
      set({ step: nextStep })
    } catch (error) {
      toast(errorMessage(error, t), 'error')
    }
  }

  return (
    <div className="page-gutter py-6 md:py-8">
      <PageHeader title={t('onboarding.title')} description={t('onboarding.description')} />

      <ol className="mb-8 grid gap-2 md:grid-cols-3 md:gap-4">
        {STEPS.map((item, position) => (
          <li key={item} aria-current={item === step ? 'step' : undefined} className={cn('flex items-center gap-3 border-t-2 pt-3', position <= index ? 'border-primary' : 'border-border')}>
            <span
              className={cn(
                'flex size-8 items-center justify-center rounded-full border title-2 tabular',
                position < index && 'border-primary bg-primary text-white',
                position === index && 'border-primary text-primary-hover',
                position > index && 'border-control text-muted'
              )}
            >
              {position < index ? <Check aria-hidden className="size-3.5" /> : position + 1}
            </span>
            <span className={cn(position === index ? 'body-2' : 'text-muted')}>{t(`onboarding.step.${item}`)}</span>
          </li>
        ))}
      </ol>

      <div className="max-w-2xl">
        {step === 'practice' && <PracticeFields form={form} />}
        {step === 'clinical' && <ClinicalFields form={form} />}
        {step === 'documents' && (
          <div className="flex flex-col gap-4">
            <p className="prose-width text-muted">{t('onboarding.documentsBody')}</p>
            <CredentialUploader />
            {documents.length > 0 && <CredentialViewer credentials={documents} />}
          </div>
        )}

        <div className="mt-6 flex flex-wrap gap-2">
          {index > 0 && (
            <Button variant="secondary" onClick={() => set({ step: STEPS[index - 1] })}>
              {t('common.back')}
            </Button>
          )}
          {step === 'documents' ? (
            documents.length > 0 ? (
              <Button onClick={() => navigate('/doctor/verification')}>{t('onboarding.finish')}</Button>
            ) : (
              <Banner className="w-full">{t('onboarding.documentsNeeded')}</Banner>
            )
          ) : (
            <Button loading={save.isPending} onMouseDown={keepFocus} onClick={() => void saveAndContinue(STEPS[index + 1])}>
              {t('onboarding.saveContinue')}
            </Button>
          )}
          <Button asChild variant="ghost">
            <Link to="/doctor/verification">{t('onboarding.later')}</Link>
          </Button>
        </div>
      </div>
    </div>
  )
}
