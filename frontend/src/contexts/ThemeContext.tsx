import { useState, useEffect, useCallback, ReactNode } from 'react'
import { Theme, ThemeContext } from './theme-context'

function getSystemTheme(): 'light' | 'dark' {
  if (typeof window === 'undefined') return 'dark'
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function applyTheme(theme: 'light' | 'dark') {
  const root = document.documentElement
  if (theme === 'dark') {
    root.classList.add('dark')
  } else {
    root.classList.remove('dark')
  }
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(() => {
    try {
      return (localStorage.getItem('theme') as Theme) || 'dark'
    } catch {
      return 'dark'
    }
  })
  const [effectiveTheme, setEffectiveTheme] = useState<'light' | 'dark'>(() =>
    theme === 'system' ? getSystemTheme() : theme
  )

  useEffect(() => {
    const media = window.matchMedia('(prefers-color-scheme: dark)')
    const handler = () => {
      if (theme === 'system') {
        const next = getSystemTheme()
        setEffectiveTheme(next)
        applyTheme(next)
      }
    }
    media.addEventListener('change', handler)
    return () => media.removeEventListener('change', handler)
  }, [theme])

  useEffect(() => {
    const next = theme === 'system' ? getSystemTheme() : theme
    setEffectiveTheme(next)
    applyTheme(next)
    try {
      localStorage.setItem('theme', theme)
    } catch { /* ignore */ }
  }, [theme])

  const setTheme = useCallback((t: Theme) => setThemeState(t), [])

  const toggleTheme = useCallback(() => {
    setThemeState(prev => {
      if (prev === 'dark') return 'light'
      if (prev === 'light') return 'system'
      return 'dark'
    })
  }, [])

  return (
    <ThemeContext.Provider value={{ theme, effectiveTheme, setTheme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}
