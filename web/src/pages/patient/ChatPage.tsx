import { useQueryClient } from '@tanstack/react-query'
import { History, Plus } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../../api/client'
import { keys, useConversation, useConversations } from '../../api/hooks'
import { AIDisclaimer } from '../../components/domain/ai-disclaimer'
import { ChatComposer } from '../../components/domain/chat-composer'
import { ChatMessage } from '../../components/domain/chat-message'
import { Banner } from '../../components/ui/banner'
import { Button } from '../../components/ui/button'
import { ErrorState } from '../../components/ui/query-state'
import { Sheet } from '../../components/ui/sheet'
import { Skeleton } from '../../components/ui/skeleton'
import { useAuth } from '../../contexts/AuthContext'
import { EMERGENCY_NUMBER } from '../../lib/constants'
import { errorMessage } from '../../lib/errors'
import { formatDateTime } from '../../lib/format'
import type { ChatMessage as ChatMessageType, ConversationDetail } from '../../types'

function ConsentPanel() {
  const { t } = useTranslation()
  const { refreshProfile } = useAuth()
  const [saving, setSaving] = useState(false)
  const [failure, setFailure] = useState<string | null>(null)

  async function agree() {
    setSaving(true)
    setFailure(null)
    try {
      await api.auth.updateMe({ ai_consent: true })
      await refreshProfile()
    } catch (error) {
      setFailure(errorMessage(error, t))
      setSaving(false)
    }
  }

  return (
    <div className="page-gutter py-8">
      <div className="mx-auto w-full max-w-[720px]">
        <h1 className="font-serif text-2xl">{t('chat.consentTitle')}</h1>
        <p className="prose-width mt-3 text-muted">{t('chat.consentBody')}</p>
        <p className="prose-width mt-3 text-muted">{t('chat.consentPrivacy')}</p>
        {failure && (
          <Banner tone="warning" className="mt-4">
            {failure}
          </Banner>
        )}
        <div className="mt-6 flex flex-wrap gap-2">
          <Button loading={saving} onClick={() => void agree()}>
            {t('chat.consentAgree')}
          </Button>
          <Button asChild variant="secondary">
            <Link to="/doctors">{t('home.browse')}</Link>
          </Button>
        </div>
        <p className="prose-width mt-6 text-sm text-muted">{t('home.emergency', { number: EMERGENCY_NUMBER })}</p>
      </div>
    </div>
  )
}

function MessagesSkeleton() {
  return (
    <div className="flex flex-col gap-4" aria-hidden>
      <Skeleton className="h-20 w-4/5" />
      <Skeleton className="ml-auto h-12 w-3/5" />
      <Skeleton className="h-16 w-4/5" />
    </div>
  )
}

/** Finds the conversation to open, creating the first one. */
function useOpenConversation(conversationId: string | undefined, enabled: boolean) {
  const navigate = useNavigate()
  const client = useQueryClient()
  const conversations = useConversations(enabled)
  const creating = useRef(false)
  const [createError, setCreateError] = useState<unknown>(null)

  const startNew = useCallback(async () => {
    if (creating.current) return
    creating.current = true
    setCreateError(null)
    try {
      const created = await api.chat.createConversation('Symptom Consultation')
      await client.invalidateQueries({ queryKey: keys.conversations })
      navigate(`/chat/${created.id}`, { replace: conversationId === undefined })
    } catch (error) {
      setCreateError(error)
    } finally {
      creating.current = false
    }
  }, [client, conversationId, navigate])

  useEffect(() => {
    if (!enabled || conversationId || !conversations.data) return
    if (conversations.data.length > 0) navigate(`/chat/${conversations.data[0].id}`, { replace: true })
    else void startNew()
  }, [conversationId, conversations.data, enabled, navigate, startNew])

  return { conversations, startNew, createError }
}

export default function ChatPage() {
  const { t, i18n } = useTranslation()
  const { conversationId } = useParams()
  const { profile } = useAuth()
  const client = useQueryClient()
  const consented = Boolean(profile?.ai_consent_at)

  const { conversations, startNew, createError } = useOpenConversation(conversationId, consented)
  const conversation = useConversation(consented ? conversationId : undefined)

  const [sending, setSending] = useState(false)
  const [followupField, setFollowupField] = useState<string | null>(null)
  const [unsent, setUnsent] = useState<{ text: string; reason: string } | null>(null)
  const [historyOpen, setHistoryOpen] = useState(false)
  const endRef = useRef<HTMLDivElement>(null)

  const messages = conversation.data?.messages
  useEffect(() => {
    endRef.current?.scrollIntoView({ block: 'end' })
  }, [messages, sending, unsent])

  const append = useCallback(
    (id: string, message: ChatMessageType) => {
      client.setQueryData<ConversationDetail>(keys.conversation(id), (current) =>
        current ? { ...current, messages: [...current.messages, message] } : current
      )
    },
    [client]
  )

  async function send(text: string, alreadyShown = false) {
    if (!conversationId) return
    setUnsent(null)
    setFollowupField(null)
    if (!alreadyShown) {
      append(conversationId, {
        id: `local-${Date.now()}`,
        conversation_id: conversationId,
        sender: 'patient',
        content: text,
        created_at: new Date().toISOString(),
      })
    }

    setSending(true)
    try {
      const reply = await api.chat.sendMessage(conversationId, text)
      append(conversationId, {
        id: `reply-${Date.now()}`,
        conversation_id: conversationId,
        sender: 'assistant',
        content: reply.assistant_reply,
        created_at: new Date().toISOString(),
        metadata: { is_emergency: reply.is_emergency, recommendations: reply.recommendations ?? [] },
      })
      setFollowupField(reply.followup_field ?? null)
    } catch (error) {
      setUnsent({ text, reason: errorMessage(error, t) })
    } finally {
      setSending(false)
    }
  }

  if (!consented) return <ConsentPanel />

  const loadError = createError ?? conversation.error ?? conversations.error

  return (
    <div className="flex h-[calc(100dvh-var(--header-height)-1px)] flex-col">
      <div className="border-b border-border bg-surface">
        <div className="mx-auto flex w-full max-w-[752px] flex-col gap-2 px-4 py-3">
          <div className="flex items-center justify-between gap-2">
            <h1 className="font-serif text-lg whitespace-nowrap md:text-xl">{t('chat.title')}</h1>
            <div className="flex gap-2">
              <Button variant="ghost" size="sm" onClick={() => setHistoryOpen(true)}>
                <History aria-hidden className="hidden size-4 md:block" strokeWidth={1.75} />
                {t('chat.history')}
              </Button>
              <Button variant="secondary" size="sm" onClick={() => void startNew()}>
                <Plus aria-hidden className="hidden size-4 md:block" strokeWidth={1.75} />
                {t('chat.new')}
              </Button>
            </div>
          </div>
          <AIDisclaimer />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto overscroll-contain">
        <div
          role="log"
          aria-label={t('chat.conversation')}
          aria-live="polite"
          aria-busy={sending}
          className="mx-auto flex w-full max-w-[752px] flex-col gap-6 px-4 py-6"
        >
          {loadError ? (
            <ErrorState
              error={loadError}
              onRetry={() => {
                void conversations.refetch()
                void conversation.refetch()
              }}
            />
          ) : messages ? (
            messages.map((message) => <ChatMessage key={message.id} message={message} />)
          ) : (
            <MessagesSkeleton />
          )}

          {sending && (
            <p role="status" className="border-l-2 border-ai pl-4 text-sm text-muted">
              {t('chat.thinking')}
            </p>
          )}

          {unsent && (
            <Banner
              tone="warning"
              title={t('chat.notSent')}
              action={
                <Button variant="secondary" onClick={() => void send(unsent.text, true)}>
                  {t('common.tryAgain')}
                </Button>
              }
            >
              <p>{unsent.reason}</p>
              <p className="mt-1">{t('chat.notSentEmergency', { number: EMERGENCY_NUMBER })}</p>
            </Banner>
          )}
          <div ref={endRef} />
        </div>
      </div>

      <div className="border-t border-border bg-surface pb-[env(safe-area-inset-bottom)]">
        <div className="mx-auto w-full max-w-[752px] px-4 py-3">
          <ChatComposer
            onSend={(text) => void send(text)}
            sending={sending || !conversation.data}
            followupField={followupField}
          />
        </div>
      </div>

      <Sheet open={historyOpen} onOpenChange={setHistoryOpen} title={t('chat.history')}>
        {conversations.data?.length ? (
          <ul className="flex flex-col gap-1">
            {conversations.data.map((item) => (
              <li key={item.id}>
                <Link
                  to={`/chat/${item.id}`}
                  onClick={() => setHistoryOpen(false)}
                  aria-current={item.id === conversationId ? 'page' : undefined}
                  className="block rounded-sm p-3 hover:bg-canvas aria-[current=page]:bg-primary-tint"
                >
                  <span className="block font-medium">{item.title}</span>
                  <span className="block text-sm text-muted tabular">
                    {formatDateTime(item.created_at, i18n.language)}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-muted">{t('chat.historyEmpty')}</p>
        )}
      </Sheet>
    </div>
  )
}
