import {
  Bot,
  CalendarClock,
  CalendarDays,
  FileBadge,
  type LucideIcon,
  ListChecks,
  LogOut,
  Menu,
  Phone,
  ScrollText,
  Search,
  ShieldCheck,
  Stethoscope,
  Tags,
  UserRound,
  Users,
} from 'lucide-react'
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
import { Logo } from './logo'

interface NavItem {
  to: string
  label: string
  icon: LucideIcon
}

const NAV: Record<UserRole | 'public', NavItem[]> = {
  public: [{ to: '/doctors', label: 'nav.findDoctors', icon: Search }],
  patient: [
    { to: '/chat', label: 'nav.assistant', icon: Bot },
    { to: '/doctors', label: 'nav.findDoctors', icon: Search },
    { to: '/appointments', label: 'nav.appointments', icon: CalendarDays },
    { to: '/account', label: 'nav.account', icon: UserRound },
  ],
  doctor: [
    { to: '/doctor/appointments', label: 'nav.appointments', icon: CalendarDays },
    { to: '/doctor/availability', label: 'nav.availability', icon: CalendarClock },
    { to: '/doctor/profile', label: 'nav.profile', icon: UserRound },
    { to: '/doctor/credentials', label: 'nav.credentials', icon: FileBadge },
    { to: '/doctor/verification', label: 'nav.verification', icon: ShieldCheck },
  ],
  admin: [
    { to: '/admin/queue', label: 'nav.queue', icon: ListChecks },
    { to: '/admin/doctors', label: 'nav.doctors', icon: Stethoscope },
    { to: '/admin/patients', label: 'nav.patients', icon: Users },
    { to: '/admin/specialties', label: 'nav.specialties', icon: Tags },
    { to: '/admin/audit-logs', label: 'nav.auditLog', icon: ScrollText },
  ],
}

const PORTAL: Record<UserRole, string> = {
  patient: 'nav.patientPortal',
  doctor: 'nav.doctorPortal',
  admin: 'nav.adminPortal',
}

function barLinkClasses({ isActive }: { isActive: boolean }) {
  return cn(
    'flex min-h-11 items-center rounded-sm px-3 text-sm font-medium transition-colors hover:bg-primary-tint',
    isActive ? 'text-ink underline decoration-2 underline-offset-8' : 'text-muted hover:text-ink'
  )
}

function sideLinkClasses({ isActive }: { isActive: boolean }) {
  return cn(
    'flex min-h-11 items-center gap-3 rounded-sm px-3 text-md font-medium transition-colors md:min-h-10 md:text-sm',
    isActive ? 'bg-primary text-on-primary' : 'text-muted hover:bg-primary-tint hover:text-ink'
  )
}

function EmergencyLink({ className }: { className?: string }) {
  const { t } = useTranslation()
  return (
    <a
      href={`tel:${EMERGENCY_NUMBER}`}
      className={cn(
        'inline-flex min-h-10 items-center justify-center gap-2 rounded-sm bg-danger px-3 text-sm font-semibold whitespace-nowrap text-white transition-colors hover:bg-danger-pressed',
        className
      )}
    >
      <Phone aria-hidden className="size-4" strokeWidth={2} />
      {t('nav.emergency', { number: EMERGENCY_NUMBER })}
    </a>
  )
}

function NavItems({ items, onNavigate, className }: { items: NavItem[]; onNavigate?: () => void; className: typeof sideLinkClasses }) {
  const { t } = useTranslation()
  return items.map((item) => (
    <NavLink key={item.to} to={item.to} className={className} onClick={onNavigate}>
      {className === sideLinkClasses && <item.icon aria-hidden className="size-4 shrink-0" strokeWidth={1.75} />}
      {t(item.label)}
    </NavLink>
  ))
}

export function AppShell() {
  const { t } = useTranslation()
  const { user, role, profile, logout } = useAuth()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)

  const items = NAV[role ?? 'public']
  const showEmergency = !role || role === 'patient'
  const portal = Boolean(role) && pathname !== '/'

  async function signOut() {
    setMenuOpen(false)
    navigate('/')
    await logout()
  }

  return (
    <div className={cn('min-h-dvh', portal ? 'lg:grid lg:grid-cols-[var(--sidebar-width)_minmax(0,1fr)]' : 'flex flex-col')}>
      <a
        href="#main"
        className="fixed top-2 left-2 z-50 -translate-y-20 rounded-sm bg-surface px-4 py-2 text-ink focus:translate-y-0"
      >
        {t('nav.skipToContent')}
      </a>

      {portal && role && (
        <aside className="on-navy sticky top-0 hidden h-dvh flex-col gap-6 bg-navy p-4 lg:flex">
          <div className="px-2 pt-2">
            <Logo />
            <p className="mt-2 text-sm text-muted">{t(PORTAL[role])}</p>
          </div>

          <nav aria-label={t('nav.main')} className="flex flex-col gap-1">
            <NavItems items={items} className={sideLinkClasses} />
          </nav>

          <div className="mt-auto flex flex-col gap-3">
            {showEmergency && <EmergencyLink />}
            <div className="flex items-center gap-2 border-t border-border pt-3">
              <p className="min-w-0 flex-1 truncate px-2 text-sm font-medium">{profile?.full_name}</p>
              <Button variant="ghost" size="sm" onClick={() => void signOut()}>
                <LogOut aria-hidden className="size-4" strokeWidth={1.75} />
                {t('nav.signOut')}
              </Button>
            </div>
          </div>
        </aside>
      )}

      <div className="flex min-h-dvh min-w-0 flex-col">
        <header className={cn('on-navy sticky top-0 z-30 bg-navy', portal && 'lg:hidden')}>
          <div className="flex h-[var(--header-height)] items-center justify-between gap-4 px-4 md:px-8">
            <div className="flex min-w-0 items-center gap-8">
              <Logo />
              <nav aria-label={t('nav.main')} className="hidden items-center gap-1 lg:flex">
                <NavItems items={items} className={barLinkClasses} />
              </nav>
            </div>

            <div className="flex items-center gap-2">
              {showEmergency && <EmergencyLink />}
              <div className="hidden items-center gap-2 lg:flex">
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
            <NavItems items={items} className={sideLinkClasses} onNavigate={() => setMenuOpen(false)} />
          </nav>
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
