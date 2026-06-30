import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import ChatsPage from './pages/ChatsPage.jsx'
import UsersPage from './pages/UsersPage.jsx'
import AnalisiPage from './pages/AnalisiPage.jsx'
import LoginPage from './pages/LoginPage.jsx'
import AdminGuard from './components/AdminGuard.jsx'
import { AuthProvider, useAuth } from './context/AuthContext.jsx'

function getAdminPage() {
  const pathname = window.location.pathname
  if (pathname === '/chats') return 'chats'
  if (pathname === '/users') return 'users'
  if (pathname === '/analisi') return 'analisi'
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

  if (adminPage === 'analisi') {
    return <AnalisiPage />
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
