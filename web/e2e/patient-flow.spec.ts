import { expect, test } from '@playwright/test'

test.describe('Patient End-to-End Discovery and Booking Flow', () => {
  test('patient lands on home page, navigates to doctor search, views profile and available slots', async ({
    page,
  }) => {
    // 1. Visit Home Page
    await page.goto('/')
    await expect(page).toHaveTitle(/MediMatch/i)
    await expect(page.getByText('Describe your symptoms.')).toBeVisible()

    // 2. Click "Browse Verified Specialists"
    await page.getByRole('link', { name: /Browse Verified Specialists/i }).click()
    await expect(page).toHaveURL(/\/doctors/)
    await expect(page.getByText('Find Verified Medical Specialists')).toBeVisible()

    // 3. Verify doctors list loads and click "Book Slot" on first doctor
    const bookButtons = page.getByRole('link', { name: /Book Slot/i })
    await expect(bookButtons.first()).toBeVisible()
    await bookButtons.first().click()

    // 4. On Doctor Detail page, check doctor information & available appointment slots
    await expect(page.getByText('Available Appointment Slots')).toBeVisible()
    await expect(page.getByText('Verified')).toBeVisible()
  })

  test('patient logs in and views symptom assistant chat disclaimer', async ({ page }) => {
    // 1. Visit Login
    await page.goto('/login')
    await expect(page.getByText('Sign in to MediMatch AI')).toBeVisible()

    // 2. Fill demo patient login
    await page.getByRole('button', { name: /👤 Patient/i }).click()
    await page.getByRole('button', { name: /Sign In/i }).click()

    // 3. Should navigate to authenticated view with disclaimer banner visible
    await expect(page.getByTestId('disclaimer-banner')).toBeVisible({ timeout: 10000 })
  })
})

