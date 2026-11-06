import { zodResolver } from '@hookform/resolvers/zod'
import { useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { Link, Navigate, useLocation } from 'react-router-dom'
import { z } from 'zod'
import { ROLE_HOME } from '../../components/common/ProtectedRoute'
import { AuthFrame } from '../../components/layout/auth-frame'
import { Banner } from '../../components/ui/banner'
import { Button } from '../../components/ui/button'
import { Field } from '../../components/ui/field'
import { Input } from '../../components/ui/input'
import { useAuth } from '../../contexts/AuthContext'

interface LoginValues {
  email: string
  password: string
}

interface LocationState {
  from?: { pathname: string; search?: string }
}

const DEMO_ACCOUNTS = [
  ['Patient', 'patient@medimatch.test', 'Patient123!Safe'],
  ['Doctor', 'doctor@medimatch.test', 'Doctor123!Safe'],
  ['Admin', 'admin@medimatch.test', 'Admin123!Safe'],
] as const

export default function LoginPage() {
  const { t } = useTranslation()
  const { login, role } = useAuth()
  const location = useLocation()
  const [failed, setFailed] = useState(false)

  const schema = useMemo(
    () =>
      z.object({
        email: z.email(t('auth.emailInvalid')),
        password: z.string().min(1, t('auth.passwordRequired')),
      }),
    [t]
  )

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<LoginValues>({ resolver: zodResolver(schema), mode: 'onTouched' })

  if (role) {
    const from = (location.state as LocationState | null)?.from
    return <Navigate to={from ? `${from.pathname}${from.search ?? ''}` : ROLE_HOME[role]} replace />
  }

  async function onSubmit(values: LoginValues) {
    setFailed(false)
    try {
      await login(values.email, values.password)
    } catch {
      setFailed(true)
    }
  }

  return (
    <AuthFrame>
      <h1 className="heading-3">{t('auth.signInTitle')}</h1>
      <form onSubmit={(event) => void handleSubmit(onSubmit)(event)} noValidate className="mt-6 flex flex-col gap-4">
        {failed && <Banner tone="warning">{t('auth.signInFailed')}</Banner>}
        <Field label={t('auth.email')} error={errors.email?.message}>
          {(control) => (
            <Input {...control} type="email" autoComplete="email" spellCheck={false} {...register('email')} />
          )}
        </Field>
        <Field label={t('auth.password')} error={errors.password?.message}>
          {(control) => (
            <Input {...control} type="password" autoComplete="current-password" {...register('password')} />
          )}
        </Field>
        <Button type="submit" loading={isSubmitting}>
          {isSubmitting ? t('auth.signingIn') : t('nav.signIn')}
        </Button>
      </form>
      <p className="mt-6 text-muted">
        {t('auth.noAccount')}{' '}
        <Link to="/register" className="text-primary underline underline-offset-4">
          {t('nav.createAccount')}
        </Link>
      </p>

      {import.meta.env.DEV && (
        <div className="mt-8 flex flex-wrap items-center gap-2 border-t border-border pt-4">
          <span className="body-6 text-muted">{t('auth.demoAccounts')}</span>
          {DEMO_ACCOUNTS.map(([label, email, password]) => (
            <Button
              key={label}
              variant="secondary"
              size="sm"
              onClick={() => {
                setValue('email', email)
                setValue('password', password)
              }}
            >
              {label}
            </Button>
          ))}
        </div>
      )}
    </AuthFrame>
  )
}
