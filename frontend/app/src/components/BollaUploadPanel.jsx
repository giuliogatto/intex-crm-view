import React, { useEffect, useRef, useState } from 'react'
import LoadingOverlay from './LoadingOverlay'
import BollaAnalysisView from './BollaAnalysisView'
import { authFetch } from '../utils/auth'

const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/webp']
const MAX_BYTES = 15 * 1024 * 1024

const STAGES = [
  { after: 0, label: 'Invio immagine…' },
  { after: 2000, label: 'Estrazione testo dalla bolla (OCR)…' },
  { after: 25000, label: 'Ricerca cliente e cicli…' },
]

export default function BollaUploadPanel({ onOpenInRicerca }) {
  const [file, setFile] = useState(null)
  const [previewUrl, setPreviewUrl] = useState(null)
  const [dragOver, setDragOver] = useState(false)
  const [loading, setLoading] = useState(false)
  const [stage, setStage] = useState(STAGES[0].label)
  const [rematching, setRematching] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)
  const [codiceCliente, setCodiceCliente] = useState('')
  const inputRef = useRef(null)

  useEffect(() => {
    if (!previewUrl) return undefined
    return () => URL.revokeObjectURL(previewUrl)
  }, [previewUrl])

  useEffect(() => {
    if (!loading) return undefined
    const timers = STAGES.map((s) => setTimeout(() => setStage(s.label), s.after))
    return () => timers.forEach(clearTimeout)
  }, [loading])

  const selectFile = (f) => {
    if (!f) return
    if (!ACCEPTED_TYPES.includes(f.type)) {
      setError('Formato non supportato: caricare JPEG, PNG o WEBP.')
      return
    }
    if (f.size > MAX_BYTES) {
      setError('Immagine troppo grande (max 15 MB).')
      return
    }
    setError(null)
    setResult(null)
    setCodiceCliente('')
    setFile(f)
    setPreviewUrl(URL.createObjectURL(f))
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    selectFile(e.dataTransfer.files?.[0])
  }

  const applyResult = (data) => {
    setResult(data)
    setCodiceCliente(data.codice_cliente || '')
  }

  const analyze = async (force = false) => {
    if (!file) return
    setLoading(true)
    setError(null)
    try {
      const form = new FormData()
      form.append('file', file)
      if (force) form.append('force', '1')
      const res = await authFetch('/api/cicli/ocr-bolla', { method: 'POST', body: form })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        if (data.code === 'ocr_no_credits' || res.status === 402) {
          setError(
            data.error
            || 'Credito OpenAI esaurito: ricaricare il piano su platform.openai.com (Billing) e riprovare.'
          )
        } else {
          setError(data.error || `Errore server (${res.status})`)
        }
        return
      }
      applyResult(data)
    } catch (e) {
      console.error('Error OCR bolla:', e)
      setError('Impossibile contattare il server. Riprovare.')
    } finally {
      setLoading(false)
    }
  }

  const rematch = async (nextCliente) => {
    if (!result) return
    setCodiceCliente(nextCliente)
    setRematching(true)
    setError(null)
    try {
      const res = await authFetch('/api/cicli/ocr-bolla/match', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: result.session_id,
          ocr: result.ocr,
          codice_cliente: nextCliente || null,
        }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        setError(data.error || `Errore server (${res.status})`)
        return
      }
      applyResult({ ...result, ...data })
    } catch (e) {
      console.error('Error rematch bolla:', e)
      setError('Impossibile contattare il server. Riprovare.')
    } finally {
      setRematching(false)
    }
  }

  const reset = () => {
    setFile(null)
    setPreviewUrl(null)
    setResult(null)
    setError(null)
    setCodiceCliente('')
    if (inputRef.current) inputRef.current.value = ''
  }

  return (
    <>
      {(loading || rematching) && <LoadingOverlay />}
      {loading && <div className="bolla-stage">{stage}</div>}

      <div className={`bolla-layout${previewUrl ? ' bolla-layout--with-preview' : ''}`}>
        <div className="bolla-main">
          <div className="panel">
            <div className="panel__head">
              <span>Upload bolla</span>
              {result && (
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button type="button" className="btn btn--sm" onClick={() => analyze(true)}>
                    Rianalizza
                  </button>
                  <button type="button" className="btn btn--sm" onClick={reset}>
                    Nuova bolla
                  </button>
                </div>
              )}
            </div>
            <div className="panel__body">
              {!result && (
                <>
                  <div
                    className={`bolla-dropzone${dragOver ? ' bolla-dropzone--over' : ''}`}
                    onDragOver={(e) => {
                      e.preventDefault()
                      setDragOver(true)
                    }}
                    onDragLeave={() => setDragOver(false)}
                    onDrop={handleDrop}
                    onClick={() => inputRef.current?.click()}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click()
                    }}
                  >
                    <div className="bolla-dropzone__icon">📄</div>
                    <div className="bolla-dropzone__title">
                      {file ? file.name : 'Trascina qui la foto della bolla o clicca per selezionarla'}
                    </div>
                    <div className="text-secondary">
                      JPEG, PNG o WEBP, max 15 MB. Inquadrare tutta la bolla, ben illuminata e a fuoco.
                    </div>
                    <input
                      ref={inputRef}
                      type="file"
                      accept={ACCEPTED_TYPES.join(',')}
                      style={{ display: 'none' }}
                      onChange={(e) => selectFile(e.target.files?.[0])}
                    />
                  </div>
                  <div className="actions-bar" style={{ marginTop: '1rem' }}>
                    <button
                      type="button"
                      className="btn btn--primary"
                      disabled={!file || loading}
                      onClick={() => analyze(false)}
                    >
                      Analizza bolla
                    </button>
                  </div>
                </>
              )}
              {error && <div className="ddt-error-message" style={{ marginTop: '1rem' }}>⚠️ {error}</div>}

              {result?.ocr && (
                <BollaAnalysisView
                  ocr={result.ocr}
                  cliente={result.cliente}
                  righeMatch={result.righe_match}
                  codiceCliente={codiceCliente}
                  capabilities={result.capabilities}
                  onSelectCliente={rematch}
                  onOpenInRicerca={onOpenInRicerca}
                />
              )}
            </div>
          </div>
        </div>

        {previewUrl && (
          <div className="bolla-preview panel">
            <div className="panel__head">Immagine</div>
            <div className="panel__body">
              <a href={previewUrl} target="_blank" rel="noreferrer">
                <img src={previewUrl} alt="Bolla caricata" />
              </a>
            </div>
          </div>
        )}
      </div>
    </>
  )
}
