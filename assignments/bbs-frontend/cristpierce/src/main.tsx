import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './styles/global.css'
import { App } from './App'
import { ThemeProvider } from './context/ThemeContext'
import { IdentityProvider } from './context/IdentityContext'
import { ToastProvider } from './context/ToastContext'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider>
      <IdentityProvider>
        <ToastProvider>
          <App />
        </ToastProvider>
      </IdentityProvider>
    </ThemeProvider>
  </StrictMode>,
)
