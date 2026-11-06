import { type ClassValue, clsx } from 'clsx'
import { extendTailwindMerge } from 'tailwind-merge'

const count = (name: string, last: number) => Array.from({ length: last }, (_, index) => `${name}-${index + 1}`)

const TEXT_STYLES = [
  ...count('heading', 6),
  ...count('title', 5),
  ...count('body', 8),
  ...count('caption', 5),
  'button-lg',
  'button-md',
  'button-sm',
  'button-xsm',
]

const twMerge = extendTailwindMerge({
  extend: { classGroups: { 'font-size': TEXT_STYLES } },
})

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}
