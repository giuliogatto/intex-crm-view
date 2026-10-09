import React, { useCallback, useEffect, useState } from 'react'
import CustomerAutocomplete from '../components/CustomerAutocomplete'
import SeasonAutocomplete from '../components/SeasonAutocomplete'
import Pagination from '../components/Pagination'
import LoadingOverlay from '../components/LoadingOverlay'
import { authFetch } from '../utils/auth'

const PAGE_SIZE = 50

const EMPTY_FILTERS = {
  codice_cliente: '',
  stagione: '',
  articolo: '',
  composizione: '',
  descrizione: '',
}

function cicloKey(item) {
  return [
    item.codice_cliente,
    item.codice_articolo,
    item.codice_ciclo,
    item.codice_linea,
    item.codice_stagione,
    item.codice_composizione,
  ].join('|')
}

export default function CicliPage() {
  const [filters, setFilters] = useState({ ...EMPTY_FILTERS })
  const [appliedFilters, setAppliedFilters] = useState({ ...EMPTY_FILTERS })
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(1)
  const [total, setTotal] = useState(0)
  const [expandedKey, setExpandedKey] = useState(null)
  const [fasiByKey, setFasiByKey] = useState({})
  const [fasiLoading, setFasiLoading] = useState(null)

  const fetchCicli = useCallback((nextFilters, nextPage = 1) => {
    setLoading(true)
    const params = new URLSearchParams()
    if (nextFilters.codice_cliente) params.append('codice_cliente', nextFilters.codice_cliente)
    if (nextFilters.stagione) params.append('stagione', nextFilters.stagione)
    if (nextFilters.articolo) params.append('articolo', nextFilters.articolo)
    if (nextFilters.composizione) params.append('composizione', nextFilters.composizione)
    if (nextFilters.descrizione) params.append('descrizione', nextFilters.descrizione)
    params.append('page', String(nextPage))
    params.append('limit', String(PAGE_SIZE))

    authFetch(`/api/cicli?${params.toString()}`)
      .then((res) => res.json())
      .then((resData) => {
        setData(resData.data || [])
        setTotal(resData.total ?? 0)
        setPage(resData.page ?? nextPage)
        setPages(resData.pages ?? 1)
        setExpandedKey(null)
      })
      .catch((err) => {
        console.error('Error fetching cicli:', err)
        setData([])
        setTotal(0)
        setPages(1)
      })
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    fetchCicli(EMPTY_FILTERS, 1)
  }, [fetchCicli])

  const handleChange = (e) => {
    const { name, value } = e.target
    setFilters((prev) => ({ ...prev, [name]: value }))
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    setAppliedFilters(filters)
    fetchCicli(filters, 1)
  }

  const handleReset = () => {
    setFilters({ ...EMPTY_FILTERS })
    setAppliedFilters({ ...EMPTY_FILTERS })
    fetchCicli(EMPTY_FILTERS, 1)
  }

  const handlePageChange = (nextPage) => {
    fetchCicli(appliedFilters, nextPage)
  }

  const loadFasi = (item) => {
    const key = cicloKey(item)
    if (expandedKey === key) {
      setExpandedKey(null)
      return
    }
    setExpandedKey(key)
    if (fasiByKey[key]) return

    setFasiLoading(key)
    const params = new URLSearchParams({
      codice_cliente: item.codice_cliente,
      codice_articolo: item.codice_articolo,
      codice_ciclo: item.codice_ciclo,
      codice_linea: item.codice_linea,
      codice_stagione: item.codice_stagione,
      codice_composizione: item.codice_composizione,
    })
    authFetch(`/api/cicli/fasi?${params.toString()}`)
      .then((res) => res.json())
      .then((resData) => {
        setFasiByKey((prev) => ({ ...prev, [key]: resData.data || [] }))
      })
      .catch((err) => {
        console.error('Error fetching fasi:', err)
        setFasiByKey((prev) => ({ ...prev, [key]: [] }))
      })
      .finally(() => setFasiLoading(null))
  }

  return (
    <>
      {loading && <LoadingOverlay />}
      <div className="panel">
        <div className="panel__head">Ricerca cicli di lavorazione</div>
        <div className="panel__body">
          <form onSubmit={handleSubmit} className="filters-form">
            <div className="filters-grid">
              <div className="field">
                <label>Cliente</label>
                <CustomerAutocomplete
                  name="codice_cliente"
                  value={filters.codice_cliente}
                  onChange={handleChange}
                  placeholder="Cerca per nome o codice..."
                  allowClear
                  endpoint="/api/cicli/clienti"
                />
              </div>
              <div className="field">
                <label>Stagione</label>
                <SeasonAutocomplete
                  name="stagione"
                  value={filters.stagione}
                  onChange={handleChange}
                  placeholder="Cerca stagione..."
                  allowClear
                />
              </div>
              <div className="field">
                <label>Articolo</label>
                <input
                  type="text"
                  name="articolo"
                  value={filters.articolo}
                  onChange={handleChange}
                  placeholder="Descrizione articolo..."
                />
              </div>
              <div className="field">
                <label>Composizione</label>
                <input
                  type="text"
                  name="composizione"
                  value={filters.composizione}
                  onChange={handleChange}
                  placeholder="Es. cotone elastan..."
                />
              </div>
              <div className="field">
                <label>Descrizione ciclo</label>
                <input
                  type="text"
                  name="descrizione"
                  value={filters.descrizione}
                  onChange={handleChange}
                  placeholder="Es. tinto stretch marmo..."
                />
              </div>
            </div>
            <div className="actions-bar">
              <div style={{ display: 'flex', gap: '0.75rem' }}>
                <button type="submit" className="btn btn--primary">
                  Cerca
                </button>
                <button type="button" onClick={handleReset} className="btn">
                  Azzera filtri
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>

      <div className="panel">
        <div className="panel__head">
          <span>Risultati cicli{total ? ` (${total})` : ''}</span>
        </div>
        <div className="panel__body">
          {data.length === 0 && !loading ? (
            <div className="empty-state">
              <div className="empty-state-icon">🔎</div>
              <h3>Nessun ciclo trovato</h3>
              <p>Prova a modificare i filtri di ricerca.</p>
            </div>
          ) : (
            <>
              <div className="table-wrap">
                <table className="data">
                  <thead>
                    <tr>
                      <th>Ciclo</th>
                      <th>Descrizione</th>
                      <th>Cliente</th>
                      <th>Articolo</th>
                      <th>Stagione</th>
                      <th>Composizione</th>
                      <th>Linea</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.map((item) => {
                      const key = cicloKey(item)
                      const isOpen = expandedKey === key
                      const fasi = fasiByKey[key] || []
                      return (
                        <React.Fragment key={key}>
                          <tr>
                            <td>
                              <strong>{item.codice_ciclo}</strong>
                              {item.codice_ciclo_cli ? (
                                <div className="text-secondary">{item.codice_ciclo_cli}</div>
                              ) : null}
                            </td>
                            <td>{item.ds_ciclo || '—'}</td>
                            <td>
                              {item.ragione_sociale || '—'}{' '}
                              <span className="text-secondary">({item.codice_cliente})</span>
                            </td>
                            <td>
                              {item.ds_articolo || item.codice_articolo}
                              {item.ds_articolo ? (
                                <div className="text-secondary">{item.codice_articolo}</div>
                              ) : null}
                            </td>
                            <td>
                              {item.ds_stagione || item.codice_stagione || '—'}
                            </td>
                            <td>
                              {item.ds_composizione || item.codice_composizione || '—'}
                            </td>
                            <td>
                              {item.ds_linea || item.codice_linea || '—'}
                            </td>
                            <td>
                              <span className="table-link" onClick={() => loadFasi(item)}>
                                {isOpen ? 'Nascondi fasi' : 'Fasi'}
                              </span>
                            </td>
                          </tr>
                          {isOpen && (
                            <tr>
                              <td colSpan={8}>
                                {fasiLoading === key ? (
                                  <div className="text-secondary">Caricamento fasi…</div>
                                ) : fasi.length === 0 ? (
                                  <div className="text-secondary">Nessuna fase per questo ciclo.</div>
                                ) : (
                                  <table className="data">
                                    <thead>
                                      <tr>
                                        <th>Seq</th>
                                        <th>Fase</th>
                                        <th>Descrizione</th>
                                        <th>UM</th>
                                        <th>Note</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {fasi.map((fase) => (
                                        <tr key={`${key}-${fase.sequenza}`}>
                                          <td>{fase.sequenza}</td>
                                          <td>{fase.codice_fase}</td>
                                          <td>{fase.ds_fase || '—'}</td>
                                          <td>{fase.codice_unita_mis || '—'}</td>
                                          <td>{fase.note || '—'}</td>
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                )}
                              </td>
                            </tr>
                          )}
                        </React.Fragment>
                      )
                    })}
                  </tbody>
                </table>
              </div>
              <Pagination
                page={page}
                pages={pages}
                total={total}
                onPageChange={handlePageChange}
                label="Cicli"
              />
            </>
          )}
        </div>
      </div>
    </>
  )
}
