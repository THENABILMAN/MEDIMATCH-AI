import React from 'react'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../src/api/client'
import * as AuthContextModule from '../src/contexts/AuthContext'
import { DoctorDetailPage } from '../src/pages/patient/DoctorDetailPage'

describe('DoctorDetailPage Booking Flow', () => {
  const mockDoctor = {
    id: 'd1111111-1111-1111-1111-111111111111',
    user_id: 'u1111111-1111-1111-1111-111111111111',
    full_name: 'Dr. Rafiqul Islam',
    bio: 'Senior Neurologist with extensive clinical experience.',
    qualifications: ['MBBS', 'FCPS'],
    years_experience: 15,
    consultation_fee: 1800,
    clinic_name: 'Apollo Hospital',
    city: 'Dhaka',
    verification_status: 'approved' as const,
    specialties: [{ id: 's1', name: 'Neurology' }],
  }

  const mockSlots = [
    {
      id: 'slot-101',
      doctor_id: mockDoctor.id,
      start_time: '2026-11-10T10:00:00Z',
      end_time: '2026-11-10T10:30:00Z',
      is_booked: false,
    },
    {
      id: 'slot-102',
      doctor_id: mockDoctor.id,
      start_time: '2026-11-11T14:00:00Z',
      end_time: '2026-11-11T14:30:00Z',
      is_booked: false,
    },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
      user: { id: 'patient-456' } as any,
      profile: { id: 'patient-456', role: 'patient', full_name: 'Alice Patient' },
      role: 'patient',
      session: {} as any,
      isLoading: false,
      login: vi.fn(),
      registerPatient: vi.fn(),
      registerDoctor: vi.fn(),
      logout: vi.fn(),
      refreshProfile: vi.fn(),
    })

    vi.spyOn(api.doctors, 'getById').mockResolvedValue(mockDoctor)
    vi.spyOn(api.doctors, 'getPublicSlots').mockResolvedValue(mockSlots)
  })

  it('renders doctor details and allows selecting and booking an appointment slot', async () => {
    const bookSpy = vi.spyOn(api.appointments, 'book').mockResolvedValue({
      id: 'app-999',
      patient_id: 'patient-456',
      doctor_id: mockDoctor.id,
      slot_id: 'slot-101',
      status: 'booked',
      created_at: new Date().toISOString(),
      start_time: '2026-11-10T10:00:00Z',
      end_time: '2026-11-10T10:30:00Z',
    })

    render(
      <MemoryRouter initialEntries={[`/doctors/${mockDoctor.id}`]}>
        <Routes>
          <Route path="/doctors/:id" element={<DoctorDetailPage />} />
        </Routes>
      </MemoryRouter>
    )

    // 1. Wait for doctor details to load
    await waitFor(() => {
      expect(screen.getByText('Dr. Rafiqul Islam')).toBeInTheDocument()
    })

    expect(screen.getByText('৳1800 BDT')).toBeInTheDocument()
    expect(screen.getByText(/15 Years/i)).toBeInTheDocument()
    expect(screen.getByText('Available Appointment Slots')).toBeInTheDocument()

    // 2. Select slot-101
    const slotButtons = screen.getAllByRole('button')
    const slot1Button = slotButtons.find((btn) => btn.textContent?.includes('10:00') || btn.textContent?.includes('Nov 10') || btn.textContent?.includes('10'))
    expect(slot1Button).toBeDefined()

    if (slot1Button) {
      fireEvent.click(slot1Button)
    }

    // 3. Confirm booking button should now be enabled
    const confirmButton = screen.getByRole('button', { name: /Confirm Appointment Booking/i })
    expect(confirmButton).toBeEnabled()

    fireEvent.click(confirmButton)

    // 4. Assert booking API called with slot-101
    await waitFor(() => {
      expect(bookSpy).toHaveBeenCalledWith('slot-101')
      expect(screen.getByText(/Booking Confirmed!/i)).toBeInTheDocument()
    })
  })
})

