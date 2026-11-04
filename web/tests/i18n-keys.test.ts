import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import en from '../src/locales/en.json'

function flatten(value: object, prefix = ''): string[] {
  return Object.entries(value).flatMap(([key, entry]) =>
    typeof entry === 'object' ? flatten(entry as object, `${prefix}${key}.`) : [`${prefix}${key}`]
  )
}

function sourceFiles(directory: string): string[] {
  return readdirSync(directory).flatMap((name) => {
    const path = join(directory, name)
    if (statSync(path).isDirectory()) return name === 'dev' ? [] : sourceFiles(path)
    return /\.tsx?$/.test(name) ? [path] : []
  })
}

const known = new Set(flatten(en).map((key) => key.replace(/_(one|other)$/, '')))
const source = sourceFiles('src').map((path) => readFileSync(path, 'utf8'))

describe('translation keys', () => {
  it('every static key exists in English', () => {
    const used = source.flatMap((text) => [
      ...[...text.matchAll(/\bt\(\s*'([\w.]+)'/g)].map((match) => match[1]),
      ...[...text.matchAll(/'((?:nav|chat\.suggest)\.[\w]+)'/g)].map((match) => match[1]),
    ])
    expect(used.length).toBeGreaterThan(200)
    expect(used.filter((key) => !known.has(key))).toEqual([])
  })

  it('every dynamic key matches at least one English key', () => {
    const patterns = source.flatMap((text) => [...text.matchAll(/\bt\(\s*`([^`]+)`/g)].map((match) => match[1]))
    expect(patterns.length).toBeGreaterThan(10)
    const missing = patterns.filter((pattern) => {
      const regex = new RegExp(`^${pattern.replace(/\./g, '\\.').replace(/\$\{[^}]+\}/g, '[\\w]+')}$`)
      return ![...known].some((key) => regex.test(key))
    })
    expect(missing).toEqual([])
  })
})
