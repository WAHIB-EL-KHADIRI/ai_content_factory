import { createContext } from 'react'

export interface ToastContextType {
  toast: {
    success: (message: string) => void
    error: (message: string) => void
    warning: (message: string) => void
    info: (message: string) => void
  }
}

export const ToastContext = createContext<ToastContextType | null>(null)
