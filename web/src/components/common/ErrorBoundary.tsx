import React from 'react'
import { Alert } from './Alert'

interface ErrorBoundaryProps {
  children: React.ReactNode
}

interface ErrorBoundaryState {
  hasError: boolean
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false }

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true }
  }

  componentDidCatch(error: Error) {
    console.error('Page failed to render:', error)
  }

  render() {
    if (!this.state.hasError) {
      return this.props.children
    }

    return (
      <div className="mx-auto max-w-2xl space-y-3 p-6">
        <Alert
          type="error"
          message="This page could not be displayed. If you have a medical emergency, call 999 now."
        />
        <button
          onClick={() => window.location.reload()}
          className="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-bold text-white transition hover:bg-indigo-700"
        >
          Reload page
        </button>
      </div>
    )
  }
}
