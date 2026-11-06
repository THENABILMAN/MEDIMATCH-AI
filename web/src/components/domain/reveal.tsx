import { useEffect, useRef, type ReactNode } from 'react'

/**
 * Writes how far the page has scrolled through an element to a CSS variable, from 0 to 1.
 * It runs at most once a frame, and CSS decides what the number moves.
 */
export function useScrollProgress<T extends HTMLElement>(
  variable: string,
  measure: (box: DOMRect, screenHeight: number) => number
) {
  const root = useRef<T>(null)

  useEffect(() => {
    const element = root.current
    if (!element) return
    let frame = 0

    function update() {
      frame = 0
      const progress = measure(element!.getBoundingClientRect(), window.innerHeight)
      element!.style.setProperty(variable, Math.min(Math.max(progress, 0), 1).toFixed(4))
    }

    function schedule() {
      if (!frame) frame = requestAnimationFrame(update)
    }

    update()
    window.addEventListener('scroll', schedule, { passive: true })
    window.addEventListener('resize', schedule)
    return () => {
      cancelAnimationFrame(frame)
      window.removeEventListener('scroll', schedule)
      window.removeEventListener('resize', schedule)
    }
  }, [variable, measure])

  return root
}

/** A section rises into place the first time it enters the screen, and stays. */
export function Reveal({ children, className }: { children: ReactNode; className?: string }) {
  const root = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const element = root.current
    if (!element) return
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) return
        element.dataset.shown = ''
        observer.disconnect()
      },
      { rootMargin: '0px 0px -10% 0px' }
    )
    observer.observe(element)
    return () => observer.disconnect()
  }, [])

  return (
    <div ref={root} className={['reveal', className].filter(Boolean).join(' ')}>
      {children}
    </div>
  )
}

// The block is read between these two lines of the screen, as fractions of its height
const START_LINE = 0.85
const END_LINE = 0.45

/** Large type whose words come to full colour one at a time as it scrolls past. */
export function TaglineReveal({ lines }: { lines: string[] }) {
  const root = useRef<HTMLParagraphElement>(null)

  useEffect(() => {
    const element = root.current
    if (!element) return
    const words = [...element.querySelectorAll<HTMLElement>('.tagline-word')]
    let frame = 0
    let lit = 0

    function update() {
      frame = 0
      const box = element!.getBoundingClientRect()
      const travel = box.height + window.innerHeight * (START_LINE - END_LINE)
      const progress = (window.innerHeight * START_LINE - box.top) / travel
      const reached = Math.round(Math.min(Math.max(progress, 0), 1) * words.length)
      // Words stay lit once read, so scrolling back never dims the text
      for (; lit < reached; lit += 1) words[lit].dataset.on = ''
    }

    function schedule() {
      if (!frame) frame = requestAnimationFrame(update)
    }

    update()
    window.addEventListener('scroll', schedule, { passive: true })
    window.addEventListener('resize', schedule)
    return () => {
      cancelAnimationFrame(frame)
      window.removeEventListener('scroll', schedule)
      window.removeEventListener('resize', schedule)
    }
  }, [])

  return (
    <p ref={root} className="heading-3 mx-auto max-w-[680px] text-center md:heading-2">
      {lines.map((line) => (
        <span key={line} className="block">
          {line.split(' ').map((word, index) => (
            <span key={`${word}-${index}`}>
              <span className="tagline-word">{word}</span>{' '}
            </span>
          ))}
        </span>
      ))}
    </p>
  )
}
