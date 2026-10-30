import React from 'react'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { DisclaimerBanner } from '../src/components/chat/DisclaimerBanner'
import { DoctorRecommendationCard } from '../src/components/chat/DoctorRecommendationCard'
import { EmergencyAlert } from '../src/components/chat/EmergencyAlert'
import type { DoctorRecommendation } from '../src/types'

describe('Chat Components', () => {
  it('renders DisclaimerBanner with prominent medical safety notice and 999 link', () => {
    render(<DisclaimerBanner />)

    expect(screen.getByTestId('disclaimer-banner')).toBeInTheDocument()
    expect(screen.getByText(/Medical Safety Notice:/i)).toBeInTheDocument()
    expect(screen.getByText(/999 \(National Emergency\)/i)).toBeInTheDocument()
  })

  it('renders EmergencyAlert with prominent emergency advice and CTA button', () => {
    render(
      <EmergencyAlert message="Severe chest pain detected. Seek immediate hospital care." />
    )

    expect(screen.getByTestId('emergency-alert')).toBeInTheDocument()
    expect(screen.getByText(/Immediate Medical Attention Required/i)).toBeInTheDocument()
    expect(screen.getByText(/Severe chest pain detected/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Call 999 Emergency Services/i })).toHaveAttribute(
      'href',
      'tel:999'
    )
  })

  it('renders DoctorRecommendationCard with score, specialties, clinic, fee, and booking link', () => {
    const mockDoctor: DoctorRecommendation = {
      doctor_id: 'd0000000-0000-0000-0000-000000000001',
      full_name: 'Dr. Sarah Khan',
      specialties: ['Neurology', 'General Medicine'],
      city: 'Dhaka',
      clinic_name: 'Square Hospital',
      consultation_fee: 1500,
      years_experience: 12,
      score: 0.94,
      match_explanation: 'Strong specialist match for persistent neurological migraines.',
      next_available_slot: '2026-11-05T10:00:00Z',
    }

    render(
      <MemoryRouter>
        <DoctorRecommendationCard doctor={mockDoctor} />
      </MemoryRouter>
    )

    expect(screen.getByTestId('recommendation-card')).toBeInTheDocument()
    expect(screen.getByText(/94% Clinical Match/i)).toBeInTheDocument()
    expect(screen.getByText('Dr. Sarah Khan')).toBeInTheDocument()
    expect(screen.getByText('Neurology')).toBeInTheDocument()
    expect(screen.getByText('৳1500 BDT')).toBeInTheDocument()
    expect(screen.getByText(/Square Hospital, Dhaka/i)).toBeInTheDocument()
    expect(
      screen.getByText(/"Strong specialist match for persistent neurological migraines."/i)
    ).toBeInTheDocument()

    const bookLink = screen.getByRole('link', { name: /View & Book Slot/i })
    expect(bookLink).toHaveAttribute('href', '/doctors/d0000000-0000-0000-0000-000000000001')
  })
})

