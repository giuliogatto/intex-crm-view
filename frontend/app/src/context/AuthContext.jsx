import React, { createContext, useContext, useEffect, useState } from 'react'
import { fetchCurrentUser, logout as authLogout } from '../utils/auth'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchCurrentUser()
      .then((currentUser) => setUser(currentUser))
      .finally(() => setLoading(false))
  }, [])

  const loginSuccess = (loggedInUser) => {
    setUser(loggedInUser)
  }

  const logout = () => {
    setUser(null)
    authLogout()
  }

  return (
    <AuthContext.Provider value={{ user, loading, loginSuccess, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
