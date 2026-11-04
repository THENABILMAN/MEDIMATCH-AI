import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { lazy, Suspense, type ComponentType, type LazyExoticComponent } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { ApiError } from './api/client'
import { ProtectedRoute } from './components/common/ProtectedRoute'
import { AppShell } from './components/layout/app-shell'
import { Skeleton } from './components/ui/skeleton'
import { ToastProvider } from './components/ui/toast'
import { TooltipProvider } from './components/ui/tooltip'
import { AuthProvider } from './contexts/AuthContext'
import type { UserRole } from './types'

const HomePage = lazy(() => import('./pages/HomePage'))
const NotFoundPage = lazy(() => import('./pages/NotFoundPage'))
const LoginPage = lazy(() => import('./pages/auth/LoginPage'))
const RegisterPage = lazy(() => import('./pages/auth/RegisterPage'))
const ChatPage = lazy(() => import('./pages/patient/ChatPage'))
const DoctorSearchPage = lazy(() => import('./pages/patient/DoctorSearchPage'))
const DoctorDetailPage = lazy(() => import('./pages/patient/DoctorDetailPage'))
const MyAppointmentsPage = lazy(() => import('./pages/patient/MyAppointmentsPage'))
const AccountPage = lazy(() => import('./pages/patient/AccountPage'))
const OnboardingPage = lazy(() => import('./pages/doctor/OnboardingPage'))
const DoctorProfilePage = lazy(() => import('./pages/doctor/DoctorProfilePage'))
const CredentialsPage = lazy(() => import('./pages/doctor/CredentialsPage'))
const VerificationPage = lazy(() => import('./pages/doctor/VerificationPage'))
const AvailabilityPage = lazy(() => import('./pages/doctor/AvailabilityPage'))
const DoctorAppointmentsPage = lazy(() => import('./pages/doctor/DoctorAppointmentsPage'))
const AdminQueuePage = lazy(() => import('./pages/admin/AdminQueuePage'))
const AdminDoctorsPage = lazy(() => import('./pages/admin/AdminDoctorsPage'))
const AdminPatientsPage = lazy(() => import('./pages/admin/AdminPatientsPage'))
const AdminSpecialtiesPage = lazy(() => import('./pages/admin/AdminSpecialtiesPage'))
const AdminAuditLogsPage = lazy(() => import('./pages/admin/AdminAuditLogsPage'))
// Referencing import.meta.env.DEV here removes the page from production bundles
const ComponentsPage = import.meta.env.DEV ? lazy(() => import('./pages/dev/ComponentsPage')) : null

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 2,
      refetchOnWindowFocus: false,
      retry: (failures, error) => !(error instanceof ApiError && error.status < 500) && failures < 1,
    },
  },
})

function PageFallback() {
  return (
    <div className="page-gutter py-8">
      <Skeleton className="h-10 w-64" />
      <Skeleton className="mt-4 h-40" />
    </div>
  )
}

function guarded(Page: LazyExoticComponent<ComponentType>, roles: UserRole[]) {
  return (
    <ProtectedRoute allowedRoles={roles}>
      <Page />
    </ProtectedRoute>
  )
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <TooltipProvider delayDuration={300}>
          <AuthProvider>
            <BrowserRouter>
              <Suspense fallback={<PageFallback />}>
                <Routes>
                  <Route element={<AppShell />}>
                    <Route path="/" element={<HomePage />} />
                    <Route path="/login" element={<LoginPage />} />
                    <Route path="/register" element={<RegisterPage />} />
                    <Route path="/doctors" element={<DoctorSearchPage />} />
                    <Route path="/doctors/:id" element={<DoctorDetailPage />} />

                    <Route path="/chat/:conversationId?" element={guarded(ChatPage, ['patient', 'admin'])} />
                    <Route path="/appointments" element={guarded(MyAppointmentsPage, ['patient', 'admin'])} />
                    <Route path="/account" element={guarded(AccountPage, ['patient', 'doctor', 'admin'])} />

                    <Route path="/doctor/onboarding" element={guarded(OnboardingPage, ['doctor'])} />
                    <Route path="/doctor/profile" element={guarded(DoctorProfilePage, ['doctor'])} />
                    <Route path="/doctor/credentials" element={guarded(CredentialsPage, ['doctor'])} />
                    <Route path="/doctor/verification" element={guarded(VerificationPage, ['doctor'])} />
                    <Route path="/doctor/availability" element={guarded(AvailabilityPage, ['doctor'])} />
                    <Route path="/doctor/appointments" element={guarded(DoctorAppointmentsPage, ['doctor'])} />

                    <Route path="/admin/queue" element={guarded(AdminQueuePage, ['admin'])} />
                    <Route path="/admin/doctors" element={guarded(AdminDoctorsPage, ['admin'])} />
                    <Route path="/admin/patients" element={guarded(AdminPatientsPage, ['admin'])} />
                    <Route path="/admin/specialties" element={guarded(AdminSpecialtiesPage, ['admin'])} />
                    <Route path="/admin/audit-logs" element={guarded(AdminAuditLogsPage, ['admin'])} />

                    {ComponentsPage && <Route path="/dev/components" element={<ComponentsPage />} />}
                    <Route path="*" element={<NotFoundPage />} />
                  </Route>
                </Routes>
              </Suspense>
            </BrowserRouter>
          </AuthProvider>
        </TooltipProvider>
      </ToastProvider>
    </QueryClientProvider>
  )
}

export default App
