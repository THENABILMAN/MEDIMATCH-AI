import { SendHorizontal } from 'lucide-react'
import { useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '../ui/button'
import { Textarea } from '../ui/input'

const SUGGESTIONS: Record<string, string[]> = {
  duration: ['chat.suggest.today', 'chat.suggest.fewDays', 'chat.suggest.week', 'chat.suggest.weeks'],
  location: ['chat.suggest.dhaka', 'chat.suggest.chattogram', 'chat.suggest.sylhet'],
  severity: ['chat.suggest.mild', 'chat.suggest.moderate', 'chat.suggest.severe'],
}

interface ChatComposerProps {
  onSend: (text: string) => void
  sending: boolean
  followupField?: string | null
  initialText?: string
}

export function ChatComposer({ onSend, sending, followupField, initialText = '' }: ChatComposerProps) {
  const { t } = useTranslation()
  const [text, setText] = useState(initialText)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const suggestions = followupField ? (SUGGESTIONS[followupField] ?? []) : []

  function submit(value: string) {
    const trimmed = value.trim()
    if (!trimmed || sending) return
    onSend(trimmed)
    setText('')
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault()
    submit(text)
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault()
      submit(text)
    }
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-2">
      {suggestions.length > 0 && (
        <div role="group" aria-label={t('chat.suggestedAnswers')} className="flex flex-wrap gap-2">
          {suggestions.map((key) => (
            <Button key={key} variant="secondary" size="sm" disabled={sending} onClick={() => submit(t(key))}>
              {t(key)}
            </Button>
          ))}
        </div>
      )}
      <div className="flex items-end gap-2">
        <label htmlFor="chat-input" className="sr-only">
          {t('chat.inputLabel')}
        </label>
        <Textarea
          id="chat-input"
          ref={inputRef}
          rows={1}
          value={text}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={onKeyDown}
          placeholder={t('chat.inputPlaceholder')}
          className="field-sizing-content max-h-32 min-h-11 flex-1 resize-none"
          autoComplete="off"
        />
        <Button type="submit" loading={sending} className="h-11 md:h-11">
          {!sending && <SendHorizontal aria-hidden className="size-4" strokeWidth={1.75} />}
          {t('chat.send')}
        </Button>
      </div>
    </form>
  )
}
