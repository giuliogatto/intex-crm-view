import React, { useState } from 'react'
import { login } from '../utils/auth'
import { useAuth } from '../context/AuthContext'

export default function LoginPage() {
  const { loginSuccess } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setSubmitting(true)

    try {
      const user = await login(username.trim(), password)
      loginSuccess(user)
    } catch (err) {
      setError(err.message || 'Accesso non riuscito')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-card__header">
          <img src="/logo.webp" alt="Intex" className="login-logo" />
          <p>Accedi per consultare i dati ERP</p>
        </div>

        <form className="login-form" onSubmit={handleSubmit}>
          <label className="login-form__field">
            <span>Email / Username</span>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              required
              disabled={submitting}
            />
          </label>

          <label className="login-form__field">
            <span>Password</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
              disabled={submitting}
            />
          </label>

          {error && <p className="login-form__error">{error}</p>}

          <button type="submit" className="btn btn--primary login-form__submit" disabled={submitting}>
            {submitting ? 'Accesso in corso...' : 'Accedi'}
          </button>
        </form>
      </div>
    </div>
  )
}
