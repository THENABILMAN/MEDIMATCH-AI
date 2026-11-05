import { useTranslation } from 'react-i18next'
import { useMyCredentials } from '../../api/hooks'
import { CredentialUploader } from '../../components/domain/credential-uploader'
import { CredentialViewer } from '../../components/domain/credential-viewer'
import { PageHeader } from '../../components/layout/page-header'
import { EmptyState } from '../../components/ui/empty-state'
import { ErrorState } from '../../components/ui/query-state'
import { Skeleton } from '../../components/ui/skeleton'

export default function CredentialsPage() {
  const { t } = useTranslation()
  const credentials = useMyCredentials()

  return (
    <div className="page-gutter py-6 md:py-8">
      <PageHeader title={t('credentials.title')} description={t('credentials.description')} />
      <div className="grid gap-6 lg:grid-cols-12">
        <div className="lg:col-span-5">
          <h2 className="mb-2 font-serif text-xl">{t('credentials.uploadTitle')}</h2>
          <CredentialUploader />
        </div>
        <div className="min-w-0 lg:col-span-7">
          <h2 className="mb-2 font-serif text-xl">{t('credentials.uploadedTitle')}</h2>
          {credentials.isPending ? (
            <Skeleton className="h-32" />
          ) : credentials.isError ? (
            <ErrorState error={credentials.error} onRetry={() => void credentials.refetch()} />
          ) : credentials.data.length === 0 ? (
            <EmptyState illustration="document" title={t('credentials.emptyTitle')} description={t('credentials.emptyBody')} />
          ) : (
            <CredentialViewer credentials={credentials.data} />
          )}
        </div>
      </div>
    </div>
  )
}
