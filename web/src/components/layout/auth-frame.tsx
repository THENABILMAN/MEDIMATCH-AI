import { Check } from 'lucide-react'
import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'

const POINTS = ['verified', 'fees', 'cancel'] as const

/** Sign-in and registration: the form on paper, the promise on a navy slip beside it. */
export function AuthFrame({ children }: { children: ReactNode }) {
  const { t } = useTranslation()
  return (
    <div className="page-gutter grid flex-1 gap-8 py-6 md:py-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] lg:items-stretch">
      <div className="flex w-full max-w-md flex-col justify-center justify-self-center">{children}</div>
      <aside className="slip on-navy relative hidden overflow-hidden bg-navy lg:flex lg:min-h-[640px] lg:flex-col lg:justify-end">
        <img
          src="/images/rickshaws.webp"
          alt=""
          width={1600}
          height={1067}
          className="absolute inset-x-0 top-0 h-1/2 w-full object-cover"
        />
        <div className="relative p-10">
          <p className="display-2">{t('auth.panelTitle')}</p>
          <p className="mt-4 max-w-[46ch] text-lg">{t('auth.panelBody')}</p>
          <ul className="mt-6 flex flex-col gap-2">
            {POINTS.map((point) => (
              <li key={point} className="flex items-center gap-2">
                <Check aria-hidden className="size-5 shrink-0" strokeWidth={2} />
                {t(`auth.panelPoints.${point}`)}
              </li>
            ))}
          </ul>
        </div>
      </aside>
    </div>
  )
}
