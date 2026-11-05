const DRAWINGS = {
  calendar: (
    <>
      <rect x="10" y="16" width="44" height="38" rx="4" />
      <path d="M10 28h44M22 10v12M42 10v12" />
      <path className="text-primary" d="m24 41 6 6 11-12" />
    </>
  ),
  search: (
    <>
      <circle cx="28" cy="28" r="17" />
      <path className="text-primary" d="m41 41 13 13" />
      <path d="M21 28h14" />
    </>
  ),
  document: (
    <>
      <path d="M16 8h22l12 12v36H16z" />
      <path d="M38 8v12h12" />
      <path className="text-primary" d="m25 38 6 6 10-12" />
    </>
  ),
}

export type IllustrationName = keyof typeof DRAWINGS

export function Illustration({ name }: { name: IllustrationName }) {
  return (
    <svg
      aria-hidden
      viewBox="0 0 64 64"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="size-16 shrink-0 text-control"
    >
      {DRAWINGS[name]}
    </svg>
  )
}
