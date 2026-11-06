import { expect, test, type Page } from '@playwright/test'
import { setup } from './support/mock-backend'

async function tabTo(page: Page, name: RegExp, limit = 40) {
  for (let step = 0; step < limit; step += 1) {
    await page.keyboard.press('Tab')
    const label = await page.evaluate(() => {
      const element = document.activeElement as HTMLElement | null
      // With nothing focused, the body's text would match any label on the page
      if (!element || element === document.body) return ''
      const labelled = element?.getAttribute('aria-label')
      const byFor = element?.id ? document.querySelector(`label[for="${element.id}"]`)?.textContent : null
      return labelled ?? byFor ?? element?.textContent ?? ''
    })
    if (name.test(label)) return
  }
  throw new Error(`Could not reach ${name} with Tab`)
}

test('the skip link moves focus to the main content', async ({ page }) => {
  await setup(page, { signedIn: false })
  await page.goto('/')
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
  await page.keyboard.press('Tab')
  await expect(page.getByRole('link', { name: 'Skip to Content' })).toBeFocused()
  await page.keyboard.press('Enter')
  await expect(page).toHaveURL(/#main/)
})

test('sign in with the keyboard', async ({ page }) => {
  await setup(page, { signedIn: false })
  await page.goto('/login')
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
  await tabTo(page, /^Email$/)
  await page.keyboard.type('patient@medimatch.test')
  await page.keyboard.press('Tab')
  await page.keyboard.type('Patient123!Safe')
  await page.keyboard.press('Enter')
  await expect(page).toHaveURL(/\/chat/)
})

test('send a chat message with the keyboard', async ({ page }) => {
  await setup(page)
  await page.goto('/chat')
  await expect(page.getByText('Hello! I am your MediMatch Assistant.', { exact: false })).toBeVisible()
  await tabTo(page, /Describe your symptoms/i)
  await page.keyboard.type('Headache and dizziness')
  await page.keyboard.press('Enter')
  await expect(page.getByRole('button', { name: 'Since today' })).toBeVisible()
})

test('book a slot with the keyboard', async ({ page }) => {
  await setup(page)
  await page.goto('/doctors/d1')
  const times = page.getByRole('radiogroup', { name: 'Choose a time' }).getByRole('radio')
  await expect(times.first()).toBeVisible()

  await tabTo(page, /^(?!.*Skip)[\d:]+\s?(am|pm)$/i)
  await page.keyboard.press('Space')
  await expect(page).toHaveURL(/slot=/)
  await tabTo(page, /Book This Slot/i)
  await page.keyboard.press('Enter')
  await expect(page.getByRole('dialog')).toBeVisible()
  await tabTo(page, /Confirm Booking/i, 6)
  await page.keyboard.press('Enter')
  await expect(page).toHaveURL(/\/appointments/)
})

test('approve a doctor with the keyboard', async ({ page }) => {
  await setup(page, { role: 'admin' })
  await page.goto('/admin/queue')
  await expect(page.getByRole('link', { name: /Dr. Jamil Pending/i })).toBeVisible()
  await tabTo(page, /Dr. Jamil Pending/i)
  await page.keyboard.press('Enter')
  await expect(page).toHaveURL(/doctor=p1/)
  await tabTo(page, /^Approve$/)
  await page.keyboard.press('Enter')
  await tabTo(page, /^Approve$/, 6)
  await page.keyboard.press('Enter')
  await expect(page.getByText('Dr. Jamil Pending was approved.').first()).toBeVisible()
})
