import React, { useState, useEffect, useCallback } from 'react'
import { authFetch } from '../utils/auth'
import UserMenu from '../components/UserMenu'
import AdminNav from '../components/AdminNav'
import Pagination from '../components/Pagination'

const PAGE_SIZE = 20

function formatBytes(n) {
  if (n == null) return '—'
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / (1024 * 1024)).toFixed(1)} MB`
}

function AuthImage({ sessionId }) {
  const [url, setUrl] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let objectUrl
    let cancelled = false
    setUrl(null)
    setError('')
    authFetch(`/api/admin/ocr-bolle/${sessionId}/image`)
      .then(async (res) => {
        if (!res.ok) {
          const data = await res.json().catch(() => ({}))
          throw new Error(data.error || 'Immagine non disponibile')
        }
        return res.blob()
      })
      .then((blob) => {
        if (cancelled) return
        objectUrl = URL.createObjectURL(blob)
        setUrl(objectUrl)
      })
      .catch((err) => {
        if (!cancelled) setError(err.message)
      })
    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [sessionId])

  if (error) return <p className="users-empty users-empty--error">{error}</p>
  if (!url) {
    return (
      <div className="loading-indicator">
        <div className="spinner" />
        <span>Caricamento immagine...</span>
      </div>
    )
  }
  return <img src={url} alt={`Bolla sessione ${sessionId}`} className="ocr-bolle-image" />
}

function MatchSummary({ match, ocr }) {
  if (!match) return <p className="users-empty">Nessun risultato di matching salvato.</p>
  const cliente = match.cliente || {}
  const selezionato = cliente.selezionato
  const candidati = cliente.candidati || []
  const righe = match.righe_match || []
  const ocrByRiga = new Map((ocr?.righe || []).map((r) => [r.riga, r]))

  return (
    <div className="ocr-bolle-match">
      <div className="detail-header-info chats-detail-meta">
        <div className="detail-info-item">
          <span className="detail-info-item__label">Cliente scelto</span>
          <span className="detail-info-item__value">
            {selezionato
              ? `${selezionato.codice_cliente || '—'} — ${selezionato.ragione_sociale || ''}`
              : '—'}
          </span>
        </div>
        <div className="detail-info-item">
          <span className="detail-info-item__label">Candidati cliente</span>
          <span className="detail-info-item__value">{candidati.length}</span>
        </div>
        <div className="detail-info-item">
          <span className="detail-info-item__label">Righe matchate</span>
          <span className="detail-info-item__value">{righe.length}</span>
        </div>
      </div>

      {righe.length > 0 && (
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>#</th>
                <th>Testo riga / fasi</th>
                <th>Top ciclo</th>
                <th>Score</th>
              </tr>
            </thead>
            <tbody>
              {righe.map((item, idx) => {
                const top = (item.candidati_ciclo || [])[0]
                const ocrRiga = ocrByRiga.get(item.riga) || {}
                return (
                  <tr key={idx}>
                    <td>{item.riga ?? idx + 1}</td>
                    <td>
                      <div className="ocr-bolle-riga-text">
                        {ocrRiga.fasi_testo
                          || ocrRiga.descrizione_articolo
                          || ocrRiga.codice_articolo
                          || (item.codici_cercati || []).join(', ')
                          || '—'}
                      </div>
                    </td>
                    <td>
                      {top ? (
                        <code className="chats-code">{top.codice_ciclo || '—'}</code>
                      ) : (
                        '—'
                      )}
                    </td>
                    <td>{top?.score != null ? Number(top.score).toFixed(2) : '—'}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export default function OcrBollePage() {
  const [sessions, setSessions] = useState([])
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(1)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [q, setQ] = useState('')
  const [qApplied, setQApplied] = useState('')

  const [selectedId, setSelectedId] = useState(null)
  const [detail, setDetail] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState('')
  const [showOcrJson, setShowOcrJson] = useState(false)

  const loadList = useCallback(() => {
    setLoading(true)
    setError('')
    const params = new URLSearchParams({
      page: String(page),
      limit: String(PAGE_SIZE),
    })
    if (qApplied) params.set('q', qApplied)
    authFetch(`/api/admin/ocr-bolle?${params}`)
      .then(async (res) => {
        const data = await res.json()
        if (!res.ok) throw new Error(data.error || 'Errore nel caricamento storico')
        setSessions(data.data || [])
        setPages(data.pages || 1)
        setTotal(data.total || 0)
      })
      .catch((err) => {
        console.error(err)
        setError(err.message)
      })
      .finally(() => setLoading(false))
  }, [page, qApplied])

  useEffect(() => {
    loadList()
  }, [loadList])

  useEffect(() => {
    if (!selectedId) {
      setDetail(null)
      return
    }
    setDetailLoading(true)
    setDetailError('')
    setShowOcrJson(false)
    authFetch(`/api/admin/ocr-bolle/${selectedId}`)
      .then(async (res) => {
        const data = await res.json()
        if (!res.ok) throw new Error(data.error || 'Dettaglio non disponibile')
        setDetail(data)
      })
      .catch((err) => {
        setDetailError(err.message)
        setDetail(null)
      })
      .finally(() => setDetailLoading(false))
  }, [selectedId])

  const handleSearch = (e) => {
    e.preventDefault()
    setPage(1)
    setQApplied(q.trim())
  }

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="app-title-group">
          <a href="/" className="app-logo-link">
            <img src="/logo.webp" alt="Intex" className="app-logo" />
          </a>
          <span className="badge-mock">Storico OCR bolle</span>
        </div>
        <div className="app-header__actions">
          <UserMenu />
          <AdminNav />
          <a href="/" className="btn">
            ← Torna alla consultazione
          </a>
        </div>
      </header>

      <div className="chats-layout">
        <div className="panel chats-list-panel">
          <div className="panel__head">
            <span>Sessioni ({total})</span>
          </div>
          <div className="panel__body panel__body--compact">
            <form className="sinonimi-filters" onSubmit={handleSearch}>
              <label className="users-form__field" style={{ flex: 1 }}>
                <span>Cerca</span>
                <input
                  type="search"
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                  placeholder="Utente, cliente, sha, id…"
                />
              </label>
              <button type="submit" className="btn btn--primary btn--sm" style={{ alignSelf: 'flex-end' }}>
                Filtra
              </button>
            </form>

            {loading ? (
              <div className="loading-indicator">
                <div className="spinner" />
                <span>Caricamento storico...</span>
              </div>
            ) : error ? (
              <p className="users-empty users-empty--error">{error}</p>
            ) : sessions.length === 0 ? (
              <p className="users-empty">Nessuna sessione OCR salvata.</p>
            ) : (
              <>
                <div className="table-wrap">
                  <table className="data chats-table">
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>Data</th>
                        <th>Utente</th>
                        <th>Cliente</th>
                        <th>Righe</th>
                        <th>Img</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sessions.map((s) => (
                        <tr
                          key={s.id}
                          className={`chats-table__row${selectedId === s.id ? ' is-selected' : ''}`}
                          onClick={() => setSelectedId(s.id)}
                        >
                          <td>{s.id}</td>
                          <td>{s.created_at}</td>
                          <td>{s.username || '—'}</td>
                          <td>{s.cliente_scelto || '—'}</td>
                          <td>{s.n_righe}</td>
                          <td>{s.has_image ? '✓' : '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <Pagination
                  page={page}
                  pages={pages}
                  total={total}
                  onPageChange={setPage}
                  label="Sessioni"
                />
              </>
            )}
          </div>
        </div>

        <div className="panel chats-detail-panel">
          <div className="panel__head">
            <span>
              {selectedId ? `Sessione #${selectedId}` : 'Seleziona una sessione'}
            </span>
          </div>
          <div className="panel__body">
            {!selectedId ? (
              <p className="chats-empty">
                Clicca su una riga per vedere immagine, OCR e matching.
              </p>
            ) : detailLoading ? (
              <div className="loading-indicator">
                <div className="spinner" />
                <span>Caricamento dettaglio...</span>
              </div>
            ) : detailError ? (
              <p className="users-empty users-empty--error">{detailError}</p>
            ) : detail ? (
              <div className="ocr-bolle-detail">
                <div className="detail-header-info chats-detail-meta">
                  <div className="detail-info-item">
                    <span className="detail-info-item__label">Utente</span>
                    <span className="detail-info-item__value">{detail.username || '—'}</span>
                  </div>
                  <div className="detail-info-item">
                    <span className="detail-info-item__label">Creato</span>
                    <span className="detail-info-item__value">{detail.created_at}</span>
                  </div>
                  <div className="detail-info-item">
                    <span className="detail-info-item__label">Modello</span>
                    <span className="detail-info-item__value">
                      <code className="chats-code">{detail.model}</code>
                    </span>
                  </div>
                  <div className="detail-info-item">
                    <span className="detail-info-item__label">Dimensione</span>
                    <span className="detail-info-item__value">{formatBytes(detail.image_bytes)}</span>
                  </div>
                  <div className="detail-info-item">
                    <span className="detail-info-item__label">SHA256</span>
                    <span className="detail-info-item__value">
                      <code className="chats-code" title={detail.image_sha256}>
                        {(detail.image_sha256 || '').slice(0, 12)}…
                      </code>
                    </span>
                  </div>
                  <div className="detail-info-item">
                    <span className="detail-info-item__label">Cliente scelto</span>
                    <span className="detail-info-item__value">{detail.cliente_scelto || '—'}</span>
                  </div>
                </div>

                <section className="ocr-bolle-section">
                  <h3 className="ocr-bolle-section__title">Immagine bolla</h3>
                  {detail.has_image ? (
                    <AuthImage sessionId={detail.id} />
                  ) : (
                    <p className="users-empty">
                      Immagine non presente su disco (sessione precedente alla persistenza file).
                    </p>
                  )}
                </section>

                <section className="ocr-bolle-section">
                  <h3 className="ocr-bolle-section__title">Matching</h3>
                  <MatchSummary match={detail.match} ocr={detail.ocr} />
                </section>

                <section className="ocr-bolle-section">
                  <div className="ocr-bolle-section__head">
                    <h3 className="ocr-bolle-section__title">OCR JSON</h3>
                    <button
                      type="button"
                      className="btn btn--sm"
                      onClick={() => setShowOcrJson((v) => !v)}
                    >
                      {showOcrJson ? 'Nascondi' : 'Mostra'}
                    </button>
                  </div>
                  {showOcrJson && (
                    <pre className="ocr-bolle-json">
                      {JSON.stringify(detail.ocr, null, 2)}
                    </pre>
                  )}
                </section>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  )
}
