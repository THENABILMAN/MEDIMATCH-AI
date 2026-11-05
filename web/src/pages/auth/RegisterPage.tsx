import { zodResolver } from '@hookform/resolvers/zod'
import { useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { Link, Navigate } from 'react-router-dom'
import { z } from 'zod'
import { Banner } from '../../components/ui/banner'
import { Button } from '../../components/ui/button'
import { Field } from '../../components/ui/field'
import { Input } from '../../components/ui/input'
import { RadioGroup } from '../../components/ui/choice'
import { ROLE_HOME } from '../../components/common/ProtectedRoute'
import { useAuth } from '../../contexts/AuthContext'
import { errorMessage } from '../../lib/errors'
import { useUrlState } from '../../lib/url-state'

interface RegisterValues {
  full_name: string
  email: string
  phone: string
  password: string
}

export default function RegisterPage() {
  const { t } = useTranslation()
  const { registerPatient, registerDoctor, role } = useAuth()
  const { params, set } = useUrlState()
  const accountType = params.get('role') === 'doctor' ? 'doctor' : 'patient'
  const [failure, setFailure] = useState<string | null>(null)

  const schema = useMemo(
    () =>
      z.object({
        full_name: z.string().trim().min(2, t('auth.nameRequired')).max(150),
        email: z.email(t('auth.emailInvalid')),
        phone: z.string().trim().max(25),
        password: z.string().min(8, t('auth.passwordLength')),
      }),
    [t]
  )

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterValues>({ resolver: zodResolver(schema), mode: 'onBlur', defaultValues: { phone: '' } })

  if (role) return <Navigate to={role === 'doctor' ? '/doctor/onboarding' : ROLE_HOME[role]} replace />

  async function onSubmit(values: RegisterValues) {
    setFailure(null)
    const payload = { ...values, phone: values.phone || undefined }
    try {
      await (accountType === 'doctor' ? registerDoctor(payload) : registerPatient(payload))
    } catch (error) {
      setFailure(errorMessage(error, t))
    }
  }

  return (
    <div className="page-gutter py-8 md:py-16">
      <div className="mx-auto w-full max-w-md">
        <h1 className="font-serif text-2xl">{t('auth.registerTitle')}</h1>
        <form onSubmit={(event) => void handleSubmit(onSubmit)(event)} noValidate className="mt-6 flex flex-col gap-4">
          {failure && <Banner tone="warning">{failure}</Banner>}
          <RadioGroup
            aria-label={t('auth.accountType')}
            value={accountType}
            onValueChange={(value) => set({ role: value === 'doctor' ? 'doctor' : undefined }, { replace: true })}
            options={[
              { value: 'patient', label: t('auth.typePatient'), description: t('auth.typePatientHint') },
              { value: 'doctor', label: t('auth.typeDoctor'), description: t('auth.typeDoctorHint') },
            ]}
          />
          <Field label={t('auth.fullName')} error={errors.full_name?.message}>
            {(control) => <Input {...control} autoComplete="name" {...register('full_name')} />}
          </Field>
          <Field label={t('auth.email')} error={errors.email?.message}>
            {(control) => (
              <Input {...control} type="email" autoComplete="email" spellCheck={false} {...register('email')} />
            )}
          </Field>
          <Field label={t('auth.phone')} optional={t('common.optional')} error={errors.phone?.message}>
            {(control) => (
              <Input {...control} type="tel" autoComplete="tel" placeholder="01712 345678" {...register('phone')} />
            )}
          </Field>
          <Field label={t('auth.password')} hint={t('auth.passwordHint')} error={errors.password?.message}>
            {(control) => <Input {...control} type="password" autoComplete="new-password" {...register('password')} />}
          </Field>
          <Button type="submit" loading={isSubmitting}>
            {isSubmitting ? t('auth.creating') : t('nav.createAccount')}
          </Button>
        </form>
        <p className="mt-6 text-muted">
          {t('auth.haveAccount')}{' '}
          <Link to="/login" className="text-primary underline underline-offset-4">
            {t('nav.signIn')}
          </Link>
        </p>
      </div>
    </div>
  )
}
