import { expect, test } from '@playwright/test'
import { setup } from './support/mock-backend'

test('at 390px the primary action is on the first screen with nothing overflowing', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await setup(page, { signedIn: false })
  await page.goto('/')
  const action = page.getByRole('button', { name: 'Find my doctor' }).first()
  await expect(action).toBeInViewport({ ratio: 1 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(0)
  await page.screenshot({ path: 'screenshots/after/landing/first-screen-390.png' })
})

test('the desktop hero has one main action and its heading is capped at 680px', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await setup(page, { signedIn: false })
  await page.goto('/')
  await expect(page.getByRole('button', { name: 'Find my doctor' }).first()).toBeInViewport({ ratio: 1 })
  await expect(page.getByRole('link', { name: 'Create account' })).toHaveCount(0)
  const heading = await page.getByRole('heading', { level: 1 }).boundingBox()
  expect(heading?.width).toBeLessThanOrEqual(680)
  await page.screenshot({ path: 'screenshots/after/landing/first-screen-1440.png' })
})

test('tagline words light one at a time as it scrolls, and stay lit', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await setup(page, { signedIn: false })
  await page.goto('/')
  const words = page.locator('.tagline-word')
  const lit = page.locator('.tagline-word[data-on]')
  await expect(words.first()).toBeAttached()
  const total = await words.count()
  expect(total).toBeGreaterThan(6)
  await expect(lit).toHaveCount(0)

  const seen = new Set<number>()
  const top = await page.locator('.tagline-word').first().evaluate((node) => node.getBoundingClientRect().top + window.scrollY)
  for (let offset = 900; offset >= 200; offset -= 20) {
    await page.evaluate((y) => window.scrollTo(0, y), top - offset)
    await page.waitForTimeout(40)
    seen.add(await lit.count())
  }
  expect(seen.size, 'the block must not flip all at once').toBeGreaterThan(3)
  await expect(lit).toHaveCount(total)

  await page.evaluate(() => window.scrollTo(0, 0))
  await page.waitForTimeout(100)
  await expect(lit).toHaveCount(total)
})

test('a section reveals once and stays revealed', async ({ page }) => {
  await setup(page, { signedIn: false })
  await page.goto('/')
  const section = page.locator('.reveal').first()
  await expect(section).not.toHaveAttribute('data-shown')
  await section.scrollIntoViewIfNeeded()
  await expect(section).toHaveAttribute('data-shown', '')
  await page.evaluate(() => window.scrollTo(0, 0))
  await expect(section).toHaveAttribute('data-shown', '')
})

test('under reduced motion, nothing rises and the tagline is at full colour', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await setup(page, { signedIn: false })
  await page.goto('/')
  const word = page.locator('.tagline-word').first()
  await expect(word).toHaveCSS('opacity', '1')
  await expect(page.locator('.reveal').first()).toHaveCSS('transform', 'none')
})

test('the mobile menu is a full height panel whose links arrive in order', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await setup(page)
  await page.goto('/doctors')
  await page.getByRole('button', { name: 'Open menu' }).click()
  const panel = page.getByRole('dialog')
  await expect(panel).toBeVisible()
  const box = await panel.boundingBox()
  expect(box?.height).toBe(844)
  expect(box?.width).toBe(390)
  const delays = await panel.getByRole('navigation').getByRole('link').evaluateAll((links) =>
    links.map((link) => parseFloat(getComputedStyle(link).animationDelay))
  )
  expect(delays).toEqual([...delays].sort((a, b) => a - b))
  expect(Math.max(...delays)).toBeLessThanOrEqual(0.4)
  await page.waitForTimeout(800)
  await page.screenshot({ path: 'screenshots/after/landing/menu-390.png' })
})

test('every footer link leads somewhere', async ({ page }) => {
  await setup(page, { signedIn: false })
  await page.goto('/')
  const footer = page.getByRole('navigation', { name: 'Footer' })
  await footer.getByRole('link', { name: 'Terms of use' }).click()
  await expect(page.getByRole('heading', { name: 'Terms of use' })).toBeVisible()
  await page.getByRole('navigation', { name: 'Footer' }).getByRole('link', { name: 'Privacy policy' }).click()
  await expect(page.getByRole('heading', { name: 'Privacy policy' })).toBeVisible()
  await expect(page).toHaveTitle(/Privacy policy/)
})

test('the hero sinks back and the how it works bar follows the scroll', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await setup(page, { signedIn: false })
  await page.goto('/')
  const hero = page.locator('.hero-scroll')
  await expect(hero).toBeVisible()
  await expect(hero).toHaveCSS('opacity', '1')

  await page.evaluate(() => window.scrollTo(0, window.innerHeight / 2))
  await expect.poll(async () => Number(await hero.evaluate((node) => getComputedStyle(node).opacity))).toBeLessThan(0.9)

  const bar = page.locator('[data-stage-bar]').first()
  const width = () => bar.evaluate((node) => node.getBoundingClientRect().width)
  const top = await page.locator('#how-title').evaluate((node) => node.getBoundingClientRect().top + window.scrollY)
  await page.evaluate((y) => window.scrollTo(0, y), top + 100)
  await expect.poll(width).toBeGreaterThan(0)
  const early = await width()
  await page.evaluate((y) => window.scrollTo(0, y), top + 250)
  await expect.poll(width).toBeGreaterThan(early)
})

test('under reduced motion, the hero stays still while the page scrolls', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await setup(page, { signedIn: false })
  await page.goto('/')
  const hero = page.locator('.hero-scroll')
  await expect(hero).toBeVisible()
  await page.evaluate(() => window.scrollTo(0, 400))
  await page.waitForTimeout(100)
  await expect(hero).toHaveCSS('transform', 'none')
  await expect(hero).toHaveCSS('opacity', '1')
})
