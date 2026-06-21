import React, { useState, useEffect, useRef } from 'react'
import Filters from './components/Filters'
import DocumentTable from './components/DocumentTable'
import DiscrepancyPanel from './components/DiscrepancyPanel'
import ChatPanel from './components/ChatPanel'
import { API_BASE } from './config'
import {
  matchCliente,
  appendClienteNotFoundMessage,
  replaceOggiPlaceholder,
  extractClienteHint
} from './utils/llm'

function App() {
  const [activeTab, setActiveTab] = useState('bolle')
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(false)
  const [selectedInvoiceId, setSelectedInvoiceId] = useState(null)
  const [invoiceDetail, setInvoiceDetail] = useState(null)
  const [currentFilters, setCurrentFilters] = useState({
    data_inizio: '',
    data_fine: '',
    codice_cliente: '',
    stagione: '',
    stato: 'Tutte'
  })
  const [discrepancyCustomer, setDiscrepancyCustomer] = useState('XXX')
  const [pendingExport, setPendingExport] = useState(false)
  const [pendingInvoiceId, setPendingInvoiceId] = useState(null)
  const clientiCache = useRef(null)
  const skipNextTabFetch = useRef(false)

  // Fetch standard listings based on tab and filters
  const fetchData = (tab, filters = currentFilters) => {
    if (tab === 'discrepanze') return
    setLoading(true)
    setSelectedInvoiceId(null)
    setInvoiceDetail(null)

    const params = new URLSearchParams()
    if (filters.data_inizio) params.append('data_inizio', filters.data_inizio)
    if (filters.data_fine) params.append('data_fine', filters.data_fine)
    if (filters.codice_cliente) params.append('codice_cliente', filters.codice_cliente)
    if (filters.stagione) params.append('stagione', filters.stagione)
    
    // Adjust state parameter name based on tab
    if (tab === 'fatture' && filters.stato && filters.stato !== 'Tutte') {
      params.append('stato', filters.stato)
    } else if (tab === 'offerte' && filters.stato && filters.stato !== 'Tutti') {
      params.append('stato', filters.stato)
    }

    fetch(`${API_BASE}/api/${tab}?${params.toString()}`)
      .then((res) => res.json())
      .then((resData) => {
        if (resData.data) {
          setData(resData.data)
        }
        setLoading(false)
      })
      .catch((err) => {
        console.error('Error fetching list data:', err)
        setLoading(false)
      })
  }

  const handleTabChange = (tab) => {
    setData([])
    setLoading(tab !== 'discrepanze')
    setSelectedInvoiceId(null)
    setInvoiceDetail(null)
    setActiveTab(tab)
  }

  // Fetch list data when activeTab changes
  useEffect(() => {
    if (activeTab !== 'discrepanze') {
      if (skipNextTabFetch.current) {
        skipNextTabFetch.current = false
        return
      }
      fetchData(activeTab)
    }
  }, [activeTab])

  useEffect(() => {
    if (pendingInvoiceId && !loading) {
      setSelectedInvoiceId(pendingInvoiceId)
      setPendingInvoiceId(null)
    }
  }, [pendingInvoiceId, loading])

  // Fetch invoice details when selectedInvoiceId changes
  useEffect(() => {
    if (!selectedInvoiceId) {
      setInvoiceDetail(null)
      return
    }
    setLoading(true)
    fetch(`${API_BASE}/api/fatture/${selectedInvoiceId}`)
      .then((res) => res.json())
      .then((resData) => {
        setInvoiceDetail(resData)
        setLoading(false)
      })
      .catch((err) => {
        console.error('Error fetching invoice details:', err)
        setLoading(false)
      })
  }, [selectedInvoiceId])

  const handleSearch = (filters) => {
    setCurrentFilters(filters)
    fetchData(activeTab, filters)
  }

  const exportCSV = () => {
    if (data.length === 0) return

    let csvContent = 'data:text/csv;charset=utf-8,'
    
    if (activeTab === 'bolle') {
      csvContent += 'N. bolla,Data,Cliente,Codice Cliente,Righe collegate\n'
      data.forEach((row) => {
        csvContent += `"${row.numero_bolla}","${row.data}","${row.cliente}","${row.codice_cliente}","${row.righe_collegate}"\n`
      })
    } else if (activeTab === 'fatture') {
      csvContent += 'N. disp.,Periodo riferimento,Cliente,Codice Cliente,Importo documento,Stato\n'
      data.forEach((row) => {
        csvContent += `"${row.numero_disposizione}","${row.data}","${row.cliente}","${row.codice_cliente}",${row.importo_documento},"${row.stato}"\n`
      })
    } else if (activeTab === 'offerte') {
      csvContent += 'N. offerta,Data,Cliente,Codice Cliente,Stagione,Importo,Stato\n'
      data.forEach((row) => {
        csvContent += `"${row.numero_offerta}","${row.data}","${row.cliente}","${row.codice_cliente}","${row.stagione}",${row.importo},"${row.stato}"\n`
      })
    }

    const encodedUri = encodeURI(csvContent)
    const link = document.createElement('a')
    link.setAttribute('href', encodedUri)
    link.setAttribute('download', `${activeTab}_esportazione.csv`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  useEffect(() => {
    if (pendingExport && !loading && data.length > 0) {
      exportCSV()
      setPendingExport(false)
    }
  }, [pendingExport, loading, data])

  const getClienti = async () => {
    if (clientiCache.current) return clientiCache.current
    const res = await fetch(`${API_BASE}/api/clienti`)
    const resData = await res.json()
    clientiCache.current = resData.data || []
    return clientiCache.current
  }

  const applyLlmResponse = async (llmJson, userMessage = '') => {
    const { area, messaggio } = llmJson || {}
    const filtri = llmJson?.filtri || {}
    const azione = llmJson?.azione || {}
    const tab = area || 'bolle'

    const newFilters = {
      data_inizio: replaceOggiPlaceholder(filtri.data_inizio || ''),
      data_fine: replaceOggiPlaceholder(filtri.data_fine || ''),
      codice_cliente: '',
      stagione: filtri.stagione || '',
      stato: filtri.stato || (tab === 'offerte' ? 'Tutti' : 'Tutte')
    }

    const llmCliente = filtri.cliente?.trim() || ''
    const userHint = extractClienteHint(userMessage)
    const clienti = await getClienti()

    const llmMatch = llmCliente ? matchCliente(llmCliente, clienti) : null
    const userMatch = userHint ? matchCliente(userHint, clienti) : null

    let matchResult = { codice: '', matched: true, ambiguous: false, candidates: [] }
    if (userMatch?.ambiguous) {
      matchResult = userMatch
    } else if (llmMatch) {
      matchResult = llmMatch
    } else if (userMatch) {
      matchResult = userMatch
    }

    newFilters.codice_cliente = matchResult.codice

    const clienteQuery = userHint || llmCliente
    const finalMessaggio = appendClienteNotFoundMessage(
      messaggio,
      clienteQuery,
      matchResult
    )

    const disambiguationContext = { tab, filtri: newFilters, azione }

    if (matchResult.ambiguous) {
      setData([])
      setLoading(false)
      setSelectedInvoiceId(null)
      setInvoiceDetail(null)
      skipNextTabFetch.current = true
      setActiveTab(tab)
      setCurrentFilters(newFilters)

      return {
        messaggio: finalMessaggio || 'Richiesta elaborata.',
        disambiguation: {
          prompt: 'Molteplici clienti trovati, quale desideri?',
          candidates: matchResult.candidates,
          context: disambiguationContext
        }
      }
    }

    if (tab === 'discrepanze') {
      setDiscrepancyCustomer(matchResult.codice || 'XXX')
      setData([])
      setLoading(false)
      setSelectedInvoiceId(null)
      setInvoiceDetail(null)
      setActiveTab('discrepanze')
      return { messaggio: finalMessaggio || 'Apertura pannello auditing discrepanze.' }
    }

    setData([])
    setLoading(true)
    setSelectedInvoiceId(null)
    setInvoiceDetail(null)
    skipNextTabFetch.current = true
    setActiveTab(tab)
    setCurrentFilters(newFilters)
    fetchData(tab, newFilters)

    if (azione.tipo === 'dettaglio_fattura' && azione.numero_documento) {
      setPendingInvoiceId(azione.numero_documento)
    } else if (azione.tipo === 'esporta_csv') {
      setPendingExport(true)
    }

    return { messaggio: finalMessaggio || 'Richiesta elaborata.' }
  }

  const applyClienteSelection = (codice, context) => {
    const { tab, filtri, azione = {} } = context
    const newFilters = { ...filtri, codice_cliente: codice }

    if (tab === 'discrepanze') {
      setDiscrepancyCustomer(codice)
      setCurrentFilters(newFilters)
      setActiveTab('discrepanze')
      return
    }

    setData([])
    setLoading(true)
    setSelectedInvoiceId(null)
    setInvoiceDetail(null)
    skipNextTabFetch.current = true
    setActiveTab(tab)
    setCurrentFilters(newFilters)
    fetchData(tab, newFilters)

    if (azione.tipo === 'dettaglio_fattura' && azione.numero_documento) {
      setPendingInvoiceId(azione.numero_documento)
    } else if (azione.tipo === 'esporta_csv') {
      setPendingExport(true)
    }
  }

  // Pre-load filter inputs for interactive Q&A shortcuts
  const applyQuestionShortcut = (tab, qFilters) => {
    setData([])
    setLoading(true)
    setSelectedInvoiceId(null)
    setInvoiceDetail(null)
    skipNextTabFetch.current = true
    setActiveTab(tab)
    setCurrentFilters((prev) => {
      const merged = { ...prev, ...qFilters }
      fetchData(tab, merged)
      return merged
    })
  }

  const formatEuro = (num) => {
    return new Intl.NumberFormat('it-IT', {
      style: 'currency',
      currency: 'EUR'
    }).format(num)
  }

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="app-title-group">
          <h1>Intex Consultazione</h1>
          <span className="badge-mock">Database Active</span>
        </div>
        <div className="badge-mock" style={{ background: 'rgba(255,255,255,0.05)', color: '#fff' }}>
          Port: 5447
        </div>
      </header>

      <nav className="nav-primary">
        <button
          className={`nav-tab ${activeTab === 'bolle' ? 'is-active' : ''}`}
          onClick={() => handleTabChange('bolle')}
        >
          📦 Bolle / DDT
        </button>
        <button
          className={`nav-tab ${activeTab === 'fatture' ? 'is-active' : ''}`}
          onClick={() => handleTabChange('fatture')}
        >
          🧾 Fatture
        </button>
        <button
          className={`nav-tab ${activeTab === 'offerte' ? 'is-active' : ''}`}
          onClick={() => handleTabChange('offerte')}
        >
          📋 Offerte / Ordini
        </button>
        <button
          className={`nav-tab ${activeTab === 'discrepanze' ? 'is-active' : ''}`}
          onClick={() => handleTabChange('discrepanze')}
        >
          ⚖️ Auditing Discrepanze
        </button>
      </nav>

      <div className="dashboard-grid">
        <div className="dashboard-chat">
          <ChatPanel onResponse={applyLlmResponse} onClienteSelect={applyClienteSelection} />
        </div>

        <div className="dashboard-main">
          {activeTab !== 'discrepanze' && (
            <div className="panel">
              <div className="panel__head">Filtri di Ricerca</div>
              <div className="panel__body">
                <Filters
                  activeTab={activeTab}
                  onSearch={handleSearch}
                  onExport={exportCSV}
                  filterValues={currentFilters}
                />
              </div>
            </div>
          )}

          {/* Detailed Invoice Rows Panel */}
          {selectedInvoiceId && invoiceDetail && (
            <div className="panel">
              <div className="panel__head">
                <span>Dettaglio Documento — Riga Disposition N. {invoiceDetail.header.numero_disposizione}</span>
                <button className="btn" onClick={() => setSelectedInvoiceId(null)}>Chiudi Dettaglio</button>
              </div>
              <div className="panel__body">
                <div className="detail-header-info">
                  <div className="detail-info-item">
                    <span className="detail-info-item__label">Cliente</span>
                    <span className="detail-info-item__value">{invoiceDetail.header.cliente} ({invoiceDetail.header.codice_cliente})</span>
                  </div>
                  <div className="detail-info-item">
                    <span className="detail-info-item__label">Data Fattura</span>
                    <span className="detail-info-item__value">{invoiceDetail.header.data}</span>
                  </div>
                  <div className="detail-info-item">
                    <span className="detail-info-item__label">Totale Documento</span>
                    <span className="detail-info-item__value">{formatEuro(invoiceDetail.header.importo_totale)}</span>
                  </div>
                  <div className="detail-info-item">
                    <span className="detail-info-item__label">Stato</span>
                    <span className={`pill pill--${invoiceDetail.header.stato.toLowerCase()}`} style={{ marginTop: '0.2rem' }}>
                      {invoiceDetail.header.stato}
                    </span>
                  </div>
                </div>

                <div className="table-wrap">
                  <table className="data">
                    <thead>
                      <tr>
                        <th>#</th>
                        <th>Data bolla</th>
                        <th>N. bolla</th>
                        <th>Articolo</th>
                        <th>Colore</th>
                        <th>Kg fatturati</th>
                        <th>Capi fatturati</th>
                        <th>Importo riga</th>
                      </tr>
                    </thead>
                    <tbody>
                      {invoiceDetail.lines.map((line) => (
                        <tr key={line.riga_disposizione}>
                          <td>{line.riga_disposizione}</td>
                          <td>{line.data_bolla}</td>
                          <td>{line.numero_bolla || '—'}</td>
                          <td><strong>{line.articolo}</strong></td>
                          <td>{line.colore}</td>
                          <td>{line.kg_fatturati}</td>
                          <td>{line.capi_fatturati}</td>
                          <td>{formatEuro(line.importo_riga)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {activeTab !== 'discrepanze' ? (
            <div className="panel">
              <div className="panel__head">
                <span>Risultati ({data.length} record)</span>
              </div>
              {loading ? (
                <div className="loading-indicator">
                  <div className="spinner"></div>
                  <span>Recupero dati in corso...</span>
                </div>
              ) : (
                <DocumentTable
                  activeTab={activeTab}
                  data={data}
                  onViewDetail={setSelectedInvoiceId}
                />
              )}
            </div>
          ) : (
            <DiscrepancyPanel
              selectedCustomer={discrepancyCustomer}
              onCustomerChange={setDiscrepancyCustomer}
            />
          )}
        </div>

        {/* Sidebar Questions Suggestions */}
        <div className="dashboard-sidebar">
          <div className="sidebar-panel">
            <div className="chat-suggestions">
              <h3 className="chat-suggestions__title">💬 Scorciatoie Domande ERP</h3>
              <div className="chat-suggestions__list">
                <button
                  className="chat-suggestion-btn"
                  onClick={() =>
                    applyQuestionShortcut('fatture', {
                      codice_cliente: 'XXX',
                      data_inizio: '2026-01-01',
                      data_fine: '2026-03-31'
                    })
                  }
                >
                  <span className="chat-suggestion-num">1</span>
                  “Mostrami tutte le fatture del cliente TAM emesse tra gennaio e marzo.”
                </button>
                <button
                  className="chat-suggestion-btn"
                  onClick={() =>
                    applyQuestionShortcut('fatture', {
                      codice_cliente: 'XXX',
                      stato: 'Aperta',
                      data_inizio: '',
                      data_fine: ''
                    })
                  }
                >
                  <span className="chat-suggestion-num">2</span>
                  “Quali fatture di TAM & COMPANY risultano ancora aperte?”
                </button>
                <button
                  className="chat-suggestion-btn"
                  onClick={() =>
                    applyQuestionShortcut('bolle', {
                      codice_cliente: 'XXX',
                      data_inizio: '2026-03-01',
                      data_fine: '2026-03-31'
                    })
                  }
                >
                  <span className="chat-suggestion-num">5</span>
                  “Quali bolle/DDT sono state emesse per TAM nel mese di marzo?”
                </button>
                <button
                  className="chat-suggestion-btn"
                  onClick={() =>
                    applyQuestionShortcut('offerte', {
                      codice_cliente: '1283',
                      stagione: 'PE2026',
                      data_inizio: '',
                      data_fine: ''
                    })
                  }
                >
                  <span className="chat-suggestion-num">7</span>
                  “Cerca le offerte di Maglificio Rossi per la stagione PE 2026.”
                </button>
                <button
                  className="chat-suggestion-btn"
                  onClick={() => handleTabChange('discrepanze')}
                >
                  <span className="chat-suggestion-num">9</span>
                  “Confrontami offerta, bolla e fattura per verificare differenze (TAM).”
                </button>
              </div>
            </div>
            
            <div className="chat-suggestions" style={{ background: 'rgba(255,255,255,0.01)', borderColor: 'var(--border-color)' }}>
              <h4 style={{ margin: '0 0 0.5rem 0', fontSize: '0.85rem', textTransform: 'uppercase', color: 'var(--text-secondary)' }}>Note Tecniche</h4>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', lineHeight: '1.4' }}>
                La base di dati è popolata dinamicamente con le migrazioni all'avvio. La tabella <strong>Fatture Dettaglio</strong> e il panel <strong>Discrepanze</strong> mostrano le righe reali mappate dal file di produzione.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
