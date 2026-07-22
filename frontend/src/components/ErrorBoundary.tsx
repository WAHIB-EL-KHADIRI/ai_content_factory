import { Component, ErrorInfo, ReactNode } from 'react'
import { AlertTriangle, RefreshCw, ExternalLink } from 'lucide-react'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo)
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-gray-950 flex items-center justify-center p-8">
          <div className="max-w-md w-full text-center space-y-6">
            <div className="flex justify-center">
              <div className="p-4 rounded-full bg-red-900/20 border border-red-800">
                <AlertTriangle className="text-red-400" size={48} />
              </div>
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-100">Something went wrong</h1>
              <p className="text-gray-400 mt-2">
                An unexpected error occurred. Our team has been notified.
              </p>
            </div>
            {this.state.error && (
              <details className="text-left card">
                <summary className="text-sm font-medium text-gray-400 cursor-pointer select-none">
                  Error details
                </summary>
                <pre className="mt-3 text-xs text-red-400 whitespace-pre-wrap break-words overflow-auto max-h-40">
                  {this.state.error.message}
                  {this.state.error.stack && `\n\n${this.state.error.stack}`}
                </pre>
              </details>
            )}
            <div className="flex items-center justify-center gap-3">
              <button onClick={this.handleRetry} className="btn-primary flex items-center gap-2">
                <RefreshCw size={16} />
                Try Again
              </button>
              <a
                href="https://github.com/WAHIB-EL-KHADIRI/ai_content_factory/issues"
                target="_blank"
                rel="noopener noreferrer"
                className="btn-secondary flex items-center gap-2"
              >
                <ExternalLink size={16} />
                Report Issue
              </a>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
