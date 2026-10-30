import React from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Navbar } from './components/common/Navbar'
import { ProtectedRoute } from './components/common/ProtectedRoute'
import { AuthProvider } from './contexts/AuthContext'

// Pages
import { HomePage } from './pages/HomePage'
import { LoginPage } from './pages/auth/LoginPage'
import { RegisterPage } from './pages/auth/RegisterPage'

// Patient Pages
import { ChatPage } from './pages/patient/ChatPage'
import { DoctorDetailPage } from './pages/patient/DoctorDetailPage'
import { DoctorSearchPage } from './pages/patient/DoctorSearchPage'
import { MyAppointmentsPage } from './pages/patient/MyAppointmentsPage'

// Doctor Pages
import { AvailabilityPage } from './pages/doctor/AvailabilityPage'
import { DoctorAppointmentsPage } from './pages/doctor/DoctorAppointmentsPage'
import { DoctorProfilePage } from './pages/doctor/DoctorProfilePage'

// Admin Pages
import { AdminAuditLogsPage } from './pages/admin/AdminAuditLogsPage'
import { AdminDoctorsPage } from './pages/admin/AdminDoctorsPage'
import { AdminSpecialtiesPage } from './pages/admin/AdminSpecialtiesPage'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 2,
      retry: 1,
    },
  },
})

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <div className="flex min-h-screen flex-col bg-slate-50 text-slate-900">
            <Navbar />
            <div className="flex-1">
              <Routes>
                {/* Public Routes */}
                <Route path="/" element={<HomePage />} />
                <Route path="/login" element={<LoginPage />} />
                <Route path="/register" element={<RegisterPage />} />
                <Route path="/doctors" element={<DoctorSearchPage />} />
                <Route path="/doctors/:id" element={<DoctorDetailPage />} />

                {/* Patient Routes */}
                <Route
                  path="/chat"
                  element={
                    <ProtectedRoute allowedRoles={['patient', 'admin']}>
                      <ChatPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/appointments"
                  element={
                    <ProtectedRoute allowedRoles={['patient', 'admin']}>
                      <MyAppointmentsPage />
                    </ProtectedRoute>
                  }
                />

                {/* Doctor Routes */}
                <Route
                  path="/doctor/profile"
                  element={
                    <ProtectedRoute allowedRoles={['doctor']}>
                      <DoctorProfilePage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/doctor/availability"
                  element={
                    <ProtectedRoute allowedRoles={['doctor']}>
                      <AvailabilityPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/doctor/appointments"
                  element={
                    <ProtectedRoute allowedRoles={['doctor']}>
                      <DoctorAppointmentsPage />
                    </ProtectedRoute>
                  }
                />

                {/* Admin Routes */}
                <Route
                  path="/admin/doctors"
                  element={
                    <ProtectedRoute allowedRoles={['admin']}>
                      <AdminDoctorsPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/admin/specialties"
                  element={
                    <ProtectedRoute allowedRoles={['admin']}>
                      <AdminSpecialtiesPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/admin/audit-logs"
                  element={
                    <ProtectedRoute allowedRoles={['admin']}>
                      <AdminAuditLogsPage />
                    </ProtectedRoute>
                  }
                />

                {/* Catch-all redirect */}
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </div>
          </div>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
}

export default App
