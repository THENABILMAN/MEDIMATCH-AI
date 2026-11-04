import { useQueryClient } from '@tanstack/react-query'
import { useRef, useState, type ChangeEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { uploadCredential } from '../../api/client'
import { keys } from '../../api/hooks'
import { errorMessage } from '../../lib/errors'
import { Banner } from '../ui/banner'
import { Button } from '../ui/button'
import { Field } from '../ui/field'
import { Select } from '../ui/select'
import { useToast } from '../ui/toast'

const ACCEPTED_TYPES = ['application/pdf', 'image/png', 'image/jpeg', 'image/webp']
const MAX_BYTES = 10 * 1024 * 1024
export const DOCUMENT_TYPES = ['bmdc_license', 'degree_certificate', 'nid_passport'] as const

export function CredentialUploader() {
  const { t } = useTranslation()
  const { toast } = useToast()
  const client = useQueryClient()
  const inputRef = useRef<HTMLInputElement>(null)
  const [documentType, setDocumentType] = useState<string>(DOCUMENT_TYPES[0])
  const [problem, setProblem] = useState<string | null>(null)
  const [progress, setProgress] = useState<number | null>(null)

  async function onFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return

    if (!ACCEPTED_TYPES.includes(file.type)) return setProblem(t('credentials.wrongType'))
    if (file.size > MAX_BYTES) return setProblem(t('credentials.tooLarge'))

    setProblem(null)
    setProgress(0)
    try {
      await uploadCredential(file, documentType, setProgress)
      await client.invalidateQueries({ queryKey: keys.myCredentials })
      toast(t('credentials.uploaded'))
    } catch (error) {
      setProblem(errorMessage(error, t))
    } finally {
      setProgress(null)
    }
  }

  return (
    <div className="flex flex-col gap-3 rounded-md border border-border bg-surface p-4">
      <Field label={t('credentials.documentType')}>
        {(control) => (
          <Select
            id={control.id}
            value={documentType}
            onValueChange={setDocumentType}
            disabled={progress !== null}
            options={DOCUMENT_TYPES.map((value) => ({ value, label: t(`credentials.type.${value}`) }))}
          />
        )}
      </Field>
      <input
        ref={inputRef}
        type="file"
        aria-label={t('credentials.chooseFile')}
        accept={ACCEPTED_TYPES.join(',')}
        onChange={(event) => void onFile(event)}
        className="sr-only"
        tabIndex={-1}
      />
      <div>
        <Button variant="secondary" loading={progress !== null} onClick={() => inputRef.current?.click()}>
          {t('credentials.chooseFile')}
        </Button>
        <p className="mt-1 text-sm text-muted">{t('credentials.requirements')}</p>
      </div>
      {progress !== null && (
        <div>
          <p className="text-sm tabular" aria-live="polite">
            {t('credentials.uploading', { percent: progress })}
          </p>
          <progress value={progress} max={100} aria-label={t('credentials.progress')} className="mt-1 h-1 w-full accent-(--primary)" />
        </div>
      )}
      {problem && <Banner tone="warning">{problem}</Banner>}
    </div>
  )
}
