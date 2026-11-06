import { ArrowSquareOut, FileText } from '@phosphor-icons/react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../../api/client'
import { errorMessage } from '../../lib/errors'
import { formatDate } from '../../lib/format'
import type { DoctorCredential } from '../../types'
import { Button } from '../ui/button'
import { useToast } from '../ui/toast'

function fileName(path: string): string {
  return (path.split('/').pop() ?? path).replace(/^[0-9a-f-]{36}_/, '')
}

export function CredentialViewer({ credentials }: { credentials: DoctorCredential[] }) {
  const { t, i18n } = useTranslation()
  const { toast } = useToast()
  const [openingId, setOpeningId] = useState<string | null>(null)

  async function open(credential: DoctorCredential) {
    setOpeningId(credential.id)
    // Opened before the await so that mobile browsers don't treat it as a popup
    const tab = window.open('', '_blank')
    try {
      const { url } = await api.doctors.getCredentialUrl(credential.id)
      if (tab) {
        tab.opener = null
        tab.location.href = url
      } else {
        window.location.assign(url)
      }
    } catch (error) {
      tab?.close()
      toast(errorMessage(error, t), 'error')
    } finally {
      setOpeningId(null)
    }
  }

  return (
    <ul className="rounded-xl border border-border bg-surface">
      {credentials.map((credential) => (
        <li
          key={credential.id}
          className="flex items-center gap-3 border-b border-border p-3 last:border-b-0"
        >
          <FileText aria-hidden className="size-5 shrink-0 text-muted" />
          <div className="min-w-0 flex-1">
            <p className="body-2">
              {t(`credentials.type.${credential.document_type}`, { defaultValue: credential.document_type })}
            </p>
            <p className="truncate body-6 text-muted">
              {fileName(credential.file_path)} · {formatDate(credential.uploaded_at, i18n.language)}
            </p>
          </div>
          <Button
            variant="secondary"
            size="sm"
            loading={openingId === credential.id}
            onClick={() => void open(credential)}
            aria-label={t('credentials.openNamed', {
              name: t(`credentials.type.${credential.document_type}`, { defaultValue: credential.document_type }),
            })}
          >
            {openingId !== credential.id && <ArrowSquareOut aria-hidden className="size-4" />}
            {t('credentials.open')}
          </Button>
        </li>
      ))}
    </ul>
  )
}
