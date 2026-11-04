import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'
import { setup, trackProblems } from './support/mock-backend'
import { BANGLA_BIO } from './support/bangla'

const VIEWPORTS = [
  { name: 'mobile', width: 360, height: 800 },
  { name: 'tablet', width: 768, height: 1024 },
  { name: 'desktop', width: 1440, height: 900 },
]

type SetupOptions = NonNullable<Parameters<typeof setup>[1]>

interface Screen {
  name: string
  path: string
  options?: SetupOptions
  ready: (page: Page) => Promise<void>
  act?: (page: Page) => Promise<void>
}

const heading = (text: string | RegExp) => (page: Page) =>
  expect(page.getByRole('heading', { name: text, exact: false }).first()).toBeVisible()

const SCREENS: Screen[] = [
  { name: 'home', path: '/', options: { signedIn: false }, ready: heading(/The Right Doctor/) },
  { name: 'not-found', path: '/nope', options: { signedIn: false }, ready: heading(/couldn’t find/i) },
  { name: 'sign-in', path: '/login', options: { signedIn: false }, ready: heading(/Sign In to MediMatch/) },
  { name: 'register', path: '/register?role=doctor', options: { signedIn: false }, ready: heading(/Create Your Account/) },
  { name: 'chat-consent', path: '/chat', options: { consent: false }, ready: heading(/Before You Start/) },
  { name: 'chat', path: '/chat', ready: heading(/Symptom Assistant/), act: async (page) => {
    await expect(page.getByTestId('ai-disclaimer')).toBeVisible()
    await page.getByLabel('Describe your symptoms').fill('Headache and dizziness')
    await page.getByRole('button', { name: 'Send' }).click()
    await page.getByRole('button', { name: '2 to 3 days' }).click()
    await expect(page.getByTestId('recommendation').first()).toBeVisible()
  } },
  { name: 'chat-emergency', path: '/chat', ready: heading(/Symptom Assistant/), act: async (page) => {
    await page.getByLabel('Describe your symptoms').fill('I have chest pain')
    await page.getByRole('button', { name: 'Send' }).click()
    await expect(page.getByTestId('emergency-notice')).toBeVisible()
  } },
  { name: 'doctor-search', path: '/doctors', ready: heading(/Dr. Kazi Ahmed/) },
  { name: 'doctor-search-empty', path: '/doctors?city=Khulna', ready: heading(/No Doctors Match/) },
  { name: 'doctor-detail', path: '/doctors/d1', ready: heading(/Book an Appointment/), act: async (page) => {
    await expect(page.getByRole('radiogroup', { name: 'Choose a time' })).toBeVisible()
    await page.getByRole('radio').nth(5).click()
  } },
  { name: 'appointments', path: '/appointments', ready: heading('My Appointments'), act: async (page) => {
    await expect(page.getByText('Dr. Kazi Ahmed')).toBeVisible()
  } },
  { name: 'appointments-empty', path: '/appointments', options: { empty: true }, ready: heading(/No Upcoming Appointments/) },
  { name: 'account', path: '/account', ready: heading(/Your Details/) },
  { name: 'doctor-onboarding', path: '/doctor/onboarding', options: { role: 'doctor', emptyDoctorProfile: true, doctorStatus: 'pending' }, ready: heading(/Set Up Your Profile/) },
  { name: 'doctor-profile', path: '/doctor/profile', options: { role: 'doctor' }, ready: heading('Your Profile'), act: async (page) => {
    await expect(page.getByLabel('Neurology')).toBeVisible()
  } },
  { name: 'doctor-credentials', path: '/doctor/credentials', options: { role: 'doctor' }, ready: heading(/No Documents Yet/) },
  { name: 'doctor-verification', path: '/doctor/verification', options: { role: 'doctor' }, ready: heading('History') },
  { name: 'doctor-availability', path: '/doctor/availability', options: { role: 'doctor' }, ready: heading(/Week of/) },
  { name: 'doctor-appointments', path: '/doctor/appointments', options: { role: 'doctor' }, ready: heading(/^Appointments$/), act: async (page) => {
    await expect(page.getByText('Demo Patient Karim')).toBeVisible()
  } },
  { name: 'admin-queue', path: '/admin/queue?doctor=p1', options: { role: 'admin' }, ready: heading(/Dr. Jamil Pending/) },
  { name: 'admin-doctors', path: '/admin/doctors', options: { role: 'admin' }, ready: heading(/^Doctors$/), act: async (page) => {
    await expect(page.getByRole('table')).toBeVisible()
  } },
  { name: 'admin-patients', path: '/admin/patients', options: { role: 'admin' }, ready: heading('Patients'), act: async (page) => {
    await expect(page.getByRole('table')).toBeVisible()
  } },
  { name: 'admin-specialties', path: '/admin/specialties', options: { role: 'admin' }, ready: heading('Specialties'), act: async (page) => {
    await expect(page.getByRole('table')).toBeVisible()
  } },
  { name: 'admin-audit-log', path: '/admin/audit-logs', options: { role: 'admin' }, ready: heading('Audit Log'), act: async (page) => {
    await expect(page.getByRole('table')).toBeVisible()
  } },
  { name: 'dev-components', path: '/dev/components', options: { signedIn: false }, ready: heading('Components') },
]

for (const screen of SCREENS) {
  for (const viewport of VIEWPORTS) {
    test(`${screen.name} at ${viewport.name}`, async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height })
      const problems = trackProblems(page)
      await setup(page, screen.options)
      await page.goto(screen.path)
      await screen.ready(page)
      await screen.act?.(page)
      await page.evaluate(() => document.fonts.ready)
      await page.evaluate(() => window.scrollTo(0, 0))

      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
      expect(overflow, 'page must not scroll sideways').toBeLessThanOrEqual(0)

      await page.screenshot({ path: `screenshots/${screen.name}/${viewport.name}.png`, fullPage: true, animations: 'disabled' })

      const results = await new AxeBuilder({ page }).analyze()
      const serious = results.violations
        .filter((item) => item.impact === 'serious' || item.impact === 'critical')
        .map((item) => `${item.id}: ${item.nodes.map((node) => node.target.join(' ')).join(', ')}`)
      expect(serious).toEqual([])
      expect(problems).toEqual([])
    })
  }
}

test('a long Bangla profile fits without overflow at 360px', async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 800 })
  const backend = await setup(page)
  backend.doctors[0].bio = BANGLA_BIO
  backend.doctors[0].full_name = 'ডা. মোহাম্মদ আব্দুল্লাহ আল মামুন চৌধুরী'
  await page.goto('/doctors/d1')
  await expect(page.getByText(BANGLA_BIO)).toBeVisible()
  await page.evaluate(() => document.fonts.load('16px "Noto Sans Bengali"', 'আ'))
  await page.evaluate(() => document.fonts.ready)
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
  expect(overflow).toBeLessThanOrEqual(0)
  expect(await page.evaluate(() => document.fonts.check('16px "Noto Sans Bengali"', 'আ'))).toBe(true)
  await page.screenshot({ path: 'screenshots/bangla/mobile.png', fullPage: true, animations: 'disabled' })
})
