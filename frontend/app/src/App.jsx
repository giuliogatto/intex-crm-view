import React, { useState, useEffect, useRef } from 'react'
import Filters from './components/Filters'
import DocumentTable from './components/DocumentTable'
import DiscrepancyPanel from './components/DiscrepancyPanel'
import ChatPanel from './components/ChatPanel'
import UserMenu from './components/UserMenu'
import Pagination from './components/Pagination'
import { authFetch, downloadAuthFile } from './utils/auth'
import {
  matchCliente,
  appendClienteNotFoundMessage,
  replaceOggiPlaceholder,
  extractClienteHint,
  isDocumentDetailAction,
  tabForDocumentDetailAction
} from './utils/llm'

const LIST_PAGE_SIZE = 50

function hasActiveFilters(filters, tab) {
  if (filters.data_inizio || filters.data_fine) return true
  if (filters.codice_cliente) return true
  if (filters.stagione) return true
  if (tab === 'fatture' && filters.stato && filters.stato !== 'Tutte') return true
  if (tab === 'offerte' && filters.stato && filters.stato !== 'Tutti') return true
  return false
}

function App() {
  const [activeTab, setActiveTab] = useState('bolle')
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(false)
  const [selectedInvoiceId, setSelectedInvoiceId] = useState(null)
  const [invoiceDetail, setInvoiceDetail] = useState(null)
  const [selectedBollaId, setSelectedBollaId] = useState(null)
  const [bollaDetail, setBollaDetail] = useState(null)
  const [selectedOffertaId, setSelectedOffertaId] = useState(null)
  const [offertaDetail, setOffertaDetail] = useState(null)
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
  const [pendingBollaId, setPendingBollaId] = useState(null)
  const [pendingOffertaId, setPendingOffertaId] = useState(null)
  const [listPage, setListPage] = useState(1)
  const [listTotal, setListTotal] = useState(0)
  const [listPages, setListPages] = useState(1)
  const clientiCache = useRef(null)
  const skipNextTabFetch = useRef(false)

  const clearDocumentDetails = () => {
    setSelectedInvoiceId(null)
    setInvoiceDetail(null)
    setSelectedBollaId(null)
    setBollaDetail(null)
    setSelectedOffertaId(null)
    setOffertaDetail(null)
  }

  // Fetch standard listings based on tab and filters
  const fetchData = (tab, filters = currentFilters, page = 1) => {
    if (tab === 'discrepanze') return
    setLoading(true)
    clearDocumentDetails()

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

    const filtersActive = hasActiveFilters(filters, tab)
    if (!filtersActive) {
      params.append('page', page)
      params.append('limit', LIST_PAGE_SIZE)
    }

    authFetch(`/api/${tab}?${params.toString()}`)
      .then((res) => res.json())
      .then((resData) => {
        if (resData.data) {
          setData(resData.data)
          setListTotal(resData.total ?? resData.data.length)
          if (filtersActive) {
            setListPage(1)
            setListPages(1)
          } else {
            setListPage(resData.page ?? page)
            setListPages(resData.pages ?? 1)
          }
        }
        setLoading(false)
      })
      .catch((err) => {
        console.error('Error fetching list data:', err)
        setLoading(false)
      })
  }

  const handleTabChange = (tab) => {
    clearDocumentDetails()

    if (tab === 'discrepanze') {
      setData([])
      setListPage(1)
      setListTotal(0)
      setListPages(1)
      setLoading(false)
      setActiveTab(tab)
      return
    }

    const tabFilters = tab !== activeTab
      ? { ...currentFilters, stato: tab === 'offerte' ? 'Tutti' : 'Tutte' }
      : currentFilters

    setData([])
    setListPage(1)
    if (tab !== activeTab) {
      setCurrentFilters(tabFilters)
    }
    skipNextTabFetch.current = true
    fetchData(tab, tabFilters, 1)
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

  useEffect(() => {
    if (pendingBollaId && !loading) {
      setSelectedBollaId(pendingBollaId)
      setPendingBollaId(null)
    }
  }, [pendingBollaId, loading])

  useEffect(() => {
    if (pendingOffertaId && !loading) {
      setSelectedOffertaId(pendingOffertaId)
      setPendingOffertaId(null)
    }
  }, [pendingOffertaId, loading])

  // Fetch invoice details when selectedInvoiceId changes
  useEffect(() => {
    if (!selectedInvoiceId) {
      setInvoiceDetail(null)
      return
    }
    setLoading(true)
    authFetch(`/api/fatture/${selectedInvoiceId}`)
      .then(async (res) => {
        const resData = await res.json()
        if (!res.ok || !resData.header) {
          console.error('Error fetching invoice details:', resData.error || res.status)
          setSelectedInvoiceId(null)
          setInvoiceDetail(null)
          return
        }
        setInvoiceDetail(resData)
      })
      .catch((err) => {
        console.error('Error fetching invoice details:', err)
        setSelectedInvoiceId(null)
        setInvoiceDetail(null)
      })
      .finally(() => setLoading(false))
  }, [selectedInvoiceId])

  useEffect(() => {
    if (!selectedBollaId) {
      setBollaDetail(null)
      return
    }
    setLoading(true)
    authFetch(`/api/bolle/${selectedBollaId}`)
      .then(async (res) => {
        const resData = await res.json()
        if (!res.ok || !resData.header) {
          console.error('Error fetching bolla details:', resData.error || res.status)
          setSelectedBollaId(null)
          setBollaDetail(null)
          return
        }
        setBollaDetail(resData)
      })
      .catch((err) => {
        console.error('Error fetching bolla details:', err)
        setSelectedBollaId(null)
        setBollaDetail(null)
      })
      .finally(() => setLoading(false))
  }, [selectedBollaId])

  useEffect(() => {
    if (!selectedOffertaId) {
      setOffertaDetail(null)
      return
    }
    setLoading(true)
    authFetch(`/api/offerte/${selectedOffertaId}`)
      .then(async (res) => {
        const resData = await res.json()
        if (!res.ok || !resData.header) {
          console.error('Error fetching offerta details:', resData.error || res.status)
          setSelectedOffertaId(null)
          setOffertaDetail(null)
          return
        }
        setOffertaDetail(resData)
      })
      .catch((err) => {
        console.error('Error fetching offerta details:', err)
        setSelectedOffertaId(null)
        setOffertaDetail(null)
      })
      .finally(() => setLoading(false))
  }, [selectedOffertaId])

  const handleSearch = (filters) => {
    setCurrentFilters(filters)
    setListPage(1)
    fetchData(activeTab, filters, 1)
  }

  const handleListPageChange = (page) => {
    setListPage(page)
    fetchData(activeTab, currentFilters, page)
  }

  const buildExportParams = (tab, filters) => {
    const params = new URLSearchParams()
    if (filters.data_inizio) params.append('data_inizio', filters.data_inizio)
    if (filters.data_fine) params.append('data_fine', filters.data_fine)
    if (filters.codice_cliente) params.append('codice_cliente', filters.codice_cliente)
    if (filters.stagione) params.append('stagione', filters.stagione)
    if (tab === 'fatture' && filters.stato && filters.stato !== 'Tutte') {
      params.append('stato', filters.stato)
    } else if (tab === 'offerte' && filters.stato && filters.stato !== 'Tutti') {
      params.append('stato', filters.stato)
    }
    return params
  }

  const exportPDF = async () => {
    if (data.length === 0) return
    try {
      const params = buildExportParams(activeTab, currentFilters)
      await downloadAuthFile(`/api/${activeTab}/export/pdf?${params}`, `${activeTab}_esportazione.pdf`)
    } catch (err) {
      console.error('Error exporting PDF:', err)
    }
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
    const res = await authFetch('/api/clienti')
    const resData = await res.json()
    clientiCache.current = resData.data || []
    return clientiCache.current
  }

  const applyPendingDocumentDetail = (azione) => {
    const numero = String(azione.numero_documento || '').trim()
    if (!numero) return

    if (azione.tipo === 'dettaglio_fattura') {
      setPendingInvoiceId(numero)
    } else if (azione.tipo === 'dettaglio_bolla') {
      setPendingBollaId(numero)
    } else if (azione.tipo === 'dettaglio_offerta') {
      setPendingOffertaId(numero)
    }
  }

  const openDocumentDetailFromLlm = (tab, filters, azione, messaggio) => {
    skipNextTabFetch.current = true
    setActiveTab(tab)
    setCurrentFilters(filters)
    setData([])
    setListPage(1)
    clearDocumentDetails()
    setLoading(false)
    applyPendingDocumentDetail(azione)
    return { messaggio: messaggio || 'Richiesta elaborata.' }
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

    if (isDocumentDetailAction(azione)) {
      if (matchResult.ambiguous) {
        newFilters.codice_cliente = ''
      }
      const detailTab = tabForDocumentDetailAction(azione, tab)
      return openDocumentDetailFromLlm(detailTab, newFilters, azione, finalMessaggio)
    }

    if (matchResult.ambiguous) {
      setData([])
      setLoading(false)
      clearDocumentDetails()
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
      clearDocumentDetails()
      setActiveTab('discrepanze')
      return { messaggio: finalMessaggio || 'Apertura pannello auditing discrepanze.' }
    }

    setData([])
    setLoading(true)
    setListPage(1)
    clearDocumentDetails()
    skipNextTabFetch.current = true
    setActiveTab(tab)
    setCurrentFilters(newFilters)
    fetchData(tab, newFilters)

    if (azione.tipo === 'esporta_csv') {
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
    setListPage(1)
    clearDocumentDetails()
    skipNextTabFetch.current = true
    setActiveTab(tab)
    setCurrentFilters(newFilters)
    fetchData(tab, newFilters)

    if (isDocumentDetailAction(azione)) {
      applyPendingDocumentDetail(azione)
    } else if (azione.tipo === 'esporta_csv') {
      setPendingExport(true)
    }
  }

  // Pre-load filter inputs for interactive Q&A shortcuts
  const applyQuestionShortcut = (tab, qFilters) => {
    setData([])
    setListPage(1)
    clearDocumentDetails()
    skipNextTabFetch.current = true

    if (tab === 'discrepanze') {
      setLoading(false)
      setDiscrepancyCustomer(qFilters.codice_cliente || 'XXX')
      setCurrentFilters((prev) => ({ ...prev, ...qFilters }))
      setActiveTab('discrepanze')
      return
    }

    setLoading(true)
    setActiveTab(tab)
    setCurrentFilters((prev) => {
      const merged = { ...prev, ...qFilters }
      fetchData(tab, merged)
      return merged
    })
  }

  const handleViewInvoiceDetail = (id) => {
    setSelectedBollaId(null)
    setBollaDetail(null)
    setSelectedOffertaId(null)
    setOffertaDetail(null)
    setSelectedInvoiceId(id)
  }

  const handleViewBollaDetail = (id) => {
    setSelectedInvoiceId(null)
    setInvoiceDetail(null)
    setSelectedOffertaId(null)
    setOffertaDetail(null)
    setSelectedBollaId(id)
  }

  const handleViewOffertaDetail = (id) => {
    setSelectedInvoiceId(null)
    setInvoiceDetail(null)
    setSelectedBollaId(null)
    setBollaDetail(null)
    setSelectedOffertaId(id)
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
          <img src="/logo.webp" alt="Intex" className="app-logo" />
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <UserMenu />
          <a href="/chats" className="btn">💬 Chats</a>
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
                  onExportPDF={exportPDF}
                  filterValues={currentFilters}
                />
              </div>
            </div>
          )}

          {/* Detailed Invoice Rows Panel */}
          {selectedInvoiceId && invoiceDetail?.header && (
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

          {selectedBollaId && bollaDetail?.header && (
            <div className="panel">
              <div className="panel__head">
                <span>Dettaglio Bolla — N. {bollaDetail.header.numero_bolla}</span>
                <button className="btn" onClick={() => setSelectedBollaId(null)}>Chiudi Dettaglio</button>
              </div>
              <div className="panel__body">
                <div className="detail-header-info">
                  <div className="detail-info-item">
                    <span className="detail-info-item__label">Cliente</span>
                    <span className="detail-info-item__value">{bollaDetail.header.cliente} ({bollaDetail.header.codice_cliente})</span>
                  </div>
                  <div className="detail-info-item">
                    <span className="detail-info-item__label">Data Bolla</span>
                    <span className="detail-info-item__value">{bollaDetail.header.data}</span>
                  </div>
                  <div className="detail-info-item">
                    <span className="detail-info-item__label">Totale Documento</span>
                    <span className="detail-info-item__value">{formatEuro(bollaDetail.header.importo_totale)}</span>
                  </div>
                  <div className="detail-info-item">
                    <span className="detail-info-item__label">Righe</span>
                    <span className="detail-info-item__value">{bollaDetail.lines.length}</span>
                  </div>
                </div>

                <div className="table-wrap">
                  <table className="data">
                    <thead>
                      <tr>
                        <th>#</th>
                        <th>N. disp.</th>
                        <th>Riga disp.</th>
                        <th>N. offerta</th>
                        <th>Articolo</th>
                        <th>Colore</th>
                        <th>Kg consegnati</th>
                        <th>Capi consegnati</th>
                        <th>Importo riga</th>
                      </tr>
                    </thead>
                    <tbody>
                      {bollaDetail.lines.map((line) => (
                        <tr key={line.riga_num}>
                          <td>{line.riga_num}</td>
                          <td>{line.numero_disposizione}</td>
                          <td>{line.riga_disposizione}</td>
                          <td>{line.numero_offerta}</td>
                          <td><strong>{line.articolo}</strong></td>
                          <td>{line.colore}</td>
                          <td>{line.kg_consegnati}</td>
                          <td>{line.capi_consegnati}</td>
                          <td>{formatEuro(line.importo_riga)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {selectedOffertaId && offertaDetail?.header && (
            <div className="panel">
              <div className="panel__head">
                <span>Dettaglio Offerta — N. {offertaDetail.header.numero_offerta}</span>
                <button className="btn" onClick={() => setSelectedOffertaId(null)}>Chiudi Dettaglio</button>
              </div>
              <div className="panel__body">
                <div className="detail-header-info">
                  <div className="detail-info-item">
                    <span className="detail-info-item__label">Cliente</span>
                    <span className="detail-info-item__value">{offertaDetail.header.cliente} ({offertaDetail.header.codice_cliente})</span>
                  </div>
                  <div className="detail-info-item">
                    <span className="detail-info-item__label">Data Offerta</span>
                    <span className="detail-info-item__value">{offertaDetail.header.data}</span>
                  </div>
                  <div className="detail-info-item">
                    <span className="detail-info-item__label">Stagione</span>
                    <span className="detail-info-item__value">{offertaDetail.header.stagione}</span>
                  </div>
                  <div className="detail-info-item">
                    <span className="detail-info-item__label">Totale Documento</span>
                    <span className="detail-info-item__value">{formatEuro(offertaDetail.header.importo_totale)}</span>
                  </div>
                  <div className="detail-info-item">
                    <span className="detail-info-item__label">Stato</span>
                    <span className={`pill pill--${offertaDetail.header.stato.toLowerCase()}`} style={{ marginTop: '0.2rem' }}>
                      {offertaDetail.header.stato}
                    </span>
                  </div>
                </div>

                <div className="table-wrap">
                  <table className="data">
                    <thead>
                      <tr>
                        <th>#</th>
                        <th>Articolo</th>
                        <th>Colore</th>
                        <th>Quantità</th>
                        <th>Prezzo unitario</th>
                        <th>Importo riga</th>
                      </tr>
                    </thead>
                    <tbody>
                      {offertaDetail.lines.map((line) => (
                        <tr key={line.riga_num}>
                          <td>{line.riga_num}</td>
                          <td><strong>{line.articolo}</strong></td>
                          <td>{line.colore}</td>
                          <td>{line.quantita}</td>
                          <td>{formatEuro(line.prezzo_unitario)}</td>
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
                <span>
                  Risultati ({hasActiveFilters(currentFilters, activeTab) ? data.length : listTotal} record)
                </span>
              </div>
              {loading ? (
                <div className="loading-indicator">
                  <div className="spinner"></div>
                  <span>Recupero dati in corso...</span>
                </div>
              ) : (
                <>
                  <DocumentTable
                    activeTab={activeTab}
                    data={data}
                    onViewDetail={handleViewInvoiceDetail}
                    onViewBollaDetail={handleViewBollaDetail}
                    onViewOffertaDetail={handleViewOffertaDetail}
                  />
                  {!hasActiveFilters(currentFilters, activeTab) && (
                    <Pagination
                      page={listPage}
                      pages={listPages}
                      total={listTotal}
                      onPageChange={handleListPageChange}
                      label="Record"
                    />
                  )}
                </>
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
              <h3 className="chat-suggestions__title">💬 Scorciatoie Domande</h3>
              <div className="chat-suggestions__list">
                <button
                  className="chat-suggestion-btn"
                  onClick={() =>
                    applyQuestionShortcut('fatture', {
                      codice_cliente: '2618',
                      data_inizio: '2026-01-01',
                      data_fine: '2026-03-31'
                    })
                  }
                >
                  <span className="chat-suggestion-num">1</span>
                  “Mostrami tutte le fatture del cliente PRIMA SRL emesse tra gennaio e marzo.”
                </button>
                <button
                  className="chat-suggestion-btn"
                  onClick={() =>
                    applyQuestionShortcut('fatture', {
                      codice_cliente: '2618',
                      stato: 'Aperta',
                      data_inizio: '',
                      data_fine: ''
                    })
                  }
                >
                  <span className="chat-suggestion-num">2</span>
                  “Quali fatture di PRIMA SRL risultano ancora aperte?”
                </button>
                <button
                  className="chat-suggestion-btn"
                  onClick={() =>
                    applyQuestionShortcut('bolle', {
                      codice_cliente: '2618',
                      data_inizio: '2026-03-01',
                      data_fine: '2026-03-31'
                    })
                  }
                >
                  <span className="chat-suggestion-num">5</span>
                  “Quali bolle/DDT sono state emesse per PRIMA SRL nel mese di marzo?”
                </button>
                <button
                  className="chat-suggestion-btn"
                  onClick={() =>
                    applyQuestionShortcut('offerte', {
                      codice_cliente: '1283',
                      stagione: 'PE2026',
                      data_inizio: '',
                      data_fine: '',
                      stagione: '',
                      stato: ''
                    })
                  }
                >
                  <span className="chat-suggestion-num">7</span>
                  “Cerca le offerte di Maglificio Rossi per la stagione PE 2026.”
                </button>
                <button
                  className="chat-suggestion-btn"
                  onClick={() =>
                    applyQuestionShortcut('discrepanze', {
                      codice_cliente: '2618'
                    })
                  }
                >
                  <span className="chat-suggestion-num">9</span>
                  “Confrontami offerta, bolla e fattura per verificare differenze di Prima Srl.”
                </button>
              </div>
            </div>
            
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
