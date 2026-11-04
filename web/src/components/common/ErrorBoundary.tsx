import { Component, type ErrorInfo, type ReactNode } from 'react'
import i18n from '../../lib/i18n'
import { Banner } from '../ui/banner'
import { Button } from '../ui/button'

interface ErrorBoundaryProps {
  children: ReactNode
}

interface ErrorBoundaryState {
  hasError: boolean
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false }

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.warn('Page failed to render:', error, info.componentStack)
  }

  render() {
    if (!this.state.hasError) return this.props.children

    return (
      <div className="page-gutter py-8">
        <Banner tone="warning" title={i18n.t('errors.crashTitle')}>
          <p>{i18n.t('errors.crashBody')}</p>
        </Banner>
        <Button variant="secondary" className="mt-4" onClick={() => window.location.reload()}>
          {i18n.t('errors.reload')}
        </Button>
      </div>
    )
  }
}
