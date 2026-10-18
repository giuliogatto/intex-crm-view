import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import ChatsPage from './pages/ChatsPage.jsx'
import UsersPage from './pages/UsersPage.jsx'
import SinonimiPage from './pages/SinonimiPage.jsx'
import OcrBollePage from './pages/OcrBollePage.jsx'
import LogsPage from './pages/LogsPage.jsx'
import AdminGuard from './components/AdminGuard.jsx'
import LoginPage from './pages/LoginPage.jsx'
import { AuthProvider, useAuth } from './context/AuthContext.jsx'

function getAdminPage() {
  const pathname = window.location.pathname
  if (pathname === '/chats') return 'chats'
  if (pathname === '/users') return 'users'
  if (pathname === '/sinonimi') return 'sinonimi'
  if (pathname === '/ocr-bolle') return 'ocr-bolle'
  if (pathname === '/logs') return 'logs'
  return null
}

function AppRoot() {
  const { user, loading } = useAuth()
  const adminPage = getAdminPage()

  if (loading) {
    return (
      <div className="login-page">
        <div className="loading-indicator">
          <div className="spinner" />
          <span>Verifica sessione...</span>
        </div>
      </div>
    )
  }

  if (!user) {
    return <LoginPage />
  }

  if (adminPage === 'chats') {
    return (
      <AdminGuard>
        <ChatsPage />
      </AdminGuard>
    )
  }

  if (adminPage === 'users') {
    return (
      <AdminGuard>
        <UsersPage />
      </AdminGuard>
    )
  }

  if (adminPage === 'sinonimi') {
    return (
      <AdminGuard>
        <SinonimiPage />
      </AdminGuard>
    )
  }

  if (adminPage === 'ocr-bolle') {
    return (
      <AdminGuard>
        <OcrBollePage />
      </AdminGuard>
    )
  }

  if (adminPage === 'logs') {
    return (
      <AdminGuard>
        <LogsPage />
      </AdminGuard>
    )
  }

  return <App />
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <AuthProvider>
      <AppRoot />
    </AuthProvider>
  </StrictMode>,
)
