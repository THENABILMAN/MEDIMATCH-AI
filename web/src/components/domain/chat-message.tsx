import { Sparkles } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { formatTime } from '../../lib/format'
import type { ChatMessage as ChatMessageType } from '../../types'
import { EmergencyNotice } from './emergency-notice'
import { RecommendationList } from './recommendation-list'

export function ChatMessage({ message }: { message: ChatMessageType }) {
  const { t, i18n } = useTranslation()
  const time = formatTime(message.created_at, i18n.language)

  if (message.sender === 'patient') {
    return (
      <article aria-label={t('chat.youSaid')} className="ml-auto max-w-[85%]">
        <p className="rounded-md border border-border bg-surface px-4 py-3 whitespace-pre-line">{message.content}</p>
        <p className="mt-1 text-right text-xs text-muted tabular">{time}</p>
      </article>
    )
  }

  if (message.metadata?.is_emergency) return <EmergencyNotice message={message.content} />

  const recommendations = message.metadata?.recommendations ?? []

  return (
    <article aria-label={t('chat.assistantSaid')} className="border-l-2 border-ai pl-4">
      <p className="flex items-center gap-1 text-xs font-medium text-ai">
        <Sparkles aria-hidden className="size-3.5" strokeWidth={1.75} />
        {t('chat.aiLabel')}
      </p>
      <p className="mt-1 whitespace-pre-line">{message.content.replaceAll('**', '')}</p>
      {recommendations.length > 0 && <RecommendationList recommendations={recommendations} />}
      <p className="mt-1 text-xs text-muted tabular">{time}</p>
    </article>
  )
}
