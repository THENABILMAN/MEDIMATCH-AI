import { useTranslation } from 'react-i18next'
import { formatTime } from '../../lib/format'
import type { ChatMessage as ChatMessageType } from '../../types'
import { CrisisNotice } from './crisis-notice'
import { EmergencyNotice } from './emergency-notice'
import { RecommendationList } from './recommendation-list'

export function ChatMessage({ message }: { message: ChatMessageType }) {
  const { t, i18n } = useTranslation()
  const time = formatTime(message.created_at, i18n.language)

  if (message.sender === 'patient') {
    return (
      <article aria-label={t('chat.youSaid')} className="ml-auto max-w-[85%]">
        <p className="rounded-xl bg-surface px-4 py-3 whitespace-pre-line">{message.content}</p>
        <p className="mt-1 text-right caption-5 text-muted tabular">{time}</p>
      </article>
    )
  }

  if (message.metadata?.safety_kind === 'self_harm') return <CrisisNotice message={message.content} />
  if (message.metadata?.is_emergency) return <EmergencyNotice message={message.content} />

  const recommendations = message.metadata?.recommendations ?? []

  return (
    <article aria-label={t('chat.assistantSaid')}>
      <div className="rounded-xl bg-ai-tint px-4 py-3">
        <p className="caption-4 text-ai">{t('chat.aiLabel')}</p>
        <p className="mt-1 whitespace-pre-line">{message.content.replaceAll('**', '')}</p>
      </div>
      {recommendations.length > 0 && <RecommendationList recommendations={recommendations} />}
      <p className="mt-1 caption-5 text-muted tabular">{time}</p>
    </article>
  )
}
