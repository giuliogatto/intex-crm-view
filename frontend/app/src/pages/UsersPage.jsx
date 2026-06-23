import React, { useState, useEffect, useCallback } from 'react'
import { authFetch } from '../utils/auth'
import UserMenu from '../components/UserMenu'
import AdminNav from '../components/AdminNav'

const ROLES = [
  { value: 'user', label: 'Utente' },
  { value: 'admin', label: 'Amministratore' },
]

function roleLabel(role) {
  return ROLES.find((r) => r.value === role)?.label || role
}

export default function UsersPage() {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [selectedUserId, setSelectedUserId] = useState(null)
  const [editPassword, setEditPassword] = useState('')
  const [editRole, setEditRole] = useState('user')
  const [editActive, setEditActive] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState('')
  const [saveSuccess, setSaveSuccess] = useState('')

  const [showCreate, setShowCreate] = useState(false)
  const [newUsername, setNewUsername] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [newRole, setNewRole] = useState('user')
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState('')

  const loadUsers = useCallback(() => {
    setLoading(true)
    setError('')
    authFetch('/api/users')
      .then(async (res) => {
        const data = await res.json()
        if (!res.ok) {
          throw new Error(data.error || 'Errore nel caricamento utenti')
        }
        setUsers(data.data || [])
      })
      .catch((err) => {
        console.error('Error fetching users:', err)
        setError(err.message)
      })
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    loadUsers()
  }, [loadUsers])

  const selectedUser = users.find((u) => u.id === selectedUserId) || null

  const handleSelectUser = (user) => {
    setSelectedUserId(user.id)
    setEditPassword('')
    setEditRole(user.role)
    setEditActive(user.is_active)
    setSaveError('')
    setSaveSuccess('')
    setShowCreate(false)
  }

  const handleCreate = async (e) => {
    e.preventDefault()
    setCreateError('')
    setCreating(true)

    try {
      const res = await authFetch('/api/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: newUsername.trim(),
          password: newPassword,
          role: newRole,
        }),
      })
      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.error || 'Creazione utente non riuscita')
      }

      setNewUsername('')
      setNewPassword('')
      setNewRole('user')
      setShowCreate(false)
      loadUsers()
      if (data.user) {
        handleSelectUser(data.user)
      }
    } catch (err) {
      setCreateError(err.message)
    } finally {
      setCreating(false)
    }
  }

  const handleSave = async (e) => {
    e.preventDefault()
    if (!selectedUser) return

    setSaveError('')
    setSaveSuccess('')
    setSaving(true)

    const payload = { role: editRole, is_active: editActive }
    if (editPassword) {
      payload.password = editPassword
    }

    try {
      const res = await authFetch(`/api/users/${selectedUser.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.error || 'Aggiornamento non riuscito')
      }

      setEditPassword('')
      setSaveSuccess('Utente aggiornato.')
      loadUsers()
    } catch (err) {
      setSaveError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="app-title-group">
          <a href="/" className="app-logo-link">
            <img src="/logo.webp" alt="Intex" className="app-logo" />
          </a>
          <span className="badge-mock">Gestione Utenti</span>
        </div>
        <div className="app-header__actions">
          <UserMenu />
          <AdminNav />
          <a href="/" className="btn">
            ← Torna alla consultazione
          </a>
        </div>
      </header>

      <div className="users-layout">
        <div className="panel users-list-panel">
          <div className="panel__head">
            <span>Utenti ({users.length})</span>
            <button
              type="button"
              className="btn btn--primary btn--sm"
              onClick={() => {
                setShowCreate(true)
                setSelectedUserId(null)
                setCreateError('')
              }}
            >
              + Nuovo utente
            </button>
          </div>
          <div className="panel__body panel__body--compact">
            {loading ? (
              <div className="loading-indicator">
                <div className="spinner" />
                <span>Caricamento utenti...</span>
              </div>
            ) : error ? (
              <p className="users-empty users-empty--error">{error}</p>
            ) : users.length === 0 ? (
              <p className="users-empty">Nessun utente trovato.</p>
            ) : (
              <div className="table-wrap">
                <table className="data users-table">
                  <thead>
                    <tr>
                      <th>Username</th>
                      <th>Ruolo</th>
                      <th>Stato</th>
                      <th>Creato il</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((user) => (
                      <tr
                        key={user.id}
                        className={`users-table__row${selectedUserId === user.id ? ' is-selected' : ''}`}
                        onClick={() => handleSelectUser(user)}
                      >
                        <td>{user.username}</td>
                        <td>
                          <span className={`users-role users-role--${user.role}`}>
                            {roleLabel(user.role)}
                          </span>
                        </td>
                        <td>
                          <span className={user.is_active ? 'users-status--active' : 'users-status--inactive'}>
                            {user.is_active ? 'Attivo' : 'Disattivo'}
                          </span>
                        </td>
                        <td>{user.created_at}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        <div className="panel users-detail-panel">
          <div className="panel__head">
            <span>
              {showCreate
                ? 'Nuovo utente'
                : selectedUser
                  ? `Modifica — ${selectedUser.username}`
                  : 'Seleziona un utente'}
            </span>
          </div>
          <div className="panel__body">
            {showCreate ? (
              <form className="users-form" onSubmit={handleCreate}>
                <label className="users-form__field">
                  <span>Username / Email</span>
                  <input
                    type="text"
                    value={newUsername}
                    onChange={(e) => setNewUsername(e.target.value)}
                    required
                    disabled={creating}
                    autoComplete="off"
                  />
                </label>

                <label className="users-form__field">
                  <span>Password</span>
                  <input
                    type="text"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    required
                    disabled={creating}
                    autoComplete="off"
                  />
                </label>

                <label className="users-form__field">
                  <span>Ruolo</span>
                  <select
                    value={newRole}
                    onChange={(e) => setNewRole(e.target.value)}
                    disabled={creating}
                  >
                    {ROLES.map((role) => (
                      <option key={role.value} value={role.value}>
                        {role.label}
                      </option>
                    ))}
                  </select>
                </label>

                {createError && <p className="users-form__error">{createError}</p>}

                <div className="users-form__actions">
                  <button
                    type="button"
                    className="btn"
                    onClick={() => setShowCreate(false)}
                    disabled={creating}
                  >
                    Annulla
                  </button>
                  <button type="submit" className="btn btn--primary" disabled={creating}>
                    {creating ? 'Creazione...' : 'Crea utente'}
                  </button>
                </div>
              </form>
            ) : !selectedUser ? (
              <p className="users-empty">
                Clicca su un utente per modificarlo oppure crea un nuovo utente.
              </p>
            ) : (
              <form className="users-form" onSubmit={handleSave}>
                <div className="users-form__readonly">
                  <span className="users-form__readonly-label">Username</span>
                  <span>{selectedUser.username}</span>
                </div>

                <label className="users-form__field">
                  <span>Nuova password</span>
                  <input
                    type="text"
                    value={editPassword}
                    onChange={(e) => setEditPassword(e.target.value)}
                    placeholder="Lascia vuoto per non modificare"
                    disabled={saving}
                    autoComplete="off"
                  />
                </label>

                <label className="users-form__field">
                  <span>Ruolo</span>
                  <select
                    value={editRole}
                    onChange={(e) => setEditRole(e.target.value)}
                    disabled={saving}
                  >
                    {ROLES.map((role) => (
                      <option key={role.value} value={role.value}>
                        {role.label}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="users-form__checkbox">
                  <input
                    type="checkbox"
                    checked={editActive}
                    onChange={(e) => setEditActive(e.target.checked)}
                    disabled={saving}
                  />
                  <span>Utente attivo</span>
                </label>

                {saveError && <p className="users-form__error">{saveError}</p>}
                {saveSuccess && <p className="users-form__success">{saveSuccess}</p>}

                <div className="users-form__actions">
                  <button type="submit" className="btn btn--primary" disabled={saving}>
                    {saving ? 'Salvataggio...' : 'Salva modifiche'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
