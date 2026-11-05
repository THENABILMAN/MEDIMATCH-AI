import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'

/** Sign-in and registration: the form on one side, a plain promise on an ink field. */
export function AuthFrame({ children }: { children: ReactNode }) {
  const { t } = useTranslation()
  return (
    <div className="grid flex-1 lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
      <aside className="on-ink hidden flex-col justify-end bg-ink-field p-12 lg:flex">
        <p className="max-w-[16ch] font-serif text-4xl">{t('auth.panelTitle')}</p>
        <p className="mt-4 max-w-[46ch] text-lg">{t('auth.panelBody')}</p>
      </aside>
      <div className="page-gutter py-8 md:py-16">
        <div className="mx-auto w-full max-w-md">{children}</div>
      </div>
    </div>
  )
}
