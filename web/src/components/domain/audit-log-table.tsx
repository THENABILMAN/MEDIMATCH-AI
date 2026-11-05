import { useTranslation } from 'react-i18next'
import { formatDateTime } from '../../lib/format'
import type { AuditLog } from '../../types'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table'

function metadataText(metadata: Record<string, unknown>): string {
  return Object.entries(metadata)
    .map(([key, value]) => `${key}: ${typeof value === 'object' ? JSON.stringify(value) : String(value)}`)
    .join(', ')
}

function readableAction(action: string): string {
  const words = action.toLowerCase().replaceAll('_', ' ')
  return words.charAt(0).toUpperCase() + words.slice(1)
}

export function AuditLogTable({ logs }: { logs: AuditLog[] }) {
  const { t, i18n } = useTranslation()
  return (
    <Table caption={t('audit.title')}>
      <TableHead>
        <tr>
          <TableHeader>{t('audit.when')}</TableHeader>
          <TableHeader>{t('audit.action')}</TableHeader>
          <TableHeader>{t('audit.target')}</TableHeader>
          <TableHeader>{t('audit.details')}</TableHeader>
        </tr>
      </TableHead>
      <TableBody>
        {logs.map((log) => (
          <TableRow key={log.id}>
            <TableCell className="whitespace-nowrap tabular">{formatDateTime(log.created_at, i18n.language)}</TableCell>
            <TableCell className="whitespace-nowrap font-medium">{readableAction(log.action)}</TableCell>
            <TableCell className="whitespace-nowrap text-muted">{log.target_type}</TableCell>
            <TableCell className="min-w-64 text-muted">{metadataText(log.metadata)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
