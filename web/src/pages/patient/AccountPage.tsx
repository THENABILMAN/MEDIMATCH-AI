import { zodResolver } from '@hookform/resolvers/zod'
import { useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { api } from '../../api/client'
import { keys } from '../../api/hooks'
import { PageHeader } from '../../components/layout/page-header'
import { Button } from '../../components/ui/button'
import { Switch } from '../../components/ui/choice'
import { ConfirmDialog } from '../../components/ui/dialog'
import { Field } from '../../components/ui/field'
import { Input } from '../../components/ui/input'
import { useToast } from '../../components/ui/toast'
import { useAuth } from '../../contexts/AuthContext'
import { errorMessage } from '../../lib/errors'

interface ProfileValues {
  full_name: string
  phone: string
}

function Section({ title, description, children }: { title: string; description?: string; children: React.ReactNode }) {
  return (
    <section className="grid gap-4 border-t border-border py-6 lg:grid-cols-12">
      <div className="lg:col-span-4">
        <h2 className="text-lg font-semibold">{title}</h2>
        {description && <p className="text-muted">{description}</p>}
      </div>
      <div className="min-w-0 lg:col-span-8">{children}</div>
    </section>
  )
}

export default function AccountPage() {
  const { t } = useTranslation()
  const { profile, role, refreshProfile, logout } = useAuth()
  const { toast } = useToast()
  const client = useQueryClient()
  const navigate = useNavigate()
  const [dialog, setDialog] = useState<'chat' | 'account' | null>(null)
  const [busy, setBusy] = useState(false)

  const schema = useMemo(
    () =>
      z.object({
        full_name: z.string().trim().min(2, t('auth.nameRequired')).max(150),
        phone: z.string().trim().max(25),
      }),
    [t]
  )

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ProfileValues>({
    resolver: zodResolver(schema),
    mode: 'onBlur',
    values: { full_name: profile?.full_name ?? '', phone: profile?.phone ?? '' },
  })

  async function saveProfile(values: ProfileValues) {
    try {
      await api.auth.updateMe(values)
      await refreshProfile()
      toast(t('account.saved'))
    } catch (error) {
      toast(errorMessage(error, t), 'error')
    }
  }

  async function setConsent(agreed: boolean) {
    setBusy(true)
    try {
      await api.auth.updateMe({ ai_consent: agreed })
      await refreshProfile()
      toast(t(agreed ? 'account.consentOn' : 'account.consentOff'))
    } catch (error) {
      toast(errorMessage(error, t), 'error')
    } finally {
      setBusy(false)
    }
  }

  async function deleteChat() {
    setBusy(true)
    try {
      await api.auth.deleteChatHistory()
      client.removeQueries({ queryKey: keys.conversations })
      setDialog(null)
      toast(t('account.chatDeleted'))
    } catch (error) {
      toast(errorMessage(error, t), 'error')
    } finally {
      setBusy(false)
    }
  }

  async function closeAccount() {
    setBusy(true)
    try {
      await api.auth.closeAccount()
      navigate('/')
      await logout()
      client.clear()
      toast(t('account.closed'))
    } catch (error) {
      toast(errorMessage(error, t), 'error')
      setBusy(false)
      setDialog(null)
    }
  }

  return (
    <div className="page-gutter py-6 md:py-8">
      <PageHeader title={t('account.title')} />

      <Section title={t('account.details')}>
        <form
          onSubmit={(event) => void handleSubmit(saveProfile)(event)}
          noValidate
          className="flex max-w-md flex-col gap-4"
        >
          <Field label={t('auth.email')} hint={t('account.emailHint')}>
            {(control) => <Input {...control} type="email" value={profile?.email ?? ''} readOnly className="bg-canvas" />}
          </Field>
          <Field label={t('auth.fullName')} error={errors.full_name?.message}>
            {(control) => <Input {...control} autoComplete="name" {...register('full_name')} />}
          </Field>
          <Field label={t('auth.phone')} optional={t('common.optional')} error={errors.phone?.message}>
            {(control) => <Input {...control} type="tel" autoComplete="tel" {...register('phone')} />}
          </Field>
          <div>
            <Button type="submit" loading={isSubmitting}>
              {t('account.save')}
            </Button>
          </div>
        </form>
      </Section>

      {role === 'patient' && (
        <>
          <Section title={t('account.privacy')} description={t('account.privacyBody')}>
            <div className="max-w-md">
              <Switch
                label={t('account.consentLabel')}
                description={t('account.consentHint')}
                checked={Boolean(profile?.ai_consent_at)}
                disabled={busy}
                onCheckedChange={(checked) => void setConsent(checked)}
              />
            </div>
          </Section>

          <Section title={t('account.yourData')}>
            <div className="flex max-w-xl flex-col gap-6">
              <div>
                <h3 className="font-semibold">{t('account.deleteChatTitle')}</h3>
                <p className="prose-width text-muted">{t('account.deleteChatBody')}</p>
                <Button variant="secondary" className="mt-2" onClick={() => setDialog('chat')}>
                  {t('account.deleteChat')}
                </Button>
              </div>
              <div>
                <h3 className="font-semibold">{t('account.closeTitle')}</h3>
                <p className="prose-width text-muted">{t('account.closeBody')}</p>
                <Button variant="danger" className="mt-2" onClick={() => setDialog('account')}>
                  {t('account.close')}
                </Button>
              </div>
            </div>
          </Section>
        </>
      )}

      <ConfirmDialog
        open={dialog === 'chat'}
        onOpenChange={(open) => !open && setDialog(null)}
        title={t('account.deleteChatConfirmTitle')}
        description={t('account.deleteChatConfirmBody')}
        confirmLabel={t('account.deleteChat')}
        cancelLabel={t('common.goBack')}
        loading={busy}
        onConfirm={() => void deleteChat()}
      />
      <ConfirmDialog
        open={dialog === 'account'}
        onOpenChange={(open) => !open && setDialog(null)}
        title={t('account.closeConfirmTitle')}
        description={t('account.closeConfirmBody')}
        confirmLabel={t('account.close')}
        cancelLabel={t('common.goBack')}
        loading={busy}
        onConfirm={() => void closeAccount()}
      />
    </div>
  )
}
