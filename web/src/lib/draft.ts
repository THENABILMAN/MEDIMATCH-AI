const KEY = 'medimatch-draft'

/** Keeps a first message for the chat screen. Symptoms stay out of the URL and last one tab. */
export function saveDraft(text: string): void {
  try {
    sessionStorage.setItem(KEY, text)
  } catch {
    // Storage can be blocked. The patient types the message again in chat.
  }
}

export function readDraft(): string {
  try {
    return sessionStorage.getItem(KEY) ?? ''
  } catch {
    return ''
  }
}

export function clearDraft(): void {
  try {
    sessionStorage.removeItem(KEY)
  } catch {
    // Nothing was stored
  }
}
