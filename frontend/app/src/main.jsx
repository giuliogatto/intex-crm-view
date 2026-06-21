import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import ChatsPage from './pages/ChatsPage.jsx'
import LoginPage from './pages/LoginPage.jsx'
import { AuthProvider, useAuth } from './context/AuthContext.jsx'

const isChatsPage = window.location.pathname === '/chats'

function AppRoot() {
  const { user, loading } = useAuth()

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

  return isChatsPage ? <ChatsPage /> : <App />
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <AuthProvider>
      <AppRoot />
    </AuthProvider>
  </StrictMode>,
)
