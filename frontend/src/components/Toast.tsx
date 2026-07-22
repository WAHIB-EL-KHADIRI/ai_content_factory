import { useState, useCallback, ReactNode } from 'react'
import { X, CheckCircle, AlertCircle, AlertTriangle, Info } from 'lucide-react'
import { ToastContext } from './toast-context'

type ToastType = 'success' | 'error' | 'warning' | 'info'

interface Toast {
  id: string
  type: ToastType
  message: string
  visible: boolean
}

const icons: Record<ToastType, typeof CheckCircle> = {
  success: CheckCircle,
  error: AlertCircle,
  warning: AlertTriangle,
  info: Info,
}

const styles: Record<ToastType, string> = {
  success: 'border-green-800 bg-green-900/80 text-green-200',
  error: 'border-red-800 bg-red-900/80 text-red-200',
  warning: 'border-yellow-800 bg-yellow-900/80 text-yellow-200',
  info: 'border-blue-800 bg-blue-900/80 text-blue-200',
}

let toastCounter = 0

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const addToast = useCallback((type: ToastType, message: string) => {
    const id = `toast-${++toastCounter}`
    setToasts(prev => [...prev, { id, type, message, visible: false }])
    requestAnimationFrame(() => {
      setToasts(prev =>
        prev.map(t => (t.id === id ? { ...t, visible: true } : t))
      )
    })
    setTimeout(() => {
      setToasts(prev =>
        prev.map(t => (t.id === id ? { ...t, visible: false } : t))
      )
      setTimeout(() => {
        setToasts(prev => prev.filter(t => t.id !== id))
      }, 300)
    }, 5000)
  }, [])

  const dismiss = useCallback((id: string) => {
    setToasts(prev =>
      prev.map(t => (t.id === id ? { ...t, visible: false } : t))
    )
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id))
    }, 300)
  }, [])

  const toast = {
    success: (message: string) => addToast('success', message),
    error: (message: string) => addToast('error', message),
    warning: (message: string) => addToast('warning', message),
    info: (message: string) => addToast('info', message),
  }

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col-reverse gap-3 max-w-sm w-full pointer-events-none">
        {toasts.map(t => {
          const Icon = icons[t.type]
          return (
            <div
              key={t.id}
              className={`pointer-events-auto flex items-start gap-3 p-4 rounded-xl border shadow-2xl backdrop-blur-sm transition-all duration-300 ${styles[t.type]} ${
                t.visible
                  ? 'opacity-100 translate-x-0'
                  : 'opacity-0 translate-x-full'
              }`}
            >
              <Icon size={20} className="flex-shrink-0 mt-0.5" />
              <p className="text-sm flex-1">{t.message}</p>
              <button
                onClick={() => dismiss(t.id)}
                className="flex-shrink-0 p-0.5 rounded hover:bg-white/10 transition-colors"
              >
                <X size={14} />
              </button>
            </div>
          )
        })}
      </div>
    </ToastContext.Provider>
  )
}
