import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const css = readFileSync('src/styles/tokens.css', 'utf8')

function token(name: string): string {
  const match = new RegExp(`--${name}:\\s*(#[0-9a-f]{6})`, 'i').exec(css)
  if (!match) throw new Error(`Missing token ${name}`)
  return match[1]
}

function luminance(hex: string): number {
  const channels = [1, 3, 5].map((start) => parseInt(hex.slice(start, start + 2), 16) / 255)
  const [r, g, b] = channels.map((value) => (value <= 0.03928 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4))
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

function contrast(foreground: string, background: string): number {
  const [light, dark] = [luminance(foreground), luminance(background)].sort((a, b) => b - a)
  return (light + 0.05) / (dark + 0.05)
}

const WHITE = '#ffffff'

const TEXT_PAIRS: [string, string][] = [
  ['ink', 'surface'],
  ['ink', 'canvas'],
  ['ink', 'primary-tint'],
  ['ink', 'ai-tint'],
  ['muted', 'surface'],
  ['muted', 'canvas'],
  ['muted', 'primary-tint'],
  ['muted', 'ai-tint'],
  ['primary', 'surface'],
  ['primary', 'canvas'],
  ['primary-hover', 'primary-tint'],
  ['ai', 'surface'],
  ['ai', 'ai-tint'],
  ['danger', 'surface'],
  ['danger', 'danger-tint'],
  ['warning', 'surface'],
  ['warning', 'warning-tint'],
  ['success', 'surface'],
  ['success', 'success-tint'],
]

describe('design tokens meet WCAG AA', () => {
  it.each(TEXT_PAIRS)('%s text on %s', (foreground, background) => {
    expect(contrast(token(foreground), token(background))).toBeGreaterThanOrEqual(4.5)
  })

  it.each(['primary', 'primary-hover', 'primary-pressed', 'danger', 'danger-pressed'])('white text on %s', (background) => {
    expect(contrast(WHITE, token(background))).toBeGreaterThanOrEqual(4.5)
  })

  it.each(['surface', 'canvas'])('control borders stand out on %s', (background) => {
    expect(contrast(token('border-control'), token(background))).toBeGreaterThanOrEqual(3)
  })
})
