import { PaperPlaneRight } from '@phosphor-icons/react'
import { useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '../ui/button'
import { Textarea } from '../ui/input'

const SUGGESTIONS: Record<string, string[]> = {
  duration: ['chat.suggest.today', 'chat.suggest.fewDays', 'chat.suggest.week', 'chat.suggest.weeks'],
  location: ['chat.suggest.dhaka', 'chat.suggest.chattogram', 'chat.suggest.sylhet'],
  severity: ['chat.suggest.mild', 'chat.suggest.moderate', 'chat.suggest.severe'],
}

// The backend's fixed labels, in backend/app/ai/graph.py
const ESCAPE_LABELS = ['Show me doctors now', 'এখনই ডাক্তার দেখান', 'Ekhon doctor dekhan']

interface ChatComposerProps {
  onSend: (text: string) => void
  sending: boolean
  followupField?: string | null
  /** Answers the assistant offered for its last question. They replace the fixed suggestions. */
  chips?: { label: string }[]
  showDoctorsNow?: boolean
  initialText?: string
}

export function ChatComposer({
  onSend,
  sending,
  followupField,
  chips = [],
  showDoctorsNow = false,
  initialText = '',
}: ChatComposerProps) {
  const { t } = useTranslation()
  const [text, setText] = useState(initialText)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const fallback = followupField ? (SUGGESTIONS[followupField] ?? []) : []
  const suggestions = chips.length > 0 ? chips.map((chip) => chip.label) : fallback.map((key) => t(key))
  const showDoctors = t('chat.showDoctors')
  // The assistant offers this itself in some turns, in the patient's language
  const escapeOffered = chips.some((chip) => ESCAPE_LABELS.includes(chip.label))

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
      {(suggestions.length > 0 || (showDoctorsNow && !escapeOffered)) && (
        <div role="group" aria-label={t('chat.suggestedAnswers')} className="flex flex-wrap gap-2">
          {suggestions.map((label) => (
            <Button key={label} variant="secondary" size="sm" disabled={sending} onClick={() => submit(label)}>
              {label}
            </Button>
          ))}
          {showDoctorsNow && !escapeOffered && (
            <Button variant="ghost" size="sm" disabled={sending} onClick={() => submit(showDoctors)}>
              {showDoctors}
            </Button>
          )}
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
          {!sending && <PaperPlaneRight aria-hidden className="size-4" />}
          {t('chat.send')}
        </Button>
      </div>
    </form>
  )
}
