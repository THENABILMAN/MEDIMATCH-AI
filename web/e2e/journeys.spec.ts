import { expect, test } from '@playwright/test'
import { setup, trackProblems } from './support/mock-backend'
import { CRISIS_REPLY, EMERGENCY_REPLY } from './support/fixtures'

test('patient goes from chat to recommendations to a booking', async ({ page }) => {
  const problems = trackProblems(page)
  await setup(page)
  await page.goto('/chat')

  await page.getByLabel('Describe your symptoms').fill('Headache and dizziness')
  await page.getByRole('button', { name: 'Send' }).click()
  await page.getByRole('button', { name: '2 to 3 days' }).click()

  const first = page.getByTestId('recommendation').first()
  await expect(first).toContainText('Dr. Kazi Ahmed')
  await expect(first).toContainText('Why this match:')
  await first.getByRole('link', { name: 'View and Book' }).click()

  await expect(page).toHaveURL(/\/doctors\/d1/)
  await page.getByRole('radiogroup', { name: 'Choose a time' }).getByRole('radio').first().click()
  await expect(page).toHaveURL(/slot=/)
  await page.getByRole('button', { name: 'Book This Slot' }).click()
  await page.getByRole('button', { name: 'Confirm Booking' }).click()

  await expect(page).toHaveURL(/\/appointments/)
  await expect(page.getByRole('main').getByRole('listitem').filter({ hasText: 'Dr. Kazi Ahmed' })).toHaveCount(2)
  expect(problems).toEqual([])
})

test('doctor saves a profile and uploads credentials, and can resume', async ({ page }) => {
  const problems = trackProblems(page)
  const backend = await setup(page, { role: 'doctor', emptyDoctorProfile: true, doctorStatus: 'pending' })
  await page.goto('/doctor/onboarding')

  await page.getByLabel('Clinic or Hospital').fill('Square Hospital')
  await page.getByLabel('Consultation Fee (BDT)').fill('1500')
  await page.getByLabel('Years of Experience').fill('12')
  await page.getByRole('button', { name: 'Save and Continue' }).click()
  await expect(page).toHaveURL(/step=clinical/)
  await expect.poll(() => backend.mine.clinic_name).toBe('Square Hospital')

  // Validation stays on the step and keeps what was typed
  await page.getByRole('button', { name: 'Save and Continue' }).click()
  await expect(page.getByText('Choose at least one specialty.')).toBeVisible()

  await page.getByLabel('Neurology').click()
  await page.getByLabel('Qualifications').fill('MBBS, FCPS (Medicine)')
  await page.getByLabel('Clinical Background').fill('I treat adults with migraine, seizures and long-term nerve conditions.')
  await page.getByRole('button', { name: 'Save and Continue' }).click()
  await expect(page).toHaveURL(/step=documents/)

  await page.getByLabel('Choose File').setInputFiles({ name: 'bmdc.pdf', mimeType: 'application/pdf', buffer: Buffer.from('%PDF') })
  await expect(page.getByText('Your document was uploaded.').first()).toBeVisible()
  await expect(page.getByRole('button', { name: 'Open BMDC Registration' })).toBeVisible()

  await page.reload()
  await expect(page.getByRole('button', { name: 'Finish Setup' })).toBeVisible()
  await page.getByRole('button', { name: 'Finish Setup' }).click()
  await expect(page).toHaveURL(/\/doctor\/verification/)
  expect(problems).toEqual([])
})

test('an unsupported credential file is refused before uploading', async ({ page }) => {
  await setup(page, { role: 'doctor' })
  await page.goto('/doctor/credentials')
  await page.getByLabel('Choose File').setInputFiles({ name: 'notes.txt', mimeType: 'text/plain', buffer: Buffer.from('x') })
  await expect(page.getByText('That file type isn’t supported.', { exact: false })).toBeVisible()
})

test('admin approves a doctor and rejection requires a reason', async ({ page }) => {
  const problems = trackProblems(page)
  const backend = await setup(page, { role: 'admin' })
  await page.goto('/admin/queue')

  await page.getByRole('link', { name: /Dr. Zubaida Pending/i }).click()
  await expect(page).toHaveURL(/doctor=p2/)
  await page.getByRole('button', { name: 'Reject' }).click()
  await page.getByRole('dialog').getByRole('button', { name: 'Reject' }).click()
  await expect(page.getByText('Write a reason of at least 10 characters.')).toBeVisible()
  await page.getByLabel('Reason').fill('The certificate is not readable.')
  await page.getByRole('dialog').getByRole('button', { name: 'Reject' }).click()
  await expect(page.getByText('Dr. Zubaida Pending was rejected.').first()).toBeVisible()

  await page.getByRole('link', { name: /Dr. Jamil Pending/i }).click()
  await page.getByRole('button', { name: 'Approve' }).click()
  await page.getByRole('dialog').getByRole('button', { name: 'Approve' }).click()
  await expect(page.getByText('Dr. Jamil Pending was approved.').first()).toBeVisible()
  expect(backend.pending[0].verification_status).toBe('approved')
  await expect(page.getByRole('heading', { name: 'Nothing to Review' })).toBeVisible()
  expect(problems).toEqual([])
})

test.describe('emergency messages', () => {
  test('appear verbatim, with a tel link and nothing softened or beneath them', async ({ page }) => {
    await setup(page)
    await page.goto('/chat')
    await page.getByLabel('Describe your symptoms').fill('I have chest pain')
    await page.getByRole('button', { name: 'Send' }).click()

    const notice = page.getByTestId('emergency-notice')
    await expect(notice).toBeVisible()
    await expect(notice.getByText('Please call 999 immediately', { exact: false })).toBeVisible()
    expect(await notice.locator('p').nth(1).evaluate((node) => node.textContent)).toBe(EMERGENCY_REPLY)
    await expect(notice.getByRole('link', { name: 'Call 999 Now' })).toHaveAttribute('href', 'tel:999')
    await expect(notice.getByRole('button')).toHaveCount(0)
    await expect(page.getByTestId('recommendation')).toHaveCount(0)
  })

  test('survive a reload', async ({ page }) => {
    const backend = await setup(page)
    await page.goto('/chat')
    await expect(page.getByRole('heading', { name: 'Symptom Assistant' })).toBeVisible()
    await expect.poll(() => backend.messages.length).toBeGreaterThan(0)
    backend.messages.push({
      id: 'e1',
      conversation_id: 'conv-1',
      sender: 'assistant',
      content: EMERGENCY_REPLY,
      created_at: new Date().toISOString(),
      metadata: { is_emergency: true, recommendations: [] },
    })
    await page.reload()
    await expect(page.getByTestId('emergency-notice')).toBeVisible()
  })
})

test('search filters live in the URL and the Back button restores them', async ({ page }) => {
  await setup(page)
  await page.goto('/doctors')
  await page.getByLabel('City').fill('Chattogram')
  await page.getByLabel('City').press('Enter')
  await expect(page).toHaveURL(/city=Chattogram/)
  await expect(page.getByRole('heading', { name: 'Dr. Samira Rahman' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Dr. Kazi Ahmed' })).toHaveCount(0)

  await page.getByRole('heading', { name: 'Dr. Samira Rahman' }).click()
  await expect(page).toHaveURL(/\/doctors\/d4/)
  await page.goBack()
  await expect(page).toHaveURL(/city=Chattogram/)
  await expect(page.getByLabel('City')).toHaveValue('Chattogram')
})

test('a slot taken by someone else is explained and the choice is cleared', async ({ page }) => {
  const backend = await setup(page)
  await page.goto('/doctors/d1')
  await page.getByRole('radiogroup', { name: 'Choose a time' }).getByRole('radio').first().click()
  await page.getByRole('button', { name: 'Book This Slot' }).click()
  backend.slots.forEach((slot) => {
    if (slot.doctor_id === 'd1' && slot.id.endsWith('-1-0')) slot.is_booked = true
  })
  await page.getByRole('button', { name: 'Confirm Booking' }).click()
  await expect(page.getByText('This slot has already been booked by another patient')).toBeVisible()
  await expect(page).not.toHaveURL(/slot=/)
})

test('booking keeps the chosen time when the network fails', async ({ page }) => {
  await setup(page)
  await page.goto('/doctors/d1')
  await page.getByRole('radiogroup', { name: 'Choose a time' }).getByRole('radio').first().click()
  await page.getByRole('button', { name: 'Book This Slot' }).click()
  await page.route('http://api.test/appointments', (route) => route.abort())
  await page.getByRole('button', { name: 'Confirm Booking' }).click()
  await expect(page.getByText('We couldn’t reach the server.', { exact: false })).toBeVisible()
  await expect(page).toHaveURL(/slot=/)
})

test('a chat message that fails offline can be retried without retyping', async ({ page }) => {
  await setup(page)
  await page.goto('/chat')
  await expect(page.getByTestId('ai-disclaimer')).toBeVisible()
  await expect(page.getByText('Hello! I am your MediMatch Assistant.', { exact: false })).toBeVisible()

  await page.route('http://api.test/chat/conversations/conv-1/messages', (route) => route.abort())
  await page.getByLabel('Describe your symptoms').fill('Headache for two days')
  await page.getByRole('button', { name: 'Send' }).click()

  await expect(page.getByText('Your Message Wasn’t Sent')).toBeVisible()
  await expect(page.getByText('If this is an emergency, call 999 now.')).toBeVisible()
  await page.unroute('http://api.test/chat/conversations/conv-1/messages')
  await page.getByRole('button', { name: 'Try Again' }).click()
  await expect(page.getByRole('button', { name: '2 to 3 days' })).toBeVisible()
  await expect(page.getByText('Headache for two days')).toHaveCount(1)
})

test('slow responses show designed loading states', async ({ page }) => {
  const backend = await setup(page)
  backend.delayMs = 1500
  await page.goto('/doctors')
  await expect(page.getByRole('status').first()).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Dr. Kazi Ahmed' })).toBeVisible({ timeout: 8000 })

  await page.goto('/chat')
  await page.getByLabel('Describe your symptoms').fill('Headache')
  await page.getByRole('button', { name: 'Send' }).click()
  await expect(page.getByText('Finding the right question to ask…')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Since today' })).toBeVisible({ timeout: 8000 })
})

test('failed page data offers a retry', async ({ page }) => {
  await setup(page)
  await page.route('http://api.test/doctors/search*', (route) => route.abort())
  await page.goto('/doctors')
  await expect(page.getByRole('heading', { name: 'You Appear to Be Offline' })).toBeVisible({ timeout: 10000 })
  await page.unroute('http://api.test/doctors/search*')
  await page.getByRole('button', { name: 'Try Again' }).click()
  await expect(page.getByRole('heading', { name: 'Dr. Kazi Ahmed' })).toBeVisible()
})

test('a doctor cannot add overlapping times', async ({ page }) => {
  const backend = await setup(page, { role: 'doctor' })
  await page.goto('/doctor/availability')
  await page.getByRole('button', { name: 'Add Time' }).first().click()
  const dialog = page.getByRole('dialog')
  const existing = backend.slots.find((slot) => slot.id === 'mine-1')
  const start = new Date(existing?.start_time ?? '')
  const day = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Dhaka' }).format(start)
  const time = new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Dhaka', hour: '2-digit', minute: '2-digit' }).format(start)
  await dialog.getByLabel('Day').fill(day)
  await dialog.getByLabel('Start Time').fill(time)
  await dialog.getByRole('button', { name: 'Add Time' }).click()
  await expect(dialog.getByText('This overlaps a time you’ve already added.')).toBeVisible()
})

test('patient can delete chat history and close their account', async ({ page }) => {
  await setup(page)
  await page.goto('/account')
  await page.getByRole('button', { name: 'Delete Chat History' }).click()
  await page.getByRole('dialog').getByRole('button', { name: 'Delete Chat History' }).click()
  await expect(page.getByText('Your chat history was deleted.').first()).toBeVisible()

  await page.getByRole('button', { name: 'Close Account' }).click()
  await page.getByRole('dialog').getByRole('button', { name: 'Close Account' }).click()
  await expect(page).toHaveURL('/')
  await expect(page.getByRole('link', { name: 'Sign In' })).toBeVisible()
})

test('the language switch changes the interface and survives a reload', async ({ page }) => {
  await setup(page, { signedIn: false })
  await page.goto('/')
  await page.getByRole('button', { name: 'বাংলা' }).click()
  await expect(page.locator('html')).toHaveAttribute('lang', 'bn')
  await expect(page.getByRole('link', { name: 'ডাক্তার খুঁজুন' }).first()).toBeVisible()
  await page.reload()
  await expect(page.locator('html')).toHaveAttribute('lang', 'bn')
  await page.getByRole('button', { name: 'English' }).click()
  await expect(page.locator('html')).toHaveAttribute('lang', 'en')
})

test('a first message typed on the home page reaches the chat', async ({ page }) => {
  await setup(page)
  await page.goto('/')
  await page.getByLabel('What are you feeling?').first().fill('Headache since yesterday')
  await page.getByRole('button', { name: 'Find my doctor' }).first().click()
  await expect(page.locator('#chat-input')).toHaveValue('Headache since yesterday')
  expect(page.url()).not.toContain('Headache')
})

test('a doctor sees no invented price, chooses a plan and sees what is owed', async ({ page }) => {
  const backend = await setup(page, { role: 'doctor' })
  await page.goto('/doctor/billing')
  await expect(page.getByText('Pricing is shared during onboarding.').first()).toBeVisible()

  backend.pricing = { booking_fee_bdt: 150, subscription_monthly_bdt: 2000 }
  await page.reload()
  await page.getByRole('radio', { name: /Monthly subscription/ }).click()
  await expect(page.getByRole('dialog')).toContainText('2,000')
  await page.getByRole('button', { name: 'Confirm plan' }).click()

  await expect(page.getByRole('radio', { name: /Monthly subscription/ })).toBeChecked()
  await expect(page.getByRole('cell', { name: 'Subscription for November 2026' })).toBeVisible()
  await expect(page.getByRole('table')).toContainText('2,000')
})

test('an admin sets prices and records a payment', async ({ page }) => {
  const backend = await setup(page, { role: 'admin' })
  await page.goto('/admin/billing')
  const fee = page.getByLabel('Fee per completed appointment (BDT)')
  await expect(fee).toHaveValue('')

  await fee.fill('12.5')
  await fee.blur()
  await expect(page.getByText('Enter a whole number from 1 to 1,000,000.')).toBeVisible()
  await fee.fill('150')
  await page.getByRole('button', { name: 'Save prices' }).click()
  await expect.poll(() => backend.pricing.booking_fee_bdt).toBe(150)
  expect(backend.pricing.subscription_monthly_bdt).toBeNull()

  backend.charges = [
    {
      id: 'c9',
      kind: 'booking_fee',
      billing_month: null,
      amount_bdt: 150,
      status: 'owed',
      created_at: '2026-11-06T06:00:00Z',
      settled_at: null,
      doctor_id: 'd1',
      doctor_name: 'Dr. Kazi Ahmed',
    },
  ]
  await page.reload()
  await page.getByRole('button', { name: 'Mark paid' }).click()
  await page.getByRole('dialog').getByRole('button', { name: 'Mark paid' }).click()
  await expect(page.getByRole('cell', { name: 'Paid' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Mark paid' })).toHaveCount(0)
})

test('the home page says patients pay nothing and the doctor page shows no invented price', async ({ page }) => {
  await setup(page, { signedIn: false })
  await page.goto('/')
  await expect(page.getByText('Free for patients', { exact: true })).toBeAttached()
  await page.getByRole('navigation', { name: 'Footer' }).getByRole('link', { name: 'For doctors' }).click()
  await expect(page).toHaveURL(/\/for-doctors$/)
  await expect(page.getByText('Pricing is shared during onboarding.')).toHaveCount(2)
  await page.getByRole('link', { name: 'Create a doctor account' }).click()
  await expect(page).toHaveURL(/role=doctor/)
})

test('a crisis message is calm, exact, and offers no doctors', async ({ page }) => {
  await setup(page)
  await page.goto('/chat')
  await page.getByLabel('Describe your symptoms').fill('I want to end my life')
  await page.getByRole('button', { name: 'Send' }).click()

  const notice = page.getByTestId('crisis-notice')
  await expect(notice).toBeVisible()
  await expect(notice).toHaveText(new RegExp(CRISIS_REPLY.split('\n')[0]))
  await expect(notice.getByRole('link', { name: 'Call 999 now' })).toHaveAttribute('href', 'tel:999')
  await expect(page.getByTestId('emergency-notice')).toHaveCount(0)
  await expect(notice).toHaveCSS('background-color', 'rgb(255, 255, 255)')
  await expect(page.getByRole('button', { name: 'Show me doctors now' })).toHaveCount(0)
})

test('a physical emergency keeps the red alert and offers no doctors', async ({ page }) => {
  await setup(page)
  await page.goto('/chat')
  await page.getByLabel('Describe your symptoms').fill('I have chest pain')
  await page.getByRole('button', { name: 'Send' }).click()
  await expect(page.getByTestId('emergency-notice')).toBeVisible()
  await expect(page.getByTestId('crisis-notice')).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Show me doctors now' })).toHaveCount(0)
})

test('the assistant offers its own answers, and doctors can be asked for at any time', async ({ page }) => {
  const backend = await setup(page)
  backend.chips = [{ label: 'Physical' }, { label: 'Emotional' }]
  await page.goto('/chat')
  await expect(page.getByRole('button', { name: 'Show me doctors now' })).toHaveCount(0)
  await page.getByLabel('Describe your symptoms').fill('I have a broken heart')
  await page.getByRole('button', { name: 'Send' }).click()

  await expect(page.getByRole('button', { name: 'Emotional' })).toBeVisible()
  await expect(page.getByRole('button', { name: '2 to 3 days' })).toHaveCount(0)
  await page.getByRole('button', { name: 'Show me doctors now' }).click()

  await expect(page.getByRole('article', { name: 'You said' }).last()).toHaveText(/Show me doctors now/)
  await expect(page.getByTestId('recommendation').first()).toBeVisible()
  await expect(page.getByRole('button', { name: 'Show me doctors now' })).toHaveCount(0)
})

test('correcting a form error does not lose the next click', async ({ page }) => {
  await setup(page, { signedIn: false })
  await page.goto('/login')
  const email = page.getByLabel('Email')
  await email.fill('not an email')
  await email.blur()
  await expect(page.locator('[aria-invalid="true"]')).toHaveCount(1)
  await email.fill('patient@example.com')
  await expect(page.locator('[aria-invalid="true"]')).toHaveCount(0)
})

