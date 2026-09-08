import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import { AuthProvider } from './auth/AuthContext'
import { LanguageProvider } from './i18n/LanguageContext'
import { PresentationModeProvider } from './i18n/PresentationModeContext'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <LanguageProvider>
      <PresentationModeProvider>
        <AuthProvider>
          <App />
        </AuthProvider>
      </PresentationModeProvider>
    </LanguageProvider>
  </StrictMode>,
)
