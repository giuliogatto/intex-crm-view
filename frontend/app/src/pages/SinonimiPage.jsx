import React, { useState, useEffect, useCallback, useMemo } from 'react'
import { authFetch } from '../utils/auth'
import UserMenu from '../components/UserMenu'
import AdminNav from '../components/AdminNav'

export default function SinonimiPage() {
  const [items, setItems] = useState([])
  const [gruppi, setGruppi] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [filterGruppo, setFilterGruppo] = useState('')
  const [filterText, setFilterText] = useState('')

  const [gruppo, setGruppo] = useState('')
  const [termine, setTermine] = useState('')
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState('')
  const [formSuccess, setFormSuccess] = useState('')
  const [deletingKey, setDeletingKey] = useState(null)

  const load = useCallback(() => {
    setLoading(true)
    setError('')
    authFetch('/api/admin/sinonimi')
      .then(async (res) => {
        const data = await res.json()
        if (!res.ok) throw new Error(data.error || 'Errore nel caricamento sinonimi')
        setItems(data.data || [])
        setGruppi(data.gruppi || [])
      })
      .catch((err) => {
        console.error(err)
        setError(err.message)
      })
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const filtered = useMemo(() => {
    const q = filterText.trim().toUpperCase()
    return items.filter((item) => {
      if (filterGruppo && item.gruppo !== filterGruppo) return false
      if (!q) return true
      return item.gruppo.includes(q) || item.termine.includes(q)
    })
  }, [items, filterGruppo, filterText])

  const handleCreate = async (e) => {
    e.preventDefault()
    setFormError('')
    setFormSuccess('')
    setSaving(true)
    try {
      const res = await authFetch('/api/admin/sinonimi', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ gruppo, termine }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Inserimento non riuscito')
      setTermine('')
      setFormSuccess(`Aggiunto: ${data.gruppo} → ${data.termine}`)
      load()
    } catch (err) {
      setFormError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (item) => {
    const key = `${item.gruppo}|${item.termine}`
    if (!window.confirm(`Eliminare «${item.termine}» dal gruppo «${item.gruppo}»?`)) return
    setDeletingKey(key)
    setFormError('')
    try {
      const res = await authFetch('/api/admin/sinonimi', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ gruppo: item.gruppo, termine: item.termine }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Eliminazione non riuscita')
      load()
    } catch (err) {
      setFormError(err.message)
    } finally {
      setDeletingKey(null)
    }
  }

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="app-title-group">
          <a href="/" className="app-logo-link">
            <img src="/logo.webp" alt="Intex" className="app-logo" />
          </a>
          <span className="badge-mock">Sinonimi ricerca</span>
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
            <span>Dizionario ({filtered.length}{filtered.length !== items.length ? ` / ${items.length}` : ''})</span>
          </div>
          <div className="panel__body panel__body--compact">
            <div className="sinonimi-filters">
              <label className="users-form__field">
                <span>Gruppo</span>
                <select value={filterGruppo} onChange={(e) => setFilterGruppo(e.target.value)}>
                  <option value="">Tutti i gruppi</option>
                  {gruppi.map((g) => (
                    <option key={g} value={g}>{g}</option>
                  ))}
                </select>
              </label>
              <label className="users-form__field">
                <span>Cerca</span>
                <input
                  type="search"
                  value={filterText}
                  onChange={(e) => setFilterText(e.target.value)}
                  placeholder="Gruppo o termine…"
                />
              </label>
            </div>

            {loading ? (
              <div className="loading-indicator">
                <div className="spinner" />
                <span>Caricamento sinonimi...</span>
              </div>
            ) : error ? (
              <p className="users-empty users-empty--error">{error}</p>
            ) : filtered.length === 0 ? (
              <p className="users-empty">Nessun sinonimo trovato.</p>
            ) : (
              <div className="table-wrap">
                <table className="data users-table">
                  <thead>
                    <tr>
                      <th>Gruppo</th>
                      <th>Termine</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map((item) => {
                      const key = `${item.gruppo}|${item.termine}`
                      return (
                        <tr key={key}>
                          <td><code className="chats-code">{item.gruppo}</code></td>
                          <td>{item.termine}</td>
                          <td>
                            <button
                              type="button"
                              className="btn btn--sm"
                              disabled={deletingKey === key}
                              onClick={() => handleDelete(item)}
                            >
                              {deletingKey === key ? '…' : 'Elimina'}
                            </button>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        <div className="panel users-detail-panel">
          <div className="panel__head">
            <span>Nuovo sinonimo</span>
          </div>
          <div className="panel__body">
            <form className="users-form" onSubmit={handleCreate}>
              <label className="users-form__field">
                <span>Gruppo</span>
                <input
                  type="text"
                  list="sinonimi-gruppi"
                  value={gruppo}
                  onChange={(e) => setGruppo(e.target.value)}
                  required
                  disabled={saving}
                  placeholder="es. TINTURA"
                  autoComplete="off"
                />
                <datalist id="sinonimi-gruppi">
                  {gruppi.map((g) => (
                    <option key={g} value={g} />
                  ))}
                </datalist>
              </label>

              <label className="users-form__field">
                <span>Termine / abbreviazione</span>
                <input
                  type="text"
                  value={termine}
                  onChange={(e) => setTermine(e.target.value)}
                  required
                  disabled={saving}
                  placeholder="es. TI"
                  autoComplete="off"
                />
              </label>

              <p className="sinonimi-hint">
                I sinonimi espandono le keyword fasi nella ricerca cicli e nell&apos;OCR bolle.
                Gruppo e termine vengono normalizzati in maiuscolo.
              </p>

              {formError && <p className="users-form__error">{formError}</p>}
              {formSuccess && <p className="users-form__success">{formSuccess}</p>}

              <div className="users-form__actions">
                <button type="submit" className="btn btn--primary" disabled={saving}>
                  {saving ? 'Salvataggio...' : 'Aggiungi'}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}
