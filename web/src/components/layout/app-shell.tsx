import { LogOut, Menu, Phone } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import { EMERGENCY_NUMBER } from '../../lib/constants'
import { cn } from '../../lib/cn'
import type { UserRole } from '../../types'
import { ErrorBoundary } from '../common/ErrorBoundary'
import { Button } from '../ui/button'
import { IconButton } from '../ui/icon-button'
import { Sheet } from '../ui/sheet'
import { LanguageSwitch } from './language-switch'
import { Logo } from './logo'

interface NavItem {
  to: string
  label: string
}

const NAV: Record<UserRole | 'public', NavItem[]> = {
  public: [{ to: '/doctors', label: 'nav.findDoctors' }],
  patient: [
    { to: '/chat', label: 'nav.assistant' },
    { to: '/doctors', label: 'nav.findDoctors' },
    { to: '/appointments', label: 'nav.appointments' },
    { to: '/account', label: 'nav.account' },
  ],
  doctor: [
    { to: '/doctor/appointments', label: 'nav.appointments' },
    { to: '/doctor/availability', label: 'nav.availability' },
    { to: '/doctor/profile', label: 'nav.profile' },
    { to: '/doctor/credentials', label: 'nav.credentials' },
    { to: '/doctor/verification', label: 'nav.verification' },
  ],
  admin: [
    { to: '/admin/queue', label: 'nav.queue' },
    { to: '/admin/doctors', label: 'nav.doctors' },
    { to: '/admin/patients', label: 'nav.patients' },
    { to: '/admin/specialties', label: 'nav.specialties' },
    { to: '/admin/audit-logs', label: 'nav.auditLog' },
  ],
}

function barLink({ isActive }: { isActive: boolean }) {
  return cn(
    'flex h-14 items-center border-b-2 px-3 text-sm font-medium transition-colors',
    isActive ? 'border-primary text-ink' : 'border-transparent text-muted hover:text-ink'
  )
}

function listLink({ isActive }: { isActive: boolean }) {
  return cn(
    'flex min-h-11 items-center rounded-sm px-3 text-md transition-colors lg:min-h-9 lg:text-sm',
    isActive ? 'bg-primary-tint font-medium text-primary-hover' : 'text-muted hover:bg-canvas hover:text-ink'
  )
}

function EmergencyLink() {
  const { t } = useTranslation()
  return (
    <a
      href={`tel:${EMERGENCY_NUMBER}`}
      className="inline-flex min-h-10 items-center gap-1 rounded-sm bg-danger px-3 text-sm font-medium whitespace-nowrap text-white transition-colors hover:bg-danger-pressed"
    >
      <Phone aria-hidden className="size-4" strokeWidth={1.75} />
      {t('nav.emergency', { number: EMERGENCY_NUMBER })}
    </a>
  )
}

export function AppShell() {
  const { t } = useTranslation()
  const { user, role, logout } = useAuth()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)

  const items = NAV[role ?? 'public']
  const showEmergency = !role || role === 'patient'
  const isAdmin = role === 'admin'
  const isHome = pathname === '/'

  async function signOut() {
    setMenuOpen(false)
    navigate('/')
    await logout()
  }

  return (
    <div className={cn('min-h-dvh', isAdmin ? 'lg:grid lg:grid-cols-[216px_minmax(0,1fr)]' : 'flex flex-col')}>
      <a
        href="#main"
        className="fixed top-2 left-2 z-50 -translate-y-20 rounded-sm bg-primary px-4 py-2 text-white focus:translate-y-0"
      >
        {t('nav.skipToContent')}
      </a>

      {isAdmin && (
        <aside className="sticky top-0 hidden h-dvh flex-col gap-4 border-r border-border bg-surface p-3 lg:flex">
          <div className="px-3 pt-2">
            <Logo />
          </div>
          <nav aria-label={t('nav.main')} className="flex flex-col gap-0.5">
            {items.map((item) => (
              <NavLink key={item.to} to={item.to} className={listLink}>
                {t(item.label)}
              </NavLink>
            ))}
          </nav>
          <div className="mt-auto flex flex-col items-start gap-1">
            <LanguageSwitch />
            <Button variant="ghost" size="sm" onClick={() => void signOut()}>
              <LogOut aria-hidden className="size-4" strokeWidth={1.75} />
              {t('nav.signOut')}
            </Button>
          </div>
        </aside>
      )}

      <div className="flex min-h-dvh min-w-0 flex-col">
        <header
          className={cn(
            'sticky top-0 z-30',
            isHome ? 'on-ink bg-ink-field' : 'border-b border-border bg-surface',
            isAdmin && 'lg:hidden'
          )}
        >
          <div className={cn('flex h-14 items-center justify-between gap-4', isHome ? 'home-gutter' : 'page-gutter')}>
            <div className="flex min-w-0 items-center gap-6">
              <Logo />
              <nav aria-label={t('nav.main')} className="hidden items-center lg:flex">
                {items.map((item) => (
                  <NavLink key={item.to} to={item.to} className={barLink}>
                    {t(item.label)}
                  </NavLink>
                ))}
              </nav>
            </div>

            <div className="flex items-center gap-2">
              {showEmergency && <EmergencyLink />}
              <div className="hidden items-center gap-2 lg:flex">
                <LanguageSwitch />
                {user ? (
                  <Button variant="ghost" size="sm" onClick={() => void signOut()}>
                    {t('nav.signOut')}
                  </Button>
                ) : (
                  <>
                    <Button asChild variant="ghost" size="sm">
                      <NavLink to="/login">{t('nav.signIn')}</NavLink>
                    </Button>
                    <Button asChild size="sm">
                      <NavLink to="/register">{t('nav.createAccount')}</NavLink>
                    </Button>
                  </>
                )}
              </div>
              <div className="lg:hidden">
                <IconButton label={t('nav.openMenu')} onClick={() => setMenuOpen(true)}>
                  <Menu aria-hidden className="size-6" strokeWidth={1.75} />
                </IconButton>
              </div>
            </div>
          </div>
        </header>

        <Sheet
          open={menuOpen}
          onOpenChange={setMenuOpen}
          title={t('nav.menu')}
          footer={
            user ? (
              <Button variant="secondary" className="w-full" onClick={() => void signOut()}>
                <LogOut aria-hidden className="size-4" strokeWidth={1.75} />
                {t('nav.signOut')}
              </Button>
            ) : (
              <div className="flex flex-col gap-2">
                <Button asChild>
                  <NavLink to="/register" onClick={() => setMenuOpen(false)}>
                    {t('nav.createAccount')}
                  </NavLink>
                </Button>
                <Button asChild variant="secondary">
                  <NavLink to="/login" onClick={() => setMenuOpen(false)}>
                    {t('nav.signIn')}
                  </NavLink>
                </Button>
              </div>
            )
          }
        >
          <nav aria-label={t('nav.main')} className="flex flex-col gap-1">
            {items.map((item) => (
              <NavLink key={item.to} to={item.to} className={listLink} onClick={() => setMenuOpen(false)}>
                {t(item.label)}
              </NavLink>
            ))}
          </nav>
          <LanguageSwitch className="mt-3" />
        </Sheet>

        <main id="main" tabIndex={-1} className="flex flex-1 flex-col outline-none">
          <ErrorBoundary>
            <Outlet />
          </ErrorBoundary>
        </main>
      </div>
    </div>
  )
}
