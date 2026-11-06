import { Clock, SealCheck, ShieldWarning, XCircle } from '@phosphor-icons/react'
import { useTranslation } from 'react-i18next'
import type { VerificationStatus } from '../../types'
import { Badge, type BadgeProps } from '../ui/badge'

const DISPLAY: Record<VerificationStatus, { tone: BadgeProps['tone']; Icon: typeof Clock }> = {
  approved: { tone: 'success', Icon: SealCheck },
  pending: { tone: 'warning', Icon: Clock },
  rejected: { tone: 'neutral', Icon: XCircle },
  suspended: { tone: 'danger', Icon: ShieldWarning },
}

export function VerificationBadge({ status }: { status: VerificationStatus }) {
  const { t } = useTranslation()
  const { tone, Icon } = DISPLAY[status]
  return (
    <Badge tone={tone}>
      <Icon aria-hidden className="size-3.5" />
      {t(`verification.status.${status}`)}
    </Badge>
  )
}
