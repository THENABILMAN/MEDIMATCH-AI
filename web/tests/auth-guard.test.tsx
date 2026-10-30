import React from 'react'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { ProtectedRoute } from '../src/components/common/ProtectedRoute'
import * as AuthContextModule from '../src/contexts/AuthContext'

describe('ProtectedRoute', () => {
  it('shows loading indicator when authentication is loading', () => {
    vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
      user: null,
      profile: null,
      role: null,
      session: null,
      isLoading: true,
      login: vi.fn(),
      registerPatient: vi.fn(),
      registerDoctor: vi.fn(),
      logout: vi.fn(),
      refreshProfile: vi.fn(),
    })

    render(
      <MemoryRouter initialEntries={['/protected']}>
        <ProtectedRoute>
          <div>Protected Content</div>
        </ProtectedRoute>
      </MemoryRouter>
    )

    expect(screen.getByText(/verifying session/i)).toBeInTheDocument()
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
  })

  it('redirects to /login if user is not authenticated', () => {
    vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
      user: null,
      profile: null,
      role: null,
      session: null,
      isLoading: false,
      login: vi.fn(),
      registerPatient: vi.fn(),
      registerDoctor: vi.fn(),
      logout: vi.fn(),
      refreshProfile: vi.fn(),
    })

    render(
      <MemoryRouter initialEntries={['/protected']}>
        <Routes>
          <Route
            path="/protected"
            element={
              <ProtectedRoute>
                <div>Protected Content</div>
              </ProtectedRoute>
            }
          />
          <Route path="/login" element={<div>Login Page</div>} />
        </Routes>
      </MemoryRouter>
    )

    expect(screen.getByText('Login Page')).toBeInTheDocument()
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
  })

  it('renders children if user is authenticated and role is permitted', () => {
    vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
      user: { id: 'patient-123' } as any,
      profile: { id: 'patient-123', role: 'patient', full_name: 'Test Patient' },
      role: 'patient',
      session: {} as any,
      isLoading: false,
      login: vi.fn(),
      registerPatient: vi.fn(),
      registerDoctor: vi.fn(),
      logout: vi.fn(),
      refreshProfile: vi.fn(),
    })

    render(
      <MemoryRouter initialEntries={['/patient-only']}>
        <ProtectedRoute allowedRoles={['patient']}>
          <div>Welcome Patient</div>
        </ProtectedRoute>
      </MemoryRouter>
    )

    expect(screen.getByText('Welcome Patient')).toBeInTheDocument()
  })

  it('redirects user if user role is not permitted for the route', () => {
    vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
      user: { id: 'patient-123' } as any,
      profile: { id: 'patient-123', role: 'patient', full_name: 'Test Patient' },
      role: 'patient',
      session: {} as any,
      isLoading: false,
      login: vi.fn(),
      registerPatient: vi.fn(),
      registerDoctor: vi.fn(),
      logout: vi.fn(),
      refreshProfile: vi.fn(),
    })

    render(
      <MemoryRouter initialEntries={['/doctor-only']}>
        <Routes>
          <Route
            path="/doctor-only"
            element={
              <ProtectedRoute allowedRoles={['doctor']}>
                <div>Doctor Only Page</div>
              </ProtectedRoute>
            }
          />
          <Route path="/chat" element={<div>Redirected to Chat</div>} />
        </Routes>
      </MemoryRouter>
    )

    expect(screen.getByText('Redirected to Chat')).toBeInTheDocument()
    expect(screen.queryByText('Doctor Only Page')).not.toBeInTheDocument()
  })
})

