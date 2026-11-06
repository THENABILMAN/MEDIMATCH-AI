import { Phone, SignOut } from '@phosphor-icons/react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
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
    { to: '/doctor/billing', label: 'nav.billing' },
  ],
  admin: [
    { to: '/admin/queue', label: 'nav.queue' },
    { to: '/admin/doctors', label: 'nav.doctors' },
    { to: '/admin/patients', label: 'nav.patients' },
    { to: '/admin/billing', label: 'nav.billing' },
    { to: '/admin/specialties', label: 'nav.specialties' },
    { to: '/admin/audit-logs', label: 'nav.auditLog' },
  ],
}

function barLink({ isActive }: { isActive: boolean }) {
  return cn(
    'body-5 flex min-h-10 items-center rounded-full px-3 py-2 transition-colors',
    isActive ? 'bg-primary text-white' : 'text-muted hover:bg-canvas hover:text-ink'
  )
}

function railLink({ isActive }: { isActive: boolean }) {
  return cn(
    'flex min-h-9 items-center rounded-full px-3 transition-colors',
    isActive ? 'body-5 bg-primary text-white' : 'body-6 text-muted hover:bg-canvas hover:text-ink'
  )
}

function menuLink({ isActive }: { isActive: boolean }) {
  return cn(
    'heading-4 flex min-h-12 items-center rounded-lg transition-colors',
    isActive ? 'text-ink underline underline-offset-8' : 'text-muted hover:text-ink'
  )
}

/** Two lines that turn into a cross. */
function MenuGlyph({ open }: { open: boolean }) {
  const line = 'absolute inset-x-0 h-0.5 rounded-full bg-current transition-transform duration-500'
  return (
    <span aria-hidden className="relative block h-3 w-6">
      <span className={cn(line, 'top-0', open && 'translate-y-[5px] rotate-45')} />
      <span className={cn(line, 'bottom-0', open && '-translate-y-[5px] -rotate-45')} />
    </span>
  )
}

/** Starts as the lines of the menu button, then turns as the panel opens. */
function ClosingGlyph() {
  const [open, setOpen] = useState(false)
  useEffect(() => {
    const frame = requestAnimationFrame(() => setOpen(true))
    return () => cancelAnimationFrame(frame)
  }, [])
  return <MenuGlyph open={open} />
}

const LINK_STEP_MS = 60
const LINK_SEQUENCE_MS = 400

function EmergencyLink() {
  const { t } = useTranslation()
  return (
    <a
      href={`tel:${EMERGENCY_NUMBER}`}
      className="body-5 inline-flex min-h-10 items-center gap-1 rounded-full bg-danger px-3 whitespace-nowrap text-white transition-[background-color,transform] hover:bg-danger-pressed active:scale-[0.98]"
    >
      <Phone aria-hidden className="size-4" />
      {t('nav.emergency', { number: EMERGENCY_NUMBER })}
    </a>
  )
}

function SiteFooter() {
  const { t } = useTranslation()
  const links = [
    { to: '/doctors', label: 'nav.findDoctors' },
    { to: '/for-doctors', label: 'home.forDoctors' },
    { to: '/privacy', label: 'legal.privacy.link' },
    { to: '/terms', label: 'legal.terms.link' },
  ]
  return (
    <footer className="border-t border-border bg-surface">
      <div className="home-gutter flex flex-col gap-4 py-8 md:flex-row md:items-center md:justify-between">
        <p className="body-6 max-w-[56ch] text-muted">{t('home.footer')}</p>
        <nav aria-label={t('nav.footer')} className="flex flex-wrap gap-x-4 gap-y-2">
          {links.map((item) => (
            <Link key={item.to} to={item.to} className="body-5 whitespace-nowrap underline underline-offset-4">
              {t(item.label)}
            </Link>
          ))}
        </nav>
      </div>
    </footer>
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
  const showFooter = !isAdmin && !pathname.startsWith('/chat')
  const linkDelay = Math.min(LINK_STEP_MS, LINK_SEQUENCE_MS / Math.max(items.length, 1))

  async function signOut() {
    setMenuOpen(false)
    navigate('/')
    await logout()
  }

  return (
    <div className={cn('min-h-dvh', isAdmin ? 'lg:grid lg:grid-cols-[216px_minmax(0,1fr)]' : 'flex flex-col')}>
      <a
        href="#main"
        className="fixed top-2 left-2 z-50 -translate-y-20 rounded-lg bg-primary px-4 py-2 text-white focus:translate-y-0"
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
              <NavLink key={item.to} to={item.to} className={railLink}>
                {t(item.label)}
              </NavLink>
            ))}
          </nav>
          <div className="mt-auto flex flex-col items-start gap-1">
            <LanguageSwitch />
            <Button variant="ghost" size="sm" onClick={() => void signOut()}>
              <SignOut aria-hidden className="size-4" />
              {t('nav.signOut')}
            </Button>
          </div>
        </aside>
      )}

      <div className="flex min-h-dvh min-w-0 flex-col">
        <header
          className={cn(
            'pointer-events-none sticky top-0 z-30 flex justify-center px-4 py-3',
            isAdmin && 'lg:hidden'
          )}
        >
          <div className="pointer-events-auto flex h-14 w-fit max-w-full items-center gap-4 rounded-2xl border border-border bg-surface/80 px-3 backdrop-blur-md lg:gap-6">
            <div className="flex min-w-0 items-center gap-4">
              <Logo />
              <nav aria-label={t('nav.main')} className="hidden items-center gap-1 lg:flex">
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
                    {/* The home page keeps one main action above the fold */}
                    {!isHome && (
                      <Button asChild size="sm">
                        <NavLink to="/register">{t('nav.createAccount')}</NavLink>
                      </Button>
                    )}
                  </>
                )}
              </div>
              <div className="lg:hidden">
                <IconButton label={t('nav.openMenu')} onClick={() => setMenuOpen(true)}>
                  <MenuGlyph open={menuOpen} />
                </IconButton>
              </div>
            </div>
          </div>
        </header>

        <Sheet
          open={menuOpen}
          onOpenChange={setMenuOpen}
          title={t('nav.menu')}
          fullScreen
          closeIcon={<ClosingGlyph />}
          footer={
            user ? (
              <Button variant="secondary" className="w-full" onClick={() => void signOut()}>
                <SignOut aria-hidden className="size-4" />
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
            {items.map((item, index) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={(state) => cn(menuLink(state), 'animate-link-in')}
                style={{ animationDelay: `${index * linkDelay}ms` }}
                onClick={() => setMenuOpen(false)}
              >
                {t(item.label)}
              </NavLink>
            ))}
          </nav>
          <LanguageSwitch className="mt-4 -ml-3" />
        </Sheet>

        <main id="main" tabIndex={-1} className={cn('flex flex-1 flex-col outline-none', isHome && '-mt-20')}>
          <ErrorBoundary>
            <Outlet />
          </ErrorBoundary>
        </main>

        {showFooter && <SiteFooter />}
      </div>
    </div>
  )
}
