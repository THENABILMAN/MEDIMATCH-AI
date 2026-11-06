import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { ProductStage } from '../domain/product-stage'

/** Sign-in and registration: the form on one side, and the product it leads to on the other. */
export function AuthFrame({ children }: { children: ReactNode }) {
  const { t } = useTranslation()
  return (
    <div className="grid flex-1 lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
      <aside className="hidden items-center justify-center bg-primary-tint p-12 lg:flex">
        <div className="flex w-full max-w-[520px] flex-col gap-8">
          <div>
            <p className="heading-3">{t('auth.panelTitle')}</p>
            <p className="mt-3 body-7">{t('auth.panelBody')}</p>
          </div>
          <ProductStage step={2} compact />
        </div>
      </aside>
      <div className="page-gutter py-8 md:py-16">
        <div className="mx-auto w-full max-w-md">{children}</div>
      </div>
    </div>
  )
}
