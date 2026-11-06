import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { ErrorBoundary } from '../src/components/common/ErrorBoundary'
import { AIDisclaimer } from '../src/components/domain/ai-disclaimer'
import { ChatMessage } from '../src/components/domain/chat-message'
import { EmergencyNotice } from '../src/components/domain/emergency-notice'
import type { ChatMessage as ChatMessageType, DoctorRecommendation } from '../src/types'

// Same shape as DoctorRecommendation in backend/app/search/recommend.py
const doctor: DoctorRecommendation = {
  id: 'd1',
  user_id: 'u1',
  full_name: 'Dr. Sarah Khan',
  specialties: [{ id: 's1', name: 'Neurology', description: 'Brain and nerves' }],
  bio: null,
  qualifications: ['MBBS'],
  city: 'Dhaka',
  clinic_name: 'Square Hospital',
  consultation_fee: 1500,
  years_experience: 12,
  match_score: 94.4,
  available_slots_count: 3,
  soonest_slot: '2026-11-05T04:00:00Z',
  match_explanation: 'Specializes in Neurology in Dhaka.',
}

function message(overrides: Partial<ChatMessageType>): ChatMessageType {
  return {
    id: 'm1',
    conversation_id: 'c1',
    sender: 'assistant',
    content: 'Hello',
    created_at: '2026-11-05T04:00:00Z',
    ...overrides,
  }
}

function renderMessage(overrides: Partial<ChatMessageType>) {
  render(
    <MemoryRouter>
      <ChatMessage message={message(overrides)} />
    </MemoryRouter>
  )
}

describe('emergency messages', () => {
  const text = 'Please call 999 immediately.\nDo not wait.'

  it('shows the text exactly as received, with a tel link and no way to dismiss', () => {
    render(<EmergencyNotice message={text} />)
    const notice = within(screen.getByRole('alert'))
    expect(notice.getByText(/Please call 999/).textContent).toBe(text)
    expect(notice.getByRole('link', { name: /Call 999/ })).toHaveAttribute('href', 'tel:999')
    expect(notice.queryByRole('button')).not.toBeInTheDocument()
  })

  it('shows no doctors, even if the data contains some', () => {
    renderMessage({ content: text, metadata: { is_emergency: true, recommendations: [doctor] } })
    expect(screen.getByTestId('emergency-notice')).toBeInTheDocument()
    expect(screen.queryByText('Dr. Sarah Khan')).not.toBeInTheDocument()
  })

  it('shows self-harm as the calm notice, with the text unchanged and no doctors', () => {
    const crisis = 'Thank you for telling me.\n\nPlease call 999 now.'
    renderMessage({
      content: crisis,
      metadata: { is_emergency: true, safety_kind: 'self_harm', recommendations: [doctor] },
    })
    const notice = within(screen.getByTestId('crisis-notice'))
    expect(notice.getByText(/Thank you for telling me/).textContent).toBe(crisis)
    expect(notice.getByRole('link', { name: /Call 999/ })).toHaveAttribute('href', 'tel:999')
    expect(notice.queryByRole('button')).not.toBeInTheDocument()
    expect(screen.queryByTestId('emergency-notice')).not.toBeInTheDocument()
    expect(screen.queryByText('Dr. Sarah Khan')).not.toBeInTheDocument()
  })

  it('keeps the red alert for an older emergency with no kind saved', () => {
    renderMessage({ content: text, metadata: { is_emergency: true } })
    expect(screen.getByTestId('emergency-notice')).toBeInTheDocument()
  })
})

describe('chat messages', () => {
  it('labels assistant replies as written by AI', () => {
    renderMessage({ content: 'How long have you had this?' })
    expect(screen.getByText('Written by AI')).toBeInTheDocument()
  })

  it('does not label patient messages as AI', () => {
    renderMessage({ sender: 'patient', content: 'Headache' })
    expect(screen.queryByText('Written by AI')).not.toBeInTheDocument()
  })

  it('ranks recommendations with the reason, availability, fee and booking link', () => {
    renderMessage({ content: 'Your shortlist', metadata: { recommendations: [doctor] } })
    const item = within(screen.getByTestId('recommendation'))
    expect(item.getByText('Dr. Sarah Khan')).toBeInTheDocument()
    expect(item.getByText(/Specializes in Neurology/)).toBeInTheDocument()
    expect(item.getByText(/Soonest:.*৳1,500/)).toBeInTheDocument()
    expect(item.getByRole('link', { name: 'View and book' })).toHaveAttribute('href', '/doctors/d1')
  })
})

describe('safety notices', () => {
  it('states that the assistant is not medical advice', () => {
    render(<AIDisclaimer />)
    expect(screen.getByTestId('ai-disclaimer')).toHaveTextContent(/Not medical advice/)
  })

  it('keeps the emergency number visible when a page crashes', () => {
    const Broken = (): React.ReactNode => {
      throw new Error('render failure')
    }
    const silence = vi.spyOn(console, 'error').mockImplementation(() => undefined)
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => undefined)

    render(
      <ErrorBoundary>
        <Broken />
      </ErrorBoundary>
    )

    expect(screen.getByText(/call 999 now/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Reload page' })).toBeInTheDocument()
    silence.mockRestore()
    warn.mockRestore()
  })
})
