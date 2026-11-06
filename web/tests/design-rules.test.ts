import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import en from '../src/locales/en.json'

function files(directory: string): string[] {
  return readdirSync(directory).flatMap((name) => {
    const path = join(directory, name)
    if (statSync(path).isDirectory()) return files(path)
    return /\.(tsx|css)$/.test(name) ? [path] : []
  })
}

function strings(value: object): string[] {
  return Object.values(value).flatMap((entry) => (typeof entry === 'object' ? strings(entry as object) : [entry as string]))
}

const source = files('src').map((path) => ({ path, text: readFileSync(path, 'utf8') }))
const markup = source.filter(({ path }) => path.endsWith('.tsx'))

function offenders(pattern: RegExp, within = markup): string[] {
  return within.flatMap(({ path, text }) => [...text.matchAll(pattern)].map((match) => `${path}: ${match[0]}`))
}

describe('the visual system in docs/DESIGN.md', () => {
  it('uses named text styles, never a loose size or weight', () => {
    expect(offenders(/(?<![\w-])(text-(xs|sm|base|lg|[0-9]?xl)|font-(serif|normal|medium|semibold|bold|black))\b/g)).toEqual([])
  })

  it('uses only the spacing table', () => {
    const spacing = /(?<![\w-])(?:[\w[\]=-]+:)*-?(?:p|px|py|pt|pb|pl|pr|m|mx|my|mt|mb|ml|mr|gap-x|gap-y|gap)-(?![xy]-|(?:0|0\.5|1|2|3|4|6|8|10|12|16|20|24|px|auto)\b|\[env)[\w.[\]-]+/g
    expect(offenders(spacing)).toEqual([])
  })

  it('has one approved typeface, no italics and no gradients on backgrounds', () => {
    expect(offenders(/\bitalic\b|bg-gradient|bg-linear/g)).toEqual([])
    expect(offenders(/font-family: '(?!Manrope|Noto Sans Bengali)[^']+'/g, source)).toEqual([])
  })

  it('takes icons from Phosphor', () => {
    expect(offenders(/lucide|material-(icons|symbols)/gi, source)).toEqual([])
  })

  it('never uses a browser default curve', () => {
    expect(offenders(/ease-(in|out|in-out|linear)\b|\b(ease|linear|ease-in-out) \d|\d+m?s (ease|linear)\b/g, source)).toEqual([])
  })
})

describe('copy in the English locale', () => {
  const copy = strings(en)

  it('has no hyphens inside text', () => {
    expect(copy.filter((text) => /\w-\w|\s-\s/.test(text))).toEqual([])
  })

  it('has no exclamation marks or banned filler words', () => {
    const banned = /!|revolutioni[sz]e|supercharge|cutting edge|effortless|transform your workflow|next level|harness the power|world class/i
    expect(copy.filter((text) => banned.test(text))).toEqual([])
  })
})
