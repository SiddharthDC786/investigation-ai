import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'

const STORAGE_KEY = 'vigil_presentation_mode'

interface PresentationModeContextValue {
  enabled: boolean
  toggle: () => void
}

const PresentationModeContext = createContext<PresentationModeContextValue | null>(null)

export function PresentationModeProvider({ children }: { children: ReactNode }) {
  const [enabled, setEnabled] = useState(() => {
    try {
      return localStorage.getItem(STORAGE_KEY) === '1'
    } catch {
      return false
    }
  })

  useEffect(() => {
    document.documentElement.classList.toggle('presentation-mode', enabled)
    try {
      localStorage.setItem(STORAGE_KEY, enabled ? '1' : '0')
    } catch {
      /* ignore */
    }
  }, [enabled])

  return (
    <PresentationModeContext.Provider
      value={{
        enabled,
        toggle: () => setEnabled((v) => !v),
      }}
    >
      {children}
    </PresentationModeContext.Provider>
  )
}

export function usePresentationMode() {
  const ctx = useContext(PresentationModeContext)
  if (!ctx) throw new Error('usePresentationMode must be used within PresentationModeProvider')
  return ctx
}
